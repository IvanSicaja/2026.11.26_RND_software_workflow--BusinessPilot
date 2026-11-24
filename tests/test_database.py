import random

import pytest

from profit_planner import schema as S
from profit_planner.calc import Engine
from profit_planner.database import Col, coerce
from profit_planner.excel_io import read_workbook, write_workbook_bytes
from profit_planner.seed import build_seed_database


@pytest.mark.parametrize("raw, expected", [
    (12, 12), (12.5, 12.5), ("12,5", 12.5), ("1'234.50", 1234.5), ("1.234,50", 1234.5),
    ("1,234.50", 1234.5), (" 8.1 % ", 8.1), ("CHF 20", 20), ("20 EUR", 20), ("-3", -3),
])
def test_number_parsing(raw, expected):
    v, err = coerce(Col("x", S.NUMBER), raw)
    assert err is None and v == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["abc", "1.2.3,4,5", "nan", "inf", True])
def test_number_errors_keep_raw(raw):
    v, err = coerce(Col("x", S.NUMBER), raw)
    assert err is not None and v == raw


def test_integer_and_bool_and_choice():
    assert coerce(Col("x", S.INTEGER), "3,0") == (3, None)
    assert coerce(Col("x", S.INTEGER), 2.5)[1] is not None
    for t in ("yes", "Y", "da", "TRUE", 1, "ja"):
        assert coerce(Col("b", S.BOOL), t) == (True, None)
    for f in ("no", "ne", "false", 0):
        assert coerce(Col("b", S.BOOL), f) == (False, None)
    assert coerce(Col("b", S.BOOL), "maybe")[1] is not None
    assert coerce(Col("c", S.CHOICE, choices=("B2C", "B2B")), "b2b") == ("B2B", None)
    assert coerce(Col("c", S.CHOICE, choices=("B2C", "B2B")), "x")[1] is not None
    assert coerce(Col("Currency", S.REF, ref=S.FX), " chf ") == ("CHF", None)
    assert coerce(Col("Origin", S.LOCATION), "western balkans") == ("Western Balkans", None)
    assert coerce(Col("x", S.TEXT), "   ") == (None, None)


def test_validation_finds_problems():
    db = build_seed_database()
    db[S.MATERIALS].rows.append(dict(db[S.MATERIALS].rows[0]))                 # duplicate ID
    db[S.CONFIGS].find("CFG-001")["Product ID"] = "MISSING"                    # bad reference
    db[S.COUNTRIES].find("CH")["VAT Standard Rate (%)"] = 150                  # out of range
    db[S.TOOLS].find("TOOL-DRILL")["Purchase Price"] = None                    # required
    db[S.SHIPPING].rows[0]["Origin"] = "Mars"                                  # bad location
    db[S.CONFIGS].find("CFG-002")["Company Type ID"] = "DE-GMBH"               # HQ mismatch
    db.set_setting("Reporting Currency", "XYZ")
    msgs = [str(i) for i in db.validate()]
    text = "\n".join(msgs)
    assert "duplicate ID 'MAT-OAK'" in text
    assert "'MISSING' does not exist" in text
    assert "at most 100" in text
    assert "Tools, row" in text and "required" in text
    assert "'Mars' is not a country code" in text
    assert "belongs to DE, not to HQ country CH" in text
    assert "reporting currency 'XYZ'" in text


def test_issue_location_uses_excel_row_numbers():
    db = build_seed_database()
    db[S.TOOLS].rows[0]["Purchase Price"] = "x"
    issue = [i for i in db.validate() if i.sheet == S.TOOLS][0]
    assert "row 2" in issue.location()


def test_rename_key_updates_all_references():
    db = build_seed_database()
    n = db.rename_key(S.MATERIALS, "MAT-OAK", "MAT-OAK-40")
    db[S.MATERIALS].find("MAT-OAK")["Material ID"] = "MAT-OAK-40"
    assert n == 1
    assert db[S.PRODUCT_MATERIALS].rows[0]["Material ID"] == "MAT-OAK-40"
    n = db.rename_key(S.COUNTRIES, "CH", "SZ")
    db[S.COUNTRIES].find("CH")["Country Code"] = "SZ"
    assert n > 5   # configurations, company types, shipping and customs locations
    assert [str(i) for i in db.validate()] == []
    assert all(r.ok for r in Engine(db).calculate_all())


def test_cascade_delete_children():
    db = build_seed_database()
    n = db.delete_cascade_children(S.PRODUCTS, "PRD-OAK-DINING")
    assert n == 10 + 15
    assert not db[S.PRODUCT_MATERIALS].children("PRD-OAK-DINING")


def test_next_id():
    db = build_seed_database()
    assert db.next_id(S.CONFIGS) == "CFG-009"
    assert db.next_id(S.MATERIALS) == "MAT-001"


def test_add_and_remove_year_with_increase():
    db = build_seed_database()
    t = db[S.MATERIALS]
    t.add_year(2027, copy_from=2026, increase_pct=10)
    assert t.find("MAT-OAK")["2027"] == pytest.approx(104.5)
    with pytest.raises(ValueError):
        t.add_year(2027)
    t.remove_year(2027)
    assert 2027 not in t.years and "2027" not in t.find("MAT-OAK")
    with pytest.raises(ValueError):
        db[S.TOOLS].add_year(2027)


def test_fuzz_random_bad_data_never_crashes():
    """Random garbage in random cells: validation, calculation and save/load must never crash."""
    rnd = random.Random(42)
    values = [None, "", "abc", -1, 0, 1e12, "12,5", "yes", "XX", "CH", "EU", "*", 3.3, "  ", "PRD-OAK-DINING"]
    for _round in range(40):
        db = build_seed_database()
        for _ in range(25):
            t = db[rnd.choice(list(S.SPECS))]
            if not t.rows:
                continue
            row = rnd.choice(t.rows)
            col = rnd.choice(t.columns())
            row[col] = rnd.choice(values)
        db.validate()
        for r in Engine(db).calculate_all():
            assert r.ok or r.error
        db.ensure_default_settings()   # what SafeStore.save does before writing
        db.normalize()
        db.validate()
        for r in Engine(db).calculate_all():
            assert r.ok or r.error
        db2, _ = read_workbook(write_workbook_bytes(db))
        assert db2.to_plain() == db.to_plain()


def test_fuzz_through_safe_store(tmp_path):
    """The real save path (with verification) accepts any garbage the user may type."""
    from profit_planner.storage import SafeStore
    rnd = random.Random(7)
    s = SafeStore(tmp_path / "f.xlsx")
    db = s.open().db
    values = [None, "", "abc", -5, "1,5", "no", "*", "Western Balkans", 10**9, "\u0161\u0111\u010d\u0107\u017e", "=1+1", "bad\x0bchar", "x" * 40000]
    for _ in range(15):
        for _ in range(10):
            t = db[rnd.choice(list(S.SPECS))]
            if t.rows:
                rnd.choice(t.rows)[rnd.choice(t.columns())] = rnd.choice(values)
        s.save(db)
        assert read_workbook((tmp_path / "f.xlsx").read_bytes())[0].to_plain() == db.to_plain()
