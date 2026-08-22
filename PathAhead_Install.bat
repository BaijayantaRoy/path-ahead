@echo off
REM ===================================================================
REM  PathAhead installer (Windows)
REM
REM  This takes about three minutes and downloads roughly 40 KB.
REM  There is no AI model to download, because PathAhead does not need
REM  one to work.
REM ===================================================================
setlocal
cd /d "%~dp0"

echo.
echo   PathAhead - setting up
echo   ---------------------------------------------------------------
echo.

REM --- 1. Is Python here? --------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
  echo   Python was not found on this computer.
  echo.
  echo   PathAhead needs Python 3.10 or newer. It is free.
  echo     1. Go to  https://www.python.org/downloads/
  echo     2. Download and run the installer
  echo     3. IMPORTANT: tick "Add python.exe to PATH" on the first screen
  echo     4. When it finishes, run this installer again
  echo.
  pause
  exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   Found Python %PYVER%
python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)"
if errorlevel 1 (
  echo.
  echo   That version is too old. PathAhead needs Python 3.10 or newer.
  echo   Please install a newer version from https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

REM --- 2. Private folder for the dependencies ------------------------
echo   Creating a private folder for PathAhead's dependencies...
python -m venv .venv
if errorlevel 1 (
  echo   Could not create the folder. Check you have write permission here.
  pause
  exit /b 1
)

echo   Installing dependencies (small - about 40 KB)...
call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
  echo   Something went wrong installing dependencies.
  echo   If you are behind a company network, that may be blocking it.
  pause
  exit /b 1
)

REM --- 3. Prepare the data -------------------------------------------
echo   Preparing the education data...
call .venv\Scripts\python.exe app\cli.py build --out web\data
if errorlevel 1 (
  echo   The data pack failed its own checks and was not installed.
  echo   Please report this - it is a bug, not something you did.
  pause
  exit /b 1
)

echo.
echo   ---------------------------------------------------------------
echo   Done. Now double-click  PathAhead_Start.bat  to open PathAhead.
echo.
echo   Nothing you type into PathAhead ever leaves this computer.
echo   ---------------------------------------------------------------
echo.
pause
