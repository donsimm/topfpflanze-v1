# Topfpflanze

Desktop-Pflanzen, die durch Mausklicks und Tastaturanschläge wachsen (PyQt6).
Spielanleitung: siehe Kopf von `src/topfpflanze/app.py`. Es wird nur die *Anzahl* der Tastendrücke gezählt, nie welche Taste.

## Installation

```
pip install .            # Windows / macOS / Linux
pip install ".[linux-keys]"   # Linux: zusätzlich evdev (Wayland)
topfpflanze              # oder: python -m topfpflanze
```

Debian/Ubuntu: vorher `sudo apt install python3-venv python3-pip libxcb-cursor0 libpulse0` (`libpulse0` für den Ton; ohne Audio bleibt das Spiel stumm), dann in einer virtuellen Umgebung installieren (`python3 -m venv .venv && source .venv/bin/activate`). Ohne `libxcb-cursor0` startet Qt (ab 6.5) nicht.

Linux, ohne offenes Terminal (Programmmenü-Eintrag, optional Autostart beim Anmelden):

```
bash scripts/install-linux.sh              # nur Programmmenü
bash scripts/install-linux.sh --autostart  # zusätzlich beim Anmelden starten
```

Meldungen des Spiels landen dann in `~/.local/share/topfpflanze/topfpflanze.log`.

Fertige Programme für Windows, macOS (Apple Silicon und Intel) und Linux erzeugt der Workflow `Release` (Git-Tag `vX.Y.Z`) und hängt sie an die GitHub-Release-Seite.

## Plattformhinweise

| System | Tastaturzählung | Hinweis |
|---|---|---|
| Windows | pynput | Spielstand in `%APPDATA%\topfpflanze` |
| macOS | pynput | Systemeinstellungen → Datenschutz → «Eingabeüberwachung» für die App freigeben; Spielstand in `~/Library/Application Support/topfpflanze` |
| Linux X11 | pynput oder evdev | `~/.local/share/topfpflanze` |
| Linux Wayland | evdev | Benutzer muss in der Gruppe `input` sein; Fenster bleiben je nach Compositor nicht «immer im Vordergrund» |

## Entwicklung

```
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen pytest
```

## Debug-Modus und Testen

```
python -m topfpflanze --debug              # eigener Spielstand im Unterordner «debug»
python -m topfpflanze --debug --speed 60   # mit Zeitraffer
python -m topfpflanze --data-dir ~/test    # beliebiger Spielstandordner (auch ohne Debug)
```

Im Debug-Modus zeigt das Pflanzenfenster oben links «DEBUG», und das Rechtsklick-Menü hat den Eintrag **Debug**:
Zeitraffer (1x/10x/60x/600x für Wasser, Dünger, Helfer, Besucher, Fokus-Timer, passives Einkommen), Gold, Wachstum und Wasser setzen,
Besucher erscheinen lassen, Fokus-Timer (1 Minute), Tastendrücke/Klicks für Erfolge, Tages-/Wochenerfolge zurücksetzen,
alle Helfer freischalten, Prestige +1. Der echte Spielstand bleibt unberührt.

## Grösse der Oberfläche

Rechtsklick → Einstellungen → zwei getrennte Regler (50 bis 200 %, «100 %» setzt zurück):

- **Pflanzengrösse:** Pflanze mit Topf (die Spielgrafik).
- **Menügrösse:** Sprechblase, Shop, Gartenhaus, Erfolge, Fokus-Timer, Sammelbuch. Standard 100 % (frühere Grösse).

Beide Einstellungen werden gespeichert. Über 100 % wird ein Fenster nie grösser als der Bildschirm.

## Sprachen

Deutsch (Standard), Englisch, Französisch und Italienisch. Umschalten: Rechtsklick → Einstellungen → Sprache / Language (das Spiel startet dabei neu).
Ohne Auswahl gilt die Systemsprache, sonst Deutsch.

Der deutsche Text ist der Schlüssel: im Code steht `tr("Dünger")`, mit Werten `tr("noch {n} bis {name}", n=3, name=x)`
(`i18n.py`). Die Übersetzungen stehen je Sprache in `src/topfpflanze/lang/<code>.py` (Wörterbuch `STRINGS`). Fehlt ein
Eintrag, erscheint der deutsche Text.

Neue Sprache: `lang/en.py` nach `lang/<code>.py` kopieren, die Werte übersetzen (Platzhalter `{…}` unverändert lassen),
den Code in `i18n.LANGUAGES` und in `i18n._load` eintragen und in `tests/test_basics.py` bei den Sprach-Tests ergänzen. Ein Test (`test_language_catalog_is_complete_and_consistent`)
prüft, dass kein Text fehlt und die Platzhalter stimmen. Neuer Text im Code: immer mit `tr(…)` schreiben und den
englischen Eintrag ergänzen, sonst schlägt der Test fehl.

## Aufbau (`src/topfpflanze/`)

| Modul | Inhalt |
|---|---|
| `app.py` | Programmstart, Kommandozeile, Spielanleitung im Kopf |
| `config.py` | Pfade, Fenstergrössen, Gold-Konstanten |
| `data.py` | Pflanzenarten, Dünger, Helfer, Besucher, Erfolge, Topfgeometrie |
| `plant.py` | Pflanzenfenster: Spielzustand, Logik, Eingaben, Menü |
| `plant_draw.py` | Zeichnen von Topf, Erde, Partikeln, Pflanzen |
| `bubble.py`, `shop.py`, `garden.py`, `panels.py`, `info.py` | Sprechblase, Shop, Gartenhaus, Erfolge/Fokus/Sammelbuch, Info-Fenster (Werte aus `data.py`, Release Notes aus `changelog.py`) |
| `drawing.py`, `theme.py`, `util.py` | Symbole, Farbschemata, Hilfsfunktionen |
| `keys.py` | Tastaturzählung (nur Anzahl) |
| `i18n.py`, `lang/` | Mehrsprachigkeit: `tr()`, Sprachwahl, Übersetzungen |
| `sound.py` | Ton: Giesssound und Gong (selbst erzeugt), Lautstärke |
| `sow.py`, `pots.py` | Dialog «Einlagern & neu aussäen», zufällige Topf-Varianten (Skins) |
| `scaling.py` | Skalierung der Oberfläche (Basisklasse `ScaledWidget`) |
| `helper_art.py` | Grafiken der Helfer (Anzeigen, Zwerg, Lampe) |
| `debug.py` | Debug-Modus |

Neue Pflanze: Eintrag in `data.py` (`PLANT_TYPES`, `PLANT_ORDER`, ggf. `POTS`) und eine `draw_<key>`-Methode in `plant_draw.py`.

## Offene Punkte / Roadmap

- Auf echten Windows-/macOS-Systemen testen (bisher nur unter Linux offscreen geprüft).
- Autostart, Tray-Symbol, Signierung/Notarisierung der Builds.
- Mehrsprachigkeit (derzeit nur Deutsch/Schweizer Schreibweise).
