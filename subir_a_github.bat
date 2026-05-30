@echo off
title Subir PARAGUASMJ a GitHub
echo ====================================================
echo  Subiendo el codigo de PARAGUASMJ a GitHub
echo ====================================================
echo.

:: Cambiar a la carpeta del proyecto
cd /d "C:\Users\Admin\Pictures\PARAGUASMJ_v10\PARAGUASMJ"
if errorlevel 1 (
    echo ERROR: No se encuentra la carpeta del proyecto.
    pause
    exit /b
)

:: Verificar que Git esta instalado
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git no esta instalado o no esta en el PATH.
    echo Descargue Git desde https://git-scm.com/download/win
    pause
    exit /b
)

:: Configurar nombre y correo (solo la primera vez, pero lo repetimos)
git config --global user.name "Mauricio Jimenez"
git config --global user.email "zidmarucio@gmail.com"

:: Inicializar repositorio local si no existe
if not exist ".git" (
    echo Inicializando repositorio local...
    git init
)

:: Agregar todos los archivos
echo Agregando archivos...
git add .

:: Realizar commit
git commit -m "Subida automatica desde .bat - PARAGUASMJ"

:: Configurar remoto HTTPS (borramos si existe y lo volvemos a poner)
git remote remove origin 2>nul
git remote add origin https://github.com/zidmauricio-droid/PARAGUASMJ.git

:: Subir a GitHub (pedira usuario y token)
echo.
echo ====================================================
echo  Subiendo a GitHub...
echo  Usuario: zidmauricio-droid
echo  Contrasena: pega tu TOKEN (generado en GitHub)
echo  (El token NO es tu contrasena de GitHub)
echo ====================================================
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo subir el codigo.
    echo Asegurate de haber creado un token en GitHub (Settings -> Developer settings -> Personal access tokens -> Classic)
    echo El token debe tener permiso 'repo'.
) else (
    echo.
    echo ====================================================
    echo  ¡CODIGO SUBIDO CORRECTAMENTE!
    echo  Repositorio: https://github.com/zidmauricio-droid/PARAGUASMJ
    echo ====================================================
)

echo.
pause