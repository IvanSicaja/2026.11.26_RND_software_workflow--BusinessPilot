# PyInstaller build specification -> single file publish/main.exe (Windows) / publish/main (macOS, Linux)
# Use publish/build_windows.bat or publish/build.sh - they run all tests first.
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(ROOT, "main", "main.py")],
    pathex=[os.path.join(ROOT, "main")],
    binaries=[],
    datas=[],
    hiddenimports=["openpyxl.cell._writer"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PySide6.QtWebEngineCore",
              "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml",
              "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="main",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
