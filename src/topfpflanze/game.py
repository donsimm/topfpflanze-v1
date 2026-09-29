#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Topfpflanze – Desktop-Pflanzen, die durch Klicks und Tastaturanschläge wachsen.

Pflanzen (Rechtsklick-Menü > «Pflanze wählen», jede mit eigenem Spielstand):
  Wiesenblume   Mittel        Terrakottatopf   (die ursprüngliche Pflanze)
  Kaktus        Leicht        Betontopf        braucht wenig Wasser
  Tulpe         Mittel        Keramiktopf      wächst NUR durch Mausklicks
  Sonnenblume   Schwer        Zinkeimer        braucht viel Wasser, lange Wachstumszeit
  Bonsai        Sehr schwer   Bonsaischale     wächst nur gut bei 30–80 % Wasser

Bedienung:
  Linksklick                 giessen (Wasser + Wachstum)
  Linke Maustaste ziehen     Fenster verschieben
  Mittelklick                Status-Sprechblase ein-/ausblenden
  Sprechblase ziehen         Sprechblase verschieben (eigenes Fenster)
  Symbol in der Sprechblase  Pflanze wählen (aktive Pflanze grün umrandet)
  Taschen-Symbol             Dünger-Shop öffnen/schliessen
  Gartenhaus-Symbol          Gartenhaus (Ehrenhalle) öffnen/schliessen

Sprechblase: oben die fünf Pflanzen, darunter die Werkzeuge
  Shop · Gartenhaus · Erfolge · Fokus-Timer · Besucher-Sammelbuch

Helfer (Shop > Reiter «Helfer», einmal kaufen, einzeln ein-/ausschaltbar):
  Tropfbewässerung, Hummel, Gartenzwerg, Pflanzenlampe, Düngerautomat

Prestige:
  Eine voll ausgewachsene Pflanze einlagern erhöht die Prestige-Stufe dieser Art um 1
  (je Stufe dauerhaft +10 % Wachstum und Coins). Nicht ausgewachsene Pflanzen kommen
  nur ins Gartenhaus.

Erfolge: 3 tägliche, 3 wöchentliche und 6 einmalige, Belohnung in Coins.
Fokus-Timer: 25, 45 oder 60 Minuten mit doppeltem Wachstum, Abbruch kostet nur den Bonus.
Besucher: kommen von selbst; Klick auf einen Besucher begrüsst ihn (+3 Coins).

Gartenhaus:
  - Wird eine Pflanze neu ausgesät, kommt sie in jedem Stadium mit Datum und Uhrzeit ins Gartenhaus.
  - Schaltfläche «Einlagern & neu aussäen» unten im Gartenhaus; die Samentüte wird golden
    und pulsiert, sobald die ausgewählte Pflanze blüht.
  - Karten lassen sich über das × oben links auf der Karte löschen (mit Rückfrage).
  - Neu ausgesäte Pflanzen erhalten eine zufällige Blütenfarbe.

Coins und Dünger:
  - Jede erreichte Wachstumsstufe bringt Coins (je schwieriger die Pflanze, desto mehr).
  - Nach der Blüte bringt jedes weitere Viertel des Blütewerts erneut Coins.
  - Passives Einkommen: 2 Coins pro Stunde, solange das Programm läuft.
  - Im Shop gekaufter Dünger wirkt auf die ausgewählte Pflanze: mehr Wachstum,
    teilweise aber höherer Wasserverbrauch. Die Laufzeit zählt nur, solange die
    Pflanze ausgewählt ist und das Programm läuft.
  Rechtsklick                Menü

Spielmechanik:
  - Wasser sinkt mit der Zeit (Geschwindigkeit je nach Pflanze), auch bei ausgeschaltetem PC.
  - Nicht ausgewählte Pflanzen pausieren: kein Wasserverlust, kein Wachstum.
  - Tastendrücke lassen die Pflanze wachsen und verbrauchen etwas Wasser.
  - Klicks bei vollem Wasserstand bringen Wachstum, ohne zu giessen (Wachstumspartikel statt Tropfen).

Abhängigkeiten:
  PyQt6    erforderlich
  pynput   Tastaturzählung unter Windows, macOS und Linux/X11
  evdev    optional (nur Linux): Tastaturzählung auch unter Wayland (Benutzer in Gruppe 'input')

Datenschutz: Es wird ausschliesslich die Anzahl der Tastendrücke gezählt,
nicht welche Tasten gedrückt wurden.
"""

import json
import math
import os
import random
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QActionGroup, QBrush, QColor, QFont, QImage, QLinearGradient,
                         QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QToolTip, QWidget

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

SCENE_DY = 50              # zusätzlicher Platz oben für die grösseren Pflanzen
SCENE_H = 330              # Höhe der Zeichenfläche für Topf und Pflanze
WIN_W, WIN_H = 220, SCENE_H + SCENE_DY
PLANT_SCALE = 1.2          # Pflanzen 20 % grösser, Töpfe unverändert
BUBBLE_W, BUBBLE_H = 224, 252
BUBBLE_ROWS_H = 164         # Höhe des Textbereichs
ICON, ICON_GAP = 30, 7 * 2 / 3  # Pflanzensymbole in der Sprechblase
SHOP_GAP = 16 * 2 / 3        # (nicht mehr verwendet)
TOOL, TOOL_GAP = 24, 6       # Werkzeugsymbole (zweite Reihe)
TOOL_ORDER = ["shop", "garden", "ach", "focus", "book"]
TOOL_NAMES = {"shop": "Shop", "garden": "Gartenhaus", "ach": "Erfolge", "focus": "Fokus-Timer",
              "book": "Besucher-Sammelbuch"}
SHOP_W, SHOP_H = 270, 304
GARDEN_W, GARDEN_H = 300, 444

STAGE_COINS = (0, 5, 10, 20, 35, 50, 100)  # Coins beim Erreichen der Stufen 1–6
MILESTONE_STEP = 0.25                      # nach der Blüte: je +25 % des Blütewerts ...
MILESTONE_COINS = 25                       # ... diese Anzahl Coins
PASSIVE_PER_HOUR = 2                       # passives Einkommen während das Programm läuft
WATER_MAX = 100.0
SEED_FRAC = 0.00625  # Anteil am Blütewert, ab dem die Pflanze keimt


# ---------------------------------------------------------------- Pflanzenarten

@dataclass(frozen=True)
class PlantType:
    key: str
    name: str
    difficulty: str
    pot: str
    bloom_at: float          # Wachstumspunkte bis zur Blüte
    growth_per_click: float
    growth_per_key: float    # 0 = Tastatur zählt nicht
    water_per_click: float
    water_per_key: float
    drain_hours: float       # Zeit von 100 % auf 0 % Wasser
    water_low: float = 20.0  # darunter reduziertes Wachstum
    water_high: float = 100.0  # darüber reduziertes Wachstum (Staunässe)
    wilt_below: float = 15.0
    stages: tuple = ("Samen", "Keimling", "Jungpflanze", "Pflanze",
                     "Grosse Pflanze", "Knospe", "Blühend")
    note: str = ""
    coin_mult: float = 1.0   # Faktor für Coin-Belohnungen
    colors: tuple = ("#E85D75", "#C44DD8", "#F2A541", "#5D8CE8", "#F25C54")  # alte Farbberechnung
    palette: tuple = ("#E85D75", "#C44DD8", "#F2A541", "#5D8CE8", "#F25C54", "#F7F3E8",
                      "#FFD23F", "#FF8FB1", "#7B2CBF", "#E63946", "#2EC4B6")  # neue Pflanzen


STAGE_FRACTIONS = (0.0, SEED_FRAC, 0.0375, 0.15, 0.5, 0.75, 1.0)

PLANT_TYPES = {
    "wiesenblume": PlantType(
        "wiesenblume", "Wiesenblume", "Mittel", "terrakotta",
        bloom_at=800, growth_per_click=0.4, growth_per_key=0.02,
        water_per_click=6.0, water_per_key=0.005, drain_hours=12),
    "kaktus": PlantType(
        "kaktus", "Kaktus", "Leicht", "beton",
        bloom_at=400, growth_per_click=0.3, growth_per_key=0.025,
        water_per_click=10.0, water_per_key=0.002, drain_hours=48,
        water_low=10, wilt_below=5,
        stages=("Samen", "Keimling", "Kügelchen", "Säule", "Grosser Kaktus", "Knospe", "Blühend"),
        note="Braucht wenig Wasser.", coin_mult=0.5,
        colors=("#FF6FA8", "#FF8C42", "#F2D14C", "#E84C6A"),
        palette=("#FF6FA8", "#FF8C42", "#F2D14C", "#E84C6A", "#FFFFFF", "#B5179E", "#FF4D00", "#FFB5C2")),
    "tulpe": PlantType(
        "tulpe", "Tulpe", "Mittel, nur Klicks", "keramik",
        bloom_at=500, growth_per_click=1.0, growth_per_key=0.0,
        water_per_click=0.8, water_per_key=0.0, drain_hours=8,
        stages=("Zwiebel", "Austrieb", "Blätter", "Stängel", "Grosse Tulpe", "Knospe", "Blühend"),
        note="Wächst nur durch Mausklicks.",
        colors=("#E8333A", "#F6C431", "#F07AA8", "#8E44AD", "#F58A32", "#F5F1E6"),
        palette=("#E8333A", "#F6C431", "#F07AA8", "#8E44AD", "#F58A32", "#F5F1E6",
                 "#3B1F4A", "#FF9EBB", "#C9184A", "#FDF0A6")),
    "sonnenblume": PlantType(
        "sonnenblume", "Sonnenblume", "Schwer", "zink",
        bloom_at=2000, growth_per_click=0.4, growth_per_key=0.02,
        water_per_click=5.0, water_per_key=0.008, drain_hours=6,
        water_low=30, wilt_below=20,
        note="Braucht viel Wasser.", coin_mult=2.0,
        colors=("#F5C518",),
        palette=("#F5C518", "#F2A516", "#FFE36E", "#D35400", "#8E2C1E", "#FFF3B0")),
    "bonsai": PlantType(
        "bonsai", "Bonsai", "Sehr schwer", "schale",
        bloom_at=4000, growth_per_click=0.3, growth_per_key=0.015,
        water_per_click=4.0, water_per_key=0.004, drain_hours=8,
        water_low=30, water_high=80, wilt_below=20,
        stages=("Steckling", "Trieb", "Jungbaum", "Bäumchen", "Bonsai", "Knospen", "Kirschblüte"),
        note="Wächst nur gut bei 30–80 % Wasser.", coin_mult=3.0,
        colors=("#F7B7C8",),
        palette=("#F7B7C8", "#FFFFFF", "#F48FB1", "#E75480", "#FCE4EC")),
}
PLANT_ORDER = ["wiesenblume", "kaktus", "tulpe", "sonnenblume", "bonsai"]


@dataclass(frozen=True)
class Fertilizer:
    key: str
    name: str
    price: int
    boost: float      # zusätzliches Wachstum, 0.5 = +50 %
    water: float      # zusätzlicher Wasserverbrauch, 0.5 = +50 %
    minutes: int      # Wirkungsdauer
    icon: str         # heap, bottle, bag, jar
    color: str
    accent: str


FERTILIZERS = {
    "kompost": Fertilizer("kompost", "Kompost", 20, 0.15, 0.0, 120, "heap", "#6B4A2E", "#5FA84F"),
    "fluessig": Fertilizer("fluessig", "Flüssigdünger", 40, 0.30, 0.20, 60, "bottle", "#3E9E5A", "#2E7D46"),
    "hornspaene": Fertilizer("hornspaene", "Hornspäne", 70, 0.25, 0.0, 360, "bag", "#C9B28A", "#8A7456"),
    "blaukorn": Fertilizer("blaukorn", "Blaukorn", 90, 0.50, 0.50, 120, "bag", "#3B6BB5", "#7FA8E8"),
    "turbo": Fertilizer("turbo", "Turbo-Booster", 120, 1.00, 1.00, 30, "bottle", "#D64541", "#F5C518"),
    "wundermix": Fertilizer("wundermix", "Wundermix", 200, 0.75, 0.25, 180, "jar", "#8E44AD", "#F5C518"),
}
FERT_ORDER = ["kompost", "fluessig", "hornspaene", "blaukorn", "turbo", "wundermix"]


# ---------------------------------------------------------------- Helfer (Automatisierung)

@dataclass(frozen=True)
class Helper:
    key: str
    name: str
    price: int
    desc: str


HELPERS = {
    "tropf": Helper("tropf", "Tropfbewässerung", 250,
                    "Hält den Wasserstand automatisch bei mindestens 40 %."),
    "hummel": Helper("hummel", "Hummel", 300,
                     "Kommt etwa alle 10 Minuten vorbei und bringt einen Wachstumsschub."),
    "zwerg": Helper("zwerg", "Gartenzwerg", 400,
                    "Hilft alle 30 Sekunden mit: bringt Wachstum wie ein Mausklick."),
    "lampe": Helper("lampe", "Pflanzenlampe", 600,
                    "Dauerhaft +10 % Wachstum für alle Pflanzen."),
    "automat": Helper("automat", "Düngerautomat", 500,
                      "Kauft den zuletzt verwendeten Dünger automatisch nach, sobald er ausläuft."),
}
HELPER_ORDER = ["tropf", "hummel", "zwerg", "lampe", "automat"]
DRIP_MIN = 40.0               # Tropfbewässerung: Mindest-Wasserstand
DRIP_RATE = 20.0 / 60         # ... füllt 20 % pro Minute nach
BEE_INTERVAL = (480, 720)     # Hummel: alle 8–12 Minuten
BEE_BOOST = 0.005             # ... Anteil des Blütewerts
GNOME_INTERVAL = 30.0         # Gartenzwerg: alle 30 Sekunden
LAMP_BOOST = 0.10             # Pflanzenlampe: +10 %
PRESTIGE_BONUS = 0.10         # je Prestige-Stufe: +10 % Wachstum und Coins
FOCUS_MULT = 2.0              # Fokus-Timer: doppeltes Wachstum
FOCUS_PRESETS = (25, 45, 60)


# ---------------------------------------------------------------- Besucher (Sammelbuch)

@dataclass(frozen=True)
class Visitor:
    key: str
    name: str
    rarity: str
    weight: int
    move: str        # fly, crawl, sit, glow
    cond: str        # "", bloom, big, night
    hint: str


VISITORS = {
    "marienkaefer": Visitor("marienkaefer", "Marienkäfer", "häufig", 50, "crawl", "",
                            "Krabbelt gern auf Blättern herum."),
    "kohlweissling": Visitor("kohlweissling", "Kohlweissling", "häufig", 50, "fly", "",
                             "Flattert bei jeder Pflanze vorbei."),
    "biene": Visitor("biene", "Honigbiene", "häufig", 40, "fly", "bloom",
                     "Kommt nur zu blühenden Pflanzen."),
    "zitronenfalter": Visitor("zitronenfalter", "Zitronenfalter", "selten", 20, "fly", "",
                              "Ein seltener Gast, Geduld lohnt sich."),
    "libelle": Visitor("libelle", "Libelle", "selten", 18, "fly", "big",
                       "Zeigt sich erst bei grösseren Pflanzen."),
    "tagpfauenauge": Visitor("tagpfauenauge", "Tagpfauenauge", "selten", 15, "fly", "bloom",
                             "Liebt Blüten."),
    "rotkehlchen": Visitor("rotkehlchen", "Rotkehlchen", "sehr selten", 6, "sit", "big",
                           "Setzt sich manchmal auf den Topfrand grosser Pflanzen."),
    "gluehwuermchen": Visitor("gluehwuermchen", "Glühwürmchen", "sehr selten", 8, "glow", "night",
                              "Nur abends und nachts (20–6 Uhr) zu sehen."),
}
VISITOR_ORDER = ["marienkaefer", "kohlweissling", "biene", "zitronenfalter",
                 "libelle", "tagpfauenauge", "rotkehlchen", "gluehwuermchen"]
VISIT_DURATION = 30.0
VISIT_GREET_COINS = 3


# ---------------------------------------------------------------- Erfolge

@dataclass(frozen=True)
class Achievement:
    key: str
    period: str      # daily, weekly, general
    name: str
    desc: str
    target: int
    reward: int


ACHIEVEMENTS = [
    Achievement("d_keys", "daily", "Fleissige Finger", "2'000 Tasten heute", 2000, 15),
    Achievement("d_clicks", "daily", "Giesskanne", "20-mal klicken heute", 20, 10),
    Achievement("d_focus", "daily", "Fokussiert", "1 Fokus-Sitzung heute", 1, 20),
    Achievement("w_keys", "weekly", "Tastenmarathon", "20'000 Tasten diese Woche", 20000, 60),
    Achievement("w_growth", "weekly", "Wachstumsschub", "300 Wachstum diese Woche", 300, 60),
    Achievement("w_focus", "weekly", "Fokus-Woche", "5 Fokus-Sitzungen diese Woche", 5, 80),
    Achievement("g_bloom", "general", "Erste Blüte", "Eine Pflanze blühen lassen", 1, 50),
    Achievement("g_garden", "general", "Sammler", "5 Pflanzen im Gartenhaus", 5, 75),
    Achievement("g_prestige", "general", "Aufstieg", "Erste Prestige-Stufe erreichen", 1, 100),
    Achievement("g_species", "general", "Artenvielfalt", "Alle 5 Arten blühen lassen", 5, 200),
    Achievement("g_keys", "general", "Tastenmeister", "100'000 Tasten insgesamt", 100000, 150),
    Achievement("g_visitors", "general", "Naturfreund", "5 Besucherarten entdecken", 5, 100),
]

# Topfgeometrie: Höhe der Erdoberfläche, Erd-Ellipse, Wassertropfen (Mittelpunkt des Bauchs, Radius)
POTS = {
    "terrakotta": {"soil_y": 234, "soil_rx": 60, "soil_ry": 6.0, "drop_y": 292, "drop_r": 9.0},
    "beton":      {"soil_y": 248, "soil_rx": 44, "soil_ry": 4.5, "drop_y": 298, "drop_r": 8.5},
    "keramik":    {"soil_y": 244, "soil_rx": 40, "soil_ry": 4.5, "drop_y": 290, "drop_r": 7.5},
    "zink":       {"soil_y": 238, "soil_rx": 56, "soil_ry": 5.0, "drop_y": 288, "drop_r": 8.5},
    "schale":     {"soil_y": 290, "soil_rx": 78, "soil_ry": 3.5, "drop_y": 306, "drop_r": 5.0},
}


# Farben der Fenster Sprechblase, Shop und Gartenhaus (hell / dunkel)
THEMES = {
    "light": {
        "panel": (255, 255, 255, 232), "panel_border": (90, 90, 90, 200), "sep": (0, 0, 0, 40),
        "text": "#1E1E1E", "text2": "#555555", "text3": "#333333", "muted": "#777777",
        "cell": "#F7F7F4", "cell_border": "#C8C8C2", "active_bg": "#E6F4E6", "active_bg_hover": "#D9F0DC",
        "hover_bg": "#EEF7EE", "gold_bg": "#FFF6DA", "ok": "#2E7D32", "coin": "#9A6B00", "bad": "#C0392B",
        "bad_bg": "#FDECEA", "button_text": "#1E5E2A", "btn_bg": "#F4F4F0", "btn_bg_hover": "#EDEDE8",
        "btn_border": "#BDBDB6", "scroll": (0, 0, 0, 60), "white": "#FFFFFF",
    },
    "dark": {
        "panel": (36, 38, 42, 238), "panel_border": (150, 150, 150, 200), "sep": (255, 255, 255, 45),
        "text": "#E8E8E8", "text2": "#B4B4B4", "text3": "#D2D2D2", "muted": "#9A9A9A",
        "cell": "#2E3135", "cell_border": "#4A4E54", "active_bg": "#1F3A25", "active_bg_hover": "#28492F",
        "hover_bg": "#263A2B", "gold_bg": "#3D3420", "ok": "#72D183", "coin": "#E6B84A", "bad": "#FF7A6B",
        "bad_bg": "#4A2522", "button_text": "#A6E8B0", "btn_bg": "#33363A", "btn_bg_hover": "#3C4045",
        "btn_border": "#5A5F66", "scroll": (255, 255, 255, 70), "white": "#2E3135",
    },
}
_THEME = {"dark": False}


def T(key):
    """Farbe des aktuellen Farbschemas (Dunkelmodus ein/aus)."""
    v = THEMES["dark" if _THEME["dark"] else "light"][key]
    return QColor(*v) if isinstance(v, tuple) else QColor(v)


def stage_index(kind, growth):
    frac = growth / kind.bloom_at
    idx = 0
    for i, threshold in enumerate(STAGE_FRACTIONS):
        if frac >= threshold:
            idx = i
    return idx


def stage_name(kind, growth):
    frac = growth / kind.bloom_at
    name = kind.stages[0]
    for threshold, label in zip(STAGE_FRACTIONS, kind.stages):
        if frac >= threshold:
            name = label
    return name


# ---------------------------------------------------------------- Hilfsfunktionen

def fmt_int(n):
    """Tausendertrennzeichen nach Schweizer Schreibweise (1'234)."""
    return f"{int(n):,}".replace(",", "'")


def fmt_age(seconds):
    seconds = max(0, int(seconds))
    d, rest = divmod(seconds, 86400)
    h, rest = divmod(rest, 3600)
    m = rest // 60
    if d:
        return f"{d} T {h} h"
    if h:
        return f"{h} h {m} min"
    return f"{m} min"


def fmt_left(seconds):
    seconds = max(0, int(seconds))
    h, rest = divmod(seconds, 3600)
    m = rest // 60
    if h:
        return f"{h}:{m:02d} h"
    return f"{max(1, m) if seconds else 0} min"


def fmt_date(ts):
    return time.strftime("%d.%m.%Y", time.localtime(ts)) if ts else "–"


def fmt_datetime(ts):
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts)) if ts else "–"


def fert_description(fz):
    text = f"{fz.name}: Wachstum +{fz.boost * 100:.0f} % für {fmt_left(fz.minutes * 60)}"
    if fz.water:
        text += f", Wasserverbrauch +{fz.water * 100:.0f} %."
    else:
        text += ", kein Mehrverbrauch an Wasser."
    return text


def round_half_up(x):
    return int(x + 0.5)


def mix(c1, c2, f):
    f = max(0.0, min(1.0, f))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * f),
        int(c1.green() + (c2.green() - c1.green()) * f),
        int(c1.blue() + (c2.blue() - c1.blue()) * f),
    )


def bezier(p0, p1, p2, t):
    u = 1 - t
    return QPointF(u * u * p0.x() + 2 * u * t * p1.x() + t * t * p2.x(),
                   u * u * p0.y() + 2 * u * t * p1.y() + t * t * p2.y())


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    a, b, c, d = u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3
    return QPointF(a * p0.x() + b * p1.x() + c * p2.x() + d * p3.x(),
                   a * p0.y() + b * p1.y() + c * p2.y() + d * p3.y())


def drop_path(cx, cy, r):
    """Wassertropfen: runder Bauch um (cx, cy) mit Radius r, Spitze nach oben."""
    tip = QPointF(cx, cy - 2.3 * r)
    path = QPainterPath(tip)
    path.cubicTo(QPointF(cx + r * 0.3, cy - 1.6 * r), QPointF(cx + r, cy - 0.9 * r), QPointF(cx + r, cy))
    path.arcTo(QRectF(cx - r, cy - r, 2 * r, 2 * r), 0, -180)
    path.cubicTo(QPointF(cx - r, cy - 0.9 * r), QPointF(cx - r * 0.3, cy - 1.6 * r), tip)
    path.closeSubpath()
    return path


def water_status(kind, water):
    """Liefert (Text, ok) für den Wasserstand der Pflanze."""
    if water < kind.wilt_below:
        return "zu trocken", False
    if water > kind.water_high:
        return "zu nass", False
    if water < kind.water_low:
        return "knapp", True
    return "gut", True


def draw_coin(p, c, r):
    p.setPen(QPen(QColor("#B8860B"), max(0.8, r * 0.18)))
    p.setBrush(QColor("#F2C230"))
    p.drawEllipse(c, r, r)
    p.setPen(QPen(QColor("#D4A017"), max(0.6, r * 0.12)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(c, r * 0.6, r * 0.6)


def draw_seed_packet(p, center, size, gold, pulse=0.0):
    """Samentüte in einem Feld von 20 x 20 Einheiten; gold = Pflanze blüht, pulse 0..1 für das Leuchten."""
    p.save()
    p.translate(center.x() - size / 2, center.y() - size / 2)
    p.scale(size / 20, size / 20)
    if gold:
        from PyQt6.QtGui import QRadialGradient
        radius = 10 + 2.5 * pulse
        glow = QRadialGradient(QPointF(10, 10), radius)
        glow.setColorAt(0, QColor(242, 194, 48, int(110 + 90 * pulse)))
        glow.setColorAt(1, QColor(242, 194, 48, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(10, 10), radius, radius)
    paper = QColor("#F5D36A") if gold else QColor("#E3DCCB")
    edge = QColor("#A47A00") if gold else QColor("#8C8577")
    path = QPainterPath(QPointF(4, 5))
    for i in range(7):
        path.lineTo(4 + i * 2, 3 if i % 2 == 0 else 5)
    path.lineTo(16, 5)
    path.lineTo(16, 18)
    path.lineTo(4, 18)
    path.closeSubpath()
    p.setPen(QPen(edge, 0.9))
    p.setBrush(paper)
    p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#4C9A4A") if gold else QColor("#9AA59A"))
    p.drawRect(QRectF(9.5, 11, 1, 4))
    p.setBrush(QColor("#E85D75") if gold else QColor("#B5A9AB"))
    for k in range(5):
        a = math.radians(k * 72 - 90)
        p.drawEllipse(QPointF(10 + math.cos(a) * 1.8, 10 + math.sin(a) * 1.8), 1.4, 1.4)
    p.setBrush(QColor("#F7D046") if gold else QColor("#D8D3C4"))
    p.drawEllipse(QPointF(10, 10), 0.9, 0.9)
    p.restore()


def draw_fert_icon(p, fz, rect):
    """Düngersymbol in einem Feld von 36 x 36 Einheiten."""
    col, acc = QColor(fz.color), QColor(fz.accent)
    p.save()
    p.translate(rect.topLeft())
    p.scale(rect.width() / 36, rect.height() / 36)
    if fz.icon == "heap":
        mound = QPainterPath(QPointF(5, 31))
        mound.quadTo(QPointF(18, 8), QPointF(31, 31))
        mound.closeSubpath()
        p.setPen(QPen(col.darker(130), 1))
        p.setBrush(col)
        p.drawPath(mound)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col.darker(140))
        for x, y in ((12, 27), (17, 24), (23, 27), (20, 29), (14, 30)):
            p.drawEllipse(QPointF(x, y), 1.1, 1.1)
        p.setPen(round_pen(acc.darker(120), 1.4))
        p.drawLine(QPointF(18, 20), QPointF(18, 11))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        for angle in (-35, -145):
            p.save()
            p.translate(18, 13)
            p.rotate(angle)
            p.drawEllipse(QRectF(0, -1.6, 6, 3.2))
            p.restore()
    elif fz.icon == "bottle":
        body = QPainterPath()
        body.addRoundedRect(QRectF(10, 13, 16, 19), 4, 4)
        p.setPen(QPen(QColor(120, 130, 140), 1))
        p.setBrush(QColor(235, 242, 248))
        p.drawRect(QRectF(15, 8, 6, 6))
        p.drawPath(body)
        p.save()
        p.setClipPath(body)
        p.fillRect(QRectF(10, 19, 16, 14), col)
        p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(body)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawRoundedRect(QRectF(14, 4.5, 8, 4), 1, 1)
        if fz.key == "turbo":
            bolt = QPainterPath(QPointF(19.5, 19))
            for x, y in ((15, 26), (18, 26), (16.5, 31), (21, 24), (18, 24), (19.5, 19)):
                bolt.lineTo(x, y)
            p.setBrush(QColor("#FFF3B0"))
            p.drawPath(bolt)
        else:
            p.setBrush(QColor(255, 255, 255, 150))
            p.drawEllipse(QPointF(14, 23), 1.2, 3)
    elif fz.icon == "bag":
        bag = QPainterPath(QPointF(10, 11))
        bag.lineTo(26, 11)
        bag.quadTo(QPointF(29.5, 22), QPointF(27, 32))
        bag.quadTo(QPointF(18, 34.5), QPointF(9, 32))
        bag.quadTo(QPointF(6.5, 22), QPointF(10, 11))
        p.setPen(QPen(col.darker(140), 1))
        p.setBrush(col)
        p.drawPath(bag)
        p.setBrush(col.darker(115))
        p.drawRoundedRect(QRectF(9, 7, 18, 5), 1.5, 1.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawRoundedRect(QRectF(12, 17, 12, 10), 2, 2)
        p.setBrush(acc)
        for x, y in ((15, 20), (18.5, 22.5), (21, 19.5), (16.5, 24.5), (20.5, 25)):
            p.drawEllipse(QPointF(x, y), 1.2, 1.2)
    elif fz.icon == "jar":
        p.setPen(QPen(col.darker(140), 1))
        p.setBrush(col)
        p.drawRoundedRect(QRectF(9, 13, 18, 19), 5, 5)
        p.setBrush(acc.darker(115))
        p.drawRoundedRect(QRectF(8, 9, 20, 5), 1.5, 1.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawEllipse(QPointF(18, 22.5), 4.2, 4.2)
        for cx, cy, r in ((29, 8, 2.6), (7, 12, 2.0)):
            star = QPainterPath(QPointF(cx, cy - r))
            for x, y in ((cx + r * 0.3, cy - r * 0.3), (cx + r, cy), (cx + r * 0.3, cy + r * 0.3),
                         (cx, cy + r), (cx - r * 0.3, cy + r * 0.3), (cx - r, cy),
                         (cx - r * 0.3, cy - r * 0.3), (cx, cy - r)):
                star.lineTo(x, y)
            p.drawPath(star)
    p.restore()


def draw_star(p, c, r, fill="#F2C230", edge="#B8860B"):
    path = QPainterPath()
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr = r if i % 2 == 0 else r * 0.45
        pt = QPointF(c.x() + math.cos(a) * rr, c.y() + math.sin(a) * rr)
        if i == 0:
            path.moveTo(pt)
        else:
            path.lineTo(pt)
    path.closeSubpath()
    p.setPen(QPen(QColor(edge), 0.8))
    p.setBrush(QColor(fill))
    p.drawPath(path)


def draw_helper_icon(p, key, rect):
    """Helfersymbol in einem Feld von 36 x 36 Einheiten."""
    p.save()
    p.translate(rect.topLeft())
    p.scale(rect.width() / 36, rect.height() / 36)
    nopen = Qt.PenStyle.NoPen
    if key == "tropf":
        pen = QPen(QColor("#4F6B4A"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        tube = QPainterPath(QPointF(4, 8))
        tube.cubicTo(QPointF(16, 6), QPointF(20, 20), QPointF(26, 20))
        p.drawPath(tube)
        p.setPen(nopen)
        p.setBrush(QColor("#2E7D46"))
        p.drawRoundedRect(QRectF(24, 17, 6, 6), 1.5, 1.5)
        p.setBrush(QColor("#4FA3E0"))
        p.drawPath(_drop_path(27, 30, 2.6))
        p.setBrush(QColor("#6B4A2E"))
        p.drawRoundedRect(QRectF(6, 32, 26, 3), 1.5, 1.5)
    elif key == "hummel":
        draw_visitor(p, "hummel", QPointF(18, 19), 1.9, 0.3)
    elif key == "zwerg":
        _draw_gnome(p, QPointF(18, 34), 1.25)
    elif key == "lampe":
        cone = QPainterPath(QPointF(11, 16))
        cone.lineTo(25, 16)
        cone.lineTo(33, 34)
        cone.lineTo(3, 34)
        cone.closeSubpath()
        p.setPen(nopen)
        p.setBrush(QColor(255, 220, 90, 90))
        p.drawPath(cone)
        p.setPen(QPen(QColor("#555555"), 1.2))
        p.drawLine(QPointF(18, 2), QPointF(18, 8))
        p.setPen(QPen(QColor("#1F4D2B"), 0.8))
        p.setBrush(QColor("#2E6B3C"))
        shade = QPainterPath(QPointF(12, 8))
        shade.lineTo(24, 8)
        shade.lineTo(28, 16)
        shade.lineTo(8, 16)
        shade.closeSubpath()
        p.drawPath(shade)
        p.setPen(nopen)
        p.setBrush(QColor("#FFE36E"))
        p.drawEllipse(QPointF(18, 17), 3.5, 2)
    elif key == "automat":
        p.setPen(QPen(QColor("#5F6870"), 1))
        p.setBrush(QColor("#AEB6BD"))
        p.drawRoundedRect(QRectF(8, 4, 20, 20), 3, 3)
        p.setBrush(QColor("#E6EEF4"))
        p.drawRoundedRect(QRectF(12, 7, 12, 9), 2, 2)
        p.setPen(nopen)
        p.setBrush(QColor("#3B6BB5"))
        for x, y in ((14.5, 13), (17.5, 14), (20.5, 12.5), (16, 11), (21, 14.5)):
            p.drawEllipse(QPointF(x, y), 1.1, 1.1)
        p.setBrush(QColor("#5F6870"))
        p.drawRect(QRectF(16, 24, 4, 4))
        p.setBrush(QColor("#3B6BB5"))
        for x, y in ((18, 30), (16.5, 33), (19.5, 34)):
            p.drawEllipse(QPointF(x, y), 1.1, 1.1)
    p.restore()


def _drop_path(cx, cy, r):
    tip = QPointF(cx, cy - 2.3 * r)
    path = QPainterPath(tip)
    path.cubicTo(QPointF(cx + r * 0.3, cy - 1.6 * r), QPointF(cx + r, cy - 0.9 * r), QPointF(cx + r, cy))
    path.arcTo(QRectF(cx - r, cy - r, 2 * r, 2 * r), 0, -180)
    path.cubicTo(QPointF(cx - r, cy - 0.9 * r), QPointF(cx - r * 0.3, cy - 1.6 * r), tip)
    path.closeSubpath()
    return path


def _draw_gnome(p, feet, s, hop=0.0):
    """Gartenzwerg, Füsse bei 'feet', Grösse s (1 = ca. 26 px hoch)."""
    p.save()
    p.translate(feet.x(), feet.y() - hop * 5)
    p.scale(s, s)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#5A3A1E"))
    p.drawEllipse(QPointF(-3, -0.8), 2.6, 1.3)
    p.drawEllipse(QPointF(3, -0.8), 2.6, 1.3)
    body = QPainterPath(QPointF(-6, -1))
    body.lineTo(6, -1)
    body.lineTo(4, -12)
    body.lineTo(-4, -12)
    body.closeSubpath()
    p.setBrush(QColor("#2F5FA8"))
    p.drawPath(body)
    p.setBrush(QColor("#6B4A2E"))
    p.drawRect(QRectF(-5.5, -5, 11, 1.6))
    p.setBrush(QColor("#F2C9A0"))
    p.drawEllipse(QPointF(0, -15), 4, 4)
    beard = QPainterPath(QPointF(-4.2, -15))
    beard.quadTo(QPointF(0, -3), QPointF(4.2, -15))
    beard.closeSubpath()
    p.setBrush(QColor("#F4F4F0"))
    p.drawPath(beard)
    p.setBrush(QColor("#E08A6A"))
    p.drawEllipse(QPointF(0, -15.5), 1.3, 1.1)
    hat = QPainterPath(QPointF(-4.8, -17))
    hat.lineTo(4.8, -17)
    hat.quadTo(QPointF(2, -24), QPointF(-1, -27))
    hat.closeSubpath()
    p.setBrush(QColor("#D62828"))
    p.drawPath(hat)
    p.restore()


def draw_visitor(p, key, pos, scale, t, alpha=1.0, silhouette=False, flip=False):
    """Besucher-Figur (ca. 20 x 20 Einheiten) an pos."""
    def c(hex_or_rgba):
        if silhouette:
            return QColor(255, 255, 255, 55) if _THEME["dark"] else QColor(0, 0, 0, 70)
        return QColor(*hex_or_rgba) if isinstance(hex_or_rgba, tuple) else QColor(hex_or_rgba)

    p.save()
    p.translate(pos)
    p.scale(-scale if flip else scale, scale)
    p.setOpacity(p.opacity() * alpha)
    p.setPen(Qt.PenStyle.NoPen)
    flap = 0.35 + 0.65 * abs(math.sin(t * 11))

    def butterfly(upper, lower, spots):
        for side in (-1, 1):
            p.save()
            p.scale(side * flap, 1)
            p.setBrush(c(upper))
            p.drawEllipse(QRectF(0.4, -7, 7.5, 7))
            p.setBrush(c(lower))
            p.drawEllipse(QRectF(0.4, -0.8, 5.6, 5.8))
            for sx, sy, sr, col in spots:
                p.setBrush(c(col))
                p.drawEllipse(QPointF(sx, sy), sr, sr)
            p.restore()
        p.setBrush(c("#2B2521"))
        p.drawEllipse(QPointF(0, 0), 1.0, 4.8)
        p.setPen(QPen(c("#2B2521"), 0.5))
        p.drawLine(QPointF(0, -4.5), QPointF(-2, -8))
        p.drawLine(QPointF(0, -4.5), QPointF(2, -8))
        p.setPen(Qt.PenStyle.NoPen)

    if key == "kohlweissling":
        butterfly("#F4F4EE", "#EDEDE4", [(5.5, -5.5, 1.1, "#555555"), (4, -3, 0.8, "#333333")])
    elif key == "zitronenfalter":
        butterfly("#F3E24A", "#EFD93C", [(4, -3.5, 0.8, "#E8892B"), (3, 2, 0.6, "#E8892B")])
    elif key == "tagpfauenauge":
        butterfly("#B5311F", "#8E2718", [(5, -4.5, 1.9, "#F2C230"), (5, -4.5, 1.3, "#2E5FA8"),
                                         (5, -4.5, 0.6, "#1A1A1A"), (3.3, 2.2, 1.1, "#3A3A3A")])
    elif key in ("biene", "hummel"):
        big = key == "hummel"
        wing = abs(math.sin(t * 25))
        p.setBrush(c((255, 255, 255, 170)))
        p.drawEllipse(QRectF(-3, -5.5 - 2 * wing, 4, 4 + 2 * wing))
        p.drawEllipse(QRectF(0, -5 - 2 * wing, 4, 4 + 2 * wing))
        body = QPainterPath()
        body.addEllipse(QPointF(0, 0), 5.5 if big else 4.5, 3.6 if big else 2.8)
        p.setBrush(c("#F2B705" if big else "#F2C230"))
        p.drawPath(body)
        p.save()
        p.setClipPath(body)
        p.setBrush(c("#1E1E1E"))
        for x in ((-2.5, 0.5, 3.5) if big else (-1.5, 1.5)):
            p.drawRect(QRectF(x, -4, 1.4, 8))
        p.restore()
        p.setBrush(c("#1E1E1E"))
        p.drawEllipse(QPointF(-5.5 if big else -4.6, 0), 2.2, 2.0)
    elif key == "libelle":
        wing = 0.7 + 0.3 * abs(math.sin(t * 20))
        p.setBrush(c((190, 225, 245, 150)))
        for ang in (-65, -115, 60, 120):
            p.save()
            p.translate(3, 0)
            p.rotate(ang)
            p.drawEllipse(QRectF(0, -1.1, 8 * wing, 2.2))
            p.restore()
        p.setPen(round_pen(c("#2E86C1"), 1.5))
        p.drawLine(QPointF(-9, 0), QPointF(5, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("#1F5F3A"))
        p.drawEllipse(QPointF(6.5, 0), 1.9, 1.9)
    elif key == "marienkaefer":
        p.setBrush(c("#1E1E1E"))
        p.drawEllipse(QPointF(0, -4), 2.2, 1.8)
        p.setBrush(c("#D62828"))
        p.drawEllipse(QPointF(0, 0), 4, 4.2)
        p.setPen(QPen(c("#1E1E1E"), 0.6))
        p.drawLine(QPointF(0, -3.8), QPointF(0, 4))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("#1E1E1E"))
        for x, y in ((-2, -1.5), (2, -1.5), (-2.2, 1.8), (2.2, 1.8)):
            p.drawEllipse(QPointF(x, y), 0.9, 0.9)
    elif key == "rotkehlchen":
        p.setPen(QPen(c("#6B4A2E"), 0.8))
        p.drawLine(QPointF(-1, 4), QPointF(-1.5, 7))
        p.drawLine(QPointF(1.5, 4), QPointF(1.5, 7))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("#7A6650"))
        p.drawEllipse(QPointF(1, 0), 6, 5)
        tail = QPainterPath(QPointF(6, -1))
        tail.lineTo(11, -3)
        tail.lineTo(10.5, 1.5)
        tail.closeSubpath()
        p.drawPath(tail)
        p.drawEllipse(QPointF(-4, -4.5), 3.4, 3.2)
        p.setBrush(c("#E4572E"))
        p.drawEllipse(QPointF(-3, 0), 3.8, 3.8)
        p.drawEllipse(QPointF(-5, -3.5), 2, 1.8)
        p.setBrush(c("#1E1E1E"))
        p.drawEllipse(QPointF(-5, -5.2), 0.7, 0.7)
        beak = QPainterPath(QPointF(-7, -5))
        beak.lineTo(-9.5, -4.2)
        beak.lineTo(-7, -3.6)
        beak.closeSubpath()
        p.setBrush(c("#3A2A1A"))
        p.drawPath(beak)
    elif key == "gluehwuermchen":
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        if not silhouette:
            from PyQt6.QtGui import QRadialGradient
            g = QRadialGradient(QPointF(0, 1.5), 8)
            g.setColorAt(0, QColor(220, 255, 120, int(120 + 120 * pulse)))
            g.setColorAt(1, QColor(220, 255, 120, 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(0, 1.5), 8, 8)
        p.setBrush(c("#3A3326"))
        p.drawEllipse(QPointF(0, -1.5), 1.8, 3)
        p.setBrush(c((235, 255, 140, int(160 + 90 * pulse))))
        p.drawEllipse(QPointF(0, 2), 1.7, 1.8)
    p.restore()


def fit_font(p, base, text, width, min_px=7):
    """Setzt die grösste Schrift (höchstens base), in die text innerhalb width passt."""
    f = QFont(base)
    p.setFont(f)
    while p.fontMetrics().horizontalAdvance(text) > width and f.pixelSize() > min_px:
        f.setPixelSize(f.pixelSize() - 1)
        p.setFont(f)
    return f


def round_pen(color, width):
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


# ---------------------------------------------------------------- Tastatur

class KeyCounter:
    """Zählt Tastendrücke systemweit in einem Hintergrund-Thread (nur Anzahl)."""

    def __init__(self):
        self._n = 0
        self._lock = threading.Lock()

    def add(self, n=1):
        with self._lock:
            self._n += n

    def take(self):
        with self._lock:
            n, self._n = self._n, 0
        return n

    def start(self):
        if sys.platform.startswith("linux") and self._start_evdev():
            return "evdev"
        return self._start_pynput()

    def _start_evdev(self):
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            return None
        devices = []
        for path in evdev.list_devices():  # listet nur lesbare Geräte
            try:
                dev = evdev.InputDevice(path)
            except OSError:
                continue
            keys = dev.capabilities().get(ecodes.EV_KEY, [])
            if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                devices.append(dev)
            else:
                dev.close()
        if not devices:
            return None

        def run():
            import selectors
            sel = selectors.DefaultSelector()
            for d in devices:
                sel.register(d, selectors.EVENT_READ)
            while sel.get_map():
                for key, _ in sel.select():
                    try:
                        for ev in key.fileobj.read():
                            if ev.type == ecodes.EV_KEY and ev.value == 1:
                                self.add()
                    except BlockingIOError:
                        continue
                    except OSError:
                        sel.unregister(key.fileobj)

        threading.Thread(target=run, daemon=True).start()
        return "evdev"

    def _start_pynput(self):
        try:
            from pynput import keyboard
            listener = keyboard.Listener(on_press=lambda _k: self.add())
            listener.daemon = True
            listener.start()
        except Exception:
            return None
        return "pynput"


# ---------------------------------------------------------------- Sprechblase

class Bubble(QWidget):
    """Eigenständiges, verschiebbares Fenster mit dem Live-Status der Pflanze."""

    def __init__(self, plant):
        super().__init__()
        self.plant = plant
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(BUBBLE_W, BUBBLE_H)
        self.setMouseTracking(True)
        self.place_window()

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.plant.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def icon_rects(self):
        """Obere Reihe: Pflanzen (gross), untere Reihe: Werkzeuge (klein)."""
        n = len(PLANT_ORDER)
        total = n * ICON + (n - 1) * ICON_GAP
        x0 = (self.width() - total) / 2
        y0 = 7 + BUBBLE_ROWS_H + 9
        rects = [(key, QRectF(x0 + i * (ICON + ICON_GAP), y0, ICON, ICON))
                 for i, key in enumerate(PLANT_ORDER)]
        m = len(TOOL_ORDER)
        tt = m * TOOL + (m - 1) * TOOL_GAP
        tx0 = (self.width() - tt) / 2
        ty = y0 + ICON + 7
        rects += [(key, QRectF(tx0 + i * (TOOL + TOOL_GAP), ty, TOOL, TOOL))
                  for i, key in enumerate(TOOL_ORDER)]
        return rects

    def icon_at(self, pos):
        for key, r in self.icon_rects():
            if r.contains(pos):
                return key
        return None

    def place_window(self):
        pos = self.plant.state.get("bubble_pos")
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        else:
            self.move(self.plant.x() + (WIN_W - BUBBLE_W) // 2,
                      max(0, self.plant.y() - BUBBLE_H + 40))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            key = self.icon_at(e.position())
            if key in TOOL_ORDER:
                self.plant.toggle_window(key)
                return
            if key:
                self.plant.select_plant(key)
                return
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.plant.set_bubble(False)
        elif e.button() == Qt.MouseButton.RightButton:
            self.plant.show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        over = self.icon_at(e.position()) is not None
        self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)

    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            key = self.icon_at(QPointF(e.pos()))
            if key == "shop":
                QToolTip.showText(e.globalPos(),
                                  f"Dünger-Shop\nCoins: {fmt_int(self.plant.state.get('coins', 0))} (+{PASSIVE_PER_HOUR} pro Stunde)", self)
            elif key == "garden":
                n = len(self.plant.state.get("garden", []))
                QToolTip.showText(e.globalPos(), f"Gartenhaus (Ehrenhalle)\n{n} Pflanze(n)", self)
            elif key == "ach":
                QToolTip.showText(e.globalPos(), f"Erfolge\n{self.plant.ach_summary()}", self)
            elif key == "focus":
                QToolTip.showText(e.globalPos(), f"Fokus-Timer\n{self.plant.focus_summary()}", self)
            elif key == "book":
                n = len(self.plant.state.get("book", {}))
                QToolTip.showText(e.globalPos(), f"Besucher-Sammelbuch\n{n} / {len(VISITORS)} entdeckt", self)
            elif key:
                k = PLANT_TYPES[key]
                pst = self.plant.state["plants"].get(key)
                text = f"{k.name} ({k.difficulty})"
                if pst:
                    text += f"\n{stage_name(k, pst['growth'])}"
                QToolTip.showText(e.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def paintEvent(self, _e):
        k, s = self.plant.kind, self.plant.ps
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(T("panel_border"), 1.2))
        p.setBrush(T("panel"))
        p.drawRoundedRect(rect, 10, 10)

        rows = [
            ("Pflanze", k.name),
            ("Stadium", stage_name(k, s["growth"])),
            ("Wachstum", f"{s['growth']:.1f} / {fmt_int(k.bloom_at)}"),
            ("Wasser", f"{s['water']:.0f} % · {water_status(k, s['water'])[0]}"),
            ("Dünger", self.plant.fert_summary()),
            ("Prestige", self.plant.prestige_summary()),
            ("Klicks", fmt_int(s["clicks_total"])),
            ("Tasten", fmt_int(s["keys_total"]) if k.growth_per_key > 0 else "– (nur Klicks)"),
            ("Alter", fmt_age(time.time() - s["created"])),
            ("Coins", fmt_int(self.plant.state.get("coins", 0))),
        ]
        font = QFont(self.font())
        font.setPixelSize(12)
        p.setFont(font)
        inner = QRectF(rect.left() + 10, rect.top() + 6, rect.width() - 20, BUBBLE_ROWS_H)
        line_h = inner.height() / len(rows)
        for i, (label, value) in enumerate(rows):
            r = QRectF(inner.left(), inner.top() + i * line_h, inner.width(), line_h)
            p.setPen(T("text2"))
            p.drawText(r, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            ok = label != "Wasser" or water_status(k, s["water"])[1]
            color = T("text") if ok else T("bad")
            if label == "Dünger" and value != "–":
                color = T("ok")
            elif label == "Prestige" and value != "–":
                color = T("coin")
            elif label == "Coins":
                color = T("coin")
            p.setPen(color)
            vr = QRectF(r)
            if label == "Coins":
                draw_coin(p, QPointF(r.right() - 5, r.center().y()), 5)
                p.setPen(color)
                vr.setRight(r.right() - 14)
            label_w = p.fontMetrics().horizontalAdvance(label) + 8
            fit_font(p, font, value, vr.width() - label_w, min_px=8)
            p.drawText(vr, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, value)
            p.setFont(font)

        sep_y = inner.bottom() + 3
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(rect.left() + 10, sep_y), QPointF(rect.right() - 10, sep_y))

        current = self.plant.state["current"]
        prestige = self.plant.state.get("prestige", {})
        for key, r in self.icon_rects():
            if key in TOOL_ORDER:
                win = self.plant.windows.get(key) if hasattr(self.plant, "windows") else None
                is_open = win is not None and win.isVisible()
                p.setPen(QPen(QColor("#D4A017"), 2.0) if is_open else QPen(T("cell_border"), 1))
                p.setBrush(T("gold_bg") if is_open else T("cell"))
                p.drawRoundedRect(r, 5, 5)
                self.draw_icon(p, key, r)
                if key == "focus" and self.plant.focus:
                    rem, total = self.plant.focus_remaining()
                    pen = QPen(QColor("#2E9E44"), 2.4)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    p.setPen(pen)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawArc(r.adjusted(1, 1, -1, -1), 90 * 16, -int(360 * 16 * (1 - rem / total)))
                if key == "ach" and self.plant.state.get("ach_new", 0) > 0:
                    c = QPointF(r.right() - 2, r.top() + 2)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor("#D64541"))
                    p.drawEllipse(c, 6, 6)
                    bf = QFont(font)
                    bf.setPixelSize(9)
                    bf.setBold(True)
                    p.setFont(bf)
                    p.setPen(QColor("#FFFFFF"))
                    p.drawText(QRectF(c.x() - 6, c.y() - 6, 12, 12), Qt.AlignmentFlag.AlignCenter,
                               str(min(9, self.plant.state["ach_new"])))
                    p.setFont(font)
                continue
            active = key == current
            p.setPen(QPen(QColor("#2E9E44"), 2.2) if active else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if active else T("cell"))
            p.drawRoundedRect(r, 6, 6)
            self.draw_icon(p, key, r)
            lvl = prestige.get(key, 0)
            if lvl:
                c = QPointF(r.right() - 4, r.bottom() - 4)
                draw_star(p, c, 6.5)
                bf = QFont(font)
                bf.setPixelSize(8)
                bf.setBold(True)
                p.setFont(bf)
                p.setPen(QColor("#5A3A00"))
                p.drawText(QRectF(c.x() - 5, c.y() - 4.5, 10, 10), Qt.AlignmentFlag.AlignCenter, str(min(9, lvl)))
                p.setFont(font)
        p.end()

    # ---------- Pflanzensymbole (30 x 30 Einheiten) ----------

    @staticmethod
    def _trap(p, color, tx1, tx2, ty, bx1, bx2, by):
        path = QPainterPath(QPointF(tx1, ty))
        path.lineTo(tx2, ty)
        path.lineTo(bx2, by)
        path.lineTo(bx1, by)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)

    @staticmethod
    def _leaf(p, x, y, angle, length, width, color):
        p.save()
        p.translate(x, y)
        p.rotate(angle)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QRectF(0, -width / 2, length, width))
        p.restore()

    def draw_icon(self, p, key, r):
        p.save()
        p.translate(r.topLeft())
        p.scale(r.width() / 30, r.height() / 30)
        p.setClipRect(QRectF(1, 1, 28, 28))
        green = QColor("#3FA34D")
        nopen = Qt.PenStyle.NoPen

        if key == "wiesenblume":
            self._trap(p, QColor("#C8693B"), 9, 21, 21, 11, 19, 28)
            p.setBrush(QColor("#DB8356"))
            p.drawRoundedRect(QRectF(8, 19.5, 14, 3), 1, 1)
            p.setPen(round_pen(QColor("#2F7D3A"), 1.4))
            p.drawLine(QPointF(15, 20), QPointF(15, 9))
            self._leaf(p, 15, 16, -30, 6, 3, green)
            self._leaf(p, 15, 14, -150, 5.5, 2.8, green)
            p.setPen(nopen)
            p.setBrush(QColor("#E85D75"))
            for i in range(5):
                a = math.radians(i * 72 - 90)
                p.drawEllipse(QPointF(15 + math.cos(a) * 2.6, 8 + math.sin(a) * 2.6), 2.1, 2.1)
            p.setBrush(QColor("#F7D046"))
            p.drawEllipse(QPointF(15, 8), 1.3, 1.3)

        elif key == "kaktus":
            self._trap(p, QColor("#A5A5A0"), 10, 20, 22, 11, 19, 28)
            p.setBrush(QColor("#C8C8C3"))
            p.drawRoundedRect(QRectF(9, 21, 12, 2.5), 0.8, 0.8)
            body = QColor("#3E8E4E")
            p.setPen(round_pen(body, 3.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            arm = QPainterPath(QPointF(15, 16))
            arm.lineTo(9.5, 16)
            arm.lineTo(9.5, 11)
            p.drawPath(arm)
            arm = QPainterPath(QPointF(15, 13.5))
            arm.lineTo(20.5, 13.5)
            arm.lineTo(20.5, 9)
            p.drawPath(arm)
            p.setPen(nopen)
            p.setBrush(body)
            p.drawRoundedRect(QRectF(12, 7, 6, 15), 3, 3)
            p.setBrush(QColor("#FF6FA8"))
            p.drawEllipse(QPointF(15, 6.8), 1.9, 1.9)

        elif key == "tulpe":
            self._leaf(p, 14, 21, -108, 11, 2.8, QColor("#4C9A4A"))
            self._leaf(p, 16, 21, -72, 10, 2.8, QColor("#4C9A4A"))
            p.setPen(round_pen(QColor("#3C7F3A"), 1.2))
            p.drawLine(QPointF(15, 21), QPointF(15, 10))
            head = QPainterPath(QPointF(12, 10))
            head.cubicTo(QPointF(11.5, 7), QPointF(12, 5.5), QPointF(12.8, 4.5))
            head.lineTo(14, 6)
            head.lineTo(15, 4)
            head.lineTo(16, 6)
            head.lineTo(17.2, 4.5)
            head.cubicTo(QPointF(18, 5.5), QPointF(18.5, 7), QPointF(18, 10))
            head.quadTo(QPointF(15, 11.5), QPointF(12, 10))
            p.setPen(nopen)
            p.setBrush(QColor("#E8333A"))
            p.drawPath(head)
            p.setPen(QPen(QColor("#C8C8C0"), 0.6))
            p.setBrush(QColor("#F6F6F2"))
            p.drawRoundedRect(QRectF(10, 21, 10, 7), 2, 2)
            p.fillRect(QRectF(10.3, 23, 9.4, 1.4), QColor("#3B6BB5"))

        elif key == "sonnenblume":
            p.setPen(round_pen(QColor("#3F7F30"), 1.5))
            p.drawLine(QPointF(15, 21), QPointF(15, 11))
            self._leaf(p, 15, 17, -20, 6, 3.6, QColor("#4E9A3E"))
            self._leaf(p, 15, 15, -160, 5, 3.2, QColor("#4E9A3E"))
            p.setPen(nopen)
            p.setBrush(QColor("#F5C518"))
            for i in range(12):
                p.save()
                p.translate(15, 9)
                p.rotate(i * 30)
                p.drawEllipse(QRectF(2.4, -1.1, 3.6, 2.2))
                p.restore()
            p.setBrush(QColor("#5A3A1E"))
            p.drawEllipse(QPointF(15, 9), 2.8, 2.8)
            self._trap(p, QColor("#A7B0B8"), 9, 21, 21, 11, 19, 28)
            p.setBrush(QColor("#D3DAE0"))
            p.drawRoundedRect(QRectF(8, 20, 14, 2.5), 1, 1)

        elif key == "ach":
            gold, edge = QColor("#E0A800"), QColor("#8A6200")
            p.setPen(QPen(edge, 1.3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(5, 7, 7, 8), 90 * 16, 180 * 16)
            p.drawArc(QRectF(18, 7, 7, 8), -90 * 16, 180 * 16)
            cup = QPainterPath(QPointF(8.5, 6))
            cup.lineTo(21.5, 6)
            cup.quadTo(QPointF(21.5, 17), QPointF(15, 18))
            cup.quadTo(QPointF(8.5, 17), QPointF(8.5, 6))
            p.setPen(QPen(edge, 0.9))
            p.setBrush(gold)
            p.drawPath(cup)
            p.drawRect(QRectF(13.8, 18, 2.4, 4))
            p.drawRoundedRect(QRectF(10, 22, 10, 3.5), 1, 1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 140))
            p.drawEllipse(QPointF(12, 10), 1.2, 2.6)

        elif key == "focus":
            p.setPen(QPen(QColor("#555555"), 1.2))
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QPointF(15, 16), 10, 10)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#D64541"))
            p.drawRoundedRect(QRectF(12.5, 3, 5, 3), 1, 1)
            p.setPen(round_pen(QColor("#333333"), 1.6))
            p.drawLine(QPointF(15, 16), QPointF(15, 9.5))
            p.drawLine(QPointF(15, 16), QPointF(19.5, 18))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#4C9A4A"))
            p.drawEllipse(QPointF(15, 16), 1.4, 1.4)

        elif key == "book":
            p.setPen(QPen(QColor("#2E5A2E"), 0.9))
            p.setBrush(QColor("#F4F1E6"))
            p.drawRect(QRectF(9, 6.5, 15, 19))
            p.setBrush(QColor("#4E8B4E"))
            p.drawRoundedRect(QRectF(7, 5, 15, 20), 1.5, 1.5)
            p.setBrush(QColor("#3B6E3B"))
            p.drawRect(QRectF(7, 5, 3, 20))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#F3E24A"))
            p.drawEllipse(QRectF(11.5, 11, 4.5, 4))
            p.drawEllipse(QRectF(16.5, 11, 4.5, 4))
            p.setBrush(QColor("#EFD93C"))
            p.drawEllipse(QRectF(12.5, 14.5, 3.5, 3.2))
            p.drawEllipse(QRectF(16.5, 14.5, 3.5, 3.2))
            p.setBrush(QColor("#2B2521"))
            p.drawRect(QRectF(15.8, 11, 0.9, 6.5))

        elif key == "garden":
            frame = QPen(QColor("#3E6E4A"), 1.1)
            house = QPainterPath(QPointF(5, 15))
            house.lineTo(15, 6)
            house.lineTo(25, 15)
            house.lineTo(25, 27)
            house.lineTo(5, 27)
            house.closeSubpath()
            p.setPen(frame)
            p.setBrush(QColor("#D6F0EC"))
            p.drawPath(house)
            p.drawLine(QPointF(5, 15), QPointF(25, 15))
            p.drawLine(QPointF(11, 15), QPointF(11, 27))
            p.drawLine(QPointF(19, 15), QPointF(19, 27))
            p.drawLine(QPointF(15, 6), QPointF(15, 15))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#E85D75"))
            p.drawEllipse(QPointF(8, 23), 1.6, 1.6)
            p.setBrush(QColor("#F5C518"))
            p.drawEllipse(QPointF(22, 22.5), 1.6, 1.6)
            p.setBrush(QColor("#4C9A4A"))
            p.drawRect(QRectF(7.4, 24, 1.2, 3))
            p.drawRect(QRectF(21.4, 23.5, 1.2, 3.5))
            p.setBrush(QColor("#8A6A4A"))
            p.drawRect(QRectF(12.5, 21, 5, 6))

        elif key == "shop":
            p.setPen(QPen(QColor("#7A3206"), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(10.5, 5.5, 9, 9), 0, 180 * 16)
            p.setPen(QPen(QColor("#7A3206"), 0.8))
            p.setBrush(QColor("#C2540F"))
            p.drawRoundedRect(QRectF(7, 10, 16, 16), 2, 2)
            draw_coin(p, QPointF(18.5, 21.5), 4.6)

        elif key == "bonsai":
            bark = QColor("#6B4A32")
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(round_pen(bark, 2.2))
            trunk = QPainterPath(QPointF(14, 24))
            trunk.cubicTo(QPointF(18, 19), QPointF(11, 15), QPointF(15, 11))
            p.drawPath(trunk)
            p.setPen(round_pen(bark, 1.1))
            p.drawLine(QPointF(14.8, 16.5), QPointF(20.5, 14))
            p.drawLine(QPointF(13.8, 18), QPointF(9.5, 16))
            p.setPen(nopen)
            p.setBrush(QColor("#355F2C"))
            p.drawEllipse(QPointF(15, 9.5), 5, 3)
            p.drawEllipse(QPointF(20.8, 13.2), 3.6, 2.2)
            p.drawEllipse(QPointF(9.2, 15.2), 3.3, 2)
            p.setBrush(QColor("#F7B7C8"))
            for x, y in ((13, 9), (16.5, 8.5), (21.5, 12.8), (8.6, 14.8), (15.5, 10.8)):
                p.drawEllipse(QPointF(x, y), 0.9, 0.9)
            self._trap(p, QColor("#2F5286"), 5, 25, 24, 7, 23, 27.5)
            p.setBrush(QColor("#4A74B0"))
            p.drawRoundedRect(QRectF(4, 23, 22, 1.8), 0.8, 0.8)
        p.restore()


# ---------------------------------------------------------------- Dünger-Shop

class Shop(QWidget):
    """Eigenständiges, verschiebbares Shop-Fenster im Stil der Sprechblase."""

    COLS = 3

    def __init__(self, plant):
        super().__init__()
        self.plant = plant
        self.hover = None
        self.tab = "duenger"
        self.message = ""
        self.message_ok = True
        self.message_until = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(SHOP_W, SHOP_H)
        self.setMouseTracking(True)
        self.place_window()

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.plant.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def place_window(self):
        pos = self.plant.state.get("shop_pos")
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        else:
            self.move(max(0, self.plant.x() - SHOP_W - 10), max(0, self.plant.y()))

    def tab_rects(self):
        w = (SHOP_W - 24 - 6) / 2
        return [("duenger", QRectF(12, 57, w, 22)), ("helfer", QRectF(18 + w, 57, w, 22))]

    def cell_rects(self):
        gap, x0, y0 = 6, 12, 88
        cw = (SHOP_W - 2 * x0 - (self.COLS - 1) * gap) / self.COLS
        ch = 76
        rects = []
        for i, key in enumerate(FERT_ORDER if self.tab == "duenger" else HELPER_ORDER):
            row, col = divmod(i, self.COLS)
            rects.append((key, QRectF(x0 + col * (cw + gap), y0 + row * (ch + gap), cw, ch)))
        return rects

    def close_rect(self):
        return QRectF(SHOP_W - 28, 8, 18, 18)

    def cell_at(self, pos):
        for key, r in self.cell_rects():
            if r.contains(pos):
                return key
        return None

    def showEvent(self, e):
        super().showEvent(e)
        self.plant.bubble.update()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.plant.bubble.update()

    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() == Qt.MouseButton.LeftButton:
            if self.close_rect().contains(pos):
                self.hide()
                return
            for tab, r in self.tab_rects():
                if r.contains(pos):
                    self.tab, self.hover, self.message = tab, None, ""
                    self.update()
                    return
            key = self.cell_at(pos)
            if key:
                if self.tab == "duenger":
                    ok, msg = self.plant.buy_fertilizer(key)
                else:
                    ok, msg = self.plant.helper_action(key)
                self.message, self.message_ok = msg, ok
                self.message_until = time.monotonic() + 5
                self.update()
                return
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.hide()

    def mouseMoveEvent(self, e):
        pos = e.position()
        key = self.cell_at(pos)
        clickable = (key is not None or self.close_rect().contains(pos)
                     or any(r.contains(pos) for _t, r in self.tab_rects()))
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
        if key != self.hover:
            self.hover = key
            self.update()

    def leaveEvent(self, _e):
        self.hover = None
        self.update()

    def paintEvent(self, _e):
        plant = self.plant
        coins = plant.state.get("coins", 0)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(T("panel_border"), 1.2))
        p.setBrush(T("panel"))
        p.drawRoundedRect(rect, 10, 10)

        font = QFont(self.font())
        font.setPixelSize(14)
        font.setBold(True)
        p.setFont(font)
        p.setPen(T("text"))
        p.drawText(QRectF(12, 7, 150, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "Shop")

        cr = self.close_rect()
        p.setPen(QPen(T("muted"), 1.6))
        p.drawLine(cr.topLeft() + QPointF(5, 5), cr.bottomRight() - QPointF(5, 5))
        p.drawLine(QPointF(cr.right() - 5, cr.top() + 5), QPointF(cr.left() + 5, cr.bottom() - 5))

        font.setBold(False)
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(T("text2"))
        p.drawText(QRectF(12, 28, 170, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"für: {plant.kind.name}" if self.tab == "duenger" else "für alle Pflanzen")
        draw_coin(p, QPointF(SHOP_W - 18, 37), 6)
        p.setPen(T("coin"))
        p.drawText(QRectF(SHOP_W - 140, 28, 112, 18),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt_int(coins))
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, 51), QPointF(SHOP_W - 12, 51))

        active_fz, _left = plant.fert()
        small = QFont(font)
        small.setPixelSize(10)
        tabfont = QFont(font)
        tabfont.setPixelSize(12)
        for tab, r in self.tab_rects():
            sel = tab == self.tab
            p.setPen(QPen(QColor("#2E9E44"), 1.6) if sel else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if sel else T("cell"))
            p.drawRoundedRect(r, 6, 6)
            tabfont.setBold(sel)
            p.setFont(tabfont)
            p.setPen(T("button_text") if sel else T("text2"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Dünger" if tab == "duenger" else "Helfer")
        if self.tab == "helfer":
            self.paint_helpers(p, small, coins)
        else:
            self.paint_fertilizers(p, small, coins, active_fz)
        info = QRectF(12, SHOP_H - 46, SHOP_W - 24, 38)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, info.top() - 4), QPointF(SHOP_W - 12, info.top() - 4))
        if self.message and time.monotonic() < self.message_until:
            text, color = self.message, T("ok") if self.message_ok else T("bad")
        elif self.hover and self.tab == "helfer":
            hp = HELPERS[self.hover]
            have = self.hover in plant.state.get("helpers", [])
            text = f"{hp.name}: {hp.desc} " + ("Klick schaltet ein oder aus." if have else "Klick kauft den Helfer.")
            color = T("text3")
        elif self.tab == "helfer":
            text, color = "Helfer arbeiten automatisch für jede ausgewählte Pflanze. Einmal kaufen, dauerhaft nutzen.", T("muted")
        elif self.hover:
            text, color = fert_description(FERTILIZERS[self.hover]), T("text3")
        elif active_fz:
            text, color = f"Aktiv: {plant.fert_summary()}", T("ok")
        else:
            text, color = (f"Dünger anklicken, um ihn für die ausgewählte Pflanze zu kaufen. "
                           f"Passives Einkommen: {PASSIVE_PER_HOUR} Coins pro Stunde."), T("muted")
        p.setFont(small)
        p.setPen(color)
        p.drawText(info, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, text)
        p.end()


    def paint_fertilizers(self, p, small, coins, active_fz):
        for key, r in self.cell_rects():
            fz = FERTILIZERS[key]
            affordable = coins >= fz.price
            is_active = active_fz is not None and active_fz.key == key
            if is_active:
                p.setPen(QPen(QColor("#2E9E44"), 2.2))
                p.setBrush(T("active_bg"))
            elif key == self.hover:
                p.setPen(QPen(QColor("#D4A017"), 1.8))
                p.setBrush(T("gold_bg"))
            else:
                p.setPen(QPen(T("cell_border"), 1))
                p.setBrush(T("cell"))
            p.drawRoundedRect(r, 7, 7)
            p.setOpacity(1.0 if affordable else 0.45)
            draw_fert_icon(p, fz, QRectF(r.center().x() - 18, r.top() + 4, 36, 36))
            p.setOpacity(1.0)
            p.setFont(small)
            p.setPen(T("text3"))
            fit_font(p, small, fz.name, r.width() - 6)
            p.drawText(QRectF(r.left() + 2, r.top() + 41, r.width() - 4, 14),
                       Qt.AlignmentFlag.AlignCenter, fz.name)
            p.setFont(small)
            price = fmt_int(fz.price)
            tw = p.fontMetrics().horizontalAdvance(price)
            cx = r.center().x() - (tw + 12) / 2
            draw_coin(p, QPointF(cx + 4, r.top() + 64), 4)
            p.setPen(T("coin") if affordable else T("bad"))
            p.drawText(QRectF(cx + 11, r.top() + 57, tw + 4, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, price)


    def paint_helpers(self, p, small, coins):
        owned = self.plant.state.get("helpers", [])
        for key, r in self.cell_rects():
            hp = HELPERS[key]
            have = key in owned
            on = have and self.plant.helper_on(key)
            affordable = coins >= hp.price
            if on:
                p.setPen(QPen(QColor("#2E9E44"), 2.2))
                p.setBrush(T("active_bg"))
            elif key == self.hover:
                p.setPen(QPen(QColor("#D4A017"), 1.8))
                p.setBrush(T("gold_bg"))
            else:
                p.setPen(QPen(T("cell_border"), 1))
                p.setBrush(T("cell"))
            p.drawRoundedRect(r, 7, 7)
            p.setOpacity(1.0 if (have or affordable) else 0.45)
            draw_helper_icon(p, key, QRectF(r.center().x() - 18, r.top() + 4, 36, 36))
            p.setOpacity(1.0)
            p.setFont(small)
            p.setPen(T("text3"))
            fit_font(p, small, hp.name, r.width() - 6)
            p.drawText(QRectF(r.left() + 2, r.top() + 41, r.width() - 4, 14),
                       Qt.AlignmentFlag.AlignCenter, hp.name)
            p.setFont(small)
            if have:
                p.setPen(T("ok") if on else T("muted"))
                p.drawText(QRectF(r.left() + 2, r.top() + 57, r.width() - 4, 14),
                           Qt.AlignmentFlag.AlignCenter, "aktiv" if on else "ausgeschaltet")
            else:
                price = fmt_int(hp.price)
                tw = p.fontMetrics().horizontalAdvance(price)
                cx = r.center().x() - (tw + 12) / 2
                draw_coin(p, QPointF(cx + 4, r.top() + 64), 4)
                p.setPen(T("coin") if affordable else T("bad"))
                p.drawText(QRectF(cx + 11, r.top() + 57, tw + 4, 14),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, price)


# ---------------------------------------------------------------- Gartenhaus

class Garden(QWidget):
    """Ehrenhalle für voll ausgewachsene Pflanzen, im Stil der Sprechblase."""

    COLS = 3
    CARD_H = 166
    GAP = 8

    def __init__(self, plant):
        super().__init__()
        self.plant = plant
        self.scroll = 0.0
        self.hover = None
        self.hover_button = False
        self.cache = {}
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(GARDEN_W, GARDEN_H)
        self.setMouseTracking(True)
        self.place_window()

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.plant.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def place_window(self):
        pos = self.plant.state.get("garden_pos")
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        else:
            self.move(max(0, self.plant.x() - GARDEN_W - 10), max(0, self.plant.y() - 40))

    def entries(self):
        return list(reversed(self.plant.state.get("garden", [])))  # neueste zuerst

    def view_rect(self):
        return QRectF(8, 56, GARDEN_W - 16, GARDEN_H - 56 - 100)

    def info_rect(self):
        return QRectF(12, GARDEN_H - 94, GARDEN_W - 24, 40)

    def button_rect(self):
        return QRectF(14, GARDEN_H - 46, GARDEN_W - 28, 34)

    def close_rect(self):
        return QRectF(GARDEN_W - 28, 8, 18, 18)

    def card_rects(self):
        x0 = 14
        cw = (GARDEN_W - 2 * x0 - (self.COLS - 1) * self.GAP) / self.COLS
        top = self.view_rect().top() + 4 - self.scroll
        rects = []
        for i in range(len(self.entries())):
            row, col = divmod(i, self.COLS)
            rects.append((i, QRectF(x0 + col * (cw + self.GAP), top + row * (self.CARD_H + self.GAP),
                                    cw, self.CARD_H)))
        return rects

    def max_scroll(self):
        rows = math.ceil(len(self.entries()) / self.COLS)
        content = rows * (self.CARD_H + self.GAP) + 4
        return max(0.0, content - self.view_rect().height())

    @staticmethod
    def delete_rect(card):
        return QRectF(card.left() + 4, card.top() + 4, 16, 16)

    def delete_card(self, idx):
        entries = self.entries()
        if idx is None or idx >= len(entries):
            return
        e = entries[idx]
        kind = PLANT_TYPES.get(e["key"])
        name = kind.name if kind else e["key"]
        answer = QMessageBox.question(
            self, "Karte löschen",
            f"Die Karte «{name}» vom {fmt_datetime(e.get('archived_at'))} endgültig aus dem Gartenhaus löschen?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        garden = self.plant.state.get("garden", [])
        garden.pop(len(garden) - 1 - idx)  # Anzeige ist umgekehrt (neueste zuerst)
        self.cache.pop((e["key"], e.get("archived_at"), e.get("seed")), None)
        self.hover = None
        self.scroll = min(self.scroll, self.max_scroll())
        self.plant.save_state()
        self.plant.bubble.update()
        self.update()

    def card_at(self, pos):
        if not self.view_rect().contains(pos):
            return None
        for i, r in self.card_rects():
            if r.contains(pos):
                return i
        return None

    def thumbnail(self, entry):
        key = (entry["key"], entry.get("archived_at"), entry.get("seed"))
        if key not in self.cache:
            self.cache[key] = self.plant.snapshot(entry)
        return self.cache[key]

    def showEvent(self, e):
        super().showEvent(e)
        self.scroll = min(self.scroll, self.max_scroll())
        self.plant.bubble.update()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.plant.bubble.update()

    def wheelEvent(self, e):
        self.scroll = max(0.0, min(self.max_scroll(), self.scroll - e.angleDelta().y() / 2))
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.close_rect().contains(e.position()):
                self.hide()
                return
            idx = self.card_at(e.position())
            if idx is not None and self.delete_rect(dict(self.card_rects())[idx]).contains(e.position()):
                self.delete_card(idx)
                return
            if self.button_rect().contains(e.position()):
                self.plant.reset_plant()
                self.scroll = 0.0
                self.update()
                return
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.hide()

    def mouseMoveEvent(self, e):
        pos = e.position()
        over_button = self.button_rect().contains(pos)
        idx = self.card_at(pos)
        over_delete = idx is not None and self.delete_rect(dict(self.card_rects())[idx]).contains(pos)
        clickable = self.close_rect().contains(pos) or over_button or over_delete
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
        if idx != self.hover or over_button != self.hover_button or over_delete != getattr(self, "hover_delete", False):
            self.hover, self.hover_button, self.hover_delete = idx, over_button, over_delete
            self.update()

    def leaveEvent(self, _e):
        self.hover = None
        self.hover_button = False
        self.update()

    def paintEvent(self, _e):
        entries = self.entries()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(T("panel_border"), 1.2))
        p.setBrush(T("panel"))
        p.drawRoundedRect(rect, 10, 10)

        font = QFont(self.font())
        font.setPixelSize(14)
        font.setBold(True)
        p.setFont(font)
        p.setPen(T("text"))
        p.drawText(QRectF(12, 7, 200, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "Gartenhaus")
        cr = self.close_rect()
        p.setPen(QPen(T("muted"), 1.6))
        p.drawLine(cr.topLeft() + QPointF(5, 5), cr.bottomRight() - QPointF(5, 5))
        p.drawLine(QPointF(cr.right() - 5, cr.top() + 5), QPointF(cr.left() + 5, cr.bottom() - 5))
        font.setBold(False)
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(T("text2"))
        n = len(entries)
        p.drawText(QRectF(12, 28, 250, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"Ehrenhalle · {n} Pflanze{'n' if n != 1 else ''}")
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, 51), QPointF(GARDEN_W - 12, 51))

        view = self.view_rect()
        small = QFont(font)
        small.setPixelSize(10)
        bold = QFont(font)
        bold.setPixelSize(11)
        bold.setBold(True)
        if not entries:
            p.setPen(T("muted"))
            p.setFont(font)
            p.drawText(view.adjusted(20, 0, -20, 0),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "Noch leer.\n\nBlühende Pflanzen kommen beim Neu-Aussäen mit Datum und Uhrzeit hierher.")
        p.save()
        p.setClipRect(view)
        for i, r in self.card_rects():
            if r.bottom() < view.top() or r.top() > view.bottom():
                continue
            e = entries[i]
            kind = PLANT_TYPES.get(e["key"])
            if kind is None:
                continue
            if i == self.hover:
                p.setPen(QPen(QColor("#2E9E44"), 1.8))
                p.setBrush(T("hover_bg"))
            else:
                p.setPen(QPen(T("cell_border"), 1))
                p.setBrush(T("cell"))
            p.drawRoundedRect(r, 7, 7)
            img = self.thumbnail(e)
            th = 112.0
            tw = th * img.width() / img.height()
            p.drawImage(QRectF(r.center().x() - tw / 2, r.top() + 4, tw, th), img)
            name_font = QFont(bold)
            p.setFont(name_font)
            while p.fontMetrics().horizontalAdvance(kind.name) > r.width() - 8 and name_font.pixelSize() > 8:
                name_font.setPixelSize(name_font.pixelSize() - 1)  # lange Namen verkleinern
                p.setFont(name_font)
            p.setPen(T("text"))
            p.drawText(QRectF(r.left() + 2, r.top() + 116, r.width() - 4, 16),
                       Qt.AlignmentFlag.AlignCenter, kind.name)
            p.setPen(QPen(T("scroll"), 0.8))
            p.setBrush(QColor(e.get("color", "#FFFFFF")))
            p.drawEllipse(QPointF(r.right() - 9, r.top() + 9), 4, 4)
            if e.get("prestige"):  # Prestige-Stern mit Stufe
                sc = QPointF(r.right() - 10, r.top() + 24)
                draw_star(p, sc, 7.5)
                sf = QFont(small)
                sf.setBold(True)
                sf.setPixelSize(8)
                p.setFont(sf)
                p.setPen(QColor("#5A3A00"))
                p.drawText(QRectF(sc.x() - 5, sc.y() - 4.5, 10, 10), Qt.AlignmentFlag.AlignCenter,
                           str(min(99, e["prestige"])))
            if i == self.hover:  # Löschen-Knopf nur beim Überfahren
                dr = self.delete_rect(r)
                active = getattr(self, "hover_delete", False)
                p.setPen(QPen(T("bad") if active else T("btn_border"), 1))
                p.setBrush(T("bad_bg") if active else T("white"))
                p.drawEllipse(dr)
                p.setPen(QPen(T("bad") if active else T("muted"), 1.4))
                p.drawLine(dr.topLeft() + QPointF(5, 5), dr.bottomRight() - QPointF(5, 5))
                p.drawLine(QPointF(dr.right() - 5, dr.top() + 5), QPointF(dr.left() + 5, dr.bottom() - 5))
            p.setFont(small)
            p.setPen(T("text2"))
            ts = e.get("archived_at")
            p.drawText(QRectF(r.left() + 2, r.top() + 132, r.width() - 4, 14),
                       Qt.AlignmentFlag.AlignCenter, fmt_date(ts))
            p.drawText(QRectF(r.left() + 2, r.top() + 146, r.width() - 4, 14),
                       Qt.AlignmentFlag.AlignCenter,
                       time.strftime("%H:%M Uhr", time.localtime(ts)) if ts else "")
        p.restore()

        ms = self.max_scroll()
        if ms > 0:  # Bildlaufanzeige
            track = view.height() - 8
            bar = max(24.0, track * view.height() / (view.height() + ms))
            y = view.top() + 4 + (track - bar) * self.scroll / ms
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(T("scroll"))
            p.drawRoundedRect(QRectF(GARDEN_W - 8, y, 3, bar), 1.5, 1.5)

        info = self.info_rect()
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, info.top() - 4), QPointF(GARDEN_W - 12, info.top() - 4))
        plant, bloomed = self.plant, self.plant.ps["growth"] >= self.plant.kind.bloom_at
        if self.hover_button:
            if bloomed:
                lvl = plant.prestige_level()
                text = (f"{plant.kind.name} blüht: Prestige-Stufe {lvl} → {lvl + 1}, kommt ins Gartenhaus "
                        f"und wird neu ausgesät.")
                color = T("ok")
            else:
                text = (f"{plant.kind.name} ({stage_name(plant.kind, plant.ps['growth'])}) kommt nur ins "
                        f"Gartenhaus, ohne Prestige-Stufe. Danach wird neu ausgesät.")
                color = T("text2")
        elif getattr(self, "hover_delete", False):
            text, color = "Karte löschen (mit Rückfrage).", T("bad")
        elif self.hover is not None and self.hover < len(entries):
            e = entries[self.hover]
            kind = PLANT_TYPES[e["key"]]
            text = ((f"Prestige-Stufe {e['prestige']} · " if e.get("prestige") else "")
                    + f"{kind.name} ({stage_name(kind, e.get('growth', 0))}): gepflanzt {fmt_date(e.get('created'))}, "
                    f"Blüte {fmt_date(e.get('bloomed_at'))}, "
                    f"ins Gartenhaus {fmt_datetime(e.get('archived_at'))}. "
                    f"Wachstum {e.get('growth', 0):.0f}, {fmt_int(e.get('clicks_total', 0))} Klicks"
                    + (f", {fmt_int(e.get('keys_total', 0))} Tasten." if kind.growth_per_key > 0 else "."))
            color = T("text3")
        else:
            text = "Mausrad zum Blättern. Zeiger auf eine Karte zeigt Details, × oben links löscht sie."
            color = T("muted")
        p.setFont(small)
        p.setPen(color)
        p.drawText(info, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                   text)
        self.draw_button(p, bloomed)
        p.end()

    def draw_button(self, p, bloomed):
        btn = self.button_rect()
        pulse = (math.sin(self.plant.t * 3.0) + 1) / 2 if bloomed else 0.0
        if bloomed:
            border = mix(QColor("#2E9E44"), QColor("#D4A017"), pulse)
            p.setPen(QPen(border, 1.4 + 0.6 * pulse))
            p.setBrush(T("active_bg_hover") if self.hover_button else T("active_bg"))
        else:
            p.setPen(QPen(T("btn_border"), 1.1))
            p.setBrush(T("btn_bg_hover") if self.hover_button else T("btn_bg"))
        p.drawRoundedRect(btn, 8, 8)
        draw_seed_packet(p, QPointF(btn.left() + 19, btn.center().y()), 22 + 2 * pulse, bloomed, pulse)
        font = QFont(self.font())
        font.setPixelSize(12)
        font.setBold(True)  # wie im Entwurf: fett, dunkelgrün
        p.setFont(font)
        p.setPen(T("button_text"))
        p.drawText(btn.adjusted(36, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "Einlagern & neu aussäen")


# ---------------------------------------------------------------- Weitere Fenster

class Panel(QWidget):
    """Gemeinsame Grundlage für Erfolge, Fokus-Timer und Sammelbuch (Stil der Sprechblase)."""

    def __init__(self, plant, w, h, pos_key):
        super().__init__()
        self.plant = plant
        self.pos_key = pos_key
        self.hover = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(w, h)
        self.setMouseTracking(True)
        self.place_window()

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.plant.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def place_window(self):
        pos = self.plant.state.get(self.pos_key)
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        else:
            b = self.plant.bubble
            self.move(max(0, b.x() - self.width() - 10), max(0, b.y()))

    def close_rect(self):
        return QRectF(self.width() - 28, 8, 18, 18)

    def items(self):
        """Liste von (Schlüssel, Rechteck, anklickbar)."""
        return []

    def item_at(self, pos):
        for key, r, _c in self.items():
            if r.contains(pos):
                return key
        return None

    def on_click(self, key):
        pass

    def showEvent(self, e):
        super().showEvent(e)
        self.plant.bubble.update()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.plant.bubble.update()

    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() == Qt.MouseButton.LeftButton:
            if self.close_rect().contains(pos):
                self.hide()
                return
            for key, r, clickable in self.items():
                if clickable and r.contains(pos):
                    self.on_click(key)
                    self.update()
                    return
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.hide()

    def mouseMoveEvent(self, e):
        pos = e.position()
        clickable = self.close_rect().contains(pos) or any(
            c and r.contains(pos) for _k, r, c in self.items())
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
        key = self.item_at(pos)
        if key != self.hover:
            self.hover = key
            self.update()

    def leaveEvent(self, _e):
        self.hover = None
        self.update()

    def begin(self, title, subtitle):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(T("panel_border"), 1.2))
        p.setBrush(T("panel"))
        p.drawRoundedRect(rect, 10, 10)
        font = QFont(self.font())
        font.setPixelSize(14)
        font.setBold(True)
        p.setFont(font)
        p.setPen(T("text"))
        p.drawText(QRectF(12, 7, self.width() - 50, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   title)
        cr = self.close_rect()
        p.setPen(QPen(T("muted"), 1.6))
        p.drawLine(cr.topLeft() + QPointF(5, 5), cr.bottomRight() - QPointF(5, 5))
        p.drawLine(QPointF(cr.right() - 5, cr.top() + 5), QPointF(cr.left() + 5, cr.bottom() - 5))
        font.setBold(False)
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(T("text2"))
        p.drawText(QRectF(12, 28, self.width() - 24, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   subtitle)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, 51), QPointF(self.width() - 12, 51))
        return p

    @staticmethod
    def font_px(base, px, bold=False):
        f = QFont(base)
        f.setPixelSize(px)
        f.setBold(bold)
        return f


class AchievementsWin(Panel):
    ROW_H = 35

    def __init__(self, plant):
        super().__init__(plant, 300, 556, "ach_pos")

    def showEvent(self, e):
        super().showEvent(e)
        self.plant.state["ach_new"] = 0
        self.plant.bubble.update()

    def paintEvent(self, _e):
        plant = self.plant
        done_n = sum(1 for a in ACHIEVEMENTS if plant.ach_is_done(a))
        p = self.begin("Erfolge", f"{done_n} von {len(ACHIEVEMENTS)} erreicht")
        base = self.font()
        y = 58.0
        W = self.width()
        now = time.localtime()
        secs_day = 86400 - (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
        secs_week = secs_day + (6 - now.tm_wday) * 86400
        sections = (("daily", "Täglich", f"neu in {fmt_left(secs_day)}"),
                    ("weekly", "Wöchentlich", f"neu in {fmt_age(secs_week)}"),
                    ("general", "Allgemein", "einmalig"))
        for period, heading, right in sections:
            p.setFont(self.font_px(base, 12, True))
            p.setPen(T("text"))
            p.drawText(QRectF(12, y, 150, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, heading)
            p.setFont(self.font_px(base, 10))
            p.setPen(T("muted"))
            p.drawText(QRectF(W - 162, y, 150, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right)
            y += 20
            for a in (a for a in ACHIEVEMENTS if a.period == period):
                done = plant.ach_is_done(a)
                val = min(plant.ach_value(a.key), a.target)
                row = QRectF(12, y, W - 24, self.ROW_H - 3)
                p.setPen(QPen(QColor("#2E9E44"), 1.2) if done else QPen(T("cell_border"), 1))
                p.setBrush(T("active_bg") if done else T("cell"))
                p.drawRoundedRect(row, 6, 6)
                icon_c = QPointF(row.left() + 13, row.center().y())
                if done:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor("#2E9E44"))
                    p.drawEllipse(icon_c, 7, 7)
                    p.setPen(round_pen(QColor("#FFFFFF"), 1.8))
                    p.drawLine(icon_c + QPointF(-3.2, 0.2), icon_c + QPointF(-0.8, 2.6))
                    p.drawLine(icon_c + QPointF(-0.8, 2.6), icon_c + QPointF(3.4, -2.4))
                else:
                    draw_star(p, icon_c, 7, "#D8D3C4" if not _THEME["dark"] else "#6A6A62",
                              "#9A958A")
                p.setFont(self.font_px(base, 11, True))
                p.setPen(T("text"))
                p.drawText(QRectF(row.left() + 26, row.top() + 1, 150, 15),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, a.name)
                reward = f"+{a.reward}"
                p.setFont(self.font_px(base, 11, True))
                tw = p.fontMetrics().horizontalAdvance(reward)
                draw_coin(p, QPointF(row.right() - 10, row.top() + 8.5), 4.5)
                p.setPen(T("coin"))
                p.drawText(QRectF(row.right() - 18 - tw, row.top() + 1, tw + 2, 15),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, reward)
                p.setFont(self.font_px(base, 10))
                p.setPen(T("text2"))
                p.drawText(QRectF(row.left() + 26, row.top() + 15, row.width() - 26 - 92, 13),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, a.desc)
                p.setPen(T("ok") if done else T("muted"))
                p.drawText(QRectF(row.right() - 90, row.top() + 15, 82, 13),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           "erreicht" if done else f"{fmt_int(val)} / {fmt_int(a.target)}")
                bar = QRectF(row.left() + 26, row.bottom() - 4.5, row.width() - 34, 2)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(T("sep"))
                p.drawRoundedRect(bar, 1, 1)
                p.setBrush(QColor("#2E9E44"))
                p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * val / a.target, 2), 1, 1)
                y += self.ROW_H
            y += 4
        p.end()


class FocusWin(Panel):
    def __init__(self, plant):
        super().__init__(plant, 240, 262, "focus_pos")

    def preset_rects(self):
        w = (self.width() - 24 - 12) / 3
        return [(f"p{m}", QRectF(12 + i * (w + 6), 58, w, 24)) for i, m in enumerate(FOCUS_PRESETS)]

    def button_rect(self):
        return QRectF(40, 206, self.width() - 80, 30)

    def items(self):
        running = self.plant.focus is not None
        return [(k, r, not running) for k, r in self.preset_rects()] + [("start", self.button_rect(), True)]

    def on_click(self, key):
        if key == "start":
            if self.plant.focus:
                self.plant.abort_focus()
            else:
                self.plant.start_focus(self.plant.state.get("focus_minutes", FOCUS_PRESETS[0]))
        elif key.startswith("p") and not self.plant.focus:
            self.plant.state["focus_minutes"] = int(key[1:])

    def paintEvent(self, _e):
        plant = self.plant
        p = self.begin("Fokus-Timer", f"Wachstum ×{FOCUS_MULT:g} während der Sitzung")
        base = self.font()
        running = plant.focus is not None
        chosen = plant.state.get("focus_minutes", FOCUS_PRESETS[0])
        for key, r in self.preset_rects():
            m = int(key[1:])
            sel = m == (plant.focus["minutes"] if running else chosen)
            p.setOpacity(1.0 if (sel or not running) else 0.45)
            p.setPen(QPen(QColor("#2E9E44"), 1.6) if sel else
                     QPen(QColor("#D4A017"), 1.4) if key == self.hover and not running else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if sel else T("cell"))
            p.drawRoundedRect(r, 6, 6)
            p.setFont(self.font_px(base, 12, sel))
            p.setPen(T("button_text") if sel else T("text2"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, f"{m} min")
            p.setOpacity(1.0)

        c = QPointF(self.width() / 2, 143)
        R = 46
        p.setPen(QPen(T("sep"), 7))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, R, R)
        if running:
            rem, total = plant.focus_remaining()
            frac = 1 - rem / total
        else:
            rem, total, frac = chosen * 60, chosen * 60, 0.0
        if frac > 0:
            pen = QPen(QColor("#2E9E44"), 7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), 90 * 16, -int(360 * 16 * frac))
        m, sec = divmod(int(math.ceil(rem)), 60)
        p.setFont(self.font_px(base, 24, True))
        p.setPen(T("text"))
        p.drawText(QRectF(c.x() - R, c.y() - 20, 2 * R, 28), Qt.AlignmentFlag.AlignCenter, f"{m:02d}:{sec:02d}")
        msg, ok = plant.focus_message()
        p.setFont(self.font_px(base, 10))
        p.setPen(T("ok") if ok else T("muted"))
        p.drawText(QRectF(c.x() - R, c.y() + 8, 2 * R, 16), Qt.AlignmentFlag.AlignCenter,
                   "läuft" if running else msg or "bereit")

        br = self.button_rect()
        hov = self.hover == "start"
        if running:
            p.setPen(QPen(T("bad"), 1.4))
            p.setBrush(T("bad_bg"))
        else:
            p.setPen(QPen(QColor("#2E9E44"), 1.6 if hov else 1.3))
            p.setBrush(T("active_bg_hover") if hov else T("active_bg"))
        p.drawRoundedRect(br, 8, 8)
        p.setFont(self.font_px(base, 12, True))
        p.setPen(T("bad") if running else T("button_text"))
        p.drawText(br, Qt.AlignmentFlag.AlignCenter, "Abbrechen" if running else "Fokus starten")

        d = plant.state.get("daily", {})
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        p.drawText(QRectF(12, self.height() - 22, self.width() - 24, 16), Qt.AlignmentFlag.AlignCenter,
                   f"Heute: {d.get('focus', 0)} Sitzung(en) · {d.get('focus_min', 0)} min")
        p.end()


class BookWin(Panel):
    COLS = 4

    def __init__(self, plant):
        super().__init__(plant, 300, 334, "book_pos")

    def card_rects(self):
        gap, x0, y0 = 6, 12, 58
        cw = (self.width() - 2 * x0 - (self.COLS - 1) * gap) / self.COLS
        ch = 104
        return [(key, QRectF(x0 + (i % self.COLS) * (cw + gap), y0 + (i // self.COLS) * (ch + gap), cw, ch))
                for i, key in enumerate(VISITOR_ORDER)]

    def items(self):
        return [(k, r, False) for k, r in self.card_rects()]

    def paintEvent(self, _e):
        plant = self.plant
        book = plant.state.get("book", {})
        p = self.begin("Besucher-Sammelbuch", f"{len(book)} von {len(VISITORS)} entdeckt")
        base = self.font()
        rarity_col = {"häufig": T("muted"), "selten": QColor("#3B82C4"), "sehr selten": QColor("#9B59B6")}
        for key, r in self.card_rects():
            v = VISITORS[key]
            found = key in book
            p.setPen(QPen(QColor("#D4A017"), 1.6) if key == self.hover else QPen(T("cell_border"), 1))
            p.setBrush(T("cell"))
            p.drawRoundedRect(r, 7, 7)
            draw_visitor(p, key, QPointF(r.center().x(), r.top() + 34), 2.3, plant.t + hash(key) % 7,
                         silhouette=not found)
            p.setFont(self.font_px(base, 10, True))
            p.setPen(T("text") if found else T("muted"))
            name_font = self.font_px(base, 10, True)
            while p.fontMetrics().horizontalAdvance(v.name if found else "???") > r.width() - 6 and name_font.pixelSize() > 7:
                name_font.setPixelSize(name_font.pixelSize() - 1)
                p.setFont(name_font)
            p.drawText(QRectF(r.left() + 2, r.top() + 62, r.width() - 4, 14), Qt.AlignmentFlag.AlignCenter,
                       v.name if found else "???")
            p.setFont(self.font_px(base, 9))
            p.setPen(rarity_col[v.rarity])
            p.drawText(QRectF(r.left() + 2, r.top() + 76, r.width() - 4, 12), Qt.AlignmentFlag.AlignCenter, v.rarity)
            p.setPen(T("text2"))
            p.drawText(QRectF(r.left() + 2, r.top() + 88, r.width() - 4, 12), Qt.AlignmentFlag.AlignCenter,
                       f"{book[key]['count']}× gesehen" if found else "unbekannt")

        info = QRectF(12, self.height() - 50, self.width() - 24, 42)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, info.top() - 4), QPointF(self.width() - 12, info.top() - 4))
        if self.hover:
            v = VISITORS[self.hover]
            e = book.get(self.hover)
            if e:
                text = (f"{v.name} ({v.rarity}): zuerst gesehen am {fmt_datetime(e.get('first'))}, "
                        f"{e['count']}× insgesamt. {v.hint}")
            else:
                text = f"Noch nicht entdeckt ({v.rarity}). Hinweis: {v.hint}"
            color = T("text3")
        else:
            text = (f"Besucher kommen von selbst zur Pflanze. Ein Klick auf einen Besucher begrüsst ihn "
                    f"und bringt {VISIT_GREET_COINS} Coins.")
            color = T("muted")
        p.setFont(self.font_px(base, 10))
        p.setPen(color)
        p.drawText(info, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, text)
        p.end()


# ---------------------------------------------------------------- Pflanzenfenster

class Plant(QWidget):
    def __init__(self):
        super().__init__()
        self.state = self.load_state()
        _THEME["dark"] = self.state.get("dark", False)

        self.t = 0.0
        self.last_tick = time.monotonic()
        self.last_save = self.last_tick
        self.drops = []      # [x, y, vy]
        self.sparkles = []   # [x, y, life]
        self.popups = []     # [x, y, life, text, coin] – Einblendungen
        self.popup_queue = []
        self.press_pos = None
        self.dragging = False
        self.top_point = QPointF(WIN_W / 2, 200)
        self.focus = None            # laufende Fokus-Sitzung
        self.focus_msg = ("", True, 0.0)
        self.visitor = None          # aktueller Besucher
        self.visit_acc = 0.0
        self.bee_timer = random.uniform(*BEE_INTERVAL)
        self.bee_anim = 0.0
        self.gnome_acc = 0.0
        self.gnome_hop = 0.0
        self.drip_active = False
        self.sec_acc = 0.0

        self.activate(self.state["current"], offline=True)

        self.keys = KeyCounter()
        self.key_source = self.keys.start()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(WIN_W, WIN_H)
        self.place_window()

        self.bubble = Bubble(self)
        self.shop = Shop(self)
        self.garden = Garden(self)
        self.ach_win = AchievementsWin(self)
        self.focus_win = FocusWin(self)
        self.book_win = BookWin(self)
        self.windows = {"shop": self.shop, "garden": self.garden, "ach": self.ach_win,
                        "focus": self.focus_win, "book": self.book_win}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)  # 20 fps
        self.update_tooltip()

    # ---------- Zustand ----------

    @staticmethod
    def new_plant_state(key=None):
        now = time.time()
        state = {"growth": 0.0, "water": 50.0, "clicks_total": 0, "keys_total": 0,
                 "seed": random.randrange(1 << 30), "created": now, "last_update": now,
                 "stage_rewarded": 0, "milestone_rewarded": 0, "fert": None, "bloomed_at": None}
        if key:  # neue Pflanze: zufällige Farbe aus der erweiterten Auswahl
            state["color"] = random.choice(PLANT_TYPES[key].palette)
        return state

    @staticmethod
    def default_state():
        return {"version": 2, "current": "wiesenblume", "plants": {},
                "pos": None, "bubble": True, "bubble_pos": None, "shop_pos": None,
                "coins": 0, "passive_acc": 0.0, "keyboard_enabled": True, "on_top": True,
                "garden": [], "garden_pos": None, "dark": False,
                "helpers": [], "helpers_off": [], "prestige": {}, "bloomed_species": [],
                "stats": {"keys": None}, "daily": {}, "weekly": {}, "ach_done": [], "ach_new": 0,
                "book": {}, "focus_minutes": FOCUS_PRESETS[0]}

    def load_state(self):
        state = self.default_state()
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {}
        if data and "plants" not in data:
            # Spielstand der ersten Version übernehmen: wird zur Wiesenblume
            plant = {k: data[k] for k in ("growth", "water", "clicks_total", "keys_total",
                                          "seed", "created", "last_update") if k in data}
            data = {k: v for k, v in data.items()
                    if k in ("pos", "bubble", "bubble_pos", "keyboard_enabled", "on_top")}
            data["plants"] = {"wiesenblume": {**self.new_plant_state(), **plant}}
            data["current"] = "wiesenblume"
        state.update(data)
        if state["current"] not in PLANT_TYPES:
            state["current"] = "wiesenblume"
        # Erweiterungen für bestehende Spielstände
        if state["stats"].get("keys") is None:
            state["stats"]["keys"] = sum(pl.get("keys_total", 0) for pl in state["plants"].values()) + sum(
                e.get("keys_total", 0) or 0 for e in state.get("garden", []))
        bloomed = set(state.get("bloomed_species", []))
        for key, pl in state["plants"].items():
            if key in PLANT_TYPES and pl.get("growth", 0) >= PLANT_TYPES[key].bloom_at:
                bloomed.add(key)
        for e in state.get("garden", []):
            if e.get("key") in PLANT_TYPES and (e.get("growth") or 0) >= PLANT_TYPES[e["key"]].bloom_at:
                bloomed.add(e["key"])
        state["bloomed_species"] = sorted(bloomed)
        return state

    def save_state(self):
        now = time.time()
        self.ps["last_update"] = now
        self.state["pos"] = [self.x(), self.y()]
        if hasattr(self, "bubble"):
            self.state["bubble_pos"] = [self.bubble.x(), self.bubble.y()]
        if hasattr(self, "shop"):
            self.state["shop_pos"] = [self.shop.x(), self.shop.y()]
        if hasattr(self, "garden"):
            self.state["garden_pos"] = [self.garden.x(), self.garden.y()]
        if hasattr(self, "windows"):
            for win in (self.ach_win, self.focus_win, self.book_win):
                self.state[win.pos_key] = [win.x(), win.y()]
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = STATE_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            os.replace(tmp, STATE_FILE)
        except OSError as e:
            print(f"Speichern fehlgeschlagen: {e}", file=sys.stderr)

    def activate(self, key, offline=False):
        """Wählt die aktive Pflanze. Nicht aktive Pflanzen pausieren."""
        now = time.time()
        if hasattr(self, "ps"):
            self.ps["last_update"] = now
        self.state["current"] = key
        self.kind = PLANT_TYPES[key]
        self.pot = POTS[self.kind.pot]
        plants = self.state["plants"]
        if key not in plants:
            plants[key] = self.new_plant_state(key)
        self.ps = plants[key]
        for k, v in self.new_plant_state().items():  # ohne 'color': bestehende Farbe bleibt
            self.ps.setdefault(k, v)
        if offline:
            elapsed = max(0.0, now - self.ps["last_update"])
            self.ps["water"] = max(0.0, self.ps["water"] - elapsed * self.drain_rate())
        self.ps["last_update"] = now
        self.drops.clear()
        self.sparkles.clear()
        self.popups.clear()
        self.setup_randomness()

    def setup_randomness(self):
        rng = random.Random(self.ps["seed"])
        self.lean = rng.uniform(-14, 14)
        self.lean_dir = 1 if self.lean >= 0 else -1
        self.leaf_rnd = [(rng.uniform(0.85, 1.15), rng.uniform(-10, 10)) for _ in range(40)]
        self.rnd = [rng.random() for _ in range(200)]
        self.blossom = [(rng.random(), rng.random(), rng.random()) for _ in range(100)]
        legacy = rng.choice(self.kind.colors)  # bisherige Berechnung, bleibt für alte Pflanzen gleich
        if not self.ps.get("color"):
            self.ps["color"] = legacy
        self.flower_color = QColor(self.ps["color"])

    # ---------- Fenster ----------

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def place_window(self):
        pos = self.state.get("pos")
        if pos:
            self.move(int(pos[0]), int(pos[1]))
            return
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.right() - WIN_W - 40, g.bottom() - WIN_H - 40)

    def select_plant(self, key):
        if key != self.state["current"]:
            self.activate(key)
            self.save_state()
            self.update_tooltip()
        self.update()
        self.bubble.update()
        if hasattr(self, "shop"):
            self.shop.update()

    def set_dark(self, on):
        self.state["dark"] = on
        _THEME["dark"] = on
        for win in [self.bubble] + list(self.windows.values()):
            win.update()
        self.save_state()

    def toggle_window(self, key):
        win = self.windows[key]
        win.setVisible(not win.isVisible())

    def toggle_shop(self):
        self.shop.setVisible(not self.shop.isVisible())

    def toggle_garden(self):
        self.garden.setVisible(not self.garden.isVisible())

    def set_bubble(self, visible):
        self.state["bubble"] = visible
        self.bubble.setVisible(visible)

    def update_tooltip(self):
        s, k = self.ps, self.kind
        self.setToolTip(f"{k.name} · {stage_name(k, s['growth'])} · "
                        f"Wachstum {s['growth']:.0f} · Wasser {s['water']:.0f} %")

    # ---------- Logik ----------

    def drain_rate(self):
        return WATER_MAX / (self.kind.drain_hours * 3600)

    def fert(self):
        f = self.ps.get("fert")
        if f and f.get("key") in FERTILIZERS and f.get("left", 0) > 0:
            return FERTILIZERS[f["key"]], f["left"]
        return None, 0

    def growth_mult(self):
        fz, _ = self.fert()
        m = 1.0 + fz.boost if fz else 1.0
        m *= 1.0 + PRESTIGE_BONUS * self.prestige_level()
        if self.helper_on("lampe"):
            m *= 1.0 + LAMP_BOOST
        if self.focus:
            m *= FOCUS_MULT
        return m

    def prestige_level(self, key=None):
        return self.state.get("prestige", {}).get(key or self.state["current"], 0)

    def prestige_summary(self):
        lvl = self.prestige_level()
        return f"Stufe {lvl} · +{lvl * PRESTIGE_BONUS * 100:.0f} %" if lvl else "–"

    def add_growth(self, amount):
        self.ps["growth"] += amount
        self.ensure_periods()
        self.state["weekly"]["growth"] = self.state["weekly"].get("growth", 0) + amount

    def popup(self, text, coin=True):
        """Einblendung über der Pflanze; mehrere erscheinen nacheinander."""
        self.popup_queue.append((text, coin))

    def release_popups(self):
        if self.popup_queue and all(pu[2] < 0.8 for pu in self.popups):
            text, coin = self.popup_queue.pop(0)
            tp = self.top_point
            self.popups.append([tp.x(), max(20.0 - SCENE_DY, tp.y() - 12), 1.0, text, coin])

    # ---------- Tages- und Wochenwerte, Erfolge ----------

    def ensure_periods(self):
        today, week = time.strftime("%Y-%m-%d"), time.strftime("%G-W%V")
        st = self.state
        if st.get("daily", {}).get("date") != today:
            st["daily"] = {"date": today, "keys": 0, "clicks": 0, "focus": 0, "focus_min": 0, "done": []}
        if st.get("weekly", {}).get("week") != week:
            st["weekly"] = {"week": week, "keys": 0, "growth": 0.0, "focus": 0, "done": []}

    def ach_value(self, key):
        st = self.state
        d, w = st["daily"], st["weekly"]
        return {
            "d_keys": d.get("keys", 0), "d_clicks": d.get("clicks", 0), "d_focus": d.get("focus", 0),
            "w_keys": w.get("keys", 0), "w_growth": int(w.get("growth", 0)), "w_focus": w.get("focus", 0),
            "g_bloom": len(st["bloomed_species"]), "g_garden": len(st["garden"]),
            "g_prestige": max(st["prestige"].values(), default=0), "g_species": len(st["bloomed_species"]),
            "g_keys": st["stats"]["keys"], "g_visitors": len(st["book"]),
        }[key]

    def ach_done_list(self, period):
        self.ensure_periods()
        if period == "daily":
            return self.state["daily"].setdefault("done", [])
        if period == "weekly":
            return self.state["weekly"].setdefault("done", [])
        return self.state.setdefault("ach_done", [])

    def ach_is_done(self, a):
        return a.key in self.ach_done_list(a.period)

    def ach_summary(self):
        done = sum(1 for a in ACHIEVEMENTS if self.ach_is_done(a))
        return f"{done} von {len(ACHIEVEMENTS)} erreicht"

    def check_achievements(self):
        self.ensure_periods()
        for a in ACHIEVEMENTS:
            done = self.ach_done_list(a.period)
            if a.key not in done and self.ach_value(a.key) >= a.target:
                done.append(a.key)
                self.state["coins"] = self.state.get("coins", 0) + a.reward
                if not self.ach_win.isVisible():
                    self.state["ach_new"] = self.state.get("ach_new", 0) + 1
                self.popup(f"+{a.reward} {a.name}")

    # ---------- Helfer ----------

    def helper_on(self, key):
        return key in self.state.get("helpers", []) and key not in self.state.get("helpers_off", [])

    def helper_action(self, key):
        hp = HELPERS[key]
        owned, off = self.state.setdefault("helpers", []), self.state.setdefault("helpers_off", [])
        if key in owned:
            if key in off:
                off.remove(key)
                msg = f"{hp.name} ist wieder eingeschaltet."
            else:
                off.append(key)
                msg = f"{hp.name} ist ausgeschaltet."
            self.save_state()
            return True, msg
        coins = self.state.get("coins", 0)
        if coins < hp.price:
            return False, f"Zu wenig Coins für {hp.name}: es fehlen {fmt_int(hp.price - coins)}."
        self.state["coins"] = coins - hp.price
        owned.append(key)
        self.save_state()
        return True, f"{hp.name} gekauft und aktiv."

    def run_helpers(self, dt):
        s, k = self.ps, self.kind
        self.drip_active = False
        if self.helper_on("tropf") and s["water"] < DRIP_MIN:
            s["water"] = min(DRIP_MIN, s["water"] + DRIP_RATE * dt)
            self.drip_active = True
        if self.helper_on("hummel"):
            self.bee_timer -= dt
            if self.bee_timer <= 0:
                self.bee_timer = random.uniform(*BEE_INTERVAL)
                self.add_growth(k.bloom_at * BEE_BOOST * self.growth_mult())
                self.bee_anim = 7.0
                self.popup("Hummel: Wachstum!", coin=False)
        self.bee_anim = max(0.0, self.bee_anim - dt)
        if self.helper_on("zwerg"):
            self.gnome_acc += dt
            if self.gnome_acc >= GNOME_INTERVAL:
                self.gnome_acc -= GNOME_INTERVAL
                self.add_growth(k.growth_per_click * self.growth_mult())
                self.gnome_hop = 1.0
        self.gnome_hop = max(0.0, self.gnome_hop - dt * 2)

    # ---------- Fokus-Timer ----------

    def start_focus(self, minutes):
        now = time.monotonic()
        self.focus = {"minutes": minutes, "start": now, "end": now + minutes * 60}
        self.focus_msg = ("", True, 0.0)
        self.popup(f"Fokus: {minutes} min", coin=False)

    def abort_focus(self):
        self.focus = None
        self.focus_msg = ("abgebrochen, kein Bonus", False, time.monotonic() + 30)

    def focus_remaining(self):
        rem = max(0.0, self.focus["end"] - time.monotonic())
        return rem, self.focus["minutes"] * 60

    def focus_message(self):
        text, ok, until = self.focus_msg
        return (text, ok) if time.monotonic() < until else ("", True)

    def focus_summary(self):
        if not self.focus:
            return "bereit"
        rem, _ = self.focus_remaining()
        m, sec = divmod(int(rem), 60)
        return f"läuft, noch {m:02d}:{sec:02d}"

    def run_focus(self):
        if self.focus and time.monotonic() >= self.focus["end"]:
            minutes = self.focus["minutes"]
            self.focus = None
            reward = minutes // 5
            self.ensure_periods()
            for bucket in (self.state["daily"], self.state["weekly"]):
                bucket["focus"] = bucket.get("focus", 0) + 1
            self.state["daily"]["focus_min"] = self.state["daily"].get("focus_min", 0) + minutes
            self.state["coins"] = self.state.get("coins", 0) + reward
            self.focus_msg = (f"geschafft! +{reward} Coins", True, time.monotonic() + 120)
            self.popup(f"+{reward} Fokus geschafft")
            self.save_state()

    # ---------- Besucher ----------

    def visitor_candidates(self):
        g, frac, _pv = self.basics()
        hour = time.localtime().tm_hour
        out = []
        for key in VISITOR_ORDER:
            v = VISITORS[key]
            if v.cond == "bloom" and frac < 1.0:
                continue
            if v.cond == "big" and frac < 0.15:
                continue
            if v.cond == "night" and 6 <= hour < 20:
                continue
            out.append(v)
        return out

    def run_visitors(self, dt):
        if self.visitor:
            if self.t - self.visitor["start"] > self.visitor["dur"]:
                self.visitor = None
            return
        self.visit_acc += dt
        if self.visit_acc < 60:
            return
        self.visit_acc -= 60
        _g, frac, _pv = self.basics()
        if frac < SEED_FRAC:
            return
        chance = 0.10 + (0.10 if frac >= 1.0 else 0.0) + (0.05 if frac >= 0.5 else 0.0)
        if random.random() < chance:
            self.spawn_visitor()

    def spawn_visitor(self, key=None):
        cands = self.visitor_candidates()
        if key:
            v = VISITORS[key]
        elif cands:
            v = random.choices(cands, weights=[c.weight for c in cands])[0]
        else:
            return
        self.visitor = {"key": v.key, "start": self.t, "dur": VISIT_DURATION,
                        "phase": random.uniform(0, 6.28), "side": random.choice((-1, 1))}
        book = self.state.setdefault("book", {})
        entry = book.setdefault(v.key, {"count": 0, "first": time.time()})
        entry["count"] += 1
        if entry["count"] == 1:
            self.popup(f"Neu: {v.name}!", coin=False)
            self.save_state()

    def visitor_pos(self):
        v = self.visitor
        vt = VISITORS[v["key"]]
        a = self.t - v["start"]
        tp = self.top_point
        cx, sy = WIN_W / 2, self.pot["soil_y"]
        if vt.move == "fly":
            return QPointF(tp.x() + math.sin(a * 0.8 + v["phase"]) * 42 * v["side"],
                           tp.y() + 28 + math.sin(a * 1.6 + v["phase"]) * 18)
        if vt.move == "crawl":
            return QPointF(tp.x() + 6 + math.sin(a * 0.5) * 5, tp.y() + 14 + (a * 1.5) % 40)
        if vt.move == "sit":
            hop = abs(math.sin(a * 6)) * 3 if int(a) % 6 == 0 else 0
            return QPointF(cx + self.pot["soil_rx"] * 0.72 * v["side"], sy - 8 - hop)
        return QPointF(tp.x() + math.sin(a * 0.35 + v["phase"]) * 30, tp.y() + 34 + math.sin(a * 0.5) * 20)

    def greet_visitor(self, pos):
        if not self.visitor:
            return False
        vp = self.visitor_pos()
        if (vp - pos).manhattanLength() > 22:
            return False
        name = VISITORS[self.visitor["key"]].name
        self.state["coins"] = self.state.get("coins", 0) + VISIT_GREET_COINS
        self.popup(f"+{VISIT_GREET_COINS} Hallo, {name}!")
        self.visitor["dur"] = self.t - self.visitor["start"] + 1.2  # fliegt davon
        return True

    def water_mult(self):
        fz, _ = self.fert()
        return 1.0 + fz.water if fz else 1.0

    def fert_summary(self):
        fz, left = self.fert()
        if not fz:
            return "–"
        parts = [f"+{fz.boost * 100:.0f} %"]
        if fz.water:
            parts.append(f"H₂O +{fz.water * 100:.0f} %")
        parts.append(fmt_left(left))
        return " · ".join(parts)

    def buy_fertilizer(self, key):
        fz = FERTILIZERS[key]
        coins = self.state.get("coins", 0)
        if coins < fz.price:
            return False, f"Zu wenig Coins für {fz.name}: es fehlen {fmt_int(fz.price - coins)}."
        self.state["coins"] = coins - fz.price
        self.ps["last_fert"] = key
        cur, left = self.fert()
        if cur and cur.key == key:
            self.ps["fert"]["left"] = left + fz.minutes * 60
            msg = f"{fz.name} verlängert: wirkt noch {fmt_left(self.ps['fert']['left'])} auf {self.kind.name}."
        else:
            self.ps["fert"] = {"key": key, "left": fz.minutes * 60}
            msg = f"{fz.name} wirkt jetzt auf {self.kind.name}"
            msg += f" (ersetzt {cur.name})." if cur else "."
        self.save_state()
        self.bubble.update()
        return True, msg

    def check_rewards(self):
        s, k = self.ps, self.kind
        earned = 0
        idx = stage_index(k, s["growth"])
        while s["stage_rewarded"] < idx:
            s["stage_rewarded"] += 1
            earned += round_half_up(STAGE_COINS[s["stage_rewarded"]] * k.coin_mult)
            if s["stage_rewarded"] == len(STAGE_FRACTIONS) - 1:
                if not s.get("bloomed_at"):
                    s["bloomed_at"] = time.time()
                species = self.state.setdefault("bloomed_species", [])
                if self.state["current"] not in species:
                    species.append(self.state["current"])
        frac = s["growth"] / k.bloom_at
        milestones = int((frac - 1.0) / MILESTONE_STEP) if frac >= 1.0 else 0
        while s["milestone_rewarded"] < milestones:
            s["milestone_rewarded"] += 1
            earned += round_half_up(MILESTONE_COINS * k.coin_mult)
        if earned:
            earned = round_half_up(earned * (1.0 + PRESTIGE_BONUS * self.prestige_level()))
            self.state["coins"] = self.state.get("coins", 0) + earned
            self.popup(f"+{fmt_int(earned)}")
            self.save_state()

    def passive_income(self, dt):
        acc = self.state.get("passive_acc", 0.0) + dt * PASSIVE_PER_HOUR / 3600
        whole = int(acc + 1e-6)  # Toleranz gegen Rundungsfehler beim Aufsummieren
        if whole:
            self.state["coins"] = self.state.get("coins", 0) + whole
            self.popup(f"+{whole}")
        self.state["passive_acc"] = acc - whole

    def water_factor(self):
        w, k = self.ps["water"], self.kind
        if w <= 0:
            return 0.0
        f = min(1.0, w / k.water_low)
        if w > k.water_high:
            f *= 0.3  # Staunässe
        return f

    def wilt(self):
        w, lim = self.ps["water"], self.kind.wilt_below
        return 0.0 if w >= lim else (lim - w) / lim

    def basics(self):
        g = self.ps["growth"]
        frac = g / self.kind.bloom_at
        return g, frac, min(1.0, frac) ** 0.5

    def tick(self):
        now = time.monotonic()
        dt = now - self.last_tick
        self.last_tick = now
        self.t += dt
        s, k = self.ps, self.kind

        wm = self.water_mult()
        s["water"] = max(0.0, s["water"] - dt * self.drain_rate() * wm)
        fz, left = self.fert()
        if fz:
            s["fert"]["left"] = left - dt
            if s["fert"]["left"] <= 0:
                s["fert"] = None
                last = s.get("last_fert")
                if self.helper_on("automat") and last in FERTILIZERS \
                        and self.state.get("coins", 0) >= FERTILIZERS[last].price:
                    self.buy_fertilizer(last)
                    self.popup(f"Automat: {FERTILIZERS[last].name}", coin=False)

        self.ensure_periods()
        n = self.keys.take()
        if n and self.state.get("keyboard_enabled", True):
            self.state["stats"]["keys"] += n
            self.state["daily"]["keys"] += n
            self.state["weekly"]["keys"] += n
        if n and k.growth_per_key > 0 and self.state.get("keyboard_enabled", True):
            s["keys_total"] += n
            self.add_growth(n * k.growth_per_key * self.water_factor() * self.growth_mult())
            s["water"] = max(0.0, s["water"] - n * k.water_per_key * wm)
            if len(self.sparkles) < 12 and s["water"] > 0:
                tp = self.top_point
                self.sparkles.append([tp.x() + random.uniform(-25, 25),
                                      tp.y() + random.uniform(-10, 20), 1.0])

        self.run_helpers(dt)
        self.run_focus()
        self.run_visitors(dt)
        self.check_rewards()
        self.passive_income(dt)
        self.update_particles(dt)
        self.sec_acc += dt
        if self.sec_acc >= 1.0:
            self.sec_acc = 0.0
            self.check_achievements()
            if self.ach_win.isVisible():
                self.ach_win.update()
        if now - self.last_save > 60:
            self.save_state()
            self.last_save = now
        if int(self.t) != int(self.t - dt):
            self.update_tooltip()
        self.update()
        if self.bubble.isVisible():
            self.bubble.update()
        if self.shop.isVisible():
            self.shop.update()
        if self.garden.isVisible() and self.ps["growth"] >= self.kind.bloom_at:
            self.garden.update(self.garden.button_rect().adjusted(-6, -6, 6, 6).toRect())
        if self.focus_win.isVisible():
            self.focus_win.update()
        if self.book_win.isVisible():
            self.book_win.update()

    def water_click(self, pos):
        s, k = self.ps, self.kind
        if self.greet_visitor(pos):
            return
        s["clicks_total"] += 1
        self.ensure_periods()
        self.state["daily"]["clicks"] += 1
        self.add_growth(k.growth_per_click * self.growth_mult())
        if s["water"] >= WATER_MAX - 0.01:
            # Wasser voll: nicht giessen, stattdessen Wachstumspartikel an der Pflanze
            tp = self.top_point
            for _ in range(4):
                if len(self.sparkles) < 24:
                    self.sparkles.append([tp.x() + random.uniform(-22, 22),
                                          tp.y() + random.uniform(-8, 24), 1.0])
        else:
            s["water"] = min(WATER_MAX, s["water"] + k.water_per_click)
            y0 = min(pos.y(), self.pot["soil_y"] - 30)
            for _ in range(3):
                self.drops.append([pos.x() + random.uniform(-8, 8),
                                   y0 - random.uniform(0, 12), random.uniform(0, 1)])
        self.update_tooltip()

    def update_particles(self, dt):
        f = dt * 20
        for d in self.drops:
            d[2] += 0.5 * f
            d[1] += d[2] * f
        self.drops = [d for d in self.drops if d[1] < self.pot["soil_y"]]
        for sp in self.sparkles:
            sp[1] -= 0.6 * f
            sp[2] -= 0.03 * f
        self.sparkles = [sp for sp in self.sparkles if sp[2] > 0]
        for pu in self.popups:
            pu[1] -= 0.45 * f
            pu[2] -= 0.012 * f
        self.popups = [pu for pu in self.popups if pu[2] > 0]
        self.release_popups()

    # ---------- Maus ----------

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.press_pos = e.position()
            self.dragging = False
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.set_bubble(not self.state.get("bubble", True))
        elif e.button() == Qt.MouseButton.RightButton:
            self.show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if (self.press_pos is not None and not self.dragging
                and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position() - self.press_pos).manhattanLength() > 6):
            self.dragging = True
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.press_pos is not None:
            if not self.dragging:
                pos = e.position()
                self.water_click(QPointF(pos.x(), pos.y() - SCENE_DY))
            self.press_pos = None
            self.dragging = False

    # ---------- Menü ----------

    def show_menu(self, global_pos):
        m = QMenu(self)
        sub = m.addMenu("Pflanze wählen")
        group = QActionGroup(sub)
        group.setExclusive(True)
        for key in PLANT_ORDER:
            k = PLANT_TYPES[key]
            label = f"{k.name}  ({k.difficulty})"
            pst = self.state["plants"].get(key)
            if pst:
                label += f"  –  {stage_name(k, pst['growth'])}"
            a = sub.addAction(label)
            a.setCheckable(True)
            a.setChecked(key == self.state["current"])
            a.setData(key)
            group.addAction(a)

        m.addSeparator()
        win_menu = m.addMenu("Fenster")
        a_bubble = win_menu.addAction("Status-Sprechblase (Mittelklick)")
        a_bubble.setCheckable(True)
        a_bubble.setChecked(self.state.get("bubble", True))
        win_menu.addSeparator()
        win_actions = {}
        for key in TOOL_ORDER:
            a = win_menu.addAction(TOOL_NAMES[key])
            a.setCheckable(True)
            a.setChecked(self.windows[key].isVisible())
            win_actions[a] = key
        set_menu = m.addMenu("Einstellungen")
        a_kb = set_menu.addAction("Tastaturanschläge zählen")
        a_kb.setCheckable(True)
        a_kb.setChecked(self.state.get("keyboard_enabled", True))
        if not self.key_source:
            a_kb.setText("Tastaturanschläge zählen (nicht verfügbar)")
            a_kb.setEnabled(False)
        a_dark = set_menu.addAction("Dunkelmodus")
        a_dark.setCheckable(True)
        a_dark.setChecked(self.state.get("dark", False))
        a_top = set_menu.addAction("Immer im Vordergrund")
        a_top.setCheckable(True)
        a_top.setChecked(self.state.get("on_top", True))
        m.addSeparator()
        a_status = m.addAction("Status anzeigen")
        a_reset = m.addAction(f"«{self.kind.name}» einlagern & neu aussäen …")
        m.addSeparator()
        a_quit = m.addAction("Beenden")

        chosen = m.exec(global_pos)
        if chosen is None:
            return
        if chosen.data() in PLANT_TYPES:
            self.select_plant(chosen.data())
        elif chosen in win_actions:
            self.toggle_window(win_actions[chosen])
        elif chosen is a_status:
            self.show_status()
        elif chosen is a_bubble:
            self.set_bubble(a_bubble.isChecked())
        elif chosen is a_dark:
            self.set_dark(a_dark.isChecked())
        elif chosen is a_kb:
            self.state["keyboard_enabled"] = a_kb.isChecked()
        elif chosen is a_top:
            self.state["on_top"] = a_top.isChecked()
            self.apply_flags()
            self.show()
            self.bubble.apply_flags()
            self.bubble.setVisible(self.state.get("bubble", True))
            for win in self.windows.values():
                visible = win.isVisible()
                win.apply_flags()
                win.setVisible(visible)
        elif chosen is a_reset:
            self.reset_plant()
        elif chosen is a_quit:
            QApplication.quit()

    def show_status(self):
        s, k = self.ps, self.kind
        days = (time.time() - s["created"]) / 86400
        src = {"evdev": "evdev (/dev/input)", "pynput": "pynput"}.get(
            self.key_source, "nicht verfügbar")
        keys = fmt_int(s["keys_total"]) if k.growth_per_key > 0 else "zählen bei dieser Pflanze nicht"
        QMessageBox.information(
            self, "Topfpflanze",
            f"Pflanze: {k.name} (Schwierigkeit: {k.difficulty})\n"
            + (f"Hinweis: {k.note}\n" if k.note else "")
            + f"Stadium: {stage_name(k, s['growth'])}\n"
            f"Wachstum: {s['growth']:.1f} (Blüte ab {fmt_int(k.bloom_at)})\n"
            f"Wasser: {s['water']:.0f} % (leer nach ca. {k.drain_hours:g} h)\n"
            f"Klicks gesamt: {fmt_int(s['clicks_total'])}\n"
            f"Tastendrücke gesamt: {keys}\n"
            f"Dünger: {self.fert_summary()}\n"
            f"Prestige: {self.prestige_summary()}\n"
            f"Helfer: {', '.join(HELPERS[h].name for h in HELPER_ORDER if self.helper_on(h)) or '–'}\n"
            f"Alter: {days:.1f} Tage\n"
            f"Coins: {fmt_int(self.state.get('coins', 0))}\n"
            f"Tastaturquelle: {src}\n"
            f"Speicherort: {STATE_FILE}")

    def reset_plant(self):
        name = self.kind.name
        key = self.state["current"]
        stage = stage_name(self.kind, self.ps["growth"])
        bloomed = self.ps["growth"] >= self.kind.bloom_at
        lvl = self.prestige_level(key)
        if bloomed:
            text = (f"«{name}» ist voll ausgewachsen: Prestige-Stufe {lvl} → {lvl + 1}.\n"
                    f"Dauerhaft +{(lvl + 1) * PRESTIGE_BONUS * 100:.0f} % Wachstum und Coins für alle "
                    f"künftigen {name}-Pflanzen.\n\nDie Pflanze kommt ins Gartenhaus und wird neu ausgesät "
                    f"(zufällige Farbe). Fortfahren?")
        else:
            text = (f"«{name}» ist noch nicht ausgewachsen (Stadium: {stage}).\n"
                    f"Sie kommt nur ins Gartenhaus, ohne Prestige-Stufe.\n\nDanach wird neu ausgesät "
                    f"(zufällige Farbe). Fortfahren?")
        answer = QMessageBox.question(self, "Einlagern & neu aussäen", text)
        if answer != QMessageBox.StandardButton.Yes:
            return
        entry = {k: self.ps.get(k) for k in ("seed", "color", "growth", "clicks_total", "keys_total",
                                              "created", "bloomed_at")}
        entry["key"] = key
        entry["archived_at"] = time.time()
        entry["prestige"] = lvl + 1 if bloomed else None
        self.state.setdefault("garden", []).append(entry)
        if bloomed:
            self.state.setdefault("prestige", {})[key] = lvl + 1
        self.state["plants"][key] = self.new_plant_state(key)
        del self.ps
        self.activate(key)
        self.save_state()
        self.update_tooltip()
        self.bubble.update()
        self.garden.update()

    def snapshot(self, entry, scale=2):
        """Zeichnet eine archivierte Pflanze als Bild (für das Gartenhaus)."""
        names = ("kind", "pot", "ps", "lean", "lean_dir", "leaf_rnd", "rnd", "blossom",
                 "flower_color", "t", "drops", "sparkles", "popups", "top_point")
        keep = {n: getattr(self, n) for n in names}
        try:
            self.kind = PLANT_TYPES[entry["key"]]
            self.pot = POTS[self.kind.pot]
            self.ps = {**self.new_plant_state(), **entry, "water": 60.0, "fert": None}
            self.setup_randomness()
            self.t, self.drops, self.sparkles, self.popups = 0.0, [], [], []
            img = QImage(WIN_W * scale, WIN_H * scale, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(QColor(0, 0, 0, 0))
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.scale(scale, scale)
            self.paint_scene(p, drop=False, particles=False)
            p.end()
            return img
        finally:
            for n, v in keep.items():
                setattr(self, n, v)

    # ---------- Zeichnen: Grundgerüst ----------

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_scene(p)
        p.end()

    def paint_scene(self, p, drop=True, particles=True):
        cx, sy = WIN_W / 2, self.pot["soil_y"]
        p.save()
        p.translate(0, SCENE_DY)
        getattr(self, "draw_pot_" + self.kind.pot)(p)
        self.draw_soil(p)
        if particles:
            self.draw_helpers_ground(p)
        p.save()  # Pflanze um den Fusspunkt vergrössern, Topf bleibt gleich
        p.translate(cx, sy)
        p.scale(PLANT_SCALE, PLANT_SCALE)
        p.translate(-cx, -sy)
        getattr(self, "draw_" + self.kind.key)(p, sy)
        p.restore()
        tp = self.top_point
        self.top_point = QPointF(cx + (tp.x() - cx) * PLANT_SCALE, sy + (tp.y() - sy) * PLANT_SCALE)
        if particles:
            self.draw_creatures(p)
            self.draw_particles(p)
        if drop:
            self.draw_water_drop(p)
        p.restore()

    def draw_helpers_ground(self, p):
        cx, sy = WIN_W / 2, self.pot["soil_y"]
        if self.helper_on("tropf"):
            end = QPointF(cx + self.pot["soil_rx"] * 0.55, sy - 1)
            tube = QPainterPath(QPointF(WIN_W - 6, sy - 46))
            tube.cubicTo(QPointF(WIN_W - 10, sy - 10), QPointF(end.x() + 20, sy - 8), end)
            p.setPen(round_pen(QColor("#4F6B4A"), 2.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(tube)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2E7D46"))
            p.drawRoundedRect(QRectF(end.x() - 3, end.y() - 3, 6, 4), 1, 1)
            if self.drip_active and int(self.t * 2) % 2 == 0:
                p.setBrush(QColor("#4FA3E0"))
                p.drawPath(_drop_path(end.x(), end.y() + 3, 1.6))
        if self.helper_on("zwerg"):
            _draw_gnome(p, QPointF(20, SCENE_H - 8), 1.0, self.gnome_hop)

    def draw_creatures(self, p):
        if self.bee_anim > 0:
            a = 7.0 - self.bee_anim
            tp = self.top_point
            pos = QPointF(tp.x() + math.cos(a * 1.8) * 34, tp.y() + 22 + math.sin(a * 3.1) * 14)
            fade = min(1.0, a, self.bee_anim)
            draw_visitor(p, "hummel", pos, 1.4, self.t, alpha=fade, flip=math.sin(a * 1.8) > 0)
        if self.visitor:
            v = self.visitor
            a = self.t - v["start"]
            fade = max(0.0, min(1.0, a / 1.5, (v["dur"] - a) / 1.2))
            pos = self.visitor_pos()
            vt = VISITORS[v["key"]]
            flip = False
            if vt.move == "fly":
                flip = math.cos(a * 0.8 + v["phase"]) * v["side"] > 0
            elif vt.move == "sit":
                flip = v["side"] < 0
            draw_visitor(p, v["key"], pos, 1.25, self.t, alpha=fade, flip=flip)

    def draw_soil(self, p):
        cx, sy = WIN_W / 2, self.pot["soil_y"]
        wet = self.ps["water"] / WATER_MAX
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix(QColor("#8A6A4A"), QColor("#4A2E1A"), wet))
        p.drawEllipse(QPointF(cx, sy), self.pot["soil_rx"], self.pot["soil_ry"])
        fz, _ = self.fert()
        if fz:  # Düngerkörner auf der Erde
            p.setBrush(QColor(fz.accent) if fz.icon == "bag" else QColor(fz.color))
            rx = self.pot["soil_rx"]
            for i in range(12):
                x = cx + (self.rnd[180 + i] - 0.5) * rx * 1.6
                p.drawEllipse(QPointF(x, sy + (self.rnd[160 + i] - 0.5) * 3), 1.3, 1.3)
        if self.kind.pot in ("terrakotta", "zink"):
            self.draw_soil_detail(p, cx, sy)
        if self.kind.pot == "beton":  # Kies
            p.setBrush(QColor("#C9C4B8"))
            for dx, dy in ((-30, 1), (-18, -2), (-6, 2), (14, -1), (26, 1), (34, -2), (-36, -1), (4, -3)):
                p.drawEllipse(QPointF(cx + dx, sy + dy), 2.6, 1.6)
        elif self.kind.pot == "schale":  # Moos
            p.setBrush(QColor("#5F8A3A"))
            for dx, w in ((-52, 12), (-20, 9), (38, 14), (62, 7)):
                p.drawEllipse(QPointF(cx + dx, sy - 0.5), w, 2.2)

    def draw_soil_detail(self, p, cx, sy):
        """Erdkrümel und kleine Steine, fest pro Topfart (ändern sich nicht bei jedem Bild)."""
        rx, ry = self.pot["soil_rx"], self.pot["soil_ry"]
        rng = random.Random(41 if self.kind.pot == "terrakotta" else 43)
        wet = self.ps["water"] / WATER_MAX

        def spot(limit=0.8):
            while True:
                dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
                if dx * dx + dy * dy < limit:
                    return QPointF(cx + dx * rx, sy + dy * ry)

        p.setPen(Qt.PenStyle.NoPen)
        dark = mix(QColor("#6E5236"), QColor("#35200F"), wet)
        light = mix(QColor("#A08262"), QColor("#654630"), wet)
        for i in range(22):  # Krümel
            p.setBrush(dark if i % 2 else light)
            c = spot()
            p.drawEllipse(c, rng.uniform(1.0, 2.2), rng.uniform(0.6, 1.2))
        stones = ("#9C9A94", "#B8B2A6", "#7E7A73", "#C9BFAE", "#8C7F6E")
        for i in range(7 if self.kind.pot == "terrakotta" else 9):  # Steinchen
            c = spot(0.7)
            w, h = rng.uniform(2.2, 3.6), rng.uniform(1.3, 2.0)
            col = QColor(stones[i % len(stones)])
            p.setBrush(col.darker(135))
            p.drawEllipse(QPointF(c.x() + 0.4, c.y() + 0.5), w, h)
            p.setBrush(col)
            p.drawEllipse(c, w, h)
            p.setBrush(QColor(255, 255, 255, 110))
            p.drawEllipse(QPointF(c.x() - w * 0.3, c.y() - h * 0.35), w * 0.35, h * 0.3)
        if self.kind.pot == "terrakotta":  # etwas Moos
            p.setBrush(QColor("#6B8E3A"))
            for dx in (-38, 30):
                p.drawEllipse(QPointF(cx + dx, sy + 1), 6, 1.8)
            p.setBrush(QColor("#86A94A"))
            for dx in (-40, 28):
                p.drawEllipse(QPointF(cx + dx, sy + 0.5), 2.5, 1.0)
        else:  # Kernschalen
            for dx, dy, a in ((-34, 1, 25), (22, -1, -40), (40, 1.5, 70)):
                p.save()
                p.translate(cx + dx, sy + dy)
                p.rotate(a)
                p.setBrush(QColor("#2E2A26"))
                p.drawEllipse(QPointF(0, 0), 2.6, 1.3)
                p.setPen(QPen(QColor("#D9D2C0"), 0.5))
                p.drawLine(QPointF(-2, 0), QPointF(2, 0))
                p.setPen(Qt.PenStyle.NoPen)
                p.restore()

    def draw_water_drop(self, p):
        k, w = self.kind, self.ps["water"]
        cx, cy, r = WIN_W / 2, self.pot["drop_y"], self.pot["drop_r"]
        path = drop_path(cx, cy, r)
        top, bottom = cy - 2.3 * r, cy + r
        ok = water_status(k, w)[1]
        fill = QColor("#4FA3E0") if ok else QColor("#E0704F")

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 90) if k.pot != "keramik" else QColor(0, 0, 0, 30))
        p.drawPath(path)
        level = bottom - (bottom - top) * w / WATER_MAX
        p.save()
        p.setClipPath(path)
        p.fillRect(QRectF(cx - r - 1, level, 2 * r + 2, bottom - level + 1), fill)
        p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(fill.darker(135), 1.1))
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 170))
        p.drawEllipse(QPointF(cx - r * 0.4, cy - r * 0.2), r * 0.18, r * 0.32)

    def draw_particles(self, p):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(80, 160, 230, 220))
        for x, y, _vy in self.drops:
            p.drawEllipse(QPointF(x, y), 2.5, 3.5)
        for x, y, life in self.sparkles:
            p.setBrush(QColor(255, 225, 90, int(200 * life)))
            p.drawEllipse(QPointF(x, y), 2 + life, 2 + life)
        if self.popups:
            font = QFont(self.font())
            font.setPixelSize(14)
            font.setBold(True)
            p.setFont(font)
            for pu in self.popups:
                x, y, life, text = pu[:4]
                coin = pu[4] if len(pu) > 4 else True
                p.setOpacity(min(1.0, life * 2))
                fm = p.fontMetrics()
                tw = fm.horizontalAdvance(text) + (18 if coin else 0)
                x0 = max(4.0, min(WIN_W - 4.0 - tw, x - tw / 2))  # im Fenster halten
                if coin:
                    draw_coin(p, QPointF(x0 + 7, y), 7)
                tx = x0 + (18 if coin else 0)
                p.setPen(QColor(60, 40, 0, 200))
                p.drawText(QPointF(tx + 1, y + 6), text)
                p.setPen(QColor("#F2C230") if coin else QColor("#FFFFFF"))
                p.drawText(QPointF(tx, y + 5), text)
            p.setOpacity(1.0)

    # ---------- Zeichnen: Töpfe ----------

    def draw_saucer_water(self, p, cx, y, rx):
        """Stehendes Wasser im Untertopf bei hohem Wasserstand."""
        w = self.ps["water"]
        if w >= 85:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(80, 160, 230, int(60 + 120 * (w - 85) / 15)))
            p.drawEllipse(QPointF(cx, y), rx, 2.2)

    def draw_pot_terrakotta(self, p):
        cx, rim_top = WIN_W / 2, 230
        body_top, bottom = rim_top + 16, SCENE_H - 8
        # Untertopf, hintere Fläche
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#8E4322"))
        p.drawEllipse(QPointF(cx, 319), 56, 4)
        self.draw_saucer_water(p, cx, 319, 52)
        body = QPainterPath()
        body.moveTo(cx - 58, body_top)
        body.lineTo(cx + 58, body_top)
        body.lineTo(cx + 44, bottom)
        body.lineTo(cx - 44, bottom)
        body.closeSubpath()
        grad = QLinearGradient(cx - 58, 0, cx + 58, 0)
        grad.setColorAt(0, QColor("#A9532C"))
        grad.setColorAt(0.4, QColor("#D27A4B"))
        grad.setColorAt(1, QColor("#9C4A26"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(body)
        rim = QRectF(cx - 66, rim_top, 132, 18)
        rgrad = QLinearGradient(rim.left(), 0, rim.right(), 0)
        rgrad.setColorAt(0, QColor("#B85F34"))
        rgrad.setColorAt(0.4, QColor("#E08C5C"))
        rgrad.setColorAt(1, QColor("#A8522B"))
        p.setBrush(QBrush(rgrad))
        p.drawRoundedRect(rim, 5, 5)
        # Untertopf, vorderer Rand
        saucer = QPainterPath()
        saucer.moveTo(cx - 57, 319)
        saucer.lineTo(cx + 57, 319)
        saucer.lineTo(cx + 50, 328)
        saucer.lineTo(cx - 50, 328)
        saucer.closeSubpath()
        sgrad = QLinearGradient(cx - 57, 0, cx + 57, 0)
        sgrad.setColorAt(0, QColor("#A9532C"))
        sgrad.setColorAt(0.4, QColor("#DC8658"))
        sgrad.setColorAt(1, QColor("#9C4A26"))
        p.setBrush(QBrush(sgrad))
        p.drawPath(saucer)
        p.setPen(QPen(QColor(255, 220, 190, 110), 1))
        p.drawLine(QPointF(cx - 56, 319.5), QPointF(cx + 56, 319.5))

    def draw_pot_beton(self, p):
        cx, top, bottom = WIN_W / 2, 250, SCENE_H - 8
        # Untertopf, hintere Fläche
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#6E6E6A"))
        p.drawRoundedRect(QRectF(cx - 50, 315, 100, 5), 1.5, 1.5)
        self.draw_saucer_water(p, cx, 317.5, 46)
        body = QPainterPath()
        body.moveTo(cx - 46, top)
        body.lineTo(cx + 46, top)
        body.lineTo(cx + 40, bottom)
        body.lineTo(cx - 40, bottom)
        body.closeSubpath()
        grad = QLinearGradient(cx - 46, 0, cx + 46, 0)
        grad.setColorAt(0, QColor("#7D7D79"))
        grad.setColorAt(0.4, QColor("#B5B5B0"))
        grad.setColorAt(1, QColor("#747470"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(body)
        rng = random.Random(7)  # feste Betonporen
        p.setBrush(QColor(70, 70, 66, 90))
        for _ in range(26):
            y = rng.uniform(top + 12, bottom - 4)
            half = 46 - (y - top) / (bottom - top) * 6 - 4
            p.drawEllipse(QPointF(cx + rng.uniform(-half, half), y), 1.0, 1.0)
        rim = QRectF(cx - 50, top - 6, 100, 10)
        rgrad = QLinearGradient(rim.left(), 0, rim.right(), 0)
        rgrad.setColorAt(0, QColor("#9A9A95"))
        rgrad.setColorAt(0.4, QColor("#CDCDC8"))
        rgrad.setColorAt(1, QColor("#8C8C88"))
        p.setBrush(QBrush(rgrad))
        p.drawRoundedRect(rim, 2, 2)
        # Untertopf, vorderer Rand
        sgrad = QLinearGradient(cx - 52, 0, cx + 52, 0)
        sgrad.setColorAt(0, QColor("#858581"))
        sgrad.setColorAt(0.4, QColor("#C4C4BF"))
        sgrad.setColorAt(1, QColor("#7A7A76"))
        p.setBrush(QBrush(sgrad))
        p.drawRoundedRect(QRectF(cx - 52, 319, 104, 9), 1.5, 1.5)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.drawLine(QPointF(cx - 51, 319.5), QPointF(cx + 51, 319.5))

    def draw_pot_keramik(self, p):
        cx, top, bottom = WIN_W / 2, 244, SCENE_H - 8
        body = QPainterPath()
        body.moveTo(cx - 44, top)
        body.lineTo(cx + 44, top)
        body.lineTo(cx + 44, bottom - 14)
        body.quadTo(QPointF(cx + 44, bottom), QPointF(cx + 30, bottom))
        body.lineTo(cx - 30, bottom)
        body.quadTo(QPointF(cx - 44, bottom), QPointF(cx - 44, bottom - 14))
        body.closeSubpath()
        grad = QLinearGradient(cx - 44, 0, cx + 44, 0)
        grad.setColorAt(0, QColor("#D8D8D2"))
        grad.setColorAt(0.4, QColor("#FBFBF8"))
        grad.setColorAt(1, QColor("#CFCFC8"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(body)
        p.save()
        p.setClipPath(body)
        p.fillRect(QRectF(cx - 50, top + 16, 100, 6), QColor("#3B6BB5"))
        p.fillRect(QRectF(cx - 50, top + 58, 100, 4), QColor("#3B6BB5"))
        p.restore()
        p.setBrush(QColor("#F4F4F0"))
        p.setPen(QPen(QColor("#C8C8C0"), 1))
        p.drawEllipse(QPointF(cx, top), 46, 6.5)

    def draw_pot_zink(self, p):
        cx, top, bottom = WIN_W / 2, 238, SCENE_H - 8
        body = QPainterPath()
        body.moveTo(cx - 58, top)
        body.lineTo(cx + 58, top)
        body.lineTo(cx + 44, bottom)
        body.lineTo(cx - 44, bottom)
        body.closeSubpath()
        grad = QLinearGradient(cx - 58, 0, cx + 58, 0)
        grad.setColorAt(0, QColor("#7B858D"))
        grad.setColorAt(0.35, QColor("#D3DAE0"))
        grad.setColorAt(0.6, QColor("#9AA4AC"))
        grad.setColorAt(1, QColor("#6F7981"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(body)
        for y in (top + 24, top + 62):  # Sicken
            half = 58 - (y - top) / (bottom - top) * 14
            p.setPen(QPen(QColor(85, 93, 100), 1.4))
            p.drawLine(QPointF(cx - half + 1, y), QPointF(cx + half - 1, y))
            p.setPen(QPen(QColor(235, 240, 244, 160), 1.0))
            p.drawLine(QPointF(cx - half + 1, y + 1.6), QPointF(cx + half - 1, y + 1.6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#6F7981"))
        p.drawRoundedRect(QRectF(cx - 67, top + 8, 9, 11), 2, 2)
        p.drawRoundedRect(QRectF(cx + 58, top + 8, 9, 11), 2, 2)
        rim = QRectF(cx - 62, top - 5, 124, 9)
        rgrad = QLinearGradient(rim.left(), 0, rim.right(), 0)
        rgrad.setColorAt(0, QColor("#8E989F"))
        rgrad.setColorAt(0.35, QColor("#E2E7EB"))
        rgrad.setColorAt(1, QColor("#7F8990"))
        p.setBrush(QBrush(rgrad))
        p.drawRoundedRect(rim, 4, 4)

    def draw_pot_schale(self, p):
        cx, top, bottom = WIN_W / 2, 290, 314
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1A2E4D"))
        p.drawRoundedRect(QRectF(cx - 66, bottom - 2, 14, 8), 2, 2)
        p.drawRoundedRect(QRectF(cx + 52, bottom - 2, 14, 8), 2, 2)
        body = QPainterPath()
        body.moveTo(cx - 82, top)
        body.lineTo(cx + 82, top)
        body.lineTo(cx + 76, bottom)
        body.lineTo(cx - 76, bottom)
        body.closeSubpath()
        grad = QLinearGradient(cx - 82, 0, cx + 82, 0)
        grad.setColorAt(0, QColor("#1D3558"))
        grad.setColorAt(0.4, QColor("#3F66A0"))
        grad.setColorAt(1, QColor("#1A2F4F"))
        p.setBrush(QBrush(grad))
        p.drawPath(body)
        p.setBrush(QColor("#4A74B0"))
        p.drawRoundedRect(QRectF(cx - 84, top - 3, 168, 6), 3, 3)

    # ---------- Zeichnen: Bausteine ----------

    def draw_seed(self, p, base):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#7A5230"))
        p.drawEllipse(QPointF(base.x() + 3, base.y() - 1), 5, 3)

    def draw_leaf(self, p, pos, angle, length, color, width=0.38):
        p.save()
        p.translate(pos)
        p.rotate(angle)
        w = length * width
        path = QPainterPath(QPointF(0, 0))
        path.quadTo(QPointF(length * 0.45, -w), QPointF(length, 0))
        path.quadTo(QPointF(length * 0.45, w), QPointF(0, 0))
        p.setPen(QPen(color.darker(130), 1))
        p.setBrush(color)
        p.drawPath(path)
        p.setPen(QPen(color.darker(145), 0.8))
        p.drawLine(QPointF(1, 0), QPointF(length * 0.85, 0))
        p.restore()

    def draw_flower(self, p, c, r, wilt, color=None):
        col = mix(color or self.flower_color, QColor("#8C7B6B"), wilt)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        for k in range(5):
            a = math.radians(k * 72 - 90)
            p.drawEllipse(QPointF(c.x() + math.cos(a) * r * 0.7, c.y() + math.sin(a) * r * 0.7),
                          r * 0.55, r * 0.55)
        p.setBrush(QColor("#F7D046"))
        p.drawEllipse(c, r * 0.38, r * 0.38)

    # ---------- Zeichnen: Wiesenblume (ursprüngliche Pflanze) ----------

    def draw_wiesenblume(self, p, sy):
        _g, frac, pv = self.basics()
        wilt = self.wilt()
        green = mix(QColor("#3FA34D"), QColor("#9A8B3A"), wilt)
        stem_col = mix(QColor("#2F7D3A"), QColor("#7D6B2E"), wilt)
        base = QPointF(WIN_W / 2, sy)
        self.top_point = base
        if frac < SEED_FRAC:
            self.draw_seed(p, base)
            length = frac / SEED_FRAC * 8
        else:
            length = 8 + pv * 180
        if length < 0.5:
            return
        sway = math.sin(self.t * 1.2) * 3 * (0.3 + pv) * (1 - wilt * 0.7)
        lean = self.lean * pv + wilt * 18 * self.lean_dir
        top = QPointF(base.x() + lean + sway, base.y() - length * (1 - wilt * 0.15))
        ctrl = QPointF(base.x() + lean * 0.2 - sway * 0.4, base.y() - length * 0.55)
        self.top_point = top
        path = QPainterPath(base)
        path.quadTo(ctrl, top)
        p.setPen(round_pen(stem_col, 1.5 + pv * 4.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        if frac < SEED_FRAC:
            return

        leaves = []
        n = int(pv * 12)
        for i in range(n):
            t = (i + 1) / (n + 2)
            pos = bezier(base, ctrl, top, t)
            scale, jitter = self.leaf_rnd[i]
            side = 1 if i % 2 == 0 else -1
            leaf_len = (12 + 30 * pv) * (1.0 - 0.4 * t) * scale
            sw = math.sin(self.t * 1.5 + i) * 3
            angle = (-30 + jitter + wilt * 60 + sw) if side > 0 else (-150 - jitter - wilt * 60 + sw)
            self.draw_leaf(p, pos, angle, leaf_len, green)
            leaves.append((pos, side, leaf_len))
        tip = 7 + 8 * pv
        self.draw_leaf(p, top, -60 + wilt * 70, tip, green.lighter(110))
        self.draw_leaf(p, top, -120 - wilt * 70, tip, green.lighter(110))

        if 0.75 <= frac < 1.0:
            f = (frac - 0.75) / 0.25
            p.setPen(QPen(stem_col, 1))
            p.setBrush(mix(QColor("#6DBE5A"), self.flower_color, f * 0.6))
            p.drawEllipse(QPointF(top.x(), top.y() - 4 - 2 * f), 3 + 2 * f, 4 + 3 * f)
        elif frac >= 1.0:
            count = min(7, 1 + int((frac - 1.0) / 0.1875))
            for pos, side, leaf_len in sorted(leaves, key=lambda lp: lp[0].y())[: count - 1]:
                fp = QPointF(pos.x() + side * leaf_len * 0.55, pos.y() - 10)
                p.setPen(QPen(stem_col, 1.2))
                p.drawLine(pos, fp)
                self.draw_flower(p, fp, 6.5, wilt)
            self.draw_flower(p, QPointF(top.x(), top.y() - 6), 9, wilt)

    # ---------- Zeichnen: Kaktus ----------

    def draw_kaktus(self, p, sy):
        _g, frac, pv = self.basics()
        wilt = self.wilt()
        cx = WIN_W / 2
        self.top_point = QPointF(cx, sy)
        if frac < SEED_FRAC:
            self.draw_seed(p, QPointF(cx, sy))
            if frac < SEED_FRAC * 0.4:
                return
        body = mix(QColor("#3E8E4E"), QColor("#A39A4E"), wilt)
        light, dark = body.lighter(125), body.darker(140)
        h = 5 + pv * 130
        w = (9 + pv * 27) * (1 - wilt * 0.15)
        top_y = sy - h
        self.top_point = QPointF(cx, top_y)

        tips = []
        arms = []
        if pv > 0.45:
            arms.append((self.lean_dir, 0.45, min(1.0, (pv - 0.45) / 0.3)))
        if pv > 0.7:
            arms.append((-self.lean_dir, 0.62, min(1.0, (pv - 0.7) / 0.3)))
        arm_w = w * 0.55
        for side, hy, a in arms:
            y0 = sy - h * hy
            x_out = cx + side * (w / 2 + 6 + 8 * a)
            up = 8 + 34 * a
            path = QPainterPath(QPointF(cx, y0))
            path.lineTo(x_out, y0)
            path.lineTo(x_out, y0 - up)
            p.setPen(round_pen(dark, arm_w + 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setPen(round_pen(body, arm_w))
            p.drawPath(path)
            p.setPen(round_pen(light, max(1.0, arm_w * 0.22)))
            p.drawLine(QPointF(x_out - side * arm_w * 0.12, y0 - arm_w * 0.4),
                       QPointF(x_out - side * arm_w * 0.12, y0 - up))
            tips.append(QPointF(x_out, y0 - up - arm_w / 2 - 1))

        rect = QRectF(cx - w / 2, top_y, w, h + 4)
        grad = QLinearGradient(rect.left(), 0, rect.right(), 0)
        grad.setColorAt(0, dark)
        grad.setColorAt(0.45, light)
        grad.setColorAt(1, dark)
        p.setPen(QPen(dark.darker(115), 1))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, w / 2, w / 2)
        p.setPen(QPen(dark, 1))
        for fx in (-0.25, 0.25):
            p.drawLine(QPointF(cx + fx * w, top_y + w * 0.35), QPointF(cx + fx * w, sy))
        if w > 14:
            p.setPen(QPen(QColor(245, 235, 200, 220), 0.9))
            y = top_y + w * 0.5
            while y < sy - 3:
                for fx in (-0.25, 0.25):
                    x = cx + fx * w
                    p.drawLine(QPointF(x - 1.5, y - 1.5), QPointF(x + 1.5, y + 1.5))
                    p.drawLine(QPointF(x - 1.5, y + 1.5), QPointF(x + 1.5, y - 1.5))
                p.drawLine(QPointF(cx - w / 2, y + 3), QPointF(cx - w / 2 - 3, y + 2))
                p.drawLine(QPointF(cx + w / 2, y + 3), QPointF(cx + w / 2 + 3, y + 2))
                y += 8

        if 0.75 <= frac < 1.0:
            f = (frac - 0.75) / 0.25
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(mix(QColor("#7FB069"), self.flower_color, f))
            p.drawEllipse(QPointF(cx, top_y - 1 - 2 * f), 2.5 + 2 * f, 3 + 2.5 * f)
        elif frac >= 1.0:
            count = min(6, 1 + int((frac - 1.0) / 0.25))
            spots = [QPointF(cx, top_y - 1)] + tips + [
                QPointF(cx - w * 0.32, top_y + 4), QPointF(cx + w * 0.32, top_y + 4),
                QPointF(cx, top_y + w * 0.6)]
            for pt in spots[:count]:
                self.draw_flower(p, pt, 6, wilt)

    # ---------- Zeichnen: Tulpe ----------

    def draw_tulip_head(self, p, pos, size, color, width, rot):
        p.save()
        p.translate(pos)
        p.rotate(rot)
        k = size / 27
        p.scale(k * width, k)
        path = QPainterPath(QPointF(-10, -2))
        path.cubicTo(QPointF(-13, -14), QPointF(-9, -22), QPointF(-6, -26))
        path.lineTo(QPointF(-2, -19))
        path.lineTo(QPointF(0, -27))
        path.lineTo(QPointF(2, -19))
        path.lineTo(QPointF(6, -26))
        path.cubicTo(QPointF(9, -22), QPointF(13, -14), QPointF(10, -2))
        path.quadTo(QPointF(0, 5), QPointF(-10, -2))
        grad = QLinearGradient(0, -27, 0, 3)
        grad.setColorAt(0, color.lighter(115))
        grad.setColorAt(1, color.darker(125))
        p.setPen(QPen(color.darker(150), 0.8))
        p.setBrush(QBrush(grad))
        p.drawPath(path)
        p.setPen(QPen(color.darker(140), 0.8))
        p.drawLine(QPointF(-2, -19), QPointF(-4, 0))
        p.drawLine(QPointF(2, -19), QPointF(4, 0))
        p.restore()

    def draw_tulpe(self, p, sy):
        _g, frac, pv = self.basics()
        wilt = self.wilt()
        cx = WIN_W / 2
        green = mix(QColor("#4C9A4A"), QColor("#9A8B3A"), wilt)
        stem_col = mix(QColor("#3C7F3A"), QColor("#7D6B2E"), wilt)
        color = mix(self.flower_color, QColor("#9C8F80"), wilt)
        self.top_point = QPointF(cx, sy - 12)

        if frac < SEED_FRAC:  # Zwiebel
            p.setPen(QPen(QColor("#8A5A34"), 1))
            p.setBrush(QColor("#C99A6B"))
            bulb = QPainterPath(QPointF(cx - 7, sy))
            bulb.cubicTo(QPointF(cx - 8, sy - 8), QPointF(cx - 2, sy - 10), QPointF(cx, sy - 14))
            bulb.cubicTo(QPointF(cx + 2, sy - 10), QPointF(cx + 8, sy - 8), QPointF(cx + 7, sy))
            bulb.closeSubpath()
            p.drawPath(bulb)
            f = frac / SEED_FRAC
            if f > 0.3:
                p.setPen(round_pen(QColor("#5FA84F"), 2))
                p.drawLine(QPointF(cx, sy - 14), QPointF(cx, sy - 14 - 6 * f))
            return

        stems = [(0.0, 1.0)]
        if frac >= 1.0:
            extra = min(2, int((frac - 1.0) / 0.5))
            if extra >= 1:
                stems.append((-24.0, 0.8))
            if extra >= 2:
                stems.append((24.0, 0.72))

        leaf_len = 12 + pv * 72
        sw = math.sin(self.t * 0.9) * 1.5
        for dx, scale in stems[1:]:
            self.draw_leaf(p, QPointF(cx + dx * 0.3, sy), (-115 if dx < 0 else -65) + sw,
                           leaf_len * 0.6, green, 0.22)
        self.draw_leaf(p, QPointF(cx - 2, sy), -104 - wilt * 45 + sw, leaf_len, green, 0.22)
        self.draw_leaf(p, QPointF(cx + 2, sy), -74 + wilt * 45 - sw, leaf_len * 0.88, green, 0.22)
        if frac < 0.15:
            self.top_point = QPointF(cx, sy - leaf_len * 0.8)
            return

        grow = max(0.0, min(1.0, (pv - 0.387) / 0.613))
        for i, (dx, scale) in enumerate(stems):
            base = QPointF(cx + dx * 0.25, sy)
            length = (18 + grow * 125) * scale
            sway = math.sin(self.t * 1.1 + i * 1.7) * 2.5 * (1 - wilt * 0.7)
            top = QPointF(base.x() + dx * 0.6 + sway + wilt * 22 * self.lean_dir,
                          base.y() - length * (1 - wilt * 0.18))
            ctrl = QPointF(base.x() + dx * 0.4, base.y() - length * 0.5)
            path = QPainterPath(base)
            path.quadTo(ctrl, top)
            p.setPen(round_pen(stem_col, 2.2 + grow * 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            if i == 0:
                self.top_point = top
            rot = wilt * 75 * self.lean_dir + sway * 1.5
            if frac < 0.5:
                continue
            if frac < 0.75:
                size = (10 + 6 * (frac - 0.5) / 0.25) * scale
                self.draw_tulip_head(p, top, size, mix(QColor("#6DAE55"), QColor("#9A8B3A"), wilt), 0.5, rot)
            elif frac < 1.0:
                f = (frac - 0.75) / 0.25
                self.draw_tulip_head(p, top, (16 + 8 * f) * scale,
                                     mix(QColor("#6DAE55"), color, 0.3 + 0.7 * f), 0.55 + 0.35 * f, rot)
            else:
                self.draw_tulip_head(p, top, 26 * scale, color, 1.0, rot)

    # ---------- Zeichnen: Sonnenblume ----------

    def draw_petal_ring(self, p, c, r_in, length, width, color, n, offset=0.0):
        p.setPen(QPen(color.darker(125), 0.6))
        p.setBrush(color)
        for k in range(n):
            p.save()
            p.translate(c)
            p.rotate(offset + k * 360 / n)
            p.drawEllipse(QRectF(r_in - 1, -width / 2, length, width))
            p.restore()

    def draw_seed_disc(self, p, c, r, wilt):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix(QColor("#4A2E14"), QColor("#5E4B36"), wilt))
        p.drawEllipse(c, r, r)
        n = int(r * r * 0.9)
        for i in range(n):
            rr = r * 0.92 * math.sqrt((i + 0.5) / n)
            a = i * 2.39996  # goldener Winkel
            p.setBrush(QColor("#2E1B0B") if i % 2 else QColor("#6B4523"))
            p.drawEllipse(QPointF(c.x() + math.cos(a) * rr, c.y() + math.sin(a) * rr), 0.8, 0.8)

    def draw_sunflower_head(self, p, c, r, wilt):
        petal = mix(self.flower_color, QColor("#9C7A3C"), wilt)
        self.draw_petal_ring(p, c, r * 0.8, r * 1.05, r * 0.42, petal.darker(108), 16, 0)
        self.draw_petal_ring(p, c, r * 0.8, r * 0.95, r * 0.4, petal, 16, 11.25)
        self.draw_seed_disc(p, c, r, wilt)

    def draw_sonnenblume(self, p, sy):
        _g, frac, pv = self.basics()
        wilt = self.wilt()
        cx = WIN_W / 2
        green = mix(QColor("#4E9A3E"), QColor("#9A8B3A"), wilt)
        stem_col = mix(QColor("#3F7F30"), QColor("#7D6B2E"), wilt)
        base = QPointF(cx, sy)
        self.top_point = base
        if frac < SEED_FRAC:
            p.save()
            p.translate(cx + 3, sy - 1)
            p.rotate(-20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2E2A26"))
            p.drawEllipse(QPointF(0, 0), 5.5, 3)
            p.setPen(QPen(QColor("#D9D2C0"), 0.8))
            p.drawLine(QPointF(-4, 0), QPointF(4, 0))
            p.restore()
            length = frac / SEED_FRAC * 8
        else:
            length = 8 + pv * 185
        if length < 0.5:
            return
        sway = math.sin(self.t * 0.9) * 2.5 * (0.3 + pv) * (1 - wilt * 0.7)
        lean = self.lean * 0.5 * pv + wilt * 14 * self.lean_dir
        top = QPointF(cx + lean + sway, sy - length * (1 - wilt * 0.1))
        ctrl = QPointF(cx + lean * 0.2 - sway * 0.3, sy - length * 0.5)
        self.top_point = top
        path = QPainterPath(base)
        path.quadTo(ctrl, top)
        p.setPen(round_pen(stem_col, 2 + pv * 6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        if frac < SEED_FRAC:
            return

        nodes = []
        n = int(pv * 8)
        for i in range(n):
            t = (i + 1) / (n + 2)
            pos = bezier(base, ctrl, top, t)
            scale, jitter = self.leaf_rnd[i]
            side = 1 if i % 2 == 0 else -1
            ll = (14 + 30 * pv) * (1.0 - 0.35 * t) * scale
            sw = math.sin(self.t * 1.3 + i) * 2.5
            angle = (-15 + jitter + wilt * 55 + sw) if side > 0 else (-165 - jitter - wilt * 55 + sw)
            self.draw_leaf(p, pos, angle, ll, green, 0.55)
            nodes.append((pos, side, ll))

        if frac < 0.5:
            tip = 6 + 8 * pv
            self.draw_leaf(p, top, -55 + wilt * 70, tip, green.lighter(110), 0.5)
            self.draw_leaf(p, top, -125 - wilt * 70, tip, green.lighter(110), 0.5)
            return

        head = QPointF(top.x() + wilt * 10 * self.lean_dir, top.y() - 2 + wilt * 8)
        if frac < 1.0:  # Knospe
            f = (frac - 0.5) / 0.5
            r = 4 + 6 * f
            if f > 0.5:
                self.draw_petal_ring(p, head, r * 0.6, r * (f - 0.5), r * 0.4,
                                     mix(self.flower_color, QColor("#9C7A3C"), wilt), 12)
            self.draw_petal_ring(p, head, r * 0.5, r * 0.7, r * 0.5, green, 10, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(green.darker(110))
            p.drawEllipse(head, r * 0.8, r * 0.8)
        else:
            extra = min(1.0, frac - 1.0)
            r = 9 + 5 * extra
            if frac >= 1.5 and nodes:
                pos, side, _ll = nodes[-1]
                fp = QPointF(pos.x() + side * 18, pos.y() - 16)
                p.setPen(round_pen(stem_col, 2))
                p.drawLine(pos, fp)
                self.draw_sunflower_head(p, fp, r * 0.55, wilt)
            self.draw_sunflower_head(p, head, r, wilt)

    # ---------- Zeichnen: Bonsai ----------

    def draw_bonsai(self, p, sy):
        _g, frac, pv = self.basics()
        wilt = self.wilt()
        cx = WIN_W / 2
        bark = mix(QColor("#6B4A32"), QColor("#8A7A62"), wilt)
        leaf_dark = mix(QColor("#355F2C"), QColor("#7F7A3E"), wilt)
        leaf_light = mix(QColor("#5E9447"), QColor("#A49C55"), wilt)

        if frac < SEED_FRAC:  # Steckling
            f = frac / SEED_FRAC
            h = 6 + 10 * f
            top = QPointF(cx + 1, sy - h)
            p.setPen(round_pen(bark, 1.6))
            p.drawLine(QPointF(cx, sy), top)
            self.draw_leaf(p, top, -40, 5 + 3 * f, leaf_light, 0.45)
            self.draw_leaf(p, top, -140, 5 + 3 * f, leaf_light, 0.45)
            self.top_point = top
            return

        d = self.lean_dir
        h = 14 + pv * 128
        bend = (10 + 20 * pv) * d
        sway = math.sin(self.t * 0.8) * 1.2 * (1 - wilt * 0.7)
        base = QPointF(cx - bend * 0.3, sy)
        c1 = QPointF(cx + bend, sy - h * 0.33)
        c2 = QPointF(cx - bend * 0.9, sy - h * 0.66)
        top = QPointF(cx + bend * 0.35 + sway, sy - h)
        self.top_point = top
        w0, w1 = 2.5 + pv * 12, 1.5 + pv * 3

        if pv > 0.35:  # sichtbare Wurzeln
            rl = (pv - 0.35) / 0.65
            p.setPen(round_pen(bark, max(1.5, w0 * 0.35)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for s in (-1, 1):
                path = QPainterPath(QPointF(base.x(), sy - 2))
                path.quadTo(QPointF(base.x() + s * (w0 * 0.6 + 6 * rl), sy - 1),
                            QPointF(base.x() + s * (w0 * 0.6 + 16 * rl), sy + 1))
                p.drawPath(path)

        steps = 18
        prev = base
        for i in range(1, steps + 1):
            t = i / steps
            pt = cubic(base, c1, c2, top, t)
            p.setPen(round_pen(bark, w0 + (w1 - w0) * t))
            p.drawLine(prev, pt)
            prev = pt

        pads = []
        ts = (0.42, 0.56, 0.68, 0.79, 0.88)
        nb = min(5, int(pv * 5.5))
        for i in range(nb):
            t = ts[i]
            start = cubic(base, c1, c2, top, t)
            side = d if i % 2 == 0 else -d
            length = (12 + 34 * pv) * (1 - 0.4 * t) * (0.85 + self.rnd[i] * 0.3)
            end = QPointF(start.x() + side * length, start.y() - length * 0.22 + sway)
            mid = QPointF(start.x() + side * length * 0.5, start.y() - length * 0.4)
            path = QPainterPath(start)
            path.quadTo(mid, end)
            p.setPen(round_pen(bark, max(1.2, (w0 + (w1 - w0) * t) * 0.45)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            pads.append((end, (7 + 10 * pv) * (1 - 0.3 * t)))
        pads.append((QPointF(top.x(), top.y() - 1), 8 + 11 * pv))

        shrink = 1 - 0.2 * wilt
        p.setPen(Qt.PenStyle.NoPen)
        for j, (c, r) in enumerate(pads):
            r *= shrink
            p.setBrush(leaf_dark)
            for k in range(7):
                ox = (self.rnd[20 + j * 14 + k * 2] - 0.5) * r * 1.8
                oy = (self.rnd[21 + j * 14 + k * 2] - 0.5) * r * 0.7
                p.drawEllipse(QPointF(c.x() + ox, c.y() + oy), r * 0.55, r * 0.45)
            p.setBrush(leaf_light)
            for k in range(4):
                ox = (self.rnd[120 + j * 8 + k * 2] - 0.5) * r * 1.4
                oy = -self.rnd[121 + j * 8 + k * 2] * r * 0.35
                p.drawEllipse(QPointF(c.x() + ox, c.y() + oy - r * 0.1), r * 0.3, r * 0.22)

        if frac >= 0.75:
            if frac < 1.0:
                count, size = int((frac - 0.75) / 0.25 * 10), 1.2
                col = mix(leaf_light, self.flower_color, 0.6)
            else:
                count, size = min(100, 16 + int((frac - 1.0) * 60)), 2.0
                col = self.flower_color
            col = mix(col, QColor("#9C8F80"), wilt)
            for i in range(count):
                a, b, c3 = self.blossom[i]
                c, r = pads[int(a * len(pads)) % len(pads)]
                r *= shrink
                pt = QPointF(c.x() + (b - 0.5) * r * 1.8, c.y() + (c3 - 0.6) * r * 0.8)
                p.setBrush(col)
                p.drawEllipse(pt, size, size)
                if frac >= 1.0:
                    p.setBrush(QColor("#E0607E"))
                    p.drawEllipse(pt, size * 0.35, size * 0.35)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # Tool-Fenster zählen nicht als Hauptfenster: ohne diese Zeile würde das
    # Schliessen eines Dialogs die Anwendung beenden.
    app.setQuitOnLastWindowClosed(False)

    plant = Plant()
    plant.show()
    plant.set_bubble(plant.state.get("bubble", True))
    app.aboutToQuit.connect(plant.save_state)

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: app.quit())
    # Die Qt-Schleife gibt Python sonst nie die Kontrolle für Signale.
    keepalive = QTimer()
    keepalive.start(500)
    keepalive.timeout.connect(lambda: None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
