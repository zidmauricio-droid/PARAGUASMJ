@echo off
title PARAGUASMJ - Actualizar GitHub
color 0A
echo.
echo ================================================
echo    PARAGUASMJ - Actualizar GitHub
echo ================================================
echo.
:: Datos fijos
set USUARIO=zidmauricio-droid
:: Agregar cambios
git add .
git commit -m "Actualizacion automatica %date%"
:: Subir
git push origin main
if errorlevel 1 (
    echo.
    echo Error al subir. Intentando pull primero...
    git pull origin main --rebase
    git push origin main
)
echo.
echo OK - Codigo actualizado
echo https://github.com/%USUARIO%/PARAGUASMJ
pause
