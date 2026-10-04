"""Spieldaten: Pflanzenarten, Dünger, Helfer, Besucher, Erfolge, Topfgeometrie."""

from dataclasses import dataclass

from .i18n import tr
from .config import SEED_FRAC


# ---------------------------------------------------------------- Pflanzenarten

@dataclass(frozen=True)
class PlantType:
    key: str
    name: str
    difficulty: str
    pot: str
    bloom_at: float          # Wachstumspunkte bis zur Blüte
    growth_per_click: float
    growth_per_key: float    # 0 = Tastatur zählt nicht
    water_per_click: float
    water_per_key: float
    drain_hours: float       # Zeit von 100 % auf 0 % Wasser
    water_low: float = 20.0  # darunter reduziertes Wachstum
    water_high: float = 100.0  # darüber reduziertes Wachstum (Staunässe)
    wilt_below: float = 15.0
    stages: tuple = (tr("Samen"), tr("Keimling"), tr("Jungpflanze"), tr("Pflanze"),
                     tr("Grosse Pflanze"), tr("Knospe"), tr("Blühend"))
    note: str = ""
    coin_mult: float = 1.0   # Faktor für Gold-Belohnungen
    colors: tuple = ("#E85D75", "#C44DD8", "#F2A541", "#5D8CE8", "#F25C54")  # alte Farbberechnung
    palette: tuple = ("#E85D75", "#C44DD8", "#F2A541", "#5D8CE8", "#F25C54", "#F7F3E8",
                      "#FFD23F", "#FF8FB1", "#7B2CBF", "#E63946", "#2EC4B6")  # neue Pflanzen


STAGE_FRACTIONS = (0.0, SEED_FRAC, 0.0375, 0.15, 0.5, 0.75, 1.0)

PLANT_TYPES = {
    "wiesenblume": PlantType(
        "wiesenblume", tr("Wiesenblume"), tr("Mittel"), "terrakotta",
        bloom_at=800, growth_per_click=0.4, growth_per_key=0.02,
        water_per_click=6.0, water_per_key=0.005, drain_hours=12),
    "kaktus": PlantType(
        "kaktus", tr("Kaktus"), tr("Leicht"), "beton",
        bloom_at=400, growth_per_click=0.3, growth_per_key=0.025,
        water_per_click=10.0, water_per_key=0.002, drain_hours=48,
        water_low=10, wilt_below=5,
        stages=(tr("Samen"), tr("Keimling"), tr("Kügelchen"), tr("Säule"), tr("Grosser Kaktus"), tr("Knospe"), tr("Blühend")),
        note=tr("Braucht wenig Wasser."), coin_mult=0.5,
        colors=("#FF6FA8", "#FF8C42", "#F2D14C", "#E84C6A"),
        palette=("#FF6FA8", "#FF8C42", "#F2D14C", "#E84C6A", "#FFFFFF", "#B5179E", "#FF4D00", "#FFB5C2")),
    "tulpe": PlantType(
        "tulpe", tr("Tulpe"), tr("Mittel, nur Klicks"), "keramik",
        bloom_at=500, growth_per_click=1.0, growth_per_key=0.0,
        water_per_click=0.8, water_per_key=0.0, drain_hours=8,
        stages=(tr("Zwiebel"), tr("Austrieb"), tr("Blätter"), tr("Stängel"), tr("Grosse Tulpe"), tr("Knospe"), tr("Blühend")),
        note=tr("Wächst nur durch Mausklicks."),
        colors=("#E8333A", "#F6C431", "#F07AA8", "#8E44AD", "#F58A32", "#F5F1E6"),
        palette=("#E8333A", "#F6C431", "#F07AA8", "#8E44AD", "#F58A32", "#F5F1E6",
                 "#3B1F4A", "#FF9EBB", "#C9184A", "#FDF0A6")),
    "sonnenblume": PlantType(
        "sonnenblume", tr("Sonnenblume"), tr("Schwer"), "zink",
        bloom_at=2000, growth_per_click=0.4, growth_per_key=0.02,
        water_per_click=5.0, water_per_key=0.008, drain_hours=6,
        water_low=30, wilt_below=20,
        note=tr("Braucht viel Wasser."), coin_mult=2.0,
        colors=("#F5C518",),
        palette=("#F5C518", "#F2A516", "#FFE36E", "#D35400", "#8E2C1E", "#FFF3B0")),
    "bonsai": PlantType(
        "bonsai", tr("Bonsai"), tr("Sehr schwer"), "schale",
        bloom_at=4000, growth_per_click=0.3, growth_per_key=0.015,
        water_per_click=4.0, water_per_key=0.004, drain_hours=8,
        water_low=30, water_high=80, wilt_below=20,
        stages=(tr("Steckling"), tr("Trieb"), tr("Jungbaum"), tr("Bäumchen"), tr("Bonsai"), tr("Knospen"), tr("Kirschblüte")),
        note=tr("Wächst nur gut bei 30–80 % Wasser."), coin_mult=3.0,
        colors=("#F7B7C8",),
        palette=("#F7B7C8", "#FFFFFF", "#F48FB1", "#E75480", "#FCE4EC")),
}
PLANT_ORDER = ["wiesenblume", "kaktus", "tulpe", "sonnenblume", "bonsai"]


@dataclass(frozen=True)
class Fertilizer:
    key: str
    name: str
    price: int
    boost: float      # zusätzliches Wachstum, 0.5 = +50 %
    water: float      # zusätzlicher Wasserverbrauch, 0.5 = +50 %
    minutes: int      # Wirkungsdauer
    icon: str         # heap, bottle, bag, jar
    color: str
    accent: str


FERTILIZERS = {
    "kompost": Fertilizer("kompost", tr("Kompost"), 20, 0.15, 0.0, 120, "heap", "#6B4A2E", "#5FA84F"),
    "fluessig": Fertilizer("fluessig", tr("Flüssigdünger"), 40, 0.30, 0.20, 60, "bottle", "#3E9E5A", "#2E7D46"),
    "hornspaene": Fertilizer("hornspaene", tr("Hornspäne"), 70, 0.25, 0.0, 360, "bag", "#C9B28A", "#8A7456"),
    "blaukorn": Fertilizer("blaukorn", tr("Blaukorn"), 90, 0.50, 0.50, 120, "bag", "#3B6BB5", "#7FA8E8"),
    "turbo": Fertilizer("turbo", tr("Turbo-Booster"), 120, 1.00, 1.00, 30, "bottle", "#D64541", "#F5C518"),
    "wundermix": Fertilizer("wundermix", tr("Wundermix"), 200, 0.75, 0.25, 180, "jar", "#8E44AD", "#F5C518"),
}
FERT_ORDER = ["kompost", "fluessig", "hornspaene", "blaukorn", "turbo", "wundermix"]


# ---------------------------------------------------------------- Helfer (Automatisierung)

@dataclass(frozen=True)
class Helper:
    key: str
    name: str
    price: int
    desc: str


HELPERS = {
    "tropf": Helper("tropf", tr("Tropfbewässerung"), 250,
                    tr("Hält den Wasserstand automatisch bei mindestens 40 %.")),
    "hummel": Helper("hummel", tr("Hummel"), 300,
                     tr("Kommt etwa alle 10 Minuten vorbei und bringt einen Wachstumsschub.")),
    "zwerg": Helper("zwerg", tr("Gartenzwerg"), 400,
                    tr("Hilft alle 30 Sekunden mit: bringt Wachstum wie ein Mausklick.")),
    "lampe": Helper("lampe", tr("Pflanzenlampe"), 600,
                    tr("Dauerhaft +10 % Wachstum für diese Pflanze.")),
    "automat": Helper("automat", tr("Düngerautomat"), 500,
                      tr("Kauft den zuletzt verwendeten Dünger automatisch nach, sobald er ausläuft.")),
}
HELPER_ORDER = ["tropf", "hummel", "zwerg", "lampe", "automat"]
DRIP_MIN = 40.0               # Tropfbewässerung: Mindest-Wasserstand
DRIP_RATE = 20.0 / 60         # ... füllt 20 % pro Minute nach
BEE_INTERVAL = (480, 720)     # Hummel: alle 8–12 Minuten
BEE_BOOST = 0.005             # ... Anteil des Blütewerts
GNOME_INTERVAL = 30.0         # Gartenzwerg: alle 30 Sekunden
LAMP_BOOST = 0.10             # Pflanzenlampe: +10 %
PRESTIGE_BONUS = 0.10         # je Prestige-Stufe: +10 % Wachstum und Gold
FOCUS_MULT = 2.0              # Fokus-Timer: doppeltes Wachstum
FOCUS_PRESETS = (10, 25, 45, 60)
FOCUS_DEFAULT = 25


# ---------------------------------------------------------------- Besucher (Sammelbuch)

@dataclass(frozen=True)
class Visitor:
    key: str
    name: str
    rarity: str
    weight: int
    move: str        # fly, crawl, sit, glow
    cond: str        # "", bloom, big, night
    hint: str


VISITORS = {
    "marienkaefer": Visitor("marienkaefer", tr("Marienkäfer"), "häufig", 50, "crawl", "",
                            tr("Krabbelt gern auf Blättern herum.")),
    "kohlweissling": Visitor("kohlweissling", tr("Kohlweissling"), "häufig", 50, "fly", "",
                             tr("Flattert bei jeder Pflanze vorbei.")),
    "biene": Visitor("biene", tr("Honigbiene"), "häufig", 40, "fly", "bloom",
                     tr("Kommt nur zu blühenden Pflanzen.")),
    "zitronenfalter": Visitor("zitronenfalter", tr("Zitronenfalter"), "selten", 20, "fly", "",
                              tr("Ein seltener Gast, Geduld lohnt sich.")),
    "libelle": Visitor("libelle", tr("Libelle"), "selten", 18, "fly", "big",
                       tr("Zeigt sich erst bei grösseren Pflanzen.")),
    "tagpfauenauge": Visitor("tagpfauenauge", tr("Tagpfauenauge"), "selten", 15, "fly", "bloom",
                             tr("Liebt Blüten.")),
    "rotkehlchen": Visitor("rotkehlchen", tr("Rotkehlchen"), "sehr selten", 6, "sit", "big",
                           tr("Setzt sich manchmal auf den Topfrand grosser Pflanzen.")),
    "gluehwuermchen": Visitor("gluehwuermchen", tr("Glühwürmchen"), "sehr selten", 8, "glow", "night",
                              tr("Nur abends und nachts (20–6 Uhr) zu sehen.")),
}
VISITOR_ORDER = ["marienkaefer", "kohlweissling", "biene", "zitronenfalter",
                 "libelle", "tagpfauenauge", "rotkehlchen", "gluehwuermchen"]
VISIT_DURATION = 30.0
VISIT_GREET_COINS = 3

# Meisterschaft (Biodiversität): Stufen je Besucher nach Anzahl Besuche (Varianten zählen mit);
# im Sammelbuch als Setzling mit 1, 2 oder 3 Blättern
MASTERY_STEPS = (10, 50, 200)
MASTERY_NAMES = (tr("Besucher"), tr("Stammgast"), tr("Gartenbewohner"))
MASTERY_COINS = (20, 60, 150)                          # Belohnung je Stufe, mal Seltenheitsfaktor
RARITY_MULT = {"häufig": 1.0, "selten": 1.5, "sehr selten": 2.0}
RARITY_LABEL = {"häufig": tr("häufig"), "selten": tr("selten"), "sehr selten": tr("sehr selten")}   # Anzeigetexte
MASTERY_TOP_BONUS = 0.01                              # je Gartenbewohner: +1 % Wachstum (dauerhaft)

# Seltene Farbvarianten: Chance je Besuch nach Seltenheit, Belohnung beim Begrüssen
SHINY_CHANCE = {"häufig": 0.05, "selten": 0.08, "sehr selten": 0.12}
SHINY_GREET_COINS = 15


@dataclass(frozen=True)
class Variant:
    name: str
    colors: tuple    # Paare (Originalfarbe, Variantenfarbe) als Hex
    glow: tuple = ()  # optional: (r, g, b) für leuchtende Besucher


VARIANTS = {
    "marienkaefer": Variant(tr("Goldener Marienkäfer"), (("#D62828", "#F2C230"),)),
    "kohlweissling": Variant(tr("Blauer Kohlweissling"), (("#F4F4EE", "#BFD9FF"), ("#EDEDE4", "#A9C7F5"))),
    "biene": Variant(tr("Blaue Biene"), (("#F2C230", "#4FA3E0"),)),
    "zitronenfalter": Variant(tr("Rosa Zitronenfalter"), (("#F3E24A", "#F49AC2"), ("#EFD93C", "#EE86B4"))),
    "libelle": Variant(tr("Rote Libelle"), (("#2E86C1", "#D64541"),)),
    "tagpfauenauge": Variant(tr("Violettes Tagpfauenauge"), (("#B5311F", "#7B4FC4"), ("#8E2718", "#5B3A9E"))),
    "rotkehlchen": Variant(tr("Weisses Rotkehlchen"), (("#7A6650", "#F0ECE0"), ("#E4572E", "#F4C9B8"))),
    "gluehwuermchen": Variant(tr("Blaues Glühwürmchen"), (), (140, 200, 255)),
}


# ---------------------------------------------------------------- Erfolge

@dataclass(frozen=True)
class Achievement:
    key: str
    period: str      # daily, weekly, general
    name: str
    desc: str
    target: int
    reward: int
    series: str = ""   # nur allgemeine Erfolge: Reihe mit mehreren Stufen, ein Eintrag im Fenster


ACHIEVEMENTS = [
    Achievement("d_keys", "daily", tr("Fleissige Finger"), tr("2'000 Tasten heute"), 2000, 15),
    Achievement("d_clicks", "daily", tr("Giesskanne"), tr("20-mal klicken heute"), 20, 10),
    Achievement("d_focus", "daily", tr("Fokussiert"), tr("1 Fokus-Sitzung heute"), 1, 20),
    Achievement("w_keys", "weekly", tr("Tastenmarathon"), tr("20'000 Tasten diese Woche"), 20000, 60),
    Achievement("w_growth", "weekly", tr("Wachstumsschub"), tr("300 Wachstum diese Woche"), 300, 60),
    Achievement("w_focus", "weekly", tr("Fokus-Woche"), tr("5 Fokus-Sitzungen diese Woche"), 5, 80),
    # Allgemein: einmalig, in Reihen (Stufen) zusammengefasst; das Fenster zeigt je Reihe die nächste Stufe
    Achievement("g_bloom", "general", tr("Erste Blüte"), tr("1 Art blühen lassen"), 1, 50, "blueten"),
    Achievement("g_bloom2", "general", tr("Zweite Art"), tr("2 Arten blühen lassen"), 2, 75, "blueten"),
    Achievement("g_bloom3", "general", tr("Dreierstrauss"), tr("3 Arten blühen lassen"), 3, 100, "blueten"),
    Achievement("g_bloom4", "general", tr("Blumenbeet"), tr("4 Arten blühen lassen"), 4, 150, "blueten"),
    Achievement("g_species", "general", tr("Artenvielfalt"), tr("Alle 5 Arten blühen lassen"), 5, 200, "blueten"),
    Achievement("g_garden", "general", tr("Sammler"), tr("5 Pflanzen im Gartenhaus"), 5, 75, "garten"),
    Achievement("g_garden15", "general", tr("Gartenhaus-Besitzer"), tr("15 Pflanzen im Gartenhaus"), 15, 150, "garten"),
    Achievement("g_garden50", "general", tr("Gartenbaumeister"), tr("50 Pflanzen im Gartenhaus"), 50, 400, "garten"),
    Achievement("g_garden150", "general", tr("Gartenkönig"), tr("150 Pflanzen im Gartenhaus"), 150, 800, "garten"),
    Achievement("g_garden500", "general", tr("Gärtnerei"), tr("500 Pflanzen im Gartenhaus"), 500, 1500, "garten"),
    Achievement("g_prestige", "general", tr("Aufstieg"), tr("Erste Prestige-Stufe erreichen"), 1, 100, "prestige"),
    Achievement("g_prestige5", "general", tr("Aufsteiger"), tr("5 Prestige-Stufen insgesamt"), 5, 200, "prestige"),
    Achievement("g_prestige15", "general", tr("Veteran"), tr("15 Prestige-Stufen insgesamt"), 15, 400, "prestige"),
    Achievement("g_prestige50", "general", tr("Grossmeister"), tr("50 Prestige-Stufen insgesamt"), 50, 1000, "prestige"),
    Achievement("g_prestige150", "general", tr("Legende"), tr("150 Prestige-Stufen insgesamt"), 150, 2000, "prestige"),
    Achievement("g_keys1", "general", tr("Tipper"), tr("1'000 Tasten insgesamt"), 1000, 20, "tasten"),
    Achievement("g_keys10", "general", tr("Vieltipper"), tr("10'000 Tasten insgesamt"), 10000, 50, "tasten"),
    Achievement("g_keys", "general", tr("Tastenmeister"), tr("100'000 Tasten insgesamt"), 100000, 150, "tasten"),
    Achievement("g_keys500", "general", tr("Tastenheld"), tr("500'000 Tasten insgesamt"), 500000, 300, "tasten"),
    Achievement("g_keys1m", "general", tr("Tastenlegende"), tr("1'000'000 Tasten insgesamt"), 1000000, 500, "tasten"),
    Achievement("g_clicks100", "general", tr("Giesskännchen"), tr("100-mal klicken insgesamt"), 100, 20, "klicks"),
    Achievement("g_clicks1k", "general", tr("Wasserträger"), tr("1'000-mal klicken insgesamt"), 1000, 60, "klicks"),
    Achievement("g_clicks10k", "general", tr("Platzregen"), tr("10'000-mal klicken insgesamt"), 10000, 150, "klicks"),
    Achievement("g_clicks100k", "general", tr("Regenmacher"), tr("100'000-mal klicken insgesamt"), 100000, 400, "klicks"),
    Achievement("g_clicks1m", "general", tr("Sintflut"), tr("1'000'000-mal klicken insgesamt"), 1000000, 1000, "klicks"),
    Achievement("g_shop1", "general", tr("Erster Einkauf"), tr("1 Kauf im Shop"), 1, 25, "shop"),
    Achievement("g_shop50", "general", tr("Stammkunde"), tr("50 Käufe im Shop"), 50, 75, "shop"),
    Achievement("g_helpers", "general", tr("Vollausstattung"), tr("Alle 5 Helfer bei einer Pflanze besitzen"), 5, 150, "shop"),
    Achievement("g_shop500", "general", tr("Grosseinkauf"), tr("500 Käufe im Shop"), 500, 300, "shop"),
    Achievement("g_spent", "general", tr("Grosszügig"), tr("100'000 Gold im Shop ausgeben"), 100000, 600, "shop"),
    Achievement("g_vis50", "general", tr("Erste Gäste"), tr("50 Besuche im Garten"), 50, 30, "besuche"),
    Achievement("g_vis250", "general", tr("Offene Tür"), tr("250 Besuche im Garten"), 250, 75, "besuche"),
    Achievement("g_vis1k", "general", tr("Gastgeber"), tr("1'000 Besuche im Garten"), 1000, 150, "besuche"),
    Achievement("g_vis5k", "general", tr("Beliebtes Plätzchen"), tr("5'000 Besuche im Garten"), 5000, 300, "besuche"),
    Achievement("g_vis25k", "general", tr("Gartenparadies"), tr("25'000 Besuche im Garten"), 25000, 800, "besuche"),
    Achievement("g_disc1", "general", tr("Erste Begegnung"), tr("1 Besucherart entdecken"), 1, 30, "entdecker"),
    Achievement("g_disc2", "general", tr("Zwei Bekannte"), tr("2 Besucherarten entdecken"), 2, 40, "entdecker"),
    Achievement("g_disc3", "general", tr("Dreiklang"), tr("3 Besucherarten entdecken"), 3, 50, "entdecker"),
    Achievement("g_disc4", "general", tr("Vierblatt"), tr("4 Besucherarten entdecken"), 4, 60, "entdecker"),
    Achievement("g_disc5", "general", tr("Naturfreund"), tr("5 Besucherarten entdecken"), 5, 100, "entdecker"),
    Achievement("g_disc6", "general", tr("Sechserpack"), tr("6 Besucherarten entdecken"), 6, 120, "entdecker"),
    Achievement("g_disc7", "general", tr("Fast komplett"), tr("7 Besucherarten entdecken"), 7, 150, "entdecker"),
    Achievement("g_disc8", "general", tr("Vollständiges Buch"), tr("Alle 8 Besucherarten entdecken"), 8, 200, "entdecker"),
    Achievement("g_reg1", "general", tr("Erster Stammgast"), tr("1 Besucher wird Stammgast"), 1, 60, "stammgaeste"),
    Achievement("g_reg2", "general", tr("Zwei Stammgäste"), tr("2 sind Stammgäste"), 2, 80, "stammgaeste"),
    Achievement("g_reg3", "general", tr("Runder Tisch"), tr("3 sind Stammgäste"), 3, 100, "stammgaeste"),
    Achievement("g_reg4", "general", tr("Stammtisch"), tr("4 sind Stammgäste"), 4, 120, "stammgaeste"),
    Achievement("g_reg5", "general", tr("Fünf Freunde"), tr("5 sind Stammgäste"), 5, 150, "stammgaeste"),
    Achievement("g_reg6", "general", tr("Halbes Dutzend"), tr("6 sind Stammgäste"), 6, 200, "stammgaeste"),
    Achievement("g_reg7", "general", tr("Fast alle da"), tr("7 sind Stammgäste"), 7, 250, "stammgaeste"),
    Achievement("g_reg8", "general", tr("Volles Haus"), tr("Alle 8 sind Stammgäste"), 8, 400, "stammgaeste"),
    Achievement("g_master1", "general", tr("Gartenbewohner"), tr("1 Besucher wird Gartenbewohner"), 1, 100, "meister"),
    Achievement("g_master2", "general", tr("Zweiter Mieter"), tr("2 sind Gartenbewohner"), 2, 150, "meister"),
    Achievement("g_master3", "general", tr("Dreier-WG"), tr("3 sind Gartenbewohner"), 3, 200, "meister"),
    Achievement("g_master4", "general", tr("Kleine Siedlung"), tr("4 sind Gartenbewohner"), 4, 250, "meister"),
    Achievement("g_master5", "general", tr("Nachbarschaft"), tr("5 sind Gartenbewohner"), 5, 300, "meister"),
    Achievement("g_master6", "general", tr("Dorfgemeinschaft"), tr("6 sind Gartenbewohner"), 6, 500, "meister"),
    Achievement("g_master7", "general", tr("Fast vollzählig"), tr("7 sind Gartenbewohner"), 7, 600, "meister"),
    Achievement("g_master8", "general", tr("Zu Hause"), tr("Alle 8 sind Gartenbewohner"), 8, 1000, "meister"),
    Achievement("g_variant1", "general", tr("Farbenfroh"), tr("1 Farbvariante entdecken"), 1, 100, "farben"),
    Achievement("g_variant2", "general", tr("Bunte Mischung"), tr("2 Farbvarianten entdecken"), 2, 120, "farben"),
    Achievement("g_variant3", "general", tr("Farbtupfer"), tr("3 Farbvarianten entdecken"), 3, 150, "farben"),
    Achievement("g_variant4", "general", tr("Glückskind"), tr("4 Farbvarianten entdecken"), 4, 200, "farben"),
    Achievement("g_variant5", "general", tr("Farbenmeer"), tr("5 Farbvarianten entdecken"), 5, 250, "farben"),
    Achievement("g_variant6", "general", tr("Malkasten"), tr("6 Farbvarianten entdecken"), 6, 300, "farben"),
    Achievement("g_variant7", "general", tr("Kunterbunt"), tr("7 Farbvarianten entdecken"), 7, 400, "farben"),
    Achievement("g_variant8", "general", tr("Regenbogen"), tr("Alle 8 Farbvarianten entdecken"), 8, 600, "farben"),
    Achievement("g_focus10", "general", tr("Konzentriert"), tr("10 Fokus-Sitzungen"), 10, 60, "fokus"),
    Achievement("g_zen", "general", tr("Zen-Gärtner"), tr("Eine 60-Minuten-Sitzung"), 60, 100, "fokus"),
    Achievement("g_focus50", "general", tr("Ruhepol"), tr("50 Fokus-Sitzungen"), 50, 200, "fokus"),
    Achievement("g_focus200", "general", tr("Meister der Stille"), tr("200 Fokus-Sitzungen"), 200, 400, "fokus"),
    Achievement("g_focus1k", "general", tr("Fels in der Brandung"), tr("1'000 Fokus-Sitzungen"), 1000, 1000, "fokus"),
    Achievement("g_streak3", "general", tr("Erste Tage"), tr("3 Tage in Folge gespielt"), 3, 40, "treue"),
    Achievement("g_streak7", "general", tr("Treue Seele"), tr("7 Tage in Folge gespielt"), 7, 100, "treue"),
    Achievement("g_streak30", "general", tr("Gartenfreund"), tr("30 Tage in Folge gespielt"), 30, 300, "treue"),
    Achievement("g_streak100", "general", tr("Unermüdlich"), tr("100 Tage in Folge gespielt"), 100, 600, "treue"),
    Achievement("g_streak365", "general", tr("Ein Jahr im Garten"), tr("365 Tage in Folge gespielt"), 365, 1500, "treue"),
]

# Topfgeometrie: Höhe der Erdoberfläche, Erd-Ellipse, Wassertropfen (Mittelpunkt des Bauchs, Radius)
POTS = {
    "terrakotta": {"soil_y": 234, "soil_rx": 60, "soil_ry": 6.0, "drop_y": 292, "drop_r": 9.0},
    "beton":      {"soil_y": 248, "soil_rx": 44, "soil_ry": 4.5, "drop_y": 298, "drop_r": 8.5},
    "keramik":    {"soil_y": 244, "soil_rx": 40, "soil_ry": 4.5, "drop_y": 290, "drop_r": 7.5},
    "zink":       {"soil_y": 238, "soil_rx": 56, "soil_ry": 5.0, "drop_y": 288, "drop_r": 8.5},
    "schale":     {"soil_y": 290, "soil_rx": 78, "soil_ry": 3.5, "drop_y": 306, "drop_r": 5.0},
}

# Namen der Werkzeug-Fenster (Reihenfolge: config.TOOL_ORDER)
TOOL_NAMES = {"shop": tr("Shop"), "garden": tr("Gartenhaus"), "ach": tr("Erfolge"), "focus": tr("Fokus-Timer"),
              "book": tr("Besucher-Sammelbuch"), "diary": tr("Tagebuch"), "info": tr("Info")}
