"""Tagebuch: Kalender (Wärmekarte mit grünem Punkt) und Textfenster mit fünf Stimmungs-Herzen.

Die Einträge liegen in `diary.json` im Datenordner (neben dem Spielstand): je Tag ein Text und eine Stimmung.
Das Textfenster speichert von selbst kurz nach dem Tippen. Es gehört nicht zu den Menüfenstern, die der
Fokusmodus ausblendet: ein offenes Textfenster bleibt sichtbar.
"""

import calendar
import datetime
import json
import os
import time

from PyQt6.QtCore import QDate, QLocale, QPointF, QRectF, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QPlainTextEdit

from . import config, i18n
from .i18n import tr
from .panels import Panel
from .theme import T, _THEME

MOODS = (("#5B7FC4", tr("schwer")), ("#8E8E9A", tr("müde")), ("#F2C230", tr("ruhig")),
         ("#F08A32", tr("gut")), ("#E0384F", tr("glücklich")))
FACES = ("sad", "tired", "calm", "happy", "love")
SAVE_DELAY_MS = 700            # so lange nach dem letzten Tippen wird gespeichert
HEAT = {"light": ("#CFE9CF", "#A9D9AE", "#7CC587"), "dark": ("#2F4A33", "#3C6B45", "#4E8A58")}
HEAT_STEPS = (100, 250)        # Zeichen: bis dahin hell, dann mittel, darüber dunkel
GREEN = QColor("#2E9E44")
GOLD = QColor("#D4A017")


def key_of(day):
    return day.isoformat()


class DiaryStore:
    """Alle Einträge: {"2026-10-04": {"text": "...", "mood": 3, "updated": 1700000000.0}}."""

    def __init__(self):
        self.entries = {}
        self.error = ""
        self.load()

    @staticmethod
    def path():
        return config.STATE_DIR / "diary.json"

    def load(self):
        try:
            with open(self.path(), encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", {}) if isinstance(data, dict) else {}
            self.entries = {k: v for k, v in entries.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            self.entries = {}

    def save(self):
        """Schreibt die Datei in einem Zug (zuerst temporär, dann ersetzen), damit sie nie halb geschrieben ist."""
        path = self.path()
        tmp = path.with_suffix(".json.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "entries": self.entries}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            self.error = ""
        except OSError as e:
            self.error = f"{type(e).__name__}: {e}"

    def get(self, day):
        return self.entries.get(key_of(day))

    def text(self, day):
        return (self.get(day) or {}).get("text", "")

    def mood(self, day):
        m = (self.get(day) or {}).get("mood")
        return m if isinstance(m, int) and 0 <= m < len(MOODS) else None

    def has(self, day):
        return key_of(day) in self.entries

    def size(self, day):
        return len(self.text(day))

    def put(self, day, text, mood):
        """Speichert den Tag; ein leerer Text ohne Stimmung entfernt den Eintrag."""
        if not text.strip() and mood is None:
            if self.entries.pop(key_of(day), None) is None:
                return
        else:
            self.entries[key_of(day)] = {"text": text, "mood": mood, "updated": time.time()}
        self.save()

    def month_count(self, year, month):
        prefix = f"{year:04d}-{month:02d}-"
        return sum(1 for k in self.entries if k.startswith(prefix))


def locale():
    return QLocale(i18n.language())


def long_date(day):
    return locale().toString(QDate(day.year, day.month, day.day), QLocale.FormatType.LongFormat)


def month_title(year, month):
    return f"{locale().monthName(month, QLocale.FormatType.LongFormat)} {year}"


def weekday_short(i):
    """Kurzname des Wochentags (0 = Montag), ohne Punkt."""
    return locale().dayName(i + 1, QLocale.FormatType.ShortFormat).rstrip(".")


# ---------------------------------------------------------------- Zeichnen

def heart_path(c, s):
    path = QPainterPath()
    x, y = c.x(), c.y()
    path.moveTo(x, y + s * 0.95)
    path.cubicTo(QPointF(x - s * 1.5, y - s * 0.1), QPointF(x - s * 0.9, y - s * 1.1), QPointF(x, y - s * 0.35))
    path.cubicTo(QPointF(x + s * 0.9, y - s * 1.1), QPointF(x + s * 1.5, y - s * 0.1), QPointF(x, y + s * 0.95))
    return path


def draw_face(p, c, s, kind, dark="#4A2A2A"):
    pen = QPen(QColor(dark), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    ey = c.y() - s * 0.12
    if kind == "tired":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for dx in (-0.35, 0.35):
            p.drawLine(QPointF(c.x() + dx * s - 2.2, ey), QPointF(c.x() + dx * s + 2.2, ey))
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(dark))
        for dx in (-0.35, 0.35):
            p.drawEllipse(QPointF(c.x() + dx * s, ey), 1.6 if kind == "love" else 1.5, 2.2 if kind == "love" else 1.5)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen)
    my = c.y() + s * 0.32
    mouth = QPainterPath(QPointF(c.x() - s * 0.3, my))
    bend = {"sad": -0.28, "tired": 0.0, "calm": 0.12, "happy": 0.34, "love": 0.5}[kind]
    if kind == "tired":
        mouth.lineTo(QPointF(c.x() + s * 0.3, my))
    else:
        mouth.quadTo(QPointF(c.x(), my + s * bend), QPointF(c.x() + s * 0.3, my))
    p.drawPath(mouth)


def draw_mood_heart(p, c, s, index, dim=False):
    color = QColor(MOODS[index][0])
    if dim:
        color.setAlpha(110)
    p.setPen(QPen(QColor(MOODS[index][0]).darker(135), 1.2))
    p.setBrush(color)
    p.drawPath(heart_path(c, s))
    draw_face(p, QPointF(c.x(), c.y() + 1), s, FACES[index])


def paper_color():
    return QColor("#2A2C2F") if _THEME["dark"] else QColor("#FCFAF2")


class PaperEdit(QPlainTextEdit):
    """Textfeld auf liniertem Papier: durchsichtig, die Linien folgen der Zeilenhöhe."""

    def paintEvent(self, e):
        p = QPainter(self.viewport())
        ls = max(8, self.fontMetrics().lineSpacing())
        top = self.contentOffset().y() + self.document().documentMargin()
        y = top + ls + 1
        while y < 0:
            y += ls
        p.setPen(QPen(QColor(255, 255, 255, 30) if _THEME["dark"] else QColor(150, 170, 200, 95), 1))
        w = self.viewport().width()
        while y < self.viewport().height():
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += ls
        p.end()
        super().paintEvent(e)


# ---------------------------------------------------------------- Textfenster

class DiaryTextWin(Panel):
    """Eigenständiges Textfenster eines Tages mit fünf Stimmungs-Herzen (blendet sich im Fokusmodus nicht aus)."""

    W, H = 380, 540
    PAPER = QRectF(12, 62, 356, 358)
    EDIT = QRectF(42, 65, 320, 352)
    EDIT_PX = 14

    def __init__(self, plant):
        self.date = datetime.date.today()
        self.mood = None
        self.dirty = False
        self._theme = None
        super().__init__(plant, self.W, self.H, "diary_text_pos")
        self.editor = PaperEdit(self)
        self.editor.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.editor.setPlaceholderText(tr("Schreibe hier deine Gedanken …"))
        self.editor.textChanged.connect(self._changed)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(SAVE_DELAY_MS)
        self.timer.timeout.connect(self.flush)
        self._layout_editor()

    def place_window(self):
        pos = self.plant.state.get(self.pos_key)
        cal = getattr(self.plant, "diary_win", None)
        if pos:
            self.move(int(pos[0]), int(pos[1]))
        elif cal is not None:
            self.move(max(0, cal.x() - self.real_width() - 10), cal.y())
        else:
            super().place_window()

    # ---------- Aufbau ----------

    def rescale(self):
        super().rescale()
        if hasattr(self, "editor"):
            self._layout_editor()

    def _layout_editor(self):
        k = self._k
        r = self.EDIT
        self.editor.setGeometry(int(r.x() * k), int(r.y() * k), int(r.width() * k), int(r.height() * k))
        font = QFont(self.font())
        font.setPixelSize(max(8, int(round(self.EDIT_PX * k))))
        self.editor.setFont(font)
        self._style_editor()

    def _style_editor(self):
        key = (_THEME["dark"], self._k)
        if key == self._theme:
            return
        self._theme = key
        text = "#E8E8E8" if _THEME["dark"] else "#1E1E1E"
        self.editor.setStyleSheet(
            f"QPlainTextEdit {{ background: transparent; border: none; color: {text};"
            " selection-background-color: #9CCF9C; selection-color: #1E1E1E; }")
        self.editor.viewport().setAutoFillBackground(False)

    # ---------- Inhalt ----------

    def open_date(self, day):
        """Zeigt den Eintrag des Tages (der bisherige wird vorher gespeichert) und setzt den Cursor ins Textfeld."""
        self.flush()
        self.date = day
        store = self.plant.diary
        self.editor.blockSignals(True)
        self.editor.setPlainText(store.text(day))
        self.editor.blockSignals(False)
        self.mood = store.mood(day)
        self.dirty = False
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()
        self.editor.setFocus()
        self.update()
        self.plant.diary_win.update()

    def _changed(self):
        self.dirty = True
        self.timer.start()
        self.update()

    def flush(self):
        """Speichert den Tag, falls etwas geändert wurde."""
        self.timer.stop()
        if not self.dirty:
            return
        self.dirty = False
        self.plant.diary.put(self.date, self.editor.toPlainText(), self.mood)
        self.update()
        win = getattr(self.plant, "diary_win", None)
        if win is not None:
            win.update()

    def hideEvent(self, e):
        self.flush()
        super().hideEvent(e)

    # ---------- Klicks ----------

    def mood_rects(self):
        return [QRectF(14 + i * 70, 466, 62, 50) for i in range(len(MOODS))]

    def items(self):
        return [(("m", i), r, True) for i, r in enumerate(self.mood_rects())]

    def on_click(self, key):
        if key[0] == "m":
            self.mood = None if self.mood == key[1] else key[1]   # nochmal klicken: Stimmung entfernen
            self.dirty = True
            self.flush()

    def tooltip_at(self, pos):
        for key, r, _c in self.items():
            if r.contains(pos):
                return MOODS[key[1]][1]
        return super().tooltip_at(pos)

    # ---------- Zeichnen ----------

    def paintEvent(self, _e):
        self._style_editor()
        base = self.font()
        p = self.begin(tr("Tagebuch"), long_date(self.date))
        paper = self.PAPER
        p.setPen(QPen(T("cell_border"), 1))
        p.setBrush(paper_color())
        p.drawRoundedRect(paper, 7, 7)
        p.setPen(QPen(QColor(220, 110, 110, 120), 1))                      # roter Rand wie auf Schulpapier
        p.drawLine(QPointF(paper.left() + 28, paper.top() + 4), QPointF(paper.left() + 28, paper.bottom() - 4))
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        p.drawText(QRectF(paper.left() + 8, paper.bottom() - 16, paper.width() - 16, 14),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   tr("{n} Zeichen", n=len(self.editor.toPlainText())))
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(12, 436), QPointF(self.W - 12, 436))
        p.setFont(self.font_px(base, 11, True))
        p.setPen(T("text2"))
        p.drawText(QRectF(14, 440, 150, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tr("Stimmung"))
        if self.mood is not None:
            p.setFont(self.font_px(base, 11))
            p.setPen(T("muted"))
            p.drawText(QRectF(150, 440, self.W - 164, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       MOODS[self.mood][1])
        for i, r in enumerate(self.mood_rects()):
            sel = self.mood == i
            hover = self.hover == ("m", i)
            p.setPen(QPen(GREEN, 2.2) if sel else QPen(GOLD, 1.6) if hover else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if sel else T("hover_bg") if hover else T("cell"))
            p.drawRoundedRect(r, 7, 7)
            draw_mood_heart(p, QPointF(r.center().x(), r.center().y() + 1), 14.5, i, dim=not (sel or hover))
        if not self.dirty and self.plant.diary.has(self.date):
            p.setFont(self.font_px(base, 10))
            p.setPen(T("ok"))
            p.drawText(QRectF(self.W - 214, 522, 200, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       tr("✓ automatisch gespeichert"))
        p.end()


# ---------------------------------------------------------------- Kalender

class DiaryCalWin(Panel):
    """Monatskalender als Wärmekarte: Tage mit Eintrag haben einen grünen Punkt, je mehr Text desto dunkler."""

    W, H = 318, 352
    GRID_Y = 104

    def __init__(self, plant):
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        super().__init__(plant, self.W, self.H, "diary_pos")

    # ---------- Layout ----------

    def cell_size(self):
        cw = (self.W - 28 - 6 * 3) / 7
        return cw, cw * 0.82

    def prev_rect(self):
        return QRectF(14, 58, 28, 24)

    def next_rect(self):
        return QRectF(self.W - 42, 58, 28, 24)

    def today_rect(self):
        return QRectF(self.W - 76, self.H - 32, 62, 20)

    def day_rects(self):
        cw, ch = self.cell_size()
        out = []
        for r, week in enumerate(calendar.Calendar(0).monthdayscalendar(self.year, self.month)):
            for c, d in enumerate(week):
                if d:
                    out.append((d, QRectF(14 + c * (cw + 3), self.GRID_Y + r * (ch + 3), cw, ch)))
        return out

    def items(self):
        out = [("prev", self.prev_rect(), True), ("next", self.next_rect(), True), ("today", self.today_rect(), True)]
        out += [(("d", d), r, True) for d, r in self.day_rects()]
        return out

    def shift_month(self, delta):
        m = self.month - 1 + delta
        self.year, self.month = self.year + m // 12, m % 12 + 1
        self.update()

    def show_month_of(self, day):
        self.year, self.month = day.year, day.month
        self.update()

    def on_click(self, key):
        if key == "prev":
            self.shift_month(-1)
        elif key == "next":
            self.shift_month(1)
        elif key == "today":
            today = datetime.date.today()
            self.show_month_of(today)
            self.plant.diary_text.open_date(today)
        elif key[0] == "d":
            self.plant.diary_text.open_date(datetime.date(self.year, self.month, key[1]))

    def tooltip_at(self, pos):
        if self.prev_rect().contains(pos):
            return tr("Vorheriger Monat")
        if self.next_rect().contains(pos):
            return tr("Nächster Monat")
        return super().tooltip_at(pos)

    # ---------- Zeichnen ----------

    def heat(self, size):
        colors = HEAT["dark" if _THEME["dark"] else "light"]
        return QColor(colors[0] if size < HEAT_STEPS[0] else colors[1] if size < HEAT_STEPS[1] else colors[2])

    def paintEvent(self, _e):
        store = self.plant.diary
        n = store.month_count(self.year, self.month)
        sub = tr("Keine Einträge in diesem Monat") if n == 0 else \
            tr("1 Eintrag in diesem Monat") if n == 1 else tr("{n} Einträge in diesem Monat", n=n)
        base = self.font()
        p = self.begin(tr("Tagebuch"), sub)
        # Monatsleiste
        p.setFont(self.font_px(base, 13, True))
        p.setPen(T("text"))
        p.drawText(QRectF(14, 58, self.W - 28, 24), Qt.AlignmentFlag.AlignCenter, month_title(self.year, self.month))
        for rect, sign in ((self.prev_rect(), -1), (self.next_rect(), 1)):
            hot = self.hover == ("prev" if sign < 0 else "next")
            p.setPen(QPen(T("text") if hot else T("muted"), 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            cx, cy = rect.center().x(), rect.center().y()
            p.drawLine(QPointF(cx + 3 * sign * -1, cy - 5), QPointF(cx - 3 * sign * -1, cy))
            p.drawLine(QPointF(cx - 3 * sign * -1, cy), QPointF(cx + 3 * sign * -1, cy + 5))
        # Wochentage
        cw, ch = self.cell_size()
        p.setFont(self.font_px(base, 10, True))
        p.setPen(T("muted"))
        for i in range(7):
            p.drawText(QRectF(14 + i * (cw + 3), 86, cw, 14), Qt.AlignmentFlag.AlignCenter, weekday_short(i))
        # Tage
        today = datetime.date.today()
        selected = self.plant.diary_text.date
        for d, rect in self.day_rects():
            day = datetime.date(self.year, self.month, d)
            is_sel, is_today, has = day == selected, day == today, store.has(day)
            hover = self.hover == ("d", d)
            p.setPen(QPen(GREEN, 2.2) if is_sel else QPen(GOLD, 1.6) if is_today or hover else QPen(T("cell_border"), 1))
            p.setBrush(self.heat(store.size(day)) if has else T("hover_bg") if hover else T("cell"))
            p.drawRoundedRect(rect, 5, 5)
            p.setFont(self.font_px(base, 11, is_sel or is_today))
            p.setPen(T("text"))
            p.drawText(rect.adjusted(5, 3, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, str(d))
            if has:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(GREEN)
                p.drawEllipse(QPointF(rect.right() - 7, rect.bottom() - 7), 2.4, 2.4)
        # Fuss: Legende und «Heute»
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        p.drawText(QRectF(14, self.H - 38, self.W - 100, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   tr("grüner Punkt = Eintrag,\ndunkler = mehr Text"))
        r = self.today_rect()
        hot = self.hover == "today"
        p.setPen(QPen(T("btn_border"), 1))
        p.setBrush(T("btn_bg_hover") if hot else T("btn_bg"))
        p.drawRoundedRect(r, 10, 10)
        p.setFont(self.font_px(base, 11, True))
        p.setPen(T("button_text"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, tr("Heute"))
        p.end()
