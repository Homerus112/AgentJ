@echo off
setlocal enableextensions
chcp 65001 > nul
title Agent J Setup
echo ============================================
echo  Agent J Context Menu Setup
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_registry.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: PowerShell failed. Code: %ERRORLEVEL%
    pause
    exit /b 1
)
echo.
echo Restarting Explorer to apply changes...
taskkill /F /IM explorer.exe > nul 2>&1
timeout /t 1 > nul
start explorer.exe
echo Explorer restarted. Right-click any file to see Agent J menu.
echo.
pause
