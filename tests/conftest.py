import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "main"))  # source code lives in main/

import pytest  # noqa: E402

from profit_planner import schema as S  # noqa: E402
from profit_planner.database import Database  # noqa: E402


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "data" / "TestDB.xlsx"


def _rows(table, cols, data):
    table.rows = [dict(zip(cols, d)) for d in data]


@pytest.fixture
def mini_db() -> Database:
    """Small database with round numbers so every result can be checked by hand."""
    db = Database()
    db.ensure_default_settings()
    db.set_setting("Reporting Currency", "EUR")
    _rows(db[S.FX], ["Currency", "Units per 1 EUR"], [("EUR", 1.0), ("CHF", 0.5)])
    _rows(db[S.COUNTRIES], ["Country Code", "Country Name", "Region", "Customs Territory", "Currency",
                            "VAT Standard Rate (%)", "Labour Cost per Hour", "Return Rate (%)",
                            "Return Handling Cost"], [
        ("AA", "Alpha", "EU", "EU", "EUR", 20, 10, 10, 5),
        ("BB", "Beta", "EFTA", "BB", "CHF", 10, 20, 0, 0),
    ])
    _rows(db[S.COMPANY_TYPES], ["Company Type ID", "Country Code", "Legal Form", "Liability",
                                "Min Share Capital", "Formation Costs", "Annual Fixed Costs",
                                "Profit / Income Tax Rate (%)", "Owner Social Contributions (%)",
                                "Distribution Tax Rate (%)"], [
        ("AA-LTD", "AA", "Ltd", S.LIABILITY_CHOICES[0], 1000, 100, 1200, 10, 0, 20),
        ("BB-SOLE", "BB", "Sole", S.LIABILITY_CHOICES[1], 0, 50, 600, 20, 10, 0),
    ])
    db[S.MATERIALS].years = [2025, 2026]
    _rows(db[S.MATERIALS], ["Material ID", "Name", "Unit", "Currency", "Waste (%)", "2025", "2026"], [
        ("M1", "Wood", "kg", "EUR", 10, 10, 20),
        ("M2", "Steel", "m", "CHF", 0, None, 5),
    ])
    db[S.SERVICES].years = [2026]
    _rows(db[S.SERVICES], ["Service ID", "Name", "Currency", "Labour Hours", "2026"], [
        ("S1", "Custom size", "EUR", 1, 50),
    ])
    _rows(db[S.TOOLS], ["Tool ID", "Name", "Currency", "Purchase Price", "Useful Life (years)"], [
        ("T1", "Saw", "EUR", 1200, 2),
    ])
    _rows(db[S.PRODUCTS], ["Product ID", "Name", "Weight (kg)", "Labour Hours"], [("P1", "Table", 10, 2)])
    _rows(db[S.PRODUCT_MATERIALS], ["Product ID", "Material ID", "Quantity", "Waste Override (%)"], [
        ("P1", "M1", 2, None), ("P1", "M2", 1, 0)])
    _rows(db[S.PRODUCT_TOOLS], ["Product ID", "Tool ID", "Quantity"], [("P1", "T1", 1)])
    _rows(db[S.SHIPPING], ["Origin", "Destination", "Currency", "Cost per Shipment", "Cost per kg"], [
        ("AA", "AA", "EUR", 10, 1), ("AA", "BB", "EUR", 20, 2), ("BB", "EU", "CHF", 15, 0.5)])
    _rows(db[S.CUSTOMS], ["Origin", "Destination", "Duty Rate (%)", "Clearance Fee", "Currency"], [
        ("AA", "BB", 10, 5, "EUR")])
    _rows(db[S.PAYMENT], ["Payment Method ID", "Name", "Fee (%)", "Fixed Fee", "Currency"], [
        ("PM1", "Card", 2, 0.5, "EUR")])
    base = {"Active": True, "Product ID": "P1", "Material Price Year": 2026, "Sale Type": "B2C",
            "Annual Volume (units)": 100, "Startup Stock (units)": 10, "Sales Commission (%)": 0,
            "Small-Business VAT Exemption": False}
    cfgs = [
        dict(base, **{"Configuration ID": "A", "HQ Country": "AA", "Company Type ID": "AA-LTD",
                      "Market Country": "AA", "Payment Method ID": "PM1",
                      "Base Gross Price (incl. VAT)": 600, "Price Currency": "EUR",
                      "Sales Commission (%)": 5}),
        dict(base, **{"Configuration ID": "B", "HQ Country": "AA", "Company Type ID": "AA-LTD",
                      "Market Country": "BB", "Markup (%)": 50}),
        dict(base, **{"Configuration ID": "C", "HQ Country": "BB", "Company Type ID": "BB-SOLE",
                      "Market Country": "AA", "Base Gross Price (incl. VAT)": 600}),
    ]
    db[S.CONFIGS].rows = []
    for c in cfgs:
        r = db[S.CONFIGS].new_row()
        r.update(c)
        db[S.CONFIGS].rows.append(r)
    db[S.CONFIG_SERVICES].rows = [{"Configuration ID": "B", "Service ID": "S1", "Quantity": 2, "Notes": None}]
    # normalise all rows to full column sets
    for t in db.tables.values():
        for r in t.rows:
            for c in t.columns():
                r.setdefault(c, None)
    return db
