"""
notion_sync.py — 로컬 데이터를 Notion에 자동 동기화하는 중앙 허브

저장 위치:
  tasks  -> Tasks DB (Agent J)           [NOTION_TASKS_DB_ID]
  goals  -> 메모/보고서 저장 (Agent J)   [NOTION_PARENT_PAGE_ID 하위 페이지]
  skills -> 메모/보고서 저장 (Agent J)   [NOTION_PARENT_PAGE_ID 하위 페이지]
  notes  -> 메모/보고서 저장 (Agent J)   [NOTION_PARENT_PAGE_ID 하위 페이지]

설계 원칙:
  - Notion 연동 실패 시 예외를 삼켜서 로컬 저장에는 영향 없음
  - 새 DB 생성 없이 기존 DB/페이지 최대 활용
  - 업데이트가 필요한 경우 local record에 notion_page_id 저장
"""

import os
from typing import Optional
from datetime import datetime


def _client():
    try:
        from notion_client import Client
    except ImportError:
        return None, "notion-client 미설치"
    key = os.getenv("NOTION_API_KEY")
    if not key:
        return None, "NOTION_API_KEY 없음"
    return Client(auth=key), None


# ── 태스크 동기화 (Tasks DB) ───────────────────────────────

_PRIORITY_MAP = {"high": "높음", "medium": "보통", "low": "낮음"}


def _find_task_page(client, title: str) -> Optional[str]:
    """Tasks DB에서 제목으로 페이지 ID를 검색한다."""
    try:
        db_id = os.getenv("NOTION_TASKS_DB_ID")
        if not db_id:
            return None
        res = client.databases.query(
            database_id=db_id,
            filter={"property": "Name", "title": {"equals": title}}
        )
        results = res.get("results", [])
        return results[0]["id"] if results else None
    except Exception:
        return None


def sync_task_add(task: dict) -> Optional[str]:
    """새 태스크를 Notion Tasks DB에 추가하고 notion_page_id를 반환한다."""
    try:
        db_id = os.getenv("NOTION_TASKS_DB_ID")
        if not db_id:
            return None
        client, err = _client()
        if err:
            return None
        props = {
            "Name":     {"title":  [{"text": {"content": task["title"]}}]},
            "Status":   {"select": {"name": "할 일"}},
            "Priority": {"select": {"name": _PRIORITY_MAP.get(task.get("priority", "medium"), "보통")}},
        }
        if task.get("due_date"):
            props["Due"] = {"date": {"start": task["due_date"]}}
        page = client.pages.create(parent={"database_id": db_id}, properties=props)
        return page["id"]
    except Exception as e:
        print(f"[notion_sync] task add 실패: {e}")
        return None


def sync_task_complete(task: dict) -> bool:
    """Notion에서 태스크를 완료 처리한다."""
    try:
        client, err = _client()
        if err:
            return False
        page_id = task.get("notion_page_id") or _find_task_page(client, task["title"])
        if not page_id:
            return False
        client.pages.update(
            page_id=page_id,
            properties={"Status": {"select": {"name": "완료"}}}
        )
        return True
    except Exception as e:
        print(f"[notion_sync] task complete 실패: {e}")
        return False


def sync_task_update(task: dict) -> bool:
    """Notion에서 태스크 내용을 수정한다."""
    try:
        client, err = _client()
        if err:
            return False
        page_id = task.get("notion_page_id") or _find_task_page(client, task["title"])
        if not page_id:
            return False
        props = {
            "Name":     {"title":  [{"text": {"content": task["title"]}}]},
            "Priority": {"select": {"name": _PRIORITY_MAP.get(task.get("priority", "medium"), "보통")}},
        }
        if task.get("due_date"):
            props["Due"] = {"date": {"start": task["due_date"]}}
        client.pages.update(page_id=page_id, properties=props)
        return True
    except Exception as e:
        print(f"[notion_sync] task update 실패: {e}")
        return False


def sync_task_delete(task: dict) -> bool:
    """Notion에서 태스크 페이지를 아카이브(삭제)한다."""
    try:
        client, err = _client()
        if err:
            return False
        page_id = task.get("notion_page_id") or _find_task_page(client, task["title"])
        if not page_id:
            return False
        client.pages.update(page_id=page_id, archived=True)
        return True
    except Exception as e:
        print(f"[notion_sync] task delete 실패: {e}")
        return False


# ── 목표(Goal) 동기화 → 메모/보고서 저장 하위 페이지 ──────────

def sync_goal_add(goal: dict) -> Optional[str]:
    """커리어 목표를 Notion 메모/보고서 저장 페이지에 추가한다."""
    try:
        from tools.notion_tools import save_rich_page
        lines = [
            "# " + goal["title"],
            "",
            "- 카테고리: " + goal.get("category", "general"),
            "- 마감일: " + (goal.get("deadline") or "미정"),
            "- 진행률: " + str(goal.get("progress", 0)) + "%",
            "- 상태: " + goal.get("status", "active"),
        ]
        if goal.get("milestones"):
            lines += ["", "## 마일스톤"]
            lines += ["- " + str(m) for m in goal["milestones"]]
        if goal.get("notes"):
            lines += ["", "## 메모", goal["notes"]]
        content = "\n".join(lines)
        result = save_rich_page(
            title="목표: " + goal["title"],
            content=content,
            category="other"
        )
        return result.get("page_id") if result.get("success") else None
    except Exception as e:
        print(f"[notion_sync] goal add 실패: {e}")
        return None


def sync_goal_update(goal: dict) -> bool:
    """Notion 목표 페이지에 진행률 업데이트 블록을 추가한다."""
    try:
        page_id = goal.get("notion_page_id")
        if not page_id:
            return False
        client, err = _client()
        if err:
            return False
        update_text = (
            "[" + datetime.now().strftime("%Y-%m-%d") + "] "
            + "진행률 " + str(goal.get("progress", 0)) + "% | "
            + "상태: " + goal.get("status", "active")
        )
        update_block = {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": update_text}}],
                "icon": {"type": "emoji", "emoji": "📊"}
            }
        }
        client.blocks.children.append(block_id=page_id, children=[update_block])
        return True
    except Exception as e:
        print(f"[notion_sync] goal update 실패: {e}")
        return False


# ── 스킬 동기화 → 메모/보고서 저장 하위 페이지 ───────────────

def sync_skill(skill: dict) -> Optional[str]:
    """스킬을 Notion 메모/보고서 저장 페이지에 저장한다."""
    try:
        from tools.notion_tools import save_rich_page
        lines = [
            "# " + skill["skill"],
            "",
            "- 레벨: " + skill.get("level", "beginner"),
            "- 기록일: " + datetime.now().strftime("%Y-%m-%d"),
        ]
        if skill.get("resource"):
            lines.append("- 참고 자료: " + skill["resource"])
        content = "\n".join(lines)
        result = save_rich_page(
            title="스킬: " + skill["skill"],
            content=content,
            category="other"
        )
        return result.get("page_id") if result.get("success") else None
    except Exception as e:
        print(f"[notion_sync] skill sync 실패: {e}")
        return None


# ── 메모(/remember) 동기화 → 메모/보고서 저장 하위 페이지 ──────

def sync_note(note_text: str, date: Optional[str] = None) -> Optional[str]:
    """메모를 Notion 메모/보고서 저장 페이지에 추가한다."""
    try:
        from tools.notion_tools import save_rich_page
        note_date = date or datetime.now().strftime("%Y-%m-%d")
        result = save_rich_page(
            title="메모 " + note_date,
            content=note_text,
            category="memo"
        )
        return result.get("page_id") if result.get("success") else None
    except Exception as e:
        print(f"[notion_sync] note sync 실패: {e}")
        return None
