"""Hilfsfunktionen: Stadien, Formatierung, Geometrie."""

import time
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath

from .i18n import tr
from .data import STAGE_FRACTIONS


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
        return tr("{d} T {h} h", d=d, h=h)
    if h:
        return tr("{h} h {m} min", h=h, m=m)
    return tr("{m} min", m=m)


def fmt_left(seconds):
    seconds = max(0, int(seconds))
    h, rest = divmod(seconds, 3600)
    m = rest // 60
    if h:
        return f"{h}:{m:02d} h"
    return tr("{seconds} min", seconds=max(1, m) if seconds else 0)


def fmt_date(ts):
    return time.strftime(tr("%d.%m.%Y"), time.localtime(ts)) if ts else "–"


def fmt_datetime(ts):
    return time.strftime(tr("%d.%m.%Y %H:%M"), time.localtime(ts)) if ts else "–"


def fert_description(fz):
    text = tr("{fz}: Wachstum +{boost:.0f} % für {minutes}", fz=fz.name, boost=fz.boost * 100, minutes=fmt_left(fz.minutes * 60))
    if fz.water:
        text += tr(", Wasserverbrauch +{water:.0f} %.", water=fz.water * 100)
    else:
        text += tr(", kein Mehrverbrauch an Wasser.")
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
        return tr("zu trocken"), False
    if water > kind.water_high:
        return tr("zu nass"), False
    if water < kind.water_low:
        return tr("knapp"), True
    return tr("gut"), True
