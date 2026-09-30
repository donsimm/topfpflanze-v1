"""Release Notes für das Info-Fenster (Reiter «Version»). Neueste Version zuerst.

Bei einem Release: den Eintrag «Unveröffentlicht» in die neue Versionsnummer mit Datum umbenennen,
`__version__` in __init__.py und `version` in pyproject.toml anpassen und oben einen neuen leeren
«Unveröffentlicht»-Eintrag anlegen (oder weglassen, solange nichts Neues da ist).
"""

from .i18n import tr


# (Version, Datum oder None, [Punkte])
CHANGELOG = [
    (tr("Unveröffentlicht"), None, [
        tr("Mehrsprachig: Deutsch und Englisch (Rechtsklick → Einstellungen → Sprache, startet das Spiel neu; Standard ist die Systemsprache). Weitere Sprachen sind eine zusätzliche Datei in lang/."),
        tr("Viel mehr Erfolge (über 80 statt 12): einmalige Erfolge sind in Reihen mit Stufen zusammengefasst, im Fenster erscheint je Reihe die nächste Stufe. Neu: Tasten bis 1 Million, Shop-Aktivität, Anzahl Besuche, Klicks, Fokus-Sitzungen, Gartenhaus, Prestige, Farbvarianten, Gartenbewohner und Tage in Folge gespielt."),
        tr("Fokus-Timer mit zusätzlicher 10-Minuten-Sitzung; im Fokusmodus feinere Umrandung von Zeit und Ring und ein kleines X unter der Zeit zum Abbrechen."),
        tr("Neu entdeckte Besucher und Farbvarianten werden mit einem roten Punkt am Sammelbuch-Symbol und auf der Karte markiert; Überfahren der Karte gilt als gesehen."),
        tr("Besucher auf der Pflanze sind 30 % grösser."),
        tr("Die Währung heisst jetzt Gold (statt Coins), das Symbol bleibt."),
        tr("Besucher-Stufen Besucher, Stammgast und Gartenbewohner (Setzling mit 1–3 Blättern im Sammelbuch), Belohnung in Gold; jeder Gartenbewohner gibt +1 % Wachstum."),
        tr("Seltene Farbvarianten der Besucher, mit Stern im Sammelbuch; der Name wird in Gold angezeigt, sobald gefunden."),
        tr("Info-Fenster mit Reiter «Version» und Release Notes."),
        tr("Goldene Aura hinter der Pflanze, sobald sie für das Prestige bereit ist (blüht)."),
        tr("Eigener Dialog «Einlagern & neu aussäen» statt Systemfenster: Topf wählen (Originaltopf gratis, ein günstiges und ein edles Design aus dem Sortiment der Pflanze) und bestätigen. 32 Topf-Designs, Bonsai mit weisser Keramik und Gold."),
        tr("Ton: Giesssound und Gong zum Ende des Fokus-Timers, Lautstärke 0–100 % in den Einstellungen, standardmässig stumm (0)."),
        tr("Fokusmodus (Schalter im Fokus-Timer): Beim Start verschwinden alle Menüfenster, nur Pflanze und die Zeit mit rundem Fortschrittsring bleiben sichtbar; danach kommen die Fenster zurück."),
        tr("Sprechblase: Stadium in Gold mit Aussaat-Symbol, sobald die Pflanze für das Prestige bereit ist; ein Klick lagert sie ein und sät neu aus."),
    ]),
    ("0.1.0", "29.09.2026", [
        tr("Fünf Pflanzen mit eigenen Töpfen und Spielständen; Wachstum durch Klicks und Tastendrücke."),
        tr("Shop mit sechs Düngern und fünf Helfern: Tropfbewässerung, Hummel, Gartenzwerg, Pflanzenlampe, Düngerautomat."),
        tr("Gartenhaus, Prestige, Erfolge (einzeln abholbar), Fokus-Timer und Besucher-Sammelbuch."),
        tr("Regler für Pflanzen- und Menügrösse, Dunkelmodus, eigene Tooltips, Info-Fenster."),
        tr("Programme für Windows, macOS und Linux; Debug-Modus zum Testen."),
    ]),
]
