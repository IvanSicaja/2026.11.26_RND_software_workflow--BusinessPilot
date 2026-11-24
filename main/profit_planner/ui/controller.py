"""Application controller: owns the database, validation, calculation and safe saving."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from ..calc import Engine, Result
from ..database import Database, Issue, coerce
from ..storage import SafeStore, SaveError, SaveResult, SyncStatus


class Controller(QObject):
    data_changed = Signal()            # any data change (rows/values)
    structure_changed = Signal(str)    # sheet whose columns changed / db replaced ("" = all)
    status_changed = Signal(str, str)  # (level: ok|pending|error|info, message)
    issues_changed = Signal(int, int)  # errors, warnings
    conflict_detected = Signal()
    message = Signal(str, str)         # (title, text) informational popups

    AUTOSAVE_DELAY_MS = 1200
    POLL_MS = 2000

    def __init__(self, store: SafeStore, db: Database, parent=None):
        super().__init__(parent)
        self.store = store
        self.db = db
        self.dirty = False
        self.autosave = True
        self.issues: list[Issue] = []
        self.issue_map: dict[tuple, str] = {}
        self.results: list[Result] = []
        self._last_stat = None
        self._conflict_open = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self.poll)
        self._recompute()

    # -- lifecycle ---------------------------------------------------------------
    def start(self):
        self._remember_stat()
        self._poll_timer.start(self.POLL_MS)

    def stop(self):
        self._poll_timer.stop()
        self._save_timer.stop()

    def _remember_stat(self):
        try:
            st = os.stat(self.store.original)
            self._last_stat = (st.st_mtime_ns, st.st_size)
        except OSError:
            self._last_stat = None

    # -- computed state ------------------------------------------------------------
    def _recompute(self):
        self.issues = self.db.validate()
        self.issue_map = {}
        for i in self.issues:
            k = (i.sheet, i.row, i.column)
            self.issue_map[k] = (self.issue_map[k] + "\n" if k in self.issue_map else "") + i.message
        self.results = Engine(self.db).calculate_all()
        errs = sum(1 for i in self.issues if i.level == "error")
        self.issues_changed.emit(errs, len(self.issues) - errs)

    def issue_at(self, sheet: str, row: int, column: str) -> str | None:
        return self.issue_map.get((sheet, row, column))

    def row_has_issue(self, sheet: str, row: int) -> bool:
        return any(k[0] == sheet and k[1] == row for k in self.issue_map)

    def engine(self) -> Engine:
        return Engine(self.db)

    # -- editing ------------------------------------------------------------------
    def changed(self, structure_sheet: str | None = None):
        self.dirty = True
        self._recompute()
        if structure_sheet is not None:
            self.structure_changed.emit(structure_sheet)
        self.data_changed.emit()
        self.status_changed.emit("pending", "Unsaved changes" + (" - saving..." if self.autosave else ""))
        if self.autosave:
            self._save_timer.start(self.AUTOSAVE_DELAY_MS)

    def set_value(self, sheet: str, row_index: int, column: str, text) -> tuple[bool, str]:
        """Set a cell from user input. Returns (accepted, message)."""
        t = self.db[sheet]
        if not 0 <= row_index < len(t.rows):
            return False, "Row no longer exists."
        col = t.col(column)
        if col is None:
            return False, "Unknown column."
        value, _err = coerce(col, text)
        row = t.rows[row_index]
        old = row.get(column)
        if value == old and type(value) is type(old):
            return False, ""
        msg = ""
        if column == t.spec.key:
            if value in (None, ""):
                return False, "The ID cannot be empty."
            other = t.find(value)
            if other is not None and other is not row:
                return False, f"The ID '{value}' already exists."
            if old not in (None, ""):
                n = self.db.rename_key(sheet, old, value)
                if n:
                    msg = f"Updated {n} reference(s) to the new ID '{value}'."
        row[column] = value
        self.changed()
        return True, msg

    def add_row(self, sheet: str, values: dict | None = None) -> int:
        t = self.db[sheet]
        r = t.new_row()
        if t.spec.key:
            r[t.spec.key] = self.db.next_id(sheet)
        for k, v in (values or {}).items():
            r[k] = v
        t.rows.append(r)
        self.changed()
        return len(t.rows) - 1

    def duplicate_row(self, sheet: str, row_index: int) -> int:
        t = self.db[sheet]
        src = t.rows[row_index]
        r = dict(src)
        if t.spec.key:
            r[t.spec.key] = self.db.next_id(sheet)
            if "Name" in r and r.get("Name"):
                r["Name"] = f"{r['Name']} (copy)"
        t.rows.insert(row_index + 1, r)
        # duplicate child rows (e.g. services of a configuration, BOM of a product)
        if t.spec.key and src.get(t.spec.key):
            for ct in self.db.tables.values():
                if ct.spec.parent and ct.spec.parent[1] == sheet:
                    pcol = ct.spec.parent[0]
                    for child in list(ct.children(src[t.spec.key])):
                        c2 = dict(child)
                        c2[pcol] = r[t.spec.key]
                        ct.rows.append(c2)
        self.changed()
        return row_index + 1

    def blocking_references(self, sheet: str, key) -> list[str]:
        """References that prevent deleting (anything but the sheet's own child link tables)."""
        out = []
        for tname, idx in self.db.references_to(sheet, key):
            t = self.db[tname]
            if t.spec.parent and t.spec.parent[1] == sheet:
                continue
            label = t.rows[idx].get(t.spec.key) if t.spec.key else f"row {idx + 2}"
            out.append(f"{tname}: {label}")
        return out

    def delete_rows(self, sheet: str, row_indices: list[int]) -> int:
        t = self.db[sheet]
        idx = sorted(set(i for i in row_indices if 0 <= i < len(t.rows)), reverse=True)
        for i in idx:
            r = t.rows.pop(i)
            if t.spec.key and r.get(t.spec.key) not in (None, ""):
                self.db.delete_cascade_children(sheet, r[t.spec.key])
        if idx:
            self.changed()
        return len(idx)

    def add_year(self, sheet: str, year: int, copy_from: int | None, increase_pct: float):
        self.db[sheet].add_year(year, copy_from, increase_pct)
        self.changed(sheet)

    def remove_year(self, sheet: str, year: int):
        self.db[sheet].remove_year(year)
        self.changed(sheet)

    def replace_database(self, db: Database, dirty: bool, note: str = ""):
        self.db = db
        self.dirty = dirty
        self._recompute()
        self.structure_changed.emit("")
        self.data_changed.emit()
        if dirty and self.autosave:
            self._save_timer.start(self.AUTOSAVE_DELAY_MS)
        if note:
            self.status_changed.emit("info", note)

    # -- saving --------------------------------------------------------------------
    def save(self) -> SaveResult | None:
        self._save_timer.stop()
        try:
            res = self.store.save(self.db, self.results)
        except (SaveError, OSError) as e:
            self.status_changed.emit("error", f"SAVE FAILED - your data is still in the app: {e}")
            self.message.emit("Save failed",
                              f"The data could not be saved:\n\n{e}\n\nNothing was overwritten. "
                              "Check that the folder is writable and try again (Ctrl+S).")
            return None
        self.dirty = False
        self._remember_stat()
        self._report(res)
        return res

    def _report(self, res: SaveResult):
        if res.status == SyncStatus.SYNCED:
            self.status_changed.emit("ok", res.message)
        elif res.status == SyncStatus.PENDING_LOCKED:
            self.status_changed.emit("pending", res.message)
        else:
            self.status_changed.emit("error", res.message)
            self.conflict_detected.emit()

    def resolve_keep_app(self):
        try:
            res = self.store.resolve_conflict_keep_app(self.db, self.results)
        except (SaveError, OSError) as e:
            self.status_changed.emit("error", f"Could not write the Excel file: {e}")
            return
        self.dirty = False
        self._remember_stat()
        self._report(res)

    def resolve_keep_excel(self):
        try:
            db, notes = self.store.resolve_conflict_keep_excel()
        except Exception as e:  # noqa: BLE001
            self.status_changed.emit("error", f"Could not read the Excel file: {e}")
            return
        self._remember_stat()
        self.replace_database(db, False, "Loaded the version from Excel (the app version was kept as a backup).")

    def reload_from_excel(self) -> bool:
        try:
            db, notes = self.store.reload_from_original()
        except Exception as e:  # noqa: BLE001
            self.status_changed.emit("error", f"Could not read the Excel file: {e}")
            return False
        self._remember_stat()
        self.replace_database(db, False, "Reloaded the data from the Excel file.")
        return True

    # -- polling: Excel closed (sync) / Excel edited (reload) ------------------------
    def poll(self):
        if self._conflict_open:
            return
        if self.store.pending_sync and not self.dirty:
            res = self.store.retry_sync()
            if res is not None:
                self._remember_stat()
                if res.status == SyncStatus.SYNCED:
                    self._report(res)
                elif res.status == SyncStatus.CONFLICT:
                    self._report(res)
                return
        try:
            st = os.stat(self.store.original)
            stat = (st.st_mtime_ns, st.st_size)
        except OSError:
            return
        if stat == self._last_stat:
            return
        if self.store.excel_lock_present() and not self.store.original_changed_externally():
            self._last_stat = stat
            return
        if not self.store.original_changed_externally():
            self._last_stat = stat
            return
        if self.dirty or self.store.pending_sync:
            self._last_stat = stat
            self.conflict_detected.emit()
            return
        # unchanged in the app -> take the Excel version automatically
        try:
            db, notes = self.store.reload_from_original()
        except Exception:  # noqa: BLE001 - Excel may still be writing; try again next tick
            return
        self._remember_stat()
        self.replace_database(db, False, "Changes saved in Excel were loaded automatically.")

    def set_conflict_open(self, flag: bool):
        self._conflict_open = flag

    @property
    def database_path(self) -> Path:
        return self.store.original
