"""Dialogs: add year, data issues, backups, conflict resolution."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt

from . import help_texts as H
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QSpinBox, QVBoxLayout)


class AddYearDialog(QDialog):
    def __init__(self, existing: list[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add price year")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Adds a new price column. Prices can be copied from an existing year\n"
                             "and increased by a percentage (e.g. expected inflation)."))
        form = QFormLayout()
        self.year = QSpinBox()
        self.year.setRange(1900, 2200)
        self.year.setValue((max(existing) + 1) if existing else datetime.now().year)
        self.copy_from = QComboBox()
        self.copy_from.addItem("(leave empty)", None)
        for y in sorted(existing, reverse=True):
            self.copy_from.addItem(str(y), y)
        if existing:
            self.copy_from.setCurrentIndex(1)
        self.increase = QDoubleSpinBox()
        self.increase.setRange(-100, 1000)
        self.increase.setDecimals(2)
        self.increase.setSuffix(" %")
        self.year.setToolTip(H.ADD_YEAR_FIELDS["year"])
        self.copy_from.setToolTip(H.ADD_YEAR_FIELDS["copy"])
        self.increase.setToolTip(H.ADD_YEAR_FIELDS["increase"])
        form.addRow("New year", self.year)
        form.addRow("Copy prices from", self.copy_from)
        form.addRow("Change prices by", self.increase)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.existing = existing

    def _ok(self):
        if self.year.value() in self.existing:
            QMessageBox.warning(self, "Add year", f"Year {self.year.value()} already exists.")
            return
        self.accept()

    def values(self):
        return self.year.value(), self.copy_from.currentData(), self.increase.value()


class IssuesDialog(QDialog):
    def __init__(self, issues, on_jump, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data check")
        self.resize(820, 460)
        lay = QVBoxLayout(self)
        errs = sum(1 for i in issues if i.level == "error")
        lay.addWidget(QLabel(f"<b>{errs} error(s), {len(issues) - errs} warning(s).</b> "
                             "Double-click an entry to go to the cell. Configurations with errors show "
                             "'Error' in the results."
                             if issues else "<b>No problems found. All data is consistent.</b>"))
        self.list = QListWidget()
        for i in issues:
            it = QListWidgetItem(("⛔ " if i.level == "error" else "⚠ ") + str(i).split("] ", 1)[-1])
            it.setData(Qt.UserRole, i)
            self.list.addItem(it)
        self.list.setToolTip(H.ISSUE_LIST)
        self.list.itemDoubleClicked.connect(lambda it: (on_jump(it.data(Qt.UserRole)), self.accept()))
        lay.addWidget(self.list, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


class BackupsDialog(QDialog):
    def __init__(self, backups: list[Path], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backups")
        self.resize(640, 420)
        self.selected: Path | None = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("A copy of the Excel file is stored before it is overwritten (at most every 10 "
                             "minutes, and always before a conflict is resolved).\nRestoring loads the backup "
                             "into the app; it becomes the current version when saved (the current version is "
                             "backed up as well)."))
        self.list = QListWidget()
        for p in backups:
            dt = datetime.fromtimestamp(p.stat().st_mtime)
            it = QListWidgetItem(f"{dt:%Y-%m-%d %H:%M:%S}    {p.name}")
            it.setData(Qt.UserRole, str(p))
            self.list.addItem(it)
        self.list.setToolTip(H.BACKUP_LIST)
        lay.addWidget(self.list, 1)
        bb = QDialogButtonBox()
        self.restore = QPushButton("Restore selected")
        self.restore.setToolTip(H.tip("Restore selected", "Loads the selected backup into the app and saves it as "
                                      "the current version (the current one is backed up first).",
                                      "Undo yesterday's accidental deletion of all walnut prices."))
        bb.addButton(self.restore, QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Close)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        it = self.list.currentItem()
        if it is None:
            return
        self.selected = Path(it.data(Qt.UserRole))
        self.accept()


def ask_conflict(parent) -> str:
    """Return 'app' or 'excel'. Both versions are always backed up."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Excel file changed")
    box.setText("The Excel database was changed outside the app while the app also has newer changes.")
    box.setInformativeText("Which version do you want to keep?\n\nThe other version is NOT lost: it is saved "
                           "in the 'Backups' folder.")
    b_app = box.addButton("Keep app version", QMessageBox.AcceptRole)
    b_xl = box.addButton("Keep Excel version", QMessageBox.DestructiveRole)
    b_app.setToolTip(H.tip("Keep app version", "The Excel file is replaced by what you see in the app.",
                           "You changed prices in the app and someone only opened and re-saved the Excel file - "
                           "keep the app version."))
    b_xl.setToolTip(H.tip("Keep Excel version", "The app loads the Excel file; the app's unsaved changes are "
                          "stored in 'Backups'.", "Your colleague entered all 2027 prices in Excel - keep the "
                          "Excel version."))
    box.setDefaultButton(b_app)
    box.exec()
    return "excel" if box.clickedButton() is b_xl else "app"
