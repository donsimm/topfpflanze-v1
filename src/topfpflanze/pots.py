"""Topf-Varianten («Skins») für neu ausgesäte Pflanzen: zufällig erzeugt, rein optisch.

Ein Skin färbt den vorhandenen Topf der Pflanze um (die Schattierung bleibt erhalten) und legt optional ein
Muster und Glanzpunkte darüber. So funktionieren alle fünf Topfformen, und jedes Angebot sieht anders aus.
"""

import colorsys
import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen

from .config import SCENE_H, WIN_W

CHEAP_PRICE = (20, 50, 5)        # Gold: von, bis, Schrittweite
PREMIUM_PRICE = (150, 300, 10)

PATTERN_NAMES = {"none": "", "stripes": "gestreift", "dots": "getupft", "zigzag": "Zickzack",
                 "diag": "schräg gestreift", "rim": "mit Randband"}
CHEAP_PATTERNS = ("none", "stripes", "dots", "zigzag", "diag", "rim")
PREMIUM_PATTERNS = ("none", "stripes", "dots", "zigzag", "diag", "rim", "none")

# Farbnamen nach Farbton (0..1)
HUE_NAMES = ((0.00, "Rot"), (0.06, "Orange"), (0.13, "Sonnengelb"), (0.22, "Lindgrün"), (0.33, "Grün"),
             (0.46, "Türkis"), (0.54, "Himmelblau"), (0.62, "Blau"), (0.72, "Violett"), (0.83, "Beere"),
             (0.92, "Rosa"), (1.00, "Rot"))

# Edle Materialien: (Name, dunkel, mittel, hell)
MATERIALS = (
    ("Gold", "#6E4B0B", "#E6B422", "#FFF1B0"),
    ("Silber", "#4A545E", "#BAC4CC", "#FFFFFF"),
    ("Kupfer", "#5A2A14", "#C8703F", "#FFD2B0"),
    ("Jade", "#0F4A3A", "#3DAE8A", "#C9FFE9"),
    ("Amethyst", "#3A1A5C", "#8E5BD0", "#E8D4FF"),
    ("Rosé", "#6B2E44", "#E38AA6", "#FFE3EC"),
    ("Mitternacht", "#0A1030", "#2B4A9E", "#9CC4FF"),
)

_CACHE = {}
_CACHE_MAX = 40


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(max(0.0, min(1.0, c)) * 255)) for c in rgb)


def _hsv(h, s, v):
    return _hex(colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v))))


def hue_name(h):
    return min(HUE_NAMES, key=lambda hn: abs(hn[0] - h))[1]


def _price(rng, spec):
    lo, hi, step = spec
    return rng.randrange(lo, hi + 1, step)


def new_skin(tier, rng=None):
    """Erzeugt einen zufälligen Skin: tier «cheap» (günstig, einfarbig/gemustert) oder «premium» (edles Material)."""
    rng = rng or random
    sid = "%s-%08x" % (tier[0], rng.getrandbits(32))
    if tier == "premium":
        material, dark, mid, light = rng.choice(MATERIALS)
        pattern = rng.choice(PREMIUM_PATTERNS)
        name = f"Reines {material}" if pattern == "none" else f"{material} {PATTERN_NAMES[pattern]}"
        h = colorsys.rgb_to_hsv(*(int(mid[i:i + 2], 16) / 255 for i in (1, 3, 5)))[0]
        accent = _hsv(h + 0.5, 0.35, 1.0) if rng.random() < 0.5 else "#FFFFFF"
        return {"id": sid, "tier": "premium", "name": name, "ramp": [dark, mid, light], "pattern": pattern,
                "accent": accent, "sparkle": True, "price": _price(rng, PREMIUM_PRICE)}
    h = rng.random()
    s = rng.uniform(0.45, 0.85)
    v = rng.uniform(0.68, 0.95)
    pattern = rng.choice(CHEAP_PATTERNS)
    name = hue_name(h) + (f" {PATTERN_NAMES[pattern]}" if pattern != "none" else "")
    ramp = [_hsv(h, s + 0.1, v * 0.58), _hsv(h, s, v), _hsv(h, s * 0.45, min(1.0, v + 0.18))]
    accent = "#FFF6E0" if rng.random() < 0.45 else _hsv(h + 0.5, 0.45, 0.97)
    return {"id": sid, "tier": "cheap", "name": name, "ramp": ramp, "pattern": pattern, "accent": accent,
            "sparkle": False, "price": _price(rng, CHEAP_PRICE)}


def new_offer(rng=None):
    """Angebot für eine Neuaussaat: ein günstiger und ein teurer Topf."""
    return {"cheap": new_skin("cheap", rng), "premium": new_skin("premium", rng)}


# ---------------------------------------------------------------- Zeichnen

def _base_image(plant):
    """Der unveränderte Topf der Pflanze (ohne dynamische Teile wie das Wasser im Untertopf)."""
    img = QImage(WIN_W, SCENE_H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    saved = plant.ps["water"]
    plant.ps["water"] = 0.0
    try:
        getattr(plant, "draw_pot_" + plant.kind.pot)(p)
    finally:
        plant.ps["water"] = saved
        p.end()
    return img


def _rgb(hex_):
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _recolor(base, skin):
    """Farbverlauf-Abbildung: die Helligkeit des Original-Topfs bestimmt die Farbe (dunkel → mittel → hell).
    Gibt (Bild, Umriss des Topfs) zurück."""
    img = base.convertToFormat(QImage.Format.Format_ARGB32)
    w, h, stride = img.width(), img.height(), img.bytesPerLine()
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    buf = bytearray(ptr)
    lums, box = [], [w, h, 0, 0]
    for y in range(h):
        row = y * stride
        for x in range(w):
            i = row + x * 4
            if buf[i + 3] > 8:
                lums.append(0.114 * buf[i] + 0.587 * buf[i + 1] + 0.299 * buf[i + 2])
                if x < box[0]:
                    box[0] = x
                if y < box[1]:
                    box[1] = y
                if x > box[2]:
                    box[2] = x
                if y > box[3]:
                    box[3] = y
    if not lums:
        return base, QRectF(0, 0, w, h)
    lums_sorted = sorted(lums)
    lo = lums_sorted[int(len(lums_sorted) * 0.03)]
    hi = lums_sorted[min(len(lums_sorted) - 1, int(len(lums_sorted) * 0.97))]
    span = max(1.0, hi - lo)
    dark, mid, light = (_rgb(c) for c in skin["ramp"])
    for y in range(h):
        row = y * stride
        for x in range(w):
            i = row + x * 4
            if buf[i + 3] <= 8:
                continue
            lum = 0.114 * buf[i] + 0.587 * buf[i + 1] + 0.299 * buf[i + 2]
            t = max(0.0, min(1.0, (lum - lo) / span))
            c = _mix(dark, mid, t * 2) if t < 0.5 else _mix(mid, light, (t - 0.5) * 2)
            buf[i], buf[i + 1], buf[i + 2] = int(c[2]), int(c[1]), int(c[0])
    out = QImage(bytes(buf), w, h, stride, QImage.Format.Format_ARGB32).copy()
    return out, QRectF(box[0], box[1], box[2] - box[0] + 1, box[3] - box[1] + 1)


def _star(p, c, r):
    path = QPainterPath(QPointF(c.x(), c.y() - r))
    for k in range(1, 8):
        ang = math.radians(-90 + k * 45)
        rr = r if k % 2 == 0 else r * 0.3
        path.lineTo(QPointF(c.x() + math.cos(ang) * rr, c.y() + math.sin(ang) * rr))
    path.closeSubpath()
    p.drawPath(path)


def _decorate(img, box, skin):
    """Muster und Glanzpunkte, nur auf den Topf (SourceAtop) gezeichnet."""
    out = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    accent = QColor(skin["accent"])
    accent.setAlpha(225)
    x0, y0, bw, bh = box.left(), box.top(), box.width(), box.height()
    x1 = x0 + bw
    pat = skin.get("pattern", "none")
    pen = QPen(accent, 3.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(accent)
    if pat == "stripes":
        for f, th in ((0.46, 4.0), (0.58, 2.2), (0.68, 4.0)):
            p.drawRect(QRectF(x0, y0 + bh * f, bw, th))
    elif pat == "rim":
        p.drawRect(QRectF(x0, y0 + bh * 0.02, bw, bh * 0.14))
    elif pat == "dots":
        row = 0
        yy = y0 + bh * 0.34
        while yy < y0 + bh * 0.82:
            xx = x0 + 9 + (7 if row % 2 else 0)
            while xx < x1 - 6:
                p.drawEllipse(QPointF(xx, yy), 2.3, 2.3)
                xx += 14
            yy += 12
            row += 1
    elif pat == "zigzag":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for base in (0.52, 0.66):
            path = QPainterPath(QPointF(x0, y0 + bh * base))
            xx, up = x0, True
            while xx < x1:
                xx += 8
                path.lineTo(QPointF(xx, y0 + bh * base + (-5 if up else 5)))
                up = not up
            p.drawPath(path)
    elif pat == "diag":
        p.setPen(QPen(accent, 3.2))
        xx = x0 - bh
        while xx < x1:
            p.drawLine(QPointF(xx, y0 + bh * 0.24), QPointF(xx + bh * 0.8, y0 + bh))
            xx += 13
    if skin.get("sparkle"):
        rng = random.Random(skin["id"])
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(6):
            c = QPointF(x0 + rng.uniform(0.12, 0.88) * bw, y0 + rng.uniform(0.2, 0.9) * bh)
            p.setBrush(QColor(255, 255, 255, 235))
            _star(p, c, rng.uniform(2.6, 4.4))
    p.end()
    return out


def _remember(key, value):
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value
    return value


def pot_image(plant, skin=None):
    """Bild des Topfs (Szenengrösse WIN_W × SCENE_H) mit Skin oder im Original; zwischengespeichert."""
    key = (plant.kind.pot, skin["id"] if skin else None)
    if key in _CACHE:
        return _CACHE[key][0]
    base = _base_image(plant)
    if not skin:
        return _remember(key, (base, _bbox(base)))[0]
    recolored, box = _recolor(base, skin)
    return _remember(key, (_decorate(recolored, box, skin), box))[0]


def pot_box(plant, skin=None):
    """Umriss des Topfs im Bild (für Vorschauen)."""
    pot_image(plant, skin)
    return _CACHE[(plant.kind.pot, skin["id"] if skin else None)][1]


def _bbox(img):
    """Umriss der sichtbaren (nicht durchsichtigen) Pixel."""
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    w, h, stride = img.width(), img.height(), img.bytesPerLine()
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    buf = bytes(ptr)
    x0, y0, x1, y1 = w, h, 0, 0
    for y in range(h):
        row = y * stride
        alpha = buf[row + 3:row + stride:4]
        if any(a > 8 for a in alpha):
            xs = [x for x, a in enumerate(alpha) if a > 8]
            x0, x1 = min(x0, xs[0]), max(x1, xs[-1])
            y0, y1 = min(y0, y), max(y1, y)
    return QRectF(x0, y0, max(1, x1 - x0 + 1), max(1, y1 - y0 + 1))


def clear_cache():
    _CACHE.clear()
