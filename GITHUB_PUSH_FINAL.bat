@echo off
title PARAGUASMJ - GitHub Sync
color 0A

echo.
echo ================================================
echo    PARAGUASMJ - GitHub Sync
echo ================================================
echo.

:: Change to main branch
git checkout main 2>nul
if errorlevel 1 (
    echo Creating main branch from origin...
    git fetch origin
    git checkout -b main origin/main
)

:: Add all changes
git add .

:: Commit changes
git commit -m "PARAGUASMJ - Sync %date% %time%" 2>nul

:: Push to GitHub
echo.
echo Uploading to GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Push failed.
    echo Try: git pull origin main --rebase
) else (
    echo.
    echo ================================================
    echo    SUCCESS! Code on GitHub
    echo    https://github.com/zidmauricio-droid/PARAGUASMJ
    echo ================================================
)

pause
