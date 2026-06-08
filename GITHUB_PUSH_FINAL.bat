@echo off
title PARAGUASMJ - GitHub Sync
color 0A

:: IR A LA CARPETA DEL PROYECTO (donde esta este .bat)
cd /d "%~dp0"

echo.
echo ================================================
echo    PARAGUASMJ - GitHub Sync
echo    Carpeta: %CD%
echo ================================================
echo.

:: Verificar que estamos en la carpeta correcta
if not exist "app.py" (
    echo [ERROR] No se encontro app.py en esta carpeta.
    echo Asegurese de ejecutar este script desde la carpeta PARAGUASMJ.
    echo Carpeta actual: %CD%
    pause
    exit /b 1
)
echo [OK] Carpeta correcta: %CD%
echo.

:: Change to main branch
git checkout main 2>nul
if errorlevel 1 (
    echo Creando rama main desde origin...
    git fetch origin
    git checkout -b main origin/main 2>nul
    if errorlevel 1 (
        git checkout -b main 2>nul
    )
)

:: Add all changes
git add .

:: Commit changes (solo si hay algo nuevo)
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "PARAGUASMJ - Sync %date% %time%"
) else (
    echo Sin cambios nuevos.
)

:: Push to GitHub
echo.
echo Subiendo a GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo subir. Intentando sincronizar primero...
    git pull origin main --rebase
    git push -u origin main
    if errorlevel 1 (
        echo.
        echo [ERROR] Verifique su token de GitHub e internet.
    )
) else (
    echo.
    echo ================================================
    echo    EXITO! Codigo en GitHub
    echo    https://github.com/zidmauricio-droid/PARAGUASMJ
    echo ================================================
)

pause
