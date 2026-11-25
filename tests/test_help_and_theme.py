"""Every visible control explains itself with a real example, and the whole UI uses the dark theme."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (QAbstractButton, QComboBox, QDoubleSpinBox, QLineEdit, QListWidget,
                               QMessageBox, QSpinBox, QToolButton)

from profit_planner import schema as S
from profit_planner.app import create_application, open_window
from profit_planner.ui import help_texts as H
from profit_planner.ui import theme
from profit_planner.ui.controller import Controller
from profit_planner.ui.dialogs import AddYearDialog, BackupsDialog, IssuesDialog
from profit_planner.ui.results_view import COLUMNS as RESULT_COLUMNS


@pytest.fixture
def win(qtbot, db_path, monkeypatch):
    create_application([])
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(Controller, "AUTOSAVE_DELAY_MS", 50)
    w = open_window(db_path, interactive=False)
    qtbot.addWidget(w)
    yield w
    from profit_planner import app as app_mod
    for x in list(app_mod._WINDOWS):
        try:
            x.c.stop()
            x.lock.unlock()
            x.setAttribute(Qt.WA_DeleteOnClose, False)
            x.hide()
        except RuntimeError:
            pass
    app_mod._WINDOWS.clear()


def assert_help(text, where):
    assert text, f"no tooltip: {where}"
    assert "Example:" in text, f"tooltip without example: {where}"
    assert len(text) > 80, f"tooltip too short: {where}"


# --- tooltips --------------------------------------------------------------------------------
def test_toolbar_actions_and_autosave_have_help(win):
    actions = [a for a in win.findChildren(QToolButton) if a.defaultAction() and a.defaultAction().text()]
    assert len(actions) >= 9
    for b in actions:
        assert_help(b.defaultAction().toolTip(), f"toolbar '{b.defaultAction().text()}'")
    assert_help(win.autosave_cb.toolTip(), "autosave")


def test_every_tab_has_help(win):
    for i in range(win.tabs.count()):
        assert_help(win.tabs.tabToolTip(i), f"tab {win.tabs.tabText(i)}")
    inner = win._logistics_tabs
    for i in range(inner.count()):
        assert_help(inner.tabToolTip(i), f"inner tab {inner.tabText(i)}")


def test_every_button_input_and_checkbox_has_help(win):
    kinds = (QAbstractButton, QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QListWidget)
    missing = []
    for w in win.findChildren(QAbstractButton) + win.findChildren(QComboBox) + win.findChildren(QSpinBox) + \
            win.findChildren(QDoubleSpinBox) + win.findChildren(QLineEdit) + win.findChildren(QListWidget):
        if not isinstance(w, kinds) or isinstance(w, QToolButton):
            continue
        if w.parent() is not None and w.parent().metaObject().className() in (
                "QComboBox", "QSpinBox", "QDoubleSpinBox", "QAbstractSpinBox", "QTabBar", "QScrollBar"):
            continue  # internal sub-widgets
        if isinstance(w, QLineEdit) and isinstance(w.parent(), (QComboBox, QSpinBox, QDoubleSpinBox)):
            continue
        if w.objectName().startswith("qt_"):
            continue
        if not w.toolTip() or "Example:" not in w.toolTip():
            missing.append(f"{type(w).__name__} '{getattr(w, 'text', lambda: '')()}'")
    # the status-bar issues button has help too
    assert "Example:" in win.issues_btn.toolTip()
    assert not missing, missing


def test_every_column_header_of_every_table_has_help(win):
    for sheet, (_tab, ed) in win.editors.items():
        m = ed.model
        if ed.child:
            parent = S.SPECS[sheet].parent[1]
            ed.set_parent_key(win.c.db[parent].rows[0][S.SPECS[parent].key])
        for c in range(m.columnCount()):
            assert_help(m.headerData(c, Qt.Horizontal, Qt.ToolTipRole), f"{sheet} / {m.column_name(c)}")


def test_all_schema_columns_have_specific_examples():
    missing = [(n, c) for n in S.SPECS for c in S.SPECS[n].column_names if (n, c) not in H.COLUMN_EXAMPLES]
    assert not missing


def test_new_year_and_extra_columns_get_help(win):
    win.c.add_year(S.MATERIALS, 2030, None, 0)
    m = win.editors[S.MATERIALS][1].model
    assert_help(m.headerData(m.column_index("2030"), Qt.Horizontal, Qt.ToolTipRole), "year column")
    win.c.db[S.TOOLS].extra_columns.append("My column")
    for r in win.c.db[S.TOOLS].rows:
        r["My column"] = None
    win.c.changed(S.TOOLS)
    m = win.editors[S.TOOLS][1].model
    assert_help(m.headerData(m.column_index("My column"), Qt.Horizontal, Qt.ToolTipRole), "extra column")


def test_results_and_explorer_help(win):
    rv = win.results_view
    for k in (rv.k_gross, rv.k_net, rv.k_year, rv.k_start, rv.k_liab):
        assert_help(k.toolTip(), f"KPI {k.t.text()}")
    assert_help(rv.bar.toolTip(), "breakdown bar")
    for c in range(len(RESULT_COLUMNS)):
        assert_help(rv.model.headerData(c, Qt.Horizontal, Qt.ToolTipRole), RESULT_COLUMNS[c][0])
    assert_help(rv.lines.item(0, 0).toolTip(), "breakdown line")
    assert_help(rv.side.item(0, 0).toolTip(), "startup line")
    assert "Double-click" in rv.model.data(rv.model.index(0, 0), Qt.ToolTipRole)
    ex = win.explorer
    for j in range(ex.table.columnCount()):
        assert_help(ex.table.horizontalHeaderItem(j).toolTip(), f"explorer column {j}")


def test_dialog_help(qtbot, win):
    d = AddYearDialog([2025, 2026])
    for w in (d.year, d.copy_from, d.increase):
        assert_help(w.toolTip(), "add year dialog")
    d2 = IssuesDialog(win.c.issues, lambda i: None)
    assert_help(d2.list.toolTip(), "issues dialog")
    d3 = BackupsDialog([])
    assert_help(d3.list.toolTip(), "backups list")
    assert_help(d3.restore.toolTip(), "restore button")
    for x in (d, d2, d3):
        x.deleteLater()


def test_tooltip_text_is_escaped():
    t = H.tip("A <b>", "x < y & z", "1 > 0")
    assert "&lt;b&gt;" in t and "x &lt; y &amp; z" in t and "1 &gt; 0" in t


# --- dark theme --------------------------------------------------------------------------------
def _lum(hex_color):
    c = QColor(hex_color)

    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_application_palette_is_dark(win):
    from PySide6.QtWidgets import QApplication
    pal = QApplication.instance().palette()
    assert pal.color(QPalette.Window).lightness() < 50
    assert pal.color(QPalette.Base).lightness() < 50
    assert pal.color(QPalette.Text).lightness() > 200
    assert win.palette().color(QPalette.Window).lightness() < 50


@pytest.mark.parametrize("fg, bg", [
    (theme.TEXT, theme.BG), (theme.TEXT, theme.SURFACE), (theme.TEXT, theme.SURFACE_ALT),
    (theme.TEXT, theme.RAISED), (theme.TEXT_MUTED, theme.BG), (theme.TEXT_MUTED, theme.SURFACE),
    (theme.ACCENT_TEXT, theme.BG), (theme.GOOD, theme.SURFACE), (theme.BAD, theme.SURFACE),
    (theme.WARN, theme.SURFACE), (theme.INFO, theme.SURFACE), (theme.PURPLE, theme.SURFACE),
    (theme.TEXT, theme.GOOD_BG), (theme.TEXT, theme.BAD_BG), (theme.TEXT, theme.WARN_BG),
    ("#FFFFFF", theme.ACCENT_DIM), ("#0B1220", theme.ACCENT), (theme.TEXT, "#252B33"),
])
def test_text_contrast_meets_wcag_aa(fg, bg):
    assert contrast(fg, bg) >= 4.5, f"{fg} on {bg}: {contrast(fg, bg):.2f}"


def test_no_light_colours_left_in_ui_code():
    """All UI colours must come from theme.py (guards against white backgrounds sneaking back in)."""
    import pathlib
    import re
    ui = pathlib.Path(__file__).resolve().parents[1] / "main" / "profit_planner" / "ui"
    offenders = []
    for f in ui.glob("*.py"):
        if f.name == "theme.py":
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"['\"]#[0-9A-Fa-f]{3,8}['\"]|QColor\(\s*['\"](white|black)", line):
                offenders.append(f"{f.name}:{n}: {line.strip()}")
    assert not offenders, offenders


@pytest.mark.parametrize("name", list(theme.SEGMENTS))
def test_breakdown_bar_labels_readable(name):
    bg = theme.SEGMENTS[name]
    assert contrast(theme.text_on(bg), bg) >= 4.5
