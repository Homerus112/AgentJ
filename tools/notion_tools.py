"""
notion_tools.py - Notion API 연동 도구
필요: NOTION_API_KEY, NOTION_TASKS_DB_ID, NOTION_PARENT_PAGE_ID
"""
import json, os, re
from datetime import datetime

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False


def _client():
    if not NOTION_AVAILABLE:
        return None, {"success": False, "error": "notion-client 미설치"}
    key = os.getenv("NOTION_API_KEY")
    if not key:
        return None, {"success": False, "error": ".env에 NOTION_API_KEY가 없습니다."}
    return Client(auth=key), None


CATEGORY_EMOJI = {
    "resume":   "👤",
    "research": "🔬",
    "meeting":  "📋",
    "memo":     "📝",
    "other":    "📄",
}


def _markdown_to_blocks(content: str) -> list:
    """마크다운 텍스트를 Notion 블록 리스트로 변환한다."""
    blocks = []
    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        plain = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        plain = re.sub(r'\*(.+?)\*', r'\1', plain)
        plain = re.sub(r'__(.+?)__', r'\1', plain)

        if s.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [{"type": "text", "text": {"content": plain[4:]}}]}})
        elif s.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"type": "text", "text": {"content": plain[3:]}}]}})
        elif s.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [{"type": "text", "text": {"content": plain[2:]}}]}})
        elif s.startswith(("- ", "* ", "• ")):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": plain[2:]}}]}})
        elif re.match(r'^\d+\.\s', s):
            text = re.sub(r'^\d+\.\s', '', plain)
            blocks.append({"object": "block", "type": "numbered_list_item",
                           "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": [{"type": "text", "text": {"content": plain}}]}})
        if len(blocks) >= 95:
            break
    return blocks


def save_rich_page(title: str, content: str, category: str = "memo",
                   parent_page_id: str = None) -> dict:
    """마크다운 내용을 Notion 페이지로 저장한다. category: memo|research|meeting|resume|other"""
    client, err = _client()
    if err:
        return err
    page_id = parent_page_id or os.getenv("NOTION_PARENT_PAGE_ID")
    if not page_id:
        return {"success": False, "error": ".env에 NOTION_PARENT_PAGE_ID가 필요합니다."}
    try:
        emoji = CATEGORY_EMOJI.get(category, "📄")
        full_title = f"{emoji} {title}"
        blocks = _markdown_to_blocks(content)
        date_block = {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {
                    "content": f"저장 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 카테고리: {category}"
                }}],
                "icon": {"type": "emoji", "emoji": emoji}
            }
        }
        page = client.pages.create(
            parent={"page_id": page_id},
            properties={"title": {"title": [{"text": {"content": full_title}}]}},
            children=[date_block] + blocks
        )
        return {
            "success": True,
            "message": f"Notion 저장 완료: {full_title}",
            "page_id": page["id"],
            "url": page.get("url", ""),
            "category": category
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_task_to_db(name: str, status: str = "할 일",
                    priority: str = "보통", due: str = None) -> dict:
    """할 일/태스크를 Notion Tasks DB에 저장한다."""
    client, err = _client()
    if err:
        return err
    db_id = os.getenv("NOTION_TASKS_DB_ID")
    if not db_id:
        return {"success": False, "error": ".env에 NOTION_TASKS_DB_ID가 없습니다."}
    try:
        props = {
            "Name":     {"title":  [{"text": {"content": name}}]},
            "Status":   {"select": {"name": status}},
            "Priority": {"select": {"name": priority}},
        }
        if due:
            props["Due"] = {"date": {"start": due}}
        page = client.pages.create(parent={"database_id": db_id}, properties=props)
        return {
            "success": True,
            "message": f"Tasks DB 저장 완료: {name}",
            "page_id": page["id"],
            "url": page.get("url", "")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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
            priority_map = {"high": "높음", "medium": "보통", "low": "낮음"}
            due_prop = {"date": {"start": task["due_date"]}} if task.get("due_date") else None
            props = {
                "Name":     {"title":  [{"text": {"content": task.get("title", "")}}]},
                "Status":   {"select": {"name": "할 일" if task.get("status") == "pending" else "완료"}},
                "Priority": {"select": {"name": priority_map.get(task.get("priority", "medium"), "보통")}},
            }
            if due_prop:
                props["Due"] = due_prop
            client.pages.create(parent={"database_id": db_id}, properties=props)
            synced += 1
        return {"success": True, "message": f"Notion에 {synced}개 할 일 동기화 완료"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_notion_page(title: str, content: str, parent_page_id: str = None) -> dict:
    """Notion에 새 페이지를 생성한다. (레거시 - save_rich_page 사용 권장)"""
    client, err = _client()
    if err:
        return err
    page_id = parent_page_id or os.getenv("NOTION_PARENT_PAGE_ID")
    if not page_id:
        return {"success": False, "error": ".env에 NOTION_PARENT_PAGE_ID가 필요합니다."}
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
        return {"success": True, "message": f"Notion 페이지 생성: {title}",
                "page_id": page["id"], "url": page.get("url", "")}
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
            items.append({"id": r["id"], "type": r.get("object"),
                          "title": title, "url": r.get("url", "")})
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
        "name": "save_rich_page",
        "description": "메모, 리서치, 회의록, 이력서, 아이디어 등을 Notion 페이지로 저장한다. 마크다운 형식 지원.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":          {"type": "string", "description": "페이지 제목"},
                "content":        {"type": "string", "description": "마크다운 형식 본문 (# 제목, ## 소제목, - 목록)"},
                "category":       {
                    "type": "string",
                    "enum": ["memo", "research", "meeting", "resume", "other"],
                    "description": "memo=메모/아이디어, research=리서치, meeting=회의록, resume=이력서"
                },
                "parent_page_id": {"type": "string", "description": "상위 페이지 ID (없으면 기본값 사용)"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "save_task_to_db",
        "description": "할 일/태스크를 Notion Tasks DB에 저장한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":     {"type": "string", "description": "태스크 이름"},
                "status":   {"type": "string", "description": "상태 (기본: 할 일)"},
                "priority": {"type": "string", "enum": ["높음", "보통", "낮음"]},
                "due":      {"type": "string", "description": "마감일 YYYY-MM-DD"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "sync_tasks_to_notion",
        "description": "Agent J 할 일 목록을 Notion DB에 동기화한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "description": "동기화할 task 객체 배열"}
            },
            "required": ["tasks"]
        }
    },
    {
        "name": "create_notion_page",
        "description": "Notion에 새 페이지를 생성한다. (레거시)",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":          {"type": "string"},
                "content":        {"type": "string"},
                "parent_page_id": {"type": "string"}
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
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_to_notion_db",
        "description": "Notion DB에 새 항목을 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string"},
                "title":       {"type": "string"},
                "properties":  {"type": "object"}
            },
            "required": ["database_id", "title"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "save_rich_page":       save_rich_page,
        "save_task_to_db":      save_task_to_db,
        "sync_tasks_to_notion": sync_tasks_to_notion,
        "create_notion_page":   create_notion_page,
        "search_notion":        search_notion,
        "add_to_notion_db":     add_to_notion_db,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
