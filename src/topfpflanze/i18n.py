"""Mehrsprachigkeit: der deutsche Text ist der Schlüssel.

    tr("Dünger")                               → «Dünger» bzw. die Übersetzung
    tr("noch {n} bis {name}", n=3, name="x")   → Platzhalter wie bei str.format

Fehlt eine Übersetzung, erscheint der deutsche Text. Die Übersetzungen stehen je Sprache in
`lang/<code>.py` als Wörterbuch `STRINGS` (deutscher Text → Übersetzung, gleiche Platzhalter).

Die Sprache wird beim Programmstart festgelegt (`init`), bevor die Spielmodule geladen werden, weil
Texte der Spieldaten einmalig beim Import übersetzt werden. Ein Sprachwechsel braucht deshalb einen Neustart.
"""

import json

DEFAULT = "de"
LANGUAGES = {"de": "Deutsch", "en": "English"}     # Code → Name in der eigenen Sprache

_lang = DEFAULT
_catalog = {}


def _load(code):
    """Wörterbuch einer Sprache. Statische Importe, damit PyInstaller die Dateien mitpackt."""
    if code == "en":
        from .lang import en
        return en.STRINGS
    raise ValueError(code)


def language():
    return _lang


def set_language(code):
    """Stellt die Sprache ein (unbekannte Codes → Deutsch) und lädt die Übersetzungen."""
    global _lang, _catalog
    _lang = code if code in LANGUAGES else DEFAULT
    _catalog = {}
    if _lang != DEFAULT:
        _catalog = dict(_load(_lang))
    return _lang


def system_language():
    """Sprache des Systems, sofern unterstützt, sonst Deutsch."""
    try:
        from PyQt6.QtCore import QLocale
        code = QLocale.system().name().split("_")[0].lower()
    except Exception:
        return DEFAULT
    return code if code in LANGUAGES else DEFAULT


def saved_language(state_file):
    """Gewählte Sprache aus dem Spielstand («auto» oder nicht gesetzt → Systemsprache)."""
    try:
        with open(state_file, encoding="utf-8") as f:
            code = json.load(f).get("language", "auto")
    except (OSError, ValueError, AttributeError):
        code = "auto"
    return system_language() if code not in LANGUAGES else code


def init(state_file):
    return set_language(saved_language(state_file))


def tr(text, **values):
    """Übersetzt `text`; mit Werten werden die Platzhalter {name} eingesetzt."""
    if _catalog:
        text = _catalog.get(text, text)
    return text.format(**values) if values else text
