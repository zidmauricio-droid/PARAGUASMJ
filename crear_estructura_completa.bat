@echo off
chcp 65001 >nul
title PARAGUASMJ - Crear Estructura de Carpetas
color 0A
cd /d "%~dp0"

echo.
echo =====================================================
echo   PARAGUASMJ - Crear Estructura Documental
echo   12 Módulos de Gestión Documental
echo =====================================================
echo.

if not exist "app.py" (
    echo [ERROR] No se encontró app.py. Ejecute desde la carpeta PARAGUASMJ.
    pause
    exit /b 1
)

python --version >nul 2>&1
if not errorlevel 1 (
    set PY=python
    goto :CREAR
)
py --version >nul 2>&1
if not errorlevel 1 (
    set PY=py
    goto :CREAR
)
echo [ERROR] Python no encontrado. Ejecute INSTALAR.bat primero.
pause
exit /b 1

:CREAR
echo Creando estructura de 12 módulos en uploads/...
echo.
%PY% -c "
import sys, os
sys.path.insert(0, os.getcwd())
from utils.file_manager import file_manager
ok, msg, creadas = file_manager.crear_estructura_completa()
if ok:
    print(f'  [OK] {msg}')
    for c in creadas[:20]:
        print(f'       + {c}')
    if len(creadas) > 20:
        print(f'       ... y {len(creadas)-20} más')
else:
    print(f'  [ERROR] {msg}')
    sys.exit(1)
"

if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo crear la estructura.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   Estructura creada exitosamente
echo =====================================================
echo.
pause
