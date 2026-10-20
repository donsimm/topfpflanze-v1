"""Aufgaben (To-do): eine Liste je Tag. Nicht erledigte Aufgaben wandern von selbst auf den nächsten Tag
und behalten ihr ursprüngliches Datum («seit 12.10.»).

Die Aufgaben liegen in `todo.json` im Datenordner (neben dem Spielstand):
    {"id": 3, "text": "Steuern", "date": "2026-10-12", "done": null}
`date` ist der Tag, für den die Aufgabe ursprünglich erfasst wurde, `done` der Tag der Erledigung (oder null).
Das Wandern ist nur eine Anzeige-Regel (keine Daten werden verschoben): Am Tag D erscheinen
  - alle Aufgaben mit `date == D`,
  - an «heute» zusätzlich alle offenen Aufgaben mit früherem Datum,
  - an «heute» zusätzlich die heute erledigten Aufgaben mit früherem Datum.
"""

import datetime
import json
import os

from PyQt6.QtCore import QDate, QLocale, QPointF, QRectF, QTimer, Qt
from PyQt6.QtGui import QFont, QFontMetricsF, QPen
from PyQt6.QtWidgets import QLineEdit

from . import config
from .diary import GOLD, GREEN, locale, long_date
from .i18n import tr
from .panels import Panel
from .theme import T

MAX_TEXT = 200          # längste Aufgabe (Zeichen)
MAX_TASKS = 5000        # Obergrenze, damit die Datei nie ausufert


def iso(day):
    return day.isoformat()


def parse(text):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def clean_tasks(raw):
    """Prüft eine geladene oder importierte Liste: nur gültige Aufgaben, Texte gekürzt, Nummern eindeutig."""
    out, seen = [], set()
    for t in raw if isinstance(raw, list) else []:
        if not isinstance(t, dict) or not isinstance(t.get("text"), str) or parse(t.get("date")) is None:
            continue
        text = " ".join(t["text"].split())[:MAX_TEXT]
        done = t.get("done")
        if not text:
            continue
        tid = t.get("id")
        if not isinstance(tid, int) or isinstance(tid, bool) or tid in seen:
            tid = max(seen, default=0) + 1
        seen.add(tid)
        out.append({"id": tid, "text": text, "date": t["date"], "done": done if parse(done) else None})
        if len(out) >= MAX_TASKS:
            break
    return out


class TodoStore:
    """Alle Aufgaben mit den Anzeige-Regeln für einen Tag."""

    def __init__(self):
        self.tasks = []
        self.error = ""
        self.frozen = False      # beim Import oder Zurücksetzen gesperrt: nichts mehr schreiben
        self.load()

    @staticmethod
    def path():
        return config.STATE_DIR / "todo.json"

    def load(self):
        try:
            with open(self.path(), encoding="utf-8") as f:
                data = json.load(f)
            self.tasks = clean_tasks(data.get("tasks") if isinstance(data, dict) else None)
        except (OSError, ValueError):
            self.tasks = []

    def save(self):
        """Schreibt die Datei in einem Zug (zuerst temporär, dann ersetzen), damit sie nie halb geschrieben ist."""
        if self.frozen:
            return
        path = self.path()
        tmp = path.with_suffix(".json.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "tasks": self.tasks}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            self.error = ""
        except OSError as e:
            self.error = f"{type(e).__name__}: {e}"

    def next_id(self):
        return max((t["id"] for t in self.tasks), default=0) + 1

    def add(self, text, day):
        """Neue Aufgabe für `day`; gibt sie zurück (None bei leerem Text oder voller Liste)."""
        text = " ".join(text.split())[:MAX_TEXT]
        if not text or len(self.tasks) >= MAX_TASKS:
            return None
        task = {"id": self.next_id(), "text": text, "date": iso(day), "done": None}
        self.tasks.append(task)
        self.save()
        return task

    def find(self, tid):
        return next((t for t in self.tasks if t["id"] == tid), None)

    def toggle(self, tid, today):
        """Erledigt-Haken setzen (Tag der Erledigung = heute) oder wieder entfernen."""
        t = self.find(tid)
        if t:
            t["done"] = None if t["done"] else iso(today)
            self.save()

    def delete(self, tid):
        self.tasks = [t for t in self.tasks if t["id"] != tid]
        self.save()

    def clear_done(self):
        """Entfernt alle erledigten Aufgaben; gibt die Anzahl zurück."""
        n = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t["done"]]
        self.save()
        return n - len(self.tasks)

    def for_day(self, day, today):
        """Aufgaben, die am Tag `day` erscheinen: offene zuerst (älteste zuerst), danach die erledigten."""
        d = iso(day)
        shown = []
        for t in self.tasks:
            if t["date"] == d:
                shown.append(t)
            elif day == today and t["date"] < d and (not t["done"] or t["done"] == d):
                shown.append(t)
        shown.sort(key=lambda t: (bool(t["done"]), t["date"], t["id"]))
        return shown

    def open_today(self, today):
        """Anzahl offener Aufgaben, die heute anstehen (inklusive der mitgewanderten)."""
        d = iso(today)
        return sum(1 for t in self.tasks if not t["done"] and t["date"] <= d)

    def carried_today(self, today):
        """Anzahl offener Aufgaben aus früheren Tagen."""
        d = iso(today)
        return sum(1 for t in self.tasks if not t["done"] and t["date"] < d)


def short_date(day):
    return locale().toString(QDate(day.year, day.month, day.day), QLocale.FormatType.ShortFormat)


# ---------------------------------------------------------------- Fenster

class TodoWin(Panel):
    """Aufgabenliste eines Tages: Haken setzen, löschen, neue Aufgabe unten eintippen (Enter)."""

    W, H = 390, 470
    LIST_Y, ROW_H = 92, 30
    ROWS = 10
    BOX = 17            # Kantenlänge des Hakenfelds

    def __init__(self, plant):
        self.date = datetime.date.today()
        self.follow = True          # folgt dem heutigen Tag (auch über Mitternacht), bis man blättert
        self.scroll = 0
        self._style_key = None
        super().__init__(plant, self.W, self.H, "todo_pos")
        self.input = QLineEdit(self)
        self.input.setMaxLength(MAX_TEXT)
        self.input.setPlaceholderText(tr("Neue Aufgabe …"))
        self.input.returnPressed.connect(self.add_task)
        self.tick = QTimer(self)        # Tageswechsel bemerken, solange das Fenster offen ist
        self.tick.setInterval(30000)
        self.tick.timeout.connect(self.refresh)
        self.tick.start()
        self._layout_input()

    # ---------- Tag ----------

    @staticmethod
    def today():
        return datetime.date.today()

    def day(self):
        return self.today() if self.follow else self.date

    def refresh(self):
        if self.follow:
            self.date = self.today()
        self.update()

    def go(self, day):
        self.date = day
        self.follow = day == self.today()
        self.scroll = 0
        self.update()

    def shown(self):
        return self.plant.todo.for_day(self.day(), self.today())

    # ---------- Layout ----------

    def prev_rect(self):
        return QRectF(14, 58, 28, 24)

    def next_rect(self):
        return QRectF(self.W - 42, 58, 28, 24)

    def input_rect(self):
        return QRectF(14, self.H - 72, self.W - 28 - 34, 28)

    def add_rect(self):
        return QRectF(self.W - 14 - 28, self.H - 72, 28, 28)

    def today_rect(self):
        return QRectF(self.W - 76, self.H - 34, 62, 20)

    def row_rect(self, i):
        return QRectF(12, self.LIST_Y + i * self.ROW_H, self.W - 24, self.ROW_H - 3)

    def box_rect(self, row):
        return QRectF(row.left() + 6, row.center().y() - self.BOX / 2, self.BOX, self.BOX)

    def del_rect(self, row):
        return QRectF(row.right() - 24, row.center().y() - 9, 18, 18)

    def date_label_rect(self, row):
        return QRectF(row.right() - 24 - 98, row.top(), 96, row.height())

    def visible_rows(self):
        tasks = self.shown()
        self.scroll = max(0, min(self.scroll, max(0, len(tasks) - self.ROWS)))
        return tasks[self.scroll:self.scroll + self.ROWS]

    def items(self):
        out = [("prev", self.prev_rect(), True), ("next", self.next_rect(), True),
               ("today", self.today_rect(), True), ("add", self.add_rect(), True)]
        for i, t in enumerate(self.visible_rows()):
            row = self.row_rect(i)
            out += [(("c", t["id"]), self.box_rect(row).adjusted(-4, -4, 4, 4), True),
                    (("x", t["id"]), self.del_rect(row), True), (("r", t["id"]), row, False)]
        return out

    def item_at(self, pos):
        for key, r, _c in self.items():          # Haken und Löschen haben Vorrang vor der ganzen Zeile
            if r.contains(pos) and key[0] != "r":
                return key
        return super().item_at(pos)

    def wheelEvent(self, e):
        step = -1 if e.angleDelta().y() > 0 else 1
        self.scroll = max(0, self.scroll + step)
        self.update()

    # ---------- Eingabe ----------

    def add_task(self):
        day = max(self.day(), self.today())       # für vergangene Tage legt man nichts mehr an: dann heute
        if self.plant.todo.add(self.input.text(), day):
            self.input.clear()
            self.go(day)
            self.scroll = 10 ** 6                  # ans Ende: dort steht die neue Aufgabe (wird beim Zeichnen begrenzt)
            self.plant.bubble.update()

    def on_click(self, key):
        store = self.plant.todo
        if key == "prev":
            self.go(self.day() - datetime.timedelta(days=1))
        elif key == "next":
            self.go(self.day() + datetime.timedelta(days=1))
        elif key == "today":
            self.go(self.today())
        elif key == "add":
            self.add_task()
        elif key[0] == "c":
            store.toggle(key[1], self.today())
        elif key[0] == "x":
            store.delete(key[1])
        self.plant.bubble.update()

    def tooltip_at(self, pos):
        if self.prev_rect().contains(pos):
            return tr("Vorheriger Tag")
        if self.next_rect().contains(pos):
            return tr("Nächster Tag")
        if self.add_rect().contains(pos):
            return tr("Aufgabe hinzufügen (Enter)")
        for i, t in enumerate(self.visible_rows()):
            row = self.row_rect(i)
            if self.box_rect(row).adjusted(-4, -4, 4, 4).contains(pos):
                return tr("Wieder öffnen") if t["done"] else tr("Als erledigt markieren")
            if self.del_rect(row).contains(pos):
                return tr("Aufgabe löschen")
            if t["date"] != iso(self.day()) and self.date_label_rect(row).contains(pos):
                return tr("Ursprünglich für den {date} erfasst", date=long_date(parse(t["date"])))
        return super().tooltip_at(pos)

    # ---------- Eingabefeld ----------

    def rescale(self):
        super().rescale()
        if hasattr(self, "input"):
            self._layout_input()

    def _layout_input(self):
        k = self._k
        r = self.input_rect()
        self.input.setGeometry(int(r.x() * k), int(r.y() * k), int(r.width() * k), int(r.height() * k))
        font = QFont(self.font())
        font.setPixelSize(max(8, int(round(13 * k))))
        self.input.setFont(font)
        self._style_key = None
        self._style_input()

    def _style_input(self):
        key = (self._k, T("cell").name(), T("text").name())
        if key == self._style_key:
            return
        self._style_key = key
        self.input.setStyleSheet(
            f"QLineEdit {{ background: {T('cell').name()}; color: {T('text').name()}; border: 1px solid {T('cell_border').name()};"
            f" border-radius: {int(6 * self._k)}px; padding: 0 {int(6 * self._k)}px; selection-background-color: #9CCF9C;"
            " selection-color: #1E1E1E; }")

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()

    # ---------- Zeichnen ----------

    def paintEvent(self, _e):
        self._style_input()
        store = self.plant.todo
        day, today = self.day(), self.today()
        tasks = self.shown()
        open_n = sum(1 for t in tasks if not t["done"])
        done_n = len(tasks) - open_n
        if not tasks:
            sub = tr("Keine Aufgaben")
        elif open_n == 0:
            sub = tr("Alles erledigt ✓")
        else:
            sub = tr("{open} offen, {done} erledigt", open=open_n, done=done_n)
        base = self.font()
        p = self.begin(tr("Aufgaben"), sub)
        # Tagesleiste
        p.setFont(self.font_px(base, 13, True))
        p.setPen(T("text"))
        title = long_date(day)
        if day == today:
            title = tr("Heute") + " · " + title
        elif day == today + datetime.timedelta(days=1):
            title = tr("Morgen") + " · " + title
        elif day == today - datetime.timedelta(days=1):
            title = tr("Gestern") + " · " + title
        fm = QFontMetricsF(p.font())
        p.drawText(QRectF(46, 58, self.W - 92, 24), Qt.AlignmentFlag.AlignCenter,
                   fm.elidedText(title, Qt.TextElideMode.ElideRight, self.W - 92))
        for rect, sign in ((self.prev_rect(), -1), (self.next_rect(), 1)):
            hot = self.hover == ("prev" if sign < 0 else "next")
            p.setPen(QPen(T("text") if hot else T("muted"), 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            cx, cy = rect.center().x(), rect.center().y()
            p.drawLine(QPointF(cx + 3 * sign * -1, cy - 5), QPointF(cx - 3 * sign * -1, cy))
            p.drawLine(QPointF(cx - 3 * sign * -1, cy), QPointF(cx + 3 * sign * -1, cy + 5))
        # Liste
        rows = self.visible_rows()
        if not tasks:
            p.setFont(self.font_px(base, 11))
            p.setPen(T("muted"))
            msg = tr("Noch nichts geplant.\nUnten eine Aufgabe eintippen und Enter drücken.") if day >= today else \
                tr("Für diesen Tag gibt es keine Aufgaben.")
            p.drawText(QRectF(20, self.LIST_Y + 20, self.W - 40, 70), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                       | Qt.TextFlag.TextWordWrap, msg)
        for i, t in enumerate(rows):
            row = self.row_rect(i)
            done = bool(t["done"])
            hover = isinstance(self.hover, tuple) and self.hover[1] == t["id"]
            p.setPen(QPen(T("cell_border"), 1))
            p.setBrush(T("hover_bg") if hover else T("cell"))
            p.drawRoundedRect(row, 6, 6)
            box = self.box_rect(row)
            hot_box = self.hover == ("c", t["id"])
            p.setPen(QPen(GREEN if done else GOLD if hot_box else T("cell_border"), 1.8 if done or hot_box else 1.2))
            p.setBrush(GREEN if done else T("white"))
            p.drawRoundedRect(box, 4, 4)
            if done:
                p.setPen(QPen(T("white"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawLine(QPointF(box.left() + 4, box.center().y() + 0.5), QPointF(box.center().x() - 1, box.bottom() - 4.5))
                p.drawLine(QPointF(box.center().x() - 1, box.bottom() - 4.5), QPointF(box.right() - 3.5, box.top() + 4.5))
            carried = t["date"] != iso(day)
            text_right = row.right() - 30 - (98 if carried else 0)
            f = self.font_px(base, 12)
            f.setStrikeOut(done)
            p.setFont(f)
            p.setPen(T("muted") if done else T("text"))
            left = box.right() + 8
            p.drawText(QRectF(left, row.top(), text_right - left, row.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       QFontMetricsF(f).elidedText(t["text"], Qt.TextElideMode.ElideRight, text_right - left))
            if carried:         # ursprüngliches Datum der mitgewanderten Aufgabe
                late = not done
                p.setFont(self.font_px(base, 10, late))
                p.setPen(T("bad") if late else T("muted"))
                p.drawText(self.date_label_rect(row), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           tr("seit {date}", date=short_date(parse(t["date"]))))
            x = self.del_rect(row)
            hot_x = self.hover == ("x", t["id"])
            p.setPen(QPen(T("bad") if hot_x else T("muted"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(x.topLeft() + QPointF(5, 5), x.bottomRight() - QPointF(5, 5))
            p.drawLine(QPointF(x.right() - 5, x.top() + 5), QPointF(x.left() + 5, x.bottom() - 5))
        if len(tasks) > self.ROWS:      # Hinweis auf weitere Zeilen
            p.setFont(self.font_px(base, 10))
            p.setPen(T("muted"))
            first = self.scroll + 1
            p.drawText(QRectF(14, self.LIST_Y + self.ROWS * self.ROW_H, self.W - 28, 14), Qt.AlignmentFlag.AlignRight
                       | Qt.AlignmentFlag.AlignVCenter, tr("{a}–{b} von {n} (Mausrad)", a=first, b=first + len(rows) - 1, n=len(tasks)))
        # «Hinzufügen»
        r = self.add_rect()
        hot = self.hover == "add"
        p.setPen(QPen(GREEN, 1.6))
        p.setBrush(T("active_bg_hover") if hot else T("active_bg"))
        p.drawRoundedRect(r, 7, 7)
        p.setPen(QPen(T("button_text"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        c = r.center()
        p.drawLine(QPointF(c.x() - 5, c.y()), QPointF(c.x() + 5, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 5), QPointF(c.x(), c.y() + 5))
        # Fuss: Hinweis und «Heute»
        p.setFont(self.font_px(base, 10))
        p.setPen(T("muted"))
        carried_n = store.carried_today(today)
        hint = tr("Offene Aufgaben wandern auf den nächsten Tag\nund behalten ihr Datum.")
        if carried_n and day == today:
            hint = tr("{n} Aufgabe(n) aus früheren Tagen\nstehen noch offen.", n=carried_n)
        p.drawText(QRectF(14, self.H - 38, self.W - 100, 28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, hint)
        r = self.today_rect()
        hot = self.hover == "today"
        p.setPen(QPen(T("btn_border"), 1))
        p.setBrush(T("btn_bg_hover") if hot else T("btn_bg"))
        p.drawRoundedRect(r, 10, 10)
        p.setFont(self.font_px(base, 11, True))
        p.setPen(T("button_text"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, tr("Heute"))
        p.end()
