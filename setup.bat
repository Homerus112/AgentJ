@echo off
echo ====================================
echo  Agent J 초기 설정 스크립트
echo ====================================
echo.

REM 1. 가상환경 생성
echo [1/4] 가상환경 생성 중...
python -m venv venv
if errorlevel 1 (
    echo [오류] 가상환경 생성 실패. Python이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

REM 2. 가상환경 활성화 및 패키지 설치
echo [2/4] 패키지 설치 중...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치 실패.
    pause
    exit /b 1
)

REM 3. .env 파일 생성 (없는 경우)
echo [3/4] 환경 설정 파일 확인 중...
if not exist .env (
    copy .env.example .env
    echo .env 파일이 생성되었습니다. API 키를 입력해주세요!
    echo 파일 위치: %cd%\.env
) else (
    echo .env 파일이 이미 존재합니다.
)

REM 4. 완료 안내
echo.
echo [4/4] 설정 완료!
echo ====================================
echo  다음 단계:
echo  1. .env 파일을 열어 ANTHROPIC_API_KEY를 입력하세요
echo  2. 아래 명령어로 J를 실행하세요:
echo.
echo     venv\Scripts\activate
echo     python main.py
echo ====================================
echo.
pause
