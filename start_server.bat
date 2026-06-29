@echo off
echo ===============================
echo   Agent J Desktop API Server
echo ===============================
echo.
if exist "venv\Scripts\activate.bat" (
    echo [+] 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo [!] 가상환경 없음 - 시스템 Python 사용
)
python -c "import fastapi, uvicorn, websockets, multipart" 2>nul
if errorlevel 1 (
    echo [!] 필수 패키지 미설치. 설치 중...
    pip install "fastapi[standard]" "uvicorn[standard]" websockets python-multipart
)
echo [+] 서버 시작: http://127.0.0.1:8765
echo [+] 종료하려면 Ctrl+C
echo.
python -m uvicorn server.api:app --host 127.0.0.1 --port 8765
pause
