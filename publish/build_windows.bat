@echo off
REM Builds publish\main.exe (needs Python 3.10+ from python.org). Runs all tests first.
cd /d "%~dp0\.."
python -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r docs\03_req-files\requirements-dev.txt || goto :error
set QT_QPA_PLATFORM=offscreen
python -m pytest tests -q -p no:cacheprovider || goto :error
set QT_QPA_PLATFORM=
pyinstaller --noconfirm --distpath publish --workpath .build-tmp publish\ProfitPlanner.spec || goto :error
rmdir /s /q .build-tmp
echo.
echo Done: publish\main.exe  - this single file can be sent to clients.
pause
exit /b 0
:error
echo BUILD FAILED
pause
exit /b 1
