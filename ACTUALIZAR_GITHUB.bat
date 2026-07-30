@echo off
title PARAGUASMJ - Actualizar GitHub
color 0A

cd /d "%~dp0"

echo.
echo ================================================
echo    PARAGUASMJ - Actualizar GitHub
echo    Carpeta: %CD%
echo ================================================
echo.

:: ── 1. Verificar carpeta correcta ───────────────────────────────────
if not exist "app.py" (
    echo [ERROR] No se encontro app.py
    echo Ejecute este script desde la carpeta PARAGUASMJ
    pause
    exit /b 1
)

:: ── 2. Verificar git ─────────────────────────────────────────────────
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git no esta instalado.
    echo Descargalo en: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: ── 3. Verificar GitHub CLI ──────────────────────────────────────────
where gh >nul 2>nul
if errorlevel 1 (
    echo [ERROR] GitHub CLI no instalado.
    echo.
    echo Instalalo UNA SOLA VEZ:
    echo   Opcion A - PowerShell como admin:
    echo     winget install --id GitHub.cli
    echo   Opcion B - Descarga manual:
    echo     https://cli.github.com/
    echo.
    echo Luego ejecutar UNA SOLA VEZ: gh auth login
    echo.
    pause
    exit /b 1
)

:: ── 4. Verificar autenticacion ───────────────────────────────────────
gh auth status >nul 2>nul
if errorlevel 1 (
    echo [AVISO] No autenticado en GitHub.
    echo.
    echo Ejecuta UNA SOLA VEZ:
    echo   gh auth login
    echo.
    echo Sigue los pasos:
    echo   - GitHub.com
    echo   - HTTPS
    echo   - Login with a web browser
    echo   - Autoriza en el navegador
    echo.
    pause
    exit /b 1
)

:: ── 5. Detectar branch activo ────────────────────────────────────────
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%B
if "%BRANCH%"=="" set BRANCH=main
echo Branch actual: %BRANCH%
echo.

:: ── 6. Asegurarse de que el remote usa HTTPS (no SSH) ───────────────
for /f "delims=" %%U in ('git remote get-url origin 2^>nul') do set REMOTE_URL=%%U
echo Remote: %REMOTE_URL%

:: Si la URL es SSH, convertir a HTTPS
echo %REMOTE_URL% | findstr /C:"git@github.com" >nul
if not errorlevel 1 (
    echo [INFO] Convirtiendo SSH a HTTPS para compatibilidad con gh...
    for /f "tokens=2 delims=:" %%P in ('echo %REMOTE_URL%') do (
        set HTTPS_URL=https://github.com/%%P
    )
    git remote set-url origin !HTTPS_URL!
    echo Remote actualizado a HTTPS.
)
echo.

:: ── 7. Agregar todos los cambios ─────────────────────────────────────
echo Detectando cambios...
git add .

:: ── 8. Verificar si hay cambios para commitear ───────────────────────
git diff --cached --quiet
if not errorlevel 1 (
    echo Sin cambios nuevos para subir.
    echo.
    echo El repositorio ya esta actualizado.
    echo https://github.com/zidmauricio-droid/PARAGUASMJ
    echo.
    pause
    exit /b 0
)

:: Mostrar resumen de cambios
echo.
echo Archivos con cambios:
git diff --cached --name-only
echo.

:: ── 9. Crear commit con timestamp ────────────────────────────────────
set FECHA=%date:~6,4%-%date:~3,2%-%date:~0,2%
set HORA=%time:~0,2%:%time:~3,2%
:: Quitar espacio si la hora tiene un digito
set HORA=%HORA: =0%

git commit -m "PARAGUASMJ actualizacion %FECHA% %HORA%"
if errorlevel 1 (
    echo [ERROR] No se pudo crear el commit.
    pause
    exit /b 1
)
echo Commit creado correctamente.
echo.

:: ── 10. Push con gh como credential helper ───────────────────────────
echo Subiendo cambios a GitHub...
git push origin %BRANCH%

if errorlevel 1 (
    echo.
    echo [AVISO] Error en push directo. Intentando sincronizar primero...
    git pull origin %BRANCH% --rebase --autostash
    if errorlevel 1 (
        echo [ERROR] Conflicto al sincronizar. Revisa manualmente:
        echo   git status
        echo   git log --oneline -5
        pause
        exit /b 1
    )
    git push origin %BRANCH%
    if errorlevel 1 (
        echo.
        echo [ERROR] Push fallido. Verifica:
        echo   1. Conexion a internet
        echo   2. gh auth status
        echo   3. Permisos en el repositorio
        pause
        exit /b 1
    )
)

:: ── 11. Confirmar exito ──────────────────────────────────────────────
echo.
echo ================================================
echo  OK - Codigo actualizado en GitHub exitosamente
echo.
echo  Branch: %BRANCH%
echo  URL:    https://github.com/zidmauricio-droid/PARAGUASMJ
echo ================================================
echo.

:: Abrir en navegador (opcional - comentar si no se desea)
:: start https://github.com/zidmauricio-droid/PARAGUASMJ

pause
