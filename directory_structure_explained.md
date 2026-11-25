# Directory structure explained

Which file can be found in which folder of **Profit Planner**.

```
ProfitPlanner/
│
├── assets/                        # Additional project resources (non-code)
│   ├── 01_media/
│   │   ├── 01_icons/              # Icons (UI, documentation, branding) – empty for now
│   │   ├── 02_figures/            # Diagrams, charts, illustrations – empty for now
│   │   ├── 03_sounds/             # Audio assets – not used
│   │   ├── 04_videos/             # Demo videos, screen recordings – empty for now
│   │   └── 05_ads/                # Marketing visuals, thumbnails, banners – empty for now
│   └── 02_3d-modeling/            # 3D objects / CAD files – empty for now
│
├── bills/                         # Invoices, receipts, subscriptions for this project – empty for now
│
├── copyright/
│   └── third_party_licenses.md    # Licenses of PySide6, openpyxl, PyInstaller, pytest
│
├── data/
│   ├── raw/
│   │   └── ProfitPlanner_Database.xlsx   # Starter Excel database (all sheets: products, materials,
│   │                                     # services, tools, countries, legal forms, shipping, customs,
│   │                                     # payment, exchange rates, configurations)
│   └── processed/                 # Cleaned / exported datasets – empty for now
│
├── docs/
│   ├── 01_structure-trees/
│   │   └── project_tree.md        # Full file tree of the project and source-code architecture
│   ├── 02_cores-docs-and-comparison-tables/
│   │   ├── calculation_model.md                      # Formula: gross price -> net to owner, startup cash
│   │   └── legal_forms_and_countries_comparison.md   # Legal forms and countries side by side
│   ├── 03_req-files/
│   │   └── requirements-dev.txt   # Test + build dependencies (pytest, pytest-qt, PyInstaller)
│   └── 04_problems-to-solve/
│       └── open_points.md         # Open points and planned improvements
│
├── main/                          # Main source code (production-ready)
│   ├── main.py                    # Project entry point:  python main/main.py
│   └── profit_planner/            # Application package
│       ├── schema.py              # Definition of every Excel sheet and column
│       ├── database.py            # In-memory database, type conversion, validation
│       ├── seed.py                # Starter data for a new database
│       ├── excel_io.py            # Reading / writing the Excel workbook
│       ├── storage.py             # Crash-safe saving (working copy, verification, backups, conflicts)
│       ├── calc.py                # Calculation engine (costs, VAT, fees, customs, taxes, net profit)
│       ├── reports.py             # Export of results to a separate Excel report
│       ├── app.py                 # Application start, style, window handling
│       └── ui/                    # User interface (PySide6): main window, tables, results,
│                                  # "Where to found?" comparison, dialogs
│           ├── theme.py           # Dark theme: every colour of the interface in one place
│           └── help_texts.py      # Hover explanations with real examples for every element
│
├── models/                        # ML / AI models – not used in this project
│   ├── 01_downloaded/
│   └── 02_trained/
│
├── notebooks/                     # Jupyter notebooks – empty for now
│
├── publish/                       # Final deliverables
│   ├── main.exe                   # Executable release – created by build_windows.bat (on Windows)
│   ├── build_windows.bat          # Runs all tests, then builds main.exe
│   ├── build.sh                   # Same for macOS / Linux (creates publish/main)
│   ├── run_windows.bat            # Starts the app from source on Windows
│   └── ProfitPlanner.spec         # PyInstaller build specification
│
├── tests/                         # 130 automated tests
│   ├── conftest.py                # Test setup (small hand-calculable database)
│   ├── test_calc.py               # Calculation results line by line
│   ├── test_database.py           # Validation, input parsing, fuzzing
│   ├── test_storage.py            # Save safety: power loss, locked/corrupt files, conflicts, Excel edits
│   ├── test_gui.py                # End-to-end tests of the user interface
│   └── test_help_and_theme.py     # Every element has a tooltip with an example; dark theme contrast
│
├── viz/                           # Visualization outputs – empty for now
│   ├── 01_mind-maps/
│   └── 02_tableau/
│
├── .gitignore                     # Ignored files (virtual env, build output, app working copies, backups)
├── requirements.txt               # Python dependencies to run the app (PySide6, openpyxl)
├── directory_structure_explained.md   # This file
└── README.md                      # Project overview, quick start, features, data safety
```

Empty folders contain a `.gitkeep` file so that Git keeps them.

Files created while the app runs (not part of the repository): next to the database the app creates `.profitplanner/` (verified working copy) and `Backups/` (earlier versions of the Excel file).
