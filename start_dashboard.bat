@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
start "" python web/app.py
timeout /t 2 /nobreak >nul
start "" http://localhost:5000
