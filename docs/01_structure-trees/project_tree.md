# Project tree

Complete file tree of Profit Planner (generated). Explanations: see `directory_structure_explained.md` in the project root.

```
ProfitPlanner/
├── assets/
│   ├── 01_media/
│   │   ├── 01_icons/
│   │   ├── 02_figures/
│   │   ├── 03_sounds/
│   │   ├── 04_videos/
│   │   └── 05_ads/
│   └── 02_3d-modeling/
├── bills/
├── copyright/
│   └── third_party_licenses.md
├── data/
│   ├── processed/
│   └── raw/
│       └── ProfitPlanner_Database.xlsx
├── docs/
│   ├── 01_structure-trees/
│   │   └── project_tree.md
│   ├── 02_cores-docs-and-comparison-tables/
│   │   ├── calculation_model.md
│   │   └── legal_forms_and_countries_comparison.md
│   ├── 03_req-files/
│   │   └── requirements-dev.txt
│   └── 04_problems-to-solve/
│       └── open_points.md
├── main/
│   ├── profit_planner/
│   │   ├── ui/
│   │   │   ├── __init__.py
│   │   │   ├── controller.py
│   │   │   ├── dialogs.py
│   │   │   ├── explorer_view.py
│   │   │   ├── main_window.py
│   │   │   ├── results_view.py
│   │   │   ├── table_editor.py
│   │   │   ├── table_model.py
│   │   │   └── widgets.py
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── calc.py
│   │   ├── database.py
│   │   ├── excel_io.py
│   │   ├── reports.py
│   │   ├── schema.py
│   │   ├── seed.py
│   │   └── storage.py
│   └── main.py
├── models/
│   ├── 01_downloaded/
│   └── 02_trained/
├── notebooks/
├── publish/
│   ├── build.sh
│   ├── build_windows.bat
│   ├── ProfitPlanner.spec
│   └── run_windows.bat
├── tests/
│   ├── conftest.py
│   ├── test_calc.py
│   ├── test_database.py
│   ├── test_gui.py
│   └── test_storage.py
├── viz/
│   ├── 01_mind-maps/
│   └── 02_tableau/
├── .gitignore
├── directory_structure_explained.md
├── README.md
└── requirements.txt
```

## Source-code architecture

```
main/main.py
   └─ profit_planner.app            start, style, opens a window per database
        ├─ storage.SafeStore        working copy -> verify -> Excel file, backups, conflicts
        │    └─ excel_io            read / write the workbook  (schema = sheet definitions)
        ├─ database.Database        tables in memory, type conversion, validation
        ├─ calc.Engine              price breakdown and net profit per configuration
        └─ ui/                      main_window, table_editor + table_model (editing),
                                    results_view (Results tab), explorer_view (Where to found?),
                                    controller (autosave, Excel change detection), dialogs
```
