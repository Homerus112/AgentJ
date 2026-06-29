@echo off
setlocal enableextensions
chcp 65001 > nul
title Agent J - Ask
pushd "%~dp0"
"%~dp0venv\Scripts\pip.exe" install pypdf --quiet
"%~dp0venv\Scripts\python.exe" "%~dp0aj_interactive.py" "%~1"
popd
pause
