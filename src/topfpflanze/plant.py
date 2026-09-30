"""Pflanzenfenster: Spielzustand, Logik, Eingaben, Menü."""

import datetime
import json
import math
import os
import random
import sys
import time
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton,
                             QSlider, QWidget, QWidgetAction)
from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtGui import QActionGroup, QColor

from .i18n import tr
from . import config, debug, i18n, pots, scaling, sound, tooltip
from .bubble import Bubble
from .config import VISITOR_SCALE, MILESTONE_COINS, MILESTONE_STEP, PASSIVE_PER_HOUR, SCENE_DY, SEED_FRAC, STAGE_COINS, TOOL_ORDER, WATER_MAX, WIN_H, WIN_W
from .data import TOOL_NAMES, ACHIEVEMENTS, BEE_BOOST, BEE_INTERVAL, DRIP_MIN, DRIP_RATE, FERTILIZERS, FOCUS_DEFAULT, FOCUS_MULT, GNOME_INTERVAL, HELPERS, HELPER_ORDER, LAMP_BOOST, PLANT_ORDER, PLANT_TYPES, POTS, MASTERY_COINS, MASTERY_TOP_BONUS, MASTERY_NAMES, MASTERY_STEPS, PRESTIGE_BONUS, RARITY_MULT, SHINY_CHANCE, SHINY_GREET_COINS, STAGE_FRACTIONS, VARIANTS, VISITORS, VISITOR_ORDER, VISIT_DURATION, VISIT_GREET_COINS
from .garden import Garden
from .info import InfoWin
from .keys import KeyCounter
from .panels import AchievementsWin, BookWin, FocusWin
from .plant_draw import PlantDrawMixin
from .scaling import ScaledWidget
from .shop import Shop
from .sow import SowWin
from .theme import _THEME
from .util import fmt_int, fmt_left, round_half_up, stage_index, stage_name


class Plant(PlantDrawMixin, ScaledWidget):
    KIND = "plant"

    def __init__(self):
        super().__init__()
        self.state = self.load_state()
        scaling.set_scale(self.state.get("ui_scale", 1.0), "plant")
        scaling.set_scale(self.state.get("menu_scale", 1.0), "menu")
        self.sound = sound.SoundPlayer(self.state.get("volume", sound.DEFAULT_VOLUME))
        _THEME["dark"] = self.state.get("dark", False)

        self.t = 0.0
        self.last_tick = time.monotonic()
        self.last_save = self.last_tick
        self.drops = []      # [x, y, vy]
        self.sparkles = []   # [x, y, life]
        self.popups = []     # [x, y, life, text, coin] – Einblendungen
        self.popup_queue = []
        self.press_pos = None
        self.dragging = False
        self.top_point = QPointF(WIN_W / 2, 200)
        self.focus = None            # laufende Fokus-Sitzung
        self.focus_msg = ("", True, 0.0)
        self.visitor = None          # aktueller Besucher
        self.visit_acc = 0.0
        self.bee_timer = random.uniform(*BEE_INTERVAL)
        self.bee_anim = 0.0
        self.gnome_acc = 0.0
        self.gnome_hop = 0.0
        self.drip_active = False
        self.sec_acc = 0.0

        self.activate(self.state["current"], offline=True)

        self.keys = KeyCounter()
        self.key_source = self.keys.start()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.apply_flags()
        self.setFixedSize(WIN_W, WIN_H)
        self.place_window()

        self.bubble = Bubble(self)
        self.shop = Shop(self)
        self.garden = Garden(self)
        self.ach_win = AchievementsWin(self)
        self.focus_win = FocusWin(self)
        self.book_win = BookWin(self)
        self.info_win = InfoWin(self)
        self.sow_win = SowWin(self)
        self.windows = {"shop": self.shop, "garden": self.garden, "ach": self.ach_win,
                        "focus": self.focus_win, "book": self.book_win, "info": self.info_win,
                        "sow": self.sow_win}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)  # 20 fps
        self.update_tooltip()

    # ---------- Zustand ----------

    @staticmethod
    def new_plant_state(key=None):
        now = time.time()
        state = {"growth": 0.0, "water": 50.0, "clicks_total": 0, "keys_total": 0,
                 "seed": random.randrange(1 << 30), "created": now, "last_update": now,
                 "stage_rewarded": 0, "milestone_rewarded": 0, "fert": None, "bloomed_at": None,
                 "pot_skin": None}  # None = Originaltopf, sonst die Kennung eines Designs aus pots.py
        if key:  # neue Pflanze: zufällige Farbe aus der erweiterten Auswahl
            state["color"] = random.choice(PLANT_TYPES[key].palette)
        return state

    @staticmethod
    def default_state():
        return {"version": 2, "current": "wiesenblume", "plants": {},
                "pos": None, "bubble": True, "bubble_pos": None, "shop_pos": None,
                "coins": 0, "passive_acc": 0.0, "keyboard_enabled": True, "on_top": True,
                "garden": [], "garden_pos": None, "dark": False,
                "helpers": [], "helpers_off": [], "prestige": {}, "bloomed_species": [],
                "stats": {"keys": None}, "daily": {}, "weekly": {}, "ach_done": [], "ach_new": 0, "ach_pending": [],
                "book": {}, "focus_minutes": FOCUS_DEFAULT, "pot_offer": {},
                "focus_mode": True, "volume": sound.DEFAULT_VOLUME, "language": "auto"}

    def load_state(self):
        state = self.default_state()
        try:
            with open(config.STATE_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {}
        if data and "plants" not in data:
            # Spielstand der ersten Version übernehmen: wird zur Wiesenblume
            plant = {k: data[k] for k in ("growth", "water", "clicks_total", "keys_total",
                                          "seed", "created", "last_update") if k in data}
            data = {k: v for k, v in data.items()
                    if k in ("pos", "bubble", "bubble_pos", "keyboard_enabled", "on_top")}
            data["plants"] = {"wiesenblume": {**self.new_plant_state(), **plant}}
            data["current"] = "wiesenblume"
        state.update(data)
        if state["current"] not in PLANT_TYPES:
            state["current"] = "wiesenblume"
        # Erweiterungen für bestehende Spielstände
        if state["stats"].get("keys") is None:
            state["stats"]["keys"] = sum(pl.get("keys_total", 0) for pl in state["plants"].values()) + sum(
                e.get("keys_total", 0) or 0 for e in state.get("garden", []))
        stats = state["stats"]
        if stats.get("clicks") is None:
            stats["clicks"] = sum(pl.get("clicks_total", 0) for pl in state["plants"].values()) + sum(
                e.get("clicks_total", 0) or 0 for e in state.get("garden", []))
        for k in ("purchases", "spent", "focus", "focus_max", "streak"):
            stats.setdefault(k, 0)
        bloomed = set(state.get("bloomed_species", []))
        for key, pl in state["plants"].items():
            if key in PLANT_TYPES and pl.get("growth", 0) >= PLANT_TYPES[key].bloom_at:
                bloomed.add(key)
        for e in state.get("garden", []):
            if e.get("key") in PLANT_TYPES and (e.get("growth") or 0) >= PLANT_TYPES[e["key"]].bloom_at:
                bloomed.add(e["key"])
        state["bloomed_species"] = sorted(bloomed)
        return state

    def save_state(self):
        now = time.time()
        self.ps["last_update"] = now
        self.state["pos"] = [self.x(), self.y()]
        if hasattr(self, "bubble"):
            self.state["bubble_pos"] = [self.bubble.x(), self.bubble.y()]
        if hasattr(self, "shop"):
            self.state["shop_pos"] = [self.shop.x(), self.shop.y()]
        if hasattr(self, "garden"):
            self.state["garden_pos"] = [self.garden.x(), self.garden.y()]
        if hasattr(self, "windows"):
            for win in (self.ach_win, self.focus_win, self.book_win, self.info_win):
                self.state[win.pos_key] = list(win.saved_pos())
        try:
            config.STATE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = config.STATE_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            os.replace(tmp, config.STATE_FILE)
        except OSError as e:
            print(tr("Speichern fehlgeschlagen: {v}", v=e), file=sys.stderr)

    def activate(self, key, offline=False):
        """Wählt die aktive Pflanze. Nicht aktive Pflanzen pausieren."""
        now = time.time()
        if hasattr(self, "ps"):
            self.ps["last_update"] = now
        self.state["current"] = key
        self.kind = PLANT_TYPES[key]
        self.pot = POTS[self.kind.pot]
        plants = self.state["plants"]
        if key not in plants:
            plants[key] = self.new_plant_state(key)
        self.ps = plants[key]
        for k, v in self.new_plant_state().items():  # ohne 'color': bestehende Farbe bleibt
            self.ps.setdefault(k, v)
        if offline:
            elapsed = max(0.0, now - self.ps["last_update"])
            self.ps["water"] = max(0.0, self.ps["water"] - elapsed * self.drain_rate())
        self.ps["last_update"] = now
        self.drops.clear()
        self.sparkles.clear()
        self.popups.clear()
        self.setup_randomness()

    def setup_randomness(self):
        rng = random.Random(self.ps["seed"])
        self.lean = rng.uniform(-14, 14)
        self.lean_dir = 1 if self.lean >= 0 else -1
        self.leaf_rnd = [(rng.uniform(0.85, 1.15), rng.uniform(-10, 10)) for _ in range(40)]
        self.rnd = [rng.random() for _ in range(200)]
        self.blossom = [(rng.random(), rng.random(), rng.random()) for _ in range(100)]
        legacy = rng.choice(self.kind.colors)  # bisherige Berechnung, bleibt für alte Pflanzen gleich
        if not self.ps.get("color"):
            self.ps["color"] = legacy
        self.flower_color = QColor(self.ps["color"])

    # ---------- Fenster ----------

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.state.get("on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def place_window(self):
        pos = self.state.get("pos")
        if pos:
            self.move(int(pos[0]), int(pos[1]))
            return
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.right() - self.real_width() - 40, g.bottom() - self.real_height() - 40)

    def select_plant(self, key):
        if key != self.state["current"]:
            self.activate(key)
            self.save_state()
            self.update_tooltip()
        self.update()
        self.bubble.update()
        if hasattr(self, "shop"):
            self.shop.update()

    def set_ui_scale(self, value, kind="plant"):
        """Grösse ändern (0.5 bis 2.0): «plant» = Pflanze mit Topf, «menu» = alle Menüfenster."""
        old = scaling.get_scale(kind)
        new = scaling.set_scale(value, kind)
        if abs(new - old) < 1e-6:
            return
        if kind == "plant":
            self.state["ui_scale"] = round(new, 3)
            # Fixpunkt: Fusspunkt (Mitte unten) der Pflanze bleibt an seinem Platz
            ax, ay = self.x() + self.real_width() / 2, self.y() + self.real_height()
            old_top = self.y()
            self.rescale()
            self.move(int(round(ax - self.real_width() / 2)), int(round(ay - self.real_height())))
            # Sprechblase folgt der Oberkante der Pflanze
            self.bubble.move(self.bubble.x(), self.bubble.y() + (self.y() - old_top))
        else:
            self.state["menu_scale"] = round(new, 3)
            for w in [self.bubble, *self.windows.values()]:  # jedes Fenster wächst um seine Mitte
                cx, cy = w.x() + w.real_width() / 2, w.y() + w.real_height() / 2
                w.rescale()
                w.move(int(round(cx - w.real_width() / 2)), int(round(cy - w.real_height() / 2)))
        self.clamp_windows_to_screen()
        self.update_tooltip()
        self.save_state()

    def clamp_to_screen(self, w):
        """Schiebt ein einzelnes Fenster auf den Bildschirm zurück, auf dem es liegt (bei mehreren Monitoren
        nicht auf den Hauptbildschirm). Liegt es auf keinem Bildschirm, gilt der Bildschirm der Pflanze."""
        screen = (QApplication.screenAt(w.geometry().center()) or QApplication.screenAt(self.geometry().center())
                  or QApplication.primaryScreen())
        if not screen:
            return
        g = screen.availableGeometry()
        x = max(g.left(), min(w.x(), g.right() - w.real_width() + 1))
        y = max(g.top(), min(w.y(), g.bottom() - w.real_height() + 1))
        if (x, y) != (w.x(), w.y()):
            w.move(x, y)

    def clamp_windows_to_screen(self):
        """Nach einer Grössenänderung: Pflanze, Sprechblase und alle Fenster im sichtbaren Bereich halten."""
        for w in [self, self.bubble, *self.windows.values()]:
            self.clamp_to_screen(w)

    def set_dark(self, on):
        self.state["dark"] = on
        _THEME["dark"] = on
        for win in [self.bubble] + list(self.windows.values()):
            win.update()
        self.save_state()

    def toggle_window(self, key):
        win = self.windows[key]
        win.setVisible(not win.isVisible())

    def toggle_shop(self):
        self.shop.setVisible(not self.shop.isVisible())

    def toggle_garden(self):
        self.garden.setVisible(not self.garden.isVisible())

    def set_bubble(self, visible):
        self.state["bubble"] = visible
        self.bubble.setVisible(visible)

    def update_tooltip(self):
        s, k = self.ps, self.kind
        self.tip_text = (tr("{v} · {growth}\nWachstum {growth2:.0f} · Wasser {water:.0f} %", v=k.name, growth=stage_name(k, s['growth']), growth2=s['growth'], water=s['water']))

    def tooltip_at(self, pos):
        return getattr(self, "tip_text", "")

    # ---------- Logik ----------

    def drain_rate(self):
        return WATER_MAX / (self.kind.drain_hours * 3600)

    def fert(self):
        f = self.ps.get("fert")
        if f and f.get("key") in FERTILIZERS and f.get("left", 0) > 0:
            return FERTILIZERS[f["key"]], f["left"]
        return None, 0

    def growth_mult(self):
        fz, _ = self.fert()
        m = 1.0 + fz.boost if fz else 1.0
        m *= 1.0 + PRESTIGE_BONUS * self.prestige_level()
        m *= 1.0 + MASTERY_TOP_BONUS * self.top_count()
        if self.helper_on("lampe"):
            m *= 1.0 + LAMP_BOOST
        if self.focus:
            m *= FOCUS_MULT
        return m

    def prestige_ready(self):
        """Die gewählte Pflanze ist ausgewachsen (Blüte erreicht) und kann fürs Prestige eingelagert werden."""
        return self.ps["growth"] >= self.kind.bloom_at

    def prestige_level(self, key=None):
        return self.state.get("prestige", {}).get(key or self.state["current"], 0)

    def prestige_summary(self):
        lvl = self.prestige_level()
        return tr("Stufe {lvl} · +{lvl2:.0f} %", lvl=lvl, lvl2=lvl * PRESTIGE_BONUS * 100) if lvl else "–"

    def add_growth(self, amount):
        self.ps["growth"] += amount
        self.ensure_periods()
        self.state["weekly"]["growth"] = self.state["weekly"].get("growth", 0) + amount

    def popup(self, text, coin=True):
        """Einblendung über der Pflanze; mehrere erscheinen nacheinander."""
        self.popup_queue.append((text, coin))

    def release_popups(self):
        if self.popup_queue and all(pu[2] < 0.8 for pu in self.popups):
            text, coin = self.popup_queue.pop(0)
            tp = self.top_point
            self.popups.append([tp.x(), max(20.0 - SCENE_DY, tp.y() - 12), 1.0, text, coin])

    # ---------- Tages- und Wochenwerte, Erfolge ----------

    def ensure_periods(self):
        today, week = time.strftime("%Y-%m-%d"), time.strftime("%G-W%V")
        st = self.state
        if st.get("daily", {}).get("date") != today:
            st["daily"] = {"date": today, "keys": 0, "clicks": 0, "focus": 0, "focus_min": 0, "done": []}
        if st.get("weekly", {}).get("week") != week:
            st["weekly"] = {"week": week, "keys": 0, "growth": 0.0, "focus": 0, "done": []}
        stats = st["stats"]
        if stats.get("last_day") != today:   # Tage in Folge: gestern gespielt = weiter, sonst von vorn
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            stats["streak"] = stats.get("streak", 0) + 1 if stats.get("last_day") == yesterday else 1
            stats["last_day"] = today
        for e in st.get("ach_pending", []):  # ältere Einträge ohne Periode ergänzen
            if "period" not in e:
                e["period"] = next((a.period for a in ACHIEVEMENTS if a.key == e["key"]), "general")
                e["pid"] = self.ach_pid(e["period"])

    def ach_pid(self, period):
        """Kennung der laufenden Periode (Tag bzw. Kalenderwoche); leer bei einmaligen Erfolgen."""
        if period == "daily":
            return time.strftime("%Y-%m-%d")
        if period == "weekly":
            return time.strftime("%G-W%V")
        return ""

    def ach_value(self, key):
        st = self.state
        d, w = st["daily"], st["weekly"]
        stats = st["stats"]
        keys, clicks, buys = stats["keys"], stats.get("clicks", 0), stats.get("purchases", 0)
        prestige = sum(st["prestige"].values())
        visits = sum(e.get("count", 0) for e in st["book"].values())
        regulars = sum(1 for k in VISITOR_ORDER if self.mastery_tier(k) >= 2)
        variants = sum(1 for e in st["book"].values() if e.get("shiny", 0) > 0)
        return {
            "d_keys": d.get("keys", 0), "d_clicks": d.get("clicks", 0), "d_focus": d.get("focus", 0),
            "w_keys": w.get("keys", 0), "w_growth": int(w.get("growth", 0)), "w_focus": w.get("focus", 0),
            **{k: len(st["bloomed_species"]) for k in ("g_bloom", "g_bloom2", "g_bloom3", "g_bloom4", "g_species")},
            "g_garden": len(st["garden"]), "g_garden150": len(st["garden"]), "g_garden500": len(st["garden"]),
            "g_prestige": max(st["prestige"].values(), default=0),
            "g_keys": keys, "g_keys1": keys, "g_keys10": keys, "g_keys500": keys, "g_keys1m": keys,
            "g_garden15": len(st["garden"]), "g_garden50": len(st["garden"]), "g_prestige5": prestige, "g_prestige15": prestige, "g_prestige50": prestige, "g_prestige150": prestige,
            "g_clicks100": clicks, "g_clicks1k": clicks, "g_clicks10k": clicks, "g_clicks100k": clicks,
            "g_clicks1m": clicks,
            "g_shop1": buys, "g_shop50": buys, "g_shop500": buys, "g_helpers": len(st["helpers"]),
            "g_spent": stats.get("spent", 0),
            "g_vis50": visits, "g_vis250": visits, "g_vis1k": visits, "g_vis5k": visits, "g_vis25k": visits,
            **{f"g_disc{i}": len(st["book"]) for i in range(1, 9)},
            **{f"g_reg{i}": regulars for i in range(1, 9)},
            **{f"g_variant{i}": variants for i in range(1, 9)},
            **{f"g_master{i}": self.top_count() for i in range(1, 9)},
            "g_focus10": stats.get("focus", 0), "g_focus50": stats.get("focus", 0), "g_focus200": stats.get("focus", 0),
            "g_focus1k": stats.get("focus", 0),
            "g_zen": stats.get("focus_max", 0),
            "g_streak3": stats.get("streak", 0), "g_streak7": stats.get("streak", 0), "g_streak30": stats.get("streak", 0),
            "g_streak100": stats.get("streak", 0), "g_streak365": stats.get("streak", 0),
        }[key]

    def ach_rows(self, period):
        """Einträge fürs Erfolge-Fenster: (Erfolg, Stufe, Anzahl Stufen). Allgemeine Erfolge sind in Reihen
        zusammengefasst; gezeigt wird die erste abholbare, sonst die nächste offene Stufe (zuletzt die letzte)."""
        out, series = [], {}
        for a in (a for a in ACHIEVEMENTS if a.period == period):
            if not a.series:
                out.append((a, 1, 1))
            elif a.series not in series:
                series[a.series] = []
                out.append(series[a.series])      # Platzhalter: Stelle der Reihe in der Anzeige
            if a.series:
                series[a.series].append(a)
        for i, item in enumerate(out):
            if isinstance(item, list):
                pick = next((j for j, a in enumerate(item) if self.ach_pending_entry(a.key)), None)
                if pick is None:
                    pick = next((j for j, a in enumerate(item) if not self.ach_is_done(a)), len(item) - 1)
                out[i] = (item[pick], pick + 1, len(item))
        return out

    def ach_done_list(self, period):
        self.ensure_periods()
        if period == "daily":
            return self.state["daily"].setdefault("done", [])
        if period == "weekly":
            return self.state["weekly"].setdefault("done", [])
        return self.state.setdefault("ach_done", [])

    def ach_is_done(self, a):
        return a.key in self.ach_done_list(a.period)

    def ach_summary(self):
        done = sum(1 for a in ACHIEVEMENTS if self.ach_is_done(a))
        return tr("{done} von {v} erreicht", done=done, v=len(ACHIEVEMENTS))

    def check_achievements(self):
        """Merkt erreichte Erfolge zur Abholung vor; das Gold gibt es erst beim Einlösen."""
        self.ensure_periods()
        self.check_mastery()
        pending = self.state.setdefault("ach_pending", [])
        for a in ACHIEVEMENTS:
            done = self.ach_done_list(a.period)
            if a.key not in done and self.ach_value(a.key) >= a.target:
                done.append(a.key)
                pending.append({"key": a.key, "name": a.name, "reward": a.reward,
                                "period": a.period, "pid": self.ach_pid(a.period)})
                self.popup(tr("Erfolg: {a}", a=a.name), coin=False)
                self.save_state()
                self.ach_win.refresh()

    def ach_pending_entry(self, key):
        """Vorgemerkter Erfolg der laufenden Periode (oder None)."""
        for e in self.state.get("ach_pending", []):
            if e["key"] == key and e.get("pid", "") == self.ach_pid(e.get("period", "general")):
                return e
        return None

    def ach_expired(self):
        """Nicht abgeholte tägliche/wöchentliche Erfolge früherer Perioden."""
        return [e for e in self.state.get("ach_pending", [])
                if e.get("period") == "mastery" or e.get("pid", "") != self.ach_pid(e.get("period", "general"))]

    def ach_pending_total(self):
        return sum(e["reward"] for e in self.state.get("ach_pending", []))

    def claim_achievement(self, entry):
        """Löst einen einzelnen vorgemerkten Erfolg ein; gibt das Gold zurück."""
        pending = self.state.get("ach_pending", [])
        if not any(e is entry for e in pending):
            return 0
        pending[:] = [e for e in pending if e is not entry]
        self.state["coins"] = self.state.get("coins", 0) + entry["reward"]
        self.popup(f"+{fmt_int(entry['reward'])} {entry['name']}")
        self.save_state()
        self.bubble.update()
        self.shop.update()
        self.ach_win.refresh()
        return entry["reward"]

    def claim_achievements(self):
        """Löst alle vorgemerkten Erfolge auf einmal ein; gibt die Summe zurück."""
        total = self.ach_pending_total()
        if total:
            self.state["coins"] = self.state.get("coins", 0) + total
            self.state["ach_pending"] = []
            self.popup(tr("+{v} Erfolge", v=fmt_int(total)))
            self.save_state()
            self.bubble.update()
            self.shop.update()
            self.ach_win.refresh()
        return total

    # ---------- Helfer ----------

    def helper_on(self, key):
        return key in self.state.get("helpers", []) and key not in self.state.get("helpers_off", [])

    def count_purchase(self, price):
        stats = self.state["stats"]
        stats["purchases"] = stats.get("purchases", 0) + 1
        stats["spent"] = stats.get("spent", 0) + price

    def helper_action(self, key):
        hp = HELPERS[key]
        owned, off = self.state.setdefault("helpers", []), self.state.setdefault("helpers_off", [])
        if key in owned:
            if key in off:
                off.remove(key)
                msg = tr("{hp} ist wieder eingeschaltet.", hp=hp.name)
            else:
                off.append(key)
                msg = tr("{hp} ist ausgeschaltet.", hp=hp.name)
            self.save_state()
            return True, msg
        coins = self.state.get("coins", 0)
        if coins < hp.price:
            return False, tr("Zu wenig Gold für {hp}: es fehlen {coins}.", hp=hp.name, coins=fmt_int(hp.price - coins))
        self.state["coins"] = coins - hp.price
        self.count_purchase(hp.price)
        owned.append(key)
        self.save_state()
        return True, tr("{hp} gekauft und aktiv.", hp=hp.name)

    def run_helpers(self, dt):
        s, k = self.ps, self.kind
        self.drip_active = False
        if self.helper_on("tropf") and s["water"] < DRIP_MIN:
            s["water"] = min(DRIP_MIN, s["water"] + DRIP_RATE * dt)
            self.drip_active = True
        if self.helper_on("hummel"):
            self.bee_timer -= dt
            if self.bee_timer <= 0:
                self.bee_timer = random.uniform(*BEE_INTERVAL)
                self.add_growth(k.bloom_at * BEE_BOOST * self.growth_mult())
                self.bee_anim = 7.0
                self.popup(tr("Hummel: Wachstum!"), coin=False)
        self.bee_anim = max(0.0, self.bee_anim - dt)
        if self.helper_on("zwerg"):
            self.gnome_acc += dt
            if self.gnome_acc >= GNOME_INTERVAL:
                self.gnome_acc -= GNOME_INTERVAL
                self.add_growth(k.growth_per_click * self.growth_mult())
                self.gnome_hop = 1.0
        self.gnome_hop = max(0.0, self.gnome_hop - dt * 2)

    # ---------- Fokus-Timer ----------

    focus_mode_active = False
    _focus_restore = ()

    def start_focus(self, minutes):
        now = time.monotonic()
        self.focus = {"minutes": minutes, "start": now, "end": now + minutes * 60}
        self.focus_msg = ("", True, 0.0)
        self.popup(tr("Fokus: {minutes} min", minutes=minutes), coin=False)
        self.enter_focus_mode()

    def abort_focus(self):
        self.focus = None
        self.focus_msg = (tr("abgebrochen, kein Bonus"), False, time.monotonic() + 30)
        self.exit_focus_mode()

    def enter_focus_mode(self):
        """Fokusmodus (Einstellung im Fokus-Fenster): alle Menüfenster schliessen, nur Pflanze und die Zeit bleiben.
        Gemerkt wird, welche Fenster offen waren, damit sie danach zurückkommen."""
        if self.focus_mode_active or not self.state.get("focus_mode", True):
            return
        others = [w for w in (self.bubble, *self.windows.values()) if w is not self.focus_win]
        self._focus_restore = [w for w in others if w.isVisible()]
        self._focus_win_was_visible = self.focus_win.isVisible()
        for w in self._focus_restore:
            w.hide()
        tooltip.hide_tip()
        self.focus_mode_active = True
        self.focus_win.set_compact(True)

    def exit_focus_mode(self):
        """Fokusmodus beenden: die Fenster, die vorher sichtbar waren, erscheinen wieder an ihrem Platz."""
        if not self.focus_mode_active:
            return
        self.focus_mode_active = False
        self.focus_win.set_compact(False)
        if not self._focus_win_was_visible:
            self.focus_win.hide()
        for w in self._focus_restore:
            w.show()
        self._focus_restore = ()
        self.bubble.update()

    def focus_remaining(self):
        rem = max(0.0, self.focus["end"] - time.monotonic())
        return rem, self.focus["minutes"] * 60

    def focus_message(self):
        text, ok, until = self.focus_msg
        return (text, ok) if time.monotonic() < until else ("", True)

    def focus_summary(self):
        if not self.focus:
            return tr("bereit")
        rem, _ = self.focus_remaining()
        m, sec = divmod(int(rem), 60)
        return tr("läuft, noch {m:02d}:{sec:02d}", m=m, sec=sec)

    def run_focus(self):
        if self.focus and time.monotonic() >= self.focus["end"]:
            minutes = self.focus["minutes"]
            self.focus = None
            reward = minutes // 5
            self.ensure_periods()
            for bucket in (self.state["daily"], self.state["weekly"]):
                bucket["focus"] = bucket.get("focus", 0) + 1
            self.state["daily"]["focus_min"] = self.state["daily"].get("focus_min", 0) + minutes
            stats = self.state["stats"]
            stats["focus"] = stats.get("focus", 0) + 1
            stats["focus_max"] = max(stats.get("focus_max", 0), minutes)
            self.state["coins"] = self.state.get("coins", 0) + reward
            self.focus_msg = (tr("geschafft! +{reward} Gold", reward=reward), True, time.monotonic() + 120)
            self.popup(tr("+{reward} Fokus geschafft", reward=reward))
            self.exit_focus_mode()
            self.sound.play("gong")
            self.save_state()

    # ---------- Besucher ----------

    def visitor_candidates(self):
        g, frac, _pv = self.basics()
        hour = time.localtime().tm_hour
        out = []
        for key in VISITOR_ORDER:
            v = VISITORS[key]
            if v.cond == "bloom" and frac < 1.0:
                continue
            if v.cond == "big" and frac < 0.15:
                continue
            if v.cond == "night" and 6 <= hour < 20:
                continue
            out.append(v)
        return out

    def run_visitors(self, dt):
        if self.visitor:
            if self.t - self.visitor["start"] > self.visitor["dur"]:
                self.visitor = None
            return
        self.visit_acc += dt
        if self.visit_acc < 60:
            return
        self.visit_acc -= 60
        _g, frac, _pv = self.basics()
        if frac < SEED_FRAC:
            return
        chance = 0.10 + (0.10 if frac >= 1.0 else 0.0) + (0.05 if frac >= 0.5 else 0.0)
        if random.random() < chance:
            self.spawn_visitor()

    def spawn_visitor(self, key=None, shiny=None):
        """Lässt einen Besucher kommen; shiny: True/False erzwingt, None = Zufall nach Seltenheit."""
        cands = self.visitor_candidates()
        if key:
            v = VISITORS[key]
        elif cands:
            v = random.choices(cands, weights=[c.weight for c in cands])[0]
        else:
            return
        if shiny is None:
            shiny = random.random() < SHINY_CHANCE[v.rarity]
        self.visitor = {"key": v.key, "start": self.t, "dur": VISIT_DURATION,
                        "phase": random.uniform(0, 6.28), "side": random.choice((-1, 1)), "shiny": bool(shiny)}
        book = self.state.setdefault("book", {})
        entry = book.setdefault(v.key, {"count": 0, "first": time.time()})
        entry["count"] += 1
        if shiny:
            entry["shiny"] = entry.get("shiny", 0) + 1
            if entry["shiny"] == 1:
                entry["shiny_first"] = time.time()
                self.mark_book_new(v.key)
                self.popup(tr("Neu: {key}!", key=VARIANTS[v.key].name), coin=False)
            else:
                self.popup(f"{VARIANTS[v.key].name}!", coin=False)
        elif entry["count"] == 1:
            self.mark_book_new(v.key)
            self.popup(tr("Neu: {v}!", v=v.name), coin=False)
        self.check_mastery()
        self.save_state()

    def mark_book_new(self, key):
        """Merkt einen neu entdeckten Besucher oder eine neue Farbvariante fürs Sammelbuch (Markierung im Menü)."""
        new = self.state.setdefault("book_new", [])
        if key not in new:
            new.append(key)

    def clear_book_new(self, key):
        new = self.state.get("book_new", [])
        if key in new:
            new.remove(key)
            self.save_state()
            return True
        return False

    # ---------- Meisterschaft ----------

    def mastery_tier(self, key):
        """Erreichte Stufe (0 = keine, 1 Besucher, 2 Stammgast, 3 Gartenbewohner) nach Anzahl Besuche."""
        count = self.state.get("book", {}).get(key, {}).get("count", 0)
        return sum(1 for s in MASTERY_STEPS if count >= s)

    def top_count(self):
        return sum(1 for k in VISITOR_ORDER if self.mastery_tier(k) >= len(MASTERY_STEPS))

    def check_mastery(self):
        """Merkt Belohnungen für neu erreichte Meisterschaftsstufen zur Abholung vor (auch rückwirkend)."""
        pending = self.state.setdefault("ach_pending", [])
        given = self.state.setdefault("mastery_given", {})
        added = False
        for key in VISITOR_ORDER:
            tier = self.mastery_tier(key)
            while given.get(key, 0) < tier:
                lvl = given.get(key, 0)
                given[key] = lvl + 1
                v = VISITORS[key]
                reward = round_half_up(MASTERY_COINS[lvl] * RARITY_MULT[v.rarity])
                pending.append({"key": f"m:{key}:{lvl + 1}", "name": f"{v.name}: {MASTERY_NAMES[lvl]}",
                                "reward": reward, "period": "mastery", "pid": ""})
                self.popup(f"{v.name}: {MASTERY_NAMES[lvl]}", coin=False)
                added = True
        if added:
            self.ach_win.refresh()

    def visitor_pos(self):
        v = self.visitor
        vt = VISITORS[v["key"]]
        a = self.t - v["start"]
        tp = self.top_point
        cx, sy = WIN_W / 2, self.pot["soil_y"]
        if vt.move == "fly":
            return QPointF(tp.x() + math.sin(a * 0.8 + v["phase"]) * 42 * v["side"],
                           tp.y() + 28 + math.sin(a * 1.6 + v["phase"]) * 18)
        if vt.move == "crawl":
            return QPointF(tp.x() + 6 + math.sin(a * 0.5) * 5, tp.y() + 14 + (a * 1.5) % 40)
        if vt.move == "sit":
            hop = abs(math.sin(a * 6)) * 3 if int(a) % 6 == 0 else 0
            return QPointF(cx + self.pot["soil_rx"] * 0.72 * v["side"], sy - 8 - hop)
        return QPointF(tp.x() + math.sin(a * 0.35 + v["phase"]) * 30, tp.y() + 34 + math.sin(a * 0.5) * 20)

    def greet_visitor(self, pos):
        if not self.visitor:
            return False
        vp = self.visitor_pos()
        if (vp - pos).manhattanLength() > 22 * VISITOR_SCALE / 1.25:
            return False
        shiny = self.visitor.get("shiny", False)
        name = VARIANTS[self.visitor["key"]].name if shiny else VISITORS[self.visitor["key"]].name
        coins = SHINY_GREET_COINS if shiny else VISIT_GREET_COINS
        self.state["coins"] = self.state.get("coins", 0) + coins
        self.popup(tr("+{coins} Hallo, {v}!", coins=coins, v=name))
        self.visitor["dur"] = self.t - self.visitor["start"] + 1.2  # fliegt davon
        return True

    def water_mult(self):
        fz, _ = self.fert()
        return 1.0 + fz.water if fz else 1.0

    def fert_summary(self):
        fz, left = self.fert()
        if not fz:
            return "–"
        parts = [f"+{fz.boost * 100:.0f} %"]
        if fz.water:
            parts.append(f"H₂O +{fz.water * 100:.0f} %")
        parts.append(fmt_left(left))
        return " · ".join(parts)

    def buy_fertilizer(self, key):
        fz = FERTILIZERS[key]
        coins = self.state.get("coins", 0)
        if coins < fz.price:
            return False, tr("Zu wenig Gold für {fz}: es fehlen {coins}.", fz=fz.name, coins=fmt_int(fz.price - coins))
        self.state["coins"] = coins - fz.price
        self.count_purchase(fz.price)
        self.ps["last_fert"] = key
        cur, left = self.fert()
        if cur and cur.key == key:
            self.ps["fert"]["left"] = left + fz.minutes * 60
            msg = tr("{fz} verlängert: wirkt noch {left} auf {v}.", fz=fz.name, left=fmt_left(self.ps['fert']['left']), v=self.kind.name)
        else:
            self.ps["fert"] = {"key": key, "left": fz.minutes * 60}
            msg = tr("{fz} wirkt jetzt auf {v}", fz=fz.name, v=self.kind.name)
            msg += tr(" (ersetzt {cur}).", cur=cur.name) if cur else "."
        self.save_state()
        self.bubble.update()
        return True, msg

    def check_rewards(self):
        s, k = self.ps, self.kind
        earned = 0
        idx = stage_index(k, s["growth"])
        while s["stage_rewarded"] < idx:
            s["stage_rewarded"] += 1
            earned += round_half_up(STAGE_COINS[s["stage_rewarded"]] * k.coin_mult)
            if s["stage_rewarded"] == len(STAGE_FRACTIONS) - 1:
                if not s.get("bloomed_at"):
                    s["bloomed_at"] = time.time()
                species = self.state.setdefault("bloomed_species", [])
                if self.state["current"] not in species:
                    species.append(self.state["current"])
        frac = s["growth"] / k.bloom_at
        milestones = int((frac - 1.0) / MILESTONE_STEP) if frac >= 1.0 else 0
        while s["milestone_rewarded"] < milestones:
            s["milestone_rewarded"] += 1
            earned += round_half_up(MILESTONE_COINS * k.coin_mult)
        if earned:
            earned = round_half_up(earned * (1.0 + PRESTIGE_BONUS * self.prestige_level()))
            self.state["coins"] = self.state.get("coins", 0) + earned
            self.popup(f"+{fmt_int(earned)}")
            self.save_state()

    def passive_income(self, dt):
        acc = self.state.get("passive_acc", 0.0) + dt * PASSIVE_PER_HOUR / 3600
        whole = int(acc + 1e-6)  # Toleranz gegen Rundungsfehler beim Aufsummieren
        if whole:
            self.state["coins"] = self.state.get("coins", 0) + whole
            self.popup(f"+{whole}")
        self.state["passive_acc"] = acc - whole

    def water_factor(self):
        w, k = self.ps["water"], self.kind
        if w <= 0:
            return 0.0
        f = min(1.0, w / k.water_low)
        if w > k.water_high:
            f *= 0.3  # Staunässe
        return f

    def wilt(self):
        w, lim = self.ps["water"], self.kind.wilt_below
        return 0.0 if w >= lim else (lim - w) / lim

    def basics(self):
        g = self.ps["growth"]
        frac = g / self.kind.bloom_at
        return g, frac, min(1.0, frac) ** 0.5

    def tick(self):
        now = time.monotonic()
        dt_real = now - self.last_tick
        self.last_tick = now
        self.t += dt_real
        dt = debug.apply_time(self, dt_real)
        s, k = self.ps, self.kind

        wm = self.water_mult()
        s["water"] = max(0.0, s["water"] - dt * self.drain_rate() * wm)
        fz, left = self.fert()
        if fz:
            s["fert"]["left"] = left - dt
            if s["fert"]["left"] <= 0:
                s["fert"] = None
                last = s.get("last_fert")
                if self.helper_on("automat") and last in FERTILIZERS \
                        and self.state.get("coins", 0) >= FERTILIZERS[last].price:
                    self.buy_fertilizer(last)
                    self.popup(tr("Automat: {last}", last=FERTILIZERS[last].name), coin=False)

        self.ensure_periods()
        n = self.keys.take()
        if n and self.state.get("keyboard_enabled", True):
            self.state["stats"]["keys"] += n
            self.state["daily"]["keys"] += n
            self.state["weekly"]["keys"] += n
        if n and k.growth_per_key > 0 and self.state.get("keyboard_enabled", True):
            s["keys_total"] += n
            self.add_growth(n * k.growth_per_key * self.water_factor() * self.growth_mult())
            s["water"] = max(0.0, s["water"] - n * k.water_per_key * wm)
            if len(self.sparkles) < 12 and s["water"] > 0:
                tp = self.top_point
                self.sparkles.append([tp.x() + random.uniform(-25, 25),
                                      tp.y() + random.uniform(-10, 20), 1.0])

        self.run_helpers(dt)
        self.run_focus()
        self.run_visitors(dt)
        self.check_rewards()
        self.passive_income(dt)
        self.update_particles(dt_real)
        self.sec_acc += dt_real
        if self.sec_acc >= 1.0:
            self.sec_acc = 0.0
            self.check_achievements()
            if self.ach_win.isVisible():
                self.ach_win.refresh()
            if self.sow_win.isVisible():
                self.sow_win.refresh()
        if now - self.last_save > 60:
            self.save_state()
            self.last_save = now
        if int(self.t) != int(self.t - dt_real):
            self.update_tooltip()
        self.update()
        if self.bubble.isVisible():
            self.bubble.update()
        if self.shop.isVisible():
            self.shop.update()
        if self.garden.isVisible() and self.ps["growth"] >= self.kind.bloom_at:
            self.garden.update(self.garden.button_rect().adjusted(-6, -6, 6, 6).toRect())
        if self.focus_win.isVisible():
            self.focus_win.update()
        if self.book_win.isVisible():
            self.book_win.update()

    def water_click(self, pos):
        s, k = self.ps, self.kind
        if self.greet_visitor(pos):
            return
        s["clicks_total"] += 1
        self.ensure_periods()
        self.state["stats"]["clicks"] = self.state["stats"].get("clicks", 0) + 1
        self.state["daily"]["clicks"] += 1
        self.add_growth(k.growth_per_click * self.growth_mult())
        if s["water"] >= WATER_MAX - 0.01:
            # Wasser voll: nicht giessen, stattdessen Wachstumspartikel an der Pflanze
            tp = self.top_point
            for _ in range(4):
                if len(self.sparkles) < 24:
                    self.sparkles.append([tp.x() + random.uniform(-22, 22),
                                          tp.y() + random.uniform(-8, 24), 1.0])
        else:
            s["water"] = min(WATER_MAX, s["water"] + k.water_per_click)
            self.sound.play("giessen")
            y0 = min(pos.y(), self.pot["soil_y"] - 30)
            for _ in range(3):
                self.drops.append([pos.x() + random.uniform(-8, 8),
                                   y0 - random.uniform(0, 12), random.uniform(0, 1)])
        self.update_tooltip()

    def update_particles(self, dt):
        f = dt * 20
        for d in self.drops:
            d[2] += 0.5 * f
            d[1] += d[2] * f
        self.drops = [d for d in self.drops if d[1] < self.pot["soil_y"]]
        for sp in self.sparkles:
            sp[1] -= 0.6 * f
            sp[2] -= 0.03 * f
        self.sparkles = [sp for sp in self.sparkles if sp[2] > 0]
        for pu in self.popups:
            pu[1] -= 0.45 * f
            pu[2] -= 0.012 * f
        self.popups = [pu for pu in self.popups if pu[2] > 0]
        self.release_popups()

    # ---------- Maus ----------

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.press_pos = e.position()
            self.dragging = False
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.set_bubble(not self.state.get("bubble", True))
        elif e.button() == Qt.MouseButton.RightButton:
            self.show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if (self.press_pos is not None and not self.dragging
                and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position() - self.press_pos).manhattanLength() > 6):
            self.dragging = True
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.press_pos is not None:
            if not self.dragging:
                pos = e.position()
                self.water_click(QPointF(pos.x(), pos.y() - SCENE_DY))
            self.press_pos = None
            self.dragging = False

    # ---------- Menü ----------

    @staticmethod
    def slider_action(parent, title, vmin, vmax, value, on_change, reset_value, reset_label, snap=1,
                      on_release=None):
        """Regler mit Beschriftung «Titel: Wert %» und Zurücksetzen-Knopf für das Einstellungsmenü."""
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 4, 12, 4)
        label = QLabel()
        label.setMinimumWidth(132)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(vmin, vmax)
        slider.setSingleStep(snap)
        slider.setPageStep(max(snap, 10))
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(25)
        slider.setMinimumWidth(150)
        reset = QPushButton(reset_label)
        reset.setFlat(True)

        def show(v):
            label.setText(f"{title}: {v} %")

        def change(v):
            v = int(round(v / float(snap))) * snap
            show(v)
            on_change(v)

        slider.setValue(value)
        show(slider.value())
        slider.valueChanged.connect(change)
        if on_release:
            slider.sliderReleased.connect(on_release)
        reset.clicked.connect(lambda: slider.setValue(reset_value))
        for wdg in (label, slider, reset):
            lay.addWidget(wdg)
        act = QWidgetAction(parent)
        act.setDefaultWidget(box)
        return act

    def scale_slider_action(self, parent, kind="plant", title=tr("Pflanzengrösse")):
        """Regler (50 bis 200 %) für das Einstellungsmenü; kind: «plant» oder «menu»."""
        return self.slider_action(parent, title, int(scaling.SCALE_MIN * 100), int(scaling.SCALE_MAX * 100),
                                  int(round(scaling.get_scale(kind) * 100)),
                                  lambda v: self.set_ui_scale(v / 100.0, kind), 100, "100 %", snap=5)

    def set_volume(self, value):
        """Gesamtlautstärke aller Töne (0–100) setzen und speichern."""
        self.state["volume"] = max(0, min(100, int(value)))
        self.sound.set_volume(self.state["volume"])
        self.save_state()

    def volume_slider_action(self, parent):
        """Regler «Lautstärke» (0–100 %); beim Loslassen ertönt zur Probe der Giesssound."""
        return self.slider_action(parent, tr("Lautstärke"), 0, 100, self.state.get("volume", sound.DEFAULT_VOLUME),
                                  self.set_volume, sound.DEFAULT_VOLUME, f"{sound.DEFAULT_VOLUME} %", snap=1,
                                  on_release=lambda: self.sound.play("giessen"))

    @staticmethod
    def restart_command():
        """Programm und Argumente, um das Spiel neu zu starten (auch als gepackte Anwendung)."""
        if getattr(sys, "frozen", False):
            return sys.executable, sys.argv[1:]
        return sys.executable, ["-m", "topfpflanze", *sys.argv[1:]]

    def choose_language(self, code):
        """Speichert die Sprache und startet das Spiel neu (die Texte werden beim Start geladen)."""
        if code == i18n.language() and self.state.get("language") == code:
            return
        self.state["language"] = code
        self.save_state()
        if code == i18n.language():
            return
        from PyQt6.QtCore import QProcess
        program, args = self.restart_command()
        app = QApplication.instance()
        # Der Start erfolgt erst nach dem Speichern beim Beenden (aboutToQuit), damit der Spielstand nicht kollidiert
        app.aboutToQuit.connect(lambda: QProcess.startDetached(program, args))
        app.quit()

    def show_menu(self, global_pos):
        m = QMenu(self)
        sub = m.addMenu(tr("Pflanze wählen"))
        group = QActionGroup(sub)
        group.setExclusive(True)
        for key in PLANT_ORDER:
            k = PLANT_TYPES[key]
            label = f"{k.name}  ({k.difficulty})"
            pst = self.state["plants"].get(key)
            if pst:
                label += f"  –  {stage_name(k, pst['growth'])}"
            a = sub.addAction(label)
            a.setCheckable(True)
            a.setChecked(key == self.state["current"])
            a.setData(key)
            group.addAction(a)

        m.addSeparator()
        win_menu = m.addMenu(tr("Fenster"))
        a_bubble = win_menu.addAction(tr("Status-Sprechblase (Mittelklick)"))
        a_bubble.setCheckable(True)
        a_bubble.setChecked(self.state.get("bubble", True))
        win_menu.addSeparator()
        win_actions = {}
        for key in TOOL_ORDER:
            a = win_menu.addAction(TOOL_NAMES[key])
            a.setCheckable(True)
            a.setChecked(self.windows[key].isVisible())
            win_actions[a] = key
        set_menu = m.addMenu(tr("Einstellungen"))
        a_kb = set_menu.addAction(tr("Tastaturanschläge zählen"))
        a_kb.setCheckable(True)
        a_kb.setChecked(self.state.get("keyboard_enabled", True))
        if not self.key_source:
            a_kb.setText(tr("Tastaturanschläge zählen (nicht verfügbar)"))
            a_kb.setEnabled(False)
        set_menu.addAction(self.scale_slider_action(set_menu, "plant", tr("Pflanzengrösse")))
        set_menu.addAction(self.scale_slider_action(set_menu, "menu", tr("Menügrösse")))
        set_menu.addAction(self.volume_slider_action(set_menu))
        lang_menu = set_menu.addMenu("Sprache / Language")
        lang_group = QActionGroup(lang_menu)
        lang_group.setExclusive(True)
        lang_actions = {}
        for code, name in i18n.LANGUAGES.items():
            a = lang_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked(code == i18n.language())
            lang_group.addAction(a)
            lang_actions[a] = code
        a_dark = set_menu.addAction(tr("Dunkelmodus"))
        a_dark.setCheckable(True)
        a_dark.setChecked(self.state.get("dark", False))
        a_top = set_menu.addAction(tr("Immer im Vordergrund"))
        a_top.setCheckable(True)
        a_top.setChecked(self.state.get("on_top", True))
        m.addSeparator()
        debug.build_menu(self, m)
        a_focus = m.addAction(tr("Fokus abbrechen")) if self.focus else None
        a_status = m.addAction(tr("Status anzeigen"))
        a_reset = m.addAction(tr("«{v}» einlagern & neu aussäen …", v=self.kind.name))
        m.addSeparator()
        a_quit = m.addAction(tr("Beenden"))

        chosen = m.exec(global_pos)
        if chosen is None:
            return
        if chosen.data() in PLANT_TYPES:
            self.select_plant(chosen.data())
        elif chosen in win_actions:
            self.toggle_window(win_actions[chosen])
        elif a_focus is not None and chosen is a_focus:
            self.abort_focus()
        elif chosen is a_status:
            self.show_status()
        elif chosen is a_bubble:
            self.set_bubble(a_bubble.isChecked())
        elif chosen in lang_actions:
            self.choose_language(lang_actions[chosen])
        elif chosen is a_dark:
            self.set_dark(a_dark.isChecked())
        elif chosen is a_kb:
            self.state["keyboard_enabled"] = a_kb.isChecked()
        elif chosen is a_top:
            self.state["on_top"] = a_top.isChecked()
            self.apply_flags()
            self.show()
            self.bubble.apply_flags()
            self.bubble.setVisible(self.state.get("bubble", True) and not self.focus_mode_active)
            for win in self.windows.values():
                visible = win.isVisible()
                win.apply_flags()
                win.setVisible(visible)
        elif chosen is a_reset:
            self.reset_plant()
        elif chosen is a_quit:
            QApplication.quit()

    def show_status(self):
        s, k = self.ps, self.kind
        days = (time.time() - s["created"]) / 86400
        src = {"evdev": "evdev (/dev/input)", "pynput": "pynput"}.get(
            self.key_source, tr("nicht verfügbar"))
        keys = fmt_int(s["keys_total"]) if k.growth_per_key > 0 else tr("zählen bei dieser Pflanze nicht")
        QMessageBox.information(
            self, "Topfpflanze",
            tr("Pflanze: {v} (Schwierigkeit: {difficulty})\n", v=k.name, difficulty=k.difficulty)
            + (tr("Hinweis: {note}\n", note=k.note) if k.note else "")
            + tr("Stadium: {growth}\nWachstum: {growth2:.1f} (Blüte ab {bloom_at})\nWasser: {water:.0f} % (leer nach ca. {drain_hours:g} h)\nKlicks gesamt: {clicks_total}\nTastendrücke gesamt: {v}\nDünger: {fert_summary}\nPrestige: {prestige_summary}\nHelfer: {v2}\nAlter: {days:.1f} Tage\nGold: {coins}\nTastaturquelle: {src}\nSpeicherort: {config}", growth=stage_name(k, s['growth']), growth2=s['growth'], bloom_at=fmt_int(k.bloom_at), water=s['water'], drain_hours=k.drain_hours, clicks_total=fmt_int(s['clicks_total']), v=keys, fert_summary=self.fert_summary(), prestige_summary=self.prestige_summary(), v2=', '.join(HELPERS[h].name for h in HELPER_ORDER if self.helper_on(h)) or '–', days=days, coins=fmt_int(self.state.get('coins', 0)), src=src, config=config.STATE_FILE))

    def reset_plant(self):
        """Öffnet den Dialog «Einlagern & neu aussäen» (Topfwahl und Bestätigung)."""
        self.sow_win.open_dialog()

    def pot_offer(self):
        """Angebot an Töpfen für die nächste Neuaussaat dieser Pflanze: ein günstiges und ein edles Design aus
        dem Katalog (pots.py). Bleibt bis zur Aussaat gleich, danach wird neu ausgewählt."""
        key = self.state["current"]
        offers = self.state.get("pot_offer")
        if not isinstance(offers, dict) or "cheap" in offers:  # leer oder alte Form
            offers = self.state["pot_offer"] = {}
        offer = offers.get(key)
        if not (isinstance(offer, dict) and all(pots.design(offer.get(t)) for t in ("cheap", "premium"))):
            current = pots.design(self.ps.get("pot_skin"))
            offer = offers[key] = pots.new_offer(self.kind.pot, exclude=current["id"] if current else None)
        return offer

    def sow_choices(self):
        """Wählbare Töpfe: Originaltopf (gratis), ein günstiges und ein edles Design."""
        offer = self.pot_offer()
        out = [{"id": "orig", "name": tr("Originaltopf"), "price": 0, "skin": None, "tier": "orig"}]
        for tier in ("cheap", "premium"):
            d = pots.design(offer[tier])
            out.append({"id": tier, "name": d["name"], "price": d["price"], "skin": d["id"], "tier": tier})
        return out

    def confirm_sow(self, choice_id="orig"):
        """Lagert die Pflanze ins Gartenhaus ein und sät neu aus, im gewählten Topf. Gibt False zurück,
        wenn das Gold nicht reicht."""
        choice = next((c for c in self.sow_choices() if c["id"] == choice_id), None)
        if choice is None or self.state.get("coins", 0) < choice["price"]:
            return False
        key = self.state["current"]
        bloomed = self.prestige_ready()
        lvl = self.prestige_level(key)
        self.state["coins"] = self.state.get("coins", 0) - choice["price"]
        entry = {k: self.ps.get(k) for k in ("seed", "color", "growth", "clicks_total", "keys_total",
                                              "created", "bloomed_at", "pot_skin")}
        entry["key"] = key
        entry["archived_at"] = time.time()
        entry["prestige"] = lvl + 1 if bloomed else None
        self.state.setdefault("garden", []).append(entry)
        if bloomed:
            self.state.setdefault("prestige", {})[key] = lvl + 1
        new_state = self.new_plant_state(key)
        new_state["pot_skin"] = choice["skin"]
        self.state["plants"][key] = new_state
        offers = self.state.get("pot_offer")
        if isinstance(offers, dict):
            offers.pop(key, None)  # nächstes Mal wird neu ausgewählt
        del self.ps
        self.activate(key)
        if choice["skin"]:
            self.popup(tr("Neuer Topf: {choice}", choice=choice['name']), coin=False)
        self.save_state()
        self.update_tooltip()
        self.bubble.update()
        self.garden.update()
        self.shop.update()
        return True
