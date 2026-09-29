"""Zeichenfunktionen für Symbole (Coin, Dünger, Helfer, Besucher)."""

import math
from PyQt6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PyQt6.QtCore import QPointF, QRectF, Qt

from .theme import _THEME


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
    if key == "tropf":  # Schauglas mit Wasserstand
        p.setPen(QPen(QColor("#465A66"), 1.2))
        p.setBrush(QColor("#EAF3F8"))
        p.drawRoundedRect(QRectF(13, 5, 10, 24), 5, 5)
        p.setPen(nopen)
        p.setBrush(QColor("#4FA3E0"))
        p.drawRoundedRect(QRectF(14.6, 15, 6.8, 12.4), 3, 3)
        p.setBrush(QColor(255, 255, 255, 190))
        p.drawRoundedRect(QRectF(15.2, 8, 1.6, 8), 0.8, 0.8)
        p.setBrush(QColor("#7A7A78"))
        p.drawRoundedRect(QRectF(13.5, 2, 9, 4), 1.5, 1.5)
        p.setBrush(QColor("#4FA3E0"))
        p.drawPath(_drop_path(18, 34, 1.6))
        p.setBrush(QColor("#6B4A2E"))
        p.drawRoundedRect(QRectF(6, 32, 26, 3), 1.5, 1.5)
    elif key == "hummel":
        draw_visitor(p, "hummel", QPointF(18, 19), 1.9, 0.3)
    elif key == "zwerg":
        from .helper_art import draw_gnome_big
        draw_gnome_big(p, QPointF(15, 34), 1.15)
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
