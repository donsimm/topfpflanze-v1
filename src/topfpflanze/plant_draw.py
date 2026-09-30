"""Zeichnen von Topf, Erde, Partikeln und den fünf Pflanzenarten."""

import math
import random
from PyQt6.QtGui import (QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                         QRadialGradient)
from PyQt6.QtCore import QPointF, QRectF, Qt

from . import debug, helper_art
from .config import PLANT_SCALE, PRESTIGE_AURA_ALPHA, PRESTIGE_AURA_PERIOD, VISITOR_SCALE, SCENE_DY, SCENE_H, SEED_FRAC, WATER_MAX, WIN_H, WIN_W
from .data import PLANT_TYPES, POTS, VISITORS
from .drawing import draw_coin, draw_visitor, round_pen
from .util import bezier, cubic, drop_path, mix, water_status


class PlantDrawMixin:
    """Zeichenmethoden des Pflanzenfensters."""

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
        p = self.new_painter()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_scene(p)
        if debug.enabled():
            debug.paint_marker(p)
        p.end()

    def paint_scene(self, p, drop=True, particles=True):
        cx, sy = WIN_W / 2, self.pot["soil_y"]
        p.save()
        p.translate(0, SCENE_DY)
        if particles:
            self.draw_prestige_aura(p)
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
            self.draw_helpers_front(p)
            self.draw_creatures(p)
            self.draw_particles(p)
        if drop:
            self.draw_water_drop(p)
        p.restore()

    def draw_prestige_aura(self, p):
        """Goldene Aura hinter der ganzen Pflanze, solange sie für das Prestige bereit ist (Blüte erreicht).
        Sehr dezent, atmet langsam: Deckkraft pendelt zwischen den Werten in PRESTIGE_AURA_ALPHA."""
        if not self.prestige_ready():
            return
        lo, hi = PRESTIGE_AURA_ALPHA
        breath = 0.5 - 0.5 * math.cos(2 * math.pi * self.t / PRESTIGE_AURA_PERIOD)  # 0..1
        alpha = lo + (hi - lo) * breath
        tp, sy = self.top_point, self.pot["soil_y"]
        cx, cy = WIN_W / 2, (tp.y() + sy) / 2 + 10
        rx = 100.0
        ry = min(210.0, (sy - tp.y()) / 2 + 70)
        g = QRadialGradient(QPointF(0, 0), rx)
        g.setColorAt(0.0, QColor(255, 214, 80, int(alpha)))
        g.setColorAt(0.55, QColor(255, 214, 80, int(alpha * 0.45)))
        g.setColorAt(1.0, QColor(255, 214, 80, 0))
        p.save()
        p.translate(cx, cy)
        p.scale(1.0, ry / rx)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(0, 0), rx, rx)
        p.restore()

    def draw_helpers_ground(self, p):
        """Helfer am Topf hinter der Pflanze: Wasseranzeige und Düngeranzeige."""
        if self.helper_on("tropf"):
            helper_art.draw_irrigation(p, self)
        if self.helper_on("automat"):
            helper_art.draw_fertilizer_machine(p, self)

    def draw_helpers_front(self, p):
        """Helfer vor der Pflanze: Gartenzwerg im Topf, Lampe (vorerst ausgeschaltet)."""
        if self.helper_on("zwerg"):
            helper_art.draw_gnome_in_pot(p, self)
        if helper_art.LAMP_VISIBLE and self.helper_on("lampe"):
            helper_art.draw_lamp(p, self)

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
            draw_visitor(p, v["key"], pos, VISITOR_SCALE, self.t, alpha=fade, flip=flip, shiny=v.get("shiny", False))

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
