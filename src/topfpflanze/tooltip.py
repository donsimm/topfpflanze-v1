"""Eigene Tooltips im Stil der Spielfenster (hell/dunkel), statt der Systemfarben."""

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt6.QtGui import QFont, QFontMetricsF, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from .theme import T

PAD_X, PAD_Y, LINE_GAP = 9, 6, 2
TITLE_PX, BODY_PX = 12, 11
SHOW_MS = 12000  # automatisch ausblenden


class _Tip(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text = ""
        self.k = 1.0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def fonts(self):
        title = QFont(self.font())
        title.setPixelSize(TITLE_PX)
        title.setBold(True)
        body = QFont(self.font())
        body.setPixelSize(BODY_PX)
        return title, body

    def logical_size(self):
        title, body = self.fonts()
        lines = self.text.split("\n")
        w, h = 0.0, 2 * PAD_Y
        for i, line in enumerate(lines):
            fm = QFontMetricsF(title if i == 0 else body)
            w = max(w, fm.horizontalAdvance(line))
            h += fm.height() + (LINE_GAP if i else 0)
        return w + 2 * PAD_X, h

    def show_text(self, text, global_pos):
        from . import scaling
        self.text = text
        self.k = scaling.get_scale("menu")
        lw, lh = self.logical_size()
        self.setFixedSize(int(lw * self.k + 2), int(lh * self.k + 2))
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        x, y = global_pos.x() + 14, global_pos.y() + 20
        if screen:
            g = screen.availableGeometry()
            if x + self.width() > g.right():
                x = global_pos.x() - self.width() - 8
            if y + self.height() > g.bottom():
                y = global_pos.y() - self.height() - 10
            x, y = max(g.left(), x), max(g.top(), y)
        self.move(QPoint(int(x), int(y)))
        self.show()
        self.update()
        self.timer.start(SHOW_MS)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.k, self.k)
        lw, lh = self.logical_size()
        p.setPen(QPen(T("panel_border"), 1.0))
        c = T("panel")
        c.setAlpha(250)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(0.5, 0.5, lw, lh), 6, 6)
        title, body = self.fonts()
        y = PAD_Y
        for i, line in enumerate(self.text.split("\n")):
            f = title if i == 0 else body
            p.setFont(f)
            p.setPen(T("text") if i == 0 else T("text2"))
            h = QFontMetricsF(f).height()
            p.drawText(QRectF(PAD_X, y, lw - 2 * PAD_X, h),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
            y += h + LINE_GAP
        p.end()


_tip = None


def _alive():
    """Tooltip-Fenster, falls vorhanden und nicht schon von Qt zerstört."""
    global _tip
    if _tip is not None and sip.isdeleted(_tip):
        _tip = None
    return _tip


def _get():
    global _tip
    if _alive() is None:
        _tip = _Tip()
    return _tip


def show_tip(text, global_pos):
    _get().show_text(text, global_pos)


def hide_tip():
    tip = _alive()
    if tip is not None and tip.isVisible():
        tip.hide()


def current_text():
    """Text des sichtbaren Tooltips (leer, wenn keiner angezeigt wird)."""
    tip = _alive()
    return tip.text if tip is not None and tip.isVisible() else ""
