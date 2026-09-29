"""Skalierung der gesamten Oberfläche (Regler in den Einstellungen, 0.5x bis 2x).

Alle Fenster rechnen weiter in «logischen» Pixeln (wie bei 100 %). ScaledWidget legt die
tatsächliche Fenstergrösse fest, skaliert beim Zeichnen und rechnet Mauspositionen zurück.
"""

from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

SCALE_MIN, SCALE_MAX = 0.5, 2.0
_SCALE = {"v": 1.0}
_MOUSE = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
          QEvent.Type.MouseMove, QEvent.Type.MouseButtonDblClick)


def get_scale():
    return _SCALE["v"]


def set_scale(v):
    _SCALE["v"] = max(SCALE_MIN, min(SCALE_MAX, float(v)))
    return _SCALE["v"]


def S(n):
    """Logische Pixel in echte Pixel umrechnen (gerundet)."""
    return int(round(n * _SCALE["v"]))


def _screen_size():
    screen = QApplication.primaryScreen()
    if not screen:
        return None
    g = screen.availableGeometry()
    return g.width(), g.height()


class ScaledWidget(QWidget):
    _lw = _lh = 0
    _k = 1.0

    def _fit(self):
        """Wirksamer Faktor: bei Vergrösserung nie grösser als der Bildschirm, nie unter 100 %."""
        k = get_scale()
        if k <= 1.0 or not self._lw:
            return k
        size = _screen_size()
        if size:
            k = min(k, size[0] * 0.98 / self._lw, size[1] * 0.96 / self._lh)
        return max(1.0, k)

    def setFixedSize(self, w, h):
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

    def event(self, ev):
        if self._k != 1.0 and ev.type() in _MOUSE and isinstance(ev, QMouseEvent):
            ev = QMouseEvent(ev.type(), ev.position() / self._k, ev.globalPosition(),
                             ev.button(), ev.buttons(), ev.modifiers())
        return super().event(ev)
