import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

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
    scaling.set_scale(1.0)


@pytest.mark.parametrize("value", [0.5, 1.5, 2.0])
def test_ui_scale_sizes(plant, scale_reset, value):
    from topfpflanze import config
    plant.bubble.show()
    plant.set_ui_scale(value)
    assert plant.real_width() == round(config.WIN_W * value) or value > 1.0
    assert plant.width() == config.WIN_W  # logische Grösse bleibt
    for w in [plant, plant.bubble, *plant.windows.values()]:
        assert w.real_width() == round(w.width() * w._k)
        assert not w.grab().isNull()
    assert plant.state["ui_scale"] == value
    plant.set_ui_scale(1.0)
    assert plant.real_width() == config.WIN_W


def test_ui_scale_limits(scale_reset):
    assert scale_reset.set_scale(0.1) == 0.5
    assert scale_reset.set_scale(9) == 2.0


def test_mouse_position_is_scaled_back(plant, scale_reset):
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest
    plant.set_ui_scale(0.5)
    b = plant.bubble
    b.show()
    key, rect = next((k, r) for k, r in b.icon_rects() if k == "kaktus")
    pt = rect.center() * b._k  # echte Pixel
    QTest.mouseClick(b, Qt.MouseButton.LeftButton, pos=QPoint(int(pt.x()), int(pt.y())))
    assert plant.state["current"] == "kaktus"


def test_ui_scale_saved_and_restored(tmp_path, monkeypatch, scale_reset):
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(config, "STATE_FILE", tmp_path / "state.json")
    from PyQt6.QtWidgets import QApplication
    from topfpflanze.plant import Plant
    app = QApplication.instance() or QApplication([])
    p = Plant()
    p.timer.stop()
    p.set_ui_scale(0.75)
    p.save_state()
    scale_reset.set_scale(1.0)
    p2 = Plant()
    p2.timer.stop()
    assert scale_reset.get_scale() == 0.75


def test_scale_slider_changes_scale(plant, scale_reset):
    from PyQt6.QtWidgets import QMenu, QPushButton, QSlider
    menu = QMenu()
    act = plant.scale_slider_action(menu)
    box = act.defaultWidget()
    slider = box.findChild(QSlider)
    assert (slider.minimum(), slider.maximum(), slider.value()) == (50, 200, 100)
    slider.setValue(150)
    assert scale_reset.get_scale() == 1.5
    box.findChild(QPushButton).click()  # «100 %»
    assert scale_reset.get_scale() == 1.0
