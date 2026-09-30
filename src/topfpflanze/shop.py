"""Dünger- und Helfer-Shop."""

import time
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtCore import QPointF, QRectF, Qt

from .i18n import tr
from .config import PASSIVE_PER_HOUR, SHOP_H, SHOP_W
from .data import FERTILIZERS, FERT_ORDER, HELPERS, HELPER_ORDER
from .drawing import draw_coin, draw_fert_icon, draw_helper_icon, fit_font
from .theme import T
from .util import fert_description, fmt_int
from .scaling import ScaledWidget


# ---------------------------------------------------------------- Dünger-Shop

class Shop(ScaledWidget):
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
            self.move(max(0, self.plant.x() - self.real_width() - 10), max(0, self.plant.y()))

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
        p = self.new_painter()
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
                   tr("Shop"))

        cr = self.close_rect()
        p.setPen(QPen(T("muted"), 1.6))
        p.drawLine(cr.topLeft() + QPointF(5, 5), cr.bottomRight() - QPointF(5, 5))
        p.drawLine(QPointF(cr.right() - 5, cr.top() + 5), QPointF(cr.left() + 5, cr.bottom() - 5))

        font.setBold(False)
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(T("text2"))
        p.drawText(QRectF(12, 28, 170, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   tr("für: {v}", v=plant.kind.name) if self.tab == "duenger" else tr("für alle Pflanzen"))
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
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, tr("Dünger") if tab == "duenger" else tr("Helfer"))
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
            text = f"{hp.name}: {hp.desc} " + (tr("Klick schaltet ein oder aus.") if have else tr("Klick kauft den Helfer."))
            color = T("text3")
        elif self.tab == "helfer":
            text, color = tr("Helfer arbeiten automatisch für jede ausgewählte Pflanze. Einmal kaufen, dauerhaft nutzen."), T("muted")
        elif self.hover:
            text, color = fert_description(FERTILIZERS[self.hover]), T("text3")
        elif active_fz:
            text, color = tr("Aktiv: {fert_summary}", fert_summary=plant.fert_summary()), T("ok")
        else:
            text, color = (tr("Dünger anklicken, um ihn für die ausgewählte Pflanze zu kaufen. Passives Einkommen: {v} Gold pro Stunde.", v=PASSIVE_PER_HOUR)), T("muted")
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
                           Qt.AlignmentFlag.AlignCenter, tr("aktiv") if on else tr("ausgeschaltet"))
            else:
                price = fmt_int(hp.price)
                tw = p.fontMetrics().horizontalAdvance(price)
                cx = r.center().x() - (tw + 12) / 2
                draw_coin(p, QPointF(cx + 4, r.top() + 64), 4)
                p.setPen(T("coin") if affordable else T("bad"))
                p.drawText(QRectF(cx + 11, r.top() + 57, tw + 4, 14),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, price)
