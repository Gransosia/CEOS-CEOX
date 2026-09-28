@echo off
title CEOS v10.0 - Auditoria
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python no esta disponible en PATH.
  pause
  exit /b 1
)
python tools\audit.py
if errorlevel 1 (
  echo.
  echo LA AUDITORIA HA DETECTADO PROBLEMAS.
  pause
  exit /b 1
)
echo.
echo AUDITORIA CEOS v10.0 COMPLETADA CORRECTAMENTE.
pause
