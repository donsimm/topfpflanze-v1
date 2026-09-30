"""Info-Fenster: Bedienung, Pflanzenwerte, Spielregeln und Shop in Kurzform (Werte aus den Spieldaten)."""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QPen

from .i18n import tr
from .config import MILESTONE_COINS, MILESTONE_STEP, PASSIVE_PER_HOUR, STAGE_COINS
from .data import (ACHIEVEMENTS, RARITY_LABEL, FERTILIZERS, FERT_ORDER, FOCUS_MULT, FOCUS_PRESETS, HELPER_ORDER, HELPERS, LAMP_BOOST,
                   PLANT_ORDER, PLANT_TYPES, PRESTIGE_BONUS, STAGE_FRACTIONS, VISITOR_ORDER, VISITORS,
                   VISIT_GREET_COINS, MASTERY_COINS, MASTERY_TOP_BONUS, MASTERY_NAMES, MASTERY_STEPS, RARITY_MULT,
                   SHINY_CHANCE, SHINY_GREET_COINS)
from . import pots
from .panels import Panel
from .theme import T
from .util import fmt_int, fmt_left

TABS = (("bed", tr("Bedienung")), ("pfl", tr("Pflanzen")), ("reg", tr("Regeln")), ("shop", tr("Shop")), ("ver", tr("Version")))
G = "{:g}".format
_GENERAL = [a for a in ACHIEVEMENTS if a.period == "general"]
T_GREEN = QColor("#2E9E44")


def pct(x):
    return f"{x * 100:g} %"


def blocks(tab, plant=None):
    """Inhalt eines Reiters: ("h", Titel) | ("p", Text) | ("b", Fettgedruckt, Text) | ("t", [Zellen], [Breiten], fett) | ("s",) Abstand."""
    if tab == "bed":
        return [
            ("h", tr("Maus")),
            ("p", tr("Linksklick: giessen und wachsen lassen. Ist das Wasser voll, gibt der Klick nur Wachstum.")),
            ("p", tr("Linke Taste ziehen: Fenster verschieben. Mittelklick: Sprechblase ein/aus. Rechtsklick: Menü.")),
            ("h", tr("Tastatur")),
            ("p", tr("Tastendrücke lassen die Pflanze wachsen und verbrauchen etwas Wasser. Gezählt wird nur die "
                  "Anzahl, nie welche Taste.")),
            ("h", tr("Symbole der Sprechblase")),
            ("p", tr("Oben: Pflanze wählen (jede hat einen eigenen Spielstand, nicht gewählte pausieren).")),
            ("p", tr("Unten: Shop, Gartenhaus, Erfolge, Fokus-Timer, Besucher-Sammelbuch, Info.")),
            ("h", tr("Einstellungen")),
            ("p", tr("Rechtsklick → Einstellungen: Tastatur zählen, Sprache (Deutsch / English / Français / Italiano, startet das Spiel neu), Dunkelmodus, Vordergrund, Pflanzen- und Menügrösse, Lautstärke (0–100 %, Standard 0 = stumm). Töne: Giessen beim Bewässern und ein Gong am Ende des Fokus-Timers.")),
        ]
    if tab == "pfl":
        out = [("p", tr("Basiswerte bei gutem Wasserstand, ohne Boni."))]
        for key in PLANT_ORDER:
            k = PLANT_TYPES[key]
            keyg = tr("Taste +{growth_per_key}", growth_per_key=G(k.growth_per_key)) if k.growth_per_key else tr("Tasten zählen nicht")
            out += [
                ("b", f"{k.name} ({k.difficulty})", ""),
                ("p", tr("Blüte bei {bloom_at} · Klick +{growth_per_click} · {keyg}", bloom_at=fmt_int(k.bloom_at), growth_per_click=G(k.growth_per_click), keyg=keyg)),
                ("p", tr("Wasser: leer nach {drain_hours} h · Klick +{water_per_click} %", drain_hours=G(k.drain_hours), water_per_click=G(k.water_per_click))
                      + (tr(" · Taste −{water_per_key} %", water_per_key=G(k.water_per_key)) if k.water_per_key else "")),
                ("p", tr("Wächst voll bei {water_low}–{water_high} % · welkt unter {wilt_below} % · Gold ×{coin_mult}", water_low=G(k.water_low), water_high=G(k.water_high), wilt_below=G(k.wilt_below), coin_mult=G(k.coin_mult))),
            ]
            if k.note:
                out.append(("p", k.note))
        return out
    if tab == "reg":
        names = PLANT_TYPES["wiesenblume"].stages
        stages = " → ".join(names)
        fr = " / ".join(G(round(f * 100, 3)) for f in STAGE_FRACTIONS)
        return [
            ("h", tr("Wachstum")),
            ("p", tr("Pro Klick/Taste = Basiswert × Wasserfaktor × Boni. Wasserfaktor: unter «voll» linear weniger, "
                  "bei 0 % kein Wachstum, über dem Maximum nur ×0.3 (Staunässe).")),
            ("p", tr("Boni werden multipliziert: Dünger, Prestige (+{pct} je Stufe), Lampe (+{pct2}), Fokus (×{v}).", pct=pct(PRESTIGE_BONUS), pct2=pct(LAMP_BOOST), v=G(FOCUS_MULT))),
            ("p", tr("Stadien (Anteil vom Blütewert: {fr} %): {stages}.", fr=fr, stages=stages)),
            ("h", tr("Wasser")),
            ("p", tr("Sinkt laufend, auch bei ausgeschaltetem PC. Nicht gewählte Pflanzen pausieren. "
                  "Unter der Welkgrenze welkt die Pflanze sichtbar.")),
            ("h", tr("Gold")),
            ("p", tr("Stufen 1–6: {coins} Gold × Faktor der Pflanze.", coins=" / ".join(str(c) for c in STAGE_COINS[1:]))),
            ("p", tr("Nach der Blüte je +{pct} des Blütewerts: {v} Gold × Faktor. Passiv {v2} Gold pro Stunde.", pct=pct(MILESTONE_STEP), v=MILESTONE_COINS, v2=PASSIVE_PER_HOUR)),
            ("h", tr("Prestige")),
            ("p", tr("Blühende Pflanze einlagern: Stufe der Art +1 (dauerhaft +{pct} Wachstum und Gold). Nicht ausgewachsene kommen nur ins Gartenhaus. Bereit ist die Pflanze, sobald sie blüht: eine sanfte goldene Aura leuchtet dann hinter ihr.", pct=pct(PRESTIGE_BONUS))),
            ("p", tr("Beim Einlagern wählst du den Topf der neuen Pflanze: der Originaltopf ist gratis, dazu gibt es ein günstiges ({cheap}–{cheap2} Gold) und ein edles ({premium}–{premium2} Gold) Design aus dem Sortiment deiner Pflanze. Das Angebot wechselt nach jeder Aussaat; der Topf ist nur Zierde und bleibt bei der Pflanze.", cheap=pots.price_range('cheap')[0], cheap2=pots.price_range('cheap')[1], premium=pots.price_range('premium')[0], premium2=pots.price_range('premium')[1])),
            ("h", tr("Fokus-Timer")),
            ("p", tr("{m} min mit ×{v} Wachstum. Belohnung: Minuten ÷ 5 Gold. Abbruch kostet nur den Bonus.", m=' / '.join(str(m) for m in FOCUS_PRESETS), v=G(FOCUS_MULT))),
            ("p", tr("Fokusmodus (Schalter im Fokus-Fenster, Standard an): Beim Start schliessen sich alle anderen "
                  "Fenster, nur die Pflanze und die Zeit mit Ring bleiben. Nach Ablauf oder Abbruch (Rechtsklick → "
                  "«Fokus abbrechen») kommen die vorher offenen Fenster zurück.")),
            ("h", tr("Erfolge")),
            ("p", tr("3 täglich, 3 wöchentlich, {v} einmalige in {a} Reihen (Tasten, Klicks, Shop, Besuche, Fokus u. a.): Im Fenster erscheint je Reihe die nächste Stufe. Belohnung einzeln oder gesammelt abholen; Nicht Abgeholtes bleibt in der Liste.", v=len(_GENERAL), a=len({a.series for a in _GENERAL}))),
            ("h", tr("Besucher")),
            ("p", tr("Jede Minute Chance 10 % (+5 % ab halber Grösse, +10 % bei Blüte). Klick: +{coins} Gold. {list}.",
                     coins=VISIT_GREET_COINS,
                     list=", ".join(f"{VISITORS[k].name} ({RARITY_LABEL[VISITORS[k].rarity]})" for k in VISITOR_ORDER))),
            ("p", tr("Meisterschaft: nach {steps} Besuchen die Stufen {names} (Setzling mit 1–3 Blättern im Sammelbuch). "
                     "Belohnung {coins} Gold, bei seltenen ×{rare}, bei sehr seltenen ×{very_rare}. "
                     "Jeder Gartenbewohner: +{pct} Wachstum.",
                     steps=" / ".join(str(s) for s in MASTERY_STEPS), names=" / ".join(MASTERY_NAMES),
                     coins=" / ".join(str(c) for c in MASTERY_COINS), rare=G(RARITY_MULT["selten"]),
                     very_rare=G(RARITY_MULT["sehr selten"]), pct=pct(MASTERY_TOP_BONUS))),
            ("p", tr("Farbvarianten (Stern im Sammelbuch, Name in Gold): Chance je Besuch {chances} "
                     "(häufig / selten / sehr selten). Klick: +{coins} Gold.",
                     chances=" / ".join(pct(SHINY_CHANCE[r]) for r in ("häufig", "selten", "sehr selten")),
                     coins=SHINY_GREET_COINS)),
        ]
    if tab == "ver":
        return version_blocks(plant)
    out = [("h", tr("Dünger (wirkt auf die gewählte Pflanze)")),
           ("t", [tr("Name"), tr("Preis"), tr("Wachstum"), tr("Wasser"), tr("Dauer")], (92, 38, 76, 60, 50), True)]
    for key in FERT_ORDER:
        f = FERTILIZERS[key]
        out.append(("t", [f.name, str(f.price), f"+{f.boost * 100:g} %", f"+{f.water * 100:g} %" if f.water else "–",
                          fmt_left(f.minutes * 60)], (92, 38, 76, 60, 50), False))
    out.append(("s",))
    out.append(("p", tr("Zeit läuft nur, solange die Pflanze gewählt ist und das Spiel läuft. Nochmal kaufen verlängert.")))
    out.append(("h", tr("Helfer (einmal kaufen, einzeln schaltbar)")))
    for key in HELPER_ORDER:
        h = HELPERS[key]
        out += [("b", h.name, tr("{price} Gold", price=fmt_int(h.price))), ("p", h.desc)]
    return out


def version_blocks(plant):
    """Reiter «Version»: Programmangaben und Release Notes."""
    import platform
    from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
    from . import __version__, config, debug
    from .changelog import CHANGELOG
    src = {"evdev": "evdev", "pynput": "pynput"}.get(getattr(plant, "key_source", None), tr("nicht verfügbar"))
    out = [("h", f"Topfpflanze {__version__}"),
           ("p", tr("System: {system} {release}", system=platform.system(), release=platform.release())),
           ("p", f"Python {platform.python_version()} · Qt {QT_VERSION_STR} · PyQt {PYQT_VERSION_STR}"),
           ("p", tr("Tastaturzählung: {src}", src=src)),
           ("p", tr("Spielstand: {config}", config=config.STATE_FILE))]
    if debug.enabled():
        out.append(("p", tr("Debug-Modus aktiv (eigener Spielstand).")))
    out.append(("p", tr("Quellcode und Downloads: github.com/donsimm/topfpflanze-v1")))
    out.append(("h", tr("Release Notes")))
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
        p = self.begin(tr("Info"), tr("Spielregeln und Werte"))
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
                    p.setPen(T("coin") if data[2].endswith(tr("Gold")) else T("muted"))
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

