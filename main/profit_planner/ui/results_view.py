"""Results dashboard: one row per configuration + detailed breakdown of the selected one."""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QLabel, QMessageBox, QPushButton, QSplitter,
                               QTableView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..calc import Result
from .table_model import SortProxy
from .widgets import BreakdownBar, KpiCard, money, pct

GOOD = QColor("#E3F4E4")
BAD = QColor("#FDE2E1")
WARN = QColor("#FFF6DA")

COLUMNS = [
    ("ID", "config_id", "text"), ("Name", "name", "text"), ("Product", "product_name", "text"),
    ("HQ", "hq", "text"), ("Legal form", "legal_form", "text"), ("Liability", "liability", "text"),
    ("Market", "market", "text"), ("Type", "sale_type", "text"),
    ("Gross price", "gross_price", "money"), ("VAT", "vat", "money"),
    ("Production", "production_cost", "money"), ("Shipping", "shipping", "money"),
    ("Customs", "customs", "money"), ("Fees+returns", "_fees", "money"),
    ("Profit before tax", "profit_before_tax", "money"), ("Taxes", "_taxes", "money"),
    ("NET TO OWNER", "net_to_owner", "money"), ("% of gross", "margin_pct", "pct"),
    ("Break-even price", "break_even_gross", "money"), ("Net per year", "annual_net_to_owner", "money"),
    ("Startup cash", "startup_total", "money"), ("Payback (months)", "payback_months", "num"),
    ("Status", "status", "text"),
]


def _value(r: Result, attr: str):
    if attr == "_fees":
        return r.payment_fee + r.commission + r.returns
    if attr == "_taxes":
        return r.social + r.profit_tax + r.distribution_tax
    return getattr(r, attr, None)


class ResultsModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.results: list[Result] = []
        self.best: set[str] = set()

    def set_results(self, results: list[Result]):
        self.beginResetModel()
        self.results = results
        best, count = {}, {}
        for r in results:
            if r.ok:
                count[r.product_id] = count.get(r.product_id, 0) + 1
                if r.product_id not in best or r.net_to_owner > best[r.product_id].net_to_owner:
                    best[r.product_id] = r
        self.best = {id(r) for pid, r in best.items() if count[pid] > 1}
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.results)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, s, o, role=Qt.DisplayRole):
        if o == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[s][0]
        if o == Qt.Horizontal and role == Qt.ToolTipRole:
            return {"NET TO OWNER": "What you keep per unit after every cost and tax (incl. dividend tax).",
                    "Startup cash": "Formation costs + max(min. share capital, tools + startup stock).",
                    "Break-even price": "Gross price (incl. VAT) at which profit before tax is 0.",
                    "% of gross": "Net to owner as a share of the gross price paid by the customer."
                    }.get(COLUMNS[s][0])
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self.results[index.row()]
        title, attr, kind = COLUMNS[index.column()]
        ok_val = r.ok or kind == "text"
        v = _value(r, attr) if ok_val else None
        if role == Qt.DisplayRole:
            if not r.ok and kind != "text":
                return ""
            if kind == "money":
                return money(v)
            if kind == "pct":
                return pct(v)
            if kind == "num":
                return "-" if v is None else f"{v:.1f}"
            return "" if v is None else str(v)
        if role == Qt.UserRole:
            if isinstance(v, (int, float)):
                return float(v)
            return "" if v is None else str(v).lower()
        if role == Qt.TextAlignmentRole:
            return int((Qt.AlignLeft if kind == "text" else Qt.AlignRight) | Qt.AlignVCenter)
        if role == Qt.BackgroundRole:
            if not r.ok:
                return QBrush(BAD)
            if attr == "net_to_owner":
                return QBrush(BAD if r.net_to_owner < 0 else (GOOD if id(r) in self.best else QColor(0, 0, 0, 0)))
            if id(r) in self.best:
                return QBrush(GOOD)
            if r.warnings and attr == "status":
                return QBrush(WARN)
        if role == Qt.FontRole and attr == "net_to_owner":
            f = QFont()
            f.setBold(True)
            return f
        if role == Qt.ToolTipRole:
            if not r.ok:
                return r.error
            if r.warnings:
                return "\n".join(r.warnings)
            if id(r) in self.best:
                return "Best configuration for this product"
        return None


class ResultsView(QWidget):
    open_configuration = Signal(str)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.c = controller
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)

        bar = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName("pageTitle")
        bar.addWidget(self.heading)
        bar.addStretch(1)
        bar.addWidget(QLabel("Product:"))
        self.product_filter = QComboBox()
        self.product_filter.setMinimumWidth(200)
        self.product_filter.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.product_filter)
        self.only_active = QCheckBox("Active only")
        self.only_active.setChecked(True)
        self.only_active.toggled.connect(self.refresh)
        bar.addWidget(self.only_active)
        self.btn_edit = QPushButton("Edit configuration")
        self.btn_edit.clicked.connect(self._edit)
        bar.addWidget(self.btn_edit)
        self.btn_export = QPushButton("Export to Excel...")
        self.btn_export.clicked.connect(self.export)
        bar.addWidget(self.btn_export)
        lay.addLayout(bar)

        hint = QLabel("One row per configuration, per product unit. Green = best net result for that product. "
                      "Select a row to see the full breakdown. Edit scenarios in the 'Configurations' tab.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        split = QSplitter(Qt.Vertical)
        self.model = ResultsModel(self)
        self.proxy = SortProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(-1, Qt.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._sized = False
        self.table.selectionModel().currentRowChanged.connect(self._show_current)
        self.table.doubleClicked.connect(lambda _i: self._edit())
        split.addWidget(self.table)

        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(0, 6, 0, 0)
        self.detail_title = QLabel("Select a configuration")
        self.detail_title.setObjectName("sectionTitle")
        dl.addWidget(self.detail_title)
        cards = QHBoxLayout()
        self.k_gross = KpiCard("Customer pays (gross)")
        self.k_net = KpiCard("Net to owner / unit")
        self.k_year = KpiCard("Net to owner / year")
        self.k_start = KpiCard("Startup cash required")
        self.k_liab = KpiCard("Company")
        for k in (self.k_gross, self.k_net, self.k_year, self.k_start, self.k_liab):
            cards.addWidget(k)
        dl.addLayout(cards)
        self.bar = BreakdownBar()
        dl.addWidget(self.bar)
        lower = QSplitter(Qt.Horizontal)
        self.lines = QTableWidget(0, 2)
        self.lines.setHorizontalHeaderLabels(["Price breakdown per unit", "Amount"])
        self._setup_small_table(self.lines)
        lower.addWidget(self.lines)
        self.side = QTableWidget(0, 2)
        self.side.setHorizontalHeaderLabels(["Startup capital & details", "Value"])
        self._setup_small_table(self.side)
        lower.addWidget(self.side)
        lower.setSizes([600, 450])
        dl.addWidget(lower, 1)
        split.addWidget(detail)
        split.setSizes([330, 470])
        lay.addWidget(split, 1)

        self.c.data_changed.connect(self.refresh)
        self.refresh()

    @staticmethod
    def _setup_small_table(t: QTableWidget):
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        t.verticalHeader().setDefaultSectionSize(22)

    def filtered_results(self) -> list[Result]:
        res = self.c.results
        active_ids = {str(r.get("Configuration ID")) for r in self.c.db["Configurations"].rows
                      if r.get("Active") is not False}
        if self.only_active.isChecked():
            res = [r for r in res if r.config_id in active_ids]
        pid = self.product_filter.currentData()
        if pid:
            res = [r for r in res if r.product_id == pid]
        return res

    def refresh(self):
        cur_id = self.current_result().config_id if self.current_result() else None
        # product filter options
        want = [("", "All products")] + [(str(r.get("Product ID")), str(r.get("Name") or r.get("Product ID")))
                                         for r in self.c.db["Products"].rows if r.get("Product ID")]
        have = [(self.product_filter.itemData(i), self.product_filter.itemText(i))
                for i in range(self.product_filter.count())]
        if want != have:
            sel = self.product_filter.currentData()
            self.product_filter.blockSignals(True)
            self.product_filter.clear()
            for k, t in want:
                self.product_filter.addItem(t, k)
            i = self.product_filter.findData(sel)
            self.product_filter.setCurrentIndex(max(i, 0))
            self.product_filter.blockSignals(False)
        self.heading.setText(f"Results per unit  ({self.c.db.reporting_currency})")
        self.model.set_results(self.filtered_results())
        if not self._sized and self.model.rowCount():
            self.table.resizeColumnsToContents()
            self._sized = True
        row = 0
        if cur_id:
            for i, r in enumerate(self.model.results):
                if r.config_id == cur_id:
                    row = i
                    break
        if self.model.rowCount():
            idx = self.proxy.mapFromSource(self.model.index(row, 0))
            self.table.setCurrentIndex(idx)
        else:
            self.show_result(None)

    def current_result(self) -> Result | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        s = self.proxy.mapToSource(idx)
        return self.model.results[s.row()] if s.row() < len(self.model.results) else None

    def _show_current(self, *_a):
        self.show_result(self.current_result())

    def show_result(self, r: Result | None):
        cur = self.c.db.reporting_currency
        self.lines.setRowCount(0)
        self.side.setRowCount(0)
        self.bar.set_result(r)
        if r is None:
            self.detail_title.setText("No configuration selected")
            for k in (self.k_gross, self.k_net, self.k_year, self.k_start, self.k_liab):
                k.set("-")
            return
        self.detail_title.setText(f"{r.config_id}  -  {r.name or r.product_name}")
        if not r.ok:
            self.k_gross.set("-")
            self.k_net.set("Error", r.error, "bad")
            self.k_year.set("-")
            self.k_start.set("-")
            self.k_liab.set("-")
            self._add(self.lines, "Cannot calculate", r.error, bold=True)
            return
        self.k_gross.set(money(r.gross_price, cur), f"VAT {r.vat_rate:g} % in {r.market}")
        self.k_net.set(money(r.net_to_owner, cur), f"{r.margin_pct:.1f} % of gross price",
                       "good" if r.net_to_owner > 0 else "bad")
        self.k_year.set(money(r.annual_net_to_owner, cur, 0), f"{r.annual_volume} units / year",
                        "good" if r.annual_net_to_owner > 0 else "bad")
        pb = f"payback {r.payback_months:.1f} months" if r.payback_months is not None else "no payback"
        self.k_start.set(money(r.startup_total, cur, 0), pb)
        self.k_liab.set(f"{r.legal_form} ({r.hq})", r.liability)

        for ln in r.lines:
            self._add(self.lines, ln.label, money(ln.amount, cur), bold=ln.group == "Result",
                      color={"Result": None, "Tax": "#6A1B9A", "Deduction": "#8D6E00",
                             "Cost": "#0D47A1"}.get(ln.group), note=ln.note)
        side = [
            ("Min. share capital", money(r.share_capital, cur)),
            ("Formation costs", money(r.formation_costs, cur)),
            ("Tools to buy", money(r.tools_cost, cur)),
            ("Startup material stock", money(r.stock_cost, cur)),
            ("STARTUP CASH REQUIRED", money(r.startup_total, cur)),
            ("", ""),
            ("Liability", r.liability),
            ("Break-even gross price", money(r.break_even_gross, cur)),
            ("Material prices of year", str(r.material_year)),
            ("Production cost / unit", money(r.production_cost, cur)),
        ]
        for a, b in side:
            self._add(self.side, a, b, bold=a.isupper())
        if r.material_lines:
            self._add(self.side, "", "")
            self._add(self.side, "MATERIALS PER UNIT (incl. waste)", "", bold=True)
            for name, qty, unit, cost in r.material_lines:
                self._add(self.side, f"{name}  -  {qty:.3g} {unit}", money(cost, cur))
        if r.warnings:
            self._add(self.side, "", "")
            self._add(self.side, "WARNINGS", "", bold=True)
            for w in r.warnings:
                self._add(self.side, w, "", color="#8D6E00")

    @staticmethod
    def _add(t: QTableWidget, a: str, b: str, bold=False, color=None, note=""):
        row = t.rowCount()
        t.insertRow(row)
        ia, ib = QTableWidgetItem(a), QTableWidgetItem(b)
        ib.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if note:
            ia.setToolTip(note)
        if bold:
            f = ia.font()
            f.setBold(True)
            ia.setFont(f)
            ib.setFont(f)
        if color:
            ia.setForeground(QColor(color))
        t.setItem(row, 0, ia)
        t.setItem(row, 1, ib)

    def _edit(self):
        r = self.current_result()
        if r:
            self.open_configuration.emit(r.config_id)

    def export(self, path: str | None = None):
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Export results", "ProfitPlanner_Results.xlsx",
                                                  "Excel (*.xlsx)")
        if not path:
            return False
        from ..reports import export_results
        try:
            export_results(self.c.db, self.c.results, path)
        except OSError as e:
            QMessageBox.warning(self, "Export failed", f"Could not write the file:\n{e}")
            return False
        self.c.status_changed.emit("info", f"Results exported to {path}")
        return True
