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
    p.state["diary_spell"] = "off"   # die Rechtschreibprüfung wird nur in den eigenen Tests geladen
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
    plant.ps["helpers"] = list(data.HELPER_ORDER)
    plant.ps["helpers_off"] = []
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
    assert total == 45                      # 15 + 10 täglich, 20 für «Tipper» (1'000 Tasten insgesamt)
    assert plant.claim_achievements() == 45
    assert plant.state["coins"] == 45
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


def test_new_visitor_marks_book_icon_until_seen(plant):
    plant.state["book"] = {}
    plant.state["book_new"] = []
    plant.spawn_visitor("marienkaefer", shiny=False)
    assert plant.state["book_new"] == ["marienkaefer"]
    plant.spawn_visitor("marienkaefer", shiny=False)          # schon bekannt: keine zweite Markierung
    assert plant.state["book_new"] == ["marienkaefer"]
    plant.spawn_visitor("marienkaefer", shiny=True)           # neue Farbvariante: Eintrag bleibt einmalig
    assert plant.state["book_new"] == ["marienkaefer"]
    plant.spawn_visitor("biene", shiny=False)
    assert plant.state["book_new"] == ["marienkaefer", "biene"]
    assert not plant.bubble.grab().isNull() and not plant.book_win.grab().isNull()
    assert plant.clear_book_new("biene") and not plant.clear_book_new("biene")
    assert plant.state["book_new"] == ["marienkaefer"]


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




def test_old_plant_states_get_default_pot_skin(plant):
    del plant.ps["pot_skin"]
    plant.activate(plant.state["current"])
    assert plant.ps["pot_skin"] is None


def test_opening_and_confirming_sow_dialog_moves_no_other_window(plant):
    wins = [plant, plant.bubble, plant.shop, plant.garden, plant.ach_win, plant.focus_win, plant.book_win,
            plant.info_win]
    spots = [(5, 5), (3000, 2000), (-400, 300), (2500, -100), (700, 590), (100, 4000), (-50, -50), (1900, 1200)]
    for w, (x, y) in zip(wins, spots):   # bewusst auch ausserhalb des (Test-)Bildschirms
        w.move(x, y)
    before = [(w.x(), w.y()) for w in wins]
    plant.ps["growth"] = plant.kind.bloom_at
    plant.reset_plant()
    assert [(w.x(), w.y()) for w in wins] == before
    plant.sow_win.on_click("ok")  # Originaltopf, gratis
    assert not plant.sow_win.isVisible()
    assert [(w.x(), w.y()) for w in wins] == before


def test_clamp_to_screen_moves_only_the_given_window(plant):
    plant.bubble.move(50, 50)
    plant.shop.move(9000, 9000)
    plant.clamp_to_screen(plant.bubble)
    assert (plant.bubble.x(), plant.bubble.y()) == (50, 50)
    assert (plant.shop.x(), plant.shop.y()) == (9000, 9000)
    plant.clamp_to_screen(plant.shop)
    assert plant.shop.x() < 9000 and plant.shop.y() < 9000


KEPT = {  # was du ausgesucht hast: Topfform -> Anzahl Designs (günstig, edel)
    "terrakotta": (5, 4), "beton": (3, 5), "keramik": (4, 4), "zink": (1, 4), "schale": (1, 1),
}


def test_catalog_matches_the_chosen_pots():
    import json
    from topfpflanze import pots
    assert sum(len(v) for v in pots.BY_POT.values()) == 32 == len(pots.DESIGNS)
    for pot, (cheap, edel) in KEPT.items():
        assert len(pots.designs_for(pot, "cheap")) == cheap, pot
        assert len(pots.designs_for(pot, "premium")) == edel, pot
    ids = list(pots.DESIGNS)
    assert len(set(ids)) == len(ids)
    for d in pots.DESIGNS.values():
        assert d["name"] and d["pot"] in KEPT and d["id"].startswith(d["pot"] + "/")
        json.dumps(d["id"])
    lo_c, hi_c = pots.price_range("cheap")
    lo_p, hi_p = pots.price_range("premium")
    assert hi_c < lo_p and lo_c >= 20  # günstig bleibt immer unter edel
    assert {d["name"] for d in pots.designs_for("schale")} == {"Weisse Keramik", "Gold"}


def test_catalog_names_of_kept_designs():
    from topfpflanze import pots
    names = {pot: {d["name"] for d in pots.designs_for(pot)} for pot in pots.BY_POT}
    assert {"Sand, breites Band", "Salbei, grosse Rauten", "Kintsugi Weiss", "Tauchglasur Salbei"} <= names["terrakotta"]
    assert names["beton"] == {"Lehm, breite Streifen", "Schwarz, Kupferband", "Marmor weiss", "Sprenkel Sand",
                              "Schwarz, Goldrand", "Kintsugi Stein", "Terrazzo hell", "Waldgrün, Goldlinien"}
    assert names["keramik"] == {"Creme, Salbeiband", "Nachtblau, Goldlinien", "Tauchglasur Rosé", "Sprenkel Weiss",
                                "Kintsugi Nachtblau", "Weiss, Goldring", "Terrazzo Rosé", "Weiss, Gold-Zickzack"}
    assert names["zink"] == {"Kupfer gehämmert", "Messing gebürstet", "Sprenkel Grau", "Gold getaucht",
                             "Gold gehämmert"}


def test_every_design_renders_and_differs_from_original(plant):
    from topfpflanze import pots
    for key in data.PLANT_ORDER:
        plant.select_plant(key)
        orig = pots.pot_image(plant, None)
        for d in pots.designs_for(plant.kind.pot):
            img = pots.pot_image(plant, d["id"])
            assert img is pots.pot_image(plant, d["id"])  # zwischengespeichert
            assert img.size() == orig.size() and img != orig, d["id"]
            plant.ps["pot_skin"] = d["id"]
            assert not plant.grab().isNull()


def test_saucer_stays_plain_on_terracotta_and_concrete(plant):
    from PyQt6.QtGui import QImage
    """Muster nur auf dem Topf: im Bereich des Untersetzers sehen alle Designs gleich aus wie das Einfarbige."""
    from topfpflanze import pots
    for key, pot_id in (("wiesenblume", "terrakotta/salbei-rauten"), ("wiesenblume", "terrakotta/salbei-punkte"),
                        ("kaktus", "beton/terrazzo-hell")):
        plant.select_plant(key)
        d = pots.design(pot_id)
        plain = pots._recolor(pots._base_image(plant), d["ramp"])[0].convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied)
        deco = pots.pot_image(plant, pot_id)
        limit = int(pots.DECOR_BOTTOM[plant.kind.pot]) + 2  # eine Zeile Abstand zur geglätteten Schnittkante
        diff = 0
        for y in range(limit, plain.height()):  # Untersetzer
            for x in range(0, plain.width(), 2):
                a, b = plain.pixelColor(x, y), deco.pixelColor(x, y)
                diff += abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())
        assert diff == 0, f"{pot_id}: Muster auf dem Untersetzer"


def test_offer_is_per_plant_from_its_own_catalog_and_rerolled_after_sowing(plant):
    from topfpflanze import pots
    plant.select_plant("wiesenblume")
    plant.ps["growth"] = plant.kind.bloom_at
    first = plant.pot_offer()
    assert plant.pot_offer() is first
    assert pots.design(first["cheap"])["pot"] == "terrakotta" and pots.design(first["cheap"])["tier"] == "cheap"
    assert pots.design(first["premium"])["tier"] == "premium"
    ids = [c["id"] for c in plant.sow_choices()]
    assert ids == ["orig", "cheap", "premium"] and plant.sow_choices()[0]["price"] == 0
    plant.select_plant("bonsai")
    offer = plant.pot_offer()
    assert {offer["cheap"], offer["premium"]} == {"schale/weisse-keramik", "schale/gold"}
    plant.select_plant("wiesenblume")
    assert plant.pot_offer() is first  # Angebot der Wiesenblume bleibt erhalten
    assert plant.confirm_sow("orig")
    assert "wiesenblume" not in plant.state["pot_offer"] or plant.pot_offer() is not first


def test_offer_avoids_the_pot_currently_in_use(plant):
    from topfpflanze import pots
    plant.select_plant("wiesenblume")
    for _ in range(40):
        current = pots.designs_for("terrakotta", "cheap")[0]["id"]
        offer = pots.new_offer("terrakotta", exclude=current)
        assert offer["cheap"] != current
    # Sonnenblume hat nur ein günstiges Design: das wird trotzdem angeboten
    assert pots.new_offer("zink", exclude="zink/sprenkel-grau")["cheap"] == "zink/sprenkel-grau"


def test_old_random_pot_formats_are_ignored_gracefully(plant):
    from topfpflanze import pots
    plant.state["pot_offer"] = {"cheap": {"id": "c-old"}, "premium": {"id": "p-old"}}  # alte Form
    offer = plant.pot_offer()
    assert pots.design(offer["cheap"]) and pots.design(offer["premium"])
    plant.ps["pot_skin"] = {"id": "c-deadbeef", "ramp": ["#000000"]}  # alter Zufallstopf: wird zum Original
    assert pots.design(plant.ps["pot_skin"]) is None
    assert not plant.grab().isNull()


def test_sow_paid_pot_costs_gold_and_is_kept_and_archived(plant):
    plant.ps["growth"] = plant.kind.bloom_at
    choice = plant.sow_choices()[1]
    plant.state["coins"] = choice["price"] + 7
    assert plant.confirm_sow("cheap")
    assert plant.state["coins"] == 7
    assert plant.ps["pot_skin"] == choice["skin"]
    # nächste Aussaat: der alte Topf wandert mit ins Gartenhaus
    plant.ps["growth"] = plant.kind.bloom_at * 0.3
    assert plant.confirm_sow("orig")
    archived = plant.state["garden"][-1]
    assert archived["pot_skin"] == choice["skin"] and archived["prestige"] is None
    assert plant.ps["pot_skin"] is None
    assert plant.state.get("prestige", {}).get(plant.state["current"], 0) == 1


def test_garden_snapshot_shows_archived_pot(plant):
    entry = {"key": "wiesenblume", "growth": 400, "seed": 3, "color": None, "created": 0, "pot_skin": None}
    plain = plant.snapshot(entry, scale=1)
    entry["pot_skin"] = "terrakotta/kintsugi-schwarz"
    assert plain != plant.snapshot(entry, scale=1)


# ---------------------------------------------------------------- Fokusmodus

def _open_all_menu_windows(plant):
    plant.bubble.show()
    wins = [plant.shop, plant.garden, plant.ach_win, plant.book_win, plant.info_win, plant.focus_win]
    for w in wins:
        w.show()
    return [plant.bubble, *wins]


def test_focus_mode_default_on_and_persisted(plant):
    assert plant.state["focus_mode"] is True
    plant.focus_win.on_click("mode")
    assert plant.state["focus_mode"] is False
    plant.save_state()
    import json
    assert json.load(open(config.STATE_FILE, encoding="utf-8"))["focus_mode"] is False


def test_focus_start_hides_menus_and_shrinks_timer_then_restores_them(plant):
    shown = _open_all_menu_windows(plant)
    plant.shop.hide()                      # war vorher zu: darf danach nicht erscheinen
    plant.garden.hide()
    before = {id(w): (w.x(), w.y()) for w in shown}
    plant.start_focus(25)
    assert plant.focus_mode_active
    for w in (plant.bubble, plant.ach_win, plant.book_win, plant.info_win):
        assert not w.isVisible()
    assert plant.isVisible()                              # die Pflanze bleibt
    assert plant.focus_win.isVisible() and plant.focus_win.compact
    assert plant.focus_win.real_width() == plant.focus_win.COMPACT
    # Ende: die vorher sichtbaren Fenster kommen zurück, die vorher geschlossenen bleiben zu
    plant.focus["end"] = 0.0
    plant.run_focus()
    assert not plant.focus_mode_active and plant.focus is None
    for w in (plant.bubble, plant.ach_win, plant.book_win, plant.info_win, plant.focus_win):
        assert w.isVisible()
    assert not plant.shop.isVisible() and not plant.garden.isVisible()
    assert not plant.focus_win.compact and plant.focus_win.real_width() == plant.focus_win.W
    for w in (plant.bubble, plant.ach_win, plant.book_win, plant.info_win, plant.focus_win):
        assert (w.x(), w.y()) == before[id(w)]  # nichts hat sich verschoben


def test_focus_has_ten_minute_preset_and_compact_abort_x(plant):
    from PyQt6.QtCore import QPointF, QEvent, Qt
    from PyQt6.QtGui import QMouseEvent
    from topfpflanze.data import FOCUS_PRESETS
    assert FOCUS_PRESETS[0] == 10 and plant.state["focus_minutes"] == 25
    assert [k for k, _r in plant.focus_win.preset_rects()][0] == "p10"
    plant.focus_win.show()
    plant.focus_win.on_click("p10")
    assert plant.state["focus_minutes"] == 10
    plant.start_focus(10)
    w = plant.focus_win
    assert w.compact and not w.grab().isNull()
    assert "abbrechen" in w.tooltip_at(w.abort_rect().center())
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(w.abort_rect().center()), w.mapToGlobal(QPointF(w.abort_rect().center())),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    w.mousePressEvent(ev)
    assert plant.focus is None and not w.compact


def test_focus_abort_restores_windows_too(plant):
    plant.bubble.show()
    plant.info_win.show()
    plant.focus_win.show()
    plant.start_focus(25)
    assert not plant.bubble.isVisible() and not plant.info_win.isVisible()
    plant.abort_focus()
    assert plant.bubble.isVisible() and plant.info_win.isVisible() and plant.focus_win.isVisible()
    assert not plant.focus_win.compact and plant.focus is None


def test_focus_started_without_open_timer_window_hides_it_again_afterwards(plant):
    plant.bubble.show()
    plant.focus_win.hide()
    plant.start_focus(25)
    assert plant.focus_win.isVisible() and plant.focus_win.compact   # die Zeit muss sichtbar sein
    plant.abort_focus()
    assert not plant.focus_win.isVisible() and plant.bubble.isVisible()


def test_focus_mode_off_leaves_windows_alone(plant):
    plant.state["focus_mode"] = False
    shown = _open_all_menu_windows(plant)
    plant.start_focus(25)
    assert not plant.focus_mode_active
    assert all(w.isVisible() for w in shown) and not plant.focus_win.compact
    plant.abort_focus()
    assert all(w.isVisible() for w in shown)


def test_focus_mode_switch_is_locked_while_running(plant):
    plant.focus_win.show()
    items = {k: c for k, _r, c in plant.focus_win.items()}
    assert items["mode"] and items["start"]
    plant.start_focus(25)
    assert [k for k, _r, _c in plant.focus_win.items()] == ["abort"]   # kompakt: nur das X ist anklickbar
    plant.abort_focus()
    plant.state["focus_mode"] = False
    plant.start_focus(25)                            # ohne Fokusmodus läuft das normale Fenster weiter
    items = {k: c for k, _r, c in plant.focus_win.items()}
    assert not items["mode"] and not items["p25"]
    plant.abort_focus()


def test_compact_timer_window_is_transparent_with_ring_and_time(plant):
    plant.focus_win.show()
    plant.start_focus(25)
    win = plant.focus_win
    img = win.grab().toImage()
    assert img.pixelColor(2, 2).alpha() == 0          # Ecken durchsichtig: kein Fensterhintergrund
    assert img.pixelColor(img.width() - 3, img.height() - 3).alpha() == 0
    cx = img.width() // 2
    ring = [img.pixelColor(cx, y).alpha() for y in range(0, img.height() // 2)]
    assert max(ring) > 100                            # oben am Ring ist etwas zu sehen
    plant.abort_focus()


def test_compact_window_saved_position_is_the_normal_windows(plant):
    win = plant.focus_win
    win.move(300, 200)
    win.show()
    normal = (win.x(), win.y())
    plant.start_focus(25)
    assert win.compact and win.saved_pos() == normal   # Mitte bleibt gleich: gleiche Top-left wie vorher
    assert (win.x(), win.y()) != normal
    plant.abort_focus()
    assert (win.x(), win.y()) == normal


def test_focus_tooltip_and_right_click_menu_entry(plant):
    from topfpflanze import tooltip
    plant.focus_win.show()
    plant.start_focus(25)
    assert "Fokus läuft" in plant.focus_win.tooltip_at(QPointF(50, 50))
    plant.abort_focus()
    assert "Fokusmodus" in plant.focus_win.tooltip_at(plant.focus_win.mode_rect().center())
    tooltip.hide_tip()


# ---------------------------------------------------------------- Ton

class _FakeEffect:
    def __init__(self):
        self.plays, self.volume = 0, None

    def play(self):
        self.plays += 1

    def setVolume(self, v):
        self.volume = v


@pytest.fixture
def fake_sound(plant):
    plant.sound.effects = {"giessen": _FakeEffect(), "gong": _FakeEffect()}
    plant.sound.available = True
    plant.sound.last.clear()
    plant.set_volume(60)              # die Tests brauchen hörbaren Ton (Standard ist stumm)
    return plant.sound


def test_synthesized_sounds_are_sane():
    import math
    import struct
    from topfpflanze import sound
    for name, (lo, hi) in (("giessen", (0.4, 0.8)), ("gong", (3.0, 4.2))):
        raw = sound.pcm(name)
        n = len(raw) // 2
        samples = struct.unpack(f"<{n}h", raw)
        assert lo < n / sound.RATE < hi
        peak = max(abs(s) for s in samples) / 32767
        assert 0.6 < peak <= 0.95, "nicht zu leise, nicht übersteuert"
        assert abs(sum(samples) / n) / 32767 < 0.02, "kein Gleichspannungsanteil"
        assert abs(samples[-1]) < 300, "endet sanft (kein Knacken)"
        assert all(math.isfinite(s) for s in samples)
    g = struct.unpack(f"<{len(sound.pcm('gong')) // 2}h", sound.pcm("gong"))
    sec = sound.RATE

    def rms(a):
        return math.sqrt(sum(x * x for x in a) / len(a))
    assert rms(g[sec:2 * sec]) > rms(g[3 * sec:]) * 2, "Gong klingt aus"


def test_sound_files_are_valid_wav(tmp_path, monkeypatch):
    import wave
    from topfpflanze import sound
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    paths = sound.ensure_files()
    assert set(paths) == {"giessen", "gong"}
    for path in paths.values():
        with wave.open(str(path)) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, sound.RATE)
            assert w.getnframes() > 1000
    assert sound.ensure_files() == paths  # zweiter Aufruf erzeugt nichts neu


def test_volume_mapping():
    from topfpflanze import sound
    assert sound.effective_volume(0, "gong") == 0
    assert sound.effective_volume(100, "gong") == sound.GAINS["gong"]
    vals = [sound.effective_volume(v, "giessen") for v in range(0, 101, 10)]
    assert vals == sorted(vals) and vals[-1] <= 1.0
    assert sound.effective_volume(150, "gong") == sound.GAINS["gong"]    # begrenzt
    assert sound.effective_volume(-5, "gong") == 0


def test_default_volume_is_saved_and_restored(plant, tmp_path, monkeypatch):
    from topfpflanze import sound
    assert plant.state["volume"] == sound.DEFAULT_VOLUME == plant.sound.volume
    plant.set_volume(35)
    assert plant.state["volume"] == 35 and plant.sound.volume == 35
    import json
    assert json.load(open(config.STATE_FILE, encoding="utf-8"))["volume"] == 35
    plant.set_volume(250)
    assert plant.state["volume"] == 100
    plant.set_volume(-3)
    assert plant.state["volume"] == 0


def test_volume_applies_to_every_effect(fake_sound):
    from topfpflanze import sound
    fake_sound.set_volume(100)
    assert fake_sound.effects["gong"].volume == sound.GAINS["gong"]
    fake_sound.set_volume(0)
    assert all(e.volume == 0 for e in fake_sound.effects.values())


def test_watering_click_plays_pour_sound_only_when_watering(plant, fake_sound):
    plant.select_plant("wiesenblume")
    plant.ps["water"] = 40
    plant.water_click(QPointF(100, 150))
    assert fake_sound.effects["giessen"].plays == 1
    fake_sound.last.clear()
    plant.ps["water"] = 100                       # voll: nur Wachstum, kein Giessen, kein Ton
    plant.water_click(QPointF(100, 150))
    assert fake_sound.effects["giessen"].plays == 1
    fake_sound.last.clear()
    plant.ps["water"] = 30
    plant.set_volume(0)                           # stumm
    plant.water_click(QPointF(100, 150))
    assert fake_sound.effects["giessen"].plays == 1


def test_fast_clicking_is_rate_limited(fake_sound):
    assert fake_sound.play("giessen") is True
    assert fake_sound.play("giessen") is False     # sofort danach: kein Rattern
    assert fake_sound.effects["giessen"].plays == 1
    fake_sound.last["giessen"] -= 1.0
    assert fake_sound.play("giessen") is True


def test_gong_at_end_of_focus_but_not_on_abort(plant, fake_sound):
    plant.start_focus(25)
    plant.abort_focus()
    assert fake_sound.effects["gong"].plays == 0
    plant.start_focus(25)
    plant.focus["end"] = 0.0
    plant.run_focus()
    assert fake_sound.effects["gong"].plays == 1
    # auch ohne Fokusmodus
    plant.state["focus_mode"] = False
    fake_sound.last.clear()
    plant.start_focus(25)
    plant.focus["end"] = 0.0
    plant.run_focus()
    assert fake_sound.effects["gong"].plays == 2


def test_volume_slider_in_settings_menu(plant, fake_sound):
    from PyQt6.QtWidgets import QLabel, QMenu, QPushButton, QSlider
    from topfpflanze import sound
    menu = QMenu()  # Referenz halten, sonst wird der Regler mit freigegeben
    box = plant.volume_slider_action(menu).defaultWidget()
    slider = box.findChild(QSlider)
    label = box.findChild(QLabel)
    assert (slider.minimum(), slider.maximum(), slider.value()) == (0, 100, 60)   # vom Fixture auf 60 gesetzt
    assert label.text() == "Lautstärke: 60 %"
    slider.setValue(20)
    assert plant.state["volume"] == 20 and plant.sound.volume == 20 and label.text() == "Lautstärke: 20 %"
    slider.sliderReleased.emit()                   # Probeton beim Loslassen
    assert fake_sound.effects["giessen"].plays == 1
    slider.setValue(75)
    assert plant.state["volume"] == 75
    box.findChild(QPushButton).click()                 # zurücksetzen = Standard = stumm
    assert plant.state["volume"] == sound.DEFAULT_VOLUME == 0 and label.text() == "Lautstärke: 0 %"


def test_size_sliders_still_work_after_refactoring(plant, scale_reset):
    from PyQt6.QtWidgets import QMenu, QSlider
    menu = QMenu()
    box = plant.scale_slider_action(menu, "menu", "Menügrösse").defaultWidget()
    slider = box.findChild(QSlider)
    assert (slider.minimum(), slider.maximum(), slider.value()) == (50, 200, 100)
    slider.setValue(150)
    assert scale_reset.get_scale("menu") == 1.5


def test_without_audio_the_game_stays_silent_and_works(tmp_path, monkeypatch):
    from topfpflanze import sound
    monkeypatch.setattr(sound, "ensure_files", lambda: (_ for _ in ()).throw(OSError("kein Audio")))
    player = sound.SoundPlayer(60)
    # Ohne Audio stumm: je nach System scheitert schon der Import (fehlende Bibliothek) oder das Schreiben der Dateien
    assert not player.available and player.error
    assert player.play("giessen") is False and player.play("gong") is False
    player.set_volume(10)            # darf nichts auslösen


def test_sound_is_muted_by_default_and_needs_the_slider(tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from topfpflanze import sound
    from topfpflanze.plant import Plant
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(config, "STATE_FILE", tmp_path / "state.json")
    app = QApplication.instance() or QApplication([])
    p = Plant()
    p.timer.stop()
    assert sound.DEFAULT_VOLUME == 0 and p.state["volume"] == 0 and p.sound.volume == 0
    fake = {"giessen": _FakeEffect(), "gong": _FakeEffect()}
    p.sound.effects, p.sound.last = fake, {}
    p.select_plant("wiesenblume")
    p.ps["water"] = 40
    p.water_click(QPointF(100, 150))
    assert fake["giessen"].plays == 0                    # stumm: kein Ton
    p.start_focus(25)
    p.focus["end"] = 0.0
    p.run_focus()
    assert fake["gong"].plays == 0
    p.set_volume(50)                                     # erst der Regler schaltet den Ton ein
    p.sound.last.clear()
    p.ps["water"] = 40
    p.water_click(QPointF(100, 150))
    assert fake["giessen"].plays == 1
    assert app is not None
    # ein gespeicherter Wert bleibt erhalten
    p.save_state()
    p2 = Plant()
    p2.timer.stop()
    assert p2.state["volume"] == 50 and p2.sound.volume == 50


def test_general_achievements_are_series_with_one_row_each(plant):
    from topfpflanze.data import ACHIEVEMENTS
    gen = [a for a in ACHIEVEMENTS if a.period == "general"]
    assert all(a.series for a in gen) and len({a.key for a in ACHIEVEMENTS}) == len(ACHIEVEMENTS)
    for a in ACHIEVEMENTS:                          # jeder Erfolg hat einen Wert
        assert plant.ach_value(a.key) >= 0
    series = {a.series: [x for x in gen if x.series == a.series] for a in gen}
    assert len(series["tasten"]) == 5 and len(series["shop"]) == 5 and len(series["besuche"]) == 5
    assert [a.target for a in series["tasten"]][-1] == 1_000_000
    rows = plant.ach_rows("general")
    assert len(rows) == len(series)
    assert rows[[r[0].series for r in rows].index("tasten")][1:] == (1, 5)
    plant.state["stats"]["keys"] = 12000
    plant.check_achievements()
    assert {e["key"] for e in plant.state["ach_pending"]} >= {"g_keys1", "g_keys10"}
    row = plant.ach_rows("general")[[r[0].series for r in rows].index("tasten")]
    assert row[0].key == "g_keys1" and row[1:] == (1, 5)         # abholbare Stufe zuerst
    plant.claim_achievement(plant.ach_pending_entry("g_keys1"))
    assert plant.ach_rows("general")[[r[0].series for r in rows].index("tasten")][0].key == "g_keys10"
    assert not plant.ach_win.grab().isNull() and plant.ach_win.height() > 600


def test_shop_visit_and_focus_stats_feed_achievements(plant):
    plant.state["coins"] = 10000
    plant.buy_fertilizer("kompost")
    plant.helper_action("tropf")
    st = plant.state["stats"]
    assert st["purchases"] == 2 and st["spent"] == 20 + 250
    assert plant.ach_value("g_shop1") == 2 and plant.ach_value("g_spent") == 270
    plant.state["book"] = {"biene": {"count": 40, "shiny": 1}, "marienkaefer": {"count": 12}}
    assert plant.ach_value("g_vis50") == 52 and plant.ach_value("g_variant1") == 1
    plant.start_focus(60)
    plant.focus["end"] = 0.0
    plant.run_focus()
    assert st["focus"] == 1 and plant.ach_value("g_zen") == 60
    plant.check_achievements()
    assert plant.ach_pending_entry("g_zen") is not None


def test_play_streak_counts_consecutive_days(plant):
    import datetime
    plant.state["stats"].update({"streak": 6, "last_day": (datetime.date.today() - datetime.timedelta(days=1)).isoformat()})
    plant.ensure_periods()
    assert plant.state["stats"]["streak"] == 7
    plant.ensure_periods()
    assert plant.state["stats"]["streak"] == 7                   # am selben Tag nicht doppelt
    plant.state["stats"].update({"last_day": "2000-01-01"})
    plant.ensure_periods()
    assert plant.state["stats"]["streak"] == 1


def test_visitor_achievement_series_one_per_visitor(plant):
    from topfpflanze.data import ACHIEVEMENTS, VISITORS
    n = len(VISITORS)
    for series in ("entdecker", "stammgaeste", "meister"):
        tiers = [a for a in ACHIEVEMENTS if a.series == series]
        assert [a.target for a in tiers] == list(range(1, n + 1))
    plant.state["book"] = {"biene": {"count": 60}, "marienkaefer": {"count": 250}, "libelle": {"count": 3}}
    assert plant.ach_value("g_disc3") == 3 and plant.ach_value("g_reg2") == 2 and plant.ach_value("g_master1") == 1


def test_every_achievement_series_has_at_least_five_ascending_tiers(plant):
    from topfpflanze.data import ACHIEVEMENTS
    series = {}
    for a in ACHIEVEMENTS:
        if a.series:
            series.setdefault(a.series, []).append(a)
    for name, tiers in series.items():
        assert len(tiers) >= 5, name
        targets = [t.target for t in tiers if t.key not in ("g_zen", "g_helpers")]   # andere Messgrösse
        assert targets == sorted(set(targets)), name
    assert len([a for a in series["blueten"]]) == 5 and len(series["farben"]) == 8


# ---------------------------------------------------------------- Sprachen

def _tr_keys():
    import ast, pathlib
    root = pathlib.Path(__file__).parent.parent / "src" / "topfpflanze"
    keys = set()
    for path in root.glob("*.py"):
        for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(n, ast.Call) and getattr(n.func, "id", None) == "tr" and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                keys.add(n.args[0].value)
    return keys


@pytest.mark.parametrize("code", ["en", "fr", "it"])
def test_language_catalog_is_complete_and_consistent(code):
    import importlib, string
    en = importlib.import_module(f"topfpflanze.lang.{code}")
    from topfpflanze import i18n
    assert code in i18n.LANGUAGES
    keys = _tr_keys()
    assert not keys - set(en.STRINGS), sorted(keys - set(en.STRINGS))[:5]      # nichts unübersetzt
    assert not set(en.STRINGS) - keys, sorted(set(en.STRINGS) - keys)[:5]      # keine veralteten Einträge

    def fields(text):
        return sorted(f for _l, f, _s, _c in string.Formatter().parse(text) if f is not None)
    for de, english in en.STRINGS.items():
        assert english.strip(), de
        assert fields(de) == fields(english), (de, english)                    # gleiche Platzhalter


def test_tr_uses_catalog_and_falls_back_to_german():
    from topfpflanze import i18n
    try:
        assert i18n.set_language("en") == "en"
        assert i18n.tr("Dünger") == "Fertilizer"
        assert i18n.tr("{m} min", m=5) == "5 min"
        assert i18n.tr("ein ungeübersetzter Text") == "ein ungeübersetzter Text"
        assert i18n.set_language("xx") == "de" and i18n.tr("Dünger") == "Dünger"
    finally:
        i18n.set_language("de")


@pytest.mark.parametrize("code", ["en", "fr", "it"])
def test_game_starts_in_each_language_in_a_fresh_process(tmp_path, code):
    import subprocess, sys, textwrap, os
    code = textwrap.dedent(f"""
        from topfpflanze import config, i18n
        config.STATE_DIR = config.Path({str(tmp_path)!r}); config.STATE_FILE = config.STATE_DIR / "state.json"
        i18n.set_language({code!r})
        from PyQt6.QtWidgets import QApplication
        app = QApplication([])
        from topfpflanze.data import PLANT_TYPES, VISITORS, ACHIEVEMENTS, RARITY_LABEL
        from topfpflanze.plant import Plant
        p = Plant()
        assert PLANT_TYPES["kaktus"].name == {{"en": "Cactus", "fr": "Cactus", "it": "Cactus"}}[{code!r}]
        assert RARITY_LABEL["sehr selten"] == {{"en": "very rare", "fr": "très rare", "it": "molto raro"}}[{code!r}]
        assert all(a.name for a in ACHIEVEMENTS)
        for w in (p, p.bubble, p.shop, p.garden, p.ach_win, p.focus_win, p.book_win, p.info_win, p.sow_win, p.diary_win, p.diary_text):
            assert not w.grab().isNull()
        print("OK")
    """)
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    assert "OK" in res.stdout, res.stderr[-800:]


def test_saved_language_and_choose_language(plant, tmp_path, monkeypatch):
    import json
    from PyQt6.QtCore import QProcess
    from PyQt6.QtWidgets import QApplication
    from topfpflanze import i18n
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"language": "en"}))
    assert i18n.saved_language(f) == "en"
    f.write_text(json.dumps({"language": "auto"}))
    monkeypatch.setattr(i18n, "system_language", lambda: "de")
    assert i18n.saved_language(f) == "de"
    assert i18n.saved_language(tmp_path / "fehlt.json") == "de"
    # Sprachwechsel: speichert, beendet und startet danach neu
    started = []
    monkeypatch.setattr(QProcess, "startDetached", staticmethod(lambda prog, args: started.append((prog, args))))
    app = QApplication.instance()
    monkeypatch.setattr(app, "quit", lambda: app.aboutToQuit.emit())
    plant.choose_language("en")
    assert plant.state["language"] == "en" and json.load(open(config.STATE_FILE, encoding="utf-8"))["language"] == "en"
    assert started and started[0] == plant.restart_command()
    started.clear()
    plant.choose_language("de")           # gleiche Sprache wie die laufende: nur speichern, kein Neustart
    assert plant.state["language"] == "de" and not started


def test_helpers_are_per_plant_like_fertilizer(plant):
    plant.state["coins"] = 10000
    plant.select_plant("wiesenblume")
    ok, _ = plant.helper_action("tropf")
    assert ok and plant.helper_on("tropf") and plant.state["coins"] == 9750
    assert plant.helper_action("tropf")[0] and not plant.helper_on("tropf")      # zweiter Klick: ausschalten
    plant.helper_action("tropf")
    plant.select_plant("kaktus")
    assert not plant.helper_on("tropf")                                          # gilt nur für die Wiesenblume
    plant.helper_action("lampe")
    assert plant.helper_on("lampe") and plant.ps["helpers"] == ["lampe"]
    plant.select_plant("wiesenblume")
    assert plant.helper_on("tropf") and not plant.helper_on("lampe")
    assert plant.ach_value("g_helpers") == 1
    plant.ps["helpers"] = list(data.HELPER_ORDER)
    assert plant.ach_value("g_helpers") == 5
    assert not plant.shop.grab().isNull()


def test_helpers_stay_with_the_plant_when_resowing(plant):
    plant.ps["helpers"], plant.ps["helpers_off"] = ["zwerg", "tropf"], ["tropf"]
    plant.state["coins"] = 1000
    plant.confirm_sow("orig")
    assert plant.ps["helpers"] == ["zwerg", "tropf"] and plant.ps["helpers_off"] == ["tropf"]
    assert plant.helper_on("zwerg") and not plant.helper_on("tropf")


def test_old_global_helpers_migrate_to_every_plant(plant, tmp_path, monkeypatch):
    import json
    state = plant.state
    state.pop("helpers_legacy", None)
    legacy = {"version": 2, "current": "wiesenblume", "helpers": ["hummel", "lampe"], "helpers_off": ["lampe"],
              "plants": {"wiesenblume": {"growth": 5.0}}}
    config.STATE_FILE.write_text(json.dumps(legacy), encoding="utf-8")
    plant.state = plant.load_state()
    assert "helpers" not in plant.state and plant.state["plants"]["wiesenblume"]["helpers"] == ["hummel", "lampe"]
    assert plant.state["plants"]["wiesenblume"]["helpers_off"] == ["lampe"]
    plant.activate("kaktus")                     # später erstellte Pflanze erhält die früheren Käufe ebenfalls
    assert plant.ps["helpers"] == ["hummel", "lampe"] and plant.helper_on("hummel") and not plant.helper_on("lampe")


# ---------------------------------------------------------------- Tagebuch

def test_diary_store_saves_loads_and_removes_empty_entries(plant):
    import datetime, json
    from topfpflanze.diary import DiaryStore
    day = datetime.date(2026, 10, 4)
    store = plant.diary
    store.put(day, "Heute war ein guter Tag.", 3)
    path = config.STATE_DIR / "diary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["entries"]["2026-10-04"]["text"] == "Heute war ein guter Tag." and data["entries"]["2026-10-04"]["mood"] == 3
    again = DiaryStore()                                   # frisch von der Platte
    assert again.text(day) == "Heute war ein guter Tag." and again.mood(day) == 3 and again.has(day)
    assert again.month_count(2026, 10) == 1 and again.month_count(2026, 9) == 0
    again.put(day, "   ", None)                            # leer und ohne Stimmung: Eintrag verschwindet
    assert not again.has(day) and DiaryStore().entries == {}
    again.put(day, "", 1)                                  # nur eine Stimmung zählt als Eintrag
    assert again.has(day) and again.size(day) == 0
    assert not (config.STATE_DIR / "diary.json.tmp").exists()


def test_diary_text_window_autosaves_and_switches_days(plant):
    import datetime
    w = plant.diary_text
    d1, d2 = datetime.date(2026, 10, 4), datetime.date(2026, 10, 5)
    w.open_date(d1)
    assert w.isVisible() and w.date == d1
    w.editor.setPlainText("Gedanken vom Sonntag")
    assert w.dirty and not plant.diary.has(d1)             # gespeichert wird nach kurzer Pause
    w.timer.timeout.emit()
    assert plant.diary.text(d1) == "Gedanken vom Sonntag" and not w.dirty
    w.editor.setPlainText("Noch ein Satz")
    w.open_date(d2)                                        # Datumswechsel speichert den bisherigen Tag
    assert plant.diary.text(d1) == "Noch ein Satz" and w.editor.toPlainText() == ""
    w.on_click(("m", 4))                                   # Stimmung wählen speichert sofort
    assert plant.diary.mood(d2) == 4 and w.mood == 4
    w.on_click(("m", 4))
    assert plant.diary.mood(d2) is None and not plant.diary.has(d2)
    w.open_date(d1)
    assert w.editor.toPlainText() == "Noch ein Satz"
    w.editor.setPlainText("zuletzt")
    w.hide()                                               # beim Schliessen wird gespeichert
    assert plant.diary.text(d1) == "zuletzt"
    plant.diary_text.editor.setPlainText("beim Beenden")
    plant.save_state()
    assert plant.diary.text(d1) == "beim Beenden"
    for win in (plant.diary_win, w):
        assert not win.grab().isNull()


def test_diary_calendar_selects_days_and_navigates_months(plant):
    import datetime
    cal = plant.diary_win
    today = datetime.date.today()
    plant.diary.put(today, "x" * 300, 2)
    cal.show_month_of(today)
    assert (cal.year, cal.month) == (today.year, today.month)
    assert not cal.grab().isNull()
    cal.on_click(("d", 1))
    assert plant.diary_text.date == today.replace(day=1) and plant.diary_text.isVisible()
    cal.on_click("prev")
    assert (cal.year, cal.month) == ((today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12))
    cal.on_click("next")
    cal.on_click("next")
    nxt = (today.month % 12) + 1
    assert cal.month == nxt
    cal.on_click("today")
    assert plant.diary_text.date == today and (cal.year, cal.month) == (today.year, today.month)
    assert any(k == ("d", today.day) for k, _r, _c in cal.items())
    assert cal.heat(300).name() != cal.heat(10).name()                       # mehr Text = dunkler


def test_diary_icon_opens_both_windows_and_focus_mode_keeps_the_text_window(plant):
    assert "diary" in config.TOOL_ORDER
    plant.toggle_window("diary")
    assert plant.diary_win.isVisible() and plant.diary_text.isVisible()
    assert plant.diary_text.date.isoformat() == __import__("time").strftime("%Y-%m-%d")
    plant.bubble.show()
    plant.ach_win.show()
    plant.start_focus(25)                                  # Fokusmodus: Menüfenster weg, Textfenster bleibt
    assert plant.focus_mode_active
    assert plant.diary_text.isVisible() and not plant.diary_win.isVisible()
    assert not plant.ach_win.isVisible() and not plant.bubble.isVisible()
    plant.abort_focus()
    assert plant.diary_win.isVisible() and plant.diary_text.isVisible() and plant.ach_win.isVisible()
    plant.toggle_window("diary")                           # nochmal klicken: beide zu
    assert not plant.diary_win.isVisible() and not plant.diary_text.isVisible()
    assert "Tagebuch" in plant.bubble.tooltip_text("diary")
    assert not plant.bubble.grab().isNull()


def test_diary_text_scales_with_the_menu_slider(plant, scale_reset):
    plant.diary_text.show()
    base = plant.diary_text.editor.geometry().width()
    plant.set_ui_scale(1.5, "menu")
    assert plant.diary_text.editor.geometry().width() > base
    assert plant.diary_text.editor.font().pixelSize() == round(plant.diary_text.EDIT_PX * plant.diary_text._k)


# ---------------------------------------------------------------- Rechtschreibung

def test_spell_checker_english_words_suggestions_and_personal_dictionary(plant):
    from topfpflanze import spell
    sc = spell.SpellChecker()
    assert sc.load_now("en") and sc.ready("en") and sc.check("en", "garden")
    assert not sc.check("en", "gardn") and sc.check("en", "NASA") and sc.check("en", "a")      # Kürzel und 1 Buchstabe nie falsch
    assert "receive" in sc.suggest("en", "recieve")
    assert not sc.check("en", "Roggwil")
    sc.add_word("Roggwil")
    assert sc.check("en", "Roggwil") and "Roggwil" in (config.STATE_DIR / "diary_words.txt").read_text(encoding="utf-8")
    assert "Roggwil" in spell.SpellChecker().personal                                          # bleibt nach einem Neustart
    sc.ignore("gardn")
    assert sc.check("en", "gardn")
    assert not sc.load_now("xx") and sc.check("xx", "irgendwas")                               # unbekannte Sprache: nichts markieren


def test_spell_checker_swiss_german_and_apostrophes(plant):
    from topfpflanze import spell
    sc = spell.SpellChecker()
    assert sc.load_now("de")
    assert sc.check("de", "Strasse") and not sc.check("de", "Straße")                          # Schweizer Rechtschreibung: ss
    assert sc.check("de", "Wiesenblume") and not sc.check("de", "lkjsdfkljsdflkj")
    assert sc.check("de", "Rad-Weg") and sc.check("de", "geht's")
    assert not sc.check("de", "gemütszustandd")
    assert sc.load_now("fr") and sc.check("fr", "l'amour") and not sc.check("fr", "bonjuor")
    assert sc.load_now("it") and sc.check("it", "dell'arte") and not sc.check("it", "ciaoo")


def test_diary_underlines_misspelled_words_but_not_the_word_being_typed(plant):
    w = plant.diary_text
    plant.state["diary_spell"] = "en"
    w.spell.load_now("en")
    w.open_date(__import__("datetime").date(2026, 10, 4))
    w.editor.setPlainText("The gardn is nice and gardn")
    w.highlighter.rehighlight()
    block = w.editor.document().firstBlock()
    marked = {f.start for f in block.layout().formats()}
    assert {4, 22} <= marked and 0 not in marked                                           # beide «gardn», nicht «The»
    assert w.spell_label() == "Rechtschreibung: English"
    plant.state["diary_spell"] = "off"
    w.apply_spell()
    assert not block.layout().formats() and w.spell_label() == "Rechtschreibung: aus"
    plant.state["diary_spell"] = "auto"
    assert w.spell_lang() == "de"                                                           # folgt der Sprache des Spiels
    assert not w.grab().isNull()


def test_dictionaries_ship_with_the_program_and_notice_lists_licences():
    import pathlib
    from topfpflanze import spell
    for name in spell.DICTIONARIES.values():
        assert (spell.DICT_DIR / name / f"{name}.dic").exists() and (spell.DICT_DIR / name / f"{name}.aff").exists()
    notice = (spell.DICT_DIR / "NOTICE.md").read_text(encoding="utf-8")
    assert "GPL" in notice and "MPL" in notice and "SCOWL" in notice
    pyproject = (pathlib.Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert "spylls" in pyproject and "dictionaries" in pyproject


def test_spell_failure_is_explained_in_label_and_tooltip(plant, monkeypatch):
    from topfpflanze import spell
    monkeypatch.setattr(spell, "_DICTS", {})
    monkeypatch.setattr(spell, "_FAILED", set())
    monkeypatch.setattr(spell, "_ERRORS", {})
    monkeypatch.setattr(spell, "DICT_DIR", spell.DICT_DIR / "fehlt")        # Wörterbuch nicht auffindbar
    w = plant.diary_text
    plant.state["diary_spell"] = "en"
    assert not w.spell.load_now("en")
    assert w.spell_label() == "Rechtschreibung: nicht verfügbar"
    assert "FileNotFoundError" in w.tooltip_at(w.spell_rect().center()) or "Error" in w.tooltip_at(w.spell_rect().center())
    w.choose_spell.__func__        # Menü existiert
    assert not w.grab().isNull()


def test_diary_has_six_moods_with_neutral_last(plant):
    from topfpflanze import diary
    assert len(diary.MOODS) == 6
    assert diary.MOODS[5][1] == "neutral" and diary.FACES[5] == "neutral"
    w = plant.diary_text
    rects = w.mood_rects()
    assert len(rects) == 6 and all(r.right() <= w.W - 14 + 0.5 for r in rects)
    import datetime
    d = datetime.date(2026, 10, 4)
    w.open_date(d)
    w.on_click(("m", 5))
    assert plant.diary.mood(d) == 5 and w.mood == 5
    order = [k[1] for k, _r, _c in w.items() if k[0] == "m"]
    assert order == [0, 1, 5, 2, 3, 4]                                  # neutral steht zwischen müde und ruhig
    rects = {k[1]: r for k, r, _c in w.items() if k[0] == "m"}
    assert rects[1].right() < rects[5].left() < rects[5].right() < rects[2].left()
    assert w.spell_rect().top() >= w.paper_rect().bottom()               # Rechtschreibung und Zeichenzahl unter dem Blatt
    assert not w.grab().isNull()


def test_clicking_the_date_toggles_the_calendar(plant):
    w, cal = plant.diary_text, plant.diary_win
    w.show()
    cal.hide()
    assert w.item_at(w.date_rect().center()) == "date"
    w.on_click("date")
    assert cal.isVisible()
    w.on_click("date")
    assert not cal.isVisible()
    assert "Kalender" in w.tooltip_at(w.date_rect().center())


def test_diary_text_window_can_be_resized_and_remembers_the_size(plant):
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    w = plant.diary_text
    w.show()
    w0, h0 = w.W, w.H
    g = w.grip_rect().center()

    def ev(kind, pos, buttons=Qt.MouseButton.LeftButton):
        return QMouseEvent(kind, QPointF(pos), QPointF(w.mapToGlobal(QPointF(pos).toPoint())),
                           Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier)
    w.mousePressEvent(ev(QEvent.Type.MouseButtonPress, g))
    target = QPointF(g.x() + 100, g.y() + 80)
    w.mouseMoveEvent(ev(QEvent.Type.MouseMove, target))
    w.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, target, Qt.MouseButton.NoButton))
    assert w.W > w0 and w.H > h0
    assert plant.state["diary_text_size"] == [w.W, w.H]
    assert w.paper_rect().height() > 338 and w.editor.geometry().height() > 300           # die Seite ist grösser
    w.resize_to(10, 10)                                                                      # nie unter die Mindestgrösse
    assert (w.W, w.H) == w.MIN_SIZE
    assert w.mood_rects()[-1].right() <= w.W
    assert not w.grab().isNull()
    from topfpflanze.diary import DiaryTextWin                                               # Grösse wird beim Start gelesen
    plant.state["diary_text_size"] = [500, 700]
    assert (lambda x: (x.W, x.H))(DiaryTextWin(plant)) == (500, 700)


# ---------------------------------------------------------------- Sicherung (Export / Import)

def _sample_backup(tmp_path, version="0.2.0", extra=None):
    from topfpflanze import backup
    state = {"version": 2, "plants": {"wiesenblume": {"growth": 12.5}}, "coins": 321, "pos": [5, 6], "bubble_pos": [1, 2],
             "diary_text_size": [500, 700], "language": "en"}
    entries = {"2026-10-04": {"text": "Hallo Tagebuch", "mood": 2, "updated": 1.0}, "2026-10-05": {"text": "", "mood": 0, "updated": 2.0}}
    path = tmp_path / "b.zip"
    backup.write_backup(path, state, entries, {"Roggwil"}, version, ["schwer", "müde", "ruhig"])
    return path, state, entries


def test_backup_roundtrip_with_readable_diary_and_without_window_positions(tmp_path):
    import zipfile
    from topfpflanze import backup
    path, state, entries = _sample_backup(tmp_path)
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist()) == set(backup.NAMES)
        text = z.read("tagebuch.txt").decode("utf-8")
    assert "=== 2026-10-04 (ruhig) ===" in text and "Hallo Tagebuch" in text and "=== 2026-10-05 (schwer) ===" in text
    data = backup.read_backup(path, "0.2.0")
    assert data["state"]["coins"] == 321 and data["state"]["language"] == "en" and data["state"]["diary_text_size"] == [500, 700]
    assert "pos" not in data["state"] and "bubble_pos" not in data["state"]          # Positionen gehören zum alten Bildschirm
    assert data["diary"] == entries and data["words"] == ["Roggwil"] and data["manifest"]["entries"] == 2
    out = tmp_path / "out"
    backup.restore(data, out / "state.json", out / "diary.json", out / "diary_words.txt")
    import json
    assert json.loads((out / "state.json").read_text(encoding="utf-8"))["coins"] == 321
    assert json.loads((out / "diary.json").read_text(encoding="utf-8"))["entries"] == entries
    assert (out / "diary_words.txt").read_text(encoding="utf-8").strip() == "Roggwil"


def test_backup_rejects_wrong_files_and_newer_versions(tmp_path):
    import json, zipfile
    from topfpflanze import backup
    junk = tmp_path / "junk.zip"
    junk.write_bytes(b"das ist keine zip-datei")
    for bad in (junk, tmp_path / "fehlt.zip"):
        try:
            backup.read_backup(bad, "0.2.0")
            assert False, "hätte scheitern müssen"
        except backup.BackupError as e:
            assert "gültige Sicherung" in str(e)
    other = tmp_path / "other.zip"
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("manifest.json", json.dumps({"app": "etwas-anderes"}))
        z.writestr("state.json", json.dumps({"plants": {}}))
    try:
        backup.read_backup(other, "0.2.0")
        assert False
    except backup.BackupError:
        pass
    newer, _s, _e = _sample_backup(tmp_path, version="9.0.0")
    try:
        backup.read_backup(newer, "0.2.0")
        assert False
    except backup.BackupError as e:
        assert "9.0.0" in str(e)
    evil = tmp_path / "evil.zip"                       # Pfade aus der ZIP-Datei werden nie benutzt
    ok, _s, _e = _sample_backup(tmp_path)
    with zipfile.ZipFile(ok) as src, zipfile.ZipFile(evil, "w") as dst:
        for n in src.namelist():
            dst.writestr(n, src.read(n))
        dst.writestr("../../evil.txt", "x")
    backup.read_backup(evil, "0.2.0")
    assert not (tmp_path.parent / "evil.txt").exists()


def test_export_and_import_replace_the_game_data_and_keep_a_safety_copy(plant, tmp_path, monkeypatch):
    import datetime, json
    from PyQt6.QtCore import QProcess
    from PyQt6.QtWidgets import QApplication, QFileDialog
    target = tmp_path / "meine-sicherung"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    day = datetime.date(2026, 10, 4)
    plant.state["coins"] = 777
    plant.diary.put(day, "Mein Eintrag", 2)
    plant.diary_text.spell.add_word("Roggwil")
    plant.export_data()
    zip_path = tmp_path / "meine-sicherung.zip"                      # «.zip» wird ergänzt
    assert zip_path.exists() and plant.confirm_win.isVisible() and "meine-sicherung.zip" in plant.confirm_win.text
    plant.confirm_win.hide()
    # Zustand ändern, dann importieren
    plant.state["coins"] = 5
    plant.diary.put(day, "Anderer Text", None)
    (config.STATE_DIR / "diary_words.txt").unlink()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(zip_path), "")))
    started = []
    monkeypatch.setattr(QProcess, "startDetached", staticmethod(lambda prog, args: started.append((prog, args))))
    app = QApplication.instance()
    monkeypatch.setattr(app, "quit", lambda: app.aboutToQuit.emit())
    plant.import_data()
    win = plant.confirm_win
    assert win.isVisible() and "Importieren" in win.ok_label and win.cancel_label and "2026" in win.text
    assert not win.grab().isNull()
    win.on_click("cancel")                                           # Abbrechen: nichts passiert
    assert plant.state["coins"] == 5 and not started
    plant.import_data()
    plant.confirm_win.on_click("ok")
    assert started and started[0] == plant.restart_command()
    assert json.loads(config.STATE_FILE.read_text(encoding="utf-8"))["coins"] == 777
    assert json.loads((config.STATE_DIR / "diary.json").read_text(encoding="utf-8"))["entries"]["2026-10-04"]["text"] == "Mein Eintrag"
    assert (config.STATE_DIR / "diary_words.txt").read_text(encoding="utf-8").strip() == "Roggwil"
    copies = list((config.STATE_DIR / "backups").glob("vor-Import-*.zip"))
    assert len(copies) == 1 or len(copies) >= 1                      # Sicherung des Stands vor dem Import
    plant.save_state()                                               # nach dem Import wird nichts mehr überschrieben
    plant.diary.put(day, "zu spät", None)
    assert json.loads(config.STATE_FILE.read_text(encoding="utf-8"))["coins"] == 777
    assert json.loads((config.STATE_DIR / "diary.json").read_text(encoding="utf-8"))["entries"]["2026-10-04"]["text"] == "Mein Eintrag"


def test_import_of_an_invalid_file_shows_a_message_and_changes_nothing(plant, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QFileDialog
    junk = tmp_path / "x.zip"
    junk.write_text("kein zip")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(junk), "")))
    plant.state["coins"] = 42
    plant.import_data()
    assert plant.confirm_win.isVisible() and "gültige Sicherung" in plant.confirm_win.text and plant.confirm_win.cancel_label is None
    assert plant.state["coins"] == 42 and not getattr(plant, "_no_save", False)
    assert not plant.confirm_win.grab().isNull()
