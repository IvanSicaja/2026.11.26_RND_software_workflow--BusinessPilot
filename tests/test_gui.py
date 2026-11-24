"""End-to-end GUI tests (run headless with QT_QPA_PLATFORM=offscreen)."""
import pytest
from openpyxl import load_workbook
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QMessageBox, QStyleOptionViewItem

from profit_planner import schema as S
from profit_planner.app import create_application, open_window
from profit_planner.excel_io import read_workbook
from profit_planner.ui import main_window as mw_mod
from profit_planner.ui.controller import Controller


@pytest.fixture
def win(qtbot, db_path, monkeypatch):
    create_application([])
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(Controller, "AUTOSAVE_DELAY_MS", 50)
    w = open_window(db_path, interactive=False)
    assert w is not None
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


def saved_db(w):
    return read_workbook(w.c.database_path.read_bytes())[0]


def editor(w, sheet):
    return w.editors[sheet][1]


def set_cell(ed, row_key, column, value):
    m = ed.model
    t = m.table
    src = next(i for i, r in enumerate(t.rows) if r.get(t.spec.key) == row_key)
    idx = m.index(m.view_row(src), m.column_index(column))
    return m.setData(idx, value, Qt.EditRole)


def test_window_opens_with_all_tabs_and_results(win):
    assert win.tabs.count() == 10
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
    rv = win.results_view
    assert rv.model.rowCount() == 8
    assert rv.current_result() is not None
    assert "OK" in win.issues_btn.text() or "no problems" in win.issues_btn.text()


def test_edit_material_price_updates_results_and_autosaves(win, qtbot):
    before = {r.config_id: r.net_to_owner for r in win.c.results}
    ed = editor(win, S.MATERIALS)
    assert set_cell(ed, "MAT-OAK", "2026", "150,00")
    after = {r.config_id: r.net_to_owner for r in win.c.results}
    assert after["CFG-001"] < before["CFG-001"]
    qtbot.waitUntil(lambda: not win.c.dirty, timeout=5000)
    assert saved_db(win)[S.MATERIALS].find("MAT-OAK")["2026"] == 150


def test_invalid_input_is_flagged_not_lost(win, qtbot):
    ed = editor(win, S.TOOLS)
    assert set_cell(ed, "TOOL-DRILL", "Purchase Price", "abc")
    assert any(i.sheet == S.TOOLS for i in win.c.issues)
    assert "error" in win.issues_btn.text()
    row = win.c.db[S.TOOLS].find("TOOL-DRILL")
    assert row["Purchase Price"] == "abc"
    m = ed.model
    idx = m.index(m.view_row(win.c.db[S.TOOLS].rows.index(row)), m.column_index("Purchase Price"))
    assert m.data(idx, Qt.ToolTipRole)
    assert m.data(idx, Qt.BackgroundRole) is not None
    qtbot.waitUntil(lambda: not win.c.dirty, timeout=5000)
    assert saved_db(win)[S.TOOLS].find("TOOL-DRILL")["Purchase Price"] == "abc"
    # configurations using tools now show an error instead of crashing
    assert any(not r.ok for r in win.c.results)


def test_rename_id_cascades(win):
    ed = editor(win, S.PRODUCTS)
    assert set_cell(ed, "PRD-OAK-DINING", "Product ID", "PRD-OAK-TABLE")
    db = win.c.db
    assert db[S.CONFIGS].find("CFG-001")["Product ID"] == "PRD-OAK-TABLE"
    assert db[S.PRODUCT_MATERIALS].children("PRD-OAK-TABLE")
    assert all(r.ok for r in win.c.results)
    # duplicate / empty IDs are refused
    assert not set_cell(ed, "PRD-OAK-TABLE", "Product ID", "PRD-WALNUT-DESK")
    assert not set_cell(ed, "PRD-OAK-TABLE", "Product ID", "")


def test_add_duplicate_delete_configuration(win, qtbot):
    ed = editor(win, S.CONFIGS)
    n = len(win.c.db[S.CONFIGS].rows)
    ed.add_row()
    assert len(win.c.db[S.CONFIGS].rows) == n + 1
    new = win.c.db[S.CONFIGS].rows[-1]
    assert new["Configuration ID"] == "CFG-009"
    assert any(not r.ok for r in win.c.results if r.config_id == "CFG-009")  # incomplete row -> error row
    ed.select_key("CFG-002")
    ed.duplicate_row()
    dup = win.c.db[S.CONFIGS].find("CFG-010")
    assert dup is not None and dup["Name"].endswith("(copy)")
    assert win.c.db[S.CONFIG_SERVICES].children("CFG-010")     # services were copied too
    ed.select_key("CFG-010")
    ed.delete_rows()
    assert win.c.db[S.CONFIGS].find("CFG-010") is None
    assert not win.c.db[S.CONFIG_SERVICES].children("CFG-010")
    qtbot.waitUntil(lambda: not win.c.dirty, timeout=5000)


def test_delete_blocked_when_referenced(win):
    ed = editor(win, S.MATERIALS)
    ed.select_key("MAT-OAK")
    ed.delete_rows()
    assert win.c.db[S.MATERIALS].find("MAT-OAK") is not None
    ed.select_key("MAT-MDF")      # unused material can be deleted
    ed.delete_rows()
    assert win.c.db[S.MATERIALS].find("MAT-MDF") is None


def test_child_tables_follow_selection(win):
    prod = editor(win, S.PRODUCTS)
    bom = editor(win, S.PRODUCT_MATERIALS)
    prod.select_key("PRD-PLY-SIDE")
    assert bom.model.rowCount() == 6
    bom.add_row()
    assert win.c.db[S.PRODUCT_MATERIALS].rows[-1]["Product ID"] == "PRD-PLY-SIDE"
    assert "PRD-PLY-SIDE" in win.product_cost.text()
    cfg = editor(win, S.CONFIGS)
    srv = editor(win, S.CONFIG_SERVICES)
    cfg.select_key("CFG-002")
    assert srv.model.rowCount() == 1
    cfg.select_key("CFG-003")
    assert srv.model.rowCount() == 0


def test_every_cell_editor_works(win):
    """Create, fill and commit the editor of every column of every sheet."""
    for sheet, (_tab, ed) in win.editors.items():
        if ed.child:
            parent = S.SPECS[sheet].parent[1]
            pk = win.c.db[parent].rows[0][S.SPECS[parent].key]
            ed.set_parent_key(pk)
        if ed.proxy.rowCount() == 0:
            ed.add_row()
        delegate = ed.view.itemDelegate()
        for col in range(ed.proxy.columnCount()):
            idx = ed.proxy.index(0, col)
            e = delegate.createEditor(ed.view, QStyleOptionViewItem(), idx)
            delegate.setEditorData(e, idx)
            delegate.setModelData(e, ed.proxy, idx)
            assert isinstance(e, (QComboBox, QLineEdit))
            e.deleteLater()


def test_company_type_dropdown_filtered_by_hq(win):
    ed = editor(win, S.CONFIGS)
    ed.select_key("CFG-004")   # HQ = HR
    col = ed.model.column_index("Company Type ID")
    idx = ed.proxy.mapFromSource(ed.model.index(ed.model.view_row(3), col))
    e = ed.view.itemDelegate().createEditor(ed.view, QStyleOptionViewItem(), idx)
    keys = [e.itemData(i) for i in range(e.count())]
    assert keys == ["HR-OBRT", "HR-JDOO", "HR-DOO"]


def test_add_year_flows_into_configuration(win, qtbot):
    win.c.add_year(S.MATERIALS, 2027, 2026, 10)
    win.c.add_year(S.SERVICES, 2027, 2026, 10)
    assert "2027" in editor(win, S.MATERIALS).model._cols
    set_cell(editor(win, S.CONFIGS), "CFG-001", "Material Price Year", "2027")
    r = next(r for r in win.c.results if r.config_id == "CFG-001")
    assert r.ok and r.material_year == 2027 and not r.warnings
    qtbot.waitUntil(lambda: not win.c.dirty, timeout=5000)
    assert 2027 in saved_db(win)[S.MATERIALS].years
    win.c.remove_year(S.MATERIALS, 2027)
    r = next(r for r in win.c.results if r.config_id == "CFG-001")
    assert r.ok and any("used 2026" in w for w in r.warnings)


def test_explorer_compare_and_save(win):
    ex = win.explorer
    ex.run()
    assert ex.table.rowCount() == 11       # CH(3) + DE(3) + HR(3) + BA(2) legal forms
    assert "Best:" in ex.summary.text()
    nets = [r.net_to_owner for _c, r in ex.results if r.ok]
    assert nets == sorted(nets, reverse=True)
    ex.table.selectRow(0)
    new_id = ex.save_selected()
    row = win.c.db[S.CONFIGS].find(new_id)
    assert row is not None and row["Market Country"] == "DE"
    assert next(r for r in win.c.results if r.config_id == new_id).ok
    # markup mode
    ex.mode_markup.setChecked(True)
    ex.run()
    assert all(r.ok for _c, r in ex.results)


def test_results_filters_and_export(win, tmp_path):
    rv = win.results_view
    i = rv.product_filter.findData("PRD-WALNUT-DESK")
    rv.product_filter.setCurrentIndex(i)
    assert rv.model.rowCount() == 1
    rv.product_filter.setCurrentIndex(0)
    set_cell(editor(win, S.CONFIGS), "CFG-001", "Active", "No")
    assert rv.model.rowCount() == 7
    rv.only_active.setChecked(False)
    assert rv.model.rowCount() == 8
    out = tmp_path / "report.xlsx"
    assert rv.export(str(out))
    wb = load_workbook(out)
    assert "Summary" in wb.sheetnames and "CFG-001" in wb.sheetnames


def test_external_excel_edit_is_picked_up(win, qtbot):
    win.c.save()
    path = win.c.database_path
    wb = load_workbook(path)
    wb[S.SETTINGS]["B2"] = "Changed in Excel"
    wb.save(path)
    win.c.poll()
    assert win.c.db.setting("Company Name") == "Changed in Excel"
    assert "Changed in Excel" in win.windowTitle()


def test_conflict_dialog_path(win, monkeypatch):
    choices = []
    monkeypatch.setattr(mw_mod, "ask_conflict", lambda parent: choices.append(1) or "excel")
    win.c.autosave = False
    set_cell(editor(win, S.SETTINGS), "Company Name", "Value", "App side")
    path = win.c.database_path
    wb = load_workbook(path)
    wb[S.SETTINGS]["B2"] = "Excel side"
    wb.save(path)
    win.c.poll()
    assert choices and win.c.db.setting("Company Name") == "Excel side"
    assert any("app-version" in p.name for p in win.c.store.list_backups())


def test_issue_jump_selects_cell(win):
    set_cell(editor(win, S.TOOLS), "TOOL-GRINDER", "Useful Life (years)", "-1")
    issue = next(i for i in win.c.issues if i.sheet == S.TOOLS)
    win.jump_to_issue(issue)
    ed = editor(win, S.TOOLS)
    assert ed.current_key() == "TOOL-GRINDER"
    # child-table issue selects the parent first
    win.c.db[S.PRODUCT_MATERIALS].rows[12]["Quantity"] = "x"
    win.c.changed()
    issue = next(i for i in win.c.issues if i.sheet == S.PRODUCT_MATERIALS)
    win.jump_to_issue(issue)
    assert editor(win, S.PRODUCTS).current_key() == win.c.db[S.PRODUCT_MATERIALS].rows[12]["Product ID"]


def test_close_saves_pending_changes(win, qtbot):
    win.c.autosave = False
    set_cell(editor(win, S.SETTINGS), "Company Name", "Value", "Saved on close")
    assert win.c.dirty
    path = win.c.database_path
    win.setAttribute(Qt.WA_DeleteOnClose, False)
    win.close()
    assert read_workbook(path.read_bytes())[0].setting("Company Name") == "Saved on close"


def test_second_window_on_same_db_refused(win, db_path):
    assert open_window(db_path, interactive=False) is None


def test_restore_backup(win, qtbot, monkeypatch):
    from profit_planner import storage as st
    monkeypatch.setattr(st, "BACKUP_INTERVAL_SECONDS", 0)
    set_cell(editor(win, S.SETTINGS), "Company Name", "Value", "Version A")
    win.c.save()
    set_cell(editor(win, S.SETTINGS), "Company Name", "Value", "Version B")
    win.c.save()
    backups = win.c.store.list_backups()
    target = next(b for b in backups if read_workbook(b.read_bytes())[0].setting("Company Name") == "Version A")
    db, _ = win.c.store.read_backup(target)
    win.c.replace_database(db, True)
    win.c.save()
    assert saved_db(win).setting("Company Name") == "Version A"


def test_real_keyboard_editing_in_table(win, qtbot):
    """Type into a cell like a user: select, type, Enter."""
    from PySide6.QtTest import QTest
    win.tabs.setCurrentIndex(win.editors[S.TOOLS][0])
    ed = editor(win, S.TOOLS)
    m = ed.model
    src = win.c.db[S.TOOLS].rows.index(win.c.db[S.TOOLS].find("TOOL-ROUTER"))
    idx = ed.proxy.mapFromSource(m.index(m.view_row(src), m.column_index("Purchase Price")))
    ed.view.setCurrentIndex(idx)
    ed.view.edit(idx)
    line = ed.view.viewport().findChild(QLineEdit)
    assert line is not None
    line.setText("499,90")
    QTest.keyClick(line, Qt.Key_Return)
    qtbot.waitUntil(lambda: win.c.db[S.TOOLS].find("TOOL-ROUTER")["Purchase Price"] == 499.9, timeout=3000)
    # drop-down editor commits on selection
    cidx = ed.proxy.mapFromSource(m.index(m.view_row(src), m.column_index("Currency")))
    ed.view.setCurrentIndex(cidx)
    ed.view.edit(cidx)
    cb = ed.view.viewport().findChild(QComboBox)
    assert cb is not None
    cb.setCurrentIndex(cb.findData("CHF"))
    cb.activated.emit(cb.currentIndex())
    assert win.c.db[S.TOOLS].find("TOOL-ROUTER")["Currency"] == "CHF"
