import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QEvent, Qt  # noqa: E402

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


def test_bubble_tooltip_event_shows_text(plant, scale_reset):
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QHelpEvent
    from PyQt6.QtWidgets import QToolTip
    b = plant.bubble
    b.show()
    for kind_scale in (1.0, 0.5):
        plant.set_ui_scale(kind_scale, "menu")
        rect = dict(b.icon_rects())["shop"]
        pt = rect.center() * b._k
        ev = QHelpEvent(QEvent.Type.ToolTip, QPoint(int(pt.x()), int(pt.y())), b.mapToGlobal(QPoint(int(pt.x()), int(pt.y()))))
        assert b.event(ev)
        assert QToolTip.isVisible() and QToolTip.text().startswith("Dünger-Shop")
        QToolTip.hideText()


def test_close_button_tooltip(plant):
    from PyQt6.QtGui import QHelpEvent
    from PyQt6.QtWidgets import QToolTip
    for win in (plant.shop, plant.garden, plant.ach_win, plant.focus_win, plant.book_win):
        win.show()
        pt = win.close_rect().center().toPoint()
        ev = QHelpEvent(QEvent.Type.ToolTip, pt, win.mapToGlobal(pt))
        assert win.event(ev)
        assert QToolTip.isVisible() and QToolTip.text() == "Schliessen"
        QToolTip.hideText()
