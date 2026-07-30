@echo off
title PARAGUASMJ - Actualizar GitHub
color 0A

:: IR A LA CARPETA DEL PROYECTO (donde esta este .bat)
cd /d "%~dp0"

echo.
echo ================================================
echo    PARAGUASMJ - Actualizar GitHub
echo    Carpeta: %CD%
echo ================================================
echo.

:: Verificar carpeta correcta
if not exist "app.py" (
    echo [ERROR] No se encontro app.py.
    echo Ejecute este script desde la carpeta PARAGUASMJ.
    pause
    exit /b 1
)

:: Datos fijos
set USUARIO=zidmauricio-droid

:: Agregar cambios
git add .

:: Commitear solo si hay cambios
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Actualizacion automatica %date%"
) else (
    echo Sin cambios nuevos para subir.
    pause
    exit /b 0
)

:: Subir
git push origin main

if errorlevel 1 (
    echo.
    echo Error al subir. Sincronizando primero...
    git pull origin main --rebase
    git push origin main
)

echo.
echo OK - Codigo actualizado
echo https://github.com/%USUARIO%/PARAGUASMJ
pause
