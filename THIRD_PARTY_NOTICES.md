# Lizenzen und Drittkomponenten

**Topfpflanze** steht unter der **GNU General Public License, Version 3 oder (nach Wahl) jeder späteren Version**
(`GPL-3.0-or-later`, Volltext in `LICENSE`). Copyright (C) 2026 donsimm.

Die GPL ist auch die Voraussetzung dafür, PyQt6 ohne kommerzielle Lizenz zu verwenden: PyQt6 gibt es von Riverbank Computing
nur unter GPLv3 oder einer kostenpflichtigen kommerziellen Lizenz.

## Programmbibliotheken

| Komponente | Verwendung | Lizenz |
|---|---|---|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) (Riverbank Computing) | Oberfläche | GPLv3 oder kommerziell |
| [Qt 6](https://www.qt.io/licensing/) (The Qt Company) | von PyQt6 mitgeliefert | LGPLv3 / GPLv3 / kommerziell |
| [spylls](https://github.com/zverok/spylls) (Victor Shepelev) | Rechtschreibprüfung (Hunspell in Python) | MPL 2.0 (`licenses/MPL-2.0.txt`) |
| [pynput](https://github.com/moses-palmer/pynput) | Tastenzählung (Windows, macOS) | LGPLv3 |
| [evdev](https://github.com/gvalkov/python-evdev) | Tastenzählung (Linux, optional) | BSD 3-Clause |
| [PyInstaller](https://pyinstaller.org/) | nur beim Bau der Programme | GPLv2+ mit Ausnahme für das erzeugte Programm |

## Wörterbücher der Rechtschreibprüfung (`src/topfpflanze/dictionaries/`)

Datendateien im Hunspell-Format, getrennt vom Programmcode und mit eigener Lizenz; Kopien aus dem Paket
[phunspell 0.1.6](https://github.com/dvwright/phunspell) (Wörterbücher von LibreOffice, Stand 2021). Die Lizenztexte liegen jeweils im Ordner.

| Ordner | Wörterbuch / Urheber | Lizenz | Verträglich mit GPLv3 |
|---|---|---|---|
| `de_CH` | igerman98 (Schweizer Variante), © 1998–2016 Björn Jacke | GPLv2 **oder** GPLv3 (`COPYING_GPLv2`, `COPYING_GPLv3`) | ja (GPLv3 gewählt) |
| `it_IT` | Estensione linguistica italiana, LibreItalia / Marina Latini, © 2020 | GPLv3 (`README-it.txt`) | ja |
| `fr_FR` | Grammalecte, Olivier R. | MPL 2.0 (`LICENSE-MPL-2.0.txt`) | ja (MPL 2.0 §3.3 erlaubt die Kombination mit GPL) |
| `en_US` | SCOWL / Hunspell-Wörterbuch, © 2000–2018 Kevin Atkinson u. a. | freizügige, BSD-ähnliche Lizenz mit Copyright-Hinweisen (`README_en_US.txt`) | ja, sofern der Hinweis mitgeliefert wird |

Pflichten, die damit erfüllt sind: Die Hinweise und Lizenztexte bleiben unverändert in den Ordnern und werden
in den fertigen Programmen mitgepackt. Die Wörterbücher sind unverändert (kein Quelltext-Austausch nötig). Der Quellcode der
Programme ist öffentlich unter <https://github.com/donsimm/topfpflanze-v1>.

## Grafik und Ton

Die Grafiken werden im Programm gezeichnet (Qt) und die Töne beim Start erzeugt. Sie stehen als Teil des Programms
unter derselben GPL. Eingebundene Fremddateien gibt es nicht; das Programmsymbol (`icons/`) gehört zum Projekt.
