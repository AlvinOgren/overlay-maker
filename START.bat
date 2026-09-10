@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python bootstrap.py
) else (
  py -3 bootstrap.py
)
if errorlevel 1 (
  echo.
  echo Installera Python 3.10 eller senare om det saknas. Se README.md.
  pause
)
