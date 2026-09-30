"""Release Notes für das Info-Fenster (Reiter «Version»). Neueste Version zuerst.

Bei einem Release: den Eintrag «Unveröffentlicht» in die neue Versionsnummer mit Datum umbenennen,
`__version__` in __init__.py und `version` in pyproject.toml anpassen und oben einen neuen leeren
«Unveröffentlicht»-Eintrag anlegen (oder weglassen, solange nichts Neues da ist).
"""

# (Version, Datum oder None, [Punkte])
CHANGELOG = [
    ("Unveröffentlicht", None, [
        "Besucher auf der Pflanze sind 30 % grösser.",
        "Die Währung heisst jetzt Gold (statt Coins), das Symbol bleibt.",
        "Besucher-Stufen Besucher, Stammgast und Gartenbewohner (Setzling mit 1–3 Blättern im Sammelbuch), Belohnung in Gold; jeder Gartenbewohner gibt +1 % Wachstum.",
        "Seltene Farbvarianten der Besucher, mit Stern im Sammelbuch; der Name wird in Gold angezeigt, sobald gefunden.",
        "Info-Fenster mit Reiter «Version» und Release Notes.",
        "Goldene Aura hinter der Pflanze, sobald sie für das Prestige bereit ist (blüht).",
        "Sprechblase: Stadium in Gold mit Aussaat-Symbol, sobald die Pflanze für das Prestige bereit ist; ein Klick lagert sie ein und sät neu aus.",
    ]),
    ("0.1.0", "29.09.2026", [
        "Fünf Pflanzen mit eigenen Töpfen und Spielständen; Wachstum durch Klicks und Tastendrücke.",
        "Shop mit sechs Düngern und fünf Helfern: Tropfbewässerung, Hummel, Gartenzwerg, Pflanzenlampe, Düngerautomat.",
        "Gartenhaus, Prestige, Erfolge (einzeln abholbar), Fokus-Timer und Besucher-Sammelbuch.",
        "Regler für Pflanzen- und Menügrösse, Dunkelmodus, eigene Tooltips, Info-Fenster.",
        "Programme für Windows, macOS und Linux; Debug-Modus zum Testen.",
    ]),
]
