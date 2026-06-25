"""
gcal_tools.py - Google Calendar 연동 도구
OAuth2 기반 — 최초 1회 setup_google_auth.py 실행 필요

필요 패키지: google-auth-oauthlib google-auth-httplib2 google-api-python-client
사전 설정: Google Cloud Console에서 OAuth 2.0 자격증명 다운로드 → credentials.json 저장
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path

TOKEN_FILE = Path(__file__).parent.parent / "data" / "google_token.json"
CREDS_FILE = Path(__file__).parent.parent / "credentials.json"

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GCAL_AVAILABLE = True
except ImportError:
    GCAL_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    """Google Calendar API 서비스 객체를 반환한다."""
    if not GCAL_AVAILABLE:
        return None, {"success": False, "error": "google 패키지 미설치. setup_google_auth.py 실행 필요"}
    if not CREDS_FILE.exists():
        return None, {"success": False, "error": f"credentials.json 없음. Google Cloud Console에서 다운로드 후 {CREDS_FILE} 에 저장하세요."}

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None, {"success": False, "error": "Google 인증 필요. setup_google_auth.py를 실행하세요."}
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service, None


def list_upcoming_events(max_results: int = 10, calendar_id: str = "primary") -> dict:
    """앞으로 예정된 Google Calendar 일정을 가져온다."""
    service, err = _get_service()
    if err:
        return err
    try:
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        items = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            items.append({
                "id":       e["id"],
                "title":    e.get("summary", "(제목 없음)"),
                "start":    start,
                "end":      e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location", ""),
            })
        return {"success": True, "count": len(items), "events": items}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_event(title: str, start_datetime: str, end_datetime: str,
                 description: str = "", location: str = "", calendar_id: str = "primary") -> dict:
    """Google Calendar에 새 일정을 추가한다.
    start_datetime / end_datetime 형식: "2026-06-25T14:00:00+09:00"
    """
    service, err = _get_service()
    if err:
        return err
    try:
        body = {
            "summary":     title,
            "description": description,
            "location":    location,
            "start":       {"dateTime": start_datetime, "timeZone": "Asia/Seoul"},
            "end":         {"dateTime": end_datetime,   "timeZone": "Asia/Seoul"},
        }
        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        return {"success": True, "message": f"일정 생성: {title}", "event_id": event["id"], "link": event.get("htmlLink", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_event(event_id: str, calendar_id: str = "primary") -> dict:
    """Google Calendar 일정을 삭제한다."""
    service, err = _get_service()
    if err:
        return err
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"success": True, "message": f"일정 삭제 완료 (id: {event_id})"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_events(query: str, max_results: int = 5, calendar_id: str = "primary") -> dict:
    """Google Calendar에서 일정을 검색한다."""
    service, err = _get_service()
    if err:
        return err
    try:
        results = service.events().list(
            calendarId=calendar_id,
            q=query,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = results.get("items", [])
        items = [{"id": e["id"], "title": e.get("summary",""), "start": e["start"].get("dateTime", e["start"].get("date"))} for e in events]
        return {"success": True, "count": len(items), "events": items}
    except Exception as e:
        return {"success": False, "error": str(e)}


GCAL_TOOLS = [
    {
        "name": "list_upcoming_events",
        "description": "다가오는 Google Calendar 일정을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results":  {"type": "integer", "description": "조회할 최대 개수 (기본 10)"},
                "calendar_id":  {"type": "string",  "description": "캘린더 ID (기본 'primary')"}
            }
        }
    },
    {
        "name": "create_event",
        "description": "Google Calendar에 새 일정을 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":          {"type": "string", "description": "일정 제목"},
                "start_datetime": {"type": "string", "description": "시작 시간 (ISO 8601, 예: '2026-06-25T14:00:00+09:00')"},
                "end_datetime":   {"type": "string", "description": "종료 시간 (ISO 8601)"},
                "description":    {"type": "string", "description": "일정 설명 (선택)"},
                "location":       {"type": "string", "description": "장소 (선택)"},
                "calendar_id":    {"type": "string", "description": "캘린더 ID (기본 'primary')"}
            },
            "required": ["title", "start_datetime", "end_datetime"]
        }
    },
    {
        "name": "delete_event",
        "description": "Google Calendar 일정을 삭제한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":    {"type": "string", "description": "삭제할 이벤트 ID"},
                "calendar_id": {"type": "string", "description": "캘린더 ID (기본 'primary')"}
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "search_events",
        "description": "Google Calendar에서 키워드로 일정을 검색한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":       {"type": "string",  "description": "검색 키워드"},
                "max_results": {"type": "integer", "description": "최대 결과 수 (기본 5)"},
                "calendar_id": {"type": "string",  "description": "캘린더 ID (기본 'primary')"}
            },
            "required": ["query"]
        }
    }
]

def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "list_upcoming_events": list_upcoming_events,
        "create_event":         create_event,
        "delete_event":         delete_event,
        "search_events":        search_events,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
