@echo off
title PARAGUASMJ - Actualizacion Segura
color 0A
chcp 65001 >nul 2>nul

cd /d "%~dp0"

echo.
echo ========================================================================
echo    PARAGUASMJ - ACTUALIZACION SEGURA
echo    Asociacion de Suscriptores del Acueducto Comunitario El Puente
echo    Villeta, Cundinamarca
echo ========================================================================
echo.

:: ── 1. Verificar carpeta correcta ───────────────────────────────────────
if not exist "app.py" (
    echo [ERROR] No se encuentra el sistema PARAGUASMJ en esta carpeta.
    echo.
    echo Verifica que este script este dentro de la carpeta de instalacion,
    echo por ejemplo: C:\PARAGUASMJ\ACTUALIZAR_CLIENTE.bat
    echo.
    pause
    exit /b 1
)

:: ── 2. Verificar git ─────────────────────────────────────────────────────
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git no esta instalado.
    echo.
    echo Descarga e instala Git desde: https://git-scm.com/download/win
    echo Luego vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

:: ── 3. Verificar conexion a internet ─────────────────────────────────────
ping -n 1 github.com >nul 2>nul
if errorlevel 1 (
    echo [SIN INTERNET] No hay conexion disponible.
    echo.
    echo El sistema seguira funcionando con la version actual.
    echo Vuelve a intentar cuando tengas internet.
    echo.
    pause
    exit /b 0
)

:: ── 4. Verificar repositorio git ─────────────────────────────────────────
git remote -v >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Esta carpeta no esta conectada al repositorio oficial.
    echo.
    echo Por favor, comunicate con el administrador del sistema.
    echo.
    pause
    exit /b 1
)

echo Descargando actualizaciones desde GitHub...
echo (Esto puede tardar unos segundos)
echo.

:: ── 5. Guardar configuracion local del usuario ───────────────────────────
git stash push -m "backup_config_local_%date%" >nul 2>nul

:: ── 6. Descargar e instalar actualizacion (SOLO LECTURA) ─────────────────
git fetch origin main
if errorlevel 1 (
    echo [ERROR] No se pudo descargar la actualizacion.
    echo Verifica tu conexion a internet e intenta nuevamente.
    git stash pop >nul 2>nul
    pause
    exit /b 1
)

git reset --hard origin/main
git clean -fd >nul 2>nul

:: ── 7. Restaurar configuracion local ────────────────────────────────────
git stash pop >nul 2>nul

:: ── 8. Verificar que el sistema sigue funcionando ────────────────────────
if not exist "app.py" (
    echo [ERROR CRITICO] La actualizacion produjo un error.
    echo Por favor, comunicate con el administrador tecnico.
    pause
    exit /b 1
)

:: ── 9. Mostrar version instalada ─────────────────────────────────────────
for /f "delims=" %%V in ('git log -1 --format^="%h %ad %s" --date^=short 2^>nul') do set VERSION=%%V
echo.
echo ========================================================================
echo    ACTUALIZACION COMPLETADA
echo.
echo    Version instalada: %VERSION%
echo    Repositorio:       https://github.com/zidmauricio-droid/PARAGUASMJ
echo ========================================================================
echo.
echo    IMPORTANTE: Reinicia PARAGUASMJ para aplicar los cambios.
echo.

:: ── 10. Ofrecer reinicio ─────────────────────────────────────────────────
choice /C SN /M "Deseas iniciar PARAGUASMJ ahora?" 2>nul
if errorlevel 2 (
    echo.
    echo Recuerda reiniciar el sistema manualmente para aplicar los cambios.
    pause
    exit /b 0
)
if errorlevel 1 (
    echo.
    echo Iniciando PARAGUASMJ...
    start "" python app.py
    exit /b 0
)

pause
