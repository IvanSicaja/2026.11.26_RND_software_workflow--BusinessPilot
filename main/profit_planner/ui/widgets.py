"""Small reusable widgets: KPI cards, price breakdown bar, money formatting."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


def money(v, cur: str = "", decimals: int = 2) -> str:
    if v is None:
        return "-"
    s = f"{v:,.{decimals}f}".replace(",", "'")
    return f"{s} {cur}".strip()


def pct(v) -> str:
    return "-" if v is None else f"{v:.1f} %"


class KpiCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        self.t = QLabel(title)
        self.t.setObjectName("kpiTitle")
        self.v = QLabel("-")
        self.v.setObjectName("kpiValue")
        self.s = QLabel("")
        self.s.setObjectName("kpiSub")
        for w in (self.t, self.v, self.s):
            lay.addWidget(w)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set(self, value: str, sub: str = "", state: str = ""):
        self.v.setText(value)
        self.s.setText(sub)
        self.v.setProperty("state", state)
        self.v.style().unpolish(self.v)
        self.v.style().polish(self.v)


SEGMENT_COLORS = {
    "Net to owner": "#2E7D32",
    "Taxes": "#8E24AA",
    "VAT": "#9E9E9E",
    "Production": "#1565C0",
    "Shipping & customs": "#EF6C00",
    "Fees & returns": "#F9A825",
    "Loss": "#C62828",
}


class BreakdownBar(QWidget):
    """Horizontal bar: where every unit of the gross price goes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments: list[tuple[str, float]] = []
        self.total = 0.0
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_result(self, r):
        if r is None or not r.ok or r.gross_price <= 0:
            self.segments, self.total = [], 0.0
        else:
            segs = [
                ("VAT", r.vat),
                ("Production", r.production_cost),
                ("Shipping & customs", r.shipping + r.customs),
                ("Fees & returns", r.payment_fee + r.commission + r.returns),
                ("Taxes", r.social + r.profit_tax + r.distribution_tax),
                ("Net to owner", max(r.net_to_owner, 0.0)),
            ]
            self.segments = [(n, v) for n, v in segs if v > 0.005]
            self.total = sum(v for _n, v in self.segments)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        bar_h = 22
        if not self.segments or self.total <= 0:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignCenter, "No breakdown available")
            return
        x = 0.0
        f = QFont(self.font())
        f.setPointSizeF(max(f.pointSizeF() - 1, 7))
        p.setFont(f)
        for name, v in self.segments:
            seg_w = w * v / self.total
            p.fillRect(QRectF(x, 0, seg_w, bar_h), QColor(SEGMENT_COLORS[name]))
            if seg_w > 46:
                p.setPen(QPen(QColor("white")))
                p.drawText(QRectF(x, 0, seg_w, bar_h), Qt.AlignCenter, f"{v / self.total * 100:.0f}%")
            x += seg_w
        # legend
        lx, ly = 0, bar_h + 8
        for name, v in self.segments:
            p.fillRect(QRectF(lx, ly + 3, 10, 10), QColor(SEGMENT_COLORS[name]))
            p.setPen(QColor(self.palette().windowText().color()))
            text = f"{name} {v / self.total * 100:.1f}%"
            tw = p.fontMetrics().horizontalAdvance(text)
            if lx + tw + 30 > w:
                lx, ly = 0, ly + 18
                p.fillRect(QRectF(lx, ly + 3, 10, 10), QColor(SEGMENT_COLORS[name]))
            p.drawText(int(lx + 14), int(ly + 12), text)
            lx += tw + 30
        needed = int(ly + 22)
        if self.minimumHeight() != needed:
            self.setMinimumHeight(needed)
