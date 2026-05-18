@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

py -3.13 -c "import sys" >nul 2>nul
if %errorlevel%==0 set "PYTHON_CMD=py -3.13"

if not defined PYTHON_CMD (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
  if %errorlevel%==0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
  if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo No encuentro Python 3.9 o superior.
  echo Ejecuta primero instalar_requisitos.bat o instala Python 3 desde:
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)

%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install --upgrade -r requirements.txt
%PYTHON_CMD% app.py

pause
