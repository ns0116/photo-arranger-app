@echo off
echo ==================================================
echo Photo Arranger App Build Script (Windows)
echo ==================================================

:: Check if venv exists
if not exist "venv" (
    echo [Error] venv [Python virtual environment] not found in this folder.
    echo Please create the virtual environment and set up dependencies first.
    echo Example command: python -m venv venv
    pause
    exit /b 1
)

echo 1. Installing/updating dependencies (PyInstaller, pillow, Flask)...
call .\venv\Scripts\python.exe -m pip install pyinstaller pillow Flask

echo 2. Building standalone .exe...
:: In PyInstaller for Windows, use semicolon (;) as path separator for --add-data
call .\venv\Scripts\python.exe -m PyInstaller --onefile --windowed ^
  --icon="assets\icon.ico" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --name "PhotoArranger" ^
  app.py

echo ==================================================
echo Build completed successfully!
echo 'PhotoArranger.exe' has been generated in the 'dist' folder.
echo ==================================================
pause
