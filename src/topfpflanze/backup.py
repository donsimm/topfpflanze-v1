"""Spieldaten sichern und wiederherstellen: Spielstand, Tagebuch und eigene Wörter in einer ZIP-Datei.

Die Sicherung enthält:
  manifest.json      Programm, Format, Version und Zeitpunkt
  state.json         Spielstand (Pflanzen, Gold, Erfolge, Einstellungen)
  diary.json         Tagebucheinträge
  diary_words.txt    eigenes Wörterbuch der Rechtschreibprüfung (falls vorhanden)
  tagebuch.txt       die Einträge als lesbarer Text (nur zum Nachlesen, wird beim Import nicht gelesen)

Beim Import werden nur diese Namen gelesen (nie Pfade aus der ZIP-Datei) und die Grössen begrenzt.
Fensterpositionen werden nicht übernommen, weil sie zu einem anderen Bildschirm gehören können.
"""

import datetime
import json
import os
import time
import zipfile

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QApplication

from .i18n import tr
from .panels import Panel
from .theme import T

APP_ID = "topfpflanze"
FORMAT = 1
MAX_BYTES = 50 * 1024 * 1024       # grösste zulässige Datei in der Sicherung (entpackt)
KEEP_SAFETY_COPIES = 5             # so viele Sicherungen «vor dem Import» bleiben im Ordner backups
NAMES = ("manifest.json", "state.json", "diary.json", "diary_words.txt", "tagebuch.txt")


class BackupError(Exception):
    """Die Sicherung kann nicht gelesen oder verwendet werden (Text ist für die Anzeige gedacht)."""


def default_name():
    return f"Topfpflanze-Sicherung-{datetime.date.today().isoformat()}.zip"


def diary_as_text(entries, moods=None):
    """Alle Einträge als lesbarer Text, neueste zuletzt."""
    lines = []
    for day in sorted(entries):
        e = entries[day]
        mood = e.get("mood")
        label = f" ({moods[mood]})" if moods and isinstance(mood, int) and 0 <= mood < len(moods) else ""
        lines.append(f"=== {day}{label} ===")
        lines.append(e.get("text", "").rstrip())
        lines.append("")
    return "\n".join(lines)


def write_backup(path, state, diary_entries, words, app_version, moods=None):
    """Schreibt die Sicherung als ZIP (zuerst temporär, dann ersetzen)."""
    manifest = {"app": APP_ID, "format": FORMAT, "app_version": app_version,
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "entries": len(diary_entries)}
    tmp = str(path) + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
        z.writestr("state.json", json.dumps(state, ensure_ascii=False, indent=1))
        z.writestr("diary.json", json.dumps({"version": 1, "entries": diary_entries}, ensure_ascii=False, indent=1))
        if words:
            z.writestr("diary_words.txt", "\n".join(sorted(words)) + "\n")
        z.writestr("tagebuch.txt", diary_as_text(diary_entries, moods))
    os.replace(tmp, path)
    return manifest


def _read(z, name):
    try:
        info = z.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_BYTES:
        raise BackupError(tr("Die Sicherung ist beschädigt oder zu gross."))
    return z.read(name)


def read_backup(path, current_version):
    """Liest und prüft eine Sicherung; gibt {manifest, state, diary, words} zurück oder wirft BackupError."""
    try:
        with zipfile.ZipFile(path) as z:
            raw_manifest, raw_state, raw_diary, raw_words = (_read(z, n) for n in NAMES[:4])
    except (OSError, zipfile.BadZipFile):
        raise BackupError(tr("Das ist keine gültige Sicherung von Topfpflanze."))
    try:
        manifest = json.loads(raw_manifest) if raw_manifest else None
        state = json.loads(raw_state) if raw_state else None
        diary = json.loads(raw_diary) if raw_diary else {"entries": {}}
    except ValueError:
        raise BackupError(tr("Das ist keine gültige Sicherung von Topfpflanze."))
    if not isinstance(manifest, dict) or manifest.get("app") != APP_ID or not isinstance(state, dict) \
            or "plants" not in state or not isinstance(diary, dict):
        raise BackupError(tr("Das ist keine gültige Sicherung von Topfpflanze."))
    if int(manifest.get("format", 0)) > FORMAT or _newer(manifest.get("app_version", ""), current_version):
        raise BackupError(tr("Die Sicherung stammt von einer neueren Version ({version}). Bitte zuerst das Spiel aktualisieren.",
                             version=manifest.get("app_version", "?")))
    entries = diary.get("entries", {})
    if not isinstance(entries, dict):
        raise BackupError(tr("Das ist keine gültige Sicherung von Topfpflanze."))
    entries = {k: v for k, v in entries.items() if isinstance(k, str) and isinstance(v, dict)}
    words = [w.strip() for w in raw_words.decode("utf-8", "replace").splitlines() if w.strip()] if raw_words else []
    return {"manifest": manifest, "state": strip_positions(state), "diary": entries, "words": words}


def _version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return ()


def _newer(backup_version, current):
    a, b = _version_tuple(backup_version), _version_tuple(current)
    return bool(a and b and a > b)


def strip_positions(state):
    """Entfernt gespeicherte Fensterpositionen (sie passen vielleicht nicht zum Bildschirm dieses Geräts)."""
    return {k: v for k, v in state.items() if k != "pos" and not k.endswith("_pos")}


def _atomic_write(path, text):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def restore(data, state_file, diary_file, words_file):
    """Schreibt die gelesene Sicherung an die Stellen des Spielstands (Ordner werden bei Bedarf angelegt)."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(state_file, json.dumps(data["state"], ensure_ascii=False))
    _atomic_write(diary_file, json.dumps({"version": 1, "entries": data["diary"]}, ensure_ascii=False, indent=1))
    if data["words"]:
        _atomic_write(words_file, "\n".join(sorted(data["words"])) + "\n")
    elif words_file.exists():
        words_file.unlink()


def make_safety_copy(directory, state, diary_entries, words, app_version, moods=None):
    """Sichert den jetzigen Stand vor einem Import in `backups/` und behält die letzten Sicherungen."""
    folder = directory / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    name = folder / f"vor-Import-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    write_backup(name, state, diary_entries, words, app_version, moods)
    old = sorted(folder.glob("vor-Import-*.zip"))
    for f in old[:-KEEP_SAFETY_COPIES]:
        try:
            f.unlink()
        except OSError:
            pass
    return name


# ---------------------------------------------------------------- Rückfrage im Stil des Spiels

class ConfirmWin(Panel):
    """Kleines Meldungs- oder Rückfragefenster: Titel, Text, ein oder zwei Knöpfe (kein Systemfenster)."""

    W = 360

    def __init__(self, plant):
        self.title, self.text, self.ok_label, self.cancel_label, self.callback = "", "", "OK", None, None
        super().__init__(plant, self.W, 170, "confirm_pos")

    def place_window(self):
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.center().x() - self.real_width() // 2, g.center().y() - self.real_height() // 2)

    def ask(self, title, text, ok_label, callback=None, cancel_label=None):
        """Zeigt das Fenster; `callback` läuft beim Klick auf den ersten Knopf."""
        self.title, self.text, self.ok_label, self.cancel_label, self.callback = title, text, ok_label, cancel_label, callback
        lines = max(2, int(len(text) / 46) + 1 + text.count("\n"))
        self.setFixedSize(self.W, 92 + lines * 16 + 40)
        self.place_window()
        self.show()
        self.raise_()
        self.update()

    def button_rects(self):
        y = self.height() - 42
        if self.cancel_label:
            return {"ok": QRectF(self.W - 12 - 140 * 2 - 8, y, 140, 30), "cancel": QRectF(self.W - 12 - 140, y, 140, 30)}
        return {"ok": QRectF(self.W - 12 - 140, y, 140, 30)}

    def items(self):
        return [(k, r, True) for k, r in self.button_rects().items()]

    def on_click(self, key):
        callback = self.callback if key == "ok" else None
        self.hide()
        if callback:
            callback()

    def paintEvent(self, _e):
        base = self.font()
        p = self.begin(self.title, "")
        p.setFont(self.font_px(base, 12))
        p.setPen(T("text"))
        p.drawText(QRectF(14, 60, self.W - 28, self.height() - 110),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, self.text)
        for key, r in self.button_rects().items():
            hot = self.hover == key
            primary = key == "ok"
            p.setPen(QPen(QColor("#2E9E44") if primary else T("btn_border"), 1.6 if primary else 1))
            p.setBrush(T("active_bg_hover") if primary and hot else T("active_bg") if primary else
                       T("btn_bg_hover") if hot else T("btn_bg"))
            p.drawRoundedRect(r, 8, 8)
            p.setFont(self.font_px(base, 12, True))
            p.setPen(T("button_text"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.ok_label if primary else self.cancel_label)
        p.end()
