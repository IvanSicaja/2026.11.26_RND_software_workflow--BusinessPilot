"""'Where to found?' - compare every legal form in every HQ country for one product and market."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QRadioButton, QSpinBox,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .. import schema as S
from ..calc import Engine, Result
from .widgets import money

COLS = ["Rank", "HQ country", "Legal form", "Liability", "Startup cash", "Gross price", "Production",
        "Shipping + customs", "Taxes", "NET TO OWNER / unit", "% of gross", "Net per year",
        "Payback (months)", "Status"]


class ExplorerView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.c = controller
        self.results: list[tuple[dict, Result]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        t = QLabel("Where should I found my company?")
        t.setObjectName("pageTitle")
        lay.addWidget(t)
        h = QLabel("Pick a product and a market. The app calculates the same sale for every legal form in every "
                   "selected HQ country and ranks them by what you keep. Nothing is saved unless you click "
                   "'Save as configuration'.")
        h.setObjectName("hint")
        h.setWordWrap(True)
        lay.addWidget(h)

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        box = QGroupBox("Scenario")
        form = QFormLayout(box)
        self.product = QComboBox()
        self.market = QComboBox()
        self.sale_type = QComboBox()
        self.sale_type.addItems(list(S.SALE_TYPES))
        self.payment = QComboBox()
        self.year = QComboBox()
        self.mode_fixed = QRadioButton("Fixed gross price")
        self.mode_markup = QRadioButton("Markup on cost")
        self.mode_fixed.setChecked(True)
        self.price = QDoubleSpinBox()
        self.price.setRange(0, 1e9)
        self.price.setDecimals(2)
        self.price.setValue(2290)
        self.price_cur = QComboBox()
        self.markup = QDoubleSpinBox()
        self.markup.setRange(-100, 10000)
        self.markup.setSuffix(" %")
        self.markup.setValue(60)
        self.volume = QSpinBox()
        self.volume.setRange(1, 10_000_000)
        self.volume.setValue(120)
        self.stock = QSpinBox()
        self.stock.setRange(0, 1_000_000)
        self.stock.setValue(10)
        self.commission = QDoubleSpinBox()
        self.commission.setRange(0, 100)
        self.commission.setSuffix(" %")
        self.sbe = QCheckBox("Small-business VAT exemption (domestic only)")
        form.addRow("Product", self.product)
        form.addRow("Market country", self.market)
        form.addRow("Sale type", self.sale_type)
        form.addRow("Payment method", self.payment)
        form.addRow("Material price year", self.year)
        modes = QHBoxLayout()
        modes.addWidget(self.mode_fixed)
        modes.addWidget(self.mode_markup)
        form.addRow("Pricing", modes)
        pr = QHBoxLayout()
        pr.addWidget(self.price, 1)
        pr.addWidget(self.price_cur)
        form.addRow("Gross price (incl. VAT)", pr)
        form.addRow("Markup", self.markup)
        form.addRow("Annual volume (units)", self.volume)
        form.addRow("Startup stock (units)", self.stock)
        form.addRow("Sales commission", self.commission)
        form.addRow("", self.sbe)
        ll.addWidget(box)
        hb = QGroupBox("HQ countries to compare")
        hl = QVBoxLayout(hb)
        self.hq_list = QListWidget()
        self.hq_list.setMaximumHeight(170)
        hl.addWidget(self.hq_list)
        ll.addWidget(hb)
        self.btn_run = QPushButton("Compare")
        self.btn_run.setObjectName("primaryButton")
        self.btn_run.clicked.connect(self.run)
        ll.addWidget(self.btn_run)
        ll.addStretch(1)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0)
        self.summary = QLabel("")
        self.summary.setObjectName("sectionTitle")
        self.summary.setWordWrap(True)
        rl.addWidget(self.summary)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        rl.addWidget(self.table, 1)
        bl = QHBoxLayout()
        bl.addStretch(1)
        self.btn_save = QPushButton("Save selected as configuration")
        self.btn_save.clicked.connect(self.save_selected)
        bl.addWidget(self.btn_save)
        rl.addLayout(bl)
        split.addWidget(right)
        split.setSizes([360, 900])
        lay.addWidget(split, 1)

        self.mode_fixed.toggled.connect(self._mode)
        self.market.currentIndexChanged.connect(self._market_changed)
        self._mode()
        self.c.structure_changed.connect(lambda _s: self.reload_options())
        self.c.data_changed.connect(self._maybe_reload)
        self.reload_options()

    # -- options ------------------------------------------------------------------
    def _mode(self):
        fixed = self.mode_fixed.isChecked()
        self.price.setEnabled(fixed)
        self.price_cur.setEnabled(fixed)
        self.markup.setEnabled(not fixed)

    def _market_changed(self):
        code = self.market.currentData()
        r = self.c.db[S.COUNTRIES].find(code)
        if r is not None and r.get("Currency"):
            i = self.price_cur.findData(str(r["Currency"]))
            if i >= 0:
                self.price_cur.setCurrentIndex(i)

    def _signature(self):
        db = self.c.db
        return (tuple(db[S.PRODUCTS].keys()), tuple(db[S.COUNTRIES].keys()), tuple(db[S.PAYMENT].keys()),
                tuple(db[S.FX].keys()), tuple(db.all_years()),
                tuple(sorted({str(r.get("Country Code")) for r in db[S.COMPANY_TYPES].rows})))

    def _maybe_reload(self):
        if self._signature() != getattr(self, "_sig", None):
            self.reload_options()

    @staticmethod
    def _fill(cb: QComboBox, items: list[tuple[str, str]], keep=True):
        cur = cb.currentData() if keep else None
        cb.blockSignals(True)
        cb.clear()
        for k, label in items:
            cb.addItem(label, k)
        i = cb.findData(cur)
        cb.setCurrentIndex(i if i >= 0 else 0)
        cb.blockSignals(False)

    def reload_options(self):
        db = self.c.db
        self._sig = self._signature()
        self._fill(self.product, [(str(r["Product ID"]), f"{r.get('Name') or ''} ({r['Product ID']})")
                                  for r in db[S.PRODUCTS].rows if r.get("Product ID")])
        countries = [(str(r["Country Code"]), f"{r.get('Country Name') or ''} ({r['Country Code']})")
                     for r in db[S.COUNTRIES].rows if r.get("Country Code")]
        had_market = self.market.count() > 0
        self._fill(self.market, countries)
        if not had_market:
            i = self.market.findData("DE")
            if i >= 0:
                self.market.setCurrentIndex(i)
        self._fill(self.payment, [("", "(none)")] + [(str(r["Payment Method ID"]),
                                                      f"{r.get('Name') or ''} ({r['Payment Method ID']})")
                                                     for r in db[S.PAYMENT].rows if r.get("Payment Method ID")])
        years = db[S.MATERIALS].years
        self._fill(self.year, [(str(y), str(y)) for y in sorted(years, reverse=True)])
        self._fill(self.price_cur, [(k, k) for k in db[S.FX].keys()])
        self._market_changed()
        checked = {self.hq_list.item(i).data(Qt.UserRole) for i in range(self.hq_list.count())
                   if self.hq_list.item(i).checkState() == Qt.Checked}
        first = self.hq_list.count() == 0
        self.hq_list.clear()
        hqs = []
        for r in db[S.COMPANY_TYPES].rows:
            cc = str(r.get("Country Code") or "").upper()
            if cc and cc not in hqs:
                hqs.append(cc)
        for cc in hqs:
            cr = db[S.COUNTRIES].find(cc)
            it = QListWidgetItem(f"{(cr or {}).get('Country Name', cc)} ({cc})")
            it.setData(Qt.UserRole, cc)
            on = (cc in ("CH", "DE", "HR", "BA")) if first else (cc in checked)
            it.setCheckState(Qt.Checked if on else Qt.Unchecked)
            self.hq_list.addItem(it)

    # -- run ------------------------------------------------------------------------
    def scenario_configs(self) -> list[dict]:
        db = self.c.db
        hqs = {self.hq_list.item(i).data(Qt.UserRole) for i in range(self.hq_list.count())
               if self.hq_list.item(i).checkState() == Qt.Checked}
        out = []
        for ct in db[S.COMPANY_TYPES].rows:
            cc = str(ct.get("Country Code") or "").upper()
            if cc not in hqs or not ct.get("Company Type ID"):
                continue
            cfg = {
                "Configuration ID": f"{ct['Company Type ID']}",
                "Name": f"{ct.get('Legal Form')} ({cc}) -> {self.market.currentData()}",
                "Active": True,
                "Product ID": self.product.currentData(),
                "Material Price Year": int(self.year.currentData()) if self.year.currentData() else None,
                "HQ Country": cc,
                "Company Type ID": ct["Company Type ID"],
                "Market Country": self.market.currentData(),
                "Sale Type": self.sale_type.currentText(),
                "Payment Method ID": self.payment.currentData() or None,
                "Base Gross Price (incl. VAT)": self.price.value() if self.mode_fixed.isChecked() else None,
                "Price Currency": self.price_cur.currentData() if self.mode_fixed.isChecked() else None,
                "Markup (%)": self.markup.value(),
                "Annual Volume (units)": self.volume.value(),
                "Startup Stock (units)": self.stock.value(),
                "Sales Commission (%)": self.commission.value(),
                "Small-Business VAT Exemption": self.sbe.isChecked(),
                "Notes": "Created from 'Where to found?'",
            }
            out.append(cfg)
        return out

    def run(self):
        if not self.product.currentData() or not self.market.currentData():
            QMessageBox.information(self, "Compare", "Please add at least one product and one country first.")
            return
        eng = Engine(self.c.db)
        res = [(cfg, eng.calculate(cfg, [])) for cfg in self.scenario_configs()]
        res.sort(key=lambda x: (not x[1].ok, -(x[1].net_to_owner if x[1].ok else 0)))
        self.results = res
        cur = self.c.db.reporting_currency
        self.table.setRowCount(0)
        best = next((r for _c, r in res if r.ok), None)
        for rank, (cfg, r) in enumerate(res, start=1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = [str(rank), r.hq or cfg["HQ Country"], r.legal_form or cfg["Company Type ID"], r.liability]
            if r.ok:
                vals += [money(r.startup_total, cur, 0), money(r.gross_price, cur), money(r.production_cost, cur),
                         money(r.shipping + r.customs, cur), money(r.social + r.profit_tax + r.distribution_tax, cur),
                         money(r.net_to_owner, cur), f"{r.margin_pct:.1f} %", money(r.annual_net_to_owner, cur, 0),
                         "-" if r.payback_months is None else f"{r.payback_months:.1f}",
                         "OK" if not r.warnings else "; ".join(r.warnings)]
            else:
                vals += [""] * 9 + ["Error: " + r.error]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if 4 <= j <= 12:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if r is best:
                    it.setBackground(QBrush(QColor("#E3F4E4")))
                elif not r.ok or (r.ok and r.net_to_owner < 0):
                    it.setBackground(QBrush(QColor("#FDE2E1")))
                if j == 9:
                    f = QFont()
                    f.setBold(True)
                    it.setFont(f)
                self.table.setItem(row, j, it)
        if best:
            self.summary.setText(f"Best: {best.legal_form} in {best.hq} keeps {money(best.net_to_owner, cur)} "
                                 f"per unit ({best.margin_pct:.1f} % of the gross price), "
                                 f"{money(best.annual_net_to_owner, cur, 0)} per year. "
                                 f"Startup cash: {money(best.startup_total, cur, 0)}.")
        else:
            self.summary.setText("No valid result - check the data issues (status bar).")
        if self.table.rowCount():
            self.table.selectRow(0)

    def save_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.results):
            QMessageBox.information(self, "Save", "Run a comparison and select a row first.")
            return
        cfg = dict(self.results[row][0])
        cfg.pop("Configuration ID", None)
        idx = self.c.add_row(S.CONFIGS, cfg)
        new_id = self.c.db[S.CONFIGS].rows[idx]["Configuration ID"]
        self.c.status_changed.emit("info", f"Saved as configuration {new_id}.")
        return new_id
