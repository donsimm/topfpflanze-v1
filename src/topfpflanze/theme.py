"""Farbschemata (hell/dunkel) der Fenster."""

from PyQt6.QtGui import QColor



# Farben der Fenster Sprechblase, Shop und Gartenhaus (hell / dunkel)
THEMES = {
    "light": {
        "panel": (255, 255, 255, 232), "panel_border": (90, 90, 90, 200), "sep": (0, 0, 0, 40),
        "text": "#1E1E1E", "text2": "#555555", "text3": "#333333", "muted": "#777777",
        "cell": "#F7F7F4", "cell_border": "#C8C8C2", "active_bg": "#E6F4E6", "active_bg_hover": "#D9F0DC",
        "hover_bg": "#EEF7EE", "gold_bg": "#FFF6DA", "ok": "#2E7D32", "coin": "#9A6B00", "bad": "#C0392B",
        "bad_bg": "#FDECEA", "button_text": "#1E5E2A", "btn_bg": "#F4F4F0", "btn_bg_hover": "#EDEDE8",
        "btn_border": "#BDBDB6", "scroll": (0, 0, 0, 60), "white": "#FFFFFF",
    },
    "dark": {
        "panel": (36, 38, 42, 238), "panel_border": (150, 150, 150, 200), "sep": (255, 255, 255, 45),
        "text": "#E8E8E8", "text2": "#B4B4B4", "text3": "#D2D2D2", "muted": "#9A9A9A",
        "cell": "#2E3135", "cell_border": "#4A4E54", "active_bg": "#1F3A25", "active_bg_hover": "#28492F",
        "hover_bg": "#263A2B", "gold_bg": "#3D3420", "ok": "#72D183", "coin": "#E6B84A", "bad": "#FF7A6B",
        "bad_bg": "#4A2522", "button_text": "#A6E8B0", "btn_bg": "#33363A", "btn_bg_hover": "#3C4045",
        "btn_border": "#5A5F66", "scroll": (255, 255, 255, 70), "white": "#2E3135",
    },
}
_THEME = {"dark": False}


def T(key):
    """Farbe des aktuellen Farbschemas (Dunkelmodus ein/aus)."""
    v = THEMES["dark" if _THEME["dark"] else "light"][key]
    return QColor(*v) if isinstance(v, tuple) else QColor(v)
