@echo off
:: PARAGUASMJ — Descarga de TipTap para uso offline
:: Ejecutar UNA SOLA VEZ con internet disponible
:: Después el editor funcionará sin internet

echo ============================================================
echo   PARAGUASMJ — Descarga de editor offline
echo   Requiere conexion a internet solo para este paso
echo ============================================================

set DEST=%~dp0static\vendor\tiptap
if not exist "%DEST%" mkdir "%DEST%"

set BASE=https://cdn.jsdelivr.net/npm/@tiptap

set archivos=pm core starter-kit extension-table extension-table-row extension-table-header extension-table-cell extension-image extension-text-align extension-link extension-underline extension-superscript extension-subscript extension-color extension-text-style extension-highlight extension-font-family

for %%A in (%archivos%) do (
  echo Descargando %%A...
  curl -sf -o "%DEST%\%%A.umd.js" "%BASE%/%%A@2.4.0/dist/index.umd.js"
  if exist "%DEST%\%%A.umd.js" (
    echo   OK: %%A.umd.js
  ) else (
    echo   FALLO: %%A -- reintentando con PowerShell...
    powershell -Command "Invoke-WebRequest -Uri '%BASE%/%%A@2.4.0/dist/index.umd.js' -OutFile '%DEST%\%%A.umd.js'" 2>nul
  )
)

echo.
echo ============================================================
echo   Descarga completada. El editor ahora funciona offline.
echo ============================================================
pause
