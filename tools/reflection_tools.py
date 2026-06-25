"""
tools/reflection_tools.py
Daily Reflection 관련 도구 모음
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_today_summary() -> dict:
    """오늘의 대화 히스토리 요약용 데이터 로드"""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from memory.history_db import search_messages

        today = datetime.now().strftime("%Y-%m-%d")
        messages = search_messages(today, limit=100)
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        return {
            "date": today,
            "user_messages": user_msgs,
            "message_count": len(messages)
        }
    except Exception as e:
        return {"date": datetime.now().strftime("%Y-%m-%d"), "user_messages": [], "message_count": 0, "error": str(e)}


def get_completed_tasks_today() -> list:
    """오늘 완료된 할 일 목록"""
    try:
        tasks_path = os.path.join(os.path.dirname(__file__), "..", "data", "tasks.json")
        if not os.path.exists(tasks_path):
            return []
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        return [t for t in tasks if t.get("status") == "done" and today in t.get("updated_at", "")]
    except Exception:
        return []


def save_reflection_to_notion(date: str, content: str) -> dict:
    """회고 내용을 Notion에 저장"""
    try:
        from notion_client import Client

        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        parent_id = os.getenv("NOTION_PARENT_PAGE_ID")

        if not parent_id or not os.getenv("NOTION_API_KEY"):
            return {"success": False, "error": "Notion 환경변수 미설정"}

        # 날짜 형식 변환 (YYYY-MM-DD → MM월 DD일)
        dt = datetime.strptime(date, "%Y-%m-%d")
        title = f"📝 Daily Reflection — {dt.month}월 {dt.day}일"

        # 내용을 2000자 단위로 분할 (Notion API 제한)
        chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            }
            for chunk in chunks
        ]

        page = notion.pages.create(
            parent={"page_id": parent_id},
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=children
        )
        return {"success": True, "url": page.get("url", ""), "title": title}

    except Exception as e:
        return {"success": False, "error": str(e)}


def load_past_reflections(days: int = 7) -> list:
    """최근 N일간 회고 내용 로드 (주간 회고용)"""
    try:
        from notion_client import Client
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        parent_id = os.getenv("NOTION_PARENT_PAGE_ID")
        if not parent_id:
            return []

        results = notion.blocks.children.list(block_id=parent_id).get("results", [])
        reflections = []
        cutoff = datetime.now() - timedelta(days=days)

        for block in results:
            if block.get("type") == "child_page":
                title = block.get("child_page", {}).get("title", "")
                if "Daily Reflection" in title:
                    created = datetime.fromisoformat(block.get("created_time", "").replace("Z", "+00:00"))
                    if created.replace(tzinfo=None) >= cutoff:
                        reflections.append({"title": title, "id": block["id"]})

        return reflections
    except Exception:
        return []
