"""
setup_google_auth.py - Google Calendar OAuth2 최초 인증 설정

사전 준비:
  1. https://console.cloud.google.com → 프로젝트 생성
  2. APIs & Services → Library → Google Calendar API 활성화
  3. APIs & Services → Credentials → OAuth 2.0 클라이언트 ID 생성 (Desktop app)
  4. JSON 다운로드 → Agent J 폴더에 credentials.json 으로 저장

실행: python setup_google_auth.py
결과: data/google_token.json 생성 → 이후 gcal_tools.py 자동 사용
"""
import sys
from pathlib import Path

CREDS_FILE = Path("credentials.json")
TOKEN_FILE  = Path("data/google_token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def main():
    if not CREDS_FILE.exists():
        print("[오류] credentials.json 파일이 없습니다.")
        print("→ Google Cloud Console에서 OAuth 2.0 자격증명을 다운로드하여")
        print(f"  이 폴더에 'credentials.json' 으로 저장하세요: {Path.cwd()}")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("[오류] google 패키지가 없습니다. 아래 명령어를 실행하세요:")
        print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    print("브라우저에서 Google 계정 인증 창이 열립니다...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())
    print(f"\n✅ 인증 완료! 토큰 저장: {TOKEN_FILE}")
    print("이제 Agent J에서 'Google Calendar 일정 추가해줘' 등을 사용할 수 있습니다.")

if __name__ == "__main__":
    main()
