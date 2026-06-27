@echo off
:: ============================================================
:: setup_notifier.bat  —  Agent J 알림 스케줄러 등록
::
:: 이 파일을 한 번만 "관리자 권한으로 실행"하면
:: Windows Task Scheduler에 두 가지 작업이 자동 등록됩니다:
::   - 오전 8:00: 아침 체크인 + Due date 임박 알림
::   - 오후 9:00: 저녁 회고 리마인더 + 학습 미달 경고
::
:: 등록 확인: 작업 스케줄러(taskschd.msc) > "Agent J" 폴더
:: 삭제:      schtasks /Delete /TN "AgentJ\Morning" /F
::            schtasks /Delete /TN "AgentJ\Evening" /F
:: ============================================================

:: Agent J 폴더 경로 (이 bat 파일이 있는 위치)
set AGENT_DIR=%~dp0
:: venv Python 경로
set PYTHON=%AGENT_DIR%venv\Scripts\python.exe

:: plyer 설치 확인 (없으면 설치)
echo [1/3] plyer 패키지 확인 중...
"%PYTHON%" -c "import plyer" 2>nul
if errorlevel 1 (
    echo     plyer 설치 중...
    "%PYTHON%" -m pip install plyer --quiet
    echo     plyer 설치 완료
) else (
    echo     plyer 이미 설치됨
)

:: 기존 작업 삭제 (재등록 시 충돌 방지)
echo [2/3] 기존 스케줄 정리 중...
schtasks /Delete /TN "AgentJ\Morning" /F >nul 2>&1
schtasks /Delete /TN "AgentJ\Evening" /F >nul 2>&1

:: 스케줄 등록
echo [3/3] 스케줄 등록 중...

:: 아침 알림 (매일 08:00)
schtasks /Create ^
  /TN "AgentJ\Morning" ^
  /TR "\"%PYTHON%\" \"%AGENT_DIR%notifier.py\" --mode morning" ^
  /SC DAILY ^
  /ST 08:00 ^
  /RU "%USERNAME%" ^
  /RL HIGHEST ^
  /F

:: 저녁 알림 (매일 21:00)
schtasks /Create ^
  /TN "AgentJ\Evening" ^
  /TR "\"%PYTHON%\" \"%AGENT_DIR%notifier.py\" --mode evening" ^
  /SC DAILY ^
  /ST 21:00 ^
  /RU "%USERNAME%" ^
  /RL HIGHEST ^
  /F

echo.
echo ============================================================
echo  Agent J 알림 스케줄 등록 완료!
echo    아침 체크인:       매일 오전 08:00
echo    저녁 회고 리마인더: 매일 오후 09:00
echo.
echo  즉시 테스트:
echo    python notifier.py --mode morning
echo    python notifier.py --mode evening
echo ============================================================
pause
