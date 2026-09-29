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
BUBBLE_W, BUBBLE_H = 258, 200
BUBBLE_ROWS_H = 148         # Höhe des Textbereichs
ICON, ICON_GAP = 30, 7 * 2 / 3  # Pflanzensymbole in der Sprechblase
SHOP_GAP = 16 * 2 / 3        # Abstand vor dem Shop-Symbol
SHOP_W, SHOP_H = 270, 274
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
        n = len(PLANT_ORDER)
        total = (n + 2) * ICON + n * ICON_GAP + SHOP_GAP
        x0 = (self.width() - total) / 2
        y0 = self.height() - ICON - 8
        rects = [(key, QRectF(x0 + i * (ICON + ICON_GAP), y0, ICON, ICON))
                 for i, key in enumerate(PLANT_ORDER)]
        xs = x0 + n * ICON + (n - 1) * ICON_GAP + SHOP_GAP
        rects.append(("shop", QRectF(xs, y0, ICON, ICON)))
        rects.append(("garden", QRectF(xs + ICON + ICON_GAP, y0, ICON, ICON)))
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
            if key == "shop":
                self.plant.toggle_shop()
                return
            if key == "garden":
                self.plant.toggle_garden()
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
            elif label == "Coins":
                color = T("coin")
            p.setPen(color)
            vr = QRectF(r)
            if label == "Coins":
                draw_coin(p, QPointF(r.right() - 5, r.center().y()), 5)
                p.setPen(color)
                vr.setRight(r.right() - 14)
            vfont = QFont(font)
            if p.fontMetrics().horizontalAdvance(value) > r.width() - 60:
                vfont.setPixelSize(10)
            p.setFont(vfont)
            p.drawText(vr, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, value)
            p.setFont(font)

        sep_y = inner.bottom() + 3
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(rect.left() + 10, sep_y), QPointF(rect.right() - 10, sep_y))

        current = self.plant.state["current"]
        shop_open = self.plant.shop.isVisible() if hasattr(self.plant, "shop") else False
        garden_open = self.plant.garden.isVisible() if hasattr(self.plant, "garden") else False
        for key, r in self.icon_rects():
            if key in ("shop", "garden"):
                is_open = shop_open if key == "shop" else garden_open
                if key == "shop":
                    p.setPen(QPen(T("sep"), 1))
                    x = r.left() - SHOP_GAP / 2 - ICON_GAP / 2 + 3
                    p.drawLine(QPointF(x, r.top() + 4), QPointF(x, r.bottom() - 4))
                p.setPen(QPen(QColor("#D4A017"), 2.2) if is_open else QPen(T("cell_border"), 1))
                p.setBrush(T("gold_bg") if is_open else T("cell"))
                p.drawRoundedRect(r, 6, 6)
                self.draw_icon(p, key, r)
                continue
            active = key == current
            p.setPen(QPen(QColor("#2E9E44"), 2.2) if active else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if active else T("cell"))
            p.drawRoundedRect(r, 6, 6)
            self.draw_icon(p, key, r)
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

    def cell_rects(self):
        gap, x0, y0 = 6, 12, 58
        cw = (SHOP_W - 2 * x0 - (self.COLS - 1) * gap) / self.COLS
        ch = 76
        rects = []
        for i, key in enumerate(FERT_ORDER):
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
            key = self.cell_at(pos)
            if key:
                ok, msg = self.plant.buy_fertilizer(key)
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
        clickable = key is not None or self.close_rect().contains(pos)
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
                   "Dünger-Shop")

        cr = self.close_rect()
        p.setPen(QPen(T("muted"), 1.6))
        p.drawLine(cr.topLeft() + QPointF(5, 5), cr.bottomRight() - QPointF(5, 5))
        p.drawLine(QPointF(cr.right() - 5, cr.top() + 5), QPointF(cr.left() + 5, cr.bottom() - 5))

        font.setBold(False)
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(T("text2"))
        p.drawText(QRectF(12, 28, 150, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"für: {plant.kind.name}")
        draw_coin(p, QPointF(SHOP_W - 18, 37), 6)
        p.setPen(T("coin"))
        p.drawText(QRectF(SHOP_W - 140, 28, 112, 18),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt_int(coins))
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, 51), QPointF(SHOP_W - 12, 51))

        active_fz, _left = plant.fert()
        small = QFont(font)
        small.setPixelSize(10)
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
            p.drawText(QRectF(r.left() + 2, r.top() + 41, r.width() - 4, 14),
                       Qt.AlignmentFlag.AlignCenter, fz.name)
            price = fmt_int(fz.price)
            tw = p.fontMetrics().horizontalAdvance(price)
            cx = r.center().x() - (tw + 12) / 2
            draw_coin(p, QPointF(cx + 4, r.top() + 64), 4)
            p.setPen(T("coin") if affordable else T("bad"))
            p.drawText(QRectF(cx + 11, r.top() + 57, tw + 4, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, price)

        info = QRectF(12, SHOP_H - 46, SHOP_W - 24, 38)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, info.top() - 4), QPointF(SHOP_W - 12, info.top() - 4))
        if self.message and time.monotonic() < self.message_until:
            text, color = self.message, T("ok") if self.message_ok else T("bad")
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
                text = (f"{plant.kind.name} blüht und kommt mit Datum und Uhrzeit ins Gartenhaus. "
                        f"Danach wird neu ausgesät, mit zufälliger Farbe.")
                color = T("ok")
            else:
                text = (f"{plant.kind.name} ({stage_name(plant.kind, plant.ps['growth'])}) kommt ins Gartenhaus, "
                        f"obwohl sie noch nicht blüht. Danach wird neu ausgesät.")
                color = T("text2")
        elif getattr(self, "hover_delete", False):
            text, color = "Karte löschen (mit Rückfrage).", T("bad")
        elif self.hover is not None and self.hover < len(entries):
            e = entries[self.hover]
            kind = PLANT_TYPES[e["key"]]
            text = (f"{kind.name} ({stage_name(kind, e.get('growth', 0))}): gepflanzt {fmt_date(e.get('created'))}, "
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
        self.popups = []     # [x, y, life, text] – Coin-Anzeigen
        self.press_pos = None
        self.dragging = False
        self.top_point = QPointF(WIN_W / 2, 200)

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
                "garden": [], "garden_pos": None, "dark": False}

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
        for win in (self.bubble, self.shop, self.garden):
            win.update()
        self.save_state()

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
        return 1.0 + fz.boost if fz else 1.0

    def water_mult(self):
        fz, _ = self.fert()
        return 1.0 + fz.water if fz else 1.0

    def fert_summary(self):
        fz, left = self.fert()
        if not fz:
            return "–"
        parts = [f"+{fz.boost * 100:.0f} %"]
        if fz.water:
            parts.append(f"Wasser +{fz.water * 100:.0f} %")
        parts.append(fmt_left(left))
        return " · ".join(parts)

    def buy_fertilizer(self, key):
        fz = FERTILIZERS[key]
        coins = self.state.get("coins", 0)
        if coins < fz.price:
            return False, f"Zu wenig Coins für {fz.name}: es fehlen {fmt_int(fz.price - coins)}."
        self.state["coins"] = coins - fz.price
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
            if s["stage_rewarded"] == len(STAGE_FRACTIONS) - 1 and not s.get("bloomed_at"):
                s["bloomed_at"] = time.time()
        frac = s["growth"] / k.bloom_at
        milestones = int((frac - 1.0) / MILESTONE_STEP) if frac >= 1.0 else 0
        while s["milestone_rewarded"] < milestones:
            s["milestone_rewarded"] += 1
            earned += round_half_up(MILESTONE_COINS * k.coin_mult)
        if earned:
            self.state["coins"] = self.state.get("coins", 0) + earned
            tp = self.top_point
            self.popups.append([tp.x(), max(20.0 - SCENE_DY, tp.y() - 12), 1.0, f"+{fmt_int(earned)}"])
            self.save_state()

    def passive_income(self, dt):
        acc = self.state.get("passive_acc", 0.0) + dt * PASSIVE_PER_HOUR / 3600
        whole = int(acc + 1e-6)  # Toleranz gegen Rundungsfehler beim Aufsummieren
        if whole:
            self.state["coins"] = self.state.get("coins", 0) + whole
            tp = self.top_point
            self.popups.append([tp.x(), max(20.0 - SCENE_DY, tp.y() - 12), 1.0, f"+{whole}"])
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

        n = self.keys.take()
        if n and k.growth_per_key > 0 and self.state.get("keyboard_enabled", True):
            s["keys_total"] += n
            s["growth"] += n * k.growth_per_key * self.water_factor() * self.growth_mult()
            s["water"] = max(0.0, s["water"] - n * k.water_per_key * wm)
            if len(self.sparkles) < 12 and s["water"] > 0:
                tp = self.top_point
                self.sparkles.append([tp.x() + random.uniform(-25, 25),
                                      tp.y() + random.uniform(-10, 20), 1.0])

        self.check_rewards()
        self.passive_income(dt)
        self.update_particles(dt)
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

    def water_click(self, pos):
        s, k = self.ps, self.kind
        s["clicks_total"] += 1
        s["growth"] += k.growth_per_click * self.growth_mult()
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

        a_shop = m.addAction("Dünger-Shop")
        a_shop.setCheckable(True)
        a_shop.setChecked(self.shop.isVisible())
        a_garden = m.addAction("Gartenhaus")
        a_garden.setCheckable(True)
        a_garden.setChecked(self.garden.isVisible())
        a_status = m.addAction("Status anzeigen")
        a_bubble = m.addAction("Status-Sprechblase (Mittelklick)")
        a_bubble.setCheckable(True)
        a_bubble.setChecked(self.state.get("bubble", True))
        m.addSeparator()
        a_kb = m.addAction("Tastaturanschläge zählen")
        a_kb.setCheckable(True)
        a_kb.setChecked(self.state.get("keyboard_enabled", True))
        if not self.key_source:
            a_kb.setText("Tastaturanschläge zählen (nicht verfügbar)")
            a_kb.setEnabled(False)
        a_dark = m.addAction("Dunkelmodus")
        a_dark.setCheckable(True)
        a_dark.setChecked(self.state.get("dark", False))
        a_top = m.addAction("Immer im Vordergrund")
        a_top.setCheckable(True)
        a_top.setChecked(self.state.get("on_top", True))
        m.addSeparator()
        a_reset = m.addAction(f"«{self.kind.name}» einlagern & neu aussäen …")
        a_quit = m.addAction("Beenden")

        chosen = m.exec(global_pos)
        if chosen is None:
            return
        if chosen.data() in PLANT_TYPES:
            self.select_plant(chosen.data())
        elif chosen is a_shop:
            self.toggle_shop()
        elif chosen is a_garden:
            self.toggle_garden()
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
            shop_visible = self.shop.isVisible()
            self.shop.apply_flags()
            self.shop.setVisible(shop_visible)
            garden_visible = self.garden.isVisible()
            self.garden.apply_flags()
            self.garden.setVisible(garden_visible)
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
            f"Alter: {days:.1f} Tage\n"
            f"Coins: {fmt_int(self.state.get('coins', 0))}\n"
            f"Tastaturquelle: {src}\n"
            f"Speicherort: {STATE_FILE}")

    def reset_plant(self):
        name = self.kind.name
        stage = stage_name(self.kind, self.ps["growth"])
        text = (f"Die Pflanze «{name}» (Stadium: {stage}) kommt mit Datum und Uhrzeit ins Gartenhaus. "
                f"Danach wird neu ausgesät, die Blütenfarbe wird zufällig gewählt. Fortfahren?")
        answer = QMessageBox.question(self, "Einlagern & neu aussäen", text)
        if answer != QMessageBox.StandardButton.Yes:
            return
        key = self.state["current"]
        entry = {k: self.ps.get(k) for k in ("seed", "color", "growth", "clicks_total", "keys_total",
                                              "created", "bloomed_at")}
        entry["key"] = key
        entry["archived_at"] = time.time()
        self.state.setdefault("garden", []).append(entry)
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
        p.save()  # Pflanze um den Fusspunkt vergrössern, Topf bleibt gleich
        p.translate(cx, sy)
        p.scale(PLANT_SCALE, PLANT_SCALE)
        p.translate(-cx, -sy)
        getattr(self, "draw_" + self.kind.key)(p, sy)
        p.restore()
        tp = self.top_point
        self.top_point = QPointF(cx + (tp.x() - cx) * PLANT_SCALE, sy + (tp.y() - sy) * PLANT_SCALE)
        if particles:
            self.draw_particles(p)
        if drop:
            self.draw_water_drop(p)
        p.restore()

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
            for x, y, life, text in self.popups:
                p.setOpacity(min(1.0, life * 2))
                draw_coin(p, QPointF(x - 14, y), 7)
                p.setPen(QColor(60, 40, 0, 200))
                p.drawText(QPointF(x - 4 + 1, y + 5 + 1), text)
                p.setPen(QColor("#F2C230"))
                p.drawText(QPointF(x - 4, y + 5), text)
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
