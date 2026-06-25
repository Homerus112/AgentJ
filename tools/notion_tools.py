"""
notion_tools.py - Notion API 연동 도구
필요: NOTION_API_KEY, NOTION_TASKS_DB_ID (선택: NOTION_NOTES_DB_ID)

Notion 설정 방법:
  1. https://www.notion.so/my-integrations → 새 통합 만들기 → API Key 복사
  2. 연동할 DB 페이지 열기 → 우상단 ··· → 연결 추가 → 방금 만든 통합 선택
  3. DB URL에서 ID 복사: notion.so/[workspace]/[DATABASE_ID]?...
"""
import json, os
from datetime import datetime

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False

def _client():
    if not NOTION_AVAILABLE:
        return None, {"success": False, "error": "notion-client 미설치. pip install notion-client 실행 필요"}
    key = os.getenv("NOTION_API_KEY")
    if not key:
        return None, {"success": False, "error": ".env에 NOTION_API_KEY가 없습니다."}
    return Client(auth=key), None


def sync_tasks_to_notion(tasks: list) -> dict:
    """Agent J 할 일 목록을 Notion DB에 동기화한다."""
    client, err = _client()
    if err:
        return err
    db_id = os.getenv("NOTION_TASKS_DB_ID")
    if not db_id:
        return {"success": False, "error": ".env에 NOTION_TASKS_DB_ID가 없습니다."}
    try:
        synced = 0
        for task in tasks:
            priority_map = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
            client.pages.create(
                parent={"database_id": db_id},
                properties={
                    "Name":     {"title": [{"text": {"content": task.get("title", "")}}]},
                    "Status":   {"select": {"name": "Pending" if task.get("status") == "pending" else "Done"}},
                    "Priority": {"select": {"name": priority_map.get(task.get("priority", "medium"), "🟡 Medium")}},
                    "Due":      {"date": {"start": task["due_date"]} if task.get("due_date") else None},
                }
            )
            synced += 1
        return {"success": True, "message": f"Notion에 {synced}개 할 일 동기화 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_notion_page(title: str, content: str, parent_page_id: str = None) -> dict:
    """Notion에 새 페이지를 생성한다."""
    client, err = _client()
    if err:
        return err
    page_id = parent_page_id or os.getenv("NOTION_PARENT_PAGE_ID")
    if not page_id:
        return {"success": False, "error": ".env에 NOTION_PARENT_PAGE_ID 또는 parent_page_id가 필요합니다."}
    try:
        paragraphs = [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}}
            for line in content.split("\n") if line.strip()
        ]
        page = client.pages.create(
            parent={"page_id": page_id},
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=paragraphs
        )
        return {"success": True, "message": f"Notion 페이지 생성: {title}", "page_id": page["id"], "url": page.get("url", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_notion(query: str) -> dict:
    """Notion에서 페이지/DB를 검색한다."""
    client, err = _client()
    if err:
        return err
    try:
        results = client.search(query=query, page_size=5).get("results", [])
        items = []
        for r in results:
            title = ""
            props = r.get("properties", {})
            if "title" in props:
                title_arr = props["title"].get("title", [])
                title = title_arr[0]["plain_text"] if title_arr else ""
            elif r.get("object") == "page":
                for v in props.values():
                    if v.get("type") == "title":
                        arr = v.get("title", [])
                        title = arr[0]["plain_text"] if arr else ""
                        break
            items.append({"id": r["id"], "type": r.get("object"), "title": title, "url": r.get("url", "")})
        return {"success": True, "count": len(items), "results": items}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_to_notion_db(database_id: str, title: str, properties: dict = None) -> dict:
    """Notion DB에 항목을 추가한다."""
    client, err = _client()
    if err:
        return err
    try:
        props = {"Name": {"title": [{"text": {"content": title}}]}}
        if properties:
            props.update(properties)
        page = client.pages.create(parent={"database_id": database_id}, properties=props)
        return {"success": True, "message": f"DB 항목 추가: {title}", "page_id": page["id"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


NOTION_TOOLS = [
    {
        "name": "sync_tasks_to_notion",
        "description": "Agent J 할 일 목록을 Notion DB에 동기화한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "description": "동기화할 task 객체 배열 (title, status, priority, due_date 포함)"}
            },
            "required": ["tasks"]
        }
    },
    {
        "name": "create_notion_page",
        "description": "Notion에 새 페이지를 생성한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":          {"type": "string", "description": "페이지 제목"},
                "content":        {"type": "string", "description": "페이지 본문 (줄바꿈 포함)"},
                "parent_page_id": {"type": "string", "description": "상위 페이지 ID (선택, 없으면 .env 기본값 사용)"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "search_notion",
        "description": "Notion 워크스페이스에서 페이지나 DB를 검색한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_to_notion_db",
        "description": "Notion 데이터베이스에 새 항목을 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "Notion DB ID"},
                "title":       {"type": "string", "description": "항목 제목"},
                "properties":  {"type": "object", "description": "추가 속성 (선택)"}
            },
            "required": ["database_id", "title"]
        }
    }
]

def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "sync_tasks_to_notion": sync_tasks_to_notion,
        "create_notion_page":   create_notion_page,
        "search_notion":        search_notion,
        "add_to_notion_db":     add_to_notion_db,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
