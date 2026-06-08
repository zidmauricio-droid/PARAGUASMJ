@echo off
title PARAGUASMJ - Subir Cambios [SOLO DESARROLLADOR]
color 0E
chcp 65001 >nul 2>nul

cd /d "%~dp0"

echo.
echo ========================================================================
echo    PARAGUASMJ - SUBIR CAMBIOS AL REPOSITORIO
echo    [SOLO PARA EL DESARROLLADOR AUTORIZADO]
echo ========================================================================
echo.

:: ── 1. Verificar carpeta correcta ───────────────────────────────────────
if not exist "app.py" (
    echo [ERROR] No se encontro app.py. Ejecuta desde la carpeta PARAGUASMJ.
    pause
    exit /b 1
)

:: ── 2. Verificar git y gh CLI ───────────────────────────────────────────
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git no instalado. Descarga en: https://git-scm.com/download/win
    pause
    exit /b 1
)

where gh >nul 2>nul
if errorlevel 1 (
    echo [ERROR] GitHub CLI no instalado.
    echo.
    echo Instala con PowerShell (como admin):
    echo   winget install --id GitHub.cli
    echo.
    echo Luego autentica UNA SOLA VEZ con: gh auth login
    pause
    exit /b 1
)

:: ── 3. Verificar autenticacion GitHub ──────────────────────────────────
gh auth status >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No autenticado en GitHub.
    echo.
    echo Ejecuta UNA SOLA VEZ: gh auth login
    echo   - Selecciona: GitHub.com
    echo   - Protocolo: HTTPS
    echo   - Autenticacion: Login with a web browser
    echo.
    pause
    exit /b 1
)

:: ── 4. Mostrar usuario autenticado ──────────────────────────────────────
for /f "tokens=*" %%U in ('gh api user --jq .login 2^>nul') do set GH_USER=%%U
echo Usuario GitHub: %GH_USER%

:: ── 5. Detectar branch activo ───────────────────────────────────────────
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%B
if "%BRANCH%"=="" set BRANCH=main
echo Branch activo : %BRANCH%
echo.

:: ── 6. Mostrar estado actual ─────────────────────────────────────────────
echo Estado del repositorio:
git status --short
echo.

:: ── 7. Agregar cambios y verificar ──────────────────────────────────────
git add .
git diff --cached --quiet
if not errorlevel 1 (
    echo Sin cambios nuevos para subir.
    echo El repositorio esta actualizado.
    pause
    exit /b 0
)

:: ── 8. Resumen de cambios ────────────────────────────────────────────────
echo Archivos a commitear:
git diff --cached --name-only
echo.

:: ── 9. Solicitar mensaje de commit ──────────────────────────────────────
set /p MSG="Mensaje del commit (Enter para timestamp automatico): "
if "%MSG%"=="" (
    set FECHA=%date:~6,4%-%date:~3,2%-%date:~0,2%
    set HORA=%time:~0,2%:%time:~3,2%
    set HORA=%HORA: =0%
    set MSG=PARAGUASMJ actualizacion %FECHA% %HORA%
)

git commit -m "%MSG%"
if errorlevel 1 (
    echo [ERROR] No se pudo crear el commit.
    pause
    exit /b 1
)
echo Commit creado.
echo.

:: ── 10. Push ────────────────────────────────────────────────────────────
echo Subiendo a GitHub (branch: %BRANCH%)...
git push origin %BRANCH%

if errorlevel 1 (
    echo.
    echo Sincronizando primero (rebase)...
    git pull origin %BRANCH% --rebase --autostash
    git push origin %BRANCH%
    if errorlevel 1 (
        echo.
        echo [ERROR] Push fallido. Verifica permisos en:
        echo   https://github.com/zidmauricio-droid/PARAGUASMJ/settings
        pause
        exit /b 1
    )
)

echo.
echo ========================================================================
echo    OK - Cambios subidos correctamente
echo    Branch: %BRANCH%
echo    URL:    https://github.com/zidmauricio-droid/PARAGUASMJ
echo ========================================================================
echo.
pause
