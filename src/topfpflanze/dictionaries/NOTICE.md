# Wörterbücher der Rechtschreibprüfung

Diese Dateien (Hunspell-Format) werden vom Tagebuch zur Rechtschreibprüfung gelesen (Modul `spell.py`, Bibliothek
[spylls](https://github.com/zverok/spylls)). Sie sind eigene, getrennte Datendateien mit eigenen Lizenzen und
nicht Teil des Programmcodes. Die Kopien stammen aus dem Paket [phunspell 0.1.6](https://github.com/dvwright/phunspell)
(Wörterbücher von LibreOffice, Stand 2021).

| Ordner | Wörterbuch | Lizenz (Angabe in den Dateien) |
|---|---|---|
| `de_CH` | Deutsch (Schweiz), abgeleitet von igerman98, © 1998–2016 Björn Jacke | GPLv2 oder GPLv3 (`COPYING_GPLv2`, `COPYING_GPLv3`) |
| `en_US` | Englisch (USA), abgeleitet von SCOWL, © Kevin Atkinson | siehe `README_en_US.txt` (BSD-ähnlich) |
| `fr_FR` | Französisch, Grammalecte, Olivier R. | MPL 2.0 (`README.txt`, `LICENSE-MPL-2.0.txt`) |
| `it_IT` | Italienisch | GPLv3 (`README-it.txt`) |

Das persönliche Wörterbuch (Wörter, die du hinzufügst) liegt nicht hier, sondern als `diary_words.txt` im Datenordner.
