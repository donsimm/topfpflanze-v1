"""Pflanzenfenster: Spielzustand, Logik, Eingaben, Menü."""

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

from . import config, debug, scaling
from .bubble import Bubble
from .config import MILESTONE_COINS, MILESTONE_STEP, PASSIVE_PER_HOUR, SCENE_DY, SEED_FRAC, STAGE_COINS, TOOL_NAMES, TOOL_ORDER, WATER_MAX, WIN_H, WIN_W
from .data import ACHIEVEMENTS, BEE_BOOST, BEE_INTERVAL, DRIP_MIN, DRIP_RATE, FERTILIZERS, FOCUS_MULT, FOCUS_PRESETS, GNOME_INTERVAL, HELPERS, HELPER_ORDER, LAMP_BOOST, PLANT_ORDER, PLANT_TYPES, POTS, PRESTIGE_BONUS, STAGE_FRACTIONS, VISITORS, VISITOR_ORDER, VISIT_DURATION, VISIT_GREET_COINS
from .garden import Garden
from .keys import KeyCounter
from .panels import AchievementsWin, BookWin, FocusWin
from .plant_draw import PlantDrawMixin
from .scaling import ScaledWidget
from .shop import Shop
from .theme import _THEME
from .util import fmt_int, fmt_left, round_half_up, stage_index, stage_name


class Plant(PlantDrawMixin, ScaledWidget):
    KIND = "plant"

    def __init__(self):
        super().__init__()
        self.state = self.load_state()
        scaling.set_scale(self.state.get("ui_scale", 1.0), "plant")
        scaling.set_scale(self.state.get("menu_scale", 1.0), "menu")
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
        self.windows = {"shop": self.shop, "garden": self.garden, "ach": self.ach_win,
                        "focus": self.focus_win, "book": self.book_win}

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
                 "stage_rewarded": 0, "milestone_rewarded": 0, "fert": None, "bloomed_at": None}
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
                "book": {}, "focus_minutes": FOCUS_PRESETS[0]}

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
            for win in (self.ach_win, self.focus_win, self.book_win):
                self.state[win.pos_key] = [win.x(), win.y()]
        try:
            config.STATE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = config.STATE_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            os.replace(tmp, config.STATE_FILE)
        except OSError as e:
            print(f"Speichern fehlgeschlagen: {e}", file=sys.stderr)

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

    def clamp_windows_to_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        g = screen.availableGeometry()
        for w in [self, self.bubble, *self.windows.values()]:
            x = max(g.left(), min(w.x(), g.right() - w.real_width() + 1))
            y = max(g.top(), min(w.y(), g.bottom() - w.real_height() + 1))
            if (x, y) != (w.x(), w.y()):
                w.move(x, y)

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
        self.tip_text = (f"{k.name} · {stage_name(k, s['growth'])}\n"
                         f"Wachstum {s['growth']:.0f} · Wasser {s['water']:.0f} %")

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
        if self.helper_on("lampe"):
            m *= 1.0 + LAMP_BOOST
        if self.focus:
            m *= FOCUS_MULT
        return m

    def prestige_level(self, key=None):
        return self.state.get("prestige", {}).get(key or self.state["current"], 0)

    def prestige_summary(self):
        lvl = self.prestige_level()
        return f"Stufe {lvl} · +{lvl * PRESTIGE_BONUS * 100:.0f} %" if lvl else "–"

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
        return {
            "d_keys": d.get("keys", 0), "d_clicks": d.get("clicks", 0), "d_focus": d.get("focus", 0),
            "w_keys": w.get("keys", 0), "w_growth": int(w.get("growth", 0)), "w_focus": w.get("focus", 0),
            "g_bloom": len(st["bloomed_species"]), "g_garden": len(st["garden"]),
            "g_prestige": max(st["prestige"].values(), default=0), "g_species": len(st["bloomed_species"]),
            "g_keys": st["stats"]["keys"], "g_visitors": len(st["book"]),
        }[key]

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
        return f"{done} von {len(ACHIEVEMENTS)} erreicht"

    def check_achievements(self):
        """Merkt erreichte Erfolge zur Abholung vor; die Coins gibt es erst beim Einlösen."""
        self.ensure_periods()
        pending = self.state.setdefault("ach_pending", [])
        for a in ACHIEVEMENTS:
            done = self.ach_done_list(a.period)
            if a.key not in done and self.ach_value(a.key) >= a.target:
                done.append(a.key)
                pending.append({"key": a.key, "name": a.name, "reward": a.reward,
                                "period": a.period, "pid": self.ach_pid(a.period)})
                self.popup(f"Erfolg: {a.name}", coin=False)
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
                if e.get("pid", "") != self.ach_pid(e.get("period", "general"))]

    def ach_pending_total(self):
        return sum(e["reward"] for e in self.state.get("ach_pending", []))

    def claim_achievement(self, entry):
        """Löst einen einzelnen vorgemerkten Erfolg ein; gibt die Coins zurück."""
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
            self.popup(f"+{fmt_int(total)} Erfolge")
            self.save_state()
            self.bubble.update()
            self.shop.update()
            self.ach_win.refresh()
        return total

    # ---------- Helfer ----------

    def helper_on(self, key):
        return key in self.state.get("helpers", []) and key not in self.state.get("helpers_off", [])

    def helper_action(self, key):
        hp = HELPERS[key]
        owned, off = self.state.setdefault("helpers", []), self.state.setdefault("helpers_off", [])
        if key in owned:
            if key in off:
                off.remove(key)
                msg = f"{hp.name} ist wieder eingeschaltet."
            else:
                off.append(key)
                msg = f"{hp.name} ist ausgeschaltet."
            self.save_state()
            return True, msg
        coins = self.state.get("coins", 0)
        if coins < hp.price:
            return False, f"Zu wenig Coins für {hp.name}: es fehlen {fmt_int(hp.price - coins)}."
        self.state["coins"] = coins - hp.price
        owned.append(key)
        self.save_state()
        return True, f"{hp.name} gekauft und aktiv."

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
                self.popup("Hummel: Wachstum!", coin=False)
        self.bee_anim = max(0.0, self.bee_anim - dt)
        if self.helper_on("zwerg"):
            self.gnome_acc += dt
            if self.gnome_acc >= GNOME_INTERVAL:
                self.gnome_acc -= GNOME_INTERVAL
                self.add_growth(k.growth_per_click * self.growth_mult())
                self.gnome_hop = 1.0
        self.gnome_hop = max(0.0, self.gnome_hop - dt * 2)

    # ---------- Fokus-Timer ----------

    def start_focus(self, minutes):
        now = time.monotonic()
        self.focus = {"minutes": minutes, "start": now, "end": now + minutes * 60}
        self.focus_msg = ("", True, 0.0)
        self.popup(f"Fokus: {minutes} min", coin=False)

    def abort_focus(self):
        self.focus = None
        self.focus_msg = ("abgebrochen, kein Bonus", False, time.monotonic() + 30)

    def focus_remaining(self):
        rem = max(0.0, self.focus["end"] - time.monotonic())
        return rem, self.focus["minutes"] * 60

    def focus_message(self):
        text, ok, until = self.focus_msg
        return (text, ok) if time.monotonic() < until else ("", True)

    def focus_summary(self):
        if not self.focus:
            return "bereit"
        rem, _ = self.focus_remaining()
        m, sec = divmod(int(rem), 60)
        return f"läuft, noch {m:02d}:{sec:02d}"

    def run_focus(self):
        if self.focus and time.monotonic() >= self.focus["end"]:
            minutes = self.focus["minutes"]
            self.focus = None
            reward = minutes // 5
            self.ensure_periods()
            for bucket in (self.state["daily"], self.state["weekly"]):
                bucket["focus"] = bucket.get("focus", 0) + 1
            self.state["daily"]["focus_min"] = self.state["daily"].get("focus_min", 0) + minutes
            self.state["coins"] = self.state.get("coins", 0) + reward
            self.focus_msg = (f"geschafft! +{reward} Coins", True, time.monotonic() + 120)
            self.popup(f"+{reward} Fokus geschafft")
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

    def spawn_visitor(self, key=None):
        cands = self.visitor_candidates()
        if key:
            v = VISITORS[key]
        elif cands:
            v = random.choices(cands, weights=[c.weight for c in cands])[0]
        else:
            return
        self.visitor = {"key": v.key, "start": self.t, "dur": VISIT_DURATION,
                        "phase": random.uniform(0, 6.28), "side": random.choice((-1, 1))}
        book = self.state.setdefault("book", {})
        entry = book.setdefault(v.key, {"count": 0, "first": time.time()})
        entry["count"] += 1
        if entry["count"] == 1:
            self.popup(f"Neu: {v.name}!", coin=False)
            self.save_state()

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
        if (vp - pos).manhattanLength() > 22:
            return False
        name = VISITORS[self.visitor["key"]].name
        self.state["coins"] = self.state.get("coins", 0) + VISIT_GREET_COINS
        self.popup(f"+{VISIT_GREET_COINS} Hallo, {name}!")
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
            return False, f"Zu wenig Coins für {fz.name}: es fehlen {fmt_int(fz.price - coins)}."
        self.state["coins"] = coins - fz.price
        self.ps["last_fert"] = key
        cur, left = self.fert()
        if cur and cur.key == key:
            self.ps["fert"]["left"] = left + fz.minutes * 60
            msg = f"{fz.name} verlängert: wirkt noch {fmt_left(self.ps['fert']['left'])} auf {self.kind.name}."
        else:
            self.ps["fert"] = {"key": key, "left": fz.minutes * 60}
            msg = f"{fz.name} wirkt jetzt auf {self.kind.name}"
            msg += f" (ersetzt {cur.name})." if cur else "."
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
                    self.popup(f"Automat: {FERTILIZERS[last].name}", coin=False)

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

    def scale_slider_action(self, parent, kind="plant", title="Pflanzengrösse"):
        """Regler (50 bis 200 %) für das Einstellungsmenü; kind: «plant» oder «menu»."""
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 4, 12, 4)
        label = QLabel()
        label.setMinimumWidth(132)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(scaling.SCALE_MIN * 100), int(scaling.SCALE_MAX * 100))
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(25)
        slider.setMinimumWidth(150)
        reset = QPushButton("100 %")
        reset.setFlat(True)

        def show(v):
            label.setText(f"{title}: {v} %")

        def change(v):
            v = int(round(v / 5.0)) * 5
            show(v)
            self.set_ui_scale(v / 100.0, kind)

        slider.setValue(int(round(scaling.get_scale(kind) * 100)))
        show(slider.value())
        slider.valueChanged.connect(change)
        reset.clicked.connect(lambda: slider.setValue(100))
        for wdg in (label, slider, reset):
            lay.addWidget(wdg)
        act = QWidgetAction(parent)
        act.setDefaultWidget(box)
        return act

    def show_menu(self, global_pos):
        m = QMenu(self)
        sub = m.addMenu("Pflanze wählen")
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
        win_menu = m.addMenu("Fenster")
        a_bubble = win_menu.addAction("Status-Sprechblase (Mittelklick)")
        a_bubble.setCheckable(True)
        a_bubble.setChecked(self.state.get("bubble", True))
        win_menu.addSeparator()
        win_actions = {}
        for key in TOOL_ORDER:
            a = win_menu.addAction(TOOL_NAMES[key])
            a.setCheckable(True)
            a.setChecked(self.windows[key].isVisible())
            win_actions[a] = key
        set_menu = m.addMenu("Einstellungen")
        a_kb = set_menu.addAction("Tastaturanschläge zählen")
        a_kb.setCheckable(True)
        a_kb.setChecked(self.state.get("keyboard_enabled", True))
        if not self.key_source:
            a_kb.setText("Tastaturanschläge zählen (nicht verfügbar)")
            a_kb.setEnabled(False)
        set_menu.addAction(self.scale_slider_action(set_menu, "plant", "Pflanzengrösse"))
        set_menu.addAction(self.scale_slider_action(set_menu, "menu", "Menügrösse"))
        a_dark = set_menu.addAction("Dunkelmodus")
        a_dark.setCheckable(True)
        a_dark.setChecked(self.state.get("dark", False))
        a_top = set_menu.addAction("Immer im Vordergrund")
        a_top.setCheckable(True)
        a_top.setChecked(self.state.get("on_top", True))
        m.addSeparator()
        debug.build_menu(self, m)
        a_status = m.addAction("Status anzeigen")
        a_reset = m.addAction(f"«{self.kind.name}» einlagern & neu aussäen …")
        m.addSeparator()
        a_quit = m.addAction("Beenden")

        chosen = m.exec(global_pos)
        if chosen is None:
            return
        if chosen.data() in PLANT_TYPES:
            self.select_plant(chosen.data())
        elif chosen in win_actions:
            self.toggle_window(win_actions[chosen])
        elif chosen is a_status:
            self.show_status()
        elif chosen is a_bubble:
            self.set_bubble(a_bubble.isChecked())
        elif chosen is a_dark:
            self.set_dark(a_dark.isChecked())
        elif chosen is a_kb:
            self.state["keyboard_enabled"] = a_kb.isChecked()
        elif chosen is a_top:
            self.state["on_top"] = a_top.isChecked()
            self.apply_flags()
            self.show()
            self.bubble.apply_flags()
            self.bubble.setVisible(self.state.get("bubble", True))
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
            self.key_source, "nicht verfügbar")
        keys = fmt_int(s["keys_total"]) if k.growth_per_key > 0 else "zählen bei dieser Pflanze nicht"
        QMessageBox.information(
            self, "Topfpflanze",
            f"Pflanze: {k.name} (Schwierigkeit: {k.difficulty})\n"
            + (f"Hinweis: {k.note}\n" if k.note else "")
            + f"Stadium: {stage_name(k, s['growth'])}\n"
            f"Wachstum: {s['growth']:.1f} (Blüte ab {fmt_int(k.bloom_at)})\n"
            f"Wasser: {s['water']:.0f} % (leer nach ca. {k.drain_hours:g} h)\n"
            f"Klicks gesamt: {fmt_int(s['clicks_total'])}\n"
            f"Tastendrücke gesamt: {keys}\n"
            f"Dünger: {self.fert_summary()}\n"
            f"Prestige: {self.prestige_summary()}\n"
            f"Helfer: {', '.join(HELPERS[h].name for h in HELPER_ORDER if self.helper_on(h)) or '–'}\n"
            f"Alter: {days:.1f} Tage\n"
            f"Coins: {fmt_int(self.state.get('coins', 0))}\n"
            f"Tastaturquelle: {src}\n"
            f"Speicherort: {config.STATE_FILE}")

    def reset_plant(self):
        name = self.kind.name
        key = self.state["current"]
        stage = stage_name(self.kind, self.ps["growth"])
        bloomed = self.ps["growth"] >= self.kind.bloom_at
        lvl = self.prestige_level(key)
        if bloomed:
            text = (f"«{name}» ist voll ausgewachsen: Prestige-Stufe {lvl} → {lvl + 1}.\n"
                    f"Dauerhaft +{(lvl + 1) * PRESTIGE_BONUS * 100:.0f} % Wachstum und Coins für alle "
                    f"künftigen {name}-Pflanzen.\n\nDie Pflanze kommt ins Gartenhaus und wird neu ausgesät "
                    f"(zufällige Farbe). Fortfahren?")
        else:
            text = (f"«{name}» ist noch nicht ausgewachsen (Stadium: {stage}).\n"
                    f"Sie kommt nur ins Gartenhaus, ohne Prestige-Stufe.\n\nDanach wird neu ausgesät "
                    f"(zufällige Farbe). Fortfahren?")
        answer = QMessageBox.question(self, "Einlagern & neu aussäen", text)
        if answer != QMessageBox.StandardButton.Yes:
            return
        entry = {k: self.ps.get(k) for k in ("seed", "color", "growth", "clicks_total", "keys_total",
                                              "created", "bloomed_at")}
        entry["key"] = key
        entry["archived_at"] = time.time()
        entry["prestige"] = lvl + 1 if bloomed else None
        self.state.setdefault("garden", []).append(entry)
        if bloomed:
            self.state.setdefault("prestige", {})[key] = lvl + 1
        self.state["plants"][key] = self.new_plant_state(key)
        del self.ps
        self.activate(key)
        self.save_state()
        self.update_tooltip()
        self.bubble.update()
        self.garden.update()
