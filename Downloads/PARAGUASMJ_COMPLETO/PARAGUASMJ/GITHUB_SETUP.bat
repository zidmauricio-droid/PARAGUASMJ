@echo off
chcp 65001 >nul
title PARAGUASMJ — Configurar GitHub por primera vez
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   PARAGUASMJ — Configuracion inicial de GitHub      ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  REQUISITOS PREVIOS:
echo  1. Tener cuenta en https://github.com (gratuita)
echo  2. Crear repositorio llamado PARAGUASMJ en GitHub
echo  3. NO marcar "Initialize this repository"
echo.

set /p USUARIO="  Tu usuario de GitHub: "
if "%USUARIO%"=="" (echo  Cancelado. & pause & exit /b 0)

set /p NOMBRE="  Tu nombre completo: "
set /p EMAIL="  Tu email de GitHub: "

echo.
echo  Configurando identidad...
git config --global user.name "%NOMBRE%"
git config --global user.email "%EMAIL%"

echo  Conectando con GitHub...
git remote add origin https://github.com/%USUARIO%/PARAGUASMJ.git 2>nul
git remote set-url origin https://github.com/%USUARIO%/PARAGUASMJ.git

echo  Subiendo codigo...
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo  [ERROR] Verifica:
    echo  - El repositorio PARAGUASMJ existe en tu GitHub
    echo  - Tu usuario y contrasena son correctos
    echo  - Puede que necesites un Personal Access Token en lugar de contrasena
    echo    Ver: https://github.com/settings/tokens
) else (
    echo.
    echo  Repositorio configurado exitosamente.
    echo  URL: https://github.com/%USUARIO%/PARAGUASMJ
)

pause
