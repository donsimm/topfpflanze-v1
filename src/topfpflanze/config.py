"""Pfade und Konstanten (Fenstergrössen, Gold-Werte)."""

import os
import sys
from pathlib import Path



APP_NAME = "topfpflanze"


def data_dir():
    """Datenordner je Betriebssystem (Windows: %APPDATA%, macOS: Application Support, sonst XDG)."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / APP_NAME


STATE_DIR = data_dir()
STATE_FILE = STATE_DIR / "state.json"


def set_data_dir(path):
    """Speicherort ändern (Kommandozeile --data-dir, Debug-Modus). Vor dem Start der Pflanze aufrufen."""
    global STATE_DIR, STATE_FILE
    STATE_DIR = Path(path).expanduser().resolve()
    STATE_FILE = STATE_DIR / "state.json"

SCENE_DY = 50              # zusätzlicher Platz oben für die grösseren Pflanzen
SCENE_H = 330              # Höhe der Zeichenfläche für Topf und Pflanze
WIN_W, WIN_H = 220, SCENE_H + SCENE_DY
PLANT_SCALE = 1.2          # Pflanzen 20 % grösser, Töpfe unverändert
BUBBLE_W, BUBBLE_H = 224, 252
BUBBLE_ROWS_H = 164         # Höhe des Textbereichs
ICON, ICON_GAP = 30, 7 * 2 / 3  # Pflanzensymbole in der Sprechblase
SHOP_GAP = 16 * 2 / 3        # (nicht mehr verwendet)
TOOL, TOOL_GAP = 24, 6       # Werkzeugsymbole (zweite Reihe)
TOOL_ORDER = ["shop", "garden", "ach", "focus", "book", "info"]
TOOL_NAMES = {"shop": "Shop", "garden": "Gartenhaus", "ach": "Erfolge", "focus": "Fokus-Timer",
              "book": "Besucher-Sammelbuch", "info": "Info"}
VISITOR_SCALE = 1.25 * 1.3   # Darstellungsgrösse der Besucher auf der Pflanze (+30 %); das Sammelbuch bleibt unverändert
SHOP_W, SHOP_H = 270, 304
GARDEN_W, GARDEN_H = 300, 444

STAGE_COINS = (0, 5, 10, 20, 35, 50, 100)  # Gold beim Erreichen der Stufen 1–6
MILESTONE_STEP = 0.25                      # nach der Blüte: je +25 % des Blütewerts ...
MILESTONE_COINS = 25                       # ... diese Anzahl Gold
PASSIVE_PER_HOUR = 2                       # passives Einkommen während das Programm läuft
WATER_MAX = 100.0
SEED_FRAC = 0.00625  # Anteil am Blütewert, ab dem die Pflanze keimt
