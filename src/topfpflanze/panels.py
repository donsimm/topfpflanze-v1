"""Zusatzfenster: Erfolge, Fokus-Timer, Besucher-Sammelbuch."""

import math
import time
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtCore import QPointF, QRectF, Qt

from .data import MASTERY_NAMES, MASTERY_STEPS, VARIANTS, ACHIEVEMENTS, FOCUS_MULT, FOCUS_PRESETS, VISITORS, VISITOR_ORDER, VISIT_GREET_COINS
from .drawing import draw_coin, draw_gift, draw_star, draw_visitor, round_pen
from .theme import T, _THEME
from .util import fmt_age, fmt_datetime, fmt_int, fmt_left
from .scaling import ScaledWidget


# ---------------------------------------------------------------- Weitere Fenster

TIER_COLORS = (QColor("#B87333"), QColor("#9AA4AE"), QColor("#E0A800"))  # Bronze, Silber, Gold


class Panel(ScaledWidget):
    """Gemeinsame Grundlage für Erfolge, Fokus-Timer und Sammelbuch (Stil der Sprechblase)."""

    def __init__(self, plant, w, h, pos_key):
        super().__init__()
        self.plant = plant
        self.pos_key = pos_key
        self.hover = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(w, h)
        self.setMouseTracking(True)
        self.place_window()

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.plant.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def place_window(self):
        pos = self.plant.state.get(self.pos_key)
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        else:
            b = self.plant.bubble
            self.move(max(0, b.x() - self.real_width() - 10), max(0, b.y()))

    def close_rect(self):
        return QRectF(self.width() - 28, 8, 18, 18)

    def items(self):
        """Liste von (Schlüssel, Rechteck, anklickbar)."""
        return []

    def item_at(self, pos):
        for key, r, _c in self.items():
            if r.contains(pos):
                return key
        return None

    def on_click(self, key):
        pass

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
            for key, r, clickable in self.items():
                if clickable and r.contains(pos):
                    self.on_click(key)
                    self.update()
                    return
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.hide()

    def mouseMoveEvent(self, e):
        pos = e.position()
        clickable = self.close_rect().contains(pos) or any(
            c and r.contains(pos) for _k, r, c in self.items())
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
        key = self.item_at(pos)
        if key != self.hover:
            self.hover = key
            self.update()

    def leaveEvent(self, _e):
        self.hover = None
        self.update()

    def begin(self, title, subtitle):
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
        p.drawText(QRectF(12, 7, self.width() - 50, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   title)
        cr = self.close_rect()
        p.setPen(QPen(T("muted"), 1.6))
        p.drawLine(cr.topLeft() + QPointF(5, 5), cr.bottomRight() - QPointF(5, 5))
        p.drawLine(QPointF(cr.right() - 5, cr.top() + 5), QPointF(cr.left() + 5, cr.bottom() - 5))
        font.setBold(False)
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(T("text2"))
        p.drawText(QRectF(12, 28, self.width() - 24, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   subtitle)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, 51), QPointF(self.width() - 12, 51))
        return p

    @staticmethod
    def font_px(base, px, bold=False):
        f = QFont(base)
        f.setPixelSize(px)
        f.setBold(bold)
        return f


class AchievementsWin(Panel):
    ROW_H = 35
    OLD_H = 35       # Höhe eines Eintrags in der Liste «Nicht abgeholt»
    OLD_MAX = 6      # so viele Einträge werden angezeigt, der Rest als «… und N weitere»

    def __init__(self, plant):
        super().__init__(plant, 300, 602, "ach_pos")

    # ---------- Layout ----------

    def layout(self):
        """Berechnet Positionen: Zeilen je Erfolg, Liste nicht abgeholter Erfolge, Knopf, Gesamthöhe."""
        W = self.width()
        now = time.localtime()
        secs_day = 86400 - (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec)
        secs_week = secs_day + (6 - now.tm_wday) * 86400
        sections = (("daily", "Täglich", f"neu in {fmt_left(secs_day)}"),
                    ("weekly", "Wöchentlich", f"neu in {fmt_age(secs_week)}"),
                    ("general", "Allgemein", "einmalig"))
        y = 58.0
        heads, rows = [], []
        for period, heading, right in sections:
            heads.append((heading, right, y))
            y += 20
            for a in (a for a in ACHIEVEMENTS if a.period == period):
                rows.append((a, QRectF(12, y, W - 24, self.ROW_H - 3)))
                y += self.ROW_H
            y += 4
        expired = self.plant.ach_expired()
        old_head_y = y
        old_rows = []
        if expired:
            y += 22
            for e in expired[:self.OLD_MAX]:
                old_rows.append((e, QRectF(12, y, W - 24, self.OLD_H - 3)))
                y += self.OLD_H
            if len(expired) > self.OLD_MAX:
                y += 16
        btn = QRectF(40, y + 6, W - 80, 30)
        return {"heads": heads, "rows": rows, "expired": expired, "old_head_y": old_head_y,
                "old_rows": old_rows, "btn": btn, "height": int(btn.bottom() + 14)}

    def refresh(self):
        """Passt die Fensterhöhe an die Liste an und zeichnet neu."""
        h = self.layout()["height"]
        if h != self.height():
            self.setFixedSize(self.width(), h)
        self.update()

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)

    def button_rect(self):
        return self.layout()["btn"]

    def items(self):
        lay = self.layout()
        out = []
        for a, r in lay["rows"]:
            e = self.plant.ach_pending_entry(a.key)
            out.append((("row", a.key), r, e is not None))
        for e, r in lay["old_rows"]:
            out.append((("old", id(e)), r, True))
        out.append(("all", lay["btn"], self.plant.ach_pending_total() > 0))
        return out

    def on_click(self, key):
        pl = self.plant
        if key == "all":
            pl.claim_achievements()
        elif key[0] == "row":
            e = pl.ach_pending_entry(key[1])
            if e:
                pl.claim_achievement(e)
        elif key[0] == "old":
            for e in pl.state.get("ach_pending", []):
                if id(e) == key[1]:
                    pl.claim_achievement(e)
                    break

    # ---------- Zeichnen ----------

    @staticmethod
    def old_label(e):
        pid = e.get("pid", "")
        if e.get("period") == "mastery":
            return "Meisterschaft (Besucher)"
        if e.get("period") == "daily" and len(pid) == 10:
            return f"Täglich, {pid[8:10]}.{pid[5:7]}."
        if e.get("period") == "weekly" and "W" in pid:
            return f"Wöchentlich, KW {int(pid.split('W')[1])}"
        return ""

    def draw_claim_row(self, p, row, name, sub, reward, hover, base):
        """Goldene, anklickbare Zeile mit Geschenk-Symbol, Name, Belohnung und «Abholen»."""
        p.setPen(QPen(QColor("#D4A017"), 2.0 if hover else 1.6))
        p.setBrush(T("gold_bg"))
        p.drawRoundedRect(row, 6, 6)
        draw_gift(p, QPointF(row.left() + 13, row.center().y()), 8)
        p.setFont(self.font_px(base, 11, True))
        p.setPen(T("text"))
        p.drawText(QRectF(row.left() + 26, row.top() + 1, 150, 15),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        text = f"+{reward}"
        tw = p.fontMetrics().horizontalAdvance(text)
        draw_coin(p, QPointF(row.right() - 10, row.top() + 8.5), 4.5)
        p.setPen(T("coin"))
        p.drawText(QRectF(row.right() - 18 - tw, row.top() + 1, tw + 2, 15),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        p.setFont(self.font_px(base, 10))
        p.setPen(T("text2"))
        p.drawText(QRectF(row.left() + 26, row.top() + 15, row.width() - 26 - 76, 13),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sub)
        pill = QRectF(row.right() - 70, row.bottom() - 15, 62, 13)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#D4A017") if hover else QColor("#E6B93A"))
        p.drawRoundedRect(pill, 6.5, 6.5)
        p.setFont(self.font_px(base, 10, True))
        p.setPen(QColor("#3B2A00"))
        p.drawText(pill, Qt.AlignmentFlag.AlignCenter, "Abholen")

    def paintEvent(self, _e):
        plant = self.plant
        lay = self.layout()
        done_n = sum(1 for a in ACHIEVEMENTS if plant.ach_is_done(a))
        total = plant.ach_pending_total()
        p = self.begin("Erfolge", f"{done_n} von {len(ACHIEVEMENTS)} erreicht")
        base = self.font()
        W = self.width()
        for heading, right, hy in lay["heads"]:
            p.setFont(self.font_px(base, 12, True))
            p.setPen(T("text"))
            p.drawText(QRectF(12, hy, 150, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, heading)
            p.setFont(self.font_px(base, 10))
            p.setPen(T("muted"))
            p.drawText(QRectF(W - 162, hy, 150, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right)
        for a, row in lay["rows"]:
            done = plant.ach_is_done(a)
            claimable = plant.ach_pending_entry(a.key) is not None
            val = min(plant.ach_value(a.key), a.target)
            if claimable:
                self.draw_claim_row(p, row, a.name, a.desc, a.reward, self.hover == ("row", a.key), base)
                continue
            p.setPen(QPen(QColor("#2E9E44"), 1.2) if done else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if done else T("cell"))
            p.drawRoundedRect(row, 6, 6)
            icon_c = QPointF(row.left() + 13, row.center().y())
            if done:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#2E9E44"))
                p.drawEllipse(icon_c, 7, 7)
                p.setPen(round_pen(QColor("#FFFFFF"), 1.8))
                p.drawLine(icon_c + QPointF(-3.2, 0.2), icon_c + QPointF(-0.8, 2.6))
                p.drawLine(icon_c + QPointF(-0.8, 2.6), icon_c + QPointF(3.4, -2.4))
            else:
                draw_star(p, icon_c, 7, "#D8D3C4" if not _THEME["dark"] else "#6A6A62", "#9A958A")
            p.setFont(self.font_px(base, 11, True))
            p.setPen(T("text"))
            p.drawText(QRectF(row.left() + 26, row.top() + 1, 150, 15),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, a.name)
            reward = f"+{a.reward}"
            tw = p.fontMetrics().horizontalAdvance(reward)
            draw_coin(p, QPointF(row.right() - 10, row.top() + 8.5), 4.5)
            p.setPen(T("coin"))
            p.drawText(QRectF(row.right() - 18 - tw, row.top() + 1, tw + 2, 15),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, reward)
            p.setFont(self.font_px(base, 10))
            p.setPen(T("text2"))
            p.drawText(QRectF(row.left() + 26, row.top() + 15, row.width() - 26 - 92, 13),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, a.desc)
            p.setPen(T("ok") if done else T("muted"))
            p.drawText(QRectF(row.right() - 90, row.top() + 15, 82, 13),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       "abgeholt" if done else f"{fmt_int(val)} / {fmt_int(a.target)}")
            bar = QRectF(row.left() + 26, row.bottom() - 4.5, row.width() - 34, 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(T("sep"))
            p.drawRoundedRect(bar, 1, 1)
            p.setBrush(QColor("#2E9E44"))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * val / a.target, 2), 1, 1)

        if lay["expired"]:
            hy = lay["old_head_y"]
            p.setFont(self.font_px(base, 12, True))
            p.setPen(T("text"))
            p.drawText(QRectF(12, hy, 190, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "Nicht abgeholt")
            p.setFont(self.font_px(base, 10))
            p.setPen(T("muted"))
            p.drawText(QRectF(W - 152, hy, 140, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       "bereit zum Abholen")
            for e, row in lay["old_rows"]:
                self.draw_claim_row(p, row, e["name"], self.old_label(e), e["reward"],
                                    self.hover == ("old", id(e)), base)
            more = len(lay["expired"]) - len(lay["old_rows"])
            if more > 0:
                last = lay["old_rows"][-1][1]
                p.setFont(self.font_px(base, 10))
                p.setPen(T("muted"))
                p.drawText(QRectF(12, last.bottom() + 3, W - 24, 13), Qt.AlignmentFlag.AlignCenter,
                           f"… und {more} weitere (Knopf unten holt alle)")

        br = lay["btn"]
        if total > 0:
            hov = self.hover == "all"
            p.setPen(QPen(QColor("#D4A017"), 1.8 if hov else 1.4))
            p.setBrush(T("gold_bg"))
            p.drawRoundedRect(br, 8, 8)
            p.setFont(self.font_px(base, 12, True))
            label = f"Alle abholen  +{fmt_int(total)}"
            tw = p.fontMetrics().horizontalAdvance(label)
            p.setPen(T("coin"))
            p.drawText(QRectF(br.center().x() - tw / 2 - 8, br.top(), tw + 2, br.height()),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            draw_coin(p, QPointF(br.center().x() + tw / 2 + 4, br.center().y()), 6)
        else:
            p.setPen(QPen(T("cell_border"), 1))
            p.setBrush(T("cell"))
            p.drawRoundedRect(br, 8, 8)
            p.setFont(self.font_px(base, 11))
            p.setPen(T("muted"))
            p.drawText(br, Qt.AlignmentFlag.AlignCenter, "nichts abzuholen")
        p.end()


class FocusWin(Panel):
    def __init__(self, plant):
        super().__init__(plant, 240, 262, "focus_pos")

    def preset_rects(self):
        w = (self.width() - 24 - 12) / 3
        return [(f"p{m}", QRectF(12 + i * (w + 6), 58, w, 24)) for i, m in enumerate(FOCUS_PRESETS)]

    def button_rect(self):
        return QRectF(40, 206, self.width() - 80, 30)

    def items(self):
        running = self.plant.focus is not None
        return [(k, r, not running) for k, r in self.preset_rects()] + [("start", self.button_rect(), True)]

    def on_click(self, key):
        if key == "start":
            if self.plant.focus:
                self.plant.abort_focus()
            else:
                self.plant.start_focus(self.plant.state.get("focus_minutes", FOCUS_PRESETS[0]))
        elif key.startswith("p") and not self.plant.focus:
            self.plant.state["focus_minutes"] = int(key[1:])

    def paintEvent(self, _e):
        plant = self.plant
        p = self.begin("Fokus-Timer", f"Wachstum ×{FOCUS_MULT:g} während der Sitzung")
        base = self.font()
        running = plant.focus is not None
        chosen = plant.state.get("focus_minutes", FOCUS_PRESETS[0])
        for key, r in self.preset_rects():
            m = int(key[1:])
            sel = m == (plant.focus["minutes"] if running else chosen)
            p.setOpacity(1.0 if (sel or not running) else 0.45)
            p.setPen(QPen(QColor("#2E9E44"), 1.6) if sel else
                     QPen(QColor("#D4A017"), 1.4) if key == self.hover and not running else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if sel else T("cell"))
            p.drawRoundedRect(r, 6, 6)
            p.setFont(self.font_px(base, 12, sel))
            p.setPen(T("button_text") if sel else T("text2"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, f"{m} min")
            p.setOpacity(1.0)

        c = QPointF(self.width() / 2, 143)
        R = 46
        p.setPen(QPen(T("sep"), 7))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, R, R)
        if running:
            rem, total = plant.focus_remaining()
            frac = 1 - rem / total
        else:
            rem, total, frac = chosen * 60, chosen * 60, 0.0
        if frac > 0:
            pen = QPen(QColor("#2E9E44"), 7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), 90 * 16, -int(360 * 16 * frac))
        m, sec = divmod(int(math.ceil(rem)), 60)
        p.setFont(self.font_px(base, 24, True))
        p.setPen(T("text"))
        p.drawText(QRectF(c.x() - R, c.y() - 20, 2 * R, 28), Qt.AlignmentFlag.AlignCenter, f"{m:02d}:{sec:02d}")
        msg, ok = plant.focus_message()
        p.setFont(self.font_px(base, 10))
        p.setPen(T("ok") if ok else T("muted"))
        p.drawText(QRectF(c.x() - R, c.y() + 8, 2 * R, 16), Qt.AlignmentFlag.AlignCenter,
                   "läuft" if running else msg or "bereit")

        br = self.button_rect()
        hov = self.hover == "start"
        if running:
            p.setPen(QPen(T("bad"), 1.4))
            p.setBrush(T("bad_bg"))
        else:
            p.setPen(QPen(QColor("#2E9E44"), 1.6 if hov else 1.3))
            p.setBrush(T("active_bg_hover") if hov else T("active_bg"))
        p.drawRoundedRect(br, 8, 8)
        p.setFont(self.font_px(base, 12, True))
        p.setPen(T("bad") if running else T("button_text"))
        p.drawText(br, Qt.AlignmentFlag.AlignCenter, "Abbrechen" if running else "Fokus starten")

        d = plant.state.get("daily", {})
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        p.drawText(QRectF(12, self.height() - 22, self.width() - 24, 16), Qt.AlignmentFlag.AlignCenter,
                   f"Heute: {d.get('focus', 0)} Sitzung(en) · {d.get('focus_min', 0)} min")
        p.end()


class BookWin(Panel):
    COLS = 4

    def __init__(self, plant):
        super().__init__(plant, 300, 334, "book_pos")

    def card_rects(self):
        gap, x0, y0 = 6, 12, 58
        cw = (self.width() - 2 * x0 - (self.COLS - 1) * gap) / self.COLS
        ch = 104
        return [(key, QRectF(x0 + (i % self.COLS) * (cw + gap), y0 + (i // self.COLS) * (ch + gap), cw, ch))
                for i, key in enumerate(VISITOR_ORDER)]

    def items(self):
        return [(k, r, False) for k, r in self.card_rects()]

    def paintEvent(self, _e):
        plant = self.plant
        book = plant.state.get("book", {})
        p = self.begin("Besucher-Sammelbuch", f"{len(book)} von {len(VISITORS)} entdeckt")
        base = self.font()
        rarity_col = {"häufig": T("muted"), "selten": QColor("#3B82C4"), "sehr selten": QColor("#9B59B6")}
        for key, r in self.card_rects():
            v = VISITORS[key]
            found = key in book
            tier = plant.mastery_tier(key)
            if key == self.hover:
                p.setPen(QPen(QColor("#D4A017"), 1.6))
            elif tier:
                p.setPen(QPen(TIER_COLORS[tier - 1], 1.8))
            else:
                p.setPen(QPen(T("cell_border"), 1))
            p.setBrush(T("cell"))
            p.drawRoundedRect(r, 7, 7)
            draw_visitor(p, key, QPointF(r.center().x(), r.top() + 34), 2.3, plant.t + hash(key) % 7,
                         silhouette=not found)
            p.setFont(self.font_px(base, 10, True))
            p.setPen(T("text") if found else T("muted"))
            name_font = self.font_px(base, 10, True)
            while p.fontMetrics().horizontalAdvance(v.name if found else "???") > r.width() - 6 and name_font.pixelSize() > 7:
                name_font.setPixelSize(name_font.pixelSize() - 1)
                p.setFont(name_font)
            p.drawText(QRectF(r.left() + 2, r.top() + 62, r.width() - 4, 14), Qt.AlignmentFlag.AlignCenter,
                       v.name if found else "???")
            p.setFont(self.font_px(base, 9))
            p.setPen(rarity_col[v.rarity])
            p.drawText(QRectF(r.left() + 2, r.top() + 76, r.width() - 4, 12), Qt.AlignmentFlag.AlignCenter, v.rarity)
            p.setPen(T("text2"))
            p.drawText(QRectF(r.left() + 2, r.top() + 88, r.width() - 4, 12), Qt.AlignmentFlag.AlignCenter,
                       (f"{book[key]['count']}× gesehen" if book[key]['count'] < 100 else f"{book[key]['count']}×")
                       if found else "unbekannt")
            if found:
                count = book[key]["count"]
                nxt = next((s for s in MASTERY_STEPS if count < s), None)
                prev = MASTERY_STEPS[tier - 1] if tier else 0
                frac = 1.0 if nxt is None else (count - prev) / (nxt - prev)
                bar = QRectF(r.left() + 8, r.bottom() - 4, r.width() - 16, 2.5)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(T("sep"))
                p.drawRoundedRect(bar, 1.2, 1.2)
                p.setBrush(TIER_COLORS[min(tier, 2)] if nxt is None else TIER_COLORS[tier])
                p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * frac, 2.5), 1.2, 1.2)
                has_var = book[key].get("shiny", 0) > 0
                draw_star(p, QPointF(r.right() - 9, r.top() + 9), 5.5,
                          "#F2C230" if has_var else ("#4A4A44" if _THEME["dark"] else "#D8D3C4"),
                          "#B8860B" if has_var else "#9A958A")

        info = QRectF(12, self.height() - 50, self.width() - 24, 42)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, info.top() - 4), QPointF(self.width() - 12, info.top() - 4))
        if self.hover:
            v = VISITORS[self.hover]
            e = book.get(self.hover)
            if e:
                tier = plant.mastery_tier(self.hover)
                nxt = next((s for s in MASTERY_STEPS if e["count"] < s), None)
                stufe = MASTERY_NAMES[tier - 1] if tier else "keine"
                weiter = f", nächste bei {nxt}" if nxt else " (Gold: +1 % Wachstum)"
                n_var = e.get("shiny", 0)
                var = (f"{VARIANTS[self.hover].name} {n_var}× gesehen" if n_var
                       else f"{VARIANTS[self.hover].name} noch nicht gesehen")
                text = (f"{v.name} ({v.rarity}): {e['count']}× seit {fmt_datetime(e.get('first'))}. "
                        f"Stufe {stufe}{weiter}. Stern: {var}.")
            else:
                text = f"Noch nicht entdeckt ({v.rarity}). Hinweis: {v.hint}"
            color = T("text3")
        else:
            text = (f"Besucher kommen von selbst zur Pflanze. Ein Klick auf einen Besucher begrüsst ihn "
                    f"und bringt {VISIT_GREET_COINS} Coins.")
            color = T("muted")
        p.setFont(self.font_px(base, 10))
        p.setPen(color)
        p.drawText(info, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, text)
        p.end()
