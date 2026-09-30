"""Topf-Designs für neu ausgesäte Pflanzen: fester Katalog, rein optisch.

Ein Design färbt den vorhandenen Topf der Pflanze um (die Schattierung bleibt erhalten) und legt Muster darüber.
Jede Pflanze hat ihre eigenen Designs; bei jeder Aussaat wird ein günstiges und ein edles Design angeboten.
Bei Töpfen mit Untersetzer bleibt der Untersetzer ohne Muster.
"""

import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QRadialGradient

from .i18n import tr
from .config import SCENE_H, WIN_W

GOLD = "#D9B24A"
CREAM = "#F6EFDD"

# Farbverläufe: (dunkel, mittel, hell); die Helligkeit des Original-Topfs bestimmt die Farbe
RAMPS = {
    "sand": ("#8C7A5E", "#D8C7A3", "#F1E6CF"), "salbei": ("#5E6F5A", "#A7B8A0", "#DCE6D5"),
    "lehm": ("#8A5A4E", "#D1A090", "#F1D8CC"), "anthrazit": ("#14161A", "#383C42", "#6A7078"),
    "elfenbein": ("#BDB6A4", "#ECE6D6", "#FFFDF5"), "stein": ("#6B6E70", "#B9BCBD", "#EDEEEE"),
    "kalk": ("#B9B6AE", "#EDEAE3", "#FFFFFF"), "senf": ("#8A6A1E", "#D4AA45", "#F3DC9A"),
    "nachtblau": ("#0F1A33", "#2E4470", "#7C93C4"), "blush": ("#9A6A70", "#E3B6B6", "#FBE6E3"),
    "kupfer": ("#5A2A14", "#C8703F", "#FFD2B0"), "messing": ("#6E5A1E", "#C9A94A", "#F5E5A8"),
    "gold": ("#6E4B0B", "#E6B422", "#FFF1B0"), "weiss": ("#B9BDC2", "#ECEEEF", "#FFFFFF"),
    "waldgruen": ("#16301F", "#2F5A3A", "#7EAA88"), "terra": ("#9A5A3C", "#D89A73", "#F3CBB0"),
    "creme": ("#B8A98C", "#E9DFC8", "#FAF5E8"), "schwarz": ("#050607", "#1D1F22", "#4A4E54"),
}

# Untersetzer beginnt bei dieser Höhe (Szenenkoordinaten): darunter wird nichts dekoriert
DECOR_BOTTOM = {"terrakotta": 318.5, "beton": 318.5}

TIER_CHEAP, TIER_PREMIUM = "cheap", "premium"


# ---------------------------------------------------------------- Dekor-Bausteine (Koordinaten relativ zum Topf)

def _c(hex_, alpha=255):
    c = QColor(hex_)
    c.setAlpha(alpha)
    return c


def _band(p, b, f0, f1, col):
    p.fillRect(QRectF(b.left(), b.top() + b.height() * f0, b.width(), b.height() * (f1 - f0)), _c(col))


def _lines(p, b, fs, w, col):
    for f in fs:
        p.fillRect(QRectF(b.left(), b.top() + b.height() * f, b.width(), w), _c(col))


def _dip(p, b, f, col, wave=3.0):
    y = b.top() + b.height() * f
    path = QPainterPath(QPointF(b.left(), y))
    x, up = b.left(), True
    while x < b.right() + 8:
        x += 10
        path.lineTo(QPointF(x, y + (wave if up else -wave)))
        up = not up
    path.lineTo(QPointF(b.right() + 10, b.bottom() + 4))
    path.lineTo(QPointF(b.left(), b.bottom() + 4))
    path.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_c(col))
    p.drawPath(path)


def _dots(p, b, r, dx, dy, f0, f1, col):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_c(col))
    y, row = b.top() + b.height() * f0, 0
    while y < b.top() + b.height() * f1:
        x = b.left() + dx / 2 + (dx / 2 if row % 2 else 0)
        while x < b.right():
            p.drawEllipse(QPointF(x, y), r, r)
            x += dx
        y += dy
        row += 1


def _chevron(p, b, amp, step, f, w, col):
    p.setBrush(Qt.BrushStyle.NoBrush)
    pen = QPen(_c(col), w)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(pen)
    y = b.top() + b.height() * f
    path = QPainterPath(QPointF(b.left(), y))
    x, up = b.left(), True
    while x < b.right() + step:
        x += step
        path.lineTo(QPointF(x, y + (-amp if up else amp)))
        up = not up
    p.drawPath(path)


def _diamonds(p, b, s, f0, f1, col, w=2.0):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(_c(col), w))
    y, row = b.top() + b.height() * f0, 0
    while y < b.top() + b.height() * f1:
        x = b.left() + (s if row % 2 else 0)
        while x < b.right() + s:
            path = QPainterPath(QPointF(x, y - s / 2))
            path.lineTo(x + s / 2, y)
            path.lineTo(x, y + s / 2)
            path.lineTo(x - s / 2, y)
            path.closeSubpath()
            p.drawPath(path)
            x += 2 * s
        y += s / 2
        row += 1


def _speckle(p, b, n, cols, rmin, rmax, seed=1):
    rng = random.Random(seed)
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(n):
        p.setBrush(_c(rng.choice(cols)))
        r = rng.uniform(rmin, rmax)
        p.drawEllipse(QPointF(b.left() + rng.random() * b.width(), b.top() + rng.random() * b.height()), r, r)


def _terrazzo(p, b, n, cols, seed=2):
    rng = random.Random(seed)
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(n):
        p.setBrush(_c(rng.choice(cols)))
        cx = b.left() + rng.random() * b.width()
        cy = b.top() + b.height() * (0.2 + rng.random() * 0.75)
        s = rng.uniform(3, 7)
        path, a0 = QPainterPath(), rng.uniform(0, 6.28)
        for k in range(rng.choice((3, 4, 5))):
            a = a0 + k * 6.28 / 3.6 + rng.uniform(-0.4, 0.4)
            q = QPointF(cx + math.cos(a) * s * rng.uniform(0.6, 1.1), cy + math.sin(a) * s * rng.uniform(0.6, 1.1))
            path.moveTo(q) if k == 0 else path.lineTo(q)
        path.closeSubpath()
        p.drawPath(path)


def _kintsugi(p, b, col, seed=3, w=1.8):
    rng = random.Random(seed)
    p.setBrush(Qt.BrushStyle.NoBrush)
    pen = QPen(_c(col), w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    x, y = b.left() + b.width() * rng.uniform(0.3, 0.6), b.top() + b.height() * 0.12
    path, pts = QPainterPath(QPointF(x, y)), [(x, y)]
    while y < b.bottom() - 4:
        x += rng.uniform(-9, 9)
        y += rng.uniform(7, 13)
        path.lineTo(QPointF(x, y))
        pts.append((x, y))
    p.drawPath(path)
    for i in (2, 4):
        if i < len(pts):
            bx, by = pts[i]
            br, d = QPainterPath(QPointF(bx, by)), rng.choice((-1, 1))
            for _ in range(3):
                bx += d * rng.uniform(5, 10)
                by += rng.uniform(2, 8)
                br.lineTo(QPointF(bx, by))
            p.setPen(QPen(_c(col), w * 0.75, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(br)


def _hammer(p, b, n, seed, light, dark):
    rng = random.Random(seed)
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(n):
        cx = b.left() + rng.random() * b.width()
        cy = b.top() + b.height() * (0.12 + rng.random() * 0.85)
        r = rng.uniform(4, 7)
        g = QRadialGradient(QPointF(cx - r * 0.3, cy - r * 0.3), r * 1.3)
        g.setColorAt(0, _c(light, 120))
        g.setColorAt(0.6, _c(light, 20))
        g.setColorAt(1, _c(dark, 60))
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), r, r)


def _brush(p, b, col, n=26, seed=5):
    rng = random.Random(seed)
    for _ in range(n):
        y = b.top() + rng.random() * b.height()
        p.fillRect(QRectF(b.left(), y, b.width(), rng.choice((0.8, 1.2))), _c(col, rng.choice((40, 70))))


def _leaves(p, b, size, f0, f1, col, dx=None):
    dx = dx or size * 2.4
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_c(col))
    row, y = 0, b.top() + b.height() * f0
    while y < b.top() + b.height() * f1:
        x = b.left() + dx / 2 + (dx / 2 if row % 2 else 0)
        while x < b.right() + dx / 2:
            for sgn in (-1, 1):
                p.save()
                p.translate(x, y)
                p.rotate(sgn * 38 - 90)
                p.drawEllipse(QRectF(0, -size * 0.34, size, size * 0.68))
                p.restore()
            p.setPen(QPen(_c(col), 1.3))
            p.drawLine(QPointF(x, y + size * 0.25), QPointF(x, y - size * 0.75))
            p.setPen(Qt.PenStyle.NoPen)
            x += dx
        y += size * 1.35
        row += 1


def _marble(p, b, col, seed=6):
    rng = random.Random(seed)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for _ in range(4):
        pen = QPen(_c(col, rng.choice((60, 90, 130))), rng.choice((1.0, 1.6, 2.4)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        x, y = b.left() + rng.random() * b.width(), b.top() + b.height() * 0.1
        path = QPainterPath(QPointF(x, y))
        while y < b.bottom():
            nx, ny = x + rng.uniform(-14, 14), y + rng.uniform(10, 22)
            path.quadTo(QPointF((x + nx) / 2 + rng.uniform(-8, 8), (y + ny) / 2), QPointF(nx, ny))
            x, y = nx, ny
        p.drawPath(path)


OPS = {"band": _band, "lines": _lines, "dip": _dip, "dots": _dots, "chevron": _chevron, "diamonds": _diamonds,
       "speckle": _speckle, "terrazzo": _terrazzo, "kintsugi": _kintsugi, "hammer": _hammer, "brush": _brush,
       "leaves": _leaves, "marble": _marble}


# ---------------------------------------------------------------- Katalog

DESIGNS = {}   # id -> Design
BY_POT = {}    # Topfform -> [ids]


def _d(pot, id_, name, tier, price, ramp, *ops):
    full = f"{pot}/{id_}"
    DESIGNS[full] = {"id": full, "pot": pot, "name": name, "tier": tier, "price": price,
                     "ramp": RAMPS[ramp], "ops": list(ops)}
    BY_POT.setdefault(pot, []).append(full)


# --- Wiesenblume (Terrakottatopf)
_d("terrakotta", "sand-band", tr("Sand, breites Band"), TIER_CHEAP, 30, "sand", ("band", .50, .66, CREAM))
_d("terrakotta", "salbei-punkte", tr("Salbei, grosse Punkte"), TIER_CHEAP, 30, "salbei",
   ("dots", 5.5, 26, 22, .34, .88, CREAM))
_d("terrakotta", "glasur-salbei", tr("Tauchglasur Salbei"), TIER_CHEAP, 40, "creme", ("dip", .52, "#8FA58A", 3))
_d("terrakotta", "gesprenkelt-creme", tr("Gesprenkelt Creme"), TIER_CHEAP, 40, "creme",
   ("speckle", 90, ("#8A6E4E", "#B59B76", "#6A523A"), .7, 1.6, 3))
_d("terrakotta", "salbei-rauten", tr("Salbei, grosse Rauten"), TIER_CHEAP, 45, "salbei",
   ("diamonds", 12, .30, .95, CREAM, 2.2))
_d("terrakotta", "anthrazit-goldlinien", tr("Anthrazit, Goldlinien"), TIER_PREMIUM, 180, "anthrazit",
   ("lines", (.46, .56, .66), 1.6, GOLD))
_d("terrakotta", "elfenbein-goldrand", tr("Elfenbein, Goldrand"), TIER_PREMIUM, 180, "elfenbein",
   ("band", .0, .13, GOLD), ("lines", (.19,), 1.4, GOLD))
_d("terrakotta", "kintsugi-schwarz", tr("Kintsugi Schwarz"), TIER_PREMIUM, 260, "schwarz", ("kintsugi", GOLD))
_d("terrakotta", "kintsugi-weiss", tr("Kintsugi Weiss"), TIER_PREMIUM, 260, "elfenbein", ("kintsugi", "#C9A23A"))
# --- Kaktus (Betontopf)
_d("beton", "lehm-streifen", tr("Lehm, breite Streifen"), TIER_CHEAP, 30, "lehm",
   ("band", .42, .55, "#B77E6E"), ("band", .64, .77, "#B77E6E"))
_d("beton", "sprenkel-sand", tr("Sprenkel Sand"), TIER_CHEAP, 40, "sand",
   ("speckle", 80, ("#5E4E36", "#8C7A5E", "#F1E6CF"), .7, 1.5, 4))
_d("beton", "terrazzo-hell", tr("Terrazzo hell"), TIER_CHEAP, 45, "kalk",
   ("terrazzo", 40, ("#B9A98C", "#8FA58A", "#C7B7AE", "#6A6E74"), 2))
_d("beton", "schwarz-kupferband", tr("Schwarz, Kupferband"), TIER_PREMIUM, 180, "schwarz", ("band", .48, .60, "#C8703F"))
_d("beton", "schwarz-goldrand", tr("Schwarz, Goldrand"), TIER_PREMIUM, 200, "schwarz", ("band", .0, .12, GOLD))
_d("beton", "waldgruen-goldlinien", tr("Waldgrün, Goldlinien"), TIER_PREMIUM, 200, "waldgruen",
   ("lines", (.44, .52), 1.6, GOLD))
_d("beton", "marmor-weiss", tr("Marmor weiss"), TIER_PREMIUM, 240, "kalk", ("marble", "#6A6E74"))
_d("beton", "kintsugi-stein", tr("Kintsugi Stein"), TIER_PREMIUM, 260, "stein", ("kintsugi", GOLD, 7))
# --- Tulpe (Keramiktopf)
_d("keramik", "creme-salbeiband", tr("Creme, Salbeiband"), TIER_CHEAP, 30, "creme", ("band", .35, .55, "#A7B8A0"))
_d("keramik", "glasur-rose", tr("Tauchglasur Rosé"), TIER_CHEAP, 40, "weiss", ("dip", .50, "#E2B8B6", 3))
_d("keramik", "sprenkel-weiss", tr("Sprenkel Weiss"), TIER_CHEAP, 40, "weiss",
   ("speckle", 70, ("#3E4A63", "#7C8AA8", "#A7AEB8"), .7, 1.5, 5))
_d("keramik", "terrazzo-rose", tr("Terrazzo Rosé"), TIER_CHEAP, 45, "blush",
   ("terrazzo", 36, ("#FFF2EE", "#B9857F", "#8A5A54", "#F2D7D0"), 3))
_d("keramik", "weiss-goldring", tr("Weiss, Goldring"), TIER_PREMIUM, 180, "weiss",
   ("band", .0, .10, GOLD), ("lines", (.15,), 1.3, GOLD))
_d("keramik", "nachtblau-goldlinien", tr("Nachtblau, Goldlinien"), TIER_PREMIUM, 200, "nachtblau",
   ("lines", (.34, .42, .50), 1.6, GOLD))
_d("keramik", "weiss-gold-zickzack", tr("Weiss, Gold-Zickzack"), TIER_PREMIUM, 220, "weiss",
   ("chevron", 7, 18, .50, 2.4, GOLD), ("chevron", 7, 18, .66, 2.4, GOLD))
_d("keramik", "kintsugi-nachtblau", tr("Kintsugi Nachtblau"), TIER_PREMIUM, 260, "nachtblau", ("kintsugi", GOLD, 9))
# --- Sonnenblume (Zinkeimer)
_d("zink", "sprenkel-grau", tr("Sprenkel Grau"), TIER_CHEAP, 40, "stein",
   ("speckle", 100, ("#3E4145", "#F2F2EF", "#7A7E82"), .8, 1.8, 6))
_d("zink", "messing-gebuerstet", tr("Messing gebürstet"), TIER_PREMIUM, 200, "messing", ("brush", "#FFFFFF", 30))
_d("zink", "kupfer-gehaemmert", tr("Kupfer gehämmert"), TIER_PREMIUM, 220, "kupfer",
   ("hammer", 34, 4, "#FFFFFF", "#3A1408"))
_d("zink", "gold-getaucht", tr("Gold getaucht"), TIER_PREMIUM, 240, "anthrazit", ("dip", .62, "#D6AD3E", 3))
_d("zink", "gold-gehaemmert", tr("Gold gehämmert"), TIER_PREMIUM, 300, "gold", ("hammer", 34, 8, "#FFFFFF", "#5A3C08"))
# --- Bonsai (Schale): nur zwei Töpfe
_d("schale", "weisse-keramik", tr("Weisse Keramik"), TIER_CHEAP, 40, "weiss", ("lines", (.12,), 1.2, "#C9CDD2"))
_d("schale", "gold", tr("Gold"), TIER_PREMIUM, 250, "gold", ("lines", (.12,), 1.2, "#8A6512"))


def design(ref):
    """Design zu einer Kennung (auch zu einem alten Spielstand-Eintrag als Wörterbuch); None = Originaltopf."""
    if isinstance(ref, dict):
        ref = ref.get("id")
    return DESIGNS.get(ref)


def designs_for(pot, tier=None):
    return [DESIGNS[i] for i in BY_POT.get(pot, []) if tier is None or DESIGNS[i]["tier"] == tier]


def price_range(tier):
    prices = [d["price"] for d in DESIGNS.values() if d["tier"] == tier]
    return min(prices), max(prices)


def new_offer(pot, exclude=None, rng=None):
    """Angebot für eine Neuaussaat in dieser Topfform: ein günstiges und ein edles Design (Kennungen).
    Der gerade benutzte Topf («exclude») wird nach Möglichkeit nicht nochmals angeboten."""
    rng = rng or random
    offer = {}
    for tier, key in ((TIER_CHEAP, "cheap"), (TIER_PREMIUM, "premium")):
        pool = designs_for(pot, tier)
        better = [d for d in pool if d["id"] != exclude] or pool
        offer[key] = rng.choice(better)["id"] if better else None
    return offer


# ---------------------------------------------------------------- Zeichnen

_CACHE = {}
_CACHE_MAX = 40


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


def _recolor(base, ramp):
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
                box[0], box[1] = min(box[0], x), min(box[1], y)
                box[2], box[3] = max(box[2], x), max(box[3], y)
    if not lums:
        return base, QRectF(0, 0, w, h)
    lums_sorted = sorted(lums)
    lo = lums_sorted[int(len(lums_sorted) * 0.03)]
    hi = lums_sorted[min(len(lums_sorted) - 1, int(len(lums_sorted) * 0.97))]
    span = max(1.0, hi - lo)
    dark, mid, light = (_rgb(c) for c in ramp)
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


def _decorate(img, box, d):
    """Muster, nur auf den Topf (SourceAtop) und nicht auf den Untersetzer gezeichnet."""
    out = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    limit = DECOR_BOTTOM.get(d["pot"])
    if limit:
        p.setClipRect(QRectF(0, 0, out.width(), limit))
    for name, *args in d["ops"]:
        OPS[name](p, box, *args)
    p.end()
    return out


def _remember(key, value):
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value
    return value


def pot_image(plant, skin=None):
    """Bild des Topfs (Szenengrösse WIN_W × SCENE_H) mit Design (Kennung) oder im Original; zwischengespeichert."""
    d = design(skin)
    key = (plant.kind.pot, d["id"] if d else None)
    if key in _CACHE:
        return _CACHE[key][0]
    base = _base_image(plant)
    if not d:
        return _remember(key, (base, _bbox(base)))[0]
    recolored, box = _recolor(base, d["ramp"])
    return _remember(key, (_decorate(recolored, box, d), box))[0]


def pot_box(plant, skin=None):
    """Umriss des Topfs im Bild (für Vorschauen)."""
    pot_image(plant, skin)
    d = design(skin)
    return _CACHE[(plant.kind.pot, d["id"] if d else None)][1]


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
