@echo off
title PARAGUASMJ - Configurar GitHub
color 0A
echo.
echo ================================================
echo    PARAGUASMJ - Configurar GitHub
echo ================================================
echo.
:: Verificar Git
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git no instalado
    echo Descargar de: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK] Git encontrado
echo.
:: DATOS FIJOS (tus datos)
set USUARIO=zidmauricio-droid
set EMAIL=zidmauricio@gmail.com
set NOMBRE=Mauricio Jimenez
echo Configurando identidad...
git config --global user.name "%NOMBRE%"
git config --global user.email "%EMAIL%"
echo [OK] Identidad configurada
echo.
:: Inicializar repositorio
if not exist ".git" (
    echo Inicializando repositorio...
    git init
)
:: Crear .gitignore
if not exist ".gitignore" (
    echo Creando .gitignore...
    (
        echo __pycache__/
        echo *.pyc
        echo *.db
        echo *.sqlite
        echo database/*.db
        echo logs/*.log
        echo backups/
        echo *.key
    ) > .gitignore
)
:: Agregar archivos
echo Agregando archivos...
git add .
git commit -m "PARAGUASMJ - Version inicial"
:: Agregar remoto
git remote remove origin 2>nul
git remote add origin https://github.com/%USUARIO%/PARAGUASMJ.git
:: Subir
echo.
echo Subiendo a GitHub...
echo Usuario: %USUARIO%
echo Repositorio: PARAGUASMJ
echo.
echo IMPORTANTE: Usa un TOKEN como contrasena
echo Crear token en: https://github.com/settings/tokens
echo Marcar: repo (todos)
echo.
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo subir
    echo.
    echo Verifica:
    echo 1. El repositorio existe en GitHub
    echo 2. Usas token (no contrasena)
    echo 3. Tienes internet
) else (
    echo.
    echo ================================================
    echo    EXITO! Codigo en GitHub
    echo    https://github.com/%USUARIO%/PARAGUASMJ
    echo ================================================
)
pause
