"""Debug-Modus zum schnellen Testen (Start mit --debug, siehe README).

Im Debug-Modus erscheint im Rechtsklick-Menü der Eintrag «Debug» und oben links
im Pflanzenfenster ein roter Hinweis. Ohne --data-dir wird ein eigener Spielstand
im Unterordner «debug» verwendet, der echte Spielstand bleibt unberührt.
"""


from PyQt6.QtGui import QActionGroup

import time

from .data import HELPER_ORDER, STAGE_FRACTIONS, VARIANTS, VISITOR_ORDER, VISITORS

DEBUG = {"on": False, "speed": 1.0}
SPEEDS = (1, 10, 60, 600)


def enabled():
    return DEBUG["on"]


def speed():
    """Zeitraffer-Faktor für Wasserverlust, Dünger, Helfer, Besucher, Fokus-Timer und passives Einkommen."""
    return DEBUG["speed"] if DEBUG["on"] else 1.0


def enable(spd=1.0):
    DEBUG["on"] = True
    DEBUG["speed"] = float(spd)


def _refresh(plant):
    plant.check_rewards()
    plant.check_achievements()
    plant.update_tooltip()
    plant.update()
    plant.bubble.update()


def _add_coins(plant, n):
    plant.state["coins"] = plant.state.get("coins", 0) + n
    _refresh(plant)


def _set_growth(plant, frac):
    plant.ps["growth"] = plant.kind.bloom_at * frac
    _refresh(plant)


def _set_water(plant, value):
    plant.ps["water"] = float(value)
    _refresh(plant)


def _add_activity(plant, keys=0, clicks=0):
    plant.ensure_periods()
    st = plant.state
    st["stats"]["keys"] = (st["stats"].get("keys") or 0) + keys
    for bucket in (st["daily"], st["weekly"]):
        bucket["keys"] = bucket.get("keys", 0) + keys
    st["daily"]["clicks"] = st["daily"].get("clicks", 0) + clicks
    _refresh(plant)


def _reset_periods(plant):
    plant.state["daily"] = {}
    plant.state["weekly"] = {}
    plant.ensure_periods()
    _refresh(plant)


def _add_visits(plant, n):
    """Erhöht den Besuchszähler aller Besucher (zum Testen der Meisterschaft)."""
    book = plant.state.setdefault("book", {})
    for key in VISITOR_ORDER:
        e = book.setdefault(key, {"count": 0, "first": time.time()})
        e["count"] += n
    _refresh(plant)


def _next_period(plant):
    """Simuliert Tages- und Wochenwechsel: laufende Zähler werden neu gestartet, offene Erfolge wandern in die Liste."""
    plant.state["daily"] = {"date": "1999-01-01"}
    plant.state["weekly"] = {"week": "1999-W01"}
    for e in plant.state.get("ach_pending", []):
        if e.get("period") == "daily":
            e["pid"] = "1999-01-01"
        elif e.get("period") == "weekly":
            e["pid"] = "1999-W01"
    plant.ensure_periods()
    _refresh(plant)


def _unlock_helpers(plant):
    plant.state["helpers"] = list(HELPER_ORDER)
    plant.state["helpers_off"] = []
    _refresh(plant)


def _prestige(plant):
    key = plant.state["current"]
    plant.state.setdefault("prestige", {})[key] = plant.prestige_level(key) + 1
    _refresh(plant)


def _set_speed(spd):
    DEBUG["speed"] = float(spd)


def _shift_focus(plant, dt_extra):
    """Der Fokus-Timer läuft auf der Systemuhr: bei Zeitraffer das Ende entsprechend vorziehen."""
    if plant.focus and dt_extra > 0:
        plant.focus["end"] -= dt_extra


def apply_time(plant, dt):
    """Skaliert das Zeitintervall des Ticks; gibt das beschleunigte dt zurück."""
    spd = speed()
    if spd != 1.0:
        _shift_focus(plant, dt * (spd - 1.0))
    return dt * spd


def build_menu(plant, menu):
    """Hängt das Untermenü «Debug» an das Rechtsklick-Menü."""
    if not DEBUG["on"]:
        return
    dm = menu.addMenu("Debug")

    sm = dm.addMenu(f"Zeitraffer (aktuell {DEBUG['speed']:g}x)")
    grp = QActionGroup(sm)
    for spd in SPEEDS:
        a = sm.addAction(f"{spd}x")
        a.setCheckable(True)
        a.setChecked(DEBUG["speed"] == spd)
        a.triggered.connect(lambda _c=False, s=spd: _set_speed(s))
        grp.addAction(a)

    dm.addAction("+1'000 Gold").triggered.connect(lambda: _add_coins(plant, 1000))

    gm = dm.addMenu("Wachstum setzen")
    k = plant.kind
    for frac, label in zip(STAGE_FRACTIONS, k.stages):
        if frac == 0.0:
            continue
        gm.addAction(f"{label} ({frac * 100:g} % des Blütewerts)").triggered.connect(
            lambda _c=False, f=frac: _set_growth(plant, f))
    gm.addAction("Blüte + 100 %").triggered.connect(lambda: _set_growth(plant, 2.0))

    wm = dm.addMenu("Wasser setzen")
    for v in (0, 10, 50, 100):
        wm.addAction(f"{v} %").triggered.connect(lambda _c=False, x=v: _set_water(plant, x))

    vm = dm.addMenu("Besucher erscheinen lassen")
    for key in VISITOR_ORDER:
        vm.addAction(VISITORS[key].name).triggered.connect(
            lambda _c=False, kk=key: (plant.spawn_visitor(kk), plant.update()))

    sm2 = dm.addMenu("Farbvariante erscheinen lassen")
    for key in VISITOR_ORDER:
        sm2.addAction(VARIANTS[key].name).triggered.connect(
            lambda _c=False, kk=key: (plant.spawn_visitor(kk, shiny=True), plant.update()))
    dm.addAction("+10 Besuche bei allen Besuchern").triggered.connect(lambda: _add_visits(plant, 10))
    dm.addAction("Fokus-Timer 1 Minute starten").triggered.connect(lambda: plant.start_focus(1))
    dm.addAction("+2'000 Tastendrücke gezählt").triggered.connect(lambda: _add_activity(plant, keys=2000))
    dm.addAction("+20 Klicks gezählt").triggered.connect(lambda: _add_activity(plant, clicks=20))
    dm.addAction("Tages-/Wochenerfolge zurücksetzen").triggered.connect(lambda: _reset_periods(plant))
    dm.addAction("Tag/Woche wechseln lassen (Erfolge)").triggered.connect(lambda: _next_period(plant))
    dm.addAction("Alle Helfer freischalten").triggered.connect(lambda: _unlock_helpers(plant))
    dm.addAction(f"Prestige-Stufe «{k.name}» +1").triggered.connect(lambda: _prestige(plant))
    dm.addAction("Spielstand jetzt speichern").triggered.connect(plant.save_state)


def paint_marker(p):
    """Roter Hinweis oben links im Pflanzenfenster."""
    from PyQt6.QtGui import QColor
    p.save()
    p.setPen(QColor("#D64541"))
    p.drawText(6, 14, f"DEBUG {DEBUG['speed']:g}x")
    p.restore()
