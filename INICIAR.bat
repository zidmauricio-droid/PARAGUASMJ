@echo off
:: ================================================================
::  PARAGUASMJ - INICIO RAPIDO
::  Doble clic para abrir el sistema
:: ================================================================
title PARAGUASMJ
cd /d "%~dp0"

:: Intentar py launcher primero (Windows), luego python
set PY_CMD=
py --version >nul 2>&1
if not errorlevel 1 (set PY_CMD=py)
if "%PY_CMD%"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 (set PY_CMD=python)
)
if "%PY_CMD%"=="" (
    echo [ERROR] Python no encontrado. Ejecute INSTALAR.bat primero.
    pause
    exit /b 1
)

:: Iniciar servidor en segundo plano
start "" /B %PY_CMD% run.py

:: Esperar a que el servidor este listo (hasta 20 intentos de 1s)
set /A intentos=0
:ESPERAR
timeout /t 1 /nobreak >nul
curl -s -o nul http://localhost:5000/ >nul 2>&1
if not errorlevel 1 goto :ABRIR
set /A intentos+=1
if %intentos% LSS 20 goto :ESPERAR

:ABRIR
start http://localhost:5000

:: Mantener abierto para ver errores si los hay
timeout /t 8 /nobreak >nul
