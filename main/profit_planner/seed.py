"""Starter data for a new database.

All figures are indicative planning values (status: November 2026) and must be
checked with a local accountant / tax advisor before real decisions are made.
Every value can be edited in the app or directly in Excel.
"""
from __future__ import annotations

from . import schema as S
from .database import Database

YEARS = [2024, 2025, 2026]


def _rows(cols, data):
    return [dict(zip(cols, d)) for d in data]


def build_seed_database() -> Database:
    db = Database()
    db.ensure_default_settings()
    db.set_setting("Company Name", "My Furniture Company")

    db[S.FX].rows = _rows(["Currency", "Units per 1 EUR", "Notes"], [
        ("EUR", 1.0, "Base currency"),
        ("CHF", 0.93, "Swiss franc - indicative, update regularly"),
        ("BAM", 1.95583, "Convertible mark - fixed peg to EUR"),
        ("RSD", 117.2, "Serbian dinar - indicative"),
        ("MKD", 61.5, "Macedonian denar - indicative (managed peg)"),
        ("USD", 1.16, "US dollar - indicative"),
        ("GBP", 0.87, "British pound - indicative"),
    ])

    ccols = ["Country Code", "Country Name", "Region", "Customs Territory", "Currency",
             "VAT Standard Rate (%)", "VAT Registration Threshold", "Labour Cost per Hour",
             "Return Rate (%)", "Return Handling Cost", "Notes"]
    db[S.COUNTRIES].rows = _rows(ccols, [
        ("CH", "Switzerland", "EFTA", "CH", "CHF", 8.1, 100000, 58, 4, 40,
         "VAT 8.1 %. Foreign sellers of low-value consignments must register above CHF 100k worldwide turnover."),
        ("DE", "Germany", "EU", "EU", "EUR", 19, 25000, 42, 8, 30,
         "VAT 19 %. Kleinunternehmer: prior year <= EUR 25k and current year <= EUR 100k (residents only)."),
        ("HR", "Croatia", "EU", "EU", "EUR", 25, 60000, 16, 4, 15, "VAT 25 %."),
        ("BA", "Bosnia and Herzegovina", "Western Balkans", "BA", "BAM", 17, 100000, 13, 3, 20,
         "VAT 17 % (state level). Labour cost is FBiH indicative."),
        ("AT", "Austria", "EU", "EU", "EUR", 20, 55000, 40, 6, 30, "VAT 20 %."),
        ("SI", "Slovenia", "EU", "EU", "EUR", 22, 60000, 22, 4, 20, "VAT 22 %."),
        ("IT", "Italy", "EU", "EU", "EUR", 22, 85000, 30, 5, 25, "VAT 22 %."),
        ("FR", "France", "EU", "EU", "EUR", 20, 85000, 40, 6, 30, "VAT 20 %."),
        ("NL", "Netherlands", "EU", "EU", "EUR", 21, 20000, 40, 7, 30, "VAT 21 %."),
        ("RS", "Serbia", "Western Balkans", "RS", "RSD", 20, 8000000, 1500, 3, 2000, "VAT 20 %."),
        ("ME", "Montenegro", "Western Balkans", "ME", "EUR", 21, 30000, 9, 3, 15, "VAT 21 %. Uses EUR."),
        ("MK", "North Macedonia", "Western Balkans", "MK", "MKD", 18, 2000000, 550, 3, 900, "VAT 18 %."),
        ("XX", "Rest of World (generic)", "Rest of World", "XX", "USD", 15, 0, 35, 5, 40,
         "Generic placeholder for far export markets - replace with real country rows when needed."),
    ])

    tcols = ["Company Type ID", "Country Code", "Legal Form", "Description", "Liability",
             "Min Share Capital", "Formation Costs", "Annual Fixed Costs",
             "Profit / Income Tax Rate (%)", "Owner Social Contributions (%)",
             "Distribution Tax Rate (%)", "Notes"]
    LIM, UNL = S.LIABILITY_CHOICES
    db[S.COMPANY_TYPES].rows = _rows(tcols, [
        ("CH-SOLE", "CH", "Einzelunternehmen", "Sole proprietorship", UNL, 0, 300, 2000, 22, 10, 0,
         "Owner liable with private assets. AHV/IV/EO for self-employed ~10 %. Income tax depends on canton/income."),
        ("CH-GMBH", "CH", "GmbH", "Limited liability company", LIM, 20000, 2500, 4500, 19.6, 0, 20,
         "CHF 20k fully paid in. Profit tax ~19.6 % (Zurich city); 12-21 % depending on canton. "
         "Dividends: 35 % withholding (refundable for residents); partial taxation -> ~20 % effective."),
        ("CH-AG", "CH", "AG", "Stock corporation", LIM, 100000, 4000, 7000, 19.6, 0, 20,
         "CHF 100k capital, min. CHF 50k paid in. Same tax as GmbH."),
        ("DE-SOLE", "DE", "Einzelunternehmen", "Sole proprietorship", UNL, 0, 60, 1800, 30, 18, 0,
         "Personal income tax 14-45 % + trade tax (partly credited). Social % = health/care insurance (approx.)."),
        ("DE-UG", "DE", "UG (haftungsbeschraenkt)", "Mini-GmbH", LIM, 1, 800, 3500, 29.9, 0, 26.4,
         "Capital from EUR 1; 25 % of profit must be retained until EUR 25k. "
         "CIT 15 % + soli 5.5 % + trade tax ~14 % = ~29.9 %. Dividend tax 26.375 %."),
        ("DE-GMBH", "DE", "GmbH", "Limited liability company", LIM, 25000, 1500, 4500, 29.9, 0, 26.4,
         "EUR 25k capital, min. EUR 12.5k paid in. CIT rate is scheduled to fall gradually from 2028."),
        ("HR-OBRT", "HR", "Obrt", "Sole trader (bookkeeping)", UNL, 0, 50, 1200, 20, 20, 0,
         "Income tax 20/30 % (local rates). Contributions approx. - check minimum contribution base."),
        ("HR-JDOO", "HR", "j.d.o.o.", "Simple LLC", LIM, 1, 400, 1500, 10, 0, 12,
         "Capital from EUR 1, 25 % of profit to reserves. Profit tax 10 % (revenue < EUR 1M), else 18 %. Dividend tax 12 %."),
        ("HR-DOO", "HR", "d.o.o.", "Limited liability company", LIM, 2500, 600, 1800, 10, 0, 12,
         "EUR 2,500 capital. Profit tax 10 % up to EUR 1M revenue, 18 % above. Dividend tax 12 %."),
        ("BA-SP", "BA", "Samostalni poduzetnik", "Sole trader (FBiH)", UNL, 0, 300, 1500, 10, 30, 0,
         "Income tax 10 %. Contributions approx. 30 % of base - verify with local accountant."),
        ("BA-DOO", "BA", "d.o.o.", "Limited liability company (FBiH)", LIM, 1000, 1500, 3000, 10, 0, 5,
         "KM 1,000 capital in FBiH (lower in RS). Profit tax 10 %. Dividend tax: verify current FBiH/RS rules."),
        ("RS-DOO", "RS", "d.o.o.", "Limited liability company", LIM, 100, 15000, 300000, 15, 0, 15,
         "RSD 100 capital. Profit tax 15 %, dividend tax 15 %."),
        ("ME-DOO", "ME", "d.o.o.", "Limited liability company", LIM, 1, 300, 1200, 9, 0, 15,
         "Progressive profit tax 9 % (to EUR 100k), 12 %, 15 %. Dividend tax 15 %."),
        ("MK-DOOEL", "MK", "DOOEL", "Single-member LLC", LIM, 307500, 15000, 90000, 10, 0, 10,
         "Min. capital EUR 5,000 equivalent. Profit tax 10 %, dividend (personal income) tax 10 %."),
    ])

    mcols = ["Material ID", "Name", "Category", "Unit", "Currency", "Waste (%)", "Supplier", "Notes",
             "2024", "2025", "2026"]
    db[S.MATERIALS].years = list(YEARS)
    db[S.MATERIALS].rows = _rows(mcols, [
        ("MAT-OAK", "Oak solid board 40 mm", "Wood", "m2", "EUR", 15, "", "", 85, 90, 95),
        ("MAT-WALNUT", "Walnut solid board 40 mm", "Wood", "m2", "EUR", 15, "", "", 140, 150, 158),
        ("MAT-BEECH", "Beech glued panel 27 mm", "Wood", "m2", "EUR", 12, "", "", 45, 48, 50),
        ("MAT-SPRUCE", "Spruce glued panel 27 mm", "Wood", "m2", "EUR", 10, "", "", 25, 27, 28),
        ("MAT-PLYWOOD", "Birch plywood 18 mm", "Wood", "m2", "EUR", 10, "", "", 32, 34, 35),
        ("MAT-MDF", "MDF board 19 mm", "Wood", "m2", "EUR", 8, "", "", 9, 9.5, 10),
        ("MAT-STEEL-TUBE", "Steel square tube 40x40x2", "Metal", "m", "EUR", 5, "", "", 6.5, 7, 7.2),
        ("MAT-STEEL-FLAT", "Steel flat bar 40x5", "Metal", "m", "EUR", 5, "", "", 3.2, 3.4, 3.5),
        ("MAT-STAINLESS", "Stainless steel tube 40x40", "Metal", "m", "EUR", 5, "", "", 18, 19, 19.5),
        ("MAT-ALU", "Aluminium profile 40x40", "Metal", "m", "EUR", 5, "", "", 9, 9.5, 10),
        ("MAT-POWDER", "Powder coating (outsourced, per metre of profile)", "Paint", "m", "CHF", 0, "",
         "", 4.5, 4.7, 4.9),
        ("MAT-OIL", "Hardwax oil", "Paint", "L", "EUR", 10, "", "", 38, 40, 42),
        ("MAT-LACQUER", "Water-based lacquer", "Paint", "L", "EUR", 10, "", "", 22, 23, 24),
        ("MAT-STAIN", "Wood stain", "Paint", "L", "EUR", 10, "", "", 25, 26, 27),
        ("MAT-GLUE-PVA", "PVA wood glue D3", "Glue", "kg", "EUR", 5, "", "", 6, 6.5, 6.8),
        ("MAT-EPOXY", "Epoxy resin", "Glue", "kg", "EUR", 8, "", "", 28, 30, 31),
        ("MAT-SCREWS", "Screws / fasteners", "Hardware", "pcs", "EUR", 5, "", "", 0.05, 0.05, 0.06),
        ("MAT-LEVELERS", "Adjustable feet", "Hardware", "pcs", "EUR", 0, "", "", 2.5, 2.6, 2.7),
        ("MAT-SANDPAPER", "Sanding discs", "Consumable", "pcs", "EUR", 0, "", "", 0.8, 0.85, 0.9),
        ("MAT-BOX", "Cardboard packaging for furniture", "Packaging", "pcs", "CHF", 0, "", "", 18, 19, 20),
        ("MAT-CORNERS", "Corner and edge protectors (set)", "Packaging", "pcs", "EUR", 0, "", "", 3, 3.1, 3.2),
    ])

    scols = ["Service ID", "Name", "Description", "Currency", "Labour Hours", "Notes", "2024", "2025", "2026"]
    db[S.SERVICES].years = list(YEARS)
    db[S.SERVICES].rows = _rows(scols, [
        ("SRV-SIZE", "Custom dimensions", "Non-standard length/width/height", "EUR", 2, "", 110, 115, 120),
        ("SRV-COLOR", "Custom colour / finish", "Colour matching, special finish", "EUR", 1, "", 55, 58, 60),
        ("SRV-EDGE", "Live edge / special edge", "Natural edge or special profile", "EUR", 1.5, "", 80, 85, 90),
        ("SRV-ENGRAVE", "Engraving / logo", "Laser engraving", "EUR", 0.5, "", 40, 42, 45),
        ("SRV-ASSEMBLY", "On-site assembly", "Assembly at customer", "EUR", 1.5, "", 70, 75, 80),
        ("SRV-EXPRESS", "Express production", "Priority production slot", "EUR", 0, "", 90, 95, 100),
        ("SRV-COAT", "Extra protective coat", "Additional lacquer coat", "EUR", 0.75, "", 35, 38, 40),
    ])

    db[S.TOOLS].rows = _rows(["Tool ID", "Name", "Category", "Currency", "Purchase Price",
                              "Useful Life (years)", "Notes"], [
        ("TOOL-TABLESAW", "Table / panel saw", "Woodworking", "EUR", 3500, 8, ""),
        ("TOOL-TRACKSAW", "Track saw with rail", "Woodworking", "EUR", 700, 6, ""),
        ("TOOL-PLANER", "Planer / thicknesser", "Woodworking", "EUR", 2800, 8, ""),
        ("TOOL-ROUTER", "Router", "Woodworking", "EUR", 450, 5, ""),
        ("TOOL-SANDER", "Random orbital sander", "Woodworking", "EUR", 450, 4, ""),
        ("TOOL-DRILL", "Cordless drill / driver set", "General", "EUR", 400, 4, ""),
        ("TOOL-CLAMPS", "Clamp set", "General", "EUR", 600, 10, ""),
        ("TOOL-DUST", "Dust extractor", "General", "EUR", 800, 6, ""),
        ("TOOL-BENCH", "Workbench", "General", "EUR", 500, 10, ""),
        ("TOOL-MEASURE", "Measuring and marking tools", "General", "EUR", 200, 5, ""),
        ("TOOL-WELDER", "MIG/MAG welder", "Metalworking", "EUR", 1200, 8, ""),
        ("TOOL-CHOPSAW", "Metal chop saw", "Metalworking", "EUR", 350, 6, ""),
        ("TOOL-GRINDER", "Angle grinder", "Metalworking", "EUR", 150, 4, ""),
        ("TOOL-SPRAY", "Spray gun system", "Finishing", "EUR", 900, 6, ""),
        ("TOOL-COMPRESSOR", "Air compressor", "General", "EUR", 700, 8, ""),
    ])

    db[S.PRODUCTS].rows = _rows(["Product ID", "Name", "Description", "Weight (kg)", "Labour Hours", "Notes"], [
        ("PRD-OAK-DINING", "Oak dining table 200x100", "Solid oak top, powder-coated steel frame", 55, 14, ""),
        ("PRD-WALNUT-DESK", "Walnut desk 160x80", "Solid walnut top, steel legs", 40, 12, ""),
        ("PRD-SPRUCE-COFFEE", "Spruce coffee table 110x60", "Glued spruce panel, wooden legs", 18, 5, ""),
        ("PRD-PLY-SIDE", "Plywood side table 50x50", "Birch plywood with steel frame", 9, 3, ""),
    ])

    bom = [
        ("PRD-OAK-DINING", "MAT-OAK", 2.6), ("PRD-OAK-DINING", "MAT-STEEL-TUBE", 8),
        ("PRD-OAK-DINING", "MAT-POWDER", 8), ("PRD-OAK-DINING", "MAT-OIL", 0.6),
        ("PRD-OAK-DINING", "MAT-GLUE-PVA", 0.3), ("PRD-OAK-DINING", "MAT-SCREWS", 30),
        ("PRD-OAK-DINING", "MAT-LEVELERS", 4), ("PRD-OAK-DINING", "MAT-SANDPAPER", 6),
        ("PRD-OAK-DINING", "MAT-BOX", 1), ("PRD-OAK-DINING", "MAT-CORNERS", 1),
        ("PRD-WALNUT-DESK", "MAT-WALNUT", 1.5), ("PRD-WALNUT-DESK", "MAT-STEEL-TUBE", 6),
        ("PRD-WALNUT-DESK", "MAT-POWDER", 6), ("PRD-WALNUT-DESK", "MAT-OIL", 0.4),
        ("PRD-WALNUT-DESK", "MAT-SCREWS", 20), ("PRD-WALNUT-DESK", "MAT-LEVELERS", 4),
        ("PRD-WALNUT-DESK", "MAT-SANDPAPER", 5), ("PRD-WALNUT-DESK", "MAT-BOX", 1),
        ("PRD-WALNUT-DESK", "MAT-CORNERS", 1),
        ("PRD-SPRUCE-COFFEE", "MAT-SPRUCE", 1.1), ("PRD-SPRUCE-COFFEE", "MAT-LACQUER", 0.3),
        ("PRD-SPRUCE-COFFEE", "MAT-GLUE-PVA", 0.2), ("PRD-SPRUCE-COFFEE", "MAT-SCREWS", 16),
        ("PRD-SPRUCE-COFFEE", "MAT-SANDPAPER", 3), ("PRD-SPRUCE-COFFEE", "MAT-BOX", 1),
        ("PRD-PLY-SIDE", "MAT-PLYWOOD", 0.6), ("PRD-PLY-SIDE", "MAT-STEEL-FLAT", 3),
        ("PRD-PLY-SIDE", "MAT-POWDER", 3), ("PRD-PLY-SIDE", "MAT-LACQUER", 0.15),
        ("PRD-PLY-SIDE", "MAT-SCREWS", 8), ("PRD-PLY-SIDE", "MAT-BOX", 1),
    ]
    db[S.PRODUCT_MATERIALS].rows = [
        {"Product ID": p, "Material ID": m, "Quantity": q, "Waste Override (%)": None, "Notes": None}
        for p, m, q in bom]

    wood = ["TOOL-TABLESAW", "TOOL-TRACKSAW", "TOOL-PLANER", "TOOL-ROUTER", "TOOL-SANDER",
            "TOOL-DRILL", "TOOL-CLAMPS", "TOOL-DUST", "TOOL-BENCH", "TOOL-MEASURE",
            "TOOL-SPRAY", "TOOL-COMPRESSOR"]
    metal = ["TOOL-WELDER", "TOOL-CHOPSAW", "TOOL-GRINDER"]
    pt = []
    for p in ("PRD-OAK-DINING", "PRD-WALNUT-DESK", "PRD-PLY-SIDE"):
        pt += [(p, t) for t in wood + metal]
    pt += [("PRD-SPRUCE-COFFEE", t) for t in wood]
    db[S.PRODUCT_TOOLS].rows = [{"Product ID": p, "Tool ID": t, "Quantity": 1, "Notes": None} for p, t in pt]

    shcols = ["Origin", "Destination", "Currency", "Cost per Shipment", "Cost per kg", "Transit Days", "Notes"]
    db[S.SHIPPING].rows = _rows(shcols, [
        ("CH", "CH", "CHF", 69, 1.2, 3, "Domestic furniture freight"),
        ("CH", "DE", "CHF", 120, 1.6, 5, ""),
        ("CH", "EU", "CHF", 140, 1.8, 6, ""),
        ("CH", "Western Balkans", "CHF", 180, 2.2, 8, ""),
        ("CH", "Rest of World", "CHF", 350, 4.5, 14, ""),
        ("DE", "DE", "EUR", 49, 0.9, 3, "Domestic furniture freight"),
        ("DE", "EU", "EUR", 89, 1.3, 5, ""),
        ("DE", "EFTA", "EUR", 110, 1.6, 6, ""),
        ("DE", "Western Balkans", "EUR", 130, 1.8, 8, ""),
        ("DE", "Rest of World", "EUR", 300, 4.0, 14, ""),
        ("HR", "HR", "EUR", 35, 0.7, 3, "Domestic furniture freight"),
        ("HR", "DE", "EUR", 85, 1.3, 5, ""),
        ("HR", "EU", "EUR", 80, 1.3, 5, ""),
        ("HR", "EFTA", "EUR", 120, 1.7, 6, ""),
        ("HR", "Western Balkans", "EUR", 60, 1.0, 4, ""),
        ("HR", "Rest of World", "EUR", 300, 4.0, 14, ""),
        ("BA", "BA", "BAM", 40, 1.0, 3, "Domestic furniture freight"),
        ("BA", "DE", "BAM", 230, 2.6, 6, ""),
        ("BA", "EU", "BAM", 220, 2.6, 6, ""),
        ("BA", "EFTA", "BAM", 290, 3.3, 7, ""),
        ("BA", "Western Balkans", "BAM", 110, 1.8, 4, ""),
        ("BA", "Rest of World", "BAM", 650, 8.0, 14, ""),
        ("Western Balkans", "Western Balkans", "EUR", 55, 0.9, 4, "Generic regional rate"),
        ("Western Balkans", "EU", "EUR", 115, 1.4, 6, "Generic regional rate"),
        ("Western Balkans", "EFTA", "EUR", 150, 1.7, 7, "Generic regional rate"),
        ("*", "*", "EUR", 300, 4.0, 14, "Fallback when no specific route exists"),
    ])

    cucols = ["Origin", "Destination", "Duty Rate (%)", "Clearance Fee", "Currency", "Notes"]
    db[S.CUSTOMS].rows = _rows(cucols, [
        ("CH", "EU", 0, 30, "EUR",
         "Furniture (HS 9403) duty-free with proof of Swiss preferential origin. Import VAT of destination applies."),
        ("EU", "EFTA", 0, 40, "CHF", "Switzerland abolished industrial tariffs (2024). Swiss import VAT applies."),
        ("Western Balkans", "EU", 0, 30, "EUR", "SAA preferential treatment with proof of origin."),
        ("EU", "Western Balkans", 0, 30, "EUR", "SAA: EU industrial goods duty-free with proof of origin."),
        ("Western Balkans", "Western Balkans", 0, 25, "EUR", "CEFTA free trade."),
        ("Western Balkans", "EFTA", 0, 40, "CHF", "No Swiss industrial tariffs."),
        ("EFTA", "Western Balkans", 0, 30, "EUR", "EFTA free trade agreements with proof of origin."),
        ("*", "Rest of World", 10, 60, "EUR", "Placeholder - check the destination's tariff (e.g. US tariffs on furniture)."),
        ("Rest of World", "*", 5, 40, "EUR", "Placeholder."),
    ])

    db[S.PAYMENT].rows = _rows(["Payment Method ID", "Name", "Fee (%)", "Fixed Fee", "Currency", "Notes"], [
        ("PAY-CARD-EU", "Card - European (e.g. Stripe)", 1.5, 0.25, "EUR", "Standard EEA cards, indicative"),
        ("PAY-CARD-CH", "Card - Switzerland (e.g. Stripe)", 2.9, 0.30, "CHF", "Indicative"),
        ("PAY-CARD-INT", "Card - international", 3.25, 0.25, "EUR", "Non-EEA cards incl. currency conversion"),
        ("PAY-TWINT", "TWINT", 1.9, 0.30, "CHF", "Swiss mobile payments, indicative"),
        ("PAY-PAYPAL", "PayPal", 3.49, 0.39, "EUR", "Indicative"),
        ("PAY-KLARNA", "Klarna / pay later", 4.99, 0.35, "EUR", "Indicative"),
        ("PAY-BANK", "Bank transfer / invoice", 0, 0.5, "EUR", ""),
    ])

    cfg_cols = ["Configuration ID", "Name", "Active", "Product ID", "Material Price Year", "HQ Country",
                "Company Type ID", "Market Country", "Sale Type", "Payment Method ID",
                "Base Gross Price (incl. VAT)", "Price Currency", "Markup (%)", "Annual Volume (units)",
                "Startup Stock (units)", "Sales Commission (%)", "Small-Business VAT Exemption", "Notes"]
    db[S.CONFIGS].rows = _rows(cfg_cols, [
        ("CFG-001", "CH GmbH -> Switzerland", True, "PRD-OAK-DINING", 2026, "CH", "CH-GMBH", "CH", "B2C",
         "PAY-CARD-CH", 2490, "CHF", None, 120, 10, 0, False, ""),
        ("CFG-002", "CH GmbH -> Germany", True, "PRD-OAK-DINING", 2026, "CH", "CH-GMBH", "DE", "B2C",
         "PAY-CARD-EU", 2290, "EUR", None, 120, 10, 0, False, ""),
        ("CFG-003", "DE GmbH -> Germany", True, "PRD-OAK-DINING", 2026, "DE", "DE-GMBH", "DE", "B2C",
         "PAY-CARD-EU", 2290, "EUR", None, 120, 10, 0, False, ""),
        ("CFG-004", "HR d.o.o. -> Germany", True, "PRD-OAK-DINING", 2026, "HR", "HR-DOO", "DE", "B2C",
         "PAY-CARD-EU", 2290, "EUR", None, 120, 10, 0, False, ""),
        ("CFG-005", "BA d.o.o. -> Germany", True, "PRD-OAK-DINING", 2026, "BA", "BA-DOO", "DE", "B2C",
         "PAY-CARD-EU", 2290, "EUR", None, 120, 10, 0, False, ""),
        ("CFG-006", "HR d.o.o. -> Switzerland", True, "PRD-OAK-DINING", 2026, "HR", "HR-DOO", "CH", "B2C",
         "PAY-CARD-CH", 2490, "CHF", None, 120, 10, 0, False, ""),
        ("CFG-007", "BA d.o.o. -> Bosnia (markup)", True, "PRD-OAK-DINING", 2026, "BA", "BA-DOO", "BA", "B2C",
         "PAY-CARD-EU", None, None, 70, 120, 10, 0, False, "Price from markup"),
        ("CFG-008", "CH sole prop -> Switzerland, walnut desk", True, "PRD-WALNUT-DESK", 2026, "CH", "CH-SOLE",
         "CH", "B2C", "PAY-TWINT", 2150, "CHF", None, 80, 5, 0, True, "Below VAT threshold"),
    ])
    db[S.CONFIG_SERVICES].rows = [
        {"Configuration ID": "CFG-002", "Service ID": "SRV-SIZE", "Quantity": 1, "Notes": None},
        {"Configuration ID": "CFG-006", "Service ID": "SRV-COLOR", "Quantity": 1, "Notes": None},
    ]
    return db
