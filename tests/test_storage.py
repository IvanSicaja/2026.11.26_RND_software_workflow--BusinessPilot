"""Safety of the Excel storage: verified saves, crash simulation, locks, conflicts, manual Excel edits."""
import os

import pytest
from openpyxl import load_workbook

from profit_planner import schema as S
from profit_planner import storage as st
from profit_planner.excel_io import WorkbookError, read_workbook, write_workbook_bytes
from profit_planner.seed import build_seed_database
from profit_planner.storage import SafeStore, SaveError, SyncStatus, sha256_file


def open_store(path):
    s = SafeStore(path)
    return s, s.open()


def edit_in_excel(path, sheet, row, column, value):
    """Simulate a user editing the file in Excel (openpyxl, like a manual save)."""
    wb = load_workbook(path)
    ws = wb[sheet]
    headers = [c.value for c in ws[1]]
    if column not in headers:
        ws.cell(row=1, column=len(headers) + 1, value=column)
        headers.append(column)
    ws.cell(row=row, column=headers.index(column) + 1, value=value)
    wb.save(path)


def test_new_database_created_and_synced(db_path):
    s, res = open_store(db_path)
    assert db_path.exists() and s.working.exists()
    assert res.status == SyncStatus.SYNCED
    assert sha256_file(db_path) == sha256_file(s.working)
    assert not s.pending_sync
    assert len(res.db[S.CONFIGS].rows) == 8


def test_round_trip_is_exact():
    db = build_seed_database()
    db2, notes = read_workbook(write_workbook_bytes(db))
    assert db2.to_plain() == db.to_plain()
    assert notes == []


def test_save_updates_working_then_original_and_backups(db_path, monkeypatch):
    s, res = open_store(db_path)
    db = res.db
    db[S.MATERIALS].find("MAT-OAK")["2026"] = 123.45
    r = s.save(db)
    assert r.status == SyncStatus.SYNCED
    for p in (db_path, s.working):
        assert read_workbook(p.read_bytes())[0][S.MATERIALS].find("MAT-OAK")["2026"] == 123.45
    assert len(s.list_backups()) == 1       # backup of the previous original
    db[S.MATERIALS].find("MAT-OAK")["2026"] = 124
    s.save(db)
    assert len(s.list_backups()) == 1       # throttled (max one backup per 10 minutes)
    monkeypatch.setattr(st, "BACKUP_INTERVAL_SECONDS", 0)
    db[S.MATERIALS].find("MAT-OAK")["2026"] = 125
    s.save(db)
    assert len(s.list_backups()) == 2


def test_backups_are_pruned(db_path, monkeypatch):
    monkeypatch.setattr(st, "BACKUP_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(st, "MAX_BACKUPS", 3)
    s, res = open_store(db_path)
    for i in range(6):
        res.db.set_setting("Company Name", f"C{i}")
        s.save(res.db)
    assert len(s.list_backups()) == 3


def test_manual_excel_edit_is_loaded_on_next_start(db_path):
    s, res = open_store(db_path)
    # row 2 of Materials = MAT-OAK; user types a price with comma decimal and adds a new year column
    edit_in_excel(db_path, S.MATERIALS, 2, "2026", "99,5")
    edit_in_excel(db_path, S.MATERIALS, 2, "2027", 110)
    edit_in_excel(db_path, S.CONFIGS, 2, "Active", "no")
    s2, res2 = open_store(db_path)
    db = res2.db
    assert db[S.MATERIALS].find("MAT-OAK")["2026"] == 99.5
    assert 2027 in db[S.MATERIALS].years
    assert db[S.MATERIALS].find("MAT-OAK")["2027"] == 110
    assert db[S.CONFIGS].find("CFG-001")["Active"] is False
    assert any("Excel" in m for m in res2.messages)
    assert sha256_file(s2.working) == sha256_file(db_path)


def test_manual_excel_new_rows_and_extra_columns_preserved(db_path):
    s, res = open_store(db_path)
    wb = load_workbook(db_path)
    ws = wb[S.MATERIALS]
    n = ws.max_row + 1
    ws.cell(row=n, column=1, value="MAT-NEW")
    ws.cell(row=n, column=2, value="New material")
    ws.cell(row=n, column=4, value="kg")
    ws.cell(row=n, column=5, value="eur")
    ws.cell(row=1, column=ws.max_column + 1, value="My Comment Column")
    ws.cell(row=n, column=ws.max_column, value="keep me")
    wb.save(db_path)
    s2, res2 = open_store(db_path)
    t = res2.db[S.MATERIALS]
    row = t.find("MAT-NEW")
    assert row is not None and row["Currency"] == "EUR"
    assert "My Comment Column" in t.extra_columns and row["My Comment Column"] == "keep me"
    s2.save(res2.db)
    db3 = read_workbook(db_path.read_bytes())[0]
    assert db3[S.MATERIALS].find("MAT-NEW")["My Comment Column"] == "keep me"


def test_missing_sheet_and_column_are_recreated(db_path):
    s, res = open_store(db_path)
    wb = load_workbook(db_path)
    del wb[S.PAYMENT]
    ws = wb[S.TOOLS]
    ws.delete_cols(7)  # Notes
    wb.save(db_path)
    s2, res2 = open_store(db_path)
    assert any("Payment Methods" in m for m in res2.messages)
    assert any("'Notes'" in m for m in res2.messages)
    assert "Notes" in res2.db[S.TOOLS].columns()
    # configurations referencing removed payment methods are reported, not crashing
    assert any(i.sheet == S.CONFIGS and i.column == "Payment Method ID" for i in res2.db.validate())


def test_power_loss_after_working_copy_before_original(db_path, monkeypatch):
    s, res = open_store(db_path)
    original_before = db_path.read_bytes()
    res.db.set_setting("Company Name", "After crash")
    real = st.atomic_write

    def crash_on_original(path, data, retries=3):
        if os.path.abspath(path) == os.path.abspath(db_path):
            raise KeyboardInterrupt("power loss")
        return real(path, data, retries)

    monkeypatch.setattr(st, "atomic_write", crash_on_original)
    with pytest.raises(KeyboardInterrupt):
        s.save(res.db)
    monkeypatch.setattr(st, "atomic_write", real)
    assert db_path.read_bytes() == original_before          # original untouched
    s2, res2 = open_store(db_path)                           # next start finishes the job
    assert res2.db.setting("Company Name") == "After crash"
    assert read_workbook(db_path.read_bytes())[0].setting("Company Name") == "After crash"
    assert not s2.pending_sync


def test_power_loss_while_writing_working_copy(db_path, monkeypatch):
    s, res = open_store(db_path)
    orig, work = db_path.read_bytes(), s.working.read_bytes()
    res.db.set_setting("Company Name", "Never written")
    real_replace = os.replace

    def failing_replace(src, dst):
        if str(dst).endswith("working_copy.xlsx"):
            raise OSError("disk unplugged")
        return real_replace(src, dst)

    monkeypatch.setattr(st.os, "replace", failing_replace)
    with pytest.raises(OSError):
        s.save(res.db)
    monkeypatch.setattr(st.os, "replace", real_replace)
    assert db_path.read_bytes() == orig and s.working.read_bytes() == work
    s2, res2 = open_store(db_path)
    assert res2.db.setting("Company Name") == "My Furniture Company"


def test_truncated_temp_file_never_replaces(db_path):
    s, res = open_store(db_path)
    (s.working.parent / "working_copy.xlsx.tmp").write_bytes(b"half written garbage")
    s2, res2 = open_store(db_path)
    assert res2.db.setting("Company Name") == "My Furniture Company"


def test_verification_failure_writes_nothing(db_path, monkeypatch):
    s, res = open_store(db_path)
    orig, work = db_path.read_bytes(), s.working.read_bytes()
    bad = build_seed_database()
    bad.set_setting("Company Name", "Different")
    monkeypatch.setattr(st, "read_workbook", lambda data: (bad, []))
    res.db.set_setting("Company Name", "Mine")
    with pytest.raises(SaveError):
        s.save(res.db)
    assert db_path.read_bytes() == orig and s.working.read_bytes() == work


def test_excel_lock_file_keeps_changes_pending(db_path):
    s, res = open_store(db_path)
    orig = db_path.read_bytes()
    lock = db_path.parent / ("~$" + db_path.name)
    lock.write_text("excel")
    res.db.set_setting("Company Name", "While Excel open")
    r = s.save(res.db)
    assert r.status == SyncStatus.PENDING_LOCKED and s.pending_sync
    assert db_path.read_bytes() == orig
    assert read_workbook(s.working.read_bytes())[0].setting("Company Name") == "While Excel open"
    lock.unlink()
    r2 = s.retry_sync()
    assert r2.status == SyncStatus.SYNCED
    assert read_workbook(db_path.read_bytes())[0].setting("Company Name") == "While Excel open"


def test_windows_permission_error_keeps_changes_pending(db_path, monkeypatch):
    s, res = open_store(db_path)
    real_replace = os.replace

    def locked(src, dst):
        if os.path.abspath(dst) == os.path.abspath(db_path):
            raise PermissionError("file is open in another program")
        return real_replace(src, dst)

    monkeypatch.setattr(st.os, "replace", locked)
    monkeypatch.setattr(st.time, "sleep", lambda s: None)
    res.db.set_setting("Company Name", "Locked")
    r = s.save(res.db)
    assert r.status == SyncStatus.PENDING_LOCKED
    assert not (db_path.parent / (db_path.name + ".tmp")).exists()
    monkeypatch.setattr(st.os, "replace", real_replace)
    s2, res2 = open_store(db_path)        # next start syncs
    assert res2.db.setting("Company Name") == "Locked"
    assert read_workbook(db_path.read_bytes())[0].setting("Company Name") == "Locked"


def make_conflict(db_path):
    s, res = open_store(db_path)
    lock = db_path.parent / ("~$" + db_path.name)
    lock.write_text("x")
    res.db.set_setting("Company Name", "App version")
    assert s.save(res.db).status == SyncStatus.PENDING_LOCKED
    lock.unlink()
    edit_in_excel(db_path, S.SETTINGS, 2, "Value", "Excel version")   # row 2 = Company Name
    return s, res


def test_conflict_detected_and_keep_app(db_path):
    s, res = make_conflict(db_path)
    assert s.retry_sync().status == SyncStatus.CONFLICT
    s2, res2 = open_store(db_path)
    assert res2.conflict and res2.excel_db.setting("Company Name") == "Excel version"
    assert res2.db.setting("Company Name") == "App version"
    r = s2.resolve_conflict_keep_app(res2.db)
    assert r.status == SyncStatus.SYNCED
    assert read_workbook(db_path.read_bytes())[0].setting("Company Name") == "App version"
    names = [p.name for p in s2.list_backups()]
    assert any("excel-version" in n for n in names)
    kept = [p for p in s2.list_backups() if "excel-version" in p.name][0]
    assert read_workbook(kept.read_bytes())[0].setting("Company Name") == "Excel version"


def test_conflict_keep_excel(db_path):
    s, res = make_conflict(db_path)
    db, _n = s.resolve_conflict_keep_excel()
    assert db.setting("Company Name") == "Excel version"
    assert not s.pending_sync
    app_copy = [p for p in s.list_backups() if "app-version" in p.name][0]
    assert read_workbook(app_copy.read_bytes())[0].setting("Company Name") == "App version"


def test_corrupt_original_falls_back_to_working(db_path):
    s, res = open_store(db_path)
    db_path.write_bytes(b"not an excel file")
    s2, res2 = open_store(db_path)
    assert res2.status == SyncStatus.CONFLICT
    assert res2.db.setting("Company Name") == "My Furniture Company"
    r = s2.resolve_conflict_keep_app(res2.db)
    assert r.status == SyncStatus.SYNCED
    assert read_workbook(db_path.read_bytes())[0].setting("Company Name") == "My Furniture Company"
    assert any("excel-version" in p.name for p in s2.list_backups())   # the broken file was kept


def test_corrupt_working_copy_rebuilt_from_original(db_path):
    s, res = open_store(db_path)
    s.working.write_bytes(b"garbage")
    s2, res2 = open_store(db_path)
    assert res2.db.setting("Company Name") == "My Furniture Company"
    assert sha256_file(s2.working) == sha256_file(db_path)


def test_corrupt_working_with_pending_flag(db_path):
    s, res = open_store(db_path)
    s.state["pending_sync"] = True
    s._save_state()
    s.working.write_bytes(b"garbage")
    s2, res2 = open_store(db_path)
    assert res2.db.setting("Company Name") == "My Furniture Company"


def test_original_deleted_is_restored(db_path):
    s, res = open_store(db_path)
    db_path.unlink()
    s2, res2 = open_store(db_path)
    assert db_path.exists()
    assert any("restored" in m for m in res2.messages)


def test_state_file_lost(db_path):
    s, res = open_store(db_path)
    s.state_path.unlink()
    s2, res2 = open_store(db_path)
    assert res2.db.setting("Company Name") == "My Furniture Company"


def test_both_unreadable_raises(db_path):
    s, res = open_store(db_path)
    db_path.write_bytes(b"x")
    s.working.write_bytes(b"y")
    with pytest.raises(WorkbookError):
        SafeStore(db_path).open()


def test_non_profit_planner_workbook_rejected(tmp_path):
    from openpyxl import Workbook
    p = tmp_path / "other.xlsx"
    wb = Workbook()
    wb.active["A1"] = "hello"
    wb.save(p)
    with pytest.raises(WorkbookError):
        SafeStore(p).open()
    assert load_workbook(p).active["A1"].value == "hello"   # untouched


def test_external_change_detection_and_reload(db_path):
    s, res = open_store(db_path)
    assert not s.original_changed_externally()
    edit_in_excel(db_path, S.SETTINGS, 2, "Value", "Edited")
    assert s.original_changed_externally()
    db, _ = s.reload_from_original()
    assert db.setting("Company Name") == "Edited"
    assert not s.original_changed_externally()


def test_results_snapshot_sheet_written_and_ignored(db_path):
    from profit_planner.calc import Engine
    s, res = open_store(db_path)
    results = Engine(res.db).calculate_all()
    s.save(res.db, results)
    wb = load_workbook(db_path)
    assert S.RESULTS in wb.sheetnames and S.INSTRUCTIONS in wb.sheetnames
    assert wb[S.RESULTS].max_row == 2 + len(results)
    db2, notes = read_workbook(db_path.read_bytes())
    assert db2.to_plain() == res.db.to_plain()


@pytest.mark.skipif(__import__("shutil").which("soffice") is None, reason="LibreOffice not installed")
def test_file_survives_resave_in_spreadsheet_app(db_path, tmp_path):
    """Open + save the database in a real spreadsheet program (LibreOffice) and read it back."""
    import subprocess
    s, res = open_store(db_path)
    out = tmp_path / "resaved"
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir",
                    str(out), str(db_path)], check=True, timeout=180, capture_output=True)
    db2, notes = read_workbook((out / db_path.name).read_bytes())
    assert db2.to_plain() == res.db.to_plain()
