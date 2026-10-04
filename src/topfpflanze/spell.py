"""Rechtschreibprüfung für das Tagebuch: Hunspell-Wörterbücher, gelesen mit der reinen Python-Bibliothek spylls.

Die Wörterbücher liegen in `dictionaries/<Name>/` (Lizenzen: dictionaries/NOTICE.md). Das Laden dauert je nach
Sprache 1 bis 4 Sekunden und läuft deshalb im Hintergrund; bis es fertig ist, wird nichts markiert. Eigene Wörter
stehen in `diary_words.txt` im Datenordner. Fehlt die Bibliothek oder ein Wörterbuch, bleibt die Prüfung aus.
"""

import itertools
import re
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from . import config

DICT_DIR = Path(__file__).parent / "dictionaries"
DICTIONARIES = {"de": "de_CH", "en": "en_US", "fr": "fr_FR", "it": "it_IT"}   # Sprachcode → Wörterbuch
LANGUAGE_NAMES = {"de": "Deutsch", "en": "English", "fr": "Français", "it": "Italiano"}
WORD_RE = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*")      # Buchstaben, innen ' oder - erlaubt (l'amour, Rad-Weg)
PERSONAL = "diary_words.txt"
_DICTS = {}                 # Sprache → Wörterbuch (einmal je Programmlauf geladen und von allen Prüfern geteilt)
_FAILED = set()
_WORDS = {}                 # Sprache → {Wort: richtig?}
_LOCK = threading.Lock()


def personal_path():
    return config.STATE_DIR / PERSONAL


class SpellChecker(QObject):
    """Prüft Wörter in der gewählten Sprache; laden im Hintergrund, `loaded(Sprache)` meldet das Ende."""

    loaded = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.pending = set()
        self.session = set()
        self.personal = set()
        self.load_personal()

    # ---------- Wörterbücher ----------

    @property
    def dicts(self):
        return _DICTS

    @property
    def failed(self):
        return _FAILED

    def load_now(self, lang):
        """Lädt das Wörterbuch sofort (wird im Hintergrundthread aufgerufen; Tests rufen es direkt)."""
        name = DICTIONARIES.get(lang)
        with _LOCK:
            if name is None or lang in _FAILED:
                return False
            if lang in _DICTS:
                return True
            try:
                from spylls.hunspell import Dictionary
                _DICTS[lang] = Dictionary.from_files(str(DICT_DIR / name / name))
                _WORDS[lang] = {}
            except Exception:                  # fehlende Bibliothek oder Datei: Prüfung bleibt aus
                _FAILED.add(lang)
                return False
        return True

    def _run(self, lang):
        self.load_now(lang)
        self.pending.discard(lang)
        try:
            self.loaded.emit(lang)
        except RuntimeError:                   # das Fenster gibt es nicht mehr
            pass

    def ensure(self, lang):
        """Startet das Laden im Hintergrund, falls nötig."""
        if lang in DICTIONARIES and lang not in _DICTS and lang not in self.pending and lang not in _FAILED:
            self.pending.add(lang)
            threading.Thread(target=self._run, args=(lang,), daemon=True).start()
        elif lang in _DICTS:
            self.loaded.emit(lang)

    def ready(self, lang):
        return lang in _DICTS

    def loading(self, lang):
        return lang in self.pending

    def available(self, lang):
        return lang in DICTIONARIES and lang not in _FAILED

    # ---------- Prüfen ----------

    def known(self, lang, word):
        cache = _WORDS[lang]
        if word not in cache:
            try:
                cache[word] = bool(_DICTS[lang].lookup(word))
            except Exception:
                cache[word] = True
        return cache[word]

    def check(self, lang, word):
        """True, wenn das Wort richtig geschrieben ist (oder nicht geprüft werden kann)."""
        if lang not in _DICTS or len(word) < 2 or word.isupper():
            return True
        if word in self.session or word in self.personal or word.lower() in self.personal:
            return True
        if self.known(lang, word):
            return True
        parts = [x for x in re.split(r"['’\-]", word) if x]
        if len(parts) > 1:      # l'amour, Rad-Weg: jeder Teil für sich (sehr kurze Teile wie «l'» gelten als richtig)
            return all(len(x) < 3 or self.check(lang, x) for x in parts)
        return False

    def suggest(self, lang, word, limit=6):
        if lang not in _DICTS:
            return []
        try:
            return list(itertools.islice(_DICTS[lang].suggest(word), limit))
        except Exception:
            return []

    # ---------- Eigene Wörter ----------

    def load_personal(self):
        try:
            self.personal = {w.strip() for w in personal_path().read_text(encoding="utf-8").splitlines() if w.strip()}
        except OSError:
            self.personal = set()

    def add_word(self, word):
        self.personal.add(word)
        try:
            personal_path().parent.mkdir(parents=True, exist_ok=True)
            personal_path().write_text("\n".join(sorted(self.personal)) + "\n", encoding="utf-8")
        except OSError:
            pass

    def ignore(self, word):
        self.session.add(word)
