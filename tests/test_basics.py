import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QEvent, QPointF, Qt  # noqa: E402

from topfpflanze import config, data, debug, util
from topfpflanze.app import parse_args


def test_data_dir_per_platform(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(sys, "platform", "win32")
    assert config.data_dir() == tmp_path / "roaming" / "topfpflanze"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert config.data_dir() == Path.home() / "Library" / "Application Support" / "topfpflanze"
    monkeypatch.setattr(sys, "platform", "linux")
    assert config.data_dir() == tmp_path / "xdg" / "topfpflanze"


def test_stage_progression():
    k = data.PLANT_TYPES["wiesenblume"]
    assert util.stage_name(k, 0) == "Samen"
    assert util.stage_name(k, k.bloom_at) == "Blühend"


def test_fmt_int_swiss():
    assert util.fmt_int(1234567) == "1'234'567"


def test_parse_args():
    args, rest = parse_args(["--debug", "--speed", "10", "--data-dir", "/x", "-platform", "offscreen"])
    assert args.debug and args.speed == 10 and args.data_dir == "/x"
    assert rest == ["-platform", "offscreen"]


@pytest.fixture
def plant(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(config, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setitem(debug.DEBUG, "on", True)
    monkeypatch.setitem(debug.DEBUG, "speed", 1.0)
    from PyQt6.QtWidgets import QApplication
    from topfpflanze.plant import Plant
    app = QApplication.instance() or QApplication([])
    p = Plant()
    p.show()
    app.processEvents()
    yield p
    p.timer.stop()


def test_plant_saves(plant, tmp_path):
    plant.save_state()
    assert (tmp_path / "state.json").exists()


def test_debug_growth_and_coins(plant):
    plant.ps["growth"] = 0
    debug._set_growth(plant, 1.0)
    assert plant.ps["growth"] >= plant.kind.bloom_at
    assert plant.state["coins"] > 0
    assert plant.state["current"] in plant.state["bloomed_species"]


def test_debug_speed_scales_time(plant):
    debug.DEBUG["speed"] = 60
    assert debug.apply_time(plant, 1.0) == 60.0
    debug.DEBUG["on"] = False
    assert debug.apply_time(plant, 1.0) == 1.0


def test_debug_menu_builds(plant):
    from PyQt6.QtWidgets import QMenu
    m = QMenu()
    debug.build_menu(plant, m)
    assert any(a.text() == "Debug" for a in m.actions())


def test_debug_visitor_and_helpers(plant):
    debug._unlock_helpers(plant)
    assert all(plant.helper_on(h) for h in data.HELPER_ORDER)
    plant.spawn_visitor("marienkaefer")
    assert plant.state["book"]["marienkaefer"]["count"] == 1


def test_helper_art_renders_all_plants(plant):
    plant.state["helpers"] = list(data.HELPER_ORDER)
    plant.state["helpers_off"] = []
    plant.ps["fert"] = {"key": "blaukorn", "left": 3600}
    for key in data.PLANT_ORDER:
        plant.select_plant(key)
        plant.ps["growth"] = plant.kind.bloom_at
        assert not plant.grab().isNull()


def test_achievements_are_claimed_manually(plant):
    plant.state["coins"] = 0
    debug._reset_periods(plant)
    debug._add_activity(plant, clicks=20)  # d_clicks: 10 Coins
    assert plant.state["coins"] == 0
    e = plant.ach_pending_entry("d_clicks")
    assert e and e["reward"] == 10
    assert plant.claim_achievement(e) == 10
    assert plant.state["coins"] == 10
    assert plant.ach_pending_entry("d_clicks") is None
    assert plant.claim_achievement(e) == 0  # nicht doppelt
    plant.check_achievements()  # nicht erneut vormerken
    assert plant.ach_pending_entry("d_clicks") is None


def test_claim_all(plant):
    plant.state["coins"] = 0
    debug._reset_periods(plant)
    debug._add_activity(plant, keys=2000, clicks=20)
    total = plant.ach_pending_total()
    assert total == 25
    assert plant.claim_achievements() == 25
    assert plant.state["coins"] == 25
    assert plant.claim_achievements() == 0


def test_expired_achievements_listed_and_claimable(plant):
    debug._reset_periods(plant)
    debug._add_activity(plant, keys=2000, clicks=20)
    assert plant.ach_expired() == []
    debug._next_period(plant)
    exp = plant.ach_expired()
    assert {e["key"] for e in exp} == {"d_keys", "d_clicks"}
    assert plant.ach_pending_entry("d_keys") is None  # nicht mehr in der Tageszeile
    plant.state["coins"] = 0
    plant.claim_achievement(exp[0])
    assert plant.state["coins"] == exp[0]["reward"]
    assert len(plant.ach_expired()) == 1


def test_old_pending_entries_are_migrated(plant):
    plant.state["ach_pending"] = [{"key": "d_keys", "name": "Fleissige Finger", "reward": 15}]
    plant.ensure_periods()
    e = plant.state["ach_pending"][0]
    assert e["period"] == "daily" and e["pid"] == plant.ach_pid("daily")


def test_achievement_window_layout_and_clicks(plant):
    debug._reset_periods(plant)
    debug._add_activity(plant, keys=2000, clicks=20)
    debug._next_period(plant)
    debug._add_activity(plant, clicks=20)
    win = plant.ach_win
    win.show()
    lay = win.layout()
    assert len(lay["old_rows"]) == 2 and win.height() == lay["height"]
    plant.state["coins"] = 0
    win.on_click(("row", "d_clicks"))
    assert plant.state["coins"] == 10
    old = lay["old_rows"][0][0]
    win.on_click(("old", id(old)))
    assert plant.state["coins"] == 10 + old["reward"]
    win.on_click("all")
    assert plant.ach_pending_total() == 0 and win.height() == win.layout()["height"]
    assert not win.grab().isNull()


@pytest.fixture
def scale_reset():
    from topfpflanze import scaling
    yield scaling
    scaling.set_scale(1.0, "plant")
    scaling.set_scale(1.0, "menu")


@pytest.mark.parametrize("value", [0.5, 1.5, 2.0])
def test_plant_scale_leaves_menus_alone(plant, scale_reset, value):
    from topfpflanze import config
    plant.bubble.show()
    menus = [plant.bubble, *plant.windows.values()]
    before = [(w.real_width(), w.real_height()) for w in menus]
    plant.set_ui_scale(value, "plant")
    assert plant.width() == config.WIN_W  # logische Grösse bleibt
    assert plant.real_width() == round(config.WIN_W * plant._k)
    assert plant._k <= value
    if value < 1.0:
        assert plant._k == value
    assert [(w.real_width(), w.real_height()) for w in menus] == before
    assert all(w._k == 1.0 for w in menus)
    for w in [plant, *menus]:
        assert not w.grab().isNull()
    assert plant.state["ui_scale"] == value
    plant.set_ui_scale(1.0, "plant")
    assert plant.real_width() == config.WIN_W


@pytest.mark.parametrize("value", [0.5, 1.5])
def test_menu_scale_leaves_plant_alone(plant, scale_reset, value, monkeypatch):
    from topfpflanze import config
    monkeypatch.setattr(scale_reset, "_screen_size", lambda: (4000, 4000))
    plant.bubble.show()
    size = (plant.real_width(), plant.real_height())
    plant.set_ui_scale(value, "menu")
    assert (plant.real_width(), plant.real_height()) == size and plant._k == 1.0
    for w in [plant.bubble, *plant.windows.values()]:
        assert w._k == value
        assert w.real_width() == round(w.width() * value)
        assert not w.grab().isNull()
    assert plant.state["menu_scale"] == value
    plant.set_ui_scale(1.0, "menu")
    assert plant.bubble.real_width() == config.BUBBLE_W


def test_menu_scale_is_limited_to_screen(plant, scale_reset, monkeypatch):
    monkeypatch.setattr(scale_reset, "_screen_size", lambda: (1920, 1080))
    plant.set_ui_scale(2.0, "menu")
    for w in [plant.bubble, *plant.windows.values()]:
        assert w.real_height() <= 1080 * 0.96 + 1 and w._k >= 1.0


def test_ui_scale_limits(scale_reset):
    assert scale_reset.set_scale(0.1, "plant") == 0.5
    assert scale_reset.set_scale(9, "menu") == 2.0


def test_mouse_position_is_scaled_back(plant, scale_reset):
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest
    plant.set_ui_scale(0.5, "plant")
    plant.set_ui_scale(0.5, "menu")
    seen = []
    plant.mousePressEvent = lambda e: seen.append(e.position())
    QTest.mouseClick(plant, Qt.MouseButton.LeftButton, pos=QPoint(50, 80))
    assert seen and abs(seen[0].x() - 100) < 1 and abs(seen[0].y() - 160) < 1  # echte Pixel → logische
    b = plant.bubble
    b.show()
    key, rect = next((k, r) for k, r in b.icon_rects() if k == "kaktus")
    pt = rect.center() * b._k
    QTest.mouseClick(b, Qt.MouseButton.LeftButton, pos=QPoint(int(pt.x()), int(pt.y())))
    assert plant.state["current"] == "kaktus"


def test_ui_scales_saved_and_restored(tmp_path, monkeypatch, scale_reset):
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(config, "STATE_FILE", tmp_path / "state.json")
    from PyQt6.QtWidgets import QApplication
    from topfpflanze.plant import Plant
    app = QApplication.instance() or QApplication([])  # Referenz behalten
    p = Plant()
    p.timer.stop()
    p.set_ui_scale(0.75, "plant")
    p.set_ui_scale(1.25, "menu")
    p.save_state()
    scale_reset.set_scale(1.0, "plant")
    scale_reset.set_scale(1.0, "menu")
    p2 = Plant()
    p2.timer.stop()
    assert scale_reset.get_scale("plant") == 0.75 and scale_reset.get_scale("menu") == 1.25
    assert app is not None


def test_scale_sliders(plant, scale_reset):
    from PyQt6.QtWidgets import QMenu, QPushButton, QSlider
    menu = QMenu()
    for kind, title in (("plant", "Pflanzengrösse"), ("menu", "Menügrösse")):
        box = plant.scale_slider_action(menu, kind, title).defaultWidget()
        slider = box.findChild(QSlider)
        assert (slider.minimum(), slider.maximum(), slider.value()) == (50, 200, 100)
        slider.setValue(150)
        assert scale_reset.get_scale(kind) == 1.5
        box.findChild(QPushButton).click()  # «100 %»
        assert scale_reset.get_scale(kind) == 1.0


def test_bubble_tooltips_say_what_the_icon_does(plant):
    b = plant.bubble
    assert b.testAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
    assert plant.testAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
    texts = {k: b.tooltip_text(k) for k in ("shop", "garden", "ach", "focus", "book", "kaktus")}
    assert texts["shop"].startswith("Dünger-Shop öffnen")
    assert texts["garden"].startswith("Gartenhaus öffnen")
    assert texts["ach"].startswith("Erfolge öffnen")
    assert texts["focus"].startswith("Fokus-Timer öffnen")
    assert texts["book"].startswith("Besucher-Sammelbuch öffnen")
    assert texts["kaktus"].startswith("Kaktus auswählen")
    plant.windows["shop"].show()
    assert b.tooltip_text("shop").startswith("Dünger-Shop schliessen")


def _help_event(win, pt):
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QHelpEvent
    p = QPoint(int(pt.x()), int(pt.y()))
    return QHelpEvent(QEvent.Type.ToolTip, p, win.mapToGlobal(p))


def test_bubble_tooltip_event_shows_text(plant, scale_reset):
    from topfpflanze import tooltip
    b = plant.bubble
    b.show()
    for menu_scale in (1.0, 0.5):
        plant.set_ui_scale(menu_scale, "menu")
        rect = dict(b.icon_rects())["shop"]
        assert b.event(_help_event(b, rect.center() * b._k))
        assert tooltip.current_text().startswith("Dünger-Shop")
        tooltip.hide_tip()
        assert tooltip.current_text() == ""


def test_tooltip_hides_on_leave_and_click(plant):
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QEvent, QPointF
    from topfpflanze import tooltip
    b = plant.bubble
    b.show()
    rect = dict(b.icon_rects())["shop"]
    b.event(_help_event(b, rect.center()))
    assert tooltip.current_text()
    b.event(QEvent(QEvent.Type.Leave))
    assert tooltip.current_text() == ""
    b.event(_help_event(b, rect.center()))
    other = dict(b.icon_rects())["kaktus"].center()
    move = QMouseEvent(QEvent.Type.MouseMove, other, QPointF(b.mapToGlobal(other.toPoint())),
                       Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    b.event(move)  # anderes Symbol → Tooltip verschwindet
    assert tooltip.current_text() == ""


def test_plant_and_menu_tooltips_use_custom_widget(plant):
    from topfpflanze import tooltip
    plant.update_tooltip()
    assert plant.event(_help_event(plant, QPointF(50, 100)))
    assert "Wiesenblume" in tooltip.current_text()
    tooltip.hide_tip()


def test_tooltip_follows_dark_theme(plant):
    from topfpflanze import tooltip
    plant.set_dark(True)
    tooltip.show_tip("Dünger-Shop öffnen\nCoins: 0", plant.mapToGlobal(QPointF(10, 10).toPoint()))
    img = tooltip._get().grab().toImage()
    px = img.pixelColor(img.width() // 2, 3)
    assert px.red() < 90 and px.green() < 90, "Tooltip muss im Dunkelmodus dunkel sein"
    plant.set_dark(False)
    img = tooltip._get().grab().toImage()
    assert img.pixelColor(img.width() // 2, 3).red() > 200
    tooltip.hide_tip()


def test_close_button_tooltip(plant):
    from topfpflanze import tooltip
    for win in (plant.shop, plant.garden, plant.ach_win, plant.focus_win, plant.book_win):
        win.show()
        assert win.event(_help_event(win, win.close_rect().center()))
        assert tooltip.current_text() == "Schliessen"
        tooltip.hide_tip()


def test_info_window_content_and_scroll(plant):
    from topfpflanze import info
    w = plant.info_win
    assert "info" in plant.windows and "info" in config.TOOL_ORDER
    for key, _name in info.TABS:
        w.tab, w.scroll = key, 0.0
        w.cache.clear()
        items, total = w.layout()
        assert items and total > 0
        assert not w.grab().isNull()
    # Werte stammen aus den Daten
    text = " ".join(str(b) for b in info.blocks("pfl"))
    for k in data.PLANT_TYPES.values():
        assert k.name in text and f"{k.growth_per_click:g}" in text
    text = " ".join(str(b) for b in info.blocks("shop"))
    for f in data.FERTILIZERS.values():
        assert f.name in text
    for h in data.HELPERS.values():
        assert h.name in text and h.desc in text
    # Reiter wechseln setzt Scroll zurück, Scroll ist begrenzt
    w.tab = "reg"
    assert w.max_scroll() > 0
    w.scroll = 1e9
    w.wheelEvent(type("E", (), {"angleDelta": lambda self: type("P", (), {"y": lambda s: 0})()})())
    assert w.scroll <= w.max_scroll()
    w.on_click(("tab", "bed"))
    assert w.tab == "bed" and w.scroll == 0.0
    plant.state["info_pos"] = None
    plant.save_state()
    assert plant.state["info_pos"] is not None
    assert plant.bubble.tooltip_text("info").startswith("Info öffnen")


def test_shiny_variants_defined_and_drawn(plant):
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtCore import QPointF
    from topfpflanze import drawing
    assert set(data.VARIANTS) == set(data.VISITOR_ORDER)
    for key in data.VISITOR_ORDER:
        imgs = []
        for shiny in (False, True):
            img = QImage(60, 60, QImage.Format.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            drawing.draw_visitor(p, key, QPointF(30, 30), 2.0, 1.0, shiny=shiny)
            p.end()
            imgs.append(img)
        assert imgs[0] != imgs[1], f"Variante von {key} sieht aus wie das Original"


def test_shiny_spawn_counts_and_reward(plant):
    plant.state["coins"] = 0
    plant.spawn_visitor("marienkaefer", shiny=True)
    e = plant.state["book"]["marienkaefer"]
    assert e["count"] == 1 and e["shiny"] == 1 and "shiny_first" in e
    assert plant.visitor["shiny"] is True
    plant.visitor_pos = lambda: QPointF(50, 50)
    assert plant.greet_visitor(QPointF(50, 50))
    assert plant.state["coins"] == data.SHINY_GREET_COINS
    plant.spawn_visitor("marienkaefer", shiny=False)
    plant.greet_visitor(QPointF(50, 50))
    assert plant.state["coins"] == data.SHINY_GREET_COINS + data.VISIT_GREET_COINS
    assert plant.state["book"]["marienkaefer"]["count"] == 2


def test_shiny_chance_by_rarity(plant, monkeypatch):
    import random
    monkeypatch.setattr(random, "random", lambda: 0.0)
    plant.spawn_visitor("biene")
    assert plant.visitor["shiny"] is True
    monkeypatch.setattr(random, "random", lambda: 0.999)
    plant.spawn_visitor("biene")
    assert plant.visitor["shiny"] is False


def test_mastery_tiers_rewards_and_bonus(plant):
    plant.state["coins"] = 0
    plant.state["ach_pending"] = []
    plant.state["book"] = {"marienkaefer": {"count": 9, "first": 0}}
    plant.check_mastery()
    assert plant.mastery_tier("marienkaefer") == 0 and not plant.state["ach_pending"]
    plant.state["book"]["marienkaefer"]["count"] = 10
    plant.check_mastery()
    assert plant.mastery_tier("marienkaefer") == 1
    e = plant.state["ach_pending"][0]
    assert e["reward"] == data.MASTERY_COINS[0] and e["period"] == "mastery"
    plant.check_mastery()  # nicht doppelt
    assert len(plant.state["ach_pending"]) == 1
    plant.state["book"]["marienkaefer"]["count"] = 200  # überspringt Stufen: alle fehlenden werden vorgemerkt
    plant.check_mastery()
    assert [x["reward"] for x in plant.state["ach_pending"]] == list(data.MASTERY_COINS)
    assert plant.top_count() == 1
    assert plant.mastery_tier("marienkaefer") == 3
    # Rotkehlchen (sehr selten) zahlt mehr
    plant.state["book"]["rotkehlchen"] = {"count": 10, "first": 0}
    plant.check_mastery()
    assert plant.state["ach_pending"][-1]["reward"] == round(data.MASTERY_COINS[0] * data.RARITY_MULT["sehr selten"])
    # Gold-Bonus wirkt auf das Wachstum
    base = plant.growth_mult()
    plant.state["book"]["kohlweissling"] = {"count": 200, "first": 0}
    assert abs(plant.growth_mult() / base - (1 + data.MASTERY_TOP_BONUS * 2) / (1 + data.MASTERY_TOP_BONUS)) < 1e-9


def test_mastery_rewards_are_claimable_in_list(plant):
    plant.state["ach_pending"] = []
    plant.state["coins"] = 0
    debug._add_visits(plant, 10)
    exp = plant.ach_expired()
    assert len(exp) == len(data.VISITOR_ORDER) and all(e["period"] == "mastery" for e in exp)
    win = plant.ach_win
    win.show()
    lay = win.layout()
    assert lay["old_rows"] and win.old_label(exp[0]) == "Meisterschaft (Besucher)"
    entry = exp[0]
    win.on_click(("old", id(entry)))
    assert plant.state["coins"] == entry["reward"]
    win.on_click("all")
    assert not plant.state["ach_pending"]


def test_book_window_draws_tiers_and_star(plant):
    plant.state["book"] = {"marienkaefer": {"count": 60, "first": 0, "shiny": 2},
                           "biene": {"count": 3, "first": 0}}
    win = plant.book_win
    win.show()
    for hover in (None, "marienkaefer", "biene", "libelle"):
        win.hover = hover
        assert not win.grab().isNull()


def test_version_tab_and_changelog(plant):
    from topfpflanze import __version__, info
    from topfpflanze.changelog import CHANGELOG
    assert ("ver", "Version") in info.TABS
    text = " ".join(str(b) for b in info.blocks("ver", plant))
    assert __version__ in text and "Release Notes" in text and "Spielstand" in text
    for version, _date, items in CHANGELOG:
        assert version in text and items
    # Die neueste veröffentlichte Version im Changelog entspricht der Programmversion
    released = [v for v, d, _i in CHANGELOG if d]
    assert released[0] == __version__
    w = plant.info_win
    w.tab = "ver"
    w.cache.clear()
    assert w.layout()[1] > 0 and not w.grab().isNull()
    import re, pathlib
    pyproject = (pathlib.Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(rf'^version = "{re.escape(__version__)}"$', pyproject, re.M)


def _aura_alpha(plant, t):
    plant.t = t
    img = plant.grab().toImage()
    return img.pixelColor(60, 190).alpha()  # seitlich der Pflanze, innerhalb der Aura


def test_prestige_aura_only_when_ready_and_breathes(plant):
    from topfpflanze import config
    plant.select_plant("wiesenblume")
    plant.ps["growth"] = plant.kind.bloom_at * 0.9
    assert not plant.prestige_ready()
    assert _aura_alpha(plant, 0.0) == 0
    plant.ps["growth"] = plant.kind.bloom_at
    assert plant.prestige_ready()
    period = config.PRESTIGE_AURA_PERIOD
    dark = _aura_alpha(plant, 0.0)               # Atemzug: dunkelster Punkt
    bright = _aura_alpha(plant, period / 2)      # hellster Punkt
    assert 0 < dark < bright
    assert bright <= config.PRESTIGE_AURA_ALPHA[1]  # bleibt dezent
    assert abs(_aura_alpha(plant, period) - dark) <= 1  # periodisch
    plant.ps["growth"] = plant.kind.bloom_at * 3   # auch weit nach der Blüte
    assert plant.prestige_ready()


def test_prestige_aura_not_in_garden_snapshot(plant):
    plant.select_plant("wiesenblume")
    plant.ps["growth"] = plant.kind.bloom_at
    plant.t = 1.5
    entry = {"key": "wiesenblume", "growth": plant.kind.bloom_at, "seed": 1, "color": None, "created": 0}
    pix = plant.snapshot(entry, scale=1)
    img = pix.toImage() if hasattr(pix, "toImage") else pix
    assert img.pixelColor(int(60), 190).alpha() == 0


def test_bubble_seed_icon_only_when_ready_and_clickable(plant, monkeypatch):
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    b = plant.bubble
    b.show()
    plant.select_plant("wiesenblume")
    plant.ps["growth"] = plant.kind.bloom_at * 0.5
    assert b.seed_rect() is None and not b.over_seed(QPointF(200, 30))
    plant.ps["growth"] = plant.kind.bloom_at
    r = b.seed_rect()
    assert r is not None and b.over_seed(r.center())
    called = []
    monkeypatch.setattr(plant, "reset_plant", lambda: called.append(1))
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, r.center(), QPointF(b.mapToGlobal(r.center().toPoint())),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    b.mousePressEvent(ev)
    assert called == [1]
    assert "einlagern & neu aussäen" in b.tooltip_at(r.center())
    assert not b.grab().isNull()
    # Klick daneben löst nichts aus
    other = QPointF(20, 20)
    ev2 = QMouseEvent(QEvent.Type.MouseButtonPress, other, QPointF(b.mapToGlobal(other.toPoint())),
                      Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    b.mousePressEvent(ev2)
    assert called == [1]


# ---------------------------------------------------------------- Töpfe und Neuaussaat

def test_skins_are_random_priced_and_serializable():
    import json
    import random
    from topfpflanze import pots
    seen = set()
    for i in range(60):
        cheap, premium = pots.new_skin("cheap", random.Random(i)), pots.new_skin("premium", random.Random(i))
        lo, hi, step = pots.CHEAP_PRICE
        assert lo <= cheap["price"] <= hi and cheap["price"] % step == 0 and cheap["tier"] == "cheap"
        lo, hi, step = pots.PREMIUM_PRICE
        assert lo <= premium["price"] <= hi and premium["price"] % step == 0 and premium["tier"] == "premium"
        assert premium["sparkle"] and not cheap["sparkle"]
        assert cheap["price"] < premium["price"]
        json.dumps([cheap, premium])
        seen.add(cheap["name"])
    assert len(seen) > 15  # viel Abwechslung
    a, b = pots.new_offer(), pots.new_offer()
    assert a["cheap"]["id"] != b["cheap"]["id"]


def test_skinned_pot_differs_from_original_for_every_pot_shape(plant):
    from topfpflanze import pots
    for key in data.PLANT_ORDER:
        plant.select_plant(key)
        skin = pots.new_skin("premium")
        orig = pots.pot_image(plant, None)
        img = pots.pot_image(plant, skin)
        assert img is pots.pot_image(plant, skin)          # zwischengespeichert
        assert img.size() == orig.size() and img != orig
        box = pots.pot_box(plant, skin)
        assert box.width() > 40 and box.height() > 10
        plant.ps["pot_skin"] = skin
        assert not plant.grab().isNull()


def test_offer_stays_until_sowing_and_is_rerolled_after(plant):
    plant.ps["growth"] = plant.kind.bloom_at
    first = plant.pot_offer()
    assert plant.pot_offer() is first
    ids = [c["id"] for c in plant.sow_choices()]
    assert ids == ["orig", "cheap", "premium"] and plant.sow_choices()[0]["price"] == 0
    assert plant.confirm_sow("orig")
    assert plant.pot_offer()["cheap"]["id"] != first["cheap"]["id"]


def test_sow_free_original_archives_and_gives_prestige(plant):
    key = plant.state["current"]
    plant.ps["growth"] = plant.kind.bloom_at
    plant.ps["pot_skin"] = None
    n = len(plant.state["garden"])
    coins = plant.state["coins"] = 50
    assert plant.confirm_sow("orig")
    assert len(plant.state["garden"]) == n + 1 and plant.state["garden"][-1]["key"] == key
    assert plant.state["prestige"][key] == 1
    assert plant.state["coins"] == coins
    assert plant.ps["growth"] == 0 and plant.ps["pot_skin"] is None


def test_sow_paid_pot_costs_gold_and_is_kept_and_archived(plant):
    plant.ps["growth"] = plant.kind.bloom_at
    choice = plant.sow_choices()[1]
    plant.state["coins"] = choice["price"] + 7
    assert plant.confirm_sow("cheap")
    assert plant.state["coins"] == 7
    assert plant.ps["pot_skin"]["id"] == choice["skin"]["id"]
    # nächste Aussaat: alter Topf wandert mit ins Gartenhaus
    plant.ps["growth"] = plant.kind.bloom_at * 0.3
    assert plant.confirm_sow("orig")
    archived = plant.state["garden"][-1]
    assert archived["pot_skin"]["id"] == choice["skin"]["id"] and archived["prestige"] is None
    assert plant.ps["pot_skin"] is None
    # nicht ausgewachsen: kein Prestige
    assert plant.state.get("prestige", {}).get(plant.state["current"], 0) == 1


def test_sow_refused_without_enough_gold(plant):
    plant.ps["growth"] = plant.kind.bloom_at
    price = plant.sow_choices()[2]["price"]
    plant.state["coins"] = price - 1
    n = len(plant.state["garden"])
    assert plant.confirm_sow("premium") is False
    assert len(plant.state["garden"]) == n and plant.state["coins"] == price - 1
    assert plant.ps["growth"] >= plant.kind.bloom_at


def test_reset_plant_opens_custom_dialog_instead_of_system_box(plant, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    called = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: called.append(1))
    plant.reset_plant()
    assert plant.sow_win.isVisible() and not called
    assert plant.sow_win.choice == "orig"
    plant.sow_win.hide()


def test_sow_dialog_flow(plant):
    win = plant.sow_win
    plant.ps["growth"] = plant.kind.bloom_at
    plant.state["coins"] = 100
    plant.reset_plant()
    lay = win.layout()
    assert win.height() == lay["height"] and len(lay["cards"]) == 3
    assert not win.grab().isNull()
    # zu teuer: Klick auf den edlen Topf ändert nichts (Panel ruft on_click nur für anklickbare Elemente)
    items = {k: c for k, _r, c in win.items()}
    assert items[("pot", "orig")] and not items[("pot", "premium")]
    assert items["ok"]
    win.on_click(("pot", "cheap"))
    assert win.choice == "cheap"
    cheap_price = win.selected()["price"]
    plant.state["coins"] = cheap_price
    win.on_click("ok")
    assert not win.isVisible() and plant.state["coins"] == 0 and plant.ps["pot_skin"] is not None
    # Abbrechen ändert nichts
    plant.ps["growth"] = plant.kind.bloom_at
    n = len(plant.state["garden"])
    plant.reset_plant()
    win.on_click("cancel")
    assert not win.isVisible() and len(plant.state["garden"]) == n


def test_sow_dialog_unaffordable_ok_is_blocked(plant):
    win = plant.sow_win
    plant.ps["growth"] = plant.kind.bloom_at
    plant.state["coins"] = 0
    plant.reset_plant()
    win.choice = "premium"
    assert not dict((k, c) for k, _r, c in win.items())["ok"]
    n = len(plant.state["garden"])
    win.on_click("ok")
    assert len(plant.state["garden"]) == n
    assert win.isVisible()
    win.hide()


def test_sow_dialog_keys_and_not_ready_text(plant):
    from PyQt6.QtGui import QKeyEvent
    win = plant.sow_win
    plant.ps["growth"] = plant.kind.bloom_at * 0.2
    plant.reset_plant()
    title, text, ready = win.info_blocks()
    assert not ready and "ohne Prestige" in text
    n = len(plant.state["garden"])
    win.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert len(plant.state["garden"]) == n + 1 and not win.isVisible()
    plant.reset_plant()
    win.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not win.isVisible()


def test_garden_snapshot_shows_archived_pot(plant):
    from topfpflanze import pots
    entry = {"key": "wiesenblume", "growth": 400, "seed": 3, "color": None, "created": 0, "pot_skin": None}
    plain = plant.snapshot(entry, scale=1)
    entry["pot_skin"] = pots.new_skin("premium")
    skinned = plant.snapshot(entry, scale=1)
    assert plain != skinned


def test_old_plant_states_get_default_pot_skin(plant):
    del plant.ps["pot_skin"]
    plant.activate(plant.state["current"])
    assert plant.ps["pot_skin"] is None
