import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from topfpflanze import game


def test_data_dir_per_platform(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(sys, "platform", "win32")
    assert game.data_dir() == tmp_path / "roaming" / "topfpflanze"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert game.data_dir() == Path.home() / "Library" / "Application Support" / "topfpflanze"
    monkeypatch.setattr(sys, "platform", "linux")
    assert game.data_dir() == tmp_path / "xdg" / "topfpflanze"


def test_stage_progression():
    k = game.PLANT_TYPES["wiesenblume"]
    assert game.stage_name(k, 0) == "Samen"
    assert game.stage_name(k, k.bloom_at) == "Blühend"


def test_fmt_int_swiss():
    assert game.fmt_int(1234567) == "1'234'567"


def test_plant_window_starts(tmp_path, monkeypatch):
    monkeypatch.setattr(game, "STATE_DIR", tmp_path)
    monkeypatch.setattr(game, "STATE_FILE", tmp_path / "state.json")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    plant = game.Plant()
    plant.show()
    app.processEvents()
    plant.save_state()
    assert (tmp_path / "state.json").exists()
