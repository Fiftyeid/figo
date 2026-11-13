@echo off
chcp 65001 >nul
title Midad - KDP Coloring Studio
cd /d "%~dp0"

echo.
echo   ============================================
echo     Midad  ^|  KDP Coloring Book Studio
echo   ============================================
echo.

REM --- البحث عن Python ---
set PY=
py -3 --version >nul 2>&1 && set PY=py -3
if not defined PY ( python --version >nul 2>&1 && set PY=python )
if not defined PY (
  echo   [X] Python not found.
  echo       Install Python 3.10+ from https://www.python.org/downloads/
  echo       IMPORTANT: tick "Add Python to PATH" during installation.
  echo.
  pause
  exit /b 1
)

REM --- إنشاء البيئة الافتراضية ---
if not exist ".venv\Scripts\python.exe" (
  echo   [1/3] Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo   [X] Failed to create venv.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat"

REM --- تثبيت المتطلبات (من مجلد wheels إن وُجد = بدون إنترنت) ---
if exist "wheels" (
  echo   [2/3] Installing requirements from local wheels ^(offline^)...
  python -m pip install --quiet --disable-pip-version-check --no-index --find-links wheels -r requirements.txt
  if errorlevel 1 (
    echo         Local wheels incomplete for this Python version - switching to internet...
    python -m pip install --quiet --disable-pip-version-check -r requirements.txt
  )
) else (
  echo   [2/3] Installing requirements ^(needs internet once^)...
  python -m pip install --quiet --disable-pip-version-check -r requirements.txt
)
if errorlevel 1 (
  echo.
  echo   [X] Could not install requirements. Check your internet connection.
  echo.
  pause
  exit /b 1
)

echo   [3/3] Starting Midad...
echo.
python midad.py %*
echo.
pause
