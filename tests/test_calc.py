import pytest

from profit_planner import schema as S
from profit_planner.calc import Engine
from profit_planner.seed import build_seed_database

approx = pytest.approx


def result(db, cid):
    return next(r for r in Engine(db).calculate_all() if r.config_id == cid)


def cfg(db, cid):
    return db[S.CONFIGS].find(cid)


def test_mini_db_is_valid(mini_db):
    assert [str(i) for i in mini_db.validate()] == []


def test_domestic_fixed_price_every_line(mini_db):
    r = result(mini_db, "A")
    assert r.ok, r.error
    assert r.materials == approx(54)          # 2*1.1*20 EUR + 1*5 CHF (=10 EUR)
    assert r.labour == approx(20)             # 2 h * 10 EUR
    assert r.tool_depreciation == approx(6)   # 1200 / 2 years / 100 units
    assert r.overhead == approx(12)           # 1200 / 100 units
    assert r.production_cost == approx(92)
    assert r.gross_price == approx(600)
    assert r.vat == approx(100)
    assert r.net_revenue == approx(500)
    assert r.payment_fee == approx(12.5)      # 2 % + 0.5
    assert r.commission == approx(30)         # 5 % of gross
    assert r.shipping == approx(20)           # 10 + 1 * 10 kg
    assert r.customs == approx(0)
    assert r.returns == approx(4.5)           # 10 % * (2*20 + 5)
    assert r.profit_before_tax == approx(341)
    assert r.profit_tax == approx(34.1)
    assert r.net_profit_company == approx(306.9)
    assert r.distribution_tax == approx(61.38)
    assert r.net_to_owner == approx(245.52)
    assert r.margin_pct == approx(40.92)
    assert r.annual_net_to_owner == approx(24552)
    # startup: formation 100 + max(capital 1000, tools 1200 + stock 540)
    assert r.tools_cost == approx(1200)
    assert r.stock_cost == approx(540)
    assert r.startup_total == approx(1840)
    assert r.payback_months == approx(1840 / (24552 / 12))
    assert r.warnings == []
    # the breakdown lines add up: gross - all deductions = net to owner
    assert sum(l.amount for l in r.lines if l.group in ("Deduction", "Cost", "Tax")) + r.gross_price == \
        approx(r.net_to_owner)


def test_break_even_price_gives_zero_profit(mini_db):
    r = result(mini_db, "A")
    be = r.break_even_gross
    assert be == approx(117 / (1 / 1.2 - 0.07))
    cfg(mini_db, "A")["Base Gross Price (incl. VAT)"] = be
    r2 = result(mini_db, "A")
    assert r2.profit_before_tax == approx(0, abs=1e-6)


def test_break_even_with_customs(mini_db):
    r = result(mini_db, "B")
    c = cfg(mini_db, "B")
    c["Base Gross Price (incl. VAT)"] = r.break_even_gross - r.services_gross
    c["Price Currency"] = "EUR"
    r2 = result(mini_db, "B")
    assert r2.profit_before_tax == approx(0, abs=1e-6)


def test_export_markup_services_customs(mini_db):
    r = result(mini_db, "B")
    assert r.ok, r.error
    assert r.service_labour == approx(20)
    assert r.production_cost == approx(112)
    assert r.vat_rate == approx(10)
    assert r.base_gross_price == approx(92 * 1.5 * 1.1)
    assert r.services_gross == approx(110)
    assert r.gross_price == approx(261.8)
    assert r.net_revenue == approx(238)
    assert r.shipping == approx(40)
    assert r.customs == approx(0.1 * (238 + 40) + 5)
    assert r.returns == approx(0)
    assert r.profit_before_tax == approx(53.2)
    assert r.net_to_owner == approx(53.2 * 0.9 * 0.8)


def test_sole_proprietor_region_fallback_and_missing_customs(mini_db):
    r = result(mini_db, "C")
    assert r.ok, r.error
    assert r.shipping == approx(40)            # BB -> EU region row: (15 + 0.5*10) CHF = 40 EUR
    assert r.labour == approx(80)              # 2 h * 20 CHF
    assert r.overhead == approx(12)            # 600 CHF / 100
    assert r.formation_costs == approx(100)
    assert r.customs == 0
    assert any("customs" in w for w in r.warnings)
    assert r.profit_before_tax == approx(299.5)
    assert r.social == approx(29.95)
    assert r.profit_tax == approx(53.91)
    assert r.net_to_owner == approx(215.64)
    assert r.liability.startswith("Unlimited")


def test_b2b_cross_border_no_vat_no_customs(mini_db):
    c = cfg(mini_db, "A")
    c["Market Country"] = "BB"
    c["Sale Type"] = "B2B"
    r = result(mini_db, "A")
    assert r.vat == 0 and r.gross_price == approx(600) and r.net_revenue == approx(600)
    assert r.customs == 0
    assert any("B2B" in w for w in r.warnings)


def test_b2b_domestic_keeps_vat(mini_db):
    cfg(mini_db, "A")["Sale Type"] = "B2B"
    assert result(mini_db, "A").vat == approx(100)


def test_small_business_exemption(mini_db):
    cfg(mini_db, "A")["Small-Business VAT Exemption"] = True
    r = result(mini_db, "A")
    assert r.vat == 0 and r.net_revenue == approx(600)
    # not allowed cross-border
    c = cfg(mini_db, "B")
    c["Small-Business VAT Exemption"] = True
    rb = result(mini_db, "B")
    assert rb.vat_rate == approx(10)
    assert any("exemption" in w for w in rb.warnings)


def test_year_fallback_and_missing_year(mini_db):
    cfg(mini_db, "A")["Material Price Year"] = 2027
    r = result(mini_db, "A")
    assert r.ok and any("used 2026" in w for w in r.warnings)
    cfg(mini_db, "A")["Material Price Year"] = 2025   # M2 has no price for 2025 or earlier
    r = result(mini_db, "A")
    assert not r.ok and "M2" in r.error
    cfg(mini_db, "A")["Material Price Year"] = None   # empty = latest year
    assert result(mini_db, "A").material_year == 2026


def test_material_price_change_flows_into_result(mini_db):
    before = result(mini_db, "A").net_to_owner
    mini_db[S.MATERIALS].find("M1")["2026"] = 30
    after = result(mini_db, "A").net_to_owner
    assert after < before
    assert result(mini_db, "A").materials == approx(2 * 1.1 * 30 + 10)


def test_exchange_rate_and_reporting_currency(mini_db):
    mini_db.set_setting("Reporting Currency", "CHF")
    r = result(mini_db, "A")
    assert r.currency == "CHF"
    assert r.gross_price == approx(300)        # 600 EUR = 300 CHF at 0.5
    assert r.net_to_owner == approx(245.52 / 2)


@pytest.mark.parametrize("mutate, expect", [
    (lambda db: cfg(db, "A").update({"Company Type ID": "BB-SOLE"}), "not of the HQ country"),
    (lambda db: cfg(db, "A").update({"Product ID": "NOPE"}), "not found"),
    (lambda db: cfg(db, "A").update({"Base Gross Price (incl. VAT)": "abc"}), "not a number"),
    (lambda db: cfg(db, "A").update({"Annual Volume (units)": 0}), "at least 1"),
    (lambda db: db[S.FX].rows.pop(1), "CHF"),
    (lambda db: db[S.TOOLS].find("T1").update({"Useful Life (years)": 0}), "greater than 0"),
    (lambda db: db[S.SHIPPING].rows.clear(), "no shipping rate"),
    (lambda db: cfg(db, "A").update({"Sale Type": "XYZ"}), "B2C or B2B"),
    (lambda db: cfg(db, "A").update({"Payment Method ID": "PMX"}), "not found"),
    (lambda db: db[S.MATERIALS].find("M1").update({"2026": "x"}), "not a number"),
])
def test_bad_data_gives_error_not_crash(mini_db, mutate, expect):
    mutate(mini_db)
    r = result(mini_db, "A")
    assert not r.ok
    assert expect in r.error


def test_zero_price_is_an_error(mini_db):
    c = cfg(mini_db, "A")
    c["Base Gross Price (incl. VAT)"] = None
    c["Markup (%)"] = -100
    r = result(mini_db, "A")
    assert not r.ok


def test_loss_is_reported(mini_db):
    cfg(mini_db, "A")["Base Gross Price (incl. VAT)"] = 50
    r = result(mini_db, "A")
    assert r.ok and r.net_to_owner < 0 and r.profit_tax == 0 and r.distribution_tax == 0
    assert r.payback_months is None
    assert any("loss" in w for w in r.warnings)


def test_seed_database_all_configs_ok():
    db = build_seed_database()
    assert [str(i) for i in db.validate()] == []
    res = Engine(db).calculate_all()
    assert len(res) == 8
    for r in res:
        assert r.ok, (r.config_id, r.error)
        assert r.gross_price > 0
        total = sum(l.amount for l in r.lines if l.group in ("Deduction", "Cost", "Tax"))
        assert r.gross_price + total == approx(r.net_to_owner)


def test_only_active(mini_db):
    cfg(mini_db, "B")["Active"] = False
    ids = [r.config_id for r in Engine(mini_db).calculate_all(only_active=True)]
    assert ids == ["A", "C"]
