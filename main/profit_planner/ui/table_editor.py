"""Reusable editor widget for one sheet: toolbar, search, table with smart editors."""
from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QStyledItemDelegate, QTableView,
                               QVBoxLayout, QWidget)

from .. import schema as S
from . import help_texts as H
from .table_model import SheetModel, SortProxy

EMPTY = "(empty)"


class SmartDelegate(QStyledItemDelegate):
    """Drop-down lists for choices, Yes/No, references and locations; text box otherwise."""

    def __init__(self, editor_widget: "TableEditor"):
        super().__init__(editor_widget)
        self.ed = editor_widget

    def _options(self, index) -> list[tuple[str, str]] | None:
        model: SheetModel = self.ed.model
        src = self.ed.proxy.mapToSource(index)
        col = model.col_spec(src.column())
        if col is None:
            return None
        db = model.c.db
        opts: list[tuple[str, str]] = []
        if col.kind == S.BOOL:
            opts = [(S.YES, S.YES), (S.NO, S.NO)]
        elif col.kind == S.CHOICE:
            opts = [(c, c) for c in col.choices]
        elif col.kind == S.REF and col.ref:
            t = db[col.ref]
            rows = t.rows
            if col.ref == S.COMPANY_TYPES and model.sheet == S.CONFIGS:
                hq = model.table.rows[model.source_row(src.row())].get("HQ Country")
                if hq:
                    rows = [r for r in rows if str(r.get("Country Code", "")).upper() == str(hq).upper()]
            for r in rows:
                k = r.get(t.spec.key)
                if k in (None, ""):
                    continue
                label = r.get("Name") or r.get("Country Name") or r.get("Legal Form") or ""
                if col.ref == S.COMPANY_TYPES:
                    label = f"{r.get('Legal Form', '')} ({r.get('Country Code', '')})"
                opts.append((str(k), f"{k}  -  {label}" if label else str(k)))
        elif col.kind == S.LOCATION:
            opts = [(S.WILDCARD, "*  -  any")]
            opts += [(r, f"{r}  -  region") for r in S.REGIONS]
            for r in db[S.COUNTRIES].rows:
                k = r.get("Country Code")
                if k:
                    opts.append((str(k), f"{k}  -  {r.get('Country Name') or ''}"))
        else:
            return None
        if not col.required and col.kind != S.BOOL:
            opts.insert(0, ("", EMPTY))
        return opts

    def createEditor(self, parent, option, index):
        opts = self._options(index)
        if opts is None:
            e = QLineEdit(parent)
            e.setFrame(False)
            return e
        cb = QComboBox(parent)
        cb.setMaxVisibleItems(25)
        for value, label in opts:
            cb.addItem(label, value)
        cb.activated.connect(lambda _i, w=cb: self._commit_combo(w))
        return cb

    def _commit_combo(self, cb):
        self.commitData.emit(cb)
        self.closeEditor.emit(cb, QStyledItemDelegate.NoHint)

    def setEditorData(self, editor, index):
        val = index.data(Qt.EditRole) or ""
        if isinstance(editor, QComboBox):
            i = editor.findData(val)
            if i < 0:
                for j in range(editor.count()):
                    if str(editor.itemData(j)).lower() == str(val).lower():
                        i = j
                        break
            if i < 0 and val:
                editor.addItem(f"{val}  (not found)", val)
                i = editor.count() - 1
            editor.setCurrentIndex(max(i, 0))
            if self.ed.isVisible():
                QTimer.singleShot(0, editor, editor.showPopup)
        else:
            editor.setText(str(val))
            editor.selectAll()

    def setModelData(self, editor, model, index):
        try:
            if isinstance(editor, QComboBox):
                model.setData(index, editor.currentData(), Qt.EditRole)
            else:
                model.setData(index, editor.text(), Qt.EditRole)
        except RuntimeError:  # application shutting down
            pass


class TableEditor(QWidget):
    selection_key_changed = Signal(object)   # key of the selected row (key tables)

    def __init__(self, controller, sheet: str, title: str | None = None, child: bool = False,
                 show_description: bool = True, parent=None):
        super().__init__(parent)
        self.c = controller
        self.sheet = sheet
        self.child = child
        self.model = SheetModel(controller, sheet, self)
        if child:
            self.model.child_mode = True
            self.model.hidden_columns = {S.SPECS[sheet].parent[0]}
            self.model.reset()
        self.proxy = SortProxy(self)
        self.proxy.setSourceModel(self.model)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        head = QHBoxLayout()
        self.title = QLabel(f"<b>{title or sheet}</b>")
        self.title.setObjectName("sectionTitle")
        head.addWidget(self.title)
        head.addStretch(1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search...")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(240)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        head.addWidget(self.search)
        self.btn_add = QPushButton("+ Add")
        self.btn_dup = QPushButton("Duplicate")
        self.btn_del = QPushButton("Delete")
        self.btn_del.setObjectName("dangerButton")
        self.btn_add.clicked.connect(self.add_row)
        self.btn_dup.clicked.connect(self.duplicate_row)
        self.btn_del.clicked.connect(self.delete_rows)
        self.btn_add.setToolTip(H.add_tip(sheet))
        self.btn_dup.setToolTip(H.duplicate_tip(sheet))
        self.btn_del.setToolTip(H.delete_tip(sheet))
        self.search.setToolTip(H.search_tip(sheet))
        self.extra_buttons = QHBoxLayout()
        head.addLayout(self.extra_buttons)
        for b in (self.btn_add, self.btn_dup, self.btn_del):
            head.addWidget(b)
        if child:
            self.btn_dup.hide()
        lay.addLayout(head)

        if show_description and S.SPECS[sheet].description:
            d = QLabel(S.SPECS[sheet].description)
            d.setObjectName("hint")
            d.setWordWrap(True)
            lay.addWidget(d)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(-1, Qt.AscendingOrder)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
                                  | QAbstractItemView.AnyKeyPressed | QAbstractItemView.SelectedClicked)
        self.view.setItemDelegate(SmartDelegate(self))
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().setDefaultSectionSize(26)
        self.view.setWordWrap(False)
        self.view.selectionModel().currentRowChanged.connect(self._current_changed)
        lay.addWidget(self.view, 1)

        QShortcut(QKeySequence("Ctrl+N"), self.view, activated=self.add_row)
        QShortcut(QKeySequence(Qt.Key_Delete), self.view, activated=self._delete_key)

        self.c.data_changed.connect(self.model.refresh)
        self.c.data_changed.connect(self.ensure_selection)
        self.c.structure_changed.connect(self._structure_changed)
        self._apply_widths()
        if not child:
            QTimer.singleShot(0, self, self.ensure_selection)

    # -- helpers ---------------------------------------------------------------
    def _structure_changed(self, sheet: str):
        if sheet in ("", self.sheet):
            key = self.current_key()
            self.model.reset()
            self._apply_widths()
            if key is not None:
                self.select_key(key)
            self.ensure_selection()

    def _apply_widths(self):
        fm = self.view.horizontalHeader().fontMetrics()
        for i in range(self.model.columnCount()):
            c = self.model.col_spec(i)
            w = (c.width if c else 16) * 8 + 24
            head = str(self.model.headerData(i, Qt.Horizontal, Qt.DisplayRole) or "")
            w = max(w, fm.horizontalAdvance(head) + 34)
            self.view.setColumnWidth(i, min(max(w, 70), 420))

    def ensure_selection(self):
        """Master tables: keep a current row so that detail tables show something."""
        if self.child or self.view.currentIndex().isValid() or self.proxy.rowCount() == 0:
            return
        self.view.setCurrentIndex(self.proxy.index(0, 0))
        self.view.selectRow(0)

    def _current_changed(self, cur: QModelIndex, _prev):
        self.selection_key_changed.emit(self.current_key())

    def selected_source_rows(self) -> list[int]:
        rows = {self.proxy.mapToSource(i).row() for i in self.view.selectionModel().selectedRows()}
        if not rows:
            cur = self.view.currentIndex()
            if cur.isValid():
                rows = {self.proxy.mapToSource(cur).row()}
        return sorted(self.model.source_row(r) for r in rows if 0 <= r < self.model.rowCount())

    def current_key(self):
        k = S.SPECS[self.sheet].key
        if not k:
            return None
        cur = self.view.currentIndex()
        if not cur.isValid():
            return None
        r = self.model.source_row(self.proxy.mapToSource(cur).row())
        rows = self.c.db[self.sheet].rows
        return rows[r].get(k) if r < len(rows) else None

    def select_source_row(self, source_row: int, edit_column: str | None = None):
        vr = self.model.view_row(source_row)
        if vr < 0:
            return
        col = max(self.model.column_index(edit_column), 0) if edit_column else 0
        idx = self.proxy.mapFromSource(self.model.index(vr, col))
        self.view.setCurrentIndex(idx)
        self.view.scrollTo(idx)
        self.view.selectRow(idx.row())

    def select_key(self, key):
        t = self.c.db[self.sheet]
        k = t.spec.key
        if not k:
            return
        for i, r in enumerate(t.rows):
            if str(r.get(k)).lower() == str(key).lower():
                self.select_source_row(i)
                return

    def set_parent_key(self, key):
        self.model.set_filter(key)
        enabled = key not in (None, "")
        self.btn_add.setEnabled(enabled)
        self.btn_del.setEnabled(enabled)

    # -- actions ------------------------------------------------------------------
    def add_row(self):
        values = {}
        if self.child:
            if self.model.filter_value in (None, ""):
                return
            values[S.SPECS[self.sheet].parent[0]] = self.model.filter_value
        self.search.clear()
        r = self.c.add_row(self.sheet, values)
        cols = [c for c in self.model._cols]
        spec = S.SPECS[self.sheet]
        first_edit = next((c for c in cols if c != spec.key), cols[0] if cols else None)
        self.select_source_row(r, first_edit)

    def duplicate_row(self):
        rows = self.selected_source_rows()
        if not rows:
            return
        r = self.c.duplicate_row(self.sheet, rows[0])
        self.select_source_row(r)

    def _delete_key(self):
        if self.view.state() != QAbstractItemView.EditingState:
            self.delete_rows()

    def delete_rows(self):
        rows = self.selected_source_rows()
        if not rows:
            return
        t = self.c.db[self.sheet]
        k = t.spec.key
        blocked = []
        names = []
        children = 0
        for r in rows:
            row = t.rows[r]
            key = row.get(k) if k else None
            names.append(str(key) if key else f"row {r + 2}")
            if k and key not in (None, ""):
                blocked += self.c.blocking_references(self.sheet, key)
                for ct in self.c.db.tables.values():
                    if ct.spec.parent and ct.spec.parent[1] == self.sheet:
                        children += len(ct.children(key))
        if blocked:
            shown = "\n".join(sorted(set(blocked))[:15])
            more = "" if len(set(blocked)) <= 15 else f"\n... and {len(set(blocked)) - 15} more"
            QMessageBox.warning(self, "Cannot delete",
                                f"{', '.join(names[:5])} is still used here:\n\n{shown}{more}\n\n"
                                "Change or delete those rows first.")
            return
        text = f"Delete {len(rows)} row(s): {', '.join(names[:8])}{' ...' if len(names) > 8 else ''}?"
        if children:
            text += f"\n\nThis also deletes {children} linked row(s) (materials, tools or services lists)."
        if QMessageBox.question(self, "Delete", text) != QMessageBox.Yes:
            return
        self.c.delete_rows(self.sheet, rows)
