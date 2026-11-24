"""Definition of every sheet (table) in the Excel database.

The Excel workbook is the single source of truth. Every sheet has a fixed set
of columns described here. Materials and Services additionally have one price
column per year (a header that is just a 4-digit year, e.g. "2026"), so a new
year can be added simply by adding a new column in Excel or in the app.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Column kinds
TEXT = "text"
NUMBER = "number"      # any real number (amounts)
INTEGER = "integer"
PERCENT = "percent"    # stored as plain number, 8.1 means 8.1 %
BOOL = "bool"          # stored as Yes / No
CHOICE = "choice"      # one of a fixed list
REF = "ref"            # reference to the key of another sheet
LOCATION = "location"  # country code or region name (shipping / customs)

YES, NO = "Yes", "No"

REGIONS = ("EU", "EFTA", "Western Balkans", "Rest of World")
WILDCARD = "*"
LIABILITY_CHOICES = ("Limited (company only)", "Unlimited (personal)")
SALE_TYPES = ("B2C", "B2B")

YEAR_RE = re.compile(r"^\s*(\d{4})(\.0)?\s*$")


@dataclass(frozen=True)
class Col:
    name: str
    kind: str = TEXT
    required: bool = False
    ref: str | None = None
    choices: tuple = ()
    min: float | None = None
    max: float | None = None
    default: object = None
    width: int = 16
    help: str = ""


@dataclass(frozen=True)
class SheetSpec:
    name: str
    columns: tuple
    key: str | None = None          # primary key column
    unique: tuple = ()              # composite unique key for link tables
    year_columns: bool = False      # has per-year price columns
    id_prefix: str = ""
    description: str = ""
    parent: tuple | None = None     # (column, parent sheet) for child/link tables

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def col(self, name: str) -> Col | None:
        for c in self.columns:
            if c.name == name:
                return c
        return None


def year_col(year: int) -> Col:
    return Col(str(year), NUMBER, min=0, width=10,
               help=f"Price per unit in {year} (in the row's currency). Leave empty if unknown.")


def is_year_header(text) -> int | None:
    if text is None:
        return None
    m = YEAR_RE.match(str(text))
    if not m:
        return None
    y = int(m.group(1))
    return y if 1900 <= y <= 2200 else None


# ---------------------------------------------------------------------------
# Sheet names
SETTINGS = "Settings"
COUNTRIES = "Countries"
COMPANY_TYPES = "Company Types"
FX = "Exchange Rates"
MATERIALS = "Materials"
SERVICES = "Services"
TOOLS = "Tools"
PRODUCTS = "Products"
PRODUCT_MATERIALS = "Product Materials"
PRODUCT_TOOLS = "Product Tools"
SHIPPING = "Shipping Rates"
CUSTOMS = "Customs Rules"
PAYMENT = "Payment Methods"
CONFIGS = "Configurations"
CONFIG_SERVICES = "Configuration Services"
INSTRUCTIONS = "Instructions"
RESULTS = "Results (read-only)"

SPECS: dict[str, SheetSpec] = {}


def _add(spec: SheetSpec):
    SPECS[spec.name] = spec
    return spec


_add(SheetSpec(SETTINGS, (
    Col("Setting", TEXT, True, width=26),
    Col("Value", TEXT, width=24),
    Col("Description", TEXT, width=70),
), key="Setting", description="General settings (company name, reporting currency)."))

_add(SheetSpec(FX, (
    Col("Currency", TEXT, True, width=10, help="ISO currency code, e.g. EUR, CHF, BAM"),
    Col("Units per 1 EUR", NUMBER, True, min=0.0000001, width=16,
        help="How many units of this currency you get for 1 EUR (EUR itself = 1)."),
    Col("Notes", TEXT, width=50),
), key="Currency", description="Exchange rates used to convert everything into the reporting currency."))

_add(SheetSpec(COUNTRIES, (
    Col("Country Code", TEXT, True, width=12, help="2-letter ISO code (XX = generic rest of world)."),
    Col("Country Name", TEXT, True, width=24),
    Col("Region", CHOICE, True, choices=REGIONS, width=16,
        help="Used as fallback for shipping and customs lookups."),
    Col("Customs Territory", TEXT, True, width=14,
        help="Countries with the same value form one customs union (all EU members = EU). "
             "Customs duty only applies between different territories."),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("VAT Standard Rate (%)", PERCENT, True, min=0, max=100, width=12),
    Col("VAT Registration Threshold", NUMBER, min=0, width=14,
        help="Small-business VAT threshold in local currency (information only)."),
    Col("Labour Cost per Hour", NUMBER, True, min=0, width=12,
        help="Fully loaded workshop labour cost per hour in local currency (used for the HQ country)."),
    Col("Return Rate (%)", PERCENT, min=0, max=100, default=0, width=10,
        help="Expected share of orders returned in this market."),
    Col("Return Handling Cost", NUMBER, min=0, default=0, width=12,
        help="Handling / refurbishing cost per returned item, local currency."),
    Col("Notes", TEXT, width=60),
), key="Country Code", description="Countries: VAT, labour cost, returns, region and customs territory."))

_add(SheetSpec(COMPANY_TYPES, (
    Col("Company Type ID", TEXT, True, width=14),
    Col("Country Code", REF, True, ref=COUNTRIES, width=10),
    Col("Legal Form", TEXT, True, width=18),
    Col("Description", TEXT, width=34),
    Col("Liability", CHOICE, True, choices=LIABILITY_CHOICES, width=22),
    Col("Min Share Capital", NUMBER, min=0, default=0, width=12,
        help="Minimum share capital in the country's currency."),
    Col("Formation Costs", NUMBER, min=0, default=0, width=12,
        help="One-time costs to found the company (notary, registry, bank, etc.), local currency."),
    Col("Annual Fixed Costs", NUMBER, min=0, default=0, width=12,
        help="Yearly fixed costs (accounting, chamber fees, insurance, minimum contributions), local currency."),
    Col("Profit / Income Tax Rate (%)", PERCENT, True, min=0, max=100, width=12,
        help="Effective tax on profit (corporate tax for companies, income tax for sole proprietors)."),
    Col("Owner Social Contributions (%)", PERCENT, min=0, max=100, default=0, width=12,
        help="Social contributions charged on profit (mostly sole proprietors)."),
    Col("Distribution Tax Rate (%)", PERCENT, min=0, max=100, default=0, width=12,
        help="Tax when profit is paid out to the owner (dividend tax). 0 for sole proprietors."),
    Col("Notes", TEXT, width=70),
), key="Company Type ID", id_prefix="CT-",
    description="Legal forms per country: liability, capital, formation and running costs, taxes."))

_YEAR_HELP = "Add a column whose header is just a year (e.g. 2027) to add prices for a new year."

_add(SheetSpec(MATERIALS, (
    Col("Material ID", TEXT, True, width=16),
    Col("Name", TEXT, True, width=32),
    Col("Category", TEXT, width=12),
    Col("Unit", TEXT, True, width=8, help="m2, m3, m, kg, L, pcs ..."),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("Waste (%)", PERCENT, min=0, max=500, default=0, width=10,
        help="Default cut-off / waste added on top of the net quantity."),
    Col("Supplier", TEXT, width=18),
    Col("Notes", TEXT, width=30),
), key="Material ID", year_columns=True, id_prefix="MAT-",
    description="Materials with a price per unit for each year. " + _YEAR_HELP))

_add(SheetSpec(SERVICES, (
    Col("Service ID", TEXT, True, width=16),
    Col("Name", TEXT, True, width=30),
    Col("Description", TEXT, width=40),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("Labour Hours", NUMBER, min=0, default=0, width=10,
        help="Extra workshop hours per service (cost at the HQ labour rate)."),
    Col("Notes", TEXT, width=24),
), key="Service ID", year_columns=True, id_prefix="SRV-",
    description="Extra services charged to the customer (net, excl. VAT) per year. " + _YEAR_HELP))

_add(SheetSpec(TOOLS, (
    Col("Tool ID", TEXT, True, width=16),
    Col("Name", TEXT, True, width=30),
    Col("Category", TEXT, width=14),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("Purchase Price", NUMBER, True, min=0, width=12),
    Col("Useful Life (years)", NUMBER, True, min=0.1, width=10),
    Col("Notes", TEXT, width=30),
), key="Tool ID", id_prefix="TOOL-",
    description="Tools and machines: purchase price (startup capital) and depreciation per product."))

_add(SheetSpec(PRODUCTS, (
    Col("Product ID", TEXT, True, width=16),
    Col("Name", TEXT, True, width=30),
    Col("Description", TEXT, width=40),
    Col("Weight (kg)", NUMBER, True, min=0, width=10, help="Packed shipping weight."),
    Col("Labour Hours", NUMBER, True, min=0, width=10, help="Workshop hours to build one unit."),
    Col("Notes", TEXT, width=30),
), key="Product ID", id_prefix="PRD-",
    description="Products. Materials and tools per product are in 'Product Materials' and 'Product Tools'."))

_add(SheetSpec(PRODUCT_MATERIALS, (
    Col("Product ID", REF, True, ref=PRODUCTS, width=16),
    Col("Material ID", REF, True, ref=MATERIALS, width=16),
    Col("Quantity", NUMBER, True, min=0, width=10, help="Net quantity per product unit (material unit)."),
    Col("Waste Override (%)", PERCENT, min=0, max=500, width=12,
        help="Leave empty to use the material's default waste."),
    Col("Notes", TEXT, width=30),
), unique=("Product ID", "Material ID"), parent=("Product ID", PRODUCTS),
    description="Bill of materials: how much of each material one product uses."))

_add(SheetSpec(PRODUCT_TOOLS, (
    Col("Product ID", REF, True, ref=PRODUCTS, width=16),
    Col("Tool ID", REF, True, ref=TOOLS, width=16),
    Col("Quantity", INTEGER, True, min=1, default=1, width=10),
    Col("Notes", TEXT, width=30),
), unique=("Product ID", "Tool ID"), parent=("Product ID", PRODUCTS),
    description="Tools needed to make each product."))

_add(SheetSpec(SHIPPING, (
    Col("Origin", LOCATION, True, width=16,
        help="Country code, region (EU, EFTA, Western Balkans, Rest of World) or * for any."),
    Col("Destination", LOCATION, True, width=16,
        help="Country code, region or *. The most specific matching row is used."),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("Cost per Shipment", NUMBER, True, min=0, width=12),
    Col("Cost per kg", NUMBER, min=0, default=0, width=10),
    Col("Transit Days", INTEGER, min=0, width=10),
    Col("Notes", TEXT, width=40),
), unique=("Origin", "Destination"),
    description="Delivery cost per order: cost per shipment + cost per kg x product weight."))

_add(SheetSpec(CUSTOMS, (
    Col("Origin", LOCATION, True, width=16),
    Col("Destination", LOCATION, True, width=16),
    Col("Duty Rate (%)", PERCENT, min=0, max=100, default=0, width=10,
        help="Customs duty on (net price + shipping). Only applied between different customs territories."),
    Col("Clearance Fee", NUMBER, min=0, default=0, width=10, help="Broker / clearance fee per shipment."),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("Notes", TEXT, width=60),
), unique=("Origin", "Destination"),
    description="Customs duty and clearance per route (B2C, delivered duty paid by you)."))

_add(SheetSpec(PAYMENT, (
    Col("Payment Method ID", TEXT, True, width=16),
    Col("Name", TEXT, True, width=30),
    Col("Fee (%)", PERCENT, min=0, max=100, default=0, width=8),
    Col("Fixed Fee", NUMBER, min=0, default=0, width=10),
    Col("Currency", REF, True, ref=FX, width=10),
    Col("Notes", TEXT, width=40),
), key="Payment Method ID", id_prefix="PAY-",
    description="Payment providers: percentage of gross price + fixed fee per transaction."))

_add(SheetSpec(CONFIGS, (
    Col("Configuration ID", TEXT, True, width=12),
    Col("Name", TEXT, width=30),
    Col("Active", BOOL, default=YES, choices=(YES, NO), width=8),
    Col("Product ID", REF, True, ref=PRODUCTS, width=16),
    Col("Material Price Year", INTEGER, min=1900, max=2200, width=10,
        help="Empty = latest year available."),
    Col("HQ Country", REF, True, ref=COUNTRIES, width=10, help="Where the company is registered and produces."),
    Col("Company Type ID", REF, True, ref=COMPANY_TYPES, width=14,
        help="Must be a legal form of the HQ country."),
    Col("Market Country", REF, True, ref=COUNTRIES, width=10, help="Where the product is sold/delivered."),
    Col("Sale Type", CHOICE, True, choices=SALE_TYPES, default="B2C", width=8),
    Col("Payment Method ID", REF, ref=PAYMENT, width=14),
    Col("Base Gross Price (incl. VAT)", NUMBER, min=0, width=14,
        help="Fixed customer price incl. VAT, without extra services. Empty = calculated from markup."),
    Col("Price Currency", REF, ref=FX, width=10, help="Currency of the base gross price. Empty = market currency."),
    Col("Markup (%)", PERCENT, min=-100, max=10000, default=60, width=10,
        help="Used when no fixed gross price is given: net price = production cost x (1 + markup)."),
    Col("Annual Volume (units)", INTEGER, True, min=1, default=100, width=10,
        help="Units sold per year (spreads fixed costs and tool depreciation)."),
    Col("Startup Stock (units)", INTEGER, min=0, default=0, width=10,
        help="Material stock to buy at the start (in product units)."),
    Col("Sales Commission (%)", PERCENT, min=0, max=100, default=0, width=10,
        help="Marketplace / agent commission on the gross price."),
    Col("Small-Business VAT Exemption", BOOL, default=NO, choices=(YES, NO), width=12,
        help="Yes = you are below the VAT registration threshold (domestic sales only)."),
    Col("Notes", TEXT, width=30),
), key="Configuration ID", id_prefix="CFG-",
    description="Scenarios to compare: product + HQ country + legal form + market + price."))

_add(SheetSpec(CONFIG_SERVICES, (
    Col("Configuration ID", REF, True, ref=CONFIGS, width=14),
    Col("Service ID", REF, True, ref=SERVICES, width=16),
    Col("Quantity", NUMBER, True, min=0, default=1, width=10),
    Col("Notes", TEXT, width=30),
), unique=("Configuration ID", "Service ID"), parent=("Configuration ID", CONFIGS),
    description="Extra services included in a configuration (added to the price)."))

# Order of sheets in the workbook
SHEET_ORDER = [CONFIGS, CONFIG_SERVICES, PRODUCTS, PRODUCT_MATERIALS, PRODUCT_TOOLS, MATERIALS,
               SERVICES, TOOLS, COUNTRIES, COMPANY_TYPES, SHIPPING, CUSTOMS, PAYMENT, FX, SETTINGS]

assert set(SHEET_ORDER) == set(SPECS)

DEFAULT_SETTINGS = [
    ("Company Name", "My Company", "Shown in the window title and reports."),
    ("Reporting Currency", "EUR", "All results are converted into this currency (must exist in 'Exchange Rates')."),
]
