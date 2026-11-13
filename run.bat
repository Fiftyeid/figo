@echo off
chcp 65001 >nul
title Midad - KDP Coloring Studio
cd /d "%~dp0"
if not exist ".venv" (
  echo Creating virtual environment...
  py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo.
  echo Failed to install requirements. Check your internet connection.
  pause
  exit /b 1
)
python midad.py
pause
