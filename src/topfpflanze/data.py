"""Spieldaten: Pflanzenarten, Dünger, Helfer, Besucher, Erfolge, Topfgeometrie."""

from dataclasses import dataclass

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
    stages: tuple = ("Samen", "Keimling", "Jungpflanze", "Pflanze",
                     "Grosse Pflanze", "Knospe", "Blühend")
    note: str = ""
    coin_mult: float = 1.0   # Faktor für Gold-Belohnungen
    colors: tuple = ("#E85D75", "#C44DD8", "#F2A541", "#5D8CE8", "#F25C54")  # alte Farbberechnung
    palette: tuple = ("#E85D75", "#C44DD8", "#F2A541", "#5D8CE8", "#F25C54", "#F7F3E8",
                      "#FFD23F", "#FF8FB1", "#7B2CBF", "#E63946", "#2EC4B6")  # neue Pflanzen


STAGE_FRACTIONS = (0.0, SEED_FRAC, 0.0375, 0.15, 0.5, 0.75, 1.0)

PLANT_TYPES = {
    "wiesenblume": PlantType(
        "wiesenblume", "Wiesenblume", "Mittel", "terrakotta",
        bloom_at=800, growth_per_click=0.4, growth_per_key=0.02,
        water_per_click=6.0, water_per_key=0.005, drain_hours=12),
    "kaktus": PlantType(
        "kaktus", "Kaktus", "Leicht", "beton",
        bloom_at=400, growth_per_click=0.3, growth_per_key=0.025,
        water_per_click=10.0, water_per_key=0.002, drain_hours=48,
        water_low=10, wilt_below=5,
        stages=("Samen", "Keimling", "Kügelchen", "Säule", "Grosser Kaktus", "Knospe", "Blühend"),
        note="Braucht wenig Wasser.", coin_mult=0.5,
        colors=("#FF6FA8", "#FF8C42", "#F2D14C", "#E84C6A"),
        palette=("#FF6FA8", "#FF8C42", "#F2D14C", "#E84C6A", "#FFFFFF", "#B5179E", "#FF4D00", "#FFB5C2")),
    "tulpe": PlantType(
        "tulpe", "Tulpe", "Mittel, nur Klicks", "keramik",
        bloom_at=500, growth_per_click=1.0, growth_per_key=0.0,
        water_per_click=0.8, water_per_key=0.0, drain_hours=8,
        stages=("Zwiebel", "Austrieb", "Blätter", "Stängel", "Grosse Tulpe", "Knospe", "Blühend"),
        note="Wächst nur durch Mausklicks.",
        colors=("#E8333A", "#F6C431", "#F07AA8", "#8E44AD", "#F58A32", "#F5F1E6"),
        palette=("#E8333A", "#F6C431", "#F07AA8", "#8E44AD", "#F58A32", "#F5F1E6",
                 "#3B1F4A", "#FF9EBB", "#C9184A", "#FDF0A6")),
    "sonnenblume": PlantType(
        "sonnenblume", "Sonnenblume", "Schwer", "zink",
        bloom_at=2000, growth_per_click=0.4, growth_per_key=0.02,
        water_per_click=5.0, water_per_key=0.008, drain_hours=6,
        water_low=30, wilt_below=20,
        note="Braucht viel Wasser.", coin_mult=2.0,
        colors=("#F5C518",),
        palette=("#F5C518", "#F2A516", "#FFE36E", "#D35400", "#8E2C1E", "#FFF3B0")),
    "bonsai": PlantType(
        "bonsai", "Bonsai", "Sehr schwer", "schale",
        bloom_at=4000, growth_per_click=0.3, growth_per_key=0.015,
        water_per_click=4.0, water_per_key=0.004, drain_hours=8,
        water_low=30, water_high=80, wilt_below=20,
        stages=("Steckling", "Trieb", "Jungbaum", "Bäumchen", "Bonsai", "Knospen", "Kirschblüte"),
        note="Wächst nur gut bei 30–80 % Wasser.", coin_mult=3.0,
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
    "kompost": Fertilizer("kompost", "Kompost", 20, 0.15, 0.0, 120, "heap", "#6B4A2E", "#5FA84F"),
    "fluessig": Fertilizer("fluessig", "Flüssigdünger", 40, 0.30, 0.20, 60, "bottle", "#3E9E5A", "#2E7D46"),
    "hornspaene": Fertilizer("hornspaene", "Hornspäne", 70, 0.25, 0.0, 360, "bag", "#C9B28A", "#8A7456"),
    "blaukorn": Fertilizer("blaukorn", "Blaukorn", 90, 0.50, 0.50, 120, "bag", "#3B6BB5", "#7FA8E8"),
    "turbo": Fertilizer("turbo", "Turbo-Booster", 120, 1.00, 1.00, 30, "bottle", "#D64541", "#F5C518"),
    "wundermix": Fertilizer("wundermix", "Wundermix", 200, 0.75, 0.25, 180, "jar", "#8E44AD", "#F5C518"),
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
    "tropf": Helper("tropf", "Tropfbewässerung", 250,
                    "Hält den Wasserstand automatisch bei mindestens 40 %."),
    "hummel": Helper("hummel", "Hummel", 300,
                     "Kommt etwa alle 10 Minuten vorbei und bringt einen Wachstumsschub."),
    "zwerg": Helper("zwerg", "Gartenzwerg", 400,
                    "Hilft alle 30 Sekunden mit: bringt Wachstum wie ein Mausklick."),
    "lampe": Helper("lampe", "Pflanzenlampe", 600,
                    "Dauerhaft +10 % Wachstum für alle Pflanzen."),
    "automat": Helper("automat", "Düngerautomat", 500,
                      "Kauft den zuletzt verwendeten Dünger automatisch nach, sobald er ausläuft."),
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
FOCUS_PRESETS = (25, 45, 60)


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
    "marienkaefer": Visitor("marienkaefer", "Marienkäfer", "häufig", 50, "crawl", "",
                            "Krabbelt gern auf Blättern herum."),
    "kohlweissling": Visitor("kohlweissling", "Kohlweissling", "häufig", 50, "fly", "",
                             "Flattert bei jeder Pflanze vorbei."),
    "biene": Visitor("biene", "Honigbiene", "häufig", 40, "fly", "bloom",
                     "Kommt nur zu blühenden Pflanzen."),
    "zitronenfalter": Visitor("zitronenfalter", "Zitronenfalter", "selten", 20, "fly", "",
                              "Ein seltener Gast, Geduld lohnt sich."),
    "libelle": Visitor("libelle", "Libelle", "selten", 18, "fly", "big",
                       "Zeigt sich erst bei grösseren Pflanzen."),
    "tagpfauenauge": Visitor("tagpfauenauge", "Tagpfauenauge", "selten", 15, "fly", "bloom",
                             "Liebt Blüten."),
    "rotkehlchen": Visitor("rotkehlchen", "Rotkehlchen", "sehr selten", 6, "sit", "big",
                           "Setzt sich manchmal auf den Topfrand grosser Pflanzen."),
    "gluehwuermchen": Visitor("gluehwuermchen", "Glühwürmchen", "sehr selten", 8, "glow", "night",
                              "Nur abends und nachts (20–6 Uhr) zu sehen."),
}
VISITOR_ORDER = ["marienkaefer", "kohlweissling", "biene", "zitronenfalter",
                 "libelle", "tagpfauenauge", "rotkehlchen", "gluehwuermchen"]
VISIT_DURATION = 30.0
VISIT_GREET_COINS = 3

# Meisterschaft (Biodiversität): Stufen je Besucher nach Anzahl Besuche (Varianten zählen mit);
# im Sammelbuch als Setzling mit 1, 2 oder 3 Blättern
MASTERY_STEPS = (10, 50, 200)
MASTERY_NAMES = ("Besucher", "Stammgast", "Gartenbewohner")
MASTERY_COINS = (20, 60, 150)                          # Belohnung je Stufe, mal Seltenheitsfaktor
RARITY_MULT = {"häufig": 1.0, "selten": 1.5, "sehr selten": 2.0}
MASTERY_TOP_BONUS = 0.01                              # je Gartenbewohner: +1 % Wachstum (dauerhaft)

# Farbvarianten («Schillernde»): Chance je Besuch nach Seltenheit, Belohnung beim Begrüssen
SHINY_CHANCE = {"häufig": 0.05, "selten": 0.08, "sehr selten": 0.12}
SHINY_GREET_COINS = 15


@dataclass(frozen=True)
class Variant:
    name: str
    colors: tuple    # Paare (Originalfarbe, Variantenfarbe) als Hex
    glow: tuple = ()  # optional: (r, g, b) für leuchtende Besucher


VARIANTS = {
    "marienkaefer": Variant("Goldener Marienkäfer", (("#D62828", "#F2C230"),)),
    "kohlweissling": Variant("Blauer Kohlweissling", (("#F4F4EE", "#BFD9FF"), ("#EDEDE4", "#A9C7F5"))),
    "biene": Variant("Blaue Biene", (("#F2C230", "#4FA3E0"),)),
    "zitronenfalter": Variant("Rosa Zitronenfalter", (("#F3E24A", "#F49AC2"), ("#EFD93C", "#EE86B4"))),
    "libelle": Variant("Rote Libelle", (("#2E86C1", "#D64541"),)),
    "tagpfauenauge": Variant("Violettes Tagpfauenauge", (("#B5311F", "#7B4FC4"), ("#8E2718", "#5B3A9E"))),
    "rotkehlchen": Variant("Weisses Rotkehlchen", (("#7A6650", "#F0ECE0"), ("#E4572E", "#F4C9B8"))),
    "gluehwuermchen": Variant("Blaues Glühwürmchen", (), (140, 200, 255)),
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


ACHIEVEMENTS = [
    Achievement("d_keys", "daily", "Fleissige Finger", "2'000 Tasten heute", 2000, 15),
    Achievement("d_clicks", "daily", "Giesskanne", "20-mal klicken heute", 20, 10),
    Achievement("d_focus", "daily", "Fokussiert", "1 Fokus-Sitzung heute", 1, 20),
    Achievement("w_keys", "weekly", "Tastenmarathon", "20'000 Tasten diese Woche", 20000, 60),
    Achievement("w_growth", "weekly", "Wachstumsschub", "300 Wachstum diese Woche", 300, 60),
    Achievement("w_focus", "weekly", "Fokus-Woche", "5 Fokus-Sitzungen diese Woche", 5, 80),
    Achievement("g_bloom", "general", "Erste Blüte", "Eine Pflanze blühen lassen", 1, 50),
    Achievement("g_garden", "general", "Sammler", "5 Pflanzen im Gartenhaus", 5, 75),
    Achievement("g_prestige", "general", "Aufstieg", "Erste Prestige-Stufe erreichen", 1, 100),
    Achievement("g_species", "general", "Artenvielfalt", "Alle 5 Arten blühen lassen", 5, 200),
    Achievement("g_keys", "general", "Tastenmeister", "100'000 Tasten insgesamt", 100000, 150),
    Achievement("g_visitors", "general", "Naturfreund", "5 Besucherarten entdecken", 5, 100),
]

# Topfgeometrie: Höhe der Erdoberfläche, Erd-Ellipse, Wassertropfen (Mittelpunkt des Bauchs, Radius)
POTS = {
    "terrakotta": {"soil_y": 234, "soil_rx": 60, "soil_ry": 6.0, "drop_y": 292, "drop_r": 9.0},
    "beton":      {"soil_y": 248, "soil_rx": 44, "soil_ry": 4.5, "drop_y": 298, "drop_r": 8.5},
    "keramik":    {"soil_y": 244, "soil_rx": 40, "soil_ry": 4.5, "drop_y": 290, "drop_r": 7.5},
    "zink":       {"soil_y": 238, "soil_rx": 56, "soil_ry": 5.0, "drop_y": 288, "drop_r": 8.5},
    "schale":     {"soil_y": 290, "soil_rx": 78, "soil_ry": 3.5, "drop_y": 306, "drop_r": 5.0},
}
