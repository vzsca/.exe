@echo off
setlocal
cd /d "%~dp0"
echo ================================
echo       .exe Launcher
echo ================================
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python 3 was not found.
    pause
    exit /b 1
  )
  set "PYTHON=python"
) else (
  set "PYTHON=py -3"
)
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PYTHON% -m venv venv
  if errorlevel 1 (
    echo [ERROR] Could not create the virtual environment.
    pause
    exit /b 1
  )
)
echo Installing / checking dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  pause
  exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul
venv\Scripts\python.exe panel.py
pause
