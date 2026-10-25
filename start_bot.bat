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
    echo [ERREUR] Python 3 est introuvable.
    pause
    exit /b 1
  )
  set "PYTHON=python"
) else (
  set "PYTHON=py -3"
)
if not exist "venv\Scripts\python.exe" (
  echo Creation de l'environnement virtuel...
  %PYTHON% -m venv venv
  if errorlevel 1 (
    echo [ERREUR] Impossible de creer venv.
    pause
    exit /b 1
  )
)
echo Installation / verification des dependances...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -e . -r requirements-dev.txt
if errorlevel 1 (
  echo [ERREUR] Installation des dependances echouee.
  pause
  exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul
venv\Scripts\python.exe panel.py
pause
