@echo off
REM JakinsCraft Tile Splitter - one click Windows build.
REM Builds TileSplitter.exe from the Python source with PyInstaller.
REM Needs Python 3 installed with "Add python.exe to PATH" ticked.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found on this PC.
  echo Install it from https://www.python.org/downloads/ and tick
  echo "Add python.exe to PATH" during setup, then run this file again.
  pause
  exit /b 1
)

echo Installing build tools, first run only...
python -m pip install --upgrade pillow pyinstaller
if errorlevel 1 (
  echo pip install failed, check your internet connection and try again.
  pause
  exit /b 1
)

echo Building TileSplitter.exe ...
python -m PyInstaller --onefile --windowed --name TileSplitter tile_splitter.py
if errorlevel 1 (
  echo The build failed, see the messages above.
  pause
  exit /b 1
)

echo.
echo Done. Your app is here:
echo   %CD%\dist\TileSplitter.exe
echo Double click it to run. Keep the exe anywhere you like.
pause
