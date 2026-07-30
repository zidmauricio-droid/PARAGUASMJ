@echo off
title PARAGUASMJ — Actualizar programa
color 0A

echo.
echo  PARAGUASMJ - Buscando actualizaciones...
echo.

cd /d "%~dp0"

ping -n 1 github.com >nul
if errorlevel 1 (
    echo  Sin conexion a internet. Actualizacion fallida.
    echo.
    echo  Para actualizar manualmente:
    echo  1. Conecta el USB con la actualizacion
    echo  2. El programa se actualizara automaticamente
    pause
    exit /b 0
)

git pull origin main 2>nul

if errorlevel 1 (
    echo  No se pudo actualizar. Asegurate de tener Git instalado.
    echo.
    echo  Descargar Git: https://git-scm.com/download/win
) else (
    echo  OK Programa actualizado correctamente
    echo.
    echo  Reinicia PARAGUASMJ para aplicar los cambios.
)

pause
