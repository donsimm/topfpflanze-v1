"""Sprechblase mit Status und Werkzeugleiste."""

import math
import time
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtCore import QPointF, QRectF, Qt

from .config import (BUBBLE_H, BUBBLE_ROWS_H, BUBBLE_W, ICON, ICON_GAP, PASSIVE_PER_HOUR, PRESTIGE_AURA_PERIOD,
                     TOOL, TOOL_GAP, TOOL_ORDER)
from .data import PLANT_ORDER, PLANT_TYPES, VISITORS
from .drawing import draw_coin, draw_seed_packet, draw_star, fit_font, round_pen
from .theme import T
from .util import fmt_age, fmt_int, stage_name, water_status
from .scaling import ScaledWidget

BUBBLE_ROW_COUNT = 10   # Zeilen der Statusliste
STAGE_ROW = 1           # Zeile «Stadium»
SEED_ICON = 14          # Grösse des Aussaat-Symbols (Kantenlänge des 20×20-Feldes): sichtbar so gross wie die Münze


# ---------------------------------------------------------------- Sprechblase

class Bubble(ScaledWidget):
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

    def seed_rect(self):
        """Klickfläche des Aussaat-Symbols hinter dem Stadium (nur wenn die Pflanze für das Prestige bereit ist)."""
        if not self.plant.prestige_ready():
            return None
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        inner = QRectF(rect.left() + 10, rect.top() + 6, rect.width() - 20, BUBBLE_ROWS_H)
        line_h = inner.height() / BUBBLE_ROW_COUNT
        row = QRectF(inner.left(), inner.top() + STAGE_ROW * line_h, inner.width(), line_h)
        return QRectF(row.right() - 13, row.center().y() - 8, 16, 16)

    def over_seed(self, pos):
        r = self.seed_rect()
        return r is not None and r.contains(pos)

    def place_window(self):
        pos = self.plant.state.get("bubble_pos")
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        else:
            self.move(self.plant.x() + (self.plant.real_width() - self.real_width()) // 2,
                      max(0, self.plant.y() - self.real_height() + 40))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.over_seed(e.position()):
                self.plant.reset_plant()  # fragt vor dem Einlagern nach
                return
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
        over = self.icon_at(e.position()) is not None or self.over_seed(e.position())
        self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)

    def tooltip_text(self, key):
        """Text beim Überfahren eines Symbols: zuerst, was der Klick auslöst, darunter Angaben dazu."""
        pl = self.plant
        if key in TOOL_ORDER:
            verb = "schliessen" if pl.windows[key].isVisible() else "öffnen"
        if key == "shop":
            return (f"Dünger-Shop {verb}\nGold: {fmt_int(pl.state.get('coins', 0))} "
                    f"(+{PASSIVE_PER_HOUR} pro Stunde)")
        if key == "garden":
            return f"Gartenhaus {verb}\n{len(pl.state.get('garden', []))} Pflanze(n) eingelagert"
        if key == "ach":
            pend = len(pl.state.get("ach_pending", []))
            return f"Erfolge {verb}\n{pl.ach_summary()}" + (f"\n{pend} zum Abholen bereit" if pend else "")
        if key == "focus":
            return f"Fokus-Timer {verb}\n{pl.focus_summary()}"
        if key == "info":
            return f"Info {verb}\nSpielregeln und Werte"
        if key == "book":
            return (f"Besucher-Sammelbuch {verb}\n"
                    f"{len(pl.state.get('book', {}))} / {len(VISITORS)} entdeckt")
        if key in PLANT_TYPES:
            k = PLANT_TYPES[key]
            pst = pl.state["plants"].get(key)
            text = f"{k.name} auswählen ({k.difficulty})"
            if pst:
                text += f"\n{stage_name(k, pst['growth'])}"
            return text
        return ""

    def tooltip_at(self, pos):
        if self.over_seed(pos):
            pl = self.plant
            lvl = pl.prestige_level()
            return (f"{pl.kind.name} einlagern & neu aussäen\n"
                    f"Prestige-Stufe {lvl} → {lvl + 1}, Topf wählen und bestätigen")
        return self.tooltip_text(self.icon_at(pos))

    def paintEvent(self, _e):
        k, s = self.plant.kind, self.plant.ps
        p = self.new_painter()
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
            ("Gold", fmt_int(self.plant.state.get("coins", 0))),
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
            elif label == "Gold":
                color = T("coin")
            ready = label == "Stadium" and self.plant.prestige_ready()
            if ready:  # bereit fürs Prestige: Stadium in Gold, dahinter das Symbol für «einlagern & neu aussäen»
                color = T("coin")
            p.setPen(color)
            vr = QRectF(r)
            if label == "Gold":
                draw_coin(p, QPointF(r.right() - 5, r.center().y()), 5)
                p.setPen(color)
                vr.setRight(r.right() - 14)
            elif ready:
                breath = 0.5 - 0.5 * math.cos(2 * math.pi * self.plant.t / PRESTIGE_AURA_PERIOD)
                draw_seed_packet(p, QPointF(r.right() - 5, r.center().y()), SEED_ICON, True, breath)
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
                if key == "ach" and self.plant.state.get("ach_pending"):
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
                               str(min(9, len(self.plant.state["ach_pending"]))))
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

        elif key == "info":
            p.setPen(QPen(QColor("#2F6DB5"), 1.3))
            p.setBrush(QColor("#DCEBFA"))
            p.drawEllipse(QPointF(15, 15), 7.8, 7.8)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2F6DB5"))
            p.drawEllipse(QPointF(15, 11.2), 1.3, 1.3)
            p.drawRoundedRect(QRectF(13.9, 13.4, 2.2, 6.4), 1.0, 1.0)

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
