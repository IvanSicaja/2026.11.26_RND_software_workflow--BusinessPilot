# Profit Planner

Desktop application (Python + PySide6) that answers three questions for a product business:

1. **What does one unit really cost me?** Materials (with waste and prices per year), labour, extra services, tool depreciation and company running costs.
2. **What do I keep from the customer's price?** VAT, payment fees, marketplace commission, shipping, customs, expected returns, profit tax, social contributions and dividend tax — down to the **net amount for the owner**.
3. **Where should I found the company?** Compare HQ countries and legal forms (GmbH, AG, UG, d.o.o., j.d.o.o., obrt, sole proprietorship …) by startup cash, liability and net profit — for Switzerland, Germany, Croatia, Bosnia and Herzegovina and more.

All data lives in **one Excel workbook** that you can edit in Excel *or* in the app.

---

## Quick start

| | |
|---|---|
| **Windows (from source)** | Install Python 3.10+ from python.org, then double-click `publish/run_windows.bat` |
| **Any OS (from source)** | `pip install -r requirements.txt` then `python main/main.py` |
| **Build the Windows .exe** | Double-click `publish/build_windows.bat` → runs all tests → creates **`publish/main.exe`** (one file, send it to clients) |
| **Build on macOS/Linux** | `./publish/build.sh` → `publish/main` |
| **Run the tests** | `pip install -r docs/03_req-files/requirements-dev.txt` then `python -m pytest tests` |

On first start the app creates `Documents/ProfitPlanner/ProfitPlanner_Database.xlsx` with starter data (4 furniture products, 21 materials, 15 tools, 13 countries, 14 legal forms, 8 example configurations). The same starter database is in `data/raw/ProfitPlanner_Database.xlsx`. Another file can be opened with *Open database…* or by passing its path: `python main/main.py path\to\file.xlsx`.

Where everything is: see [`directory_structure_explained.md`](directory_structure_explained.md).

## The app

| Tab | Purpose |
|---|---|
| **Results** | One row per configuration: gross price, VAT, production, shipping, customs, fees, taxes, **net to owner**, % of gross, break-even price, startup cash, payback. Green = best for that product. Click a row for the full breakdown, a cost bar and startup-capital details. Export to Excel. |
| **Where to found?** | Pick product + market → every legal form in every selected HQ country is calculated and ranked. Save the best one as a configuration with one click. |
| **Configurations** | Your scenarios: product, material price year, HQ country, legal form, market, B2C/B2B, payment method, fixed gross price *or* markup, annual volume, startup stock, commission, small-business VAT exemption, plus extra services. |
| **Products** | Products with weight and labour hours; below: materials (bill of materials) and tools of the selected product, with material cost per year. |
| **Materials / Services** | Prices per year. *Add year…* creates a new year column and can copy last year's prices with a % increase. |
| **Tools** | Purchase price (startup capital) and useful life (depreciation per unit). |
| **Countries & Legal Forms** | VAT, labour cost, return rate; legal forms with liability, min. share capital, formation and annual costs, profit tax, social contributions, dividend tax. |
| **Shipping, Customs & Payment** | Rates per route (country, region or `*`; the most specific row wins), duty + clearance, payment fees. |
| **Currencies & Settings** | Exchange rates (units per 1 EUR), company name, reporting currency. |

Editing: double-click or just start typing; drop-down lists for IDs and choices; *Ctrl+N* new row, *Delete* deletes, *Ctrl+S* saves (autosave is on by default), *Ctrl+K* data check. Renaming an ID updates every reference. Rows still in use cannot be deleted. Invalid values are kept, shown in red and listed in **Data check** — they never crash a calculation; the affected configuration shows the reason instead.

## Data safety

* The app **never works on your Excel file directly**. It works on a working copy in `.profitplanner/` next to the database.
* Every save is serialised and **read back and compared** first — if anything differs, nothing is written.
* The working copy is replaced atomically (write temp → flush → fsync → rename). **Only after that succeeds** the Excel file is backed up and replaced the same way. A power cut at any moment leaves the old or the new version of each file — never a half-written file; unfinished syncs are completed on the next start.
* If the Excel file is open in Excel (locked), changes stay safe in the working copy and the file is updated automatically when Excel is closed.
* Edits saved in Excel are picked up automatically while the app is running. If both sides changed, the app asks which version to keep — **the other one goes to `Backups/`**.
* `Backups/` keeps the last 60 versions (at most one every 10 minutes, plus one before every conflict resolution or restore). *Backups…* restores any of them.
* Only one app window can open a database at a time.

## Editing in Excel

Keep the headers in row 1, add rows at the bottom. Percentages are plain numbers (`8.1` = 8.1 %). Decimal commas are accepted. A new year column for prices is a column whose header is just the year (e.g. `2027`). Header cells have comments explaining each column; drop-down validations help with IDs. Extra columns you add are kept. The sheets *Instructions* and *Results (read-only)* are regenerated by the app.

## Calculation model

The complete formula and the legal-form comparison are in [`docs/02_cores-docs-and-comparison-tables/`](docs/02_cores-docs-and-comparison-tables/).

## Tests

`QT_QPA_PLATFORM=offscreen python -m pytest tests` — 94 automated tests:
hand-calculated scenarios for every line of the calculation, break-even checks, B2B/B2C/VAT exemption/customs/region fallbacks, error handling for broken data, random-garbage fuzzing of the whole database, crash simulations (power loss during each save step, locked files, corrupt files, deleted files, lost state), conflict resolution, manual Excel edits (decimal commas, new rows, new year columns, extra columns, deleted sheets/columns), re-saving in a real spreadsheet program, and end-to-end GUI tests of every tab, every cell editor, autosave, external edits, conflicts, backups and export.

## Disclaimer

Tax rates, fees, shipping and formation costs in the starter data are **indicative planning values (November 2026)**. Verify them with a local accountant or tax advisor before making decisions, and keep them up to date in the database.
