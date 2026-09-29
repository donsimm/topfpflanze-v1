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
