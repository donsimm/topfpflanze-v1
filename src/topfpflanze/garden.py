"""Gartenhaus (Ehrenhalle)."""

import math
import time
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtCore import QPointF, QRectF, Qt

from .config import GARDEN_H, GARDEN_W
from .data import PLANT_TYPES
from .drawing import draw_seed_packet, draw_star
from .theme import T
from .util import fmt_date, fmt_datetime, fmt_int, mix, stage_name
from .scaling import ScaledWidget


# ---------------------------------------------------------------- Gartenhaus

class Garden(ScaledWidget):
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
            self.move(max(0, self.plant.x() - self.real_width() - 10), max(0, self.plant.y() - 40))

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
        p = self.new_painter()
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
