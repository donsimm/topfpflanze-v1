"""English translations.

To add a language: copy this file to `<code>.py`, translate the values and register the code in `i18n.LANGUAGES` and `i18n._load`.

Key: German source text; value: translation with the same {placeholders}.
"""

STRINGS = {
    "{v} auswählen ({difficulty})":
        "Select {v} ({difficulty})",
    "{v} einlagern & neu aussäen\nPrestige-Stufe {lvl} → {lvl2}, Topf wählen und bestätigen":
        "Store {v} & resow\nPrestige level {lvl} → {lvl2}, choose a pot and confirm",
    "Dünger-Shop schliessen":
        "Close fertilizer shop",
    "Dünger-Shop öffnen":
        "Open fertilizer shop",
    "\nGold: {coins} (+{rate} pro Stunde)":
        "\nGold: {coins} (+{rate} per hour)",
    "Gartenhaus schliessen":
        "Close Garden Shed",
    "Gartenhaus öffnen":
        "Open Garden Shed",
    "\n{garden} Pflanze(n) eingelagert":
        "\n{garden} plant(s) stored",
    "Erfolge schliessen":
        "Close achievements",
    "Erfolge öffnen":
        "Open achievements",
    "Fokus-Timer schliessen":
        "Close focus timer",
    "Fokus-Timer öffnen":
        "Open focus timer",
    "Info schliessen":
        "Close info",
    "Info öffnen":
        "Open info",
    "\nSpielregeln und Werte":
        "\nRules and values",
    "Besucher-Sammelbuch schliessen":
        "Close visitor book",
    "Besucher-Sammelbuch öffnen":
        "Open visitor book",
    "\n{book} / {total} entdeckt":
        "\n{book} / {total} discovered",
    "Pflanze":
        "Plant",
    "Stadium":
        "Stage",
    "Wachstum":
        "Growth",
    "Wasser":
        "Water",
    "Dünger":
        "Fertilizer",
    "Prestige":
        "Prestige",
    "Klicks":
        "Clicks",
    "Tasten":
        "Keys",
    "Alter":
        "Age",
    "Gold":
        "Gold",
    "\n{pend} zum Abholen bereit":
        "\n{pend} ready to collect",
    "– (nur Klicks)":
        "– (clicks only)",
    "Helfer gelten je Pflanze (wie der Dünger): pro Pflanze kaufen und ein-/ausschalten; beim Neuaussäen bleiben sie bei der Pflanze. Bereits gekaufte Helfer gelten weiterhin für alle Pflanzen.":
        "Helpers now apply per plant (like fertilizer): buy and switch them per plant; they stay with the plant when resowing. Helpers you already bought keep working for all plants.",
    "Mehrsprachig: Deutsch, Englisch, Französisch und Italienisch (Rechtsklick → Einstellungen → Sprache, startet das Spiel neu; Standard ist die Systemsprache). Weitere Sprachen sind eine zusätzliche Datei in lang/.":
        "Multilingual: German, English, French and Italian (right click → Settings → Language, restarts the game; the default is the system language). More languages are just one extra file in lang/.",
    "Viel mehr Erfolge (über 80 statt 12): einmalige Erfolge sind in Reihen mit Stufen zusammengefasst, im Fenster erscheint je Reihe die nächste Stufe. Neu: Tasten bis 1 Million, Shop-Aktivität, Anzahl Besuche, Klicks, Fokus-Sitzungen, Gartenhaus, Prestige, Farbvarianten, Gartenbewohner und Tage in Folge gespielt.":
        "Many more achievements (over 80 instead of 12): one-time achievements are grouped into series with tiers, and the window shows the next tier of each series. New: keys up to 1 million, shop activity, number of visits, clicks, focus sessions, Garden Shed, prestige, colour variants, garden residents and days played in a row.",
    "Fokus-Timer mit zusätzlicher 10-Minuten-Sitzung; im Fokusmodus feinere Umrandung von Zeit und Ring und ein kleines X unter der Zeit zum Abbrechen.":
        "Focus timer with an extra 10-minute session; in focus mode a finer outline around the time and ring, and a small X under the time to cancel.",
    "Neu entdeckte Besucher und Farbvarianten werden mit einem roten Punkt am Sammelbuch-Symbol und auf der Karte markiert; Überfahren der Karte gilt als gesehen.":
        "Newly discovered visitors and colour variants are marked with a red dot on the visitor book icon and on the card; hovering over the card counts as seen.",
    "Besucher auf der Pflanze sind 30 % grösser.":
        "Visitors on the plant are 30 % larger.",
    "Die Währung heisst jetzt Gold (statt Coins), das Symbol bleibt.":
        "The currency is now called Gold (instead of Coins); the symbol stays.",
    "Besucher-Stufen Besucher, Stammgast und Gartenbewohner (Setzling mit 1–3 Blättern im Sammelbuch), Belohnung in Gold; jeder Gartenbewohner gibt +1 % Wachstum.":
        "Visitor levels Visitor, Regular and Garden Resident (seedling with 1–3 leaves in the visitor book), rewarded in Gold; every Garden Resident gives +1 % growth.",
    "Seltene Farbvarianten der Besucher, mit Stern im Sammelbuch; der Name wird in Gold angezeigt, sobald gefunden.":
        "Rare colour variants of visitors, with a star in the visitor book; the name is shown in gold once found.",
    "Info-Fenster mit Reiter «Version» und Release Notes.":
        "Info window with a «Version» tab and release notes.",
    "Goldene Aura hinter der Pflanze, sobald sie für das Prestige bereit ist (blüht).":
        "Golden aura behind the plant as soon as it is ready for prestige (in bloom).",
    "Eigener Dialog «Einlagern & neu aussäen» statt Systemfenster: Topf wählen (Originaltopf gratis, ein günstiges und ein edles Design aus dem Sortiment der Pflanze) und bestätigen. 32 Topf-Designs, Bonsai mit weisser Keramik und Gold.":
        "Own dialog «Store & resow» instead of a system window: choose a pot (original pot free, one affordable and one premium design from the plant's range) and confirm. 32 pot designs, bonsai with white ceramic and gold.",
    "Ton: Giesssound und Gong zum Ende des Fokus-Timers, Lautstärke 0–100 % in den Einstellungen, standardmässig stumm (0).":
        "Sound: watering sound and a gong at the end of the focus timer, volume 0–100 % in the settings, muted by default (0).",
    "Fokusmodus (Schalter im Fokus-Timer): Beim Start verschwinden alle Menüfenster, nur Pflanze und die Zeit mit rundem Fortschrittsring bleiben sichtbar; danach kommen die Fenster zurück.":
        "Focus mode (switch in the focus timer): when it starts, all menu windows disappear and only the plant and the time with a round progress ring stay visible; the windows return afterwards.",
    "Sprechblase: Stadium in Gold mit Aussaat-Symbol, sobald die Pflanze für das Prestige bereit ist; ein Klick lagert sie ein und sät neu aus.":
        "Status bubble: stage in gold with a seed symbol as soon as the plant is ready for prestige; one click stores it and resows.",
    "Fünf Pflanzen mit eigenen Töpfen und Spielständen; Wachstum durch Klicks und Tastendrücke.":
        "Five plants with their own pots and saved games; growth through clicks and key presses.",
    "Shop mit sechs Düngern und fünf Helfern: Tropfbewässerung, Hummel, Gartenzwerg, Pflanzenlampe, Düngerautomat.":
        "Shop with six fertilizers and five helpers: drip irrigation, bumblebee, garden gnome, grow lamp, fertilizer dispenser.",
    "Gartenhaus, Prestige, Erfolge (einzeln abholbar), Fokus-Timer und Besucher-Sammelbuch.":
        "Garden Shed, prestige, achievements (collectable one by one), focus timer and visitor book.",
    "Regler für Pflanzen- und Menügrösse, Dunkelmodus, eigene Tooltips, Info-Fenster.":
        "Sliders for plant and menu size, dark mode, custom tooltips, info window.",
    "Programme für Windows, macOS und Linux; Debug-Modus zum Testen.":
        "Programs for Windows, macOS and Linux; debug mode for testing.",
    "Besucher":
        "Visitor",
    "Stammgast":
        "Regular",
    "Gartenbewohner":
        "Garden Resident",
    "häufig":
        "common",
    "selten":
        "rare",
    "sehr selten":
        "very rare",
    "Shop":
        "Shop",
    "Gartenhaus":
        "Garden Shed",
    "Erfolge":
        "Achievements",
    "Fokus-Timer":
        "Focus Timer",
    "Besucher-Sammelbuch":
        "Visitor Book",
    "Info":
        "Info",
    "Samen":
        "Seed",
    "Keimling":
        "Sprout",
    "Jungpflanze":
        "Seedling",
    "Grosse Pflanze":
        "Large plant",
    "Knospe":
        "Bud",
    "Blühend":
        "In bloom",
    "Wiesenblume":
        "Meadow Flower",
    "Mittel":
        "Medium",
    "Kaktus":
        "Cactus",
    "Leicht":
        "Easy",
    "Tulpe":
        "Tulip",
    "Mittel, nur Klicks":
        "Medium, clicks only",
    "Sonnenblume":
        "Sunflower",
    "Schwer":
        "Hard",
    "Bonsai":
        "Bonsai",
    "Sehr schwer":
        "Very hard",
    "Kompost":
        "Compost",
    "Flüssigdünger":
        "Liquid Fertilizer",
    "Hornspäne":
        "Horn Shavings",
    "Blaukorn":
        "NPK Granules",
    "Turbo-Booster":
        "Turbo Booster",
    "Wundermix":
        "Wonder Mix",
    "Tropfbewässerung":
        "Drip Irrigation",
    "Hält den Wasserstand automatisch bei mindestens 40 %.":
        "Keeps the water level at 40 % or more automatically.",
    "Hummel":
        "Bumblebee",
    "Kommt etwa alle 10 Minuten vorbei und bringt einen Wachstumsschub.":
        "Drops by about every 10 minutes and gives a growth boost.",
    "Gartenzwerg":
        "Garden Gnome",
    "Hilft alle 30 Sekunden mit: bringt Wachstum wie ein Mausklick.":
        "Helps every 30 seconds: gives growth like a mouse click.",
    "Pflanzenlampe":
        "Grow Lamp",
    "Dauerhaft +10 % Wachstum für diese Pflanze.":
        "Permanent +10 % growth for this plant.",
    "Düngerautomat":
        "Fertilizer Dispenser",
    "Kauft den zuletzt verwendeten Dünger automatisch nach, sobald er ausläuft.":
        "Automatically rebuys the last fertilizer used as soon as it runs out.",
    "Marienkäfer":
        "Ladybird",
    "Krabbelt gern auf Blättern herum.":
        "Likes crawling around on leaves.",
    "Kohlweissling":
        "Cabbage White",
    "Flattert bei jeder Pflanze vorbei.":
        "Flutters past every plant.",
    "Honigbiene":
        "Honeybee",
    "Kommt nur zu blühenden Pflanzen.":
        "Only visits plants in bloom.",
    "Zitronenfalter":
        "Brimstone Butterfly",
    "Ein seltener Gast, Geduld lohnt sich.":
        "A rare guest, patience pays off.",
    "Libelle":
        "Dragonfly",
    "Zeigt sich erst bei grösseren Pflanzen.":
        "Only shows up at larger plants.",
    "Tagpfauenauge":
        "Peacock Butterfly",
    "Liebt Blüten.":
        "Loves blossoms.",
    "Rotkehlchen":
        "Robin",
    "Setzt sich manchmal auf den Topfrand grosser Pflanzen.":
        "Sometimes sits on the pot rim of large plants.",
    "Glühwürmchen":
        "Firefly",
    "Nur abends und nachts (20–6 Uhr) zu sehen.":
        "Only seen in the evening and at night (8 pm – 6 am).",
    "Goldener Marienkäfer":
        "Golden Ladybird",
    "Blauer Kohlweissling":
        "Blue Cabbage White",
    "Blaue Biene":
        "Blue Bee",
    "Rosa Zitronenfalter":
        "Pink Brimstone Butterfly",
    "Rote Libelle":
        "Red Dragonfly",
    "Violettes Tagpfauenauge":
        "Violet Peacock Butterfly",
    "Weisses Rotkehlchen":
        "White Robin",
    "Blaues Glühwürmchen":
        "Blue Firefly",
    "Fleissige Finger":
        "Busy Fingers",
    "2'000 Tasten heute":
        "2'000 keys today",
    "Giesskanne":
        "Watering Can",
    "20-mal klicken heute":
        "Click 20 times today",
    "Fokussiert":
        "Focused",
    "1 Fokus-Sitzung heute":
        "1 focus session today",
    "Tastenmarathon":
        "Key Marathon",
    "20'000 Tasten diese Woche":
        "20'000 keys this week",
    "Wachstumsschub":
        "Growth Spurt",
    "300 Wachstum diese Woche":
        "300 growth this week",
    "Fokus-Woche":
        "Focus Week",
    "5 Fokus-Sitzungen diese Woche":
        "5 focus sessions this week",
    "Erste Blüte":
        "First Bloom",
    "1 Art blühen lassen":
        "Bloom 1 species",
    "Zweite Art":
        "Second Species",
    "2 Arten blühen lassen":
        "Bloom 2 species",
    "Dreierstrauss":
        "Bouquet of Three",
    "3 Arten blühen lassen":
        "Bloom 3 species",
    "Blumenbeet":
        "Flower Bed",
    "4 Arten blühen lassen":
        "Bloom 4 species",
    "Artenvielfalt":
        "Biodiversity",
    "Alle 5 Arten blühen lassen":
        "Bloom all 5 species",
    "Sammler":
        "Collector",
    "5 Pflanzen im Gartenhaus":
        "5 plants in the Garden Shed",
    "Gartenhaus-Besitzer":
        "Shed Owner",
    "15 Pflanzen im Gartenhaus":
        "15 plants in the Garden Shed",
    "Gartenbaumeister":
        "Master Gardener",
    "50 Pflanzen im Gartenhaus":
        "50 plants in the Garden Shed",
    "Gartenkönig":
        "Garden King",
    "150 Pflanzen im Gartenhaus":
        "150 plants in the Garden Shed",
    "Gärtnerei":
        "Nursery",
    "500 Pflanzen im Gartenhaus":
        "500 plants in the Garden Shed",
    "Aufstieg":
        "Ascent",
    "Erste Prestige-Stufe erreichen":
        "Reach the first prestige level",
    "Aufsteiger":
        "Climber",
    "5 Prestige-Stufen insgesamt":
        "5 prestige levels in total",
    "Veteran":
        "Veteran",
    "15 Prestige-Stufen insgesamt":
        "15 prestige levels in total",
    "Grossmeister":
        "Grandmaster",
    "50 Prestige-Stufen insgesamt":
        "50 prestige levels in total",
    "Legende":
        "Legend",
    "150 Prestige-Stufen insgesamt":
        "150 prestige levels in total",
    "Tipper":
        "Typist",
    "1'000 Tasten insgesamt":
        "1'000 keys in total",
    "Vieltipper":
        "Heavy Typist",
    "10'000 Tasten insgesamt":
        "10'000 keys in total",
    "Tastenmeister":
        "Key Master",
    "100'000 Tasten insgesamt":
        "100'000 keys in total",
    "Tastenheld":
        "Key Hero",
    "500'000 Tasten insgesamt":
        "500'000 keys in total",
    "Tastenlegende":
        "Key Legend",
    "1'000'000 Tasten insgesamt":
        "1'000'000 keys in total",
    "Giesskännchen":
        "Little Watering Can",
    "100-mal klicken insgesamt":
        "Click 100 times in total",
    "Wasserträger":
        "Water Carrier",
    "1'000-mal klicken insgesamt":
        "Click 1'000 times in total",
    "Platzregen":
        "Downpour",
    "10'000-mal klicken insgesamt":
        "Click 10'000 times in total",
    "Regenmacher":
        "Rainmaker",
    "100'000-mal klicken insgesamt":
        "Click 100'000 times in total",
    "Sintflut":
        "Deluge",
    "1'000'000-mal klicken insgesamt":
        "Click 1'000'000 times in total",
    "Erster Einkauf":
        "First Purchase",
    "1 Kauf im Shop":
        "1 purchase in the shop",
    "Stammkunde":
        "Regular Customer",
    "50 Käufe im Shop":
        "50 purchases in the shop",
    "Vollausstattung":
        "Fully Equipped",
    "Alle 5 Helfer bei einer Pflanze besitzen":
        "Own all 5 helpers on one plant",
    "Grosseinkauf":
        "Big Spender",
    "500 Käufe im Shop":
        "500 purchases in the shop",
    "Grosszügig":
        "Generous",
    "100'000 Gold im Shop ausgeben":
        "Spend 100'000 Gold in the shop",
    "Erste Gäste":
        "First Guests",
    "50 Besuche im Garten":
        "50 visits to the garden",
    "Offene Tür":
        "Open Door",
    "250 Besuche im Garten":
        "250 visits to the garden",
    "Gastgeber":
        "Host",
    "1'000 Besuche im Garten":
        "1'000 visits to the garden",
    "Beliebtes Plätzchen":
        "Popular Spot",
    "5'000 Besuche im Garten":
        "5'000 visits to the garden",
    "Gartenparadies":
        "Garden Paradise",
    "25'000 Besuche im Garten":
        "25'000 visits to the garden",
    "Erste Begegnung":
        "First Encounter",
    "1 Besucherart entdecken":
        "Discover 1 visitor species",
    "Zwei Bekannte":
        "Two Acquaintances",
    "2 Besucherarten entdecken":
        "Discover 2 visitor species",
    "Dreiklang":
        "Triad",
    "3 Besucherarten entdecken":
        "Discover 3 visitor species",
    "Vierblatt":
        "Four-Leaf Clover",
    "4 Besucherarten entdecken":
        "Discover 4 visitor species",
    "Naturfreund":
        "Nature Lover",
    "5 Besucherarten entdecken":
        "Discover 5 visitor species",
    "Sechserpack":
        "Six-Pack",
    "6 Besucherarten entdecken":
        "Discover 6 visitor species",
    "Fast komplett":
        "Almost Complete",
    "7 Besucherarten entdecken":
        "Discover 7 visitor species",
    "Vollständiges Buch":
        "Complete Book",
    "Alle 8 Besucherarten entdecken":
        "Discover all 8 visitor species",
    "Erster Stammgast":
        "First Regular",
    "1 Besucher wird Stammgast":
        "1 becomes a Regular",
    "Zwei Stammgäste":
        "Two Regulars",
    "2 sind Stammgäste":
        "2 are Regulars",
    "Runder Tisch":
        "Round Table",
    "3 sind Stammgäste":
        "3 are Regulars",
    "Stammtisch":
        "Regulars' Table",
    "4 sind Stammgäste":
        "4 are Regulars",
    "Fünf Freunde":
        "Five Friends",
    "5 sind Stammgäste":
        "5 are Regulars",
    "Halbes Dutzend":
        "Half a Dozen",
    "6 sind Stammgäste":
        "6 are Regulars",
    "Fast alle da":
        "Almost Everyone",
    "7 sind Stammgäste":
        "7 are Regulars",
    "Volles Haus":
        "Full House",
    "Alle 8 sind Stammgäste":
        "All 8 are Regulars",
    "1 Besucher wird Gartenbewohner":
        "1 becomes a Garden Resident",
    "Zweiter Mieter":
        "Second Tenant",
    "2 sind Gartenbewohner":
        "2 are Garden Residents",
    "Dreier-WG":
        "Shared Flat of Three",
    "3 sind Gartenbewohner":
        "3 are Garden Residents",
    "Kleine Siedlung":
        "Small Settlement",
    "4 sind Gartenbewohner":
        "4 are Garden Residents",
    "Nachbarschaft":
        "Neighbourhood",
    "5 sind Gartenbewohner":
        "5 are Garden Residents",
    "Dorfgemeinschaft":
        "Village Community",
    "6 sind Gartenbewohner":
        "6 are Garden Residents",
    "Fast vollzählig":
        "Nearly Full",
    "7 sind Gartenbewohner":
        "7 are Garden Residents",
    "Zu Hause":
        "At Home",
    "Alle 8 sind Gartenbewohner":
        "All 8 are Garden Residents",
    "Farbenfroh":
        "Colourful",
    "1 Farbvariante entdecken":
        "Discover 1 colour variant",
    "Bunte Mischung":
        "Colourful Mix",
    "2 Farbvarianten entdecken":
        "Discover 2 colour variants",
    "Farbtupfer":
        "Splash of Colour",
    "3 Farbvarianten entdecken":
        "Discover 3 colour variants",
    "Glückskind":
        "Lucky Child",
    "4 Farbvarianten entdecken":
        "Discover 4 colour variants",
    "Farbenmeer":
        "Sea of Colour",
    "5 Farbvarianten entdecken":
        "Discover 5 colour variants",
    "Malkasten":
        "Paint Box",
    "6 Farbvarianten entdecken":
        "Discover 6 colour variants",
    "Kunterbunt":
        "Kaleidoscope",
    "7 Farbvarianten entdecken":
        "Discover 7 colour variants",
    "Regenbogen":
        "Rainbow",
    "Alle 8 Farbvarianten entdecken":
        "Discover all 8 colour variants",
    "Konzentriert":
        "Concentrated",
    "10 Fokus-Sitzungen":
        "10 focus sessions",
    "Zen-Gärtner":
        "Zen Gardener",
    "Eine 60-Minuten-Sitzung":
        "One 60-minute session",
    "Ruhepol":
        "Calm Centre",
    "50 Fokus-Sitzungen":
        "50 focus sessions",
    "Meister der Stille":
        "Master of Silence",
    "200 Fokus-Sitzungen":
        "200 focus sessions",
    "Fels in der Brandung":
        "Rock in the Surf",
    "1'000 Fokus-Sitzungen":
        "1'000 focus sessions",
    "Erste Tage":
        "First Days",
    "3 Tage in Folge gespielt":
        "Played 3 days in a row",
    "Treue Seele":
        "Loyal Soul",
    "7 Tage in Folge gespielt":
        "Played 7 days in a row",
    "Gartenfreund":
        "Garden Friend",
    "30 Tage in Folge gespielt":
        "Played 30 days in a row",
    "Unermüdlich":
        "Tireless",
    "100 Tage in Folge gespielt":
        "Played 100 days in a row",
    "Ein Jahr im Garten":
        "A Year in the Garden",
    "365 Tage in Folge gespielt":
        "Played 365 days in a row",
    "Braucht wenig Wasser.":
        "Needs little water.",
    "Wächst nur durch Mausklicks.":
        "Grows only through mouse clicks.",
    "Braucht viel Wasser.":
        "Needs a lot of water.",
    "Wächst nur gut bei 30–80 % Wasser.":
        "Only grows well at 30–80 % water.",
    "Kügelchen":
        "Little ball",
    "Säule":
        "Column",
    "Grosser Kaktus":
        "Large cactus",
    "Zwiebel":
        "Bulb",
    "Austrieb":
        "Shoot",
    "Blätter":
        "Leaves",
    "Stängel":
        "Stem",
    "Grosse Tulpe":
        "Large tulip",
    "Steckling":
        "Cutting",
    "Trieb":
        "Sprout",
    "Jungbaum":
        "Young tree",
    "Bäumchen":
        "Little tree",
    "Knospen":
        "Buds",
    "Kirschblüte":
        "Cherry blossom",
    "Karte löschen":
        "Delete card",
    "Die Karte «{v}» vom {archived_at} endgültig aus dem Gartenhaus löschen?":
        "Delete the card «{v}» from {archived_at} from the Garden Shed for good?",
    "Einlagern & neu aussäen":
        "Store & resow",
    "Ehrenhalle · {n} Pflanze":
        "Hall of Fame · {n} plant",
    "Ehrenhalle · {n} Pflanzen":
        "Hall of Fame · {n} plants",
    "Noch leer.\n\nBlühende Pflanzen kommen beim Neu-Aussäen mit Datum und Uhrzeit hierher.":
        "Nothing here yet.\n\nPlants in bloom end up here with date and time when you resow.",
    "{v} blüht: Prestige-Stufe {lvl} → {lvl2}, kommt ins Gartenhaus und wird neu ausgesät.":
        "{v} is in bloom: prestige level {lvl} → {lvl2}, goes into the Garden Shed and is resown.",
    "{v} ({growth}) kommt nur ins Gartenhaus, ohne Prestige-Stufe. Danach wird neu ausgesät.":
        "{v} ({growth}) only goes into the Garden Shed, without a prestige level. It is resown afterwards.",
    "Karte löschen (mit Rückfrage).":
        "Delete card (with confirmation).",
    "Mausrad zum Blättern. Zeiger auf eine Karte zeigt Details, × oben links löscht sie.":
        "Mouse wheel to scroll. Hover over a card for details, × at the top left deletes it.",
    "%H:%M Uhr":
        "%H:%M",
    "{v} ({growth}): gepflanzt {created}, Blüte {bloomed_at}, ins Gartenhaus {archived_at}. Wachstum {growth2:.0f}, {clicks_total} Klicks":
        "{v} ({growth}): planted {created}, bloom {bloomed_at}, in the Garden Shed {archived_at}. Growth {growth2:.0f}, {clicks_total} clicks",
    ", {keys_total} Tasten.":
        ", {keys_total} keys.",
    "Prestige-Stufe {prestige} · ":
        "Prestige level {prestige} · ",
    "Bedienung":
        "Controls",
    "Pflanzen":
        "Plants",
    "Regeln":
        "Rules",
    "Version":
        "Version",
    "nicht verfügbar":
        "not available",
    "Dünger (wirkt auf die gewählte Pflanze)":
        "Fertilizer (affects the selected plant)",
    "Zeit läuft nur, solange die Pflanze gewählt ist und das Spiel läuft. Nochmal kaufen verlängert.":
        "Time only runs while the plant is selected and the game is running. Buying again extends it.",
    "Helfer (pro Pflanze einmal kaufen, einzeln schaltbar)":
        "Helpers (buy once per plant, switch individually)",
    "System: {system} {release}":
        "System: {system} {release}",
    "Tastaturzählung: {src}":
        "Keyboard counting: {src}",
    "Spielstand: {config}":
        "Save file: {config}",
    "Quellcode und Downloads: github.com/donsimm/topfpflanze-v1":
        "Source code and downloads: github.com/donsimm/topfpflanze-v1",
    "Release Notes":
        "Release Notes",
    "Spielregeln und Werte":
        "Rules and values",
    "Maus":
        "Mouse",
    "Linksklick: giessen und wachsen lassen. Ist das Wasser voll, gibt der Klick nur Wachstum.":
        "Left click: water and make it grow. If the water is full, the click only gives growth.",
    "Linke Taste ziehen: Fenster verschieben. Mittelklick: Sprechblase ein/aus. Rechtsklick: Menü.":
        "Drag with the left button: move the window. Middle click: bubble on/off. Right click: menu.",
    "Tastatur":
        "Keyboard",
    "Tastendrücke lassen die Pflanze wachsen und verbrauchen etwas Wasser. Gezählt wird nur die Anzahl, nie welche Taste.":
        "Key presses make the plant grow and use a little water. Only the count is recorded, never which key.",
    "Symbole der Sprechblase":
        "Bubble icons",
    "Oben: Pflanze wählen (jede hat einen eigenen Spielstand, nicht gewählte pausieren).":
        "Top: select a plant (each has its own save; unselected plants pause).",
    "Unten: Shop, Gartenhaus, Erfolge, Fokus-Timer, Besucher-Sammelbuch, Tagebuch, Info.":
        "Bottom: Shop, Garden Shed, Achievements, Focus Timer, Visitor Book, Diary, Info.",
    "Einstellungen":
        "Settings",
    "Rechtsklick → Einstellungen: Tastatur zählen, Sprache (Deutsch / English / Français / Italiano, startet das Spiel neu), Dunkelmodus, Vordergrund, Pflanzen- und Menügrösse, Lautstärke (0–100 %, Standard 0 = stumm). Töne: Giessen beim Bewässern und ein Gong am Ende des Fokus-Timers.":
        "Right click → Settings: count keys, language (Deutsch / English / Français / Italiano, restarts the game), dark mode, always on top, plant and menu size, volume (0–100 %, default 0 = muted). Sounds: watering when you water and a gong at the end of the focus timer.",
    "Basiswerte bei gutem Wasserstand, ohne Boni.":
        "Base values at a good water level, without bonuses.",
    "Taste +{growth_per_key}":
        "Key +{growth_per_key}",
    "Tasten zählen nicht":
        "Keys do not count",
    "Pro Klick/Taste = Basiswert × Wasserfaktor × Boni. Wasserfaktor: unter «voll» linear weniger, bei 0 % kein Wachstum, über dem Maximum nur ×0.3 (Staunässe).":
        "Per click/key = base value × water factor × bonuses. Water factor: below «full» linearly less, at 0 % no growth, above the maximum only ×0.3 (waterlogging).",
    "Boni werden multipliziert: Dünger, Prestige (+{pct} je Stufe), Lampe (+{pct2}), Fokus (×{v}).":
        "Bonuses are multiplied: fertilizer, prestige (+{pct} per level), lamp (+{pct2}), focus (×{v}).",
    "Stadien (Anteil vom Blütewert: {fr} %): {stages}.":
        "Stages (share of the bloom value: {fr} %): {stages}.",
    "Sinkt laufend, auch bei ausgeschaltetem PC. Nicht gewählte Pflanzen pausieren. Unter der Welkgrenze welkt die Pflanze sichtbar.":
        "Keeps falling, even when the PC is off. Unselected plants pause. Below the wilting threshold the plant visibly wilts.",
    "Stufen 1–6: {coins} Gold × Faktor der Pflanze.":
        "Stages 1–6: {coins} Gold × plant factor.",
    "Nach der Blüte je +{pct} des Blütewerts: {v} Gold × Faktor. Passiv {v2} Gold pro Stunde.":
        "After blooming, for every +{pct} of the bloom value: {v} Gold × factor. Passive {v2} Gold per hour.",
    "Blühende Pflanze einlagern: Stufe der Art +1 (dauerhaft +{pct} Wachstum und Gold). Nicht ausgewachsene kommen nur ins Gartenhaus. Bereit ist die Pflanze, sobald sie blüht: eine sanfte goldene Aura leuchtet dann hinter ihr.":
        "Store a blooming plant: species level +1 (permanent +{pct} growth and Gold). Plants that are not fully grown only go into the Garden Shed. A plant is ready as soon as it blooms: a soft golden aura then glows behind it.",
    "Beim Einlagern wählst du den Topf der neuen Pflanze: der Originaltopf ist gratis, dazu gibt es ein günstiges ({cheap}–{cheap2} Gold) und ein edles ({premium}–{premium2} Gold) Design aus dem Sortiment deiner Pflanze. Das Angebot wechselt nach jeder Aussaat; der Topf ist nur Zierde und bleibt bei der Pflanze.":
        "When storing, you choose the pot of the new plant: the original pot is free, plus an affordable ({cheap}–{cheap2} Gold) and a premium ({premium}–{premium2} Gold) design from your plant's range. The offer changes after every sowing; the pot is purely decorative and stays with the plant.",
    "{m} min mit ×{v} Wachstum. Belohnung: Minuten ÷ 5 Gold. Abbruch kostet nur den Bonus.":
        "{m} min with ×{v} growth. Reward: minutes ÷ 5 Gold. Cancelling only costs the bonus.",
    "Fokusmodus (Schalter im Fokus-Fenster, Standard an): Beim Start schliessen sich alle anderen Fenster, nur die Pflanze und die Zeit mit Ring bleiben. Nach Ablauf oder Abbruch (Rechtsklick → «Fokus abbrechen») kommen die vorher offenen Fenster zurück.":
        "Focus mode (switch in the focus window, on by default): when it starts, all other windows close and only the plant and the time with the ring stay. After it ends or is cancelled (right click → «Cancel focus») the previously open windows return.",
    "3 täglich, 3 wöchentlich, {v} einmalige in {a} Reihen (Tasten, Klicks, Shop, Besuche, Fokus u. a.): Im Fenster erscheint je Reihe die nächste Stufe. Belohnung einzeln oder gesammelt abholen; Nicht Abgeholtes bleibt in der Liste.":
        "3 daily, 3 weekly, {v} one-time ones in {a} series (keys, clicks, shop, visits, focus and more): the window shows the next tier of each series. Collect rewards one by one or all at once; anything not collected stays in the list.",
    "Jede Minute Chance 10 % (+5 % ab halber Grösse, +10 % bei Blüte). Klick: +{coins} Gold. {list}.":
        "Every minute a 10 % chance (+5 % from half size, +10 % in bloom). Click: +{coins} Gold. {list}.",
    "Meisterschaft: nach {steps} Besuchen die Stufen {names} (Setzling mit 1–3 Blättern im Sammelbuch). Belohnung {coins} Gold, bei seltenen ×{rare}, bei sehr seltenen ×{very_rare}. Jeder Gartenbewohner: +{pct} Wachstum.":
        "Mastery: after {steps} visits the levels {names} (seedling with 1–3 leaves in the visitor book). Reward {coins} Gold, ×{rare} for rare, ×{very_rare} for very rare. Every Garden Resident: +{pct} growth.",
    "Farbvarianten (Stern im Sammelbuch, Name in Gold): Chance je Besuch {chances} (häufig / selten / sehr selten). Klick: +{coins} Gold.":
        "Colour variants (star in the visitor book, name in gold): chance per visit {chances} (common / rare / very rare). Click: +{coins} Gold.",
    "Name":
        "Name",
    "Preis":
        "Price",
    "Dauer":
        "Duration",
    "{price} Gold":
        "{price} Gold",
    "Debug-Modus aktiv (eigener Spielstand).":
        "Debug mode active (separate save).",
    "Blüte bei {bloom_at} · Klick +{growth_per_click} · {keyg}":
        "Bloom at {bloom_at} · Click +{growth_per_click} · {keyg}",
    "Wächst voll bei {water_low}–{water_high} % · welkt unter {wilt_below} % · Gold ×{coin_mult}":
        "Fully grows at {water_low}–{water_high} % · wilts below {wilt_below} % · Gold ×{coin_mult}",
    "Wasser: leer nach {drain_hours} h · Klick +{water_per_click} %":
        "Water: empty after {drain_hours} h · Click +{water_per_click} %",
    " · Taste −{water_per_key} %":
        " · Key −{water_per_key} %",
    "Meisterschaft (Besucher)":
        "Mastery (visitors)",
    "Täglich, {pid}.{pid2}.":
        "Daily, {pid}.{pid2}.",
    "Wöchentlich, KW {split}":
        "Weekly, week {split}",
    "Abholen":
        "Collect",
    "{done_n} von {v} erreicht":
        "{done_n} of {v} reached",
    "Alle abholen  +{v}":
        "Collect all  +{v}",
    "Fokus läuft: noch {m:02d}:{sec:02d}\nRechtsklick: Menü, Fokus abbrechen":
        "Focus running: {m:02d}:{sec:02d} left\nRight click: menu, cancel focus",
    "Fokusmodus\nBeim Start werden alle anderen Fenster ausgeblendet, nur Pflanze und Zeit bleiben. Nach dem Ablauf kommen sie zurück.":
        "Focus mode\nWhen it starts, all other windows are hidden and only the plant and the time remain. They return after it ends.",
    "Wachstum ×{v:g} während der Sitzung":
        "Growth ×{v:g} during the session",
    "Fokusmodus":
        "Focus mode",
    "Heute: {focus} Sitzung(en) · {focus_min} min":
        "Today: {focus} session(s) · {focus_min} min",
    "{book} von {v} entdeckt":
        "{book} of {v} discovered",
    "Täglich":
        "Daily",
    "neu in {secs_day}":
        "new in {secs_day}",
    "Wöchentlich":
        "Weekly",
    "neu in {secs_week}":
        "new in {secs_week}",
    "Allgemein":
        "General",
    "einmalig":
        "one-time",
    "Nicht abgeholt":
        "Not collected",
    "bereit zum Abholen":
        "ready to collect",
    "nichts abzuholen":
        "nothing to collect",
    "Fokus abbrechen\nKein Bonus für diese Sitzung.":
        "Cancel focus\nNo bonus for this session.",
    "{m} min":
        "{m} min",
    "läuft":
        "running",
    "Abbrechen":
        "Cancel",
    "Fokus starten":
        "Start focus",
    "an":
        "on",
    "aus":
        "off",
    "Noch nicht entdeckt. Hinweis: {hint}":
        "Not discovered yet. Hint: {hint}",
    "abgeholt":
        "collected",
    "… und {more} weitere (Knopf unten holt alle)":
        "… and {more} more (the button below collects all)",
    "bereit":
        "ready",
    "unbekannt":
        "unknown",
    "{count}× · seit {first}":
        "{count}× · since {first}",
    "Noch keine Stufe":
        "No level yet",
    "  noch {count} bis {tier}":
        "  {count} more to {tier}",
    "  Höchste Stufe, +{v:g} %":
        "  Highest level, +{v:g} %",
    "  {n_var}× gesehen":
        "  {n_var}× seen",
    "  offen":
        "  open",
    "{count}× gesehen":
        "{count}× seen",
    "Ein Klick auf einen Besucher bringt {v} Gold.":
        "Clicking a visitor gives {v} Gold.",
    "Setzling":
        "Seedling",
    "  Stufe nach {steps} Besuchen":
        "  Level after {steps} visits",
    "Stern":
        "Star",
    "  Farbvariante gesehen":
        "  Colour variant seen",
    "{v} · {growth}\nWachstum {growth2:.0f} · Wasser {water:.0f} %":
        "{v} · {growth}\nGrowth {growth2:.0f} · Water {water:.0f} %",
    "{done} von {v} erreicht":
        "{done} of {v} reached",
    "läuft, noch {m:02d}:{sec:02d}":
        "running, {m:02d}:{sec:02d} left",
    "Pflanzengrösse":
        "Plant size",
    "Stufe {lvl} · +{lvl2:.0f} %":
        "Level {lvl} · +{lvl2:.0f} %",
    "{hp} gekauft und aktiv.":
        "{hp} bought and active.",
    "Fokus: {minutes} min":
        "Focus: {minutes} min",
    "abgebrochen, kein Bonus":
        "cancelled, no bonus",
    "+{coins} Hallo, {v}!":
        "+{coins} Hello, {v}!",
    "{fz} verlängert: wirkt noch {left} auf {v}.":
        "{fz} extended: works for {left} more on {v}.",
    "{fz} wirkt jetzt auf {v}":
        "{fz} now works on {v}",
    "Lautstärke":
        "Volume",
    "Pflanze wählen":
        "Select plant",
    "Fenster":
        "Windows",
    "Status-Sprechblase (Mittelklick)":
        "Status bubble (middle click)",
    "Tastaturanschläge zählen":
        "Count key presses",
    "Dunkelmodus":
        "Dark mode",
    "Immer im Vordergrund":
        "Always on top",
    "Status anzeigen":
        "Show status",
    "«{v}» einlagern & neu aussäen …":
        "Store «{v}» & resow …",
    "Beenden":
        "Quit",
    "zählen bei dieser Pflanze nicht":
        "do not count for this plant",
    "+{v} Erfolge":
        "+{v} Achievements",
    "{hp} ist wieder eingeschaltet.":
        "{hp} is switched on again.",
    "{hp} ist ausgeschaltet.":
        "{hp} is switched off.",
    "Zu wenig Gold für {hp}: es fehlen {coins}.":
        "Not enough Gold for {hp}: {coins} missing.",
    "geschafft! +{reward} Gold":
        "done! +{reward} Gold",
    "+{reward} Fokus geschafft":
        "+{reward} Focus done",
    "Zu wenig Gold für {fz}: es fehlen {coins}.":
        "Not enough Gold for {fz}: {coins} missing.",
    " (ersetzt {cur}).":
        " (replaces {cur}).",
    "Tastaturanschläge zählen (nicht verfügbar)":
        "Count key presses (not available)",
    "Menügrösse":
        "Menu size",
    "Fokus abbrechen":
        "Cancel focus",
    "Stadium: {growth}\nWachstum: {growth2:.1f} (Blüte ab {bloom_at})\nWasser: {water:.0f} % (leer nach ca. {drain_hours:g} h)\nKlicks gesamt: {clicks_total}\nTastendrücke gesamt: {v}\nDünger: {fert_summary}\nPrestige: {prestige_summary}\nHelfer: {v2}\nAlter: {days:.1f} Tage\nGold: {coins}\nTastaturquelle: {src}\nSpeicherort: {config}":
        "Stage: {growth}\nGrowth: {growth2:.1f} (bloom from {bloom_at})\nWater: {water:.0f} % (empty after approx. {drain_hours:g} h)\nTotal clicks: {clicks_total}\nTotal key presses: {v}\nFertilizer: {fert_summary}\nPrestige: {prestige_summary}\nHelpers: {v2}\nAge: {days:.1f} days\nGold: {coins}\nKeyboard source: {src}\nSave location: {config}",
    "Originaltopf":
        "Original pot",
    "Neuer Topf: {choice}":
        "New pot: {choice}",
    "Speichern fehlgeschlagen: {v}":
        "Saving failed: {v}",
    "Erfolg: {a}":
        "Achievement: {a}",
    "Hummel: Wachstum!":
        "Bumblebee: growth!",
    "Neu: {key}!":
        "New: {key}!",
    "Neu: {v}!":
        "New: {v}!",
    "Pflanze: {v} (Schwierigkeit: {difficulty})\n":
        "Plant: {v} (difficulty: {difficulty})\n",
    "Automat: {last}":
        "Dispenser: {last}",
    "Hinweis: {note}\n":
        "Note: {note}\n",
    "Sand, breites Band":
        "Sand, wide band",
    "Salbei, grosse Punkte":
        "Sage, large dots",
    "Tauchglasur Salbei":
        "Dipped glaze sage",
    "Gesprenkelt Creme":
        "Speckled cream",
    "Salbei, grosse Rauten":
        "Sage, large diamonds",
    "Anthrazit, Goldlinien":
        "Anthracite, gold lines",
    "Elfenbein, Goldrand":
        "Ivory, gold rim",
    "Kintsugi Schwarz":
        "Kintsugi black",
    "Kintsugi Weiss":
        "Kintsugi white",
    "Lehm, breite Streifen":
        "Clay, wide stripes",
    "Sprenkel Sand":
        "Speckled sand",
    "Terrazzo hell":
        "Terrazzo light",
    "Schwarz, Kupferband":
        "Black, copper band",
    "Schwarz, Goldrand":
        "Black, gold rim",
    "Waldgrün, Goldlinien":
        "Forest green, gold lines",
    "Marmor weiss":
        "White marble",
    "Kintsugi Stein":
        "Kintsugi stone",
    "Creme, Salbeiband":
        "Cream, sage band",
    "Tauchglasur Rosé":
        "Dipped glaze rosé",
    "Sprenkel Weiss":
        "Speckled white",
    "Terrazzo Rosé":
        "Terrazzo rosé",
    "Weiss, Goldring":
        "White, gold ring",
    "Nachtblau, Goldlinien":
        "Midnight blue, gold lines",
    "Weiss, Gold-Zickzack":
        "White, gold zigzag",
    "Kintsugi Nachtblau":
        "Kintsugi midnight blue",
    "Sprenkel Grau":
        "Speckled grey",
    "Messing gebürstet":
        "Brushed brass",
    "Kupfer gehämmert":
        "Hammered copper",
    "Gold getaucht":
        "Dipped gold",
    "Gold gehämmert":
        "Hammered gold",
    "Weisse Keramik":
        "White ceramic",
    "Schliessen":
        "Close",
    "für: {v}":
        "for: {v}",
    "Helfer":
        "Helpers",
    "Klick schaltet ein oder aus.":
        "Click to switch on or off.",
    "Klick kauft den Helfer.":
        "Click to buy the helper.",
    "Helfer gelten nur für die ausgewählte Pflanze. Pro Pflanze einmal kaufen, dauerhaft nutzen.":
        "Helpers only apply to the selected plant. Buy once per plant, use forever.",
    "aktiv":
        "active",
    "ausgeschaltet":
        "switched off",
    "Aktiv: {fert_summary}":
        "Active: {fert_summary}",
    "Dünger anklicken, um ihn für die ausgewählte Pflanze zu kaufen. Passives Einkommen: {v} Gold pro Stunde.":
        "Click a fertilizer to buy it for the selected plant. Passive income: {v} Gold per hour.",
    "Gratis":
        "Free",
    "Günstig":
        "Affordable",
    "Edel":
        "Premium",
    "«{v}» ist noch nicht ausgewachsen":
        "«{v}» is not fully grown yet",
    "Stadium: {growth}. Sie kommt nur ins Gartenhaus, ohne Prestige-Stufe.":
        "Stage: {growth}. It only goes into the Garden Shed, without a prestige level.",
    "Topf für die neue Pflanze":
        "Pot for the new plant",
    "Gewählt: {sel}":
        "Selected: {sel}",
    " · es fehlen {coins}":
        " · {coins} missing",
    "Dein Gold: {coins}{note}":
        "Your Gold: {coins}{note}",
    "«{v}» ist ausgewachsen":
        "«{v}» is fully grown",
    "Prestige-Stufe {lvl} → {lvl2}: dauerhaft +{lvl3:.0f} % Wachstum und Gold für alle künftigen {v}. Die Pflanze kommt ins Gartenhaus.":
        "Prestige level {lvl} → {lvl2}: permanent +{lvl3:.0f} % growth and Gold for all future {v}. The plant goes into the Garden Shed.",
    "{seconds} min":
        "{seconds} min",
    "{fz}: Wachstum +{boost:.0f} % für {minutes}":
        "{fz}: growth +{boost:.0f} % for {minutes}",
    "{h} h {m} min":
        "{h} h {m} min",
    ", Wasserverbrauch +{water:.0f} %.":
        ", water use +{water:.0f} %.",
    ", kein Mehrverbrauch an Wasser.":
        ", no extra water use.",
    "gut":
        "good",
    "zu trocken":
        "too dry",
    "zu nass":
        "too wet",
    "knapp":
        "low",
    "{d} T {h} h":
        "{d} d {h} h",
    "%d.%m.%Y":
        "%Y-%m-%d",
    "%d.%m.%Y %H:%M":
        "%Y-%m-%d %H:%M",
    "schwer":
        "heavy",
    "müde":
        "tired",
    "ruhig":
        "calm",
    "glücklich":
        "happy",
    "Schreibe hier deine Gedanken …":
        "Write your thoughts here …",
    "Tagebuch":
        "Diary",
    "{n} Zeichen":
        "{n} characters",
    "Stimmung":
        "Mood",
    "✓ automatisch gespeichert":
        "✓ saved automatically",
    "Keine Einträge in diesem Monat":
        "No entries this month",
    "1 Eintrag in diesem Monat":
        "1 entry this month",
    "{n} Einträge in diesem Monat":
        "{n} entries this month",
    "Vorheriger Monat":
        "Previous month",
    "Nächster Monat":
        "Next month",
    "grüner Punkt = Eintrag,\ndunkler = mehr Text":
        "green dot = entry,\ndarker = more text",
    "Heute":
        "Today",
    "Tagebuch schliessen":
        "Close diary",
    "Tagebuch öffnen":
        "Open diary",
    "\n{n} Einträge":
        "\n{n} entries",
    "Unveröffentlicht":
        "Unreleased",
    "Das Tagebuch-Symbol öffnet den Kalender und das Textfenster des heutigen Tags. Der Text wird von selbst gespeichert, dazu eine von fünf Stimmungs-Herzen (nochmal klicken: entfernen). Ein Klick auf einen Tag im Kalender öffnet dessen Eintrag; grüner Punkt = Eintrag, dunkler = mehr Text. Die Einträge liegen in der Datei diary.json im Spielstand-Ordner. Im Fokusmodus bleibt ein offenes Textfenster sichtbar. Die Rechtschreibung wird mit Hunspell geprüft (rote Wellenlinie, Rechtsklick zeigt Vorschläge, eigene Wörter landen in diary_words.txt); die Sprache lässt sich unter dem Papier wählen.":
        "The diary icon opens the calendar and the text window of today. The text is saved automatically, along with one of five mood hearts (click again to remove). Clicking a day in the calendar opens its entry; green dot = entry, darker = more text. The entries are stored in the file diary.json in the save folder. In focus mode an open text window stays visible. Spelling is checked with Hunspell (red wavy underline, right click shows suggestions, your own words go into diary_words.txt); the language can be chosen below the paper.",
    "Tagebuch: neues Symbol im Menü mit Kalender (Wärmekarte, grüner Punkt bei Tagen mit Eintrag) und eigenem Textfenster. Der Text wird von selbst gespeichert, dazu fünf Stimmungs-Herzen. Das Textfenster bleibt im Fokusmodus sichtbar. Mit Rechtschreibprüfung (Hunspell, offline).":
        "Diary: a new icon in the menu with a calendar (heat map, green dot on days with an entry) and its own text window. The text is saved automatically, with five mood hearts. The text window stays visible in focus mode. With spell checking (Hunspell, offline).",
    "Rechtschreibung: aus":
        "Spelling: off",
    "Rechtschreibung: {lang}":
        "Spelling: {lang}",
    "Rechtschreibung: {lang} (lädt …)":
        "Spelling: {lang} (loading …)",
    "Rechtschreibung: nicht verfügbar":
        "Spelling: not available",
    "Automatisch (Sprache des Spiels)":
        "Automatic (game language)",
    "Aus":
        "Off",
    "Zum Wörterbuch hinzufügen":
        "Add to dictionary",
    "Ignorieren":
        "Ignore",
    "Keine Vorschläge":
        "No suggestions",
    "Rückgängig":
        "Undo",
    "Wiederholen":
        "Redo",
    "Ausschneiden":
        "Cut",
    "Kopieren":
        "Copy",
    "Einfügen":
        "Paste",
    "Alles auswählen":
        "Select all",
    "Rechtschreibprüfung nicht verfügbar:\n{error}":
        "Spell checking not available:\n{error}",
    "Klicken: Sprache der Rechtschreibung wählen":
        "Click to choose the spelling language",
    "neutral":
        "neutral",
    "Klicken: Kalender ein-/ausblenden":
        "Click to show/hide the calendar",
    "Spieldaten":
        "Game data",
    "Exportieren …":
        "Export …",
    "Importieren …":
        "Import …",
    "Spieldaten exportieren":
        "Export game data",
    "Spieldaten importieren":
        "Import game data",
    "Sicherung (*.zip)":
        "Backup (*.zip)",
    "Spieldaten exportiert":
        "Game data exported",
    "Gespeichert in:\n{path}":
        "Saved to:\n{path}",
    "Export fehlgeschlagen":
        "Export failed",
    "Import nicht möglich":
        "Import not possible",
    "Import fehlgeschlagen":
        "Import failed",
    "OK":
        "OK",
    "Importieren":
        "Import",
    "Spieldaten importieren?":
        "Import game data?",
    "Der jetzige Spielstand und alle Tagebucheinträge werden durch die Sicherung vom {date} ersetzt ({entries} Tagebucheinträge). Der jetzige Stand wird vorher im Ordner «backups» gesichert. Das Spiel startet danach neu.":
        "The current game and all diary entries will be replaced by the backup from {date} ({entries} diary entries). The current state is backed up first in the folder «backups». The game restarts afterwards.",
    "Das ist keine gültige Sicherung von Topfpflanze.":
        "This is not a valid Topfpflanze backup.",
    "Die Sicherung ist beschädigt oder zu gross.":
        "The backup is damaged or too large.",
    "Die Sicherung stammt von einer neueren Version ({version}). Bitte zuerst das Spiel aktualisieren.":
        "The backup comes from a newer version ({version}). Please update the game first.",
    "Rechtsklick → Spieldaten → Exportieren speichert Spielstand, Tagebuch und eigene Wörter in einer ZIP-Datei (das Tagebuch zusätzlich als lesbare Textdatei). Importieren ersetzt den jetzigen Stand durch eine Sicherung; vorher wird der jetzige Stand im Ordner backups gesichert, danach startet das Spiel neu. Fensterpositionen werden nicht übernommen.":
        "Right click → Game data → Export saves the game, the diary and your own words in a ZIP file (the diary also as a readable text file). Import replaces the current state with a backup; the current state is first saved in the folder backups, then the game restarts. Window positions are not imported.",
    "Spieldaten exportieren und importieren (Rechtsklick → Spieldaten): Spielstand, Tagebuch und eigene Wörter in einer ZIP-Datei; vor einem Import wird der jetzige Stand gesichert.":
        "Export and import game data (right click → Game data): game, diary and your own words in one ZIP file; the current state is backed up before an import.",
    "Spieldaten sichern":
        "Backing up game data",
    "Datenordner öffnen":
        "Open data folder",
    "Programmordner öffnen":
        "Open program folder",
    "Alle Spieldaten zurücksetzen …":
        "Reset all game data …",
    "Alle Spieldaten zurücksetzen?":
        "Reset all game data?",
    "Zurücksetzen":
        "Reset",
    "Zurücksetzen fehlgeschlagen":
        "Reset failed",
    "Ordner nicht gefunden":
        "Folder not found",
    "Der Ordner konnte nicht geöffnet werden:\n{path}":
        "The folder could not be opened:\n{path}",
    "Alle Pflanzen, das Gold, die Erfolge und alle Tagebucheinträge werden gelöscht, und das Spiel beginnt von vorn. Der jetzige Stand wird vorher im Ordner «backups» gesichert; über «Importieren» lässt er sich zurückholen. Das Spiel startet danach neu.":
        "All plants, the Gold, the achievements and all diary entries will be deleted, and the game starts from scratch. The current state is backed up first in the folder «backups»; you can bring it back with «Import». The game restarts afterwards.",
    "Spieldaten → Datenordner öffnen zeigt den Ordner mit Spielstand, Tagebuch und Sicherungen, Programmordner öffnen den Ordner des Programms. Alle Spieldaten zurücksetzen löscht alles und beginnt von vorn (vorher wird der jetzige Stand in backups gesichert).":
        "Game data → Open data folder shows the folder with the save, the diary and the backups; Open program folder shows the folder of the program. Reset all game data deletes everything and starts from scratch (the current state is first backed up in backups).",
    "Spieldaten: Ordner mit Spielstand und Programm direkt öffnen und alle Spieldaten zurücksetzen (mit Rückfrage und vorheriger Sicherung).":
        "Game data: open the folders with the save and the program directly, and reset all game data (with confirmation and a backup first).",
}
