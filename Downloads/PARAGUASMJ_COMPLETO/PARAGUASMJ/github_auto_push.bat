@echo off
chcp 65001 >nul
title PARAGUASMJ — GitHub Auto-Push
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║              PARAGUASMJ — PUSH AUTOMÁTICO a GitHub                       ║
echo  ║                                                                          ║
echo  ║                    Usuario: zidmauricio-droid                            ║
echo  ║                    Email:   zidmauricio@gmail.com                        ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.

:: ============================================================
:: DATOS AUTOMÁTICOS
:: ============================================================
set USUARIO_GITHUB=zidmauricio-droid
set EMAIL_GITHUB=zidmauricio@gmail.com
set NOMBRE_GITHUB=Mauricio Jimenez

echo  [1/5] Configurando identidad...
git config --global user.name "%NOMBRE_GITHUB%"
git config --global user.email "%EMAIL_GITHUB%"
echo  OK Identidad configurada
echo.

:: ============================================================
:: VERIFICAR GIT
:: ============================================================
echo  [2/5] Verificando Git...
where git >nul 2>nul
if errorlevel 1 (
    echo  Instalando Git...
    winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
    echo  OK Git instalado
) else (
    echo  OK Git encontrado
)
echo.

:: ============================================================
:: CONFIGURAR GITHUB CLI
:: ============================================================
echo  [3/5] Configurando GitHub CLI...
where gh >nul 2>nul
if errorlevel 1 (
    echo  Instalando GitHub CLI...
    winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
    echo  OK GitHub CLI instalado
)

gh auth status >nul 2>nul
if errorlevel 1 (
    echo.
    echo  Iniciando sesion en GitHub...
    echo  Se abrira una ventana del navegador.
    echo  Solo necesitas hacer esto UNA SOLA VEZ.
    echo.
    gh auth login
    if errorlevel 1 (
        echo.
        echo  Para autenticarte manualmente:
        echo  1. Ve a: https://github.com/settings/tokens
        echo  2. Genera un token con permisos "repo"
        echo  3. Ejecuta: gh auth login --with-token
        echo.
        pause
    )
)
echo.

:: ============================================================
:: INICIALIZAR REPOSITORIO
:: ============================================================
echo  [4/5] Inicializando repositorio...
cd /d "%~dp0"

if not exist ".git" (
    git init
    echo  OK Repositorio git creado
)

if not exist ".gitignore" (
    echo  Creando .gitignore...
    (
        echo __pycache__/
        echo *.pyc
        echo *.pyo
        echo *.db
        echo *.sqlite
        echo database/*.db
        echo logs/*.log
        echo logs/*.json
        echo backups/
        echo *.key
        echo config/secret.key
        echo .env
        echo .DS_Store
        echo Thumbs.db
        echo desktop.ini
    ) > .gitignore
)

git add .
git commit -m "PARAGUASMJ - Actualizacion automatica %date% %time%"
echo  OK Cambios guardados localmente
echo.

:: ============================================================
:: SUBIR A GITHUB
:: ============================================================
echo  [5/5] Subiendo a GitHub...

git remote -v | find "origin" >nul
if errorlevel 1 (
    echo  Creando repositorio en GitHub...
    gh repo create PARAGUASMJ --public --source=. --remote=origin --push 2>nul
    if errorlevel 1 (
        git remote add origin https://github.com/%USUARIO_GITHUB%/PARAGUASMJ.git
        git branch -M main
        git push -u origin main
    )
) else (
    git push origin main
)

if errorlevel 1 (
    echo.
    echo  Error al subir. Intentando pull primero...
    git pull origin main --rebase
    git push origin main
)

echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                         OK CODIGO SUBIDO                                 ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo  Tu codigo esta en: https://github.com/%USUARIO_GITHUB%/PARAGUASMJ
echo.
echo  Para proximas actualizaciones, ejecuta: actualizar_github.bat
echo.

pause
