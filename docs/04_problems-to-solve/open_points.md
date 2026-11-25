# Problems to solve / open points

1. **Verify starter tax data** with a local accountant: dividend tax in Bosnia and Herzegovina (FBiH vs. RS), Swiss canton-specific profit tax, social contributions of sole proprietors (all marked "verify" in the database notes).
2. **Progressive tax brackets** (e.g. Croatia 10 % / 18 % profit tax, Montenegro 9–15 %) are modelled as one flat effective rate per legal form.
3. **Windows executable** `publish/main.exe` must be built on a Windows PC with `publish/build_windows.bat` (PyInstaller cannot cross-compile from Linux/macOS).
4. **Exchange rates** are entered manually (sheet *Exchange Rates*) – no automatic online update.
5. Possible extensions: optional light theme switch (all colours are in `main/profit_planner/ui/theme.py`), app icon (`assets/01_media/01_icons/`), more countries / products, charts per year.
