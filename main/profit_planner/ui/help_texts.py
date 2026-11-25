"""Hover help for every element of the user interface.

Every tooltip has the same three parts so that it is always clear what an element is for:
  1. what it is / what it does,
  2. a real example from this project (a small furniture company making tables),
  3. optionally: when to use it ("Use it when ...").
"""
from __future__ import annotations

from html import escape

from .. import schema as S
from . import theme


def tip(title: str, what: str, example: str, when: str = "") -> str:
    """Build a rich-text tooltip. Plain text arguments are escaped."""
    parts = [f"<p style='margin:0 0 4px 0'><b style='color:{theme.ACCENT_TEXT}'>{escape(title)}</b></p>",
             f"<p style='margin:0 0 6px 0'>{escape(what)}</p>"]
    if when:
        parts.append(f"<p style='margin:0 0 6px 0'><b style='color:{theme.TEXT_MUTED}'>Use it when:</b> "
                     f"{escape(when)}</p>")
    parts.append(f"<p style='margin:0'><b style='color:{theme.GOOD}'>Example:</b> {escape(example)}</p>")
    return "<qt>" + "".join(parts) + "</qt>"


# ---------------------------------------------------------------------------------------
# Toolbar
TOOLBAR = {
    "Save": tip("Save (Ctrl+S)",
                "Saves all changes immediately: first to the verified working copy, then to your Excel file. "
                "With Autosave on you rarely need it.",
                "You raised the oak price to 105 EUR and want to send the Excel file to your accountant right "
                "now - press Save, then the file is guaranteed to contain 105.",
                "you switched Autosave off, or before copying / e-mailing the Excel file."),
    "Reload from Excel": tip("Reload from Excel (Ctrl+R)",
                             "Reads the Excel database again and shows its current content in the app.",
                             "Your colleague entered the 2027 material prices directly in Excel on the shared "
                             "drive. Click Reload and the new prices appear in Materials and in all results.",
                             "the Excel file was changed outside the app (normally this is detected automatically)."),
    "Open in Excel": tip("Open in Excel",
                         "Opens the database file in Excel (or your spreadsheet program) for bulk editing. "
                         "Save and close Excel afterwards - the app loads your changes automatically.",
                         "You received a new price list from your timber supplier with 40 lines. Paste it into "
                         "the 'Materials' sheet in Excel instead of typing every price in the app.",
                         "you want to paste or edit many rows at once."),
    "Open folder": tip("Open folder",
                       "Opens the folder that contains the database, the 'Backups' folder and the working copy.",
                       "You want to attach ProfitPlanner_Database.xlsx to an e-mail or copy it to a USB stick.",
                       "you need the file itself."),
    "Data check": tip("Data check (Ctrl+K)",
                      "Lists every missing or invalid value in all tables. Double-click an entry to jump to "
                      "the exact cell.",
                      "A configuration shows 'Error' in Results. Data check tells you: 'Tools, row 5, Purchase "
                      "Price: value is required' - double-click and type the price of the drill.",
                      "a result shows Error or the status bar shows a red error count."),
    "Backups...": tip("Backups",
                      "Shows earlier versions of the Excel file (one at most every 10 minutes, last 60 kept) and "
                      "restores one of them.",
                      "You accidentally deleted all walnut prices yesterday. Open Backups, pick the version from "
                      "yesterday morning and restore it.",
                      "you want to undo a mistake that was already saved."),
    "Open database...": tip("Open database (Ctrl+O)",
                            "Opens another Profit Planner Excel file. The current one is saved first.",
                            "You keep one database for furniture and a second one for a new line of lamps - "
                            "switch between them here.",
                            "you work with more than one database file."),
    "New database...": tip("New database",
                           "Creates a new Excel database filled with the starter data (example products, "
                           "countries, legal forms) and opens it.",
                           "You want to plan a completely separate business (e.g. kitchen cabinets) without "
                           "mixing it with your table data.",
                           "you start a new, separate plan."),
    "Autosave": tip("Autosave",
                    "When ticked, every change is saved about one second after you make it.",
                    "You change the Swiss labour cost from 58 to 60 CHF - one second later it is safely in the "
                    "Excel file, even if the power goes out right after.",
                    "always - untick it only if you want to try changes and save them manually."),
    "About": tip("About",
                 "Shows the version, the location of the database and how your data is protected.",
                 "Your client asks which version of the program they have - it is shown here.",
                 "you need the version number or the database location."),
}

# ---------------------------------------------------------------------------------------
# Main tabs
TABS = {
    "Results": tip("Results",
                   "The answer: for every configuration (scenario) what the customer pays, every deduction and "
                   "what you keep per table, per year, plus the startup cash you need.",
                   "With the starter data, row CFG-004 'HR d.o.o. -> Germany': the customer pays 2,290 EUR and you "
                   "keep about 785 EUR per oak table. Startup cash is about 18,900 EUR.",
                   "you want to know which setup earns the most."),
    "Where to found?": tip("Where to found?",
                           "Quick comparison: one product and one market, calculated for EVERY legal form in every "
                           "selected country, ranked by what you keep.",
                           "Select 'Oak dining table' and market 'Germany', tick CH, DE, HR, BA and click Compare: "
                           "with the starter data a Croatian d.o.o. keeps more than twice as much per table as a German GmbH.",
                           "you have not yet decided where to register your company."),
    "Configurations": tip("Configurations",
                          "Your saved scenarios. One row = one product sold from one company (country + legal form) "
                          "to one market at one price. Every row becomes one line in Results.",
                          "Add a row: product PRD-OAK-DINING, HQ HR, company HR-DOO, market CH, price 2,490 CHF - "
                          "Results shows the profit of selling oak tables to Switzerland from Croatia.",
                          "you want to keep a scenario and compare it with others."),
    "Products": tip("Products",
                    "What you make: weight, labour hours, and below the materials and tools each product needs.",
                    "The oak dining table weighs 55 kg packed, takes 14 hours and uses 2.6 m2 of oak, 8 m of "
                    "steel tube, 0.6 L of oil ...",
                    "you add a new product or change how much material a product uses."),
    "Materials": tip("Materials",
                     "Everything you buy to make products, with a price per unit for each year.",
                     "Oak board costs 85 EUR/m2 in 2024, 90 in 2025, 95 in 2026. Next year: 'Add year...' -> "
                     "2027, copy 2026, +5 %.",
                     "prices change or you start using a new material."),
    "Services": tip("Services",
                    "Extras you charge the customer for (custom size, colour, assembly ...) with a price per year.",
                    "A customer wants the table 230 cm instead of 200 cm: 'Custom dimensions' adds 120 EUR to the "
                    "price and 2 hours of work.",
                    "you offer something extra and want it included in the price."),
    "Tools": tip("Tools",
                 "Machines and tools you must buy. Their price counts as startup cash and is spread over the "
                 "products as depreciation.",
                 "A table saw for 3,500 EUR that lasts 8 years, with 120 tables per year, costs about 3.65 EUR per "
                 "table.",
                 "you buy a new machine or prices of tools change."),
    "Countries & Legal Forms": tip("Countries & Legal Forms",
                                   "Top: country data (VAT, labour cost, returns). Bottom: the legal forms you can "
                                   "found in each country, with capital, costs, liability and taxes.",
                                   "Croatia: VAT 25 %, labour 16 EUR/h. Croatian d.o.o.: 2,500 EUR capital, 10 % "
                                   "profit tax, 12 % dividend tax, liability limited to the company.",
                                   "tax rates change or you want to compare a new country."),
    "Shipping, Customs & Payment": tip("Shipping, Customs & Payment",
                                       "What it costs to deliver an order, customs between countries and the fees "
                                       "of payment providers.",
                                       "Shipping CH -> DE: 120 CHF + 1.60 CHF per kg. A card payment in the EU costs "
                                       "1.5 % + 0.25 EUR.",
                                       "your carrier or payment provider changes its prices."),
    "Currencies & Settings": tip("Currencies & Settings",
                                 "Exchange rates and general settings such as your company name and the currency "
                                 "all results are shown in.",
                                 "Set 'Reporting Currency' to CHF and every result is shown in Swiss francs; update "
                                 "CHF to 0.94 per EUR when the rate moves.",
                                 "exchange rates change or you want results in another currency."),
}

INNER_TABS = {
    "Shipping": tip("Shipping rates", "Delivery cost per order for each route.",
                    "BA -> DE costs 230 BAM + 2.60 BAM per kg; a 55 kg table therefore costs 373 BAM to ship."),
    "Customs": tip("Customs rules", "Customs duty and clearance fees between different customs territories.",
                   "Switzerland -> EU: 0 % duty for furniture of Swiss origin, but 30 EUR clearance per shipment."),
    "Payment": tip("Payment methods", "Fees your payment provider keeps from each sale.",
                   "PayPal: 3.49 % + 0.39 EUR - on a 2,000 EUR table that is 70.19 EUR."),
}

# ---------------------------------------------------------------------------------------
# Table buttons, per sheet: (thing, add example, duplicate example, delete example)
_TABLE_EXAMPLES = {
    S.CONFIGS: ("scenario", "Add CFG-009 to test selling the walnut desk to Austria.",
                "Duplicate 'CH GmbH -> Germany' and change only the market to Austria - all other settings and "
                "extra services stay the same.", "Delete a scenario you no longer need, e.g. an old test row."),
    S.CONFIG_SERVICES: ("extra service of the selected scenario", "Add 'SRV-ENGRAVE' to CFG-001 so every table "
                        "in that scenario includes a logo engraving.", "",
                        "Remove the custom colour from CFG-006."),
    S.PRODUCTS: ("product", "Add 'Oak bench 180 cm', then list its materials and tools below.",
                 "Duplicate the oak dining table to create a walnut version - its materials and tools are copied, "
                 "then swap oak for walnut.", "Delete a product you stopped making (only possible when no "
                 "configuration uses it)."),
    S.PRODUCT_MATERIALS: ("material of the selected product", "Add MAT-EPOXY with quantity 1.5 kg to make a "
                          "river table.", "", "Remove the levelling feet if the product no longer uses them."),
    S.PRODUCT_TOOLS: ("tool needed for the selected product", "Add the welder to the side table because its "
                      "frame is welded.", "", "Remove the planer from a product made only from pre-cut boards."),
    S.MATERIALS: ("material", "Add 'Ash board 40 mm' with its price per m2.",
                  "Duplicate 'Oak solid board 40 mm' to create '... 30 mm' with a lower price.",
                  "Delete a material nobody uses (materials used in a product cannot be deleted)."),
    S.SERVICES: ("service", "Add 'Gift wrapping' for 25 EUR.", "Duplicate 'On-site assembly' to make "
                 "'On-site assembly - weekend' with a higher price.", "Delete a service you no longer offer."),
    S.TOOLS: ("tool", "Add a CNC router for 18,000 EUR, life 10 years.", "Duplicate the drill set if you buy a "
              "second one for another workplace.", "Delete a tool you sold."),
    S.COUNTRIES: ("country", "Add Austria (AT) to sell there - with VAT 20 %, region EU.",
                  "Duplicate Germany to create Austria quickly and change only what differs.",
                  "Delete a country that no configuration, legal form or route uses."),
    S.COMPANY_TYPES: ("legal form", "Add 'AT-GMBH' for an Austrian GmbH with 10,000 EUR capital.",
                      "Duplicate 'DE-GMBH' and adjust it for a GmbH in another German city with different "
                      "trade tax.", "Delete a legal form you are no longer considering."),
    S.SHIPPING: ("shipping route", "Add HR -> AT: 70 EUR + 1.1 EUR/kg.",
                 "Duplicate HR -> DE and change the destination to AT.", "Delete an old route."),
    S.CUSTOMS: ("customs rule", "Add a rule BA -> CH with 0 % duty and 40 CHF clearance.",
                "Duplicate an existing rule and change the destination.", "Delete a rule that no longer applies."),
    S.PAYMENT: ("payment method", "Add 'Apple Pay' with 1.5 % + 0.25 EUR.", "Duplicate 'Card - European' to "
                "create a variant with a negotiated lower fee.", "Delete a provider you stopped using."),
    S.FX: ("currency", "Add HUF (Hungarian forint) with 395 per EUR.", "", "Delete a currency nobody uses."),
    S.SETTINGS: ("setting", "Normally not needed - the important settings already exist.", "",
                 "Settings like 'Reporting Currency' should not be deleted."),
}


def add_tip(sheet: str) -> str:
    thing, ex, _d, _x = _TABLE_EXAMPLES[sheet]
    return tip(f"Add a {thing} (Ctrl+N)",
               f"Adds a new row at the end of '{sheet}' with a new ID. Fill in the fields marked with *.", ex)


def duplicate_tip(sheet: str) -> str:
    thing, _a, ex, _x = _TABLE_EXAMPLES[sheet]
    return tip(f"Duplicate the selected {thing}",
               "Creates a copy of the selected row with a new ID (and copies its linked lists), so you only "
               "change what is different.", ex or "Copy a row and change one value.")


def delete_tip(sheet: str) -> str:
    thing, _a, _d, ex = _TABLE_EXAMPLES[sheet]
    return tip(f"Delete the selected {thing} (Delete key)",
               "Deletes the selected row(s) after asking. Rows that are still used elsewhere are protected and "
               "the app tells you where they are used. A backup of the Excel file is kept.", ex)


def search_tip(sheet: str) -> str:
    examples = {S.MATERIALS: "Type 'oak' to see only oak materials.", S.CONFIGS: "Type 'DE' to see every "
                "scenario that involves Germany.", S.COUNTRIES: "Type 'balkans' to see Western Balkan countries."}
    return tip("Search", "Shows only the rows that contain the text in any column. Clear it to see all rows again.",
               examples.get(sheet, "Type 'steel' to find every row that mentions steel."))


ADD_YEAR = tip("Add year...",
               "Adds a new price column for a year. Prices can be copied from an existing year and raised by a "
               "percentage in one step.",
               "In December your supplier announces +6 % for next year: Add year -> 2027, copy from 2026, change "
               "by 6 %. Then set 'Material Price Year' to 2027 in a configuration to see the new profit.",
               "a new year starts or you want to plan with future prices.")
REMOVE_YEAR = tip("Remove year...",
                  "Deletes the price column of one year (a backup of the Excel file is kept).",
                  "You added 2028 by mistake - remove it again.",
                  "a year column is wrong or no longer needed.")

# ---------------------------------------------------------------------------------------
# Results tab
RESULTS = {
    "product_filter": tip("Product filter", "Shows only the configurations of one product.",
                          "Choose 'Walnut desk 160x80' to compare only the desk scenarios with each other."),
    "only_active": tip("Active only", "Hides configurations whose 'Active' column is set to No.",
                       "You keep old scenarios (Active = No) for reference but do not want them in the list."),
    "edit": tip("Edit configuration", "Jumps to the selected scenario in the Configurations tab (double-click a "
                "row does the same).", "The Bosnian scenario shows a loss - click here to change its price."),
    "export": tip("Export to Excel", "Saves all results into a new Excel report: one summary sheet and one "
                  "detailed sheet per configuration.", "Send the report to your bank or business partner as the "
                  "basis for a loan discussion."),
    "table": tip("Results table", "One row per configuration, all amounts per unit in the reporting currency. "
                 "Green = best result for that product, red = loss or error. Click a column header to sort, "
                 "double-click a row to edit it.", "Sort by 'NET TO OWNER' to see the most profitable setup "
                 "at the top."),
    "lines": tip("Price breakdown", "Every amount from the price the customer pays down to what you keep, for one "
                 "unit. Blue = production costs, yellow = sales deductions, purple = taxes.",
                 "CFG-003 (DE GmbH -> Germany): gross 2,290 EUR - VAT 366 - materials 459 - labour 588 - shipping "
                 "98 ... = about 347 EUR net to owner."),
    "side": tip("Startup capital & details", "How much money you need before the first sale, plus key figures "
                "and the materials used per unit.", "Swiss GmbH: the 13,700 EUR of tools and stock are paid from the "
                "20,000 CHF share capital; with formation costs you need about 24,200 EUR in total."),
    "bar": tip("Where the customer's money goes", "Each colour shows which share of the gross price goes to VAT, "
               "production, shipping, fees, taxes - and what stays with you (green).",
               "If green is only 10 %, a small rise in material prices could already make you lose money."),
}

KPI = {
    "Customer pays (gross)": tip("Customer pays (gross)", "The full price the customer pays, including VAT and "
                                 "extra services.", "2,290 EUR for the table + 143 EUR custom size (120 EUR + German VAT) = 2,433 EUR."),
    "Net to owner / unit": tip("Net to owner per unit", "What finally stays in YOUR pocket from one sale after all "
                               "costs, taxes and dividend tax. Green = profit, red = loss.",
                               "CFG-004: from a 2,290 EUR table you keep about 785 EUR = 34 % of what the customer paid."),
    "Net to owner / year": tip("Net to owner per year", "Net to owner per unit multiplied by the annual volume of "
                               "the configuration.", "About 785 EUR x 120 tables per year = about 94,200 EUR per year."),
    "Startup cash required": tip("Startup cash required", "Money needed before you start: formation costs plus "
                                 "share capital or tools + first material stock (whichever is higher). Below: how "
                                 "many months until it is earned back.",
                                 "German GmbH: 1,500 EUR formation + 25,000 EUR capital = 26,500 EUR, earned back "
                                 "in about 7.6 months (CFG-003)."),
    "Company": tip("Company", "The legal form and who is liable for debts.",
                   "GmbH (CH) - Limited: if the company fails, your private savings are safe. A sole "
                   "proprietorship is 'Unlimited': you are liable with your private assets."),
}

RESULT_COLUMNS = {
    "ID": ("Configuration ID", "CFG-002"),
    "Name": ("Name of the scenario", "'CH GmbH -> Germany'"),
    "Product": ("Product sold in this scenario", "Oak dining table 200x100"),
    "HQ": ("Country where the company is registered and produces", "CH = the workshop is in Switzerland"),
    "Legal form": ("Legal form of the company", "GmbH, d.o.o., sole proprietorship ..."),
    "Liability": ("Who pays if the company has debts", "Limited = only the company; Unlimited = also you "
                  "privately"),
    "Market": ("Country where the customer lives", "DE = tables are delivered to customers in Germany"),
    "Type": ("B2C = sale to private persons, B2B = sale to companies", "A hotel buying 20 tables is B2B"),
    "Gross price": ("Price the customer pays incl. VAT", "2,290 EUR"),
    "VAT": ("VAT included in the gross price, paid to the tax office", "19 % in Germany = 365.63 EUR of "
            "2,290 EUR"),
    "Production": ("Cost to make one unit: materials, labour, tool depreciation, fixed company costs",
                   "Materials 459 EUR + 14 h labour 588 EUR + tools and fixed costs (DE GmbH)"),
    "Shipping": ("Delivery cost per order", "120 CHF + 55 kg x 1.60 CHF"),
    "Customs": ("Customs duty + clearance fee", "Shipping from Bosnia to Switzerland: 0 % duty + 40 CHF "
                "clearance"),
    "Fees+returns": ("Payment fees, sales commission and the expected cost of returns",
                     "1.5 % card fee + 8 % of orders returned in Germany"),
    "Profit before tax": ("Net revenue minus all costs, before taxes", "Taxes are calculated on this amount"),
    "Taxes": ("Profit tax + social contributions + dividend tax", "Croatian d.o.o.: 10 % profit tax + 12 % on "
              "the payout"),
    "NET TO OWNER": ("What you keep per unit after everything", "The number to compare setups by"),
    "% of gross": ("Net to owner as a share of the customer's price", "30 % = 30 cents of every euro paid stay "
                   "with you"),
    "Break-even price": ("Gross price at which you make exactly 0 profit", "CFG-004: below about 1,089 EUR every "
                         "table loses money"),
    "Net per year": ("Net to owner x annual volume", "785 EUR x 120 = 94,200 EUR"),
    "Startup cash": ("Money needed to start (formation + capital or tools and stock)", "26,500 EUR for a "
                     "German GmbH"),
    "Payback (months)": ("Months until the startup cash is earned back", "7.6 = after about 7.6 months of sales"),
    "Status": ("OK, OK with warnings, or Error with the reason", "'Error: no shipping rate from BA to IT' -> "
               "add that route in Shipping"),
}


def result_column_tip(title: str) -> str:
    what, ex = RESULT_COLUMNS[title]
    return tip(title, what, ex)


_EXPLORER_COLUMNS = {
    "Rank": ("Position in the ranking, 1 = keeps the most money", "1"),
    "HQ country": RESULT_COLUMNS["HQ"],
    "Shipping + customs": ("Delivery cost plus customs duty and clearance per order",
                           "Croatia -> Germany: no customs inside the EU, only shipping"),
    "NET TO OWNER / unit": RESULT_COLUMNS["NET TO OWNER"],
}


def explorer_column_tip(title: str) -> str:
    what, ex = _EXPLORER_COLUMNS.get(title) or RESULT_COLUMNS[title]
    return tip(title, what, ex)


# ---------------------------------------------------------------------------------------
# "Where to found?" tab
EXPLORER = {
    "product": tip("Product", "The product you want to sell.", "Oak dining table 200x100"),
    "market": tip("Market country", "Where your customers are. VAT, shipping, customs and returns of this "
                  "country are used.", "Germany - most of your customers order from Munich and Stuttgart."),
    "sale_type": tip("Sale type", "B2C = private customers (VAT always charged). B2B = companies (no VAT on "
                     "cross-border sales because of reverse charge).", "A restaurant chain in Austria buying 30 "
                     "tables = B2B."),
    "payment": tip("Payment method", "How customers pay - its fee is deducted from every sale.",
                   "Most German customers pay by card: 'Card - European'."),
    "year": tip("Material price year", "Which year's material and service prices are used.",
                "Choose 2026 for today's prices or 2027 after you added next year's prices."),
    "fixed": tip("Fixed gross price", "You decide the customer price (incl. VAT) and see what remains.",
                 "Competitors sell similar tables for 2,290 EUR, so you use the same price."),
    "markup": tip("Markup on cost", "The app calculates the price: production cost + markup % + VAT.",
                  "Production cost 1,100 EUR + 60 % markup = 1,760 EUR net, plus German VAT = 2,094 EUR."),
    "price": tip("Gross price (incl. VAT)", "The customer price including VAT, in the currency next to it.",
                 "2,290 EUR in Germany or 2,490 CHF in Switzerland."),
    "price_cur": tip("Price currency", "Currency of the gross price (set automatically to the market currency).",
                     "CHF when you sell to Switzerland."),
    "markup_value": tip("Markup %", "Percentage added on top of the production cost (used with 'Markup on cost').",
                        "60 % means a table that costs 1,000 EUR to make is sold for 1,600 EUR net."),
    "volume": tip("Annual volume", "How many units you expect to sell per year. Fixed costs and machines are "
                  "spread over this number.", "120 tables per year = about 10 per month."),
    "stock": tip("Startup stock", "How many units' worth of material you buy before the first sale (counts "
                 "as startup cash).", "Material for 10 tables so you can deliver quickly."),
    "commission": tip("Sales commission", "Percentage of the gross price kept by a marketplace or sales agent.",
                      "Selling through a furniture marketplace that keeps 12 %."),
    "sbe": tip("Small-business VAT exemption", "Tick if your turnover is below the national VAT threshold - you "
               "charge no VAT. Only valid for sales in your own country.",
               "A Swiss sole proprietor selling for less than 100,000 CHF per year in Switzerland."),
    "hq_list": tip("HQ countries to compare", "Every legal form of each ticked country is calculated.",
                   "Tick CH, DE, HR and BA to compare 11 legal forms in one click."),
    "run": tip("Compare", "Calculates all selected legal forms and ranks them by net to owner (best first).",
               "Oak table to Germany: the top row shows 'd.o.o. (BA)', rank 2 'j.d.o.o. (HR)'."),
    "save": tip("Save selected as configuration", "Stores the selected row as a new scenario in Configurations, "
                "so it appears permanently in Results.", "You like the Croatian j.d.o.o. result - save it and "
                "fine-tune it later in Configurations."),
    "table": tip("Comparison", "Ranking of all legal forms. Green = best, red = loss or error. Select a row and "
                 "save it as a configuration.", "Oak table to Germany (starter data): rank 1 d.o.o. (BA) with about "
                 "930 EUR per table, the Swiss AG last."),
}

# ---------------------------------------------------------------------------------------
# Status bar and dialogs
STATUS = tip("Save status", "Green = everything saved in the Excel file. Orange = changes are safe in the working "
             "copy but not yet in Excel (e.g. Excel has the file open). Red = problem, read the message.",
             "Orange 'Excel file is open in Excel' - close Excel and the dot turns green by itself.")
ISSUES = tip("Data check summary", "Number of invalid or missing values. Click to see the list and jump to them.",
             "'1 error' after typing 'abc' as a price - click, double-click the entry, fix the number.")
ADD_YEAR_FIELDS = {
    "year": tip("New year", "The year of the new price column.", "2027"),
    "copy": tip("Copy prices from", "Fills the new year with the prices of an existing year.",
                "Copy 2026 so you only have to adjust the few prices that change."),
    "increase": tip("Change prices by", "Raises (or lowers, with a minus) all copied prices by this percentage.",
                    "+4 % expected inflation: 95 EUR oak becomes 98.80 EUR."),
}
BACKUP_LIST = tip("Backups", "Saved versions of the Excel file, newest first.",
                  "Pick '2026-11-20 09:12' to go back to the state before yesterday's changes.")
ISSUE_LIST = tip("Problems", "Each line names the table, the Excel row number and the column.",
                 "'Materials, row 7, column 2026: abc is not a number' - double-click to go there.")

# ---------------------------------------------------------------------------------------
# Column examples: (sheet, column) -> example
NOTES_EX = "Free text for your own remarks, e.g. 'price confirmed by supplier on 12 Nov'."
COLUMN_EXAMPLES = {
    (S.SETTINGS, "Setting"): "'Reporting Currency'",
    (S.SETTINGS, "Value"): "EUR (or CHF to see all results in Swiss francs)",
    (S.SETTINGS, "Description"): "Explanation of the setting",

    (S.FX, "Currency"): "CHF",
    (S.FX, "Units per 1 EUR"): "0.93 means 1 EUR = 0.93 CHF; EUR itself is always 1",
    (S.FX, "Notes"): "'rate from 1 Nov 2026'",

    (S.COUNTRIES, "Country Code"): "HR for Croatia, XX for 'rest of the world'",
    (S.COUNTRIES, "Country Name"): "Croatia",
    (S.COUNTRIES, "Region"): "EU - a shipping row 'HR -> EU' then covers every EU country without its own row",
    (S.COUNTRIES, "Customs Territory"): "All EU countries have 'EU', so Croatia -> Germany has no customs; "
                                        "Switzerland has 'CH', so EU -> CH does",
    (S.COUNTRIES, "Currency"): "EUR for Croatia, BAM for Bosnia and Herzegovina",
    (S.COUNTRIES, "VAT Standard Rate (%)"): "25 for Croatia, 19 for Germany, 8.1 for Switzerland",
    (S.COUNTRIES, "VAT Registration Threshold"): "60000 (EUR) in Croatia - below it a small business may skip VAT",
    (S.COUNTRIES, "Labour Cost per Hour"): "16 = one workshop hour in Croatia costs 16 EUR incl. contributions",
    (S.COUNTRIES, "Return Rate (%)"): "8 = 8 of 100 German customers send the table back",
    (S.COUNTRIES, "Return Handling Cost"): "30 = repairing and repacking one returned table costs 30 EUR",
    (S.COUNTRIES, "Notes"): NOTES_EX,

    (S.COMPANY_TYPES, "Company Type ID"): "HR-DOO",
    (S.COMPANY_TYPES, "Country Code"): "HR - this legal form exists in Croatia",
    (S.COMPANY_TYPES, "Legal Form"): "d.o.o.",
    (S.COMPANY_TYPES, "Description"): "Limited liability company",
    (S.COMPANY_TYPES, "Liability"): "'Limited (company only)' - your house is safe if the company fails",
    (S.COMPANY_TYPES, "Min Share Capital"): "2500 = a Croatian d.o.o. needs 2,500 EUR paid in",
    (S.COMPANY_TYPES, "Formation Costs"): "600 = notary, court register and bank fees once",
    (S.COMPANY_TYPES, "Annual Fixed Costs"): "1800 = accountant, chamber fees, bank account per year",
    (S.COMPANY_TYPES, "Profit / Income Tax Rate (%)"): "10 = Croatian profit tax below 1 million EUR revenue",
    (S.COMPANY_TYPES, "Owner Social Contributions (%)"): "10 = a Swiss sole proprietor pays ~10 % AHV on profit",
    (S.COMPANY_TYPES, "Distribution Tax Rate (%)"): "12 = tax when the d.o.o. pays the profit out to you",
    (S.COMPANY_TYPES, "Notes"): NOTES_EX,

    (S.MATERIALS, "Material ID"): "MAT-OAK",
    (S.MATERIALS, "Name"): "Oak solid board 40 mm",
    (S.MATERIALS, "Category"): "Wood, Metal, Paint, Glue ...",
    (S.MATERIALS, "Unit"): "m2 - the price and the quantities in products are per square metre",
    (S.MATERIALS, "Currency"): "EUR - the price is in euros even if you buy from Switzerland",
    (S.MATERIALS, "Waste (%)"): "15 = for 2.6 m2 net you actually buy 2.99 m2 because of off-cuts",
    (S.MATERIALS, "Supplier"): "Holz Huber GmbH",
    (S.MATERIALS, "Notes"): NOTES_EX,

    (S.SERVICES, "Service ID"): "SRV-SIZE",
    (S.SERVICES, "Name"): "Custom dimensions",
    (S.SERVICES, "Description"): "Non-standard length, width or height",
    (S.SERVICES, "Currency"): "EUR",
    (S.SERVICES, "Labour Hours"): "2 = custom size costs 2 extra workshop hours (counted as cost)",
    (S.SERVICES, "Notes"): NOTES_EX,

    (S.TOOLS, "Tool ID"): "TOOL-TABLESAW",
    (S.TOOLS, "Name"): "Table / panel saw",
    (S.TOOLS, "Category"): "Woodworking",
    (S.TOOLS, "Currency"): "EUR",
    (S.TOOLS, "Purchase Price"): "3500 = paid once at the start",
    (S.TOOLS, "Useful Life (years)"): "8 = 3,500 EUR / 8 years = 437.50 EUR per year spread over all tables",
    (S.TOOLS, "Notes"): NOTES_EX,

    (S.PRODUCTS, "Product ID"): "PRD-OAK-DINING",
    (S.PRODUCTS, "Name"): "Oak dining table 200x100",
    (S.PRODUCTS, "Description"): "Solid oak top, powder-coated steel frame",
    (S.PRODUCTS, "Weight (kg)"): "55 = packed weight, used for shipping cost per kg",
    (S.PRODUCTS, "Labour Hours"): "14 = cutting, gluing, sanding, oiling and packing one table",
    (S.PRODUCTS, "Notes"): NOTES_EX,

    (S.PRODUCT_MATERIALS, "Product ID"): "PRD-OAK-DINING",
    (S.PRODUCT_MATERIALS, "Material ID"): "MAT-OAK",
    (S.PRODUCT_MATERIALS, "Quantity"): "2.6 = one table top needs 2.6 m2 of oak (before waste)",
    (S.PRODUCT_MATERIALS, "Waste Override (%)"): "25 = this product wastes more oak than usual; empty = use the "
                                                 "material's default waste",
    (S.PRODUCT_MATERIALS, "Notes"): NOTES_EX,

    (S.PRODUCT_TOOLS, "Product ID"): "PRD-OAK-DINING",
    (S.PRODUCT_TOOLS, "Tool ID"): "TOOL-WELDER",
    (S.PRODUCT_TOOLS, "Quantity"): "2 = you need two of these tools",
    (S.PRODUCT_TOOLS, "Notes"): NOTES_EX,

    (S.SHIPPING, "Origin"): "HR (a country), 'Western Balkans' (a region) or * (anywhere)",
    (S.SHIPPING, "Destination"): "DE; if no DE row exists the app uses 'EU', then *",
    (S.SHIPPING, "Currency"): "EUR",
    (S.SHIPPING, "Cost per Shipment"): "85 = fixed price per order",
    (S.SHIPPING, "Cost per kg"): "1.3 = a 55 kg table adds 71.50 EUR",
    (S.SHIPPING, "Transit Days"): "5 (information only)",
    (S.SHIPPING, "Notes"): "'Quote from DHL Freight, Nov 2026'",

    (S.CUSTOMS, "Origin"): "Western Balkans",
    (S.CUSTOMS, "Destination"): "EU",
    (S.CUSTOMS, "Duty Rate (%)"): "0 for furniture with proof of origin; 10 for far export markets",
    (S.CUSTOMS, "Clearance Fee"): "30 = customs broker fee per shipment",
    (S.CUSTOMS, "Currency"): "EUR",
    (S.CUSTOMS, "Notes"): NOTES_EX,

    (S.PAYMENT, "Payment Method ID"): "PAY-CARD-EU",
    (S.PAYMENT, "Name"): "Card - European (e.g. Stripe)",
    (S.PAYMENT, "Fee (%)"): "1.5 = 1.5 % of the gross price",
    (S.PAYMENT, "Fixed Fee"): "0.25 = plus 0.25 EUR per payment",
    (S.PAYMENT, "Currency"): "EUR",
    (S.PAYMENT, "Notes"): NOTES_EX,

    (S.CONFIGS, "Configuration ID"): "CFG-004",
    (S.CONFIGS, "Name"): "'HR d.o.o. -> Germany'",
    (S.CONFIGS, "Active"): "No = keep the scenario but hide it in Results",
    (S.CONFIGS, "Product ID"): "PRD-OAK-DINING",
    (S.CONFIGS, "Material Price Year"): "2027 to calculate with next year's prices; empty = latest year",
    (S.CONFIGS, "HQ Country"): "HR = the company and the workshop are in Croatia",
    (S.CONFIGS, "Company Type ID"): "HR-DOO (the list only offers legal forms of the HQ country)",
    (S.CONFIGS, "Market Country"): "DE = customers in Germany",
    (S.CONFIGS, "Sale Type"): "B2C for private customers, B2B for a hotel or office",
    (S.CONFIGS, "Payment Method ID"): "PAY-CARD-EU",
    (S.CONFIGS, "Base Gross Price (incl. VAT)"): "2290 = the customer pays 2,290 incl. VAT; leave empty to use "
                                                 "the markup instead",
    (S.CONFIGS, "Price Currency"): "EUR (empty = currency of the market country)",
    (S.CONFIGS, "Markup (%)"): "60 = sell at production cost + 60 % (only used when no fixed price is given)",
    (S.CONFIGS, "Annual Volume (units)"): "120 tables per year",
    (S.CONFIGS, "Startup Stock (units)"): "10 = buy material for 10 tables before opening",
    (S.CONFIGS, "Sales Commission (%)"): "12 = a marketplace keeps 12 % of each sale",
    (S.CONFIGS, "Small-Business VAT Exemption"): "Yes = you are below the VAT threshold and sell only "
                                                 "domestically",
    (S.CONFIGS, "Notes"): NOTES_EX,

    (S.CONFIG_SERVICES, "Configuration ID"): "CFG-002",
    (S.CONFIG_SERVICES, "Service ID"): "SRV-SIZE",
    (S.CONFIG_SERVICES, "Quantity"): "1 = one custom size per table",
    (S.CONFIG_SERVICES, "Notes"): NOTES_EX,
}

YEAR_EXAMPLE = "95 = one unit costs 95 (in the row's currency) in this year; leave empty if unknown"
EXTRA_EXAMPLE = "A column you added yourself in Excel - kept as it is, not used in calculations"


def column_tip(sheet: str, column: str, col) -> str:
    """Tooltip for a table column header."""
    if col is not None and S.is_year_header(column) and S.SPECS[sheet].year_columns:
        what = f"Price per unit in {column}."
        ex = YEAR_EXAMPLE
    else:
        what = (col.help if col is not None and col.help else column)
        if not what.endswith("."):
            what += "."
        ex = COLUMN_EXAMPLES.get((sheet, column), EXTRA_EXAMPLE)
    if col is not None and col.required:
        what += " Required."
    return tip(column, what, ex)
