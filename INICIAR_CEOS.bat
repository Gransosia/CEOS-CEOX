@echo off
title CEOS v5 - Motor CRONOS-Espiral
color 0B
cd /d "%~dp0"

echo.
echo  ========================================================
echo    CEOS v5  -  Motor CRONOS-Espiral
echo  ========================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no esta en el PATH.
    echo  Instala desde https://www.python.org/downloads/
    echo  Marca "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo  Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
echo  Instalando/actualizando dependencias...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo  [ERROR] Fallo al instalar dependencias.
    pause
    exit /b 1
)

if not exist "data" mkdir data
for %%D in (identity memory grammar library mentor codex user uploads chat long_memory coaching) do (
    if not exist "data\%%D" mkdir "data\%%D"
)

echo.
echo  Arrancando servidor...
echo  Se abrira el navegador en unos segundos.
echo  Deja esta ventana ABIERTA mientras uses CEOS.
echo  Ctrl+C para detener.
echo.

start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

python run.py

echo.
echo  Servidor detenido.
pause
