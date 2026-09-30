"""Info-Fenster: Bedienung, Pflanzenwerte, Spielregeln und Shop in Kurzform (Werte aus den Spieldaten)."""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QPen

from .config import MILESTONE_COINS, MILESTONE_STEP, PASSIVE_PER_HOUR, STAGE_COINS
from .data import (FERTILIZERS, FERT_ORDER, FOCUS_MULT, FOCUS_PRESETS, HELPER_ORDER, HELPERS, LAMP_BOOST,
                   PLANT_ORDER, PLANT_TYPES, PRESTIGE_BONUS, STAGE_FRACTIONS, VISITOR_ORDER, VISITORS,
                   VISIT_GREET_COINS, MASTERY_COINS, MASTERY_TOP_BONUS, MASTERY_NAMES, MASTERY_STEPS, RARITY_MULT,
                   SHINY_CHANCE, SHINY_GREET_COINS)
from . import pots
from .panels import Panel
from .theme import T
from .util import fmt_int, fmt_left

TABS = (("bed", "Bedienung"), ("pfl", "Pflanzen"), ("reg", "Regeln"), ("shop", "Shop"), ("ver", "Version"))
G = "{:g}".format
T_GREEN = QColor("#2E9E44")


def pct(x):
    return f"{x * 100:g} %"


def blocks(tab, plant=None):
    """Inhalt eines Reiters: ("h", Titel) | ("p", Text) | ("b", Fettgedruckt, Text) | ("t", [Zellen], [Breiten], fett) | ("s",) Abstand."""
    if tab == "bed":
        return [
            ("h", "Maus"),
            ("p", "Linksklick: giessen und wachsen lassen. Ist das Wasser voll, gibt der Klick nur Wachstum."),
            ("p", "Linke Taste ziehen: Fenster verschieben. Mittelklick: Sprechblase ein/aus. Rechtsklick: Menü."),
            ("h", "Tastatur"),
            ("p", "Tastendrücke lassen die Pflanze wachsen und verbrauchen etwas Wasser. Gezählt wird nur die "
                  "Anzahl, nie welche Taste."),
            ("h", "Symbole der Sprechblase"),
            ("p", "Oben: Pflanze wählen (jede hat einen eigenen Spielstand, nicht gewählte pausieren)."),
            ("p", "Unten: Shop, Gartenhaus, Erfolge, Fokus-Timer, Besucher-Sammelbuch, Info."),
            ("h", "Einstellungen"),
            ("p", "Rechtsklick → Einstellungen: Tastatur zählen, Dunkelmodus, Vordergrund, Pflanzen- und Menügrösse, Lautstärke (0–100 %, 0 = stumm). Töne: Giessen beim Bewässern und ein Gong am Ende des Fokus-Timers."),
        ]
    if tab == "pfl":
        out = [("p", "Basiswerte bei gutem Wasserstand, ohne Boni.")]
        for key in PLANT_ORDER:
            k = PLANT_TYPES[key]
            keyg = f"Taste +{G(k.growth_per_key)}" if k.growth_per_key else "Tasten zählen nicht"
            out += [
                ("b", f"{k.name} ({k.difficulty})", ""),
                ("p", f"Blüte bei {fmt_int(k.bloom_at)} · Klick +{G(k.growth_per_click)} · {keyg}"),
                ("p", f"Wasser: leer nach {G(k.drain_hours)} h · Klick +{G(k.water_per_click)} %"
                      + (f" · Taste −{G(k.water_per_key)} %" if k.water_per_key else "")),
                ("p", f"Wächst voll bei {G(k.water_low)}–{G(k.water_high)} % · welkt unter {G(k.wilt_below)} %"
                      f" · Gold ×{G(k.coin_mult)}"),
            ]
            if k.note:
                out.append(("p", k.note))
        return out
    if tab == "reg":
        names = PLANT_TYPES["wiesenblume"].stages
        stages = " → ".join(names)
        fr = " / ".join(G(round(f * 100, 3)) for f in STAGE_FRACTIONS)
        return [
            ("h", "Wachstum"),
            ("p", "Pro Klick/Taste = Basiswert × Wasserfaktor × Boni. Wasserfaktor: unter «voll» linear weniger, "
                  "bei 0 % kein Wachstum, über dem Maximum nur ×0.3 (Staunässe)."),
            ("p", f"Boni werden multipliziert: Dünger, Prestige (+{pct(PRESTIGE_BONUS)} je Stufe), "
                  f"Lampe (+{pct(LAMP_BOOST)}), Fokus (×{G(FOCUS_MULT)})."),
            ("p", f"Stadien (Anteil vom Blütewert: {fr} %): {stages}."),
            ("h", "Wasser"),
            ("p", "Sinkt laufend, auch bei ausgeschaltetem PC. Nicht gewählte Pflanzen pausieren. "
                  "Unter der Welkgrenze welkt die Pflanze sichtbar."),
            ("h", "Gold"),
            ("p", "Stufen 1–6: " + " / ".join(str(c) for c in STAGE_COINS[1:]) + " Gold × Faktor der Pflanze."),
            ("p", f"Nach der Blüte je +{pct(MILESTONE_STEP)} des Blütewerts: {MILESTONE_COINS} Gold × Faktor. "
                  f"Passiv {PASSIVE_PER_HOUR} Gold pro Stunde."),
            ("h", "Prestige"),
            ("p", f"Blühende Pflanze einlagern: Stufe der Art +1 (dauerhaft +{pct(PRESTIGE_BONUS)} Wachstum und "
                  "Gold). Nicht ausgewachsene kommen nur ins Gartenhaus. Bereit ist die Pflanze, sobald sie "
                  "blüht: eine sanfte goldene Aura leuchtet dann hinter ihr."),
            ("p", "Beim Einlagern wählst du den Topf der neuen Pflanze: der Originaltopf ist gratis, dazu gibt es "
                  f"ein günstiges ({pots.price_range('cheap')[0]}–{pots.price_range('cheap')[1]} Gold) und ein edles "
                  f"({pots.price_range('premium')[0]}–{pots.price_range('premium')[1]} Gold) Design aus dem "
                  "Sortiment deiner Pflanze. Das Angebot wechselt nach jeder Aussaat; der Topf ist nur Zierde und "
                  "bleibt bei der Pflanze."),
            ("h", "Fokus-Timer"),
            ("p", f"{' / '.join(str(m) for m in FOCUS_PRESETS)} min mit ×{G(FOCUS_MULT)} Wachstum. "
                  "Belohnung: Minuten ÷ 5 Gold. Abbruch kostet nur den Bonus."),
            ("p", "Fokusmodus (Schalter im Fokus-Fenster, Standard an): Beim Start schliessen sich alle anderen "
                  "Fenster, nur die Pflanze und die Zeit mit Ring bleiben. Nach Ablauf oder Abbruch (Rechtsklick → "
                  "«Fokus abbrechen») kommen die vorher offenen Fenster zurück."),
            ("h", "Erfolge"),
            ("p", "3 täglich, 3 wöchentlich, 6 einmalig. Belohnung einzeln oder gesammelt abholen; "
                  "Nicht Abgeholtes bleibt in der Liste."),
            ("h", "Besucher"),
            ("p", "Jede Minute Chance 10 % (+5 % ab halber Grösse, +10 % bei Blüte). Klick: "
                  f"+{VISIT_GREET_COINS} Gold. " + ", ".join(
                      f"{VISITORS[k].name} ({VISITORS[k].rarity})" for k in VISITOR_ORDER) + "."),
            ("p", "Meisterschaft: nach " + " / ".join(str(s) for s in MASTERY_STEPS) + " Besuchen die Stufen "
                  + " / ".join(MASTERY_NAMES) + " (Setzling mit 1–3 Blättern im Sammelbuch). Belohnung "
                  + " / ".join(str(c) for c in MASTERY_COINS) + " Gold, bei seltenen ×"
                  + G(RARITY_MULT["selten"]) + ", bei sehr seltenen ×" + G(RARITY_MULT["sehr selten"])
                  + f". Jeder Gartenbewohner: +{pct(MASTERY_TOP_BONUS)} Wachstum."),
            ("p", "Farbvarianten (Stern im Sammelbuch, Name in Gold): Chance je Besuch "
                  + " / ".join(pct(SHINY_CHANCE[r]) for r in ("häufig", "selten", "sehr selten"))
                  + f" (häufig / selten / sehr selten). Klick: +{SHINY_GREET_COINS} Gold."),
        ]
    if tab == "ver":
        return version_blocks(plant)
    out = [("h", "Dünger (wirkt auf die gewählte Pflanze)"),
           ("t", ["Name", "Preis", "Wachstum", "Wasser", "Dauer"], (92, 38, 76, 60, 50), True)]
    for key in FERT_ORDER:
        f = FERTILIZERS[key]
        out.append(("t", [f.name, str(f.price), f"+{f.boost * 100:g} %", f"+{f.water * 100:g} %" if f.water else "–",
                          fmt_left(f.minutes * 60)], (92, 38, 76, 60, 50), False))
    out.append(("s",))
    out.append(("p", "Zeit läuft nur, solange die Pflanze gewählt ist und das Spiel läuft. Nochmal kaufen verlängert."))
    out.append(("h", "Helfer (einmal kaufen, einzeln schaltbar)"))
    for key in HELPER_ORDER:
        h = HELPERS[key]
        out += [("b", h.name, f"{fmt_int(h.price)} Gold"), ("p", h.desc)]
    return out


def version_blocks(plant):
    """Reiter «Version»: Programmangaben und Release Notes."""
    import platform
    from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
    from . import __version__, config, debug
    from .changelog import CHANGELOG
    src = {"evdev": "evdev", "pynput": "pynput"}.get(getattr(plant, "key_source", None), "nicht verfügbar")
    out = [("h", f"Topfpflanze {__version__}"),
           ("p", f"System: {platform.system()} {platform.release()}"),
           ("p", f"Python {platform.python_version()} · Qt {QT_VERSION_STR} · PyQt {PYQT_VERSION_STR}"),
           ("p", f"Tastaturzählung: {src}"),
           ("p", f"Spielstand: {config.STATE_FILE}")]
    if debug.enabled():
        out.append(("p", "Debug-Modus aktiv (eigener Spielstand)."))
    out.append(("p", "Quellcode und Downloads: github.com/donsimm/topfpflanze-v1"))
    out.append(("h", "Release Notes"))
    for version, date, items in CHANGELOG:
        out.append(("b", version, date or ""))
        out += [("p", "• " + text) for text in items]
    return out


class InfoWin(Panel):
    W, H = 350, 500
    TOP = 88            # Beginn des scrollbaren Bereichs
    BOTTOM = 10

    def __init__(self, plant):
        super().__init__(plant, self.W, self.H, "info_pos")
        self.tab = "bed"
        self.scroll = 0.0
        self.cache = {}

    # ---------- Layout ----------

    def tab_rects(self):
        w = (self.width() - 24 - (len(TABS) - 1) * 5) / len(TABS)
        return [(key, QRectF(12 + i * (w + 5), 58, w, 22)) for i, (key, _n) in enumerate(TABS)]

    def view_height(self):
        return self.height() - self.TOP - self.BOTTOM

    def layout(self):
        """Positioniert alle Blöcke des gewählten Reiters; liefert (Liste, Gesamthöhe)."""
        if self.tab in self.cache:
            return self.cache[self.tab]
        base = self.font()
        head, bold, body = (self.font_px(base, 12, True), self.font_px(base, 11, True), self.font_px(base, 11))
        width = self.width() - 24 - 8
        y, out = 0.0, []
        for blk in blocks(self.tab, self.plant):
            kind = blk[0]
            if kind == "h":
                y += 8 if y else 0
                out.append(("h", blk[1], QRectF(0, y, width, 18), head))
                y += 19
            elif kind == "b":
                y += 4
                out.append(("b", blk, QRectF(0, y, width, 16), bold))
                y += 16
            elif kind == "s":
                y += 5
            elif kind == "t":
                out.append(("t", blk, QRectF(0, y, width, 15), bold if blk[3] else body))
                y += 15
            else:
                h = QFontMetricsF(body).boundingRect(QRectF(0, 0, width, 5000), int(Qt.TextFlag.TextWordWrap),
                                                     blk[1]).height()
                out.append(("p", blk[1], QRectF(0, y, width, h + 1), body))
                y += h + 4
        self.cache[self.tab] = (out, y)
        return self.cache[self.tab]

    def max_scroll(self):
        return max(0.0, self.layout()[1] - self.view_height())

    # ---------- Eingaben ----------

    def items(self):
        return [(("tab", k), r, True) for k, r in self.tab_rects()]

    def on_click(self, key):
        if key[0] == "tab" and key[1] != self.tab:
            self.tab, self.scroll = key[1], 0.0

    def wheelEvent(self, e):
        self.scroll = max(0.0, min(self.max_scroll(), self.scroll - e.angleDelta().y() / 2))
        self.update()

    # ---------- Zeichnen ----------

    def paintEvent(self, _e):
        p = self.begin("Info", "Spielregeln und Werte")
        base = self.font()
        for key, r in self.tab_rects():
            sel = key == self.tab
            p.setPen(QPen(T_GREEN, 1.6) if sel else QPen(T("cell_border"), 1))
            p.setBrush(T("active_bg") if sel else T("cell"))
            p.drawRoundedRect(r, 6, 6)
            p.setFont(self.font_px(base, 10, sel))
            p.setPen(T("button_text") if sel else T("text2"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, dict(TABS)[key])
        items, total = self.layout()
        view = QRectF(12, self.TOP, self.width() - 24, self.view_height())
        p.setPen(QPen(T("sep"), 1))
        p.drawLine(QPointF(view.left(), self.TOP - 4), QPointF(view.right(), self.TOP - 4))
        p.save()
        p.setClipRect(view)
        p.translate(view.left(), view.top() - self.scroll)
        for kind, data, rect, font in items:
            if rect.bottom() < self.scroll or rect.top() > self.scroll + view.height():
                continue
            p.setFont(font)
            p.setPen(T("text") if kind in ("h", "b", "t") else T("text2"))
            if kind == "h":
                p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, data)
            elif kind == "b":
                p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, data[1])
                if data[2]:
                    p.setPen(T("coin") if data[2].endswith("Gold") else T("muted"))
                    p.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, data[2])
            elif kind == "t":
                x = 0.0
                for i, (cell, w) in enumerate(zip(data[1], data[2])):
                    al = Qt.AlignmentFlag.AlignLeft if i == 0 else Qt.AlignmentFlag.AlignRight
                    p.drawText(QRectF(x, rect.top(), w - 4, rect.height()), al | Qt.AlignmentFlag.AlignVCenter, cell)
                    x += w
            else:
                p.drawText(rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                           data)
        p.restore()
        ms = self.max_scroll()
        if ms > 0:  # Scrollbalken
            track = view.height() - 8
            bar = max(24.0, track * view.height() / (view.height() + ms))
            y = view.top() + 4 + (track - bar) * self.scroll / ms
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(T("scroll"))
            p.drawRoundedRect(QRectF(self.width() - 9, y, 3, bar), 1.5, 1.5)
        p.end()

