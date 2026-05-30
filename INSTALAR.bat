@echo off
:: ================================================================
::  PARAGUASMJ - INSTALADOR AUTOMATICO
::  Ejecute este archivo UNA SOLA VEZ como Administrador
::  Despues use el acceso directo del escritorio
:: ================================================================
title PARAGUASMJ - Instalador
color 0B

echo.
echo  =====================================================
echo   PARAGUASMJ
echo   Sistema Integrado de Gestion Documental
echo   Acueducto El Puente - Villeta, Cundinamarca
echo  =====================================================
echo.
echo  Instalando el sistema, por favor espere...
echo.

:: Verificar si se ejecuta como Administrador
net session >nul 2>&1
if errorlevel 1 (
    echo  [!] Necesita permisos de Administrador.
    echo  [!] Haga clic derecho en INSTALAR.bat y elija
    echo      "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

:: Definir carpeta de instalacion
set "INSTALL_DIR=%PROGRAMFILES%\PARAGUASMJ_2026"
set "SCRIPT_DIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"

echo  [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python no encontrado. Descargando Python 3.11...
    echo      Esto puede tardar unos minutos segun su conexion.
    
    :: Descargar Python con curl (disponible en Windows 10/11)
    curl -L -o "%TEMP%\python_installer.exe" ^
        "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" ^
        --progress-bar
    
    if exist "%TEMP%\python_installer.exe" (
        echo  Instalando Python 3.11 silenciosamente...
        "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
        del "%TEMP%\python_installer.exe"
        
        :: Actualizar PATH sin reiniciar
        call refreshenv.cmd >nul 2>&1
        set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts"
    ) else (
        echo  [ERROR] No se pudo descargar Python.
        echo  Descargue Python 3.11 manualmente desde python.org
        pause & exit /b 1
    )
)
echo  [OK] Python encontrado.

echo  [2/6] Instalando dependencias del sistema...
python -m pip install --upgrade pip --quiet
python -m pip install flask==3.1.0 waitress==3.0.2 --quiet
python -m pip install pandas openpyxl reportlab Pillow --quiet
python -m pip install apscheduler requests python-docx --quiet
python -m pip install pyinstaller --quiet
echo  [OK] Dependencias instaladas.

echo  [3/6] Compilando ejecutable PARAGUASMJ_2026.exe...
cd /d "%SCRIPT_DIR%"

:: Limpiar compilaciones anteriores
if exist build rmdir /s /q build >nul 2>&1
if exist dist  rmdir /s /q dist  >nul 2>&1

:: Crear icono institucional
if not exist "icon.ico" (
    powershell -Command "Add-Type -AssemblyName System.Drawing; $bmp = New-Object System.Drawing.Bitmap(256,256); $g = [System.Drawing.Graphics]::FromImage($bmp); $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias; $g.Clear([System.Drawing.Color]::FromArgb(11,43,74)); $font = New-Object System.Drawing.Font('Arial', 55, [System.Drawing.FontStyle]::Bold); $g.DrawString('A', $font, [System.Drawing.Brushes]::White, 72, 65); $font2 = New-Object System.Drawing.Font('Arial', 14, [System.Drawing.FontStyle]::Bold); $g.DrawString('SIGD', $font2, [System.Drawing.Brushes]::Cyan, 60, 175); $bmp.Save('icon.ico', [System.Drawing.Imaging.ImageFormat]::Icon);" >nul 2>&1
)

python -m PyInstaller --onefile ^
    --windowed ^
    --icon=icon.ico ^
    --name="PARAGUASMJ_2026" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "routes;routes" ^
    --add-data "database;database" ^
    --add-data "core;core" ^
    --add-data "utils;utils" ^
    --hidden-import=waitress ^
    --hidden-import=flask.cli ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=openpyxl.styles ^
    --hidden-import=reportlab ^
    --hidden-import=apscheduler ^
    --hidden-import=requests ^
    --hidden-import=docx ^
    --hidden-import=werkzeug.security ^
    --hidden-import=sqlite3 ^
    --hidden-import=PIL ^
    --clean ^
    --log-level=ERROR ^
    run.py >nul 2>&1

if not exist "dist\PARAGUASMJ_2026.exe" (
    echo.
    echo  [ERROR] Fallo la compilacion. Intentando metodo alternativo...
    python -m PyInstaller --onefile --console --icon=icon.ico ^
        --name="PARAGUASMJ_2026" ^
        --add-data "templates;templates" ^
        --add-data "static;static" ^
        --add-data "routes;routes" ^
        --add-data "database;database" ^
        --add-data "core;core" ^
        --add-data "utils;utils" ^
        --hidden-import=waitress --hidden-import=flask.cli ^
        --hidden-import=pandas --hidden-import=openpyxl ^
        --hidden-import=reportlab --hidden-import=apscheduler ^
        --hidden-import=requests --hidden-import=docx ^
        --hidden-import=werkzeug.security --hidden-import=sqlite3 ^
        --clean run.py >nul 2>&1
)

if not exist "dist\PARAGUASMJ_2026.exe" (
    echo  [ERROR] No se pudo crear el ejecutable.
    echo  Usando modo directo (sin compilar)...
    goto :CREAR_ACCESO_DIRECTO_PYTHON
)

echo  [OK] Ejecutable creado correctamente.

echo  [4/6] Instalando en Archivos de programa...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "dist\PARAGUASMJ_2026.exe" "%INSTALL_DIR%\" >nul
if exist "icon.ico" copy /Y "icon.ico" "%INSTALL_DIR%\" >nul
echo  [OK] Instalado en %INSTALL_DIR%

echo  [5/6] Creando acceso directo en el escritorio...
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $S = $WS.CreateShortcut('%DESKTOP%\PARAGUASMJ.lnk'); $S.TargetPath = '%INSTALL_DIR%\PARAGUASMJ_2026.exe'; $S.WorkingDirectory = '%INSTALL_DIR%'; $S.IconLocation = '%INSTALL_DIR%\icon.ico'; $S.Description = 'ASUACAP - Sistema Integrado de Gestion Documental 2026'; $S.Save()"

:: Tambien crear acceso directo en el menu Inicio
if not exist "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\ASUACAP" (
    mkdir "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\ASUACAP"
)
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $S = $WS.CreateShortcut('%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\ASUACAP\PARAGUASMJ.lnk'); $S.TargetPath = '%INSTALL_DIR%\PARAGUASMJ_2026.exe'; $S.WorkingDirectory = '%INSTALL_DIR%'; $S.IconLocation = '%INSTALL_DIR%\icon.ico'; $S.Save()"

echo  [OK] Acceso directo creado en el escritorio.

echo  [6/6] Configurando inicio automatico...

goto :EXITO

:CREAR_ACCESO_DIRECTO_PYTHON
:: Modo alternativo: acceso directo que ejecuta Python directamente
set "LAUNCH_SCRIPT=%INSTALL_DIR%\iniciar_asuacap.bat"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
xcopy /E /I /Q "%SCRIPT_DIR%*" "%INSTALL_DIR%\" >nul 2>&1

echo @echo off > "%LAUNCH_SCRIPT%"
echo cd /d "%INSTALL_DIR%" >> "%LAUNCH_SCRIPT%"
echo start "" /B python run.py >> "%LAUNCH_SCRIPT%"
echo timeout /t 3 /nobreak >nul >> "%LAUNCH_SCRIPT%"
echo start http://localhost:5000 >> "%LAUNCH_SCRIPT%"

powershell -Command "$WS = New-Object -ComObject WScript.Shell; $S = $WS.CreateShortcut('%DESKTOP%\PARAGUASMJ.lnk'); $S.TargetPath = '%LAUNCH_SCRIPT%'; $S.WorkingDirectory = '%INSTALL_DIR%'; $S.IconLocation = '%INSTALL_DIR%\icon.ico'; $S.WindowStyle = 7; $S.Description = 'ASUACAP - Sistema Integrado de Gestion Documental 2026'; $S.Save()"

:EXITO
echo.
echo  =====================================================
echo   INSTALACION COMPLETADA!
echo  =====================================================
echo.
echo   En su escritorio encontrara el icono:
echo   "PARAGUASMJ"
echo.
echo   Solo haga DOBLE CLIC para iniciar el sistema.
echo   Se abrira el navegador automaticamente.
echo.
echo   Usuario:    admin
echo   Contrasena: PARAGUASMJ2026
echo.
echo  =====================================================
echo.

:: Preguntar si desea iniciar ahora
choice /C SN /N /M "  Desea iniciar el sistema ahora? (S=Si / N=No): "
if errorlevel 2 goto :TERMINAR
if errorlevel 1 (
    echo.
    echo  Iniciando PARAGUASMJ...
    if exist "%INSTALL_DIR%\PARAGUASMJ_2026.exe" (
        start "" "%INSTALL_DIR%\PARAGUASMJ_2026.exe"
    ) else (
        start "" "%INSTALL_DIR%\iniciar_asuacap.bat"
    )
)

:TERMINAR
echo.
echo  Puede cerrar esta ventana.
timeout /t 5 /nobreak >nul
exit /b 0
