"""Dialog «Einlagern & neu aussäen»: Topf wählen und bestätigen (im Stil der Spielfenster)."""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QPen

from . import pots
from .data import PRESTIGE_BONUS
from .drawing import draw_coin
from .panels import Panel
from .theme import T
from .util import fmt_int, stage_name

CARD_H = 152
PREVIEW_H = 74
TIER_LABEL = {"orig": "Gratis", "cheap": "Günstig", "premium": "Edel"}


class SowWin(Panel):
    W = 340

    def __init__(self, plant):
        super().__init__(plant, self.W, 420, "sow_pos")
        self.choice = "orig"
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ---------- Öffnen und Platzieren ----------

    def place_window(self):
        """In der Mitte über der Pflanze."""
        pl = self.plant
        x = pl.x() + pl.real_width() // 2 - self.real_width() // 2
        y = pl.y() + pl.real_height() // 2 - self.real_height() // 2
        self.move(x, y)

    def open_dialog(self):
        self.choice = "orig"
        self.refresh()
        self.place_window()
        self.plant.clamp_windows_to_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    # ---------- Inhalt ----------

    def info_blocks(self):
        pl = self.plant
        k = pl.kind
        if pl.prestige_ready():
            lvl = pl.prestige_level()
            return (f"«{k.name}» ist ausgewachsen",
                    f"Prestige-Stufe {lvl} → {lvl + 1}: dauerhaft +{(lvl + 1) * PRESTIGE_BONUS * 100:.0f} % Wachstum "
                    f"und Gold für alle künftigen {k.name}. Die Pflanze kommt ins Gartenhaus.", True)
        return (f"«{k.name}» ist noch nicht ausgewachsen",
                f"Stadium: {stage_name(k, pl.ps['growth'])}. Sie kommt nur ins Gartenhaus, ohne Prestige-Stufe.", False)

    def layout(self):
        base = self.font()
        head, body = self.font_px(base, 12, True), self.font_px(base, 11)
        width = self.width() - 24
        title, text, _ready = self.info_blocks()
        text_h = QFontMetricsF(body).boundingRect(QRectF(0, 0, width, 4000), int(Qt.TextFlag.TextWordWrap), text).height()
        y = 58.0
        info = (QRectF(12, y, width, 16), QRectF(12, y + 18, width, text_h + 1))
        y += 18 + text_h + 14
        heading = QRectF(12, y, width, 16)
        y += 22
        gap = 8.0
        cw = (width - 2 * gap) / 3
        cards = [(c, QRectF(12 + i * (cw + gap), y, cw, CARD_H)) for i, c in enumerate(self.plant.sow_choices())]
        y += CARD_H + 10
        chosen = QRectF(12, y, width, 16)
        gold_row = QRectF(12, y + 17, width, 14)
        y += 40
        cancel = QRectF(12, y, 96, 30)
        ok = QRectF(116, y, width - 104, 30)
        return {"head": head, "body": body, "info": info, "heading": heading, "cards": cards,
                "chosen": chosen, "gold": gold_row, "cancel": cancel, "ok": ok, "height": int(y + 30 + 14)}

    def refresh(self):
        h = self.layout()["height"]
        if h != self.height():
            self.setFixedSize(self.width(), h)
        self.update()

    def selected(self):
        return next(c for c in self.plant.sow_choices() if c["id"] == self.choice)

    def affordable(self, choice):
        return self.plant.state.get("coins", 0) >= choice["price"]

    # ---------- Eingaben ----------

    def items(self):
        lay = self.layout()
        out = [(("pot", c["id"]), r, self.affordable(c)) for c, r in lay["cards"]]
        out.append(("cancel", lay["cancel"], True))
        out.append(("ok", lay["ok"], self.affordable(self.selected())))
        return out

    def on_click(self, key):
        if key == "cancel":
            self.hide()
        elif key == "ok":
            if self.plant.confirm_sow(self.choice):
                self.hide()
        elif key[0] == "pot":
            self.choice = key[1]

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.hide()
        elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.on_click("ok")
        else:
            super().keyPressEvent(e)

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)

    # ---------- Zeichnen ----------

    def draw_preview(self, p, skin, area):
        img = pots.pot_image(self.plant, skin)
        box = pots.pot_box(self.plant, skin).adjusted(-2, -2, 2, 2)
        scale = min(area.width() / box.width(), area.height() / box.height())
        w, h = box.width() * scale, box.height() * scale
        target = QRectF(area.center().x() - w / 2, area.center().y() - h / 2, w, h)
        p.drawImage(target, img, box)

    def paintEvent(self, _e):
        pl = self.plant
        lay = self.layout()
        title, text, ready = self.info_blocks()
        p = self.begin("Einlagern & neu aussäen", pl.kind.name)
        base = self.font()
        p.setFont(lay["head"])
        p.setPen(T("coin") if ready else T("text"))
        p.drawText(lay["info"][0], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        p.setFont(lay["body"])
        p.setPen(T("text2"))
        p.drawText(lay["info"][1], int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                   text)
        p.setFont(self.font_px(base, 12, True))
        p.setPen(T("text"))
        p.drawText(lay["heading"], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "Topf für die neue Pflanze")

        for c, r in lay["cards"]:
            sel = c["id"] == self.choice
            can = self.affordable(c)
            hov = self.hover == ("pot", c["id"]) and can
            p.setOpacity(1.0 if can else 0.5)
            p.setPen(QPen(QColor("#D4A017"), 2.2) if sel else QPen(QColor("#D4A017"), 1.4) if hov
                     else QPen(T("cell_border"), 1))
            p.setBrush(T("gold_bg") if sel else T("cell"))
            p.drawRoundedRect(r, 7, 7)
            p.setFont(self.font_px(base, 9, True))
            tier_col = {"orig": T("ok"), "cheap": T("muted"), "premium": T("coin")}[c["tier"]]
            p.setPen(tier_col)
            p.drawText(QRectF(r.left() + 8, r.top() + 5, r.width() - 16, 12),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, TIER_LABEL[c["tier"]])
            self.draw_preview(p, c["skin"], QRectF(r.left() + 6, r.top() + 18, r.width() - 12, PREVIEW_H))
            p.setFont(self.font_px(base, 10, True))
            p.setPen(T("text"))
            p.drawText(QRectF(r.left() + 4, r.top() + 18 + PREVIEW_H + 4, r.width() - 8, 28),
                       int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                       c["name"])
            price_rect = QRectF(r.left() + 4, r.bottom() - 20, r.width() - 8, 16)
            p.setFont(self.font_px(base, 11, True))
            if c["price"] == 0:
                p.setPen(T("ok"))
                p.drawText(price_rect, Qt.AlignmentFlag.AlignCenter, "Gratis")
            else:
                txt = fmt_int(c["price"])
                tw = p.fontMetrics().horizontalAdvance(txt)
                left = price_rect.center().x() - (tw + 14) / 2
                draw_coin(p, QPointF(left + 5, price_rect.center().y()), 5)
                p.setPen(T("coin") if can else T("bad"))
                p.drawText(QRectF(left + 14, price_rect.top(), tw + 2, price_rect.height()),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, txt)
            if sel:  # Häkchen oben rechts
                cc = QPointF(r.right() - 11, r.top() + 11)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#D4A017"))
                p.drawEllipse(cc, 7, 7)
                p.setPen(QPen(QColor("#FFFFFF"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                              Qt.PenJoinStyle.RoundJoin))
                p.drawLine(cc + QPointF(-3, 0.2), cc + QPointF(-0.8, 2.6))
                p.drawLine(cc + QPointF(-0.8, 2.6), cc + QPointF(3.2, -2.4))
            p.setOpacity(1.0)

        sel = self.selected()
        p.setFont(self.font_px(base, 11))
        p.setPen(T("text2"))
        fm = p.fontMetrics()
        label = fm.elidedText(f"Gewählt: {sel['name']}", Qt.TextElideMode.ElideRight, int(lay["chosen"].width() - 70))
        p.drawText(lay["chosen"], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        p.setFont(self.font_px(base, 11, True))
        if sel["price"]:
            txt = f"−{fmt_int(sel['price'])}"
            tw = p.fontMetrics().horizontalAdvance(txt)
            draw_coin(p, QPointF(lay["chosen"].right() - 5, lay["chosen"].center().y()), 5)
            p.setPen(T("coin") if self.affordable(sel) else T("bad"))
            p.drawText(QRectF(lay["chosen"].right() - 14 - tw, lay["chosen"].top(), tw + 2, lay["chosen"].height()),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, txt)
        else:
            p.setPen(T("ok"))
            p.drawText(lay["chosen"], Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "Gratis")
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        coins = pl.state.get("coins", 0)
        note = "" if self.affordable(sel) else f" · es fehlen {fmt_int(sel['price'] - coins)}"
        p.drawText(lay["gold"], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"Dein Gold: {fmt_int(coins)}{note}")

        # Knöpfe
        hov = self.hover
        r = lay["cancel"]
        p.setPen(QPen(T("btn_border"), 1.2))
        p.setBrush(T("btn_bg_hover") if hov == "cancel" else T("btn_bg"))
        p.drawRoundedRect(r, 8, 8)
        p.setFont(self.font_px(base, 12, True))
        p.setPen(T("text2"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Abbrechen")
        r = lay["ok"]
        can_ok = self.affordable(sel)
        p.setOpacity(1.0 if can_ok else 0.5)
        p.setPen(QPen(QColor("#2E9E44"), 1.8 if hov == "ok" and can_ok else 1.4))
        p.setBrush(T("active_bg_hover") if hov == "ok" and can_ok else T("active_bg"))
        p.drawRoundedRect(r, 8, 8)
        p.setPen(T("button_text"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Einlagern & neu aussäen")
        p.setOpacity(1.0)
        p.end()
