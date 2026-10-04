"""Erzeugt die Bilder für die README (docs/*.png) ohne Bildschirm:  QT_QPA_PLATFORM=offscreen python scripts/make-screenshots.py"""

import datetime
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from topfpflanze import config, i18n  # noqa: E402

DOCS = pathlib.Path(__file__).resolve().parents[1] / "docs"
tmp = pathlib.Path(tempfile.mkdtemp())
config.STATE_DIR, config.STATE_FILE = tmp, tmp / "state.json"
i18n.set_language("de")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QColor, QPainter, QPixmap  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from topfpflanze.data import PLANT_TYPES  # noqa: E402
from topfpflanze.plant import Plant  # noqa: E402

BG = QColor("#8FB57A")
app = QApplication([])
plant = Plant()
plant.show()
plant.state["diary_spell"] = "off"
k = PLANT_TYPES["wiesenblume"]
plant.ps["growth"] = k.bloom_at * 1.02
plant.ps["water"] = 72.0
plant.state["coins"] = 1284
plant.state["stats"].update({"keys": 148_000, "clicks": 3_200, "purchases": 12, "focus": 14})
plant.state["book"] = {"marienkaefer": {"count": 120, "shiny": 1}, "biene": {"count": 60}, "kohlweissling": {"count": 14},
                       "zitronenfalter": {"count": 3}, "libelle": {"count": 1}}
plant.helper_action("tropf")
for day, text, mood in ((1, "x" * 120, 3), (2, "x" * 40, 1), (3, "x" * 90, 5), (7, "x" * 300, 4), (8, "x" * 80, 2),
                        (12, "x" * 15, 0), (15, "x" * 220, 3), (19, "x" * 90, 2), (23, "x" * 410, 4)):
    plant.diary.put(datetime.date(2026, 10, day), text, mood)
plant.check_achievements()
plant.bubble.show()
app.processEvents()


def compose(parts, name, gap=14, pad=14):
    w = sum(p.width() for p in parts) + gap * (len(parts) - 1) + 2 * pad
    h = max(p.height() for p in parts) + 2 * pad
    pm = QPixmap(w, h)
    pm.fill(BG)
    q = QPainter(pm)
    x = pad
    for part in parts:
        q.drawPixmap(x, pad + (h - 2 * pad - part.height()) // 2, part)
        x += part.width() + gap
    q.end()
    pm.save(str(DOCS / name))


def shot(win):
    win.show()
    app.processEvents()
    return win.grab()


plant.popups.clear()
plant.popup_queue.clear()
plant.shop.tab = "duenger"
compose([shot(plant), shot(plant.bubble), shot(plant.shop), shot(plant.focus_win)], "spiel.png")
day = datetime.date(2026, 10, 4)
plant.diary_win.show_month_of(day)
plant.diary_text.open_date(day)
plant.diary_text.editor.setPlainText(
    "Ruhiger Sonntag\n"
    "Heute war ein ruhiger Tag. Die Wiesenblume hat endlich geblüht, ein Marienkäfer war zu Besuch.\n\n"
    "45 Minuten konzentriert gearbeitet und danach im Garten gesessen.")
plant.diary_text.on_click(("m", 2))
compose([shot(plant.diary_win), shot(plant.diary_text)], "tagebuch.png")
compose([shot(plant.ach_win), shot(plant.book_win)], "erfolge-sammelbuch.png")
print("fertig:", ", ".join(sorted(p.name for p in DOCS.glob("*.png"))))
