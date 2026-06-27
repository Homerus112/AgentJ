@echo off
setlocal enableextensions
chcp 65001 > nul
title Agent J - Analyze
pushd "%~dp0"
"%~dp0venv\Scripts\pip.exe" install pypdf --quiet
"%~dp0venv\Scripts\python.exe" "%~dp0agents\vision_agent.py" --file "%~1"
popd
pause
