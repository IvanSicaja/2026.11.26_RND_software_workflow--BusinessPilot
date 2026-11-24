"""Export of calculated results to a separate Excel report."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .calc import Result
from .database import Database
from .excel_io import RESULT_COLUMNS
from .storage import atomic_write

HEAD = PatternFill("solid", fgColor="1F4E78")


def export_results(db: Database, results: list[Result], path: str | Path):
    import io
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    cur = db.reporting_currency
    ws.cell(row=1, column=1, value=f"{db.setting('Company Name', '')} - results per unit in {cur} "
                                   f"({datetime.now():%Y-%m-%d %H:%M})").font = Font(bold=True, size=13)
    for j, (title, _a) in enumerate(RESULT_COLUMNS, start=1):
        c = ws.cell(row=3, column=j, value=title)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEAD
        ws.column_dimensions[get_column_letter(j)].width = 15
    for i, r in enumerate(results, start=4):
        for j, (_t, attr) in enumerate(RESULT_COLUMNS, start=1):
            v = getattr(r, attr, None)
            if not r.ok and isinstance(v, (int, float)) and attr not in ("material_year",):
                v = None
            c = ws.cell(row=i, column=j, value=round(v, 2) if isinstance(v, float) else v)
            if isinstance(v, float):
                c.number_format = "#,##0.00"
    ws.freeze_panes = "C4"

    for r in results:
        name = "".join(ch for ch in (r.config_id or "Config") if ch not in '[]:*?/\\')[:31] or "Config"
        base, n = name, 2
        while name in wb.sheetnames:
            name = f"{base[:28]}_{n}"
            n += 1
        s = wb.create_sheet(name)
        s.column_dimensions["A"].width = 55
        s.column_dimensions["B"].width = 18
        s.cell(row=1, column=1, value=f"{r.config_id} - {r.name}").font = Font(bold=True, size=13)
        s.cell(row=2, column=1, value=f"{r.product_name} | HQ {r.hq} ({r.legal_form}) -> market {r.market} "
                                      f"| {r.sale_type} | amounts per unit in {cur}")
        row = 4
        if not r.ok:
            s.cell(row=row, column=1, value="Error: " + r.error)
            continue
        for ln in r.lines:
            a = s.cell(row=row, column=1, value=ln.label)
            b = s.cell(row=row, column=2, value=round(ln.amount, 2))
            b.number_format = "#,##0.00"
            if ln.group == "Result":
                a.font = b.font = Font(bold=True)
            row += 1
        row += 1
        for label, v in [("Min. share capital", r.share_capital), ("Formation costs", r.formation_costs),
                         ("Tools to buy", r.tools_cost), ("Startup material stock", r.stock_cost),
                         ("Startup cash required", r.startup_total),
                         ("Annual net to owner", r.annual_net_to_owner),
                         ("Payback (months)", r.payback_months), ("Break-even gross price", r.break_even_gross)]:
            s.cell(row=row, column=1, value=label)
            c = s.cell(row=row, column=2, value=round(v, 2) if isinstance(v, float) else v)
            c.number_format = "#,##0.00"
            row += 1
        if r.warnings:
            row += 1
            s.cell(row=row, column=1, value="Warnings").font = Font(bold=True)
            for w in r.warnings:
                row += 1
                s.cell(row=row, column=1, value=w)
    buf = io.BytesIO()
    wb.save(buf)
    atomic_write(Path(path), buf.getvalue())
