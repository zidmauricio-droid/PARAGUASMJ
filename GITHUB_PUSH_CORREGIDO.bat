@echo off
title PARAGUASMJ - Push Corregido
color 0A

echo.
echo ================================================
echo    PARAGUASMJ - Push Corregido
echo ================================================
echo.

:: Verificar rama actual
git branch > temp_rama.txt
find "main" temp_rama.txt >nul
if errorlevel 1 (
    echo No estas en la rama main.
    echo Cambiando a main...
    git checkout main 2>nul
    if errorlevel 1 (
        echo Creando rama main desde origin...
        git fetch origin
        git checkout -b main origin/main
    )
)
del temp_rama.txt 2>nul

:: Agregar cambios
git add .

:: Commitear solo si hay cambios
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "PARAGUASMJ - Actualizacion %date%"
) else (
    echo Sin cambios nuevos para commitear.
)

:: Subir
echo.
echo Subiendo a GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo subir.
    echo.
    echo Ejecuta estos comandos manualmente:
    echo   git fetch origin
    echo   git checkout -B main origin/main
    echo   git push -u origin main
) else (
    echo.
    echo ================================================
    echo    EXITO! Codigo en GitHub
    echo    https://github.com/zidmauricio-droid/PARAGUASMJ
    echo ================================================
)

pause
