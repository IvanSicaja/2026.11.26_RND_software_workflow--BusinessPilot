"""Generic editable Qt model on top of one database sheet."""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QBrush, QColor, QFont

from .. import schema as S
from . import help_texts, theme
from ..database import display

ERROR_BG = QColor(theme.BAD_BG)
KEY_FONT = QFont()
KEY_FONT.setBold(True)
NUMERIC_KINDS = (S.NUMBER, S.PERCENT, S.INTEGER)


class SheetModel(QAbstractTableModel):
    def __init__(self, controller, sheet: str, parent=None):
        super().__init__(parent)
        self.c = controller
        self.sheet = sheet
        self.filter_value = None          # for child tables: show only rows of this parent
        self.child_mode = False
        self.hidden_columns: set[str] = set()
        self._rows: list[int] = []
        self._cols: list[str] = []
        self._rebuild()

    # -- structure -------------------------------------------------------------
    @property
    def table(self):
        return self.c.db[self.sheet]

    def _rebuild(self):
        t = self.table
        self._cols = [c for c in t.columns() if c not in self.hidden_columns]
        if self.child_mode and t.spec.parent:
            if self.filter_value in (None, ""):
                self._rows = []
            else:
                pcol = t.spec.parent[0]
                fv = str(self.filter_value).lower()
                self._rows = [i for i, r in enumerate(t.rows)
                              if r.get(pcol) is not None and str(r.get(pcol)).lower() == fv]
        else:
            self._rows = list(range(len(t.rows)))

    def refresh(self):
        old_r, old_c = list(self._rows), list(self._cols)
        self._rebuild()
        if old_r == self._rows and old_c == self._cols:
            if self._rows and self._cols:
                self.dataChanged.emit(self.index(0, 0), self.index(len(self._rows) - 1, len(self._cols) - 1))
        else:
            self.beginResetModel()
            self.endResetModel()

    def reset(self):
        self.beginResetModel()
        self._rebuild()
        self.endResetModel()

    def set_filter(self, value):
        self.filter_value = value
        self.reset()

    def column_name(self, col: int) -> str:
        return self._cols[col]

    def column_index(self, name: str) -> int:
        return self._cols.index(name) if name in self._cols else -1

    def source_row(self, row: int) -> int:
        return self._rows[row]

    def view_row(self, source_row: int) -> int:
        return self._rows.index(source_row) if source_row in self._rows else -1

    def col_spec(self, col: int):
        return self.table.col(self._cols[col])

    # -- Qt API ----------------------------------------------------------------
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._cols)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and 0 <= section < len(self._cols):
            name = self._cols[section]
            if role == Qt.DisplayRole:
                c = self.table.col(name)
                return name + (" *" if c is not None and c.required else "")
            if role == Qt.ToolTipRole:
                return help_texts.column_tip(self.sheet, name, self.table.col(name))
        if orientation == Qt.Vertical and role == Qt.DisplayRole and 0 <= section < len(self._rows):
            return str(self._rows[section] + 2)  # same row number as in Excel
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self._rows[index.row()]
        cname = self._cols[index.column()]
        t = self.table
        if r >= len(t.rows):
            return None
        val = t.rows[r].get(cname)
        col = t.col(cname)
        if role in (Qt.DisplayRole, Qt.EditRole):
            return display(col, val)
        if role == Qt.BackgroundRole:
            if self.c.issue_at(self.sheet, r, cname):
                return QBrush(ERROR_BG)
            return None
        if role == Qt.ToolTipRole:
            issue = self.c.issue_at(self.sheet, r, cname)
            if issue:
                return issue
            if col is not None and col.kind == S.REF and col.ref and val:
                ref = self.c.db[col.ref].find(val)
                if ref is not None:
                    return str(ref.get("Name") or ref.get("Country Name") or ref.get("Legal Form") or val)
            return None
        if role == Qt.TextAlignmentRole:
            if col is not None and col.kind in NUMERIC_KINDS:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.FontRole and cname == t.spec.key:
            return KEY_FONT
        if role == Qt.UserRole:  # sort key
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return float(val)
            return display(col, val).lower()
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        r = self._rows[index.row()]
        cname = self._cols[index.column()]
        ok, msg = self.c.set_value(self.sheet, r, cname, value)
        if msg:
            self.c.status_changed.emit("info" if ok else "error", msg)
        return ok


class SortProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortRole(Qt.UserRole)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(-1)

    def lessThan(self, left, right):
        a = left.data(Qt.UserRole)
        b = right.data(Qt.UserRole)
        if isinstance(a, float) and isinstance(b, float):
            return a < b
        if isinstance(a, float):
            return True
        if isinstance(b, float):
            return False
        return str(a or "") < str(b or "")
