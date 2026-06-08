@echo off
title PARAGUASMJ — Actualizar GitHub (Rapido)
color 0A

echo.
echo  Actualizando codigo en GitHub...
echo.

cd /d "%~dp0"

git add .
git commit -m "Actualizacion %date% %time%"
git push origin main

if errorlevel 1 (
    echo.
    echo  Error al subir. Intentando sincronizar primero...
    git pull origin main --rebase
    git push origin main
)

echo.
echo  OK Codigo actualizado: https://github.com/zidmauricio-droid/PARAGUASMJ
echo.

pause
