"""Application entry point."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QLockFile, QSettings, QStandardPaths, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import APP_NAME
from .excel_io import WorkbookError
from .storage import DEFAULT_DB_NAME, SafeStore
from .ui import theme
from .ui.controller import Controller
from .ui.dialogs import ask_conflict
from .ui.main_window import MainWindow

STYLE = theme.STYLE


_WINDOWS: list = []  # keep windows alive


def default_database_path() -> Path:
    env = os.environ.get("PROFITPLANNER_DB")
    if env:
        return Path(env)
    saved = QSettings().value("database_path", "")
    if saved and Path(str(saved)).exists():
        return Path(str(saved))
    docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or str(Path.home())
    return Path(docs) / "ProfitPlanner" / DEFAULT_DB_NAME


def create_application(argv=None) -> QApplication:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setOrganizationName("ProfitPlanner")
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setPalette(theme.palette())
    f = QFont(app.font())
    if f.pointSizeF() < 9.5:
        f.setPointSizeF(10)
    app.setFont(f)
    app.setStyleSheet(STYLE)
    return app


def open_window(path: str | Path, previous=None, interactive: bool = True) -> MainWindow | None:
    """Open (or create) the database at `path` and show a main window. Returns None on failure."""
    path = Path(path)
    parent = previous
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        QMessageBox.critical(parent, APP_NAME, f"Cannot create the folder {path.parent}:\n{e}")
        return None
    store = SafeStore(path)
    store.meta_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(store.meta_dir / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.warning(parent, APP_NAME, f"This database is already open in another {APP_NAME} window:\n{path}")
        return None
    try:
        opened = store.open()
    except WorkbookError as e:
        lock.unlock()
        QMessageBox.critical(parent, APP_NAME,
                             f"The file cannot be opened as a {APP_NAME} database:\n{path}\n\n{e}\n\n"
                             "The file was not changed. Restore a version from the 'Backups' folder or open "
                             "another file.")
        return None
    except OSError as e:
        lock.unlock()
        QMessageBox.critical(parent, APP_NAME, f"Cannot access the database:\n{path}\n\n{e}")
        return None

    ctrl = Controller(store, opened.db)
    if opened.conflict:
        choice = ask_conflict(parent) if interactive else "app"
        if choice == "excel":
            ctrl.resolve_keep_excel()
        else:
            ctrl.resolve_keep_app()
    win = MainWindow(ctrl, launcher=lambda p, prev: open_window(p, prev, interactive))
    win.lock = lock
    win.setAttribute(Qt.WA_DeleteOnClose, True)
    _WINDOWS.append(win)
    win.destroyed.connect(lambda *_a, w=win: _WINDOWS.remove(w) if w in _WINDOWS else None)
    QSettings().setValue("database_path", str(path))
    win.show()
    important = [m for m in opened.messages if m]
    if important:
        win._status("info", " ".join(important[-2:]))
        if interactive and any("missing" in m.lower() or "could not" in m.lower() for m in important):
            QMessageBox.information(win, APP_NAME, "\n\n".join(important))
    return win


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    app = create_application(argv)

    def excepthook(etype, value, tb):
        text = "".join(traceback.format_exception(etype, value, tb))
        sys.__stderr__.write(text)
        try:
            QMessageBox.critical(None, APP_NAME, "An unexpected error occurred. Your data is safe (working copy "
                                 f"and backups).\n\n{etype.__name__}: {value}")
        except Exception:  # noqa: BLE001
            pass

    sys.excepthook = excepthook
    path = Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("-") else default_database_path()
    win = open_window(path)
    if win is None:
        alt, _ = QFileDialog.getOpenFileName(None, "Open database", str(path.parent), "Excel (*.xlsx)")
        if not alt or open_window(alt) is None:
            return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
