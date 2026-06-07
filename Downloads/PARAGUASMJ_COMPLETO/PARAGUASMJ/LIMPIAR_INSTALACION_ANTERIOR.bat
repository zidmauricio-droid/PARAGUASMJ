@echo off
chcp 65001 >nul
title PARAGUASMJ — Limpiar registros de instalaciones anteriores
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   PARAGUASMJ — Sistema para Acueductos Rurales      ║
echo  ║   Limpiador de registros de instalaciones previas   ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Este proceso elimina SOLAMENTE:
echo    [*] Documentos creados en instalaciones de prueba
echo    [*] PQRS, proyectos y registros de prueba
echo    [*] Archivos subidos durante las pruebas
echo    [*] PDFs generados durante las pruebas
echo    [*] Logs del sistema
echo.
echo  NO se elimina:
echo    [+] Usuarios del sistema
echo    [+] Configuracion institucional
echo    [+] Logo y firmas digitales
echo    [+] Tipos de documento configurados
echo    [+] Autorizadores y firmantes
echo.
set /p RESP="  Continuar? (S para confirmar, cualquier otra tecla para cancelar): "
if /i not "%RESP%"=="S" (
    echo.
    echo  Operacion cancelada. No se elimino nada.
    timeout /t 3 >nul
    exit /b 0
)

echo.
echo  Buscando Python...
set PYTHON=
python --version >nul 2>&1 && set PYTHON=python
if "%PYTHON%"=="" py --version >nul 2>&1 && set PYTHON=py
if "%PYTHON%"=="" (
    echo  [ERROR] Python no encontrado. Instale Python 3.8 o superior.
    pause & exit /b 1
)

echo  Ejecutando limpieza con %PYTHON%...
echo.
%PYTHON% "%~dp0limpiar_datos_prueba.py"
echo.
