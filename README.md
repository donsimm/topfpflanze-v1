# Topfpflanze

Desktop-Pflanzen, die durch Mausklicks und Tastaturanschläge wachsen (PyQt6).
Spielanleitung: siehe Kopf von `src/topfpflanze/game.py`. Es wird nur die *Anzahl* der Tastendrücke gezählt, nie welche Taste.

## Installation

```
pip install .            # Windows / macOS / Linux
pip install ".[linux-keys]"   # Linux: zusätzlich evdev (Wayland)
topfpflanze              # oder: python -m topfpflanze
```

Debian/Ubuntu: vorher `sudo apt install python3-venv python3-pip libxcb-cursor0`, dann in einer virtuellen Umgebung installieren (`python3 -m venv .venv && source .venv/bin/activate`). Ohne `libxcb-cursor0` startet Qt (ab 6.5) nicht.

Fertige Programme für Windows, macOS und Linux erzeugt der Workflow `Release` (Git-Tag `vX.Y.Z`) und hängt sie an die GitHub-Release-Seite.

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

## Offene Punkte / Roadmap

- Auf echten Windows-/macOS-Systemen testen (bisher nur unter Linux offscreen geprüft).
- Autostart, Tray-Symbol, Signierung/Notarisierung der Builds.
- `game.py` (2700 Zeilen) in Module aufteilen: Daten, Zeichnen, Fenster, Speicherstand.
- Mehrsprachigkeit (derzeit nur Deutsch/Schweizer Schreibweise).
