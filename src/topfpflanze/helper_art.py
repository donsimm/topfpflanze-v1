"""Grafiken der Helfer im Pflanzenfenster (je zwei Varianten A/B zur Auswahl).

Alle Funktionen zeichnen in Szenenkoordinaten (Ursprung oben links im Zeichenbereich,
Erdoberfläche bei pot["soil_y"]). «plant» ist das Pflanzenfenster (liest nur Zustand).
"""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainterPath, QPen

from .config import WIN_W
from .data import DRIP_MIN
from .drawing import _drop_path, round_pen

# Lampe: Grafik vorerst ausgeschaltet (der Bonus von +10 % Wachstum bleibt aktiv).
# Variante «A» = Schwanenhals-Lampe, «B» = hängende LED-Leiste.
LAMP_VISIBLE = False
LAMP_STYLE = "B"


# ---------------------------------------------------------------- Füllstandsanzeigen

def _gauge_a(p, x, top, bottom, frac, color, mark=None, active=False, t=0.0):
    """Schauglas an der Topfwand: senkrechtes Glasröhrchen mit Füllstand (0..1)."""
    w = 9.0
    r = QRectF(x - w / 2, top, w, bottom - top)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(20, 20, 20, 70))  # Schatten
    p.drawRoundedRect(r.adjusted(1.2, 1.2, 1.2, 1.2), 4, 4)
    p.setBrush(QColor(255, 255, 255, 150))
    p.drawRoundedRect(r, 4, 4)
    inner = r.adjusted(1.6, 1.6, -1.6, -1.6)
    level = inner.bottom() - inner.height() * max(0.0, min(1.0, frac))
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(inner, 3, 3)
    p.setClipPath(clip)
    p.fillRect(QRectF(inner.left(), level, inner.width(), inner.bottom() - level + 1), color)
    p.fillRect(QRectF(inner.left(), level, inner.width(), 1.2), color.lighter(140))
    p.restore()
    if mark is not None:  # Mindeststand
        y = inner.bottom() - inner.height() * mark
        p.setPen(QPen(QColor("#B03A2E"), 1.0))
        p.drawLine(QPointF(r.left() - 2.5, y), QPointF(r.right() + 2.5, y))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(70, 70, 70, 200), 1.0))
    p.drawRoundedRect(r, 4, 4)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawRoundedRect(QRectF(r.left() + 2, r.top() + 4, 1.6, r.height() * 0.45), 0.8, 0.8)
    # Ventilkappe oben
    p.setBrush(QColor("#7A7A78"))
    p.drawRoundedRect(QRectF(x - 4.5, top - 4.5, 9, 5), 1.5, 1.5)
    if active and int(t * 3) % 2 == 0:  # aktiv: Kontrolllicht
        p.setBrush(QColor("#5BE07A"))
        p.drawEllipse(QPointF(x, top - 2), 1.2, 1.2)


def _gauge_geometry(plant, side):
    pot = plant.pot
    cx = WIN_W / 2
    x = cx + side * pot["soil_rx"] * 0.62
    top = pot["soil_y"] + 16
    bottom = max(top + 22, pot["drop_y"] + pot["drop_r"] + 4)
    if pot["soil_y"] > 280:  # flache Schale: Anzeige nur klein
        bottom = top + 14
    return x, top, bottom


def _water_frac(plant):
    return plant.ps["water"] / 100.0


def draw_irrigation(p, plant):
    """Tropfbewässerung: Schauglas mit Wasserstand an der Topfwand (rechts)."""
    blue = QColor("#4FA3E0")
    active = getattr(plant, "drip_active", False)
    x, top, bottom = _gauge_geometry(plant, +1)
    _gauge_a(p, x, top, bottom, _water_frac(plant), blue, mark=DRIP_MIN / 100.0, active=active, t=plant.t)
    if active and int(plant.t * 2) % 2 == 0:  # Tropfen an der Erdoberfläche
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(blue)
        p.drawPath(_drop_path(x, plant.pot["soil_y"] + 6, 1.6))


def draw_fertilizer_machine(p, plant):
    """Düngerautomat: Schauglas links in der Farbe des Düngers, Füllstand = Restlaufzeit."""
    fz, left = plant.fert()
    if not fz:  # leer: nur das Glas
        color, frac = QColor("#9AA0A6"), 0.0
    else:
        color, frac = QColor(fz.color), left / (fz.minutes * 60)
    x, top, bottom = _gauge_geometry(plant, -1)
    _gauge_a(p, x, top, bottom, frac, color, mark=None, active=bool(fz), t=plant.t)


# ---------------------------------------------------------------- Gartenzwerg

def _arm(p, shoulder, hand, skin=QColor("#2F5FA8")):
    p.setPen(round_pen(skin, 2.4))
    p.drawLine(shoulder, hand)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#F2C9A0"))
    p.drawEllipse(hand, 1.7, 1.7)


def draw_gnome_big(p, feet, s, hop=0.0, t=0.0):
    """Grosser Gartenzwerg mit Schaufel (s = 1: ca. 26 px hoch); Füsse bei «feet»."""
    p.save()
    p.translate(feet.x(), feet.y() - hop * 4 * s)
    p.scale(s, s)
    p.setPen(round_pen(QColor("#8A6A3E"), 1.4))
    p.drawLine(QPointF(8, 0), QPointF(11, -19))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#9AA0A6"))
    blade = QPainterPath(QPointF(6.2, 1.5))
    blade.lineTo(10.2, 1.5)
    blade.lineTo(9.6, -3.5)
    blade.lineTo(6.8, -3.5)
    blade.closeSubpath()
    p.drawPath(blade)
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
    _arm(p, QPointF(-4, -11), QPointF(-7, -6))
    _arm(p, QPointF(4, -11), QPointF(9, -10))
    hat = QPainterPath(QPointF(-4.8, -17))
    hat.lineTo(4.8, -17)
    hat.quadTo(QPointF(2, -24), QPointF(-1, -27))
    hat.closeSubpath()
    p.setBrush(QColor("#D62828"))
    p.drawPath(hat)
    p.restore()


def draw_gnome_in_pot(p, plant):
    pot = plant.pot
    cx, sy = WIN_W / 2, pot["soil_y"]
    x = cx - pot["soil_rx"] * 0.6
    feet = QPointF(x, sy + 2)
    draw_gnome_big(p, feet, 2.7, getattr(plant, "gnome_hop", 0.0), plant.t)
    # Erdhäufchen vor den Füssen: der Zwerg steht «im» Topf
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#4A3728"))
    p.drawEllipse(QPointF(x, sy + 3), 15, 4.2)
    p.setBrush(QColor("#5C4632"))
    p.drawEllipse(QPointF(x + 3, sy + 1.8), 8, 2.4)


# ---------------------------------------------------------------- Pflanzenlampe

def draw_lamp(p, plant):
    """Pflanzenlampe mit sichtbarem Lichtkegel (über der Pflanze gezeichnet)."""
    pot = plant.pot
    cx, sy = WIN_W / 2, pot["soil_y"]
    pulse = 0.5 + 0.5 * math.sin(plant.t * 2.0)
    if LAMP_STYLE == "A":
        # Schwanenhals-Lampe, am Topfrand rechts eingeklemmt
        base = QPointF(cx + pot["soil_rx"] + 4, sy + 2)
        head = QPointF(cx + 38, -22)
        arm = QPainterPath(base)
        arm.cubicTo(QPointF(base.x() + 8, sy - 110), QPointF(head.x() + 26, head.y() + 60), head)
        # Lichtkegel
        cone = QPainterPath(QPointF(head.x() - 5, head.y() + 7))
        cone.lineTo(QPointF(cx - 62, sy - 105))
        cone.lineTo(QPointF(cx + 12, sy - 105))
        cone.lineTo(QPointF(head.x() + 5, head.y() + 7))
        cone.closeSubpath()
        g = QLinearGradient(head, QPointF(cx - 24, sy - 105))
        g.setColorAt(0, QColor(255, 120, 230, int(60 + 25 * pulse)))
        g.setColorAt(1, QColor(255, 120, 230, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawPath(cone)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(round_pen(QColor("#4A4A4A"), 2.6))
        p.drawPath(arm)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#5A5A5A"))
        p.drawRoundedRect(QRectF(base.x() - 4, base.y() - 3, 8, 7), 1.5, 1.5)  # Klemme
        # Lampenschirm (Halbschale, zeigt nach unten-links)
        p.save()
        p.translate(head)
        p.rotate(-18)
        shade = QPainterPath(QPointF(-10, 6))
        shade.quadTo(QPointF(-9, -8), QPointF(0, -8))
        shade.quadTo(QPointF(9, -8), QPointF(10, 6))
        shade.closeSubpath()
        p.setBrush(QColor("#3C3C3C"))
        p.drawPath(shade)
        p.setBrush(QColor(255, 235, 250))
        p.drawEllipse(QPointF(0, 6), 8, 2.4)
        p.restore()
    else:
        # Hängende LED-Leiste mit senkrechten Lichtstrahlen
        y = -34
        left, right = cx - 52, cx + 52
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(7):
            x = left + 10 + i * (right - left - 20) / 6
            g = QLinearGradient(QPointF(x, y + 5), QPointF(x, sy - 110))
            g.setColorAt(0, QColor(255, 110, 225, int(55 + 20 * pulse)))
            g.setColorAt(1, QColor(255, 110, 225, 0))
            p.setBrush(QBrush(g))
            p.drawPolygon([QPointF(x - 3, y + 5), QPointF(x + 3, y + 5),
                           QPointF(x + 9 + (x - cx) * 0.12, sy - 110), QPointF(x - 9 + (x - cx) * 0.12, sy - 110)])
        p.setPen(QPen(QColor("#666666"), 0.9))
        p.drawLine(QPointF(left + 6, y), QPointF(left + 2, -50))
        p.drawLine(QPointF(right - 6, y), QPointF(right - 2, -50))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#4A4A4A"))
        p.drawRoundedRect(QRectF(left, y - 3, right - left, 8), 3, 3)
        for i in range(7):
            x = left + 10 + i * (right - left - 20) / 6
            p.setBrush(QColor(255, 190, 245))
            p.drawEllipse(QPointF(x, y + 3), 1.8, 1.4)
