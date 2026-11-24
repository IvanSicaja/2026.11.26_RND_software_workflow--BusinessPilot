"""Application entry point."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QLockFile, QSettings, QStandardPaths, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import APP_NAME
from .excel_io import WorkbookError
from .storage import DEFAULT_DB_NAME, SafeStore
from .ui.controller import Controller
from .ui.dialogs import ask_conflict
from .ui.main_window import MainWindow

STYLE = """
QMainWindow, QWidget { font-size: 10pt; }
QToolBar { spacing: 4px; padding: 4px; border: none; border-bottom: 1px solid #D0D7E2; background: #F4F7FB; }
QToolBar QToolButton { padding: 5px 10px; border-radius: 4px; }
QToolBar QToolButton:hover { background: #DCE6F3; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 8px 16px; border: none; color: #44546A; }
QTabBar::tab:selected { color: #1F4E78; border-bottom: 3px solid #2E75B6; font-weight: bold; }
QTabBar::tab:hover { color: #1F4E78; }
QLabel#pageTitle { font-size: 15pt; font-weight: bold; color: #1F4E78; }
QLabel#sectionTitle { font-size: 11pt; color: #1F4E78; }
QLabel#hint { color: #5F6B7A; }
QPushButton { padding: 5px 12px; border: 1px solid #B8C4D4; border-radius: 4px; background: #FFFFFF; }
QPushButton:hover { background: #EEF3F9; }
QPushButton:disabled { color: #A0A8B4; }
QPushButton#primaryButton { background: #2E75B6; color: white; border-color: #2E75B6; font-weight: bold;
                            padding: 8px; }
QPushButton#primaryButton:hover { background: #1F4E78; }
QPushButton#dangerButton:hover { background: #FDE2E1; border-color: #C62828; }
QTableView { gridline-color: #E3E8EF; selection-background-color: #CFE2F7; selection-color: black;
             alternate-background-color: #F8FAFD; }
QHeaderView::section { background: #EEF2F7; padding: 4px; border: none; border-right: 1px solid #DDE3EA;
                       border-bottom: 1px solid #C9D3DF; font-weight: bold; color: #2B3A4F; }
QFrame#kpiCard { background: #F4F7FB; border: 1px solid #DCE3EC; border-radius: 6px; }
QLabel#kpiTitle { color: #5F6B7A; font-size: 9pt; }
QLabel#kpiValue { font-size: 15pt; font-weight: bold; color: #1F2D3D; }
QLabel#kpiValue[state="good"] { color: #2E7D32; }
QLabel#kpiValue[state="bad"] { color: #C62828; }
QLabel#kpiSub { color: #5F6B7A; font-size: 9pt; }
QGroupBox { font-weight: bold; border: 1px solid #DCE3EC; border-radius: 6px; margin-top: 10px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #1F4E78; }
"""


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
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#FFFFFF"))
    pal.setColor(QPalette.Base, QColor("#FFFFFF"))
    pal.setColor(QPalette.AlternateBase, QColor("#F8FAFD"))
    pal.setColor(QPalette.Text, QColor("#1F2D3D"))
    pal.setColor(QPalette.WindowText, QColor("#1F2D3D"))
    pal.setColor(QPalette.ButtonText, QColor("#1F2D3D"))
    pal.setColor(QPalette.Button, QColor("#FFFFFF"))
    pal.setColor(QPalette.Highlight, QColor("#2E75B6"))
    pal.setColor(QPalette.ToolTipBase, QColor("#FFFFE8"))
    pal.setColor(QPalette.ToolTipText, QColor("#1F2D3D"))
    app.setPalette(pal)
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
