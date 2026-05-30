@echo off
:: ================================================================
::  PARAGUASMJ - INICIO RAPIDO
::  Doble clic para abrir el sistema
:: ================================================================
title PARAGUASMJ
cd /d "%~dp0"

:: Iniciar servidor en segundo plano
start "" /B python run.py

:: Esperar 3 segundos y abrir el navegador
timeout /t 3 /nobreak >nul
start http://localhost:5000

:: Mantener visible por si hay errores
:: (se cierra solo despues de 5 segundos si todo va bien)
timeout /t 5 /nobreak >nul
