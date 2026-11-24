@echo off
REM Start Profit Planner from source (first start installs the requirements)
cd /d "%~dp0\.."
if not exist .venv ( python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt )
start "" .venv\Scripts\pythonw.exe main\main.py %*
