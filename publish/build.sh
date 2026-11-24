#!/usr/bin/env bash
# Builds publish/main (Linux / macOS). Runs all tests first.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docs/03_req-files/requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest tests -q -p no:cacheprovider
pyinstaller --noconfirm --distpath publish --workpath .build-tmp publish/ProfitPlanner.spec
rm -rf .build-tmp
echo "Done: publish/main"
