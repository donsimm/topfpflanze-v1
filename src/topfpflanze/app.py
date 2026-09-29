"""
Topfpflanze – Desktop-Pflanzen, die durch Klicks und Tastaturanschläge wachsen.

Pflanzen (Rechtsklick-Menü > «Pflanze wählen», jede mit eigenem Spielstand):
  Wiesenblume   Mittel        Terrakottatopf   (die ursprüngliche Pflanze)
  Kaktus        Leicht        Betontopf        braucht wenig Wasser
  Tulpe         Mittel        Keramiktopf      wächst NUR durch Mausklicks
  Sonnenblume   Schwer        Zinkeimer        braucht viel Wasser, lange Wachstumszeit
  Bonsai        Sehr schwer   Bonsaischale     wächst nur gut bei 30–80 % Wasser

Bedienung:
  Linksklick                 giessen (Wasser + Wachstum)
  Linke Maustaste ziehen     Fenster verschieben
  Mittelklick                Status-Sprechblase ein-/ausblenden
  Sprechblase ziehen         Sprechblase verschieben (eigenes Fenster)
  Symbol in der Sprechblase  Pflanze wählen (aktive Pflanze grün umrandet)
  Taschen-Symbol             Dünger-Shop öffnen/schliessen
  Gartenhaus-Symbol          Gartenhaus (Ehrenhalle) öffnen/schliessen

Sprechblase: oben die fünf Pflanzen, darunter die Werkzeuge
  Shop · Gartenhaus · Erfolge · Fokus-Timer · Besucher-Sammelbuch

Helfer (Shop > Reiter «Helfer», einmal kaufen, einzeln ein-/ausschaltbar):
  Tropfbewässerung, Hummel, Gartenzwerg, Pflanzenlampe, Düngerautomat

Prestige:
  Eine voll ausgewachsene Pflanze einlagern erhöht die Prestige-Stufe dieser Art um 1
  (je Stufe dauerhaft +10 % Wachstum und Coins). Nicht ausgewachsene Pflanzen kommen
  nur ins Gartenhaus.

Erfolge: 3 tägliche, 3 wöchentliche und 6 einmalige. Erreichte Erfolge holt man einzeln (Geschenk-Symbol)
  oder mit «Alle abholen» ab; nicht abgeholte tägliche/wöchentliche stehen unten in der Liste «Nicht abgeholt».
Fokus-Timer: 25, 45 oder 60 Minuten mit doppeltem Wachstum, Abbruch kostet nur den Bonus.
Besucher: kommen von selbst; Klick auf einen Besucher begrüsst ihn (+3 Coins).

Gartenhaus:
  - Wird eine Pflanze neu ausgesät, kommt sie in jedem Stadium mit Datum und Uhrzeit ins Gartenhaus.
  - Schaltfläche «Einlagern & neu aussäen» unten im Gartenhaus; die Samentüte wird golden
    und pulsiert, sobald die ausgewählte Pflanze blüht.
  - Karten lassen sich über das × oben links auf der Karte löschen (mit Rückfrage).
  - Neu ausgesäte Pflanzen erhalten eine zufällige Blütenfarbe.

Coins und Dünger:
  - Jede erreichte Wachstumsstufe bringt Coins (je schwieriger die Pflanze, desto mehr).
  - Nach der Blüte bringt jedes weitere Viertel des Blütewerts erneut Coins.
  - Passives Einkommen: 2 Coins pro Stunde, solange das Programm läuft.
  - Im Shop gekaufter Dünger wirkt auf die ausgewählte Pflanze: mehr Wachstum,
    teilweise aber höherer Wasserverbrauch. Die Laufzeit zählt nur, solange die
    Pflanze ausgewählt ist und das Programm läuft.
  Rechtsklick                Menü (Einstellungen: Regler «Grösse» 50–200 %)

Spielmechanik:
  - Wasser sinkt mit der Zeit (Geschwindigkeit je nach Pflanze), auch bei ausgeschaltetem PC.
  - Nicht ausgewählte Pflanzen pausieren: kein Wasserverlust, kein Wachstum.
  - Tastendrücke lassen die Pflanze wachsen und verbrauchen etwas Wasser.
  - Klicks bei vollem Wasserstand bringen Wachstum, ohne zu giessen (Wachstumspartikel statt Tropfen).

Abhängigkeiten:
  PyQt6    erforderlich
  pynput   Tastaturzählung unter Windows, macOS und Linux/X11
  evdev    optional (nur Linux): Tastaturzählung auch unter Wayland (Benutzer in Gruppe 'input')

Datenschutz: Es wird ausschliesslich die Anzahl der Tastendrücke gezählt,
nicht welche Tasten gedrückt wurden.
"""


import argparse
import signal
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from . import config, debug
from .config import APP_NAME
from .plant import Plant


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="topfpflanze", description="Desktop-Pflanzen, die durch Klicks und Tastaturanschläge wachsen.")
    ap.add_argument("--data-dir", metavar="ORDNER", help="Spielstand in diesem Ordner speichern statt im Standardordner")
    ap.add_argument("--debug", action="store_true",
                    help="Debug-Modus: Menü «Debug», Zeitraffer; verwendet einen eigenen Spielstand (Unterordner «debug»)")
    ap.add_argument("--speed", type=float, default=1.0, metavar="FAKTOR", help="Zeitraffer beim Start (nur mit --debug)")
    return ap.parse_known_args(argv)


def main(argv=None):
    args, qt_args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.debug:
        debug.enable(args.speed)
    if args.data_dir:
        config.set_data_dir(args.data_dir)
    elif args.debug:
        config.set_data_dir(config.STATE_DIR / "debug")
    if args.debug:
        print(f"Debug-Modus, Spielstand: {config.STATE_FILE}", flush=True)
    app = QApplication([sys.argv[0]] + qt_args)
    app.setApplicationName(APP_NAME)
    # Tool-Fenster zählen nicht als Hauptfenster: ohne diese Zeile würde das
    # Schliessen eines Dialogs die Anwendung beenden.
    app.setQuitOnLastWindowClosed(False)

    plant = Plant()
    plant.show()
    plant.set_bubble(plant.state.get("bubble", True))
    app.aboutToQuit.connect(plant.save_state)

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: app.quit())
    # Die Qt-Schleife gibt Python sonst nie die Kontrolle für Signale.
    keepalive = QTimer()
    keepalive.start(500)
    keepalive.timeout.connect(lambda: None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
