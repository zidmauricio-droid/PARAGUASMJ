@echo off
chcp 65001 >nul
title PARAGUASMJ — Subir cambios a GitHub
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   PARAGUASMJ — Subir cambios a GitHub               ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Verificar que git está instalado
git --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Git no instalado. Descarga desde https://git-scm.com
    pause & exit /b 1
)

:: Pedir mensaje del commit
set /p MSG="  Descripcion del cambio (Enter para 'Actualización PARAGUASMJ'): "
if "%MSG%"=="" set MSG=Actualizacion PARAGUASMJ

echo.
echo  Preparando cambios...
git add .
git status --short

echo.
echo  Guardando commit: %MSG%
git commit -m "%MSG%"

echo.
echo  Subiendo a GitHub...
git push

if errorlevel 1 (
    echo.
    echo  [NOTA] Si es la primera vez, ejecuta primero:
    echo  git remote add origin https://github.com/TU_USUARIO/PARAGUASMJ.git
    echo  git push -u origin main
) else (
    echo.
    echo  Cambios subidos exitosamente a GitHub.
)

echo.
pause
