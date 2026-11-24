"""Profit Planner - project entry point.

Start:  python main/main.py [path/to/database.xlsx]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make the profit_planner package importable

from profit_planner.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
