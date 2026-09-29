"""Skalierung der Oberfläche mit zwei getrennten Reglern (0.5x bis 2x): «plant» für das
Pflanzenfenster (Pflanze mit Topf), «menu» für alle Menüfenster (Sprechblase, Shop, Gartenhaus, ...).

Alle Fenster rechnen in «logischen» Pixeln (wie bei 100 %). ScaledWidget legt die tatsächliche
Fenstergrösse fest, skaliert beim Zeichnen und rechnet Mauspositionen zurück.
"""

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from . import tooltip

SCALE_MIN, SCALE_MAX = 0.5, 2.0
_SCALE = {"plant": 1.0, "menu": 1.0}
_MOUSE = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
          QEvent.Type.MouseMove, QEvent.Type.MouseButtonDblClick)


def get_scale(kind="plant"):
    return _SCALE[kind]


def set_scale(v, kind="plant"):
    _SCALE[kind] = max(SCALE_MIN, min(SCALE_MAX, float(v)))
    return _SCALE[kind]


def _screen_size():
    screen = QApplication.primaryScreen()
    if not screen:
        return None
    g = screen.availableGeometry()
    return g.width(), g.height()


class ScaledWidget(QWidget):
    KIND = "menu"  # welcher Regler gilt: "plant" oder "menu"
    _lw = _lh = 0
    _k = 1.0

    def _fit(self):
        """Wirksamer Faktor: bei Vergrösserung nie grösser als der Bildschirm, nie unter 100 %."""
        k = get_scale(self.KIND)
        if k <= 1.0 or not self._lw:
            return k
        size = _screen_size()
        if size:
            k = min(k, size[0] * 0.98 / self._lw, size[1] * 0.96 / self._lh)
        return max(1.0, k)

    def setFixedSize(self, w, h):
        # Tooltips auch anzeigen, wenn das Fenster nicht aktiv ist (Desktop-Fenster ohne Fokus)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        self._lw, self._lh = w, h
        self.rescale()

    def rescale(self):
        self._k = self._fit()
        super().setFixedSize(int(round(self._lw * self._k)), int(round(self._lh * self._k)))
        self.update()

    def width(self):  # logische Breite/Höhe: der Zeichencode bleibt unverändert
        return self._lw or super().width()

    def height(self):
        return self._lh or super().height()

    def real_width(self):
        return QWidget.width(self)

    def real_height(self):
        return QWidget.height(self)

    def new_painter(self):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._k, self._k)
        return p

    def tooltip_at(self, pos):
        """Text für einen Tooltip an der (logischen) Position; leer = keiner. Unterklassen überschreiben das."""
        if hasattr(self, "close_rect") and self.close_rect().contains(pos):
            return "Schliessen"
        return ""

    def event(self, ev):
        t = ev.type()
        if t == QEvent.Type.ToolTip:
            text = self.tooltip_at(QPointF(ev.pos()) / self._k)
            if text:
                tooltip.show_tip(text, ev.globalPos())
            else:
                tooltip.hide_tip()
            return True
        if t in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.Hide, QEvent.Type.Wheel):
            tooltip.hide_tip()
        elif t == QEvent.Type.MouseMove and tooltip.current_text():
            if self.tooltip_at(QPointF(ev.position()) / self._k) != tooltip.current_text():
                tooltip.hide_tip()
        if self._k != 1.0 and t in _MOUSE and isinstance(ev, QMouseEvent):
            ev = QMouseEvent(ev.type(), ev.position() / self._k, ev.globalPosition(),
                             ev.button(), ev.buttons(), ev.modifiers())
        return super().event(ev)
