"""Crash-safe storage of the Excel database.

Files (for a database ``<folder>/ProfitPlanner_Database.xlsx``):

* ``<folder>/ProfitPlanner_Database.xlsx`` - the ORIGINAL. You can open and edit it in Excel.
* ``<folder>/.profitplanner/<name>/working_copy.xlsx`` - the WORKING COPY. The app only ever
  reads from and writes to this file while running.
* ``<folder>/.profitplanner/<name>/state.json`` - bookkeeping (hashes, pending sync flag).
* ``<folder>/Backups/`` - timestamped copies of the original taken before it is overwritten.

Save sequence (every step is atomic: write temp file -> flush -> fsync -> rename):

1. The database is serialised in memory and read back; the save is aborted unless the
   read-back data is identical (nothing broken is ever written).
2. The working copy is replaced atomically and marked "pending sync".
3. Only if step 2 succeeded: the original is backed up and then replaced atomically with
   the verified working copy, and the pending flag is cleared.

A power cut at any moment therefore leaves either the old or the new version of each
file - never a half-written file. If the original is open in Excel (locked) the changes
stay safely in the working copy and are synced automatically later.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from .database import Database
from .excel_io import WorkbookError, read_workbook, write_workbook_bytes
from .seed import build_seed_database

DEFAULT_DB_NAME = "ProfitPlanner_Database.xlsx"
MAX_BACKUPS = 60
BACKUP_INTERVAL_SECONDS = 10 * 60


class SaveError(Exception):
    pass


class SyncStatus(Enum):
    SYNCED = "synced"                 # working copy and original identical
    PENDING_LOCKED = "pending_locked"  # saved to working copy, original locked (open in Excel)
    CONFLICT = "conflict"             # original changed in Excel while the app had unsynced changes


@dataclass
class SaveResult:
    status: SyncStatus
    message: str


@dataclass
class OpenResult:
    db: Database
    messages: list[str] = field(default_factory=list)
    conflict: bool = False
    excel_db: Database | None = None   # only when conflict
    status: SyncStatus = SyncStatus.SYNCED


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return None


def _fsync_dir(path: Path):
    if os.name != "posix":
        return
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def atomic_write(path: Path, data: bytes, retries: int = 3):
    """Write bytes so that `path` contains either the old or the new content, never a mix."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    last_err = None
    for attempt in range(retries):
        try:
            os.replace(tmp, path)
            _fsync_dir(path.parent)
            return
        except PermissionError as e:  # Windows: file open in Excel / antivirus scan
            last_err = e
            time.sleep(0.15 * (attempt + 1))
    try:
        tmp.unlink()
    except OSError:
        pass
    raise last_err  # type: ignore[misc]


class SafeStore:
    def __init__(self, original_path: str | Path):
        self.original = Path(original_path).resolve()
        self.folder = self.original.parent
        self.meta_dir = self.folder / ".profitplanner" / self.original.stem
        self.working = self.meta_dir / "working_copy.xlsx"
        self.state_path = self.meta_dir / "state.json"
        self.backup_dir = self.folder / "Backups"
        self._last_backup_time = 0.0
        self.state = {"original_hash": None, "working_hash": None, "pending_sync": False}

    # -- state -------------------------------------------------------------
    def _load_state(self):
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.state.update({k: data.get(k, v) for k, v in self.state.items()})
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def _save_state(self):
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(self.state_path, json.dumps(self.state, indent=2).encode("utf-8"))

    # -- helpers -------------------------------------------------------------
    def excel_lock_present(self) -> bool:
        """Excel creates '~$<name>' next to a workbook it has open."""
        name = self.original.name
        candidates = {"~$" + name}
        if len(name) > 2:
            candidates.add("~$" + name[2:])
        return any((self.folder / c).exists() for c in candidates)

    @property
    def pending_sync(self) -> bool:
        return bool(self.state.get("pending_sync"))

    def _read(self, path: Path) -> tuple[Database, list[str]]:
        return read_workbook(path.read_bytes())

    def backup_original(self, tag: str = "", force: bool = False) -> Path | None:
        if not self.original.exists():
            return None
        now = time.time()
        if not force and now - self._last_backup_time < BACKUP_INTERVAL_SECONDS:
            return None
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        suffix = f"_{tag}" if tag else ""
        dest = self.backup_dir / f"{self.original.stem}_{ts}{suffix}.xlsx"
        n = 1
        while dest.exists():
            dest = self.backup_dir / f"{self.original.stem}_{ts}{suffix}_{n}.xlsx"
            n += 1
        atomic_write(dest, self.original.read_bytes())
        self._last_backup_time = now
        self._prune_backups()
        return dest

    def _prune_backups(self):
        files = sorted(self.backup_dir.glob(f"{self.original.stem}_*.xlsx"), key=lambda p: p.stat().st_mtime)
        for p in files[:-MAX_BACKUPS]:
            try:
                p.unlink()
            except OSError:
                pass

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(self.backup_dir.glob(f"{self.original.stem}_*.xlsx"),
                      key=lambda p: p.stat().st_mtime, reverse=True)

    # -- open ----------------------------------------------------------------
    def open(self) -> OpenResult:
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()
        orig_exists = self.original.exists()
        work_exists = self.working.exists()

        if not orig_exists and not work_exists:
            db = build_seed_database()
            self.state = {"original_hash": None, "working_hash": None, "pending_sync": False}
            res = self.save(db)
            return OpenResult(db, [f"A new database with starter data was created: {self.original}"],
                              status=res.status)

        if not orig_exists and work_exists:
            db, notes = self._read(self.working)
            self.state["original_hash"] = None
            self.state["pending_sync"] = True
            self._save_state()
            res = self._sync()
            return OpenResult(db, notes + ["The Excel file was missing and has been restored from the working copy."],
                              status=res.status)

        orig_hash = sha256_file(self.original)

        if work_exists and self.pending_sync:
            try:
                app_db, notes = self._read(self.working)
            except WorkbookError:
                app_db = None
                notes = []
            if app_db is not None:
                if orig_hash == self.state.get("original_hash"):
                    res = self._sync()
                    msg = ["Unsynced changes from the last session were found in the working copy."]
                    msg.append(res.message)
                    return OpenResult(app_db, notes + msg, status=res.status)
                # Excel file changed too -> the user must decide
                try:
                    excel_db, _n = self._read(self.original)
                except WorkbookError:
                    excel_db = None
                if excel_db is None:
                    return OpenResult(app_db, notes + [
                        "The Excel file cannot be read. The app uses the working copy; the Excel file "
                        "will be backed up before it is overwritten on the next save."],
                        status=SyncStatus.CONFLICT)
                return OpenResult(app_db, notes, conflict=True, excel_db=excel_db, status=SyncStatus.CONFLICT)

        work_hash = sha256_file(self.working) if work_exists else None
        if (work_exists and work_hash == self.state.get("working_hash")
                and orig_hash == self.state.get("original_hash")):
            try:
                db, notes = self._read(self.working)
                return OpenResult(db, notes)
            except WorkbookError:
                pass  # fall through: rebuild working copy from original

        # Excel file was edited outside the app (or the working copy is missing/damaged)
        try:
            data = self.original.read_bytes()
            db, notes = read_workbook(data)
        except WorkbookError as e:
            if work_exists:
                try:
                    db, notes = self._read(self.working)
                    return OpenResult(db, notes + [
                        f"The Excel file could not be read ({e}). The last working copy is used instead; "
                        "the Excel file will be backed up before it is replaced."], status=SyncStatus.CONFLICT)
                except WorkbookError:
                    pass
            raise
        atomic_write(self.working, data)
        self.state.update(original_hash=sha256_bytes(data), working_hash=sha256_bytes(data), pending_sync=False)
        self._save_state()
        msg = []
        if work_exists:
            msg.append("Changes made directly in Excel were loaded.")
        return OpenResult(db, notes + msg)

    # -- save ----------------------------------------------------------------
    def save(self, db: Database, results: list | None = None) -> SaveResult:
        db.ensure_default_settings()
        db.normalize()
        try:
            data = write_workbook_bytes(db, results)
        except Exception as e:  # noqa: BLE001 - never write anything if serialisation fails
            raise SaveError(f"The data could not be converted to Excel, nothing was written: {e}") from e
        try:
            check_db, _n = read_workbook(data)
        except WorkbookError as e:
            raise SaveError(f"Verification failed, nothing was written: {e}") from e
        if check_db.to_plain() != db.to_plain():
            raise SaveError("Verification failed (data read back differs), nothing was written.")
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(self.working, data)
        self.state["working_hash"] = sha256_bytes(data)
        self.state["pending_sync"] = True
        self._save_state()
        return self._sync()

    def _sync(self) -> SaveResult:
        """Copy the verified working copy over the original (with backup)."""
        if not self.working.exists():
            return SaveResult(SyncStatus.CONFLICT, "Working copy missing.")
        if self.original.exists():
            cur = sha256_file(self.original)
            known = self.state.get("original_hash")
            if known is not None and cur != known:
                return SaveResult(SyncStatus.CONFLICT,
                                  "The Excel file was changed outside the app. Choose which version to keep.")
            if known is None and cur is not None:
                # unknown original (e.g. restored from elsewhere): keep a copy before replacing
                self.backup_original("before-restore", force=True)
        if self.excel_lock_present():
            return SaveResult(SyncStatus.PENDING_LOCKED,
                              "Saved safely to the working copy. The Excel file is open in Excel - "
                              "close it and the app will update it automatically.")
        data = self.working.read_bytes()
        if sha256_bytes(data) != self.state.get("working_hash"):
            # working copy changed on disk unexpectedly; verify it is readable before using it
            try:
                read_workbook(data)
            except WorkbookError:
                return SaveResult(SyncStatus.CONFLICT, "Working copy is damaged - not synced.")
        try:
            self.backup_original()
            atomic_write(self.original, data)
        except PermissionError:
            return SaveResult(SyncStatus.PENDING_LOCKED,
                              "Saved safely to the working copy. The Excel file is locked (probably open in Excel) - "
                              "it will be updated automatically when it is closed.")
        except OSError as e:
            return SaveResult(SyncStatus.PENDING_LOCKED,
                              f"Saved safely to the working copy. The Excel file could not be updated yet ({e}).")
        h = sha256_bytes(data)
        self.state.update(original_hash=h, working_hash=h, pending_sync=False)
        self._save_state()
        return SaveResult(SyncStatus.SYNCED, "All changes saved (working copy and Excel file).")

    def retry_sync(self) -> SaveResult | None:
        if not self.pending_sync:
            return None
        return self._sync()

    # -- external changes / conflicts ------------------------------------------
    def original_changed_externally(self) -> bool:
        if not self.original.exists():
            return False
        return sha256_file(self.original) != self.state.get("original_hash")

    def reload_from_original(self) -> tuple[Database, list[str]]:
        data = self.original.read_bytes()
        db, notes = read_workbook(data)
        atomic_write(self.working, data)
        h = sha256_bytes(data)
        self.state.update(original_hash=h, working_hash=h, pending_sync=False)
        self._save_state()
        return db, notes

    def resolve_conflict_keep_app(self, db: Database, results: list | None = None) -> SaveResult:
        """Overwrite the Excel file with the app's version (Excel version is backed up first)."""
        if self.original.exists():
            self.backup_original("excel-version-before-overwrite", force=True)
        self.state["original_hash"] = sha256_file(self.original)
        return self.save(db, results)

    def resolve_conflict_keep_excel(self) -> tuple[Database, list[str]]:
        """Use the Excel file; the app's unsynced version is kept as a backup file."""
        if self.working.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            dest = self.backup_dir / f"{self.original.stem}_{ts}_app-version-discarded.xlsx"
            atomic_write(dest, self.working.read_bytes())
        return self.reload_from_original()

    @staticmethod
    def read_backup(backup: Path) -> tuple[Database, list[str]]:
        """Load a backup into memory (it becomes the current version on the next save)."""
        return read_workbook(Path(backup).read_bytes())

    def export_copy(self, db: Database, dest: Path, results: list | None = None):
        atomic_write(Path(dest), write_workbook_bytes(db, results))
