@echo off
title PARAGUASMJ - Limpiar git mal configurado
color 0C

echo.
echo ================================================
echo    LIMPIAR .git de carpeta personal
echo ================================================
echo.
echo Este script elimina el repositorio git que se
echo creo accidentalmente en C:\Users\%USERNAME%
echo (NO borra sus archivos personales)
echo.

:: Verificar que NO estamos en la carpeta del proyecto
if exist "app.py" (
    echo [ERROR] Parece que esta en la carpeta del PROYECTO.
    echo NO ejecute este script desde PARAGUASMJ.
    echo Solo ejecutelo desde C:\Users\%USERNAME%
    pause
    exit /b 1
)

:: Verificar que hay un .git aqui
if not exist ".git" (
    echo [OK] No hay repositorio .git en %CD%
    echo No hay nada que limpiar.
    pause
    exit /b 0
)

echo Carpeta actual: %CD%
echo.
echo Se eliminara la carpeta .git de: %CD%
echo Sus archivos personales NO seran borrados.
echo.
choice /C SN /N /M "Desea continuar? (S=Si / N=No): "
if errorlevel 2 (
    echo Cancelado.
    pause
    exit /b 0
)

echo Eliminando .git...
rmdir /s /q ".git"

if exist ".git" (
    echo [ERROR] No se pudo eliminar. Intente como Administrador.
) else (
    echo.
    echo [OK] Repositorio .git eliminado de la carpeta personal.
    echo Sus archivos personales estan intactos.
)

pause
