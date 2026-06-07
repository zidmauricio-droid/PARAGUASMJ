@echo off
chcp 65001 >nul
title PARAGUASMJ — Instalador
color 0B

echo.
echo  =====================================================
echo   PARAGUASMJ
echo   Sistema Integrado de Gestion Documental
echo   Acueducto El Puente - Villeta, Cundinamarca
echo  =====================================================
echo.

:: Verificar permisos de administrador
net session >nul 2>&1
if errorlevel 1 (
    echo  [!] NECESITA PERMISOS DE ADMINISTRADOR
    echo  [!] Haga clic derecho en INSTALAR.bat
    echo      y elija "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"
set "INSTALL_DIR=%PROGRAMFILES%\PARAGUASMJ_2026"

:: ============================================================
:: [1/5] VERIFICAR / INSTALAR PYTHON
:: ============================================================
echo  [1/5] Verificando Python...

:: Intentar python y py (launcher de Windows)
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    echo  [OK] Python %PY_VER% encontrado
    set PY_CMD=python
    goto :PYTHON_OK
)

py --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do set PY_VER=%%v
    echo  [OK] Python %PY_VER% encontrado (via py launcher)
    set PY_CMD=py
    goto :PYTHON_OK
)

:: No encontrado — descargar Python 3.11
echo  [!] Python no encontrado. Descargando Python 3.11.9...
echo      Esto puede tardar 2-5 minutos segun su conexion.
echo.

curl -L --progress-bar -o "%TEMP%\python_installer.exe" ^
    "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

if not exist "%TEMP%\python_installer.exe" (
    echo  [ERROR] No se pudo descargar Python.
    echo  Descargue Python 3.11 desde: https://www.python.org/downloads/
    echo  Marque "Add Python to PATH" al instalar.
    pause
    exit /b 1
)

echo  Instalando Python 3.11 (silencioso)...
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=1
del "%TEMP%\python_installer.exe" >nul 2>&1

:: Refrescar PATH en esta sesion
set "PATH=C:\Python311;C:\Python311\Scripts;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;%PATH%"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

:: Verificar de nuevo
python --version >nul 2>&1
if not errorlevel 1 (
    set PY_CMD=python
    echo  [OK] Python instalado correctamente
    goto :PYTHON_OK
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PY_CMD=py
    echo  [OK] Python instalado correctamente
    goto :PYTHON_OK
)

echo  [ERROR] Python se instalo pero no se puede ejecutar todavia.
echo  Por favor CIERRE esta ventana, abra una nueva como Administrador
echo  y vuelva a ejecutar INSTALAR.bat
pause
exit /b 1

:PYTHON_OK

:: ============================================================
:: [2/5] INSTALAR DEPENDENCIAS
:: ============================================================
echo.
echo  [2/5] Instalando dependencias Python...
echo        (Flask, pandas, reportlab, openpyxl, etc.)
echo        Puede tardar 3-8 minutos con conexion lenta.
echo.

%PY_CMD% -m pip install --upgrade pip --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [!] Advertencia: no se pudo actualizar pip. Continuando...
)

:: Instalar desde requirements.txt
%PY_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [!] Error con requirements.txt. Instalando uno por uno...
    %PY_CMD% -m pip install "Flask>=3.1.0" --quiet
    %PY_CMD% -m pip install "waitress>=3.0.0" --quiet
    %PY_CMD% -m pip install "pandas>=2.1.0" --quiet
    %PY_CMD% -m pip install "openpyxl>=3.1.0" --quiet
    %PY_CMD% -m pip install "reportlab>=4.1.0" --quiet
    %PY_CMD% -m pip install "Pillow>=10.0.0" --quiet
    %PY_CMD% -m pip install "APScheduler>=3.10.0" --quiet
    %PY_CMD% -m pip install "requests>=2.32.0" --quiet
    %PY_CMD% -m pip install "python-docx>=1.1.0" --quiet
)

echo  [OK] Dependencias instaladas.

:: ============================================================
:: [3/5] INSTALAR PYINSTALLER Y COMPILAR EXE
:: ============================================================
echo.
echo  [3/5] Preparando ejecutable PARAGUASMJ_2026.exe...
echo        (Primera vez puede tardar 5-10 minutos)
echo.

%PY_CMD% -m pip install "pyinstaller>=6.0.0" --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [!] No se pudo instalar PyInstaller. Usando modo script.
    goto :MODO_SCRIPT
)

cd /d "%SCRIPT_DIR%"

:: Limpiar compilaciones anteriores
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist"  rmdir /s /q "dist"  >nul 2>&1
if exist "*.spec" del /q "*.spec" >nul 2>&1

:: Crear icono institucional
if not exist "icon.ico" (
    echo  Creando icono...
    powershell -Command "Add-Type -AssemblyName System.Drawing; try { $bmp=New-Object System.Drawing.Bitmap(256,256); $g=[System.Drawing.Graphics]::FromImage($bmp); $g.Clear([System.Drawing.Color]::FromArgb(30,58,138)); $font=New-Object System.Drawing.Font('Arial',80,[System.Drawing.FontStyle]::Bold); $g.DrawString('A',$font,[System.Drawing.Brushes]::White,50,60); $bmp.Save('icon.bmp',[System.Drawing.Imaging.ImageFormat]::Bmp); } catch { }" >nul 2>&1
)

echo  Compilando (puede tardar varios minutos, no cierre esta ventana)...

%PY_CMD% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name="PARAGUASMJ_2026" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "routes;routes" ^
    --add-data "database;database" ^
    --add-data "core;core" ^
    --add-data "utils;utils" ^
    --add-data "config.py;." ^
    --hidden-import=waitress ^
    --hidden-import=waitress.server ^
    --hidden-import=flask ^
    --hidden-import=flask.cli ^
    --hidden-import=flask.json ^
    --hidden-import=jinja2 ^
    --hidden-import=pandas ^
    --hidden-import=pandas._libs.tslibs.np_datetime ^
    --hidden-import=openpyxl ^
    --hidden-import=openpyxl.styles ^
    --hidden-import=openpyxl.utils ^
    --hidden-import=reportlab ^
    --hidden-import=reportlab.platypus ^
    --hidden-import=reportlab.graphics ^
    --hidden-import=reportlab.lib ^
    --hidden-import=apscheduler ^
    --hidden-import=apscheduler.schedulers.background ^
    --hidden-import=apscheduler.triggers.cron ^
    --hidden-import=requests ^
    --hidden-import=urllib3 ^
    --hidden-import=docx ^
    --hidden-import=docx.oxml ^
    --hidden-import=docx.oxml.ns ^
    --hidden-import=werkzeug.security ^
    --hidden-import=werkzeug.routing ^
    --hidden-import=sqlite3 ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=pkg_resources ^
    --hidden-import=routes.autenticacion ^
    --hidden-import=routes.dashboard ^
    --hidden-import=routes.documentos ^
    --hidden-import=routes.pqrs ^
    --hidden-import=routes.gis ^
    --hidden-import=routes.balance_hidrico ^
    --hidden-import=routes.comunicaciones ^
    --hidden-import=routes.proyectos ^
    --hidden-import=routes.api ^
    --hidden-import=routes.finanzas ^
    --hidden-import=routes.reportes_normativos ^
    --hidden-import=routes.auditoria ^
    --hidden-import=routes.proyectos_v2 ^
    --hidden-import=routes.emergencias ^
    --hidden-import=routes.convenios ^
    --hidden-import=core.database_manager ^
    --hidden-import=core.seguridad ^
    --hidden-import=core.logger ^
    --hidden-import=core.auditoria ^
    --hidden-import=core.otp_manager ^
    --hidden-import=core.pdf_profesional ^
    --hidden-import=core.backup_manager ^
    --hidden-import=core.scheduler_notificaciones ^
    --hidden-import=core.usb_updater ^
    --hidden-import=utils.audit ^
    --hidden-import=utils.helpers ^
    --hidden-import=utils.validators ^
    --collect-all=reportlab ^
    --collect-all=apscheduler ^
    --collect-all=jinja2 ^
    --clean ^
    run.py

if not exist "dist\PARAGUASMJ_2026.exe" (
    echo.
    echo  [!] Compilacion con interfaz grafica fallo.
    echo      Intentando version con consola (para ver errores)...
    echo.
    %PY_CMD% -m PyInstaller ^
        --onefile ^
        --console ^
        --name="PARAGUASMJ_2026" ^
        --add-data "templates;templates" ^
        --add-data "static;static" ^
        --add-data "routes;routes" ^
        --add-data "database;database" ^
        --add-data "core;core" ^
        --add-data "utils;utils" ^
        --add-data "config.py;." ^
        --hidden-import=waitress --hidden-import=flask --hidden-import=jinja2 ^
        --hidden-import=pandas --hidden-import=openpyxl --hidden-import=reportlab ^
        --hidden-import=apscheduler --hidden-import=apscheduler.schedulers.background ^
        --hidden-import=requests --hidden-import=docx --hidden-import=werkzeug.security ^
        --hidden-import=sqlite3 --hidden-import=PIL --hidden-import=PIL.Image ^
        --hidden-import=routes.autenticacion --hidden-import=routes.dashboard ^
        --hidden-import=routes.documentos --hidden-import=routes.pqrs ^
        --hidden-import=routes.proyectos --hidden-import=routes.convenios ^
        --collect-all=reportlab --collect-all=apscheduler --collect-all=jinja2 ^
        --clean ^
        run.py
)

if exist "dist\PARAGUASMJ_2026.exe" (
    echo  [OK] Ejecutable creado: dist\PARAGUASMJ_2026.exe
    goto :INSTALAR_EXE
)

echo  [!] No se creo el ejecutable. Usando modo script Python directo.
goto :MODO_SCRIPT

:: ============================================================
:: INSTALAR EXE en Archivos de programa
:: ============================================================
:INSTALAR_EXE
echo.
echo  [4/5] Instalando en Archivos de programa...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "dist\PARAGUASMJ_2026.exe" "%INSTALL_DIR%\" >nul
if exist "icon.ico" copy /Y "icon.ico" "%INSTALL_DIR%\" >nul

:: Crear carpetas necesarias dentro del directorio de instalacion
for %%d in (uploads pdfs database logs static templates) do (
    if not exist "%INSTALL_DIR%\%%d" mkdir "%INSTALL_DIR%\%%d" >nul 2>&1
)

echo  [OK] Instalado en: %INSTALL_DIR%
goto :CREAR_ACCESO

:: ============================================================
:: MODO SCRIPT: sin compilar, ejecuta Python directamente
:: ============================================================
:MODO_SCRIPT
echo.
echo  [4/5] Configurando modo script (sin compilar)...

set "INSTALL_DIR=%SCRIPT_DIR%"

:: Crear launcher .bat que usara Python directamente
echo @echo off > "%SCRIPT_DIR%iniciar_asuacap.bat"
echo title PARAGUASMJ >> "%SCRIPT_DIR%iniciar_asuacap.bat"
echo cd /d "%%~dp0" >> "%SCRIPT_DIR%iniciar_asuacap.bat"
echo echo Iniciando PARAGUASMJ... >> "%SCRIPT_DIR%iniciar_asuacap.bat"
echo start "" /B python run.py >> "%SCRIPT_DIR%iniciar_asuacap.bat"
echo timeout /t 4 /nobreak ^>nul >> "%SCRIPT_DIR%iniciar_asuacap.bat"
echo start http://localhost:5000 >> "%SCRIPT_DIR%iniciar_asuacap.bat"
echo timeout /t 60 /nobreak ^>nul >> "%SCRIPT_DIR%iniciar_asuacap.bat"

echo  [OK] Modo script configurado.

:: ============================================================
:: [5/5] CREAR ACCESO DIRECTO EN EL ESCRITORIO
:: ============================================================
:CREAR_ACCESO
echo.
echo  [5/5] Creando acceso directo en el escritorio...

if exist "%INSTALL_DIR%\PARAGUASMJ_2026.exe" (
    set "TARGET=%INSTALL_DIR%\PARAGUASMJ_2026.exe"
    set "WORKDIR=%INSTALL_DIR%"
) else (
    set "TARGET=%SCRIPT_DIR%INICIAR.bat"
    set "WORKDIR=%SCRIPT_DIR%"
)

set "ICON_PATH=%INSTALL_DIR%\icon.ico"
if not exist "%ICON_PATH%" set "ICON_PATH=%TARGET%"

powershell -Command "$WS=New-Object -ComObject WScript.Shell; $S=$WS.CreateShortcut('%DESKTOP%\PARAGUASMJ.lnk'); $S.TargetPath='%TARGET%'; $S.WorkingDirectory='%WORKDIR%'; $S.Description='ASUACAP - Sistema de Gestion Documental 2026'; $S.Save()" >nul 2>&1

:: Menu inicio
if not exist "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\ASUACAP" (
    mkdir "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\ASUACAP" >nul 2>&1
)
powershell -Command "$WS=New-Object -ComObject WScript.Shell; $S=$WS.CreateShortcut('%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\ASUACAP\PARAGUASMJ.lnk'); $S.TargetPath='%TARGET%'; $S.WorkingDirectory='%WORKDIR%'; $S.Description='ASUACAP - Sistema de Gestion Documental 2026'; $S.Save()" >nul 2>&1

echo  [OK] Acceso directo creado en el escritorio.

:: ============================================================
:: INICIALIZAR BASE DE DATOS
:: ============================================================
echo.
echo  Inicializando base de datos...
cd /d "%SCRIPT_DIR%"
%PY_CMD% -c "
from database.inicializar_db import inicializar_base_datos, inicializar_tablas_extra, inicializar_tablas_prog3_prog4
inicializar_base_datos()
inicializar_tablas_extra()
inicializar_tablas_prog3_prog4()
print('  Base de datos lista.')
" 2>&1
if errorlevel 1 (
    echo  [!] La base de datos se creara al iniciar por primera vez.
)

:: ============================================================
:: RESULTADO FINAL
:: ============================================================
echo.
echo  =====================================================
echo   INSTALACION COMPLETADA EXITOSAMENTE
echo  =====================================================
echo.
echo   Icono en su escritorio: PARAGUASMJ
echo   Solo haga DOBLE CLIC para iniciar.
echo.
echo   Usuario:    admin
echo   Contrasena: PARAGUASMJ2026
echo.
echo   Si el exe no inicia, use: INICIAR.bat
echo  =====================================================
echo.

choice /C SN /N /M "  Desea iniciar PARAGUASMJ ahora? (S=Si / N=No): "
if errorlevel 2 goto :FIN
if errorlevel 1 (
    echo.
    echo  Iniciando PARAGUASMJ...
    if exist "%INSTALL_DIR%\PARAGUASMJ_2026.exe" (
        start "" "%INSTALL_DIR%\PARAGUASMJ_2026.exe"
    ) else (
        start "" "%SCRIPT_DIR%INICIAR.bat"
    )
)

:FIN
echo.
echo  Puede cerrar esta ventana.
timeout /t 8 /nobreak >nul
exit /b 0
