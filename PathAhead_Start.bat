@echo off
REM  PathAhead launcher (Windows). Self-heals if something is missing.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   PathAhead is not set up on this computer yet.
  echo   Please double-click  PathAhead_Install.bat  first.
  echo.
  pause
  exit /b 1
)

REM Self-heal: make sure dependencies and data are present and current.
call .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet >nul 2>nul

echo.
echo   Starting PathAhead...
echo   Your browser will open in a moment. Nothing you type leaves this computer.
echo   Close this window (or press Ctrl+C) to stop.
echo.
call .venv\Scripts\python.exe app\cli.py serve --port 8902
pause
