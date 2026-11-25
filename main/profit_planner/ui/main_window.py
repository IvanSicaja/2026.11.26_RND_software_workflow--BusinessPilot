"""Main application window."""
from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QSizePolicy, QSplitter, QStatusBar, QTabWidget, QToolBar, QVBoxLayout,
                               QWidget)

from .. import APP_NAME, __version__
from .. import schema as S
from ..calc import Engine
from . import help_texts as H
from . import theme
from .controller import Controller
from .dialogs import AddYearDialog, BackupsDialog, IssuesDialog, ask_conflict
from .explorer_view import ExplorerView
from .results_view import ResultsView
from .table_editor import TableEditor
from .widgets import money


def _page(*widgets, margins=10) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(margins, margins, margins, margins)
    for x in widgets:
        lay.addWidget(x, 0 if isinstance(x, QLabel) else 1)
    return w


def _vsplit(*widgets, sizes=None) -> QSplitter:
    s = QSplitter(Qt.Vertical)
    for w in widgets:
        s.addWidget(w)
    if sizes:
        s.setSizes(sizes)
    s.setChildrenCollapsible(False)
    return s


class MainWindow(QMainWindow):
    def __init__(self, controller: Controller, launcher=None):
        super().__init__()
        self.c = controller
        self.launcher = launcher
        self.editors: dict[str, tuple[int, TableEditor]] = {}
        self._closing_ok = False
        self.resize(1400, 860)
        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self.c.status_changed.connect(self._status)
        self.c.issues_changed.connect(self._issues)
        self.c.conflict_detected.connect(self._conflict)
        self.c.message.connect(lambda t, m: QMessageBox.warning(self, t, m))
        self.c.data_changed.connect(self._update_title)
        self._update_title()
        self.c._recompute()
        self.c.start()
        self._status("ok", "Ready. All data is saved in: " + str(self.c.database_path))

    # -- UI construction -------------------------------------------------------------
    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)

        def act(text, slot, shortcut=None, tip=""):
            a = QAction(text, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setToolTip(H.TOOLBAR.get(text, tip or text))
            tb.addAction(a)
            return a

        self.a_save = act("Save", self.save, "Ctrl+S", "Save now (Ctrl+S). Autosave is normally on.")
        act("Reload from Excel", self.reload_excel, "Ctrl+R", "Load the Excel file again (after editing it in Excel)")
        act("Open in Excel", self.open_excel, None, "Open the database file in Excel / your spreadsheet app")
        act("Open folder", self.open_folder, None, "Show the database folder")
        tb.addSeparator()
        act("Data check", self.show_issues, "Ctrl+K", "List every missing or invalid value")
        act("Backups...", self.show_backups, None, "Restore an earlier version")
        tb.addSeparator()
        act("Open database...", self.open_other, "Ctrl+O", "Open another database file")
        act("New database...", self.new_database, None, "Create a new database with starter data")
        tb.addSeparator()
        self.autosave_cb = QCheckBox("Autosave")
        self.autosave_cb.setChecked(self.c.autosave)
        self.autosave_cb.setToolTip(H.TOOLBAR["Autosave"])
        self.autosave_cb.toggled.connect(self._toggle_autosave)
        tb.addWidget(self.autosave_cb)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        act("About", self.about)

    def _editor(self, sheet, tab_index, title=None, child=False, show_description=True) -> TableEditor:
        e = TableEditor(self.c, sheet, title, child=child, show_description=show_description)
        self.editors.setdefault(sheet, (tab_index, e))
        return e

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.results_view = ResultsView(self.c)
        self.results_view.open_configuration.connect(self.go_to_configuration)
        self.tabs.addTab(self.results_view, "Results")
        self.explorer = ExplorerView(self.c)
        self.tabs.addTab(self.explorer, "Where to found?")

        # Configurations + services
        i = self.tabs.count()
        cfg = self._editor(S.CONFIGS, i, "Configurations (scenarios)")
        cs = self._editor(S.CONFIG_SERVICES, i, "Extra services of the selected configuration", child=True)
        cfg.selection_key_changed.connect(cs.set_parent_key)
        cs.set_parent_key(None)
        self.tabs.addTab(_page(_vsplit(cfg, cs, sizes=[520, 220])), "Configurations")

        # Products + BOM + tools
        i = self.tabs.count()
        prod = self._editor(S.PRODUCTS, i, "Products")
        bom = self._editor(S.PRODUCT_MATERIALS, i, "Materials of the selected product", child=True,
                           show_description=False)
        ptools = self._editor(S.PRODUCT_TOOLS, i, "Tools for the selected product", child=True,
                              show_description=False)
        self.product_cost = QLabel("")
        self.product_cost.setObjectName("hint")
        self.product_cost.setWordWrap(True)
        prod.selection_key_changed.connect(bom.set_parent_key)
        prod.selection_key_changed.connect(ptools.set_parent_key)
        prod.selection_key_changed.connect(self._update_product_cost)
        self.c.data_changed.connect(lambda: self._update_product_cost(prod.current_key()))
        bom.set_parent_key(None)
        ptools.set_parent_key(None)
        lower = QSplitter(Qt.Horizontal)
        lower.addWidget(bom)
        lower.addWidget(ptools)
        lower.setSizes([800, 500])
        self._prod_editor = prod
        self.tabs.addTab(_page(_vsplit(prod, _page(self.product_cost, lower, margins=0), sizes=[300, 420])),
                         "Products")

        # Materials / services with year columns
        for sheet, title in ((S.MATERIALS, "Materials (price per unit and year)"),
                             (S.SERVICES, "Services (net price per year)")):
            i = self.tabs.count()
            e = self._editor(sheet, i, title)
            b1 = QPushButton("Add year...")
            b1.setToolTip(H.ADD_YEAR)
            b1.clicked.connect(lambda _=False, s=sheet: self.add_year(s))
            b2 = QPushButton("Remove year...")
            b2.setToolTip(H.REMOVE_YEAR)
            b2.clicked.connect(lambda _=False, s=sheet: self.remove_year(s))
            e.extra_buttons.addWidget(b1)
            e.extra_buttons.addWidget(b2)
            self.tabs.addTab(_page(e), "Materials" if sheet == S.MATERIALS else "Services")

        i = self.tabs.count()
        self.tabs.addTab(_page(self._editor(S.TOOLS, i, "Tools and machines")), "Tools")

        i = self.tabs.count()
        self.tabs.addTab(_page(_vsplit(self._editor(S.COUNTRIES, i, "Countries"),
                                       self._editor(S.COMPANY_TYPES, i, "Legal forms (company types)"),
                                       sizes=[380, 380])), "Countries && Legal Forms")

        i = self.tabs.count()
        inner = QTabWidget()
        inner.addTab(_page(self._editor(S.SHIPPING, i, "Shipping rates")), "Shipping")
        inner.addTab(_page(self._editor(S.CUSTOMS, i, "Customs rules")), "Customs")
        inner.addTab(_page(self._editor(S.PAYMENT, i, "Payment methods")), "Payment")
        self._logistics_tabs = inner
        self.tabs.addTab(_page(inner, margins=4), "Shipping, Customs && Payment")

        i = self.tabs.count()
        self.tabs.addTab(_page(_vsplit(self._editor(S.FX, i, "Exchange rates"),
                                       self._editor(S.SETTINGS, i, "Settings"), sizes=[400, 250])),
                         "Currencies && Settings")
        for k in range(self.tabs.count()):
            self.tabs.setTabToolTip(k, H.TABS[self.tabs.tabText(k).replace("&&", "&")])
        for k in range(inner.count()):
            inner.setTabToolTip(k, H.INNER_TABS[inner.tabText(k)])

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.status_dot = QLabel("●")
        self.status_label = QLabel("")
        self.issues_btn = QPushButton("")
        self.issues_btn.setFlat(True)
        self.issues_btn.clicked.connect(self.show_issues)
        self.issues_btn.setToolTip(H.ISSUES)
        self.status_dot.setToolTip(H.STATUS)
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.addWidget(self.status_dot)
        lay.addWidget(self.status_label, 1)
        sb.addWidget(w, 1)
        sb.addPermanentWidget(self.issues_btn)
        self._issues(*self._issue_counts())

    # -- status ------------------------------------------------------------------
    def _issue_counts(self):
        errs = sum(1 for i in self.c.issues if i.level == "error")
        return errs, len(self.c.issues) - errs

    def _status(self, level: str, msg: str):
        color = {"ok": theme.GOOD, "pending": theme.WARN, "error": theme.BAD, "info": theme.INFO}.get(level, theme.TEXT_MUTED)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.status_label.setText(msg)
        self.status_label.setToolTip(H.STATUS.replace("</qt>", f"<p style='margin:6px 0 0 0'><b>Current:</b> "
                                                            f"{escape(msg)}</p></qt>"))

    def _issues(self, errors: int, warnings: int):
        if errors or warnings:
            self.issues_btn.setText(f"⚠ {errors} error(s), {warnings} warning(s) - click to see")
            self.issues_btn.setStyleSheet(f"color: {theme.BAD}; font-weight: bold;" if errors else f"color: {theme.WARN};")
        else:
            self.issues_btn.setText("✓ Data check: no problems")
            self.issues_btn.setStyleSheet(f"color: {theme.GOOD};")

    def _update_title(self):
        name = self.c.db.setting("Company Name", "")
        star = " *" if self.c.dirty else ""
        self.setWindowTitle(f"{APP_NAME} - {name} - {self.c.database_path.name}{star}")

    def _update_product_cost(self, key):
        if key in (None, ""):
            self.product_cost.setText("Select a product to edit its materials and tools.")
            return
        eng = Engine(self.c.db)
        parts = []
        cur = self.c.db.reporting_currency
        for y in sorted(self.c.db[S.MATERIALS].years)[-4:]:
            total, err = 0.0, None
            warns = []
            for line in self.c.db[S.PRODUCT_MATERIALS].children(key):
                m = self.c.db[S.MATERIALS].find(line.get("Material ID"))
                try:
                    if m is None:
                        raise ValueError(f"unknown material {line.get('Material ID')}")
                    waste = line.get("Waste Override (%)")
                    if waste in (None, ""):
                        waste = m.get("Waste (%)") or 0
                    price = eng._year_price(m, self.c.db[S.MATERIALS].years, y, str(m.get("Material ID")), warns)
                    total += eng.fx(float(line.get("Quantity")) * (1 + float(waste) / 100) * price, m.get("Currency"))
                except Exception as e:  # noqa: BLE001 - preview only
                    err = str(e)
                    break
            parts.append(f"{y}: {'n/a' if err else money(total, cur)}")
        self.product_cost.setText(f"<b>Material cost per unit of {key}</b> (incl. waste):  " + "   |   ".join(parts))

    # -- actions --------------------------------------------------------------------
    def _toggle_autosave(self, on: bool):
        self.c.autosave = on
        if on and self.c.dirty:
            self.c.save()

    def save(self):
        self._commit_editors()
        self.c.save()
        self._update_title()

    def _commit_editors(self):
        fw = self.focusWidget()
        if fw is not None:
            fw.clearFocus()

    def reload_excel(self):
        if self.c.dirty or self.c.store.pending_sync:
            if self.c.store.original_changed_externally():
                self._conflict()
                return
            r = QMessageBox.question(self, "Reload from Excel",
                                     "The app has changes that are not yet in the Excel file. Discard them and "
                                     "reload the Excel file?\n(The app version is kept in the Backups folder.)")
            if r != QMessageBox.Yes:
                return
            self.c.resolve_keep_excel()
        else:
            self.c.reload_from_excel()
        self._update_title()

    def open_excel(self):
        if self.c.dirty:
            self.c.save()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.c.database_path)))
        self._status("info", "Opened in Excel. Save and close Excel - the app picks up the changes automatically.")

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.c.database_path.parent)))

    def show_issues(self):
        IssuesDialog(self.c.issues, self.jump_to_issue, self).exec()

    def jump_to_issue(self, issue):
        if issue.sheet not in self.editors:
            return
        tab, ed = self.editors[issue.sheet]
        self.tabs.setCurrentIndex(tab)
        if issue.sheet in (S.SHIPPING, S.CUSTOMS, S.PAYMENT):
            self._logistics_tabs.setCurrentIndex([S.SHIPPING, S.CUSTOMS, S.PAYMENT].index(issue.sheet))
        if issue.row is None:
            return
        if ed.child:
            t = self.c.db[issue.sheet]
            parent_col, parent_sheet = t.spec.parent
            pkey = t.rows[issue.row].get(parent_col)
            if parent_sheet in self.editors and pkey:
                self.editors[parent_sheet][1].select_key(pkey)
        ed.search.clear()
        ed.select_source_row(issue.row, issue.column)

    def go_to_configuration(self, cid: str):
        tab, ed = self.editors[S.CONFIGS]
        self.tabs.setCurrentIndex(tab)
        ed.search.clear()
        ed.select_key(cid)

    def add_year(self, sheet: str):
        t = self.c.db[sheet]
        d = AddYearDialog(t.years, self)
        if d.exec():
            y, src, inc = d.values()
            self.c.add_year(sheet, y, src, inc)
            self._status("info", f"Added year {y} to '{sheet}'.")

    def remove_year(self, sheet: str):
        t = self.c.db[sheet]
        if not t.years:
            return
        from PySide6.QtWidgets import QInputDialog
        items = [str(y) for y in sorted(t.years, reverse=True)]
        y, ok = QInputDialog.getItem(self, "Remove year", "Remove the price column of year:", items, 0, False)
        if not ok:
            return
        if QMessageBox.question(self, "Remove year", f"Delete all {sheet.lower()} prices of {y}?\n"
                                                     "(A backup of the Excel file is kept.)") == QMessageBox.Yes:
            self.c.remove_year(sheet, int(y))

    def show_backups(self):
        backups = self.c.store.list_backups()
        if not backups:
            QMessageBox.information(self, "Backups", "No backups yet. They are created automatically when "
                                                     "the Excel file is updated.")
            return
        d = BackupsDialog(backups, self)
        if d.exec() and d.selected:
            try:
                db, notes = self.c.store.read_backup(d.selected)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, "Restore", f"The backup cannot be read:\n{e}")
                return
            self.c.store.backup_original("before-restore", force=True)
            self.c.replace_database(db, True, f"Restored backup {d.selected.name}.")
            self.c.save()

    def _conflict(self):
        self.c.set_conflict_open(True)
        try:
            choice = ask_conflict(self)
            if choice == "app":
                self.c.resolve_keep_app()
            else:
                self.c.resolve_keep_excel()
        finally:
            self.c.set_conflict_open(False)
        self._update_title()

    def open_other(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open database", str(self.c.database_path.parent),
                                              "Excel (*.xlsx)")
        if path and self.launcher:
            self._switch(path)

    def new_database(self):
        path, _ = QFileDialog.getSaveFileName(self, "New database", str(self.c.database_path.parent /
                                                                         "New_ProfitPlanner_Database.xlsx"),
                                              "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        if Path(path).exists():
            QMessageBox.warning(self, "New database", "That file already exists. Use 'Open database' instead.")
            return
        if self.launcher:
            self._switch(path)

    def _switch(self, path: str):
        if self.c.dirty:
            self.c.save()
        win = self.launcher(path, self)
        if win is not None:
            self._closing_ok = True
            self.close()

    def about(self):
        QMessageBox.about(self, f"About {APP_NAME}", (
            f"<h3>{APP_NAME} {__version__}</h3>"
            "<p>Plan product prices, compare where to found your company and see your net profit per unit.</p>"
            f"<p><b>Database:</b> {self.c.database_path}</p>"
            "<p>The app always works on a verified working copy and then updates the Excel file; earlier "
            "versions are kept in the <i>Backups</i> folder.</p>"
            "<p><b>Disclaimer:</b> tax rates, fees and costs are indicative planning values. Verify them with "
            "a local accountant or tax advisor.</p>"))

    # -- close ------------------------------------------------------------------------
    def closeEvent(self, e):
        self._commit_editors()
        if self.c.dirty:
            res = self.c.save()
            if res is None:
                r = QMessageBox.question(self, "Close", "Saving failed. Close anyway and lose the last changes?")
                if r != QMessageBox.Yes:
                    e.ignore()
                    return
        self.c.stop()
        QSettings().setValue("database_path", str(self.c.database_path))
        if getattr(self, "lock", None) is not None:
            self.lock.unlock()
        e.accept()
