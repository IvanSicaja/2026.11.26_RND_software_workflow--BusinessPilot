"""Reading and writing the Excel workbook (pure functions, no file-safety logic)."""
from __future__ import annotations

import io
import warnings
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import __version__
from . import schema as S
from .database import Database, Table, coerce, to_excel


class WorkbookError(Exception):
    """The file cannot be read as a Profit Planner database."""


HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
KEY_FILL = PatternFill("solid", fgColor="2E75B6")
YEAR_FILL = PatternFill("solid", fgColor="548235")
HEADER_FONT = Font(bold=True, color="FFFFFF")
THIN = Side(style="thin", color="BFBFBF")


def read_workbook(source) -> tuple[Database, list[str]]:
    """Read a database from a path or bytes. Returns (database, warnings)."""
    notes: list[str] = []
    try:
        if isinstance(source, (bytes, bytearray)):
            source = io.BytesIO(source)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb = load_workbook(source, data_only=True, read_only=False)
    except Exception as e:  # noqa: BLE001 - any parser error means unreadable file
        raise WorkbookError(f"The file is not a readable Excel workbook ({type(e).__name__}: {e})") from e

    db = Database()
    known = 0
    for name, spec in S.SPECS.items():
        if name not in wb.sheetnames:
            notes.append(f"Sheet '{name}' was missing and has been created empty.")
            continue
        known += 1
        db.tables[name] = _read_sheet(wb[name], spec, notes)
    wb.close()
    if known == 0:
        raise WorkbookError("The workbook does not contain any Profit Planner sheets.")
    db.ensure_default_settings()
    return db, notes


def _read_sheet(ws, spec: S.SheetSpec, notes: list[str]) -> Table:
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        header = ()
    col_map: list[tuple[int, str]] = []  # (index, column name)
    years: list[int] = []
    extras: list[str] = []
    seen = set()
    lower_spec = {c.lower(): c for c in spec.column_names}
    for idx, h in enumerate(header):
        if h is None or str(h).strip() == "":
            continue
        hs = str(h).strip()
        y = S.is_year_header(h) if spec.year_columns else None
        if y is not None:
            cname = str(y)
            if y not in years:
                years.append(y)
        elif hs.lower() in lower_spec:
            cname = lower_spec[hs.lower()]
        else:
            cname = hs
            if cname not in extras:
                extras.append(cname)
                notes.append(f"Sheet '{spec.name}': extra column '{cname}' is kept but not used in calculations.")
        if cname in seen:
            notes.append(f"Sheet '{spec.name}': duplicate column '{cname}' ignored.")
            continue
        seen.add(cname)
        col_map.append((idx, cname))
    for c in spec.column_names:
        if c not in seen:
            notes.append(f"Sheet '{spec.name}': column '{c}' was missing and has been added.")

    table = Table(spec, years=years, extra_columns=extras)
    for raw in rows_iter:
        if raw is None or all(v is None or (isinstance(v, str) and v.strip() == "") for v in raw):
            continue
        row = {c: None for c in table.columns()}
        for idx, cname in col_map:
            v = raw[idx] if idx < len(raw) else None
            if isinstance(v, datetime):
                v = v.isoformat(sep=" ")
            col = table.col(cname)
            val, _err = coerce(col, v) if col is not None else (v, None)
            row[cname] = val
        table.rows.append(row)
    return table


def write_workbook_bytes(db: Database, results: list | None = None) -> bytes:
    wb = Workbook()
    ws0 = wb.active
    ws0.title = S.INSTRUCTIONS
    _write_instructions(ws0, db)
    for name in S.SHEET_ORDER:
        _write_sheet(wb.create_sheet(name), db[name], db)
    if results is not None:
        _write_results(wb.create_sheet(S.RESULTS), results, db.reporting_currency)
    wb.properties.creator = "Profit Planner"
    wb.properties.title = "Profit Planner Database"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _write_sheet(ws, table: Table, db: Database):
    cols = table.columns()
    spec = table.spec
    for j, cname in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=j, value=cname)
        col = table.col(cname)
        cell.font = HEADER_FONT
        cell.fill = KEY_FILL if cname in (spec.key,) + tuple(spec.unique) else (
            YEAR_FILL if S.is_year_header(cname) and spec.year_columns else HEADER_FILL)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = Border(bottom=THIN)
        if col is not None and col.help:
            cm = Comment(col.help, "Profit Planner")
            cm.width, cm.height = 300, 110
            cell.comment = cm
        ws.column_dimensions[get_column_letter(j)].width = (col.width if col else 16) + 2
    for i, r in enumerate(table.rows, start=2):
        for j, cname in enumerate(cols, start=1):
            v = to_excel(table.col(cname), r.get(cname))
            cell = ws.cell(row=i, column=j, value=v)
            if isinstance(v, str) and v.startswith("="):
                cell.data_type = "s"   # keep text that looks like a formula as text
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "B2" if spec.key or spec.unique else "A2"
    if cols:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(len(table.rows) + 1, 2)}"
    _add_validations(ws, table, cols)


def _add_validations(ws, table: Table, cols: list[str]):
    last = 5000
    for j, cname in enumerate(cols, start=1):
        col = table.col(cname)
        if col is None:
            continue
        letter = get_column_letter(j)
        dv = None
        if col.kind in (S.CHOICE, S.BOOL) and col.choices:
            dv = DataValidation(type="list", formula1='"' + ",".join(col.choices) + '"', allow_blank=True)
        elif col.kind == S.REF and col.ref:
            ref_spec = S.SPECS[col.ref]
            k_idx = ref_spec.column_names.index(ref_spec.key) + 1
            kl = get_column_letter(k_idx)
            dv = DataValidation(type="list", formula1=f"='{col.ref}'!${kl}$2:${kl}${last}", allow_blank=True)
        if dv is not None:
            dv.errorStyle = "warning"
            dv.showErrorMessage = True
            dv.error = "This value is not in the list. The app will flag it as an error."
            dv.add(f"{letter}2:{letter}{last}")
            ws.add_data_validation(dv)


def _write_instructions(ws, db: Database):
    lines = [
        ("PROFIT PLANNER DATABASE", True),
        (f"Created by Profit Planner {__version__}. You can edit every sheet here in Excel or inside the app.", False),
        ("", False),
        ("HOW TO EDIT IN EXCEL", True),
        ("1. Close the Profit Planner app or make sure it has no unsaved changes, then edit and save this file.", False),
        ("2. Keep the column headers in row 1 exactly as they are. Add new rows at the bottom.", False),
        ("3. Percentages are plain numbers: 8.1 means 8.1 %.", False),
        ("4. Amounts are in the currency stated in the row ('Currency' column) or, for Company Types, "
         "in the currency of that country.", False),
        ("5. To add prices for a new year in 'Materials' or 'Services', add a column whose header is only "
         "the year (e.g. 2027).", False),
        ("6. IDs (first column) must be unique. Other sheets refer to them, e.g. 'Product Materials' "
         "refers to 'Product ID' and 'Material ID'.", False),
        ("7. Formulas are allowed, but the app stores their calculated values the next time it saves.", False),
        ("8. Formatting is regenerated by the app on save; your data is never removed. Extra columns are kept.", False),
        ("9. The sheet 'Results (read-only)' is a snapshot written by the app - changes there are ignored.", False),
        ("", False),
        ("SAFETY", True),
        ("The app always works on a working copy (folder '.profitplanner'). Every save is verified first, then "
         "copied to this file. Previous versions are kept in the 'Backups' folder.", False),
        ("", False),
        ("SHEETS", True),
    ]
    for name in S.SHEET_ORDER:
        lines.append((f"{name}: {S.SPECS[name].description}", False))
    lines += [("", False), ("DISCLAIMER", True),
              ("Tax rates, fees and costs are indicative planning values. Verify them with a local "
               "accountant or tax advisor before making decisions.", False)]
    ws.column_dimensions["A"].width = 130
    for i, (text, bold) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=text)
        c.alignment = Alignment(wrap_text=True)
        if bold:
            c.font = Font(bold=True, size=12 if i > 1 else 16, color="1F4E78")


RESULT_COLUMNS = [
    ("Configuration ID", "config_id"), ("Name", "name"), ("Status", "status"),
    ("Product", "product_name"), ("HQ", "hq"), ("Legal Form", "legal_form"), ("Liability", "liability"),
    ("Market", "market"), ("Sale Type", "sale_type"), ("Material Year", "material_year"),
    ("Gross Price", "gross_price"), ("VAT", "vat"), ("Net Revenue", "net_revenue"),
    ("Production Cost", "production_cost"), ("Payment Fee", "payment_fee"), ("Commission", "commission"),
    ("Shipping", "shipping"), ("Customs", "customs"), ("Returns", "returns"),
    ("Profit Before Tax", "profit_before_tax"), ("Social Contributions", "social"),
    ("Profit Tax", "profit_tax"), ("Net Profit (company)", "net_profit_company"),
    ("Distribution Tax", "distribution_tax"), ("Net to Owner", "net_to_owner"),
    ("Net to Owner % of Gross", "margin_pct"), ("Break-even Gross Price", "break_even_gross"),
    ("Annual Net to Owner", "annual_net_to_owner"), ("Startup Cash Required", "startup_total"),
    ("Payback (months)", "payback_months"),
]


def _write_results(ws, results: list, currency: str):
    ws.cell(row=1, column=1, value=f"Snapshot of calculated results per unit in {currency} - "
                                   f"written {datetime.now():%Y-%m-%d %H:%M}. Read-only: edits here are ignored.")
    ws.cell(row=1, column=1).font = Font(italic=True, color="7F7F7F")
    for j, (title, _a) in enumerate(RESULT_COLUMNS, start=1):
        c = ws.cell(row=2, column=j, value=title)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True)
        ws.column_dimensions[get_column_letter(j)].width = 14
    for i, r in enumerate(results, start=3):
        for j, (_t, attr) in enumerate(RESULT_COLUMNS, start=1):
            v = getattr(r, attr, None)
            if isinstance(v, float):
                v = round(v, 2)
            c = ws.cell(row=i, column=j, value=v)
            if isinstance(v, float):
                c.number_format = "#,##0.00"
    ws.freeze_panes = "C3"
