@echo off
title CEOS v5
cd /d "%~dp0"

echo.
echo CEOS v5 - Motor CRONOS-Espiral
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta en el PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt -q

if not exist "data" mkdir data
for %%D in (identity memory grammar library mentor codex user uploads chat long_memory coaching) do (
    if not exist "data\%%D" mkdir "data\%%D"
)

echo.
echo Abriendo CEOS en el navegador...
echo Deja esta ventana abierta. Ctrl+C para salir.
echo.

start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"
python run.py
pause
