@echo off
title PARAGUASMJ - Configurar GitHub
color 0A

:: IR A LA CARPETA DEL PROYECTO (donde esta este .bat)
cd /d "%~dp0"

echo.
echo ================================================
echo    PARAGUASMJ - Configurar GitHub
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

:: Verificar Git instalado
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git no instalado.
    echo Descargar de: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK] Git encontrado
echo.

:: DATOS FIJOS
set USUARIO=zidmauricio-droid
set EMAIL=zidmauricio@gmail.com
set NOMBRE=Mauricio Jimenez

echo Configurando identidad...
git config --global user.name "%NOMBRE%"
git config --global user.email "%EMAIL%"
echo [OK] Identidad: %NOMBRE% - %EMAIL%
echo.

:: Inicializar repositorio SI NO EXISTE
if not exist ".git" (
    echo Inicializando repositorio...
    git init
    git branch -M main
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
        echo .env
        echo dist/
        echo build/
        echo *.spec
    ) > .gitignore
)

:: Agregar archivos
echo Agregando archivos del proyecto...
git add .
git commit -m "PARAGUASMJ - Version inicial"

:: Configurar remoto
git remote remove origin 2>nul
git remote add origin https://github.com/%USUARIO%/PARAGUASMJ.git

:: Subir
echo.
echo Subiendo a GitHub...
echo Usuario: %USUARIO%
echo.
echo IMPORTANTE: Cuando pida contrasena, pegue su TOKEN de GitHub
echo (no su contrasena normal — crear en: https://github.com/settings/tokens)
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo subir.
    echo Verifique: token correcto, repositorio existe, tiene internet.
) else (
    echo.
    echo ================================================
    echo    EXITO! Codigo en GitHub
    echo    https://github.com/%USUARIO%/PARAGUASMJ
    echo ================================================
)
pause
