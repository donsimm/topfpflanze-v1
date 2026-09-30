"""Zusatzfenster: Erfolge, Fokus-Timer, Besucher-Sammelbuch."""

import math
import time
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PyQt6.QtCore import QPointF, QRectF, Qt

from .i18n import tr
from .data import RARITY_LABEL, MASTERY_NAMES, MASTERY_STEPS, MASTERY_TOP_BONUS, VARIANTS, ACHIEVEMENTS, FOCUS_DEFAULT, FOCUS_MULT, FOCUS_PRESETS, VISITORS, VISITOR_ORDER, VISIT_GREET_COINS
from .drawing import fit_font, draw_coin, draw_gift, draw_seedling, draw_star, draw_visitor, round_pen
from .theme import T, _THEME
from .util import fmt_age, fmt_date, fmt_int, fmt_left
from .scaling import ScaledWidget


# ---------------------------------------------------------------- Weitere Fenster

TIER_COLORS = (QColor("#8CC084"), QColor("#4FA35A"), QColor("#2E7D46"))  # Besucher, Stammgast, Gartenbewohner (Grüntöne)


def tier_text_color(tier):
    """Grün der Stufe als Schriftfarbe: gleicher Farbton wie der Rahmen, je nach Modus abgedunkelt/aufgehellt
    damit es auf dem Hintergrund gut lesbar bleibt."""
    c = TIER_COLORS[tier - 1]
    return c.lighter(145) if _THEME["dark"] else c.darker(135)


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

    def saved_pos(self):
        """Position, die im Spielstand gespeichert wird."""
        return self.x(), self.y()

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
        sections = (("daily", tr("Täglich"), tr("neu in {secs_day}", secs_day=fmt_left(secs_day))),
                    ("weekly", tr("Wöchentlich"), tr("neu in {secs_week}", secs_week=fmt_age(secs_week))),
                    ("general", tr("Allgemein"), tr("einmalig")))
        y = 58.0
        heads, rows = [], []
        for period, heading, right in sections:
            heads.append((heading, right, y))
            y += 20
            for a, tier, tiers in self.plant.ach_rows(period):
                rows.append((a, QRectF(12, y, W - 24, self.ROW_H - 3), tier, tiers))
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
        for a, r, _t, _n in lay["rows"]:
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
            return tr("Meisterschaft (Besucher)")
        if e.get("period") == "daily" and len(pid) == 10:
            return tr("Täglich, {pid}.{pid2}.", pid=pid[8:10], pid2=pid[5:7])
        if e.get("period") == "weekly" and "W" in pid:
            return tr("Wöchentlich, KW {split}", split=int(pid.split('W')[1]))
        return ""

    @staticmethod
    def draw_tier_dots(p, row, name_w, tier, tiers, done):
        """Punkte hinter dem Namen für die Stufen einer Reihe: erreichte gefüllt, aktuelle mit Ring, offene leer."""
        if tiers < 2:
            return
        x = row.left() + 26 + name_w + 9
        y = row.top() + 8.5
        for i in range(tiers):
            c = QPointF(x + i * 7.4, y)
            reached = i < tier - 1 or (done and i == tier - 1)
            p.setBrush(QColor("#2E9E44") if reached else Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#2E9E44") if reached or i == tier - 1 else T("muted"), 1.3 if i == tier - 1 else 1.0))
            p.drawEllipse(c, 2.7, 2.7)

    def draw_claim_row(self, p, row, name, sub, reward, hover, base, tier=1, tiers=1):
        """Goldene, anklickbare Zeile mit Geschenk-Symbol, Name, Belohnung und «Abholen»."""
        p.setPen(QPen(QColor("#D4A017"), 2.0 if hover else 1.6))
        p.setBrush(T("gold_bg"))
        p.drawRoundedRect(row, 6, 6)
        draw_gift(p, QPointF(row.left() + 13, row.center().y()), 8)
        p.setFont(self.font_px(base, 11, True))
        p.setPen(T("text"))
        p.drawText(QRectF(row.left() + 26, row.top() + 1, 175, 15),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        self.draw_tier_dots(p, row, p.fontMetrics().horizontalAdvance(name), tier, tiers, False)
        p.setFont(self.font_px(base, 11, True))
        text = f"+{reward}"
        tw = p.fontMetrics().horizontalAdvance(text)
        draw_coin(p, QPointF(row.right() - 10, row.top() + 8.5), 4.5)
        p.setPen(T("coin"))
        p.drawText(QRectF(row.right() - 18 - tw, row.top() + 1, tw + 2, 15),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        fit_font(p, self.font_px(base, 10), sub, row.width() - 26 - 76, min_px=8)
        p.setPen(T("text2"))
        p.drawText(QRectF(row.left() + 26, row.top() + 15, row.width() - 26 - 76, 13),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sub)
        pill = QRectF(row.right() - 70, row.bottom() - 15, 62, 13)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#D4A017") if hover else QColor("#E6B93A"))
        p.drawRoundedRect(pill, 6.5, 6.5)
        p.setFont(self.font_px(base, 10, True))
        p.setPen(QColor("#3B2A00"))
        p.drawText(pill, Qt.AlignmentFlag.AlignCenter, tr("Abholen"))

    def paintEvent(self, _e):
        plant = self.plant
        lay = self.layout()
        done_n = sum(1 for a in ACHIEVEMENTS if plant.ach_is_done(a))
        total = plant.ach_pending_total()
        p = self.begin(tr("Erfolge"), tr("{done_n} von {v} erreicht", done_n=done_n, v=len(ACHIEVEMENTS)))
        base = self.font()
        W = self.width()
        for heading, right, hy in lay["heads"]:
            p.setFont(self.font_px(base, 12, True))
            p.setPen(T("text"))
            p.drawText(QRectF(12, hy, 150, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, heading)
            p.setFont(self.font_px(base, 10))
            p.setPen(T("muted"))
            p.drawText(QRectF(W - 162, hy, 150, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right)
        for a, row, tier, tiers in lay["rows"]:
            done = plant.ach_is_done(a)
            claimable = plant.ach_pending_entry(a.key) is not None
            val = min(plant.ach_value(a.key), a.target)
            if claimable:
                self.draw_claim_row(p, row, a.name, a.desc, a.reward, self.hover == ("row", a.key), base, tier, tiers)
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
            p.drawText(QRectF(row.left() + 26, row.top() + 1, 175, 15),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, a.name)
            self.draw_tier_dots(p, row, p.fontMetrics().horizontalAdvance(a.name), tier, tiers, done)
            reward = f"+{a.reward}"
            tw = p.fontMetrics().horizontalAdvance(reward)
            draw_coin(p, QPointF(row.right() - 10, row.top() + 8.5), 4.5)
            p.setPen(T("coin"))
            p.drawText(QRectF(row.right() - 18 - tw, row.top() + 1, tw + 2, 15),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, reward)
            fit_font(p, self.font_px(base, 10), a.desc, row.width() - 26 - 92, min_px=8)
            p.setPen(T("text2"))
            p.drawText(QRectF(row.left() + 26, row.top() + 15, row.width() - 26 - 92, 13),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, a.desc)
            p.setPen(T("ok") if done else T("muted"))
            p.drawText(QRectF(row.right() - 90, row.top() + 15, 82, 13),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       tr("abgeholt") if done else f"{fmt_int(val)} / {fmt_int(a.target)}")
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
                       tr("Nicht abgeholt"))
            p.setFont(self.font_px(base, 10))
            p.setPen(T("muted"))
            p.drawText(QRectF(W - 152, hy, 140, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       tr("bereit zum Abholen"))
            for e, row in lay["old_rows"]:
                self.draw_claim_row(p, row, e["name"], self.old_label(e), e["reward"],
                                    self.hover == ("old", id(e)), base)
            more = len(lay["expired"]) - len(lay["old_rows"])
            if more > 0:
                last = lay["old_rows"][-1][1]
                p.setFont(self.font_px(base, 10))
                p.setPen(T("muted"))
                p.drawText(QRectF(12, last.bottom() + 3, W - 24, 13), Qt.AlignmentFlag.AlignCenter,
                           tr("… und {more} weitere (Knopf unten holt alle)", more=more))

        br = lay["btn"]
        if total > 0:
            hov = self.hover == "all"
            p.setPen(QPen(QColor("#D4A017"), 1.8 if hov else 1.4))
            p.setBrush(T("gold_bg"))
            p.drawRoundedRect(br, 8, 8)
            p.setFont(self.font_px(base, 12, True))
            label = tr("Alle abholen  +{v}", v=fmt_int(total))
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
            p.drawText(br, Qt.AlignmentFlag.AlignCenter, tr("nichts abzuholen"))
        p.end()


class FocusWin(Panel):
    W, H = 240, 290
    COMPACT = 150   # Kantenlänge im Fokusmodus: nur Zeit und Ring, durchsichtig

    def __init__(self, plant):
        super().__init__(plant, self.W, self.H, "focus_pos")
        self.compact = False

    # ---------- Fokusmodus: kleines, durchsichtiges Fenster ----------

    def _center(self):
        return self.x() + self.real_width() / 2, self.y() + self.real_height() / 2

    def set_compact(self, on):
        """Wechselt zwischen normalem Fenster und Fokusmodus-Ansicht; das Fenster bleibt um seine Mitte."""
        if on == self.compact:
            return
        cx, cy = self._center()
        self.compact = on
        if on:
            self.setFixedSize(self.COMPACT, self.COMPACT)
        else:
            self.setFixedSize(self.W, self.H)
        self.move(int(round(cx - self.real_width() / 2)), int(round(cy - self.real_height() / 2)))
        if on:
            self.show()
            self.raise_()
        self.update()

    def saved_pos(self):
        """Im Fokusmodus die Position, die das normale Fenster hätte (Mitte bleibt gleich)."""
        if not self.compact:
            return super().saved_pos()
        cx, cy = self._center()
        return int(round(cx - self.W * self._k / 2)), int(round(cy - self.H * self._k / 2))

    def mousePressEvent(self, e):
        if not self.compact:
            return super().mousePressEvent(e)
        if e.button() == Qt.MouseButton.LeftButton:
            if self.abort_rect().contains(e.position()):
                self.plant.abort_focus()
                return
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
        elif e.button() == Qt.MouseButton.RightButton:
            self.plant.show_menu(e.globalPosition().toPoint())

    def abort_rect(self):
        """Klickfläche des kleinen X unter der Zeit (nur im Fokusmodus)."""
        return QRectF(self.width() / 2 - 11, self.height() / 2 + 20, 22, 20)

    def tooltip_at(self, pos):
        if self.compact:
            if self.abort_rect().contains(pos):
                return tr("Fokus abbrechen\nKein Bonus für diese Sitzung.")
            rem, _ = self.plant.focus_remaining()
            m, sec = divmod(int(math.ceil(rem)), 60)
            return tr("Fokus läuft: noch {m:02d}:{sec:02d}\nRechtsklick: Menü, Fokus abbrechen", m=m, sec=sec)
        if self.mode_rect().contains(pos):
            return (tr("Fokusmodus\nBeim Start werden alle anderen Fenster ausgeblendet, nur Pflanze und Zeit bleiben. "
                    "Nach dem Ablauf kommen sie zurück."))
        return super().tooltip_at(pos)

    def paint_compact(self):
        """Nur Zeit und runder Fortschrittsring, ohne Fensterhintergrund (auf jedem Desktop lesbar)."""
        plant = self.plant
        p = self.new_painter()
        c = QPointF(self.width() / 2, self.height() / 2)
        R = 52
        running = plant.focus is not None
        rem, total = plant.focus_remaining() if running else (0.0, 1.0)
        frac = 1 - rem / total
        halo = T("panel")
        halo.setAlpha(175)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(halo, 9))
        p.drawEllipse(c, R, R)
        track = T("text2")
        track.setAlpha(110)
        p.setPen(QPen(track, 7))
        p.drawEllipse(c, R, R)
        if frac > 0:
            pen = QPen(QColor("#2E9E44"), 7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), 90 * 16, -int(360 * 16 * frac))
        m, sec = divmod(int(math.ceil(rem)), 60)
        font = self.font_px(self.font(), 28, True)
        text = f"{m:02d}:{sec:02d}"
        fm = QFontMetricsF(font)
        path = QPainterPath()
        path.addText(c.x() - fm.horizontalAdvance(text) / 2, c.y() + fm.ascent() / 2 - 2, font, text)
        outline = T("panel")
        outline.setAlpha(230)
        p.setPen(QPen(outline, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(T("text"))
        p.drawPath(path)
        ar = self.abort_rect()                      # kleines X zum Abbrechen
        hot = self.hover == "abort"
        a = QPointF(ar.center().x(), ar.center().y())
        for col, w in ((outline, 3.2), (QColor("#D64541") if hot else T("text2"), 1.4)):
            p.setPen(QPen(col, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(a.x() - 3.5, a.y() - 3.5), QPointF(a.x() + 3.5, a.y() + 3.5))
            p.drawLine(QPointF(a.x() - 3.5, a.y() + 3.5), QPointF(a.x() + 3.5, a.y() - 3.5))
        p.end()

    # ---------- Normales Fenster ----------

    def preset_rects(self):
        n = len(FOCUS_PRESETS)
        w = (self.width() - 24 - 6 * (n - 1)) / n
        return [(f"p{m}", QRectF(12 + i * (w + 6), 58, w, 24)) for i, m in enumerate(FOCUS_PRESETS)]

    def button_rect(self):
        return QRectF(40, 206, self.width() - 80, 30)

    def mode_rect(self):
        return QRectF(12, 244, self.width() - 24, 22)

    def items(self):
        if self.compact:
            return [("abort", self.abort_rect(), True)]
        running = self.plant.focus is not None
        return ([(k, r, not running) for k, r in self.preset_rects()] + [("start", self.button_rect(), True),
                                                                          ("mode", self.mode_rect(), not running)])

    def on_click(self, key):
        if key == "start":
            if self.plant.focus:
                self.plant.abort_focus()
            else:
                self.plant.start_focus(self.plant.state.get("focus_minutes", FOCUS_DEFAULT))
        elif key == "mode":
            self.plant.state["focus_mode"] = not self.plant.state.get("focus_mode", True)
            self.plant.save_state()
        elif key.startswith("p") and not self.plant.focus:
            self.plant.state["focus_minutes"] = int(key[1:])

    def paintEvent(self, _e):
        if self.compact:
            self.paint_compact()
            return
        plant = self.plant
        p = self.begin(tr("Fokus-Timer"), tr("Wachstum ×{v:g} während der Sitzung", v=FOCUS_MULT))
        base = self.font()
        running = plant.focus is not None
        chosen = plant.state.get("focus_minutes", FOCUS_DEFAULT)
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
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, tr("{m} min", m=m))
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
                   tr("läuft") if running else msg or tr("bereit"))

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
        p.drawText(br, Qt.AlignmentFlag.AlignCenter, tr("Abbrechen") if running else tr("Fokus starten"))

        # Schalter «Fokusmodus»
        mr = self.mode_rect()
        on = plant.state.get("focus_mode", True)
        p.setOpacity(1.0 if not running else 0.5)
        p.setFont(self.font_px(base, 11, True))
        p.setPen(T("text"))
        p.drawText(QRectF(mr.left(), mr.top(), 120, mr.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   tr("Fokusmodus"))
        sw = QRectF(mr.right() - 38, mr.center().y() - 9, 38, 18)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2E9E44") if on else T("cell_border"))
        p.drawRoundedRect(sw, 9, 9)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(sw.right() - 9 if on else sw.left() + 9, sw.center().y()), 7, 7)
        p.setFont(self.font_px(base, 10, True))
        p.setPen(T("ok") if on else T("muted"))
        p.drawText(QRectF(sw.left() - 34, mr.top(), 30, mr.height()), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   tr("an") if on else tr("aus"))
        p.setOpacity(1.0)

        d = plant.state.get("daily", {})
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        p.drawText(QRectF(12, self.height() - 22, self.width() - 24, 16), Qt.AlignmentFlag.AlignCenter,
                   tr("Heute: {focus} Sitzung(en) · {focus_min} min", focus=d.get('focus', 0), focus_min=d.get('focus_min', 0)))
        p.end()


class BookWin(Panel):
    COLS = 4

    def __init__(self, plant):
        super().__init__(plant, 300, 360, "book_pos")

    def card_rects(self):
        gap, x0, y0 = 8, 12, 58
        cw = (self.width() - 2 * x0 - (self.COLS - 1) * gap) / self.COLS
        ch = 112
        return [(key, QRectF(x0 + (i % self.COLS) * (cw + gap), y0 + (i // self.COLS) * (ch + gap), cw, ch))
                for i, key in enumerate(VISITOR_ORDER)]

    def items(self):
        return [(k, r, False) for k, r in self.card_rects()]

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if self.hover and self.plant.clear_book_new(self.hover):   # Überfahren gilt als gesehen
            self.plant.bubble.update()

    def paintEvent(self, _e):
        plant = self.plant
        book = plant.state.get("book", {})
        fresh = plant.state.get("book_new", [])
        p = self.begin(tr("Besucher-Sammelbuch"), tr("{book} von {v} entdeckt", book=len(book), v=len(VISITORS)))
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
            draw_visitor(p, key, QPointF(r.center().x(), r.top() + 38), 2.3, plant.t + hash(key) % 7,
                         silhouette=not found)
            p.setFont(self.font_px(base, 10, True))
            p.setPen(T("text") if found else T("muted"))
            name_font = self.font_px(base, 10, True)
            while p.fontMetrics().horizontalAdvance(v.name if found else "???") > r.width() - 6 and name_font.pixelSize() > 7:
                name_font.setPixelSize(name_font.pixelSize() - 1)
                p.setFont(name_font)
            p.drawText(QRectF(r.left() + 2, r.top() + 64, r.width() - 4, 14), Qt.AlignmentFlag.AlignCenter,
                       v.name if found else "???")
            p.setFont(self.font_px(base, 9))
            p.setPen(rarity_col[v.rarity])
            p.drawText(QRectF(r.left() + 2, r.top() + 78, r.width() - 4, 12), Qt.AlignmentFlag.AlignCenter, RARITY_LABEL[v.rarity])
            p.setPen(T("text2"))
            p.drawText(QRectF(r.left() + 2, r.top() + 90, r.width() - 4, 12), Qt.AlignmentFlag.AlignCenter,
                       (tr("{count}× gesehen", count=book[key]['count']) if book[key]['count'] < 100 else f"{book[key]['count']}×")
                       if found else tr("unbekannt"))
            if found:
                count = book[key]["count"]
                nxt = next((s for s in MASTERY_STEPS if count < s), None)
                prev = MASTERY_STEPS[tier - 1] if tier else 0
                frac = 1.0 if nxt is None else (count - prev) / (nxt - prev)
                bar = QRectF(r.left() + 10, r.bottom() - 8, r.width() - 20, 2.5)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(T("sep"))
                p.drawRoundedRect(bar, 1.2, 1.2)
                p.setBrush(TIER_COLORS[min(tier, 2)] if nxt is None else TIER_COLORS[tier])
                p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * frac, 2.5), 1.2, 1.2)
                # Setzling oben links: Keimspitze (noch keine Stufe) oder 1–3 Blätter
                draw_seedling(p, QPointF(r.left() + 11, r.top() + 16.2), 14, tier,
                              TIER_COLORS[tier - 1] if tier else QColor("#8CC084"))
                has_var = book[key].get("shiny", 0) > 0
                draw_star(p, QPointF(r.right() - 11, r.top() + 11), 5.5,
                          "#F2C230" if has_var else ("#4A4A44" if _THEME["dark"] else "#D8D3C4"),
                          "#B8860B" if has_var else "#9A958A")
                if key in fresh:   # neu entdeckt: roter Punkt an der Kartenecke
                    p.setPen(QPen(T("cell"), 1.2))
                    p.setBrush(QColor("#D64541"))
                    p.drawEllipse(QPointF(r.left() + 4, r.top() + 4), 4, 4)

        info = QRectF(12, self.height() - 60, self.width() - 24, 3 * self.ROW)
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, info.top() - 4), QPointF(self.width() - 12, info.top() - 4))
        self.draw_info(p, info, base, book, rarity_col)
        p.end()

    ROW = 16  # Zeilenhöhe im Infobereich

    def info_row(self, p, info, i, parts, base, icon=None, right=None):
        """Zeile i des Infobereichs: optionales Symbol links, farbige Textteile (Text, Farbe, fett),
        optional rechtsbündiger Text. Zu lange Zeilen werden leicht verkleinert."""
        y = info.top() + i * self.ROW
        x0 = info.left() + (18 if icon else 0)
        avail = info.right() - x0
        px = 10

        def width(size):
            w = 0.0
            for text, _c, bold in parts:
                p.setFont(self.font_px(base, size, bold))
                w += p.fontMetrics().horizontalAdvance(text)
            if right:
                p.setFont(self.font_px(base, size))
                w += p.fontMetrics().horizontalAdvance(right[0]) + 8
            return w

        while px > 8 and width(px) > avail:
            px -= 1
        if icon:
            icon(QPointF(info.left() + 7, y + self.ROW / 2))
        x = x0
        for text, color, bold in parts:
            p.setFont(self.font_px(base, px, bold))
            p.setPen(color)
            w = p.fontMetrics().horizontalAdvance(text)
            p.drawText(QRectF(x, y, w + 2, self.ROW), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            x += w
        if right:
            p.setFont(self.font_px(base, px))
            p.setPen(right[1])
            p.drawText(QRectF(info.left(), y, info.width(), self.ROW),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right[0])

    def draw_info(self, p, info, base, book, rarity_col):
        """Infobereich: Legende, solange nichts markiert ist, sonst Angaben zum Besucher in drei Zeilen."""
        plant = self.plant
        ok, gold, muted, text = T("ok"), T("coin"), T("muted"), T("text")

        def seedling(leaves, color):
            return lambda c: draw_seedling(p, c + QPointF(0, 5.2), 14, leaves, color)

        def star(filled):
            return lambda c: draw_star(p, c, 5.5, "#F2C230" if filled else ("#4A4A44" if _THEME["dark"] else "#D8D3C4"),
                                       "#B8860B" if filled else "#9A958A")

        if not self.hover:  # Legende
            steps = " / ".join(str(s) for s in MASTERY_STEPS)
            self.info_row(p, info, 0, [(tr("Ein Klick auf einen Besucher bringt {v} Gold.", v=VISIT_GREET_COINS), muted, False)], base)
            self.info_row(p, info, 1, [(tr("Setzling"), ok, True), (tr("  Stufe nach {steps} Besuchen", steps=steps), muted, False)], base,
                          icon=seedling(3, TIER_COLORS[2]))
            self.info_row(p, info, 2, [(tr("Stern"), gold, True), (tr("  Farbvariante gesehen"), muted, False)], base,
                          icon=star(True))
            return
        key = self.hover
        v = VISITORS[key]
        e = book.get(key)
        if not e:
            self.info_row(p, info, 0, [("???", text, True), (f"  {RARITY_LABEL[v.rarity]}", rarity_col[v.rarity], False)], base)
            p.setFont(self.font_px(base, 10))
            p.setPen(muted)
            p.drawText(QRectF(info.left(), info.top() + self.ROW, info.width(), 2 * self.ROW),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                       tr("Noch nicht entdeckt. Hinweis: {hint}", hint=v.hint))
            return
        tier = plant.mastery_tier(key)
        count = e["count"]
        nxt = next((s for s in MASTERY_STEPS if count < s), None)
        self.info_row(p, info, 0, [(v.name, text, True), (f"  {RARITY_LABEL[v.rarity]}", rarity_col[v.rarity], False)], base,
                      right=(tr("{count}× · seit {first}", count=count, first=fmt_date(e.get('first'))), muted))
        if tier:
            stufe = [(MASTERY_NAMES[tier - 1], tier_text_color(tier), True)]
        else:
            stufe = [(tr("Noch keine Stufe"), muted, True)]
        if nxt:
            stufe.append((tr("  noch {count} bis {tier}", count=nxt - count, tier=MASTERY_NAMES[tier]), muted, False))
        else:
            stufe.append((tr("  Höchste Stufe, +{v:g} %", v=MASTERY_TOP_BONUS * 100), muted, False))
        self.info_row(p, info, 1, stufe, base, icon=seedling(tier, TIER_COLORS[tier - 1] if tier else TIER_COLORS[0]))
        n_var = e.get("shiny", 0)
        vname = VARIANTS[key].name
        if n_var:
            parts = [(vname, gold, True), (tr("  {n_var}× gesehen", n_var=n_var), muted, False)]
        else:
            parts = [(vname, muted, True), (tr("  offen"), muted, False)]
        self.info_row(p, info, 2, parts, base, icon=star(n_var > 0))
