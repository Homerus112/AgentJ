"""
planner_tools.py
Planner Agent가 사용하는 할 일(Task) 및 일정(Schedule) 관리 도구
"""

import json
import os
from datetime import datetime
from pathlib import Path

# __file__ 기반 절대 경로 — CWD와 무관하게 동작 (PyInstaller frozen 환경 포함)
_BASE = Path(__file__).resolve().parent.parent
TASKS_FILE    = Path(os.getenv("TASKS_FILE",    str(_BASE / "data" / "tasks.json")))
SCHEDULE_FILE = Path(os.getenv("SCHEDULE_FILE", str(_BASE / "data" / "schedule.json")))


def _load_tasks() -> dict:
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    return {"tasks": [], "next_id": 1}


def _save_tasks(data: dict):
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_schedule() -> dict:
    if SCHEDULE_FILE.exists():
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    return {"events": []}


def _save_schedule(data: dict):
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# Task 관련 도구

def add_task(title: str, description: str = "", due_date: str = "", priority: str = "medium") -> dict:
    data = _load_tasks()
    task = {
        "id": data["next_id"],
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "notion_page_id": None,
    }
    data["tasks"].append(task)
    data["next_id"] += 1
    _save_tasks(data)

    # Notion 자동 동기화
    try:
        from tools.notion_sync import sync_task_add
        page_id = sync_task_add(task)
        if page_id:
            task["notion_page_id"] = page_id
            _save_tasks(data)   # notion_page_id 포함해서 재저장
    except Exception:
        pass

    return {"success": True, "message": f"할 일 추가: [{task['id']}] {title}", "task": task}


def list_tasks(filter_status: str = "all", filter_priority: str = "all") -> dict:
    data = _load_tasks()
    tasks = data["tasks"]
    if filter_status != "all":
        tasks = [t for t in tasks if t["status"] == filter_status]
    if filter_priority != "all":
        tasks = [t for t in tasks if t["priority"] == filter_priority]
    return {"success": True, "count": len(tasks), "tasks": tasks}


def complete_task(task_id: int) -> dict:
    data = _load_tasks()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = "done"
            task["completed_at"] = datetime.now().isoformat()
            _save_tasks(data)
            # Notion 자동 동기화
            try:
                from tools.notion_sync import sync_task_complete
                sync_task_complete(task)
            except Exception:
                pass
            return {"success": True, "message": f"완료 처리: [{task_id}] {task['title']}"}
    return {"success": False, "error": f"ID {task_id} 할 일을 찾을 수 없음"}


def delete_task(task_id: int) -> dict:
    data = _load_tasks()
    target = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if not target:
        return {"success": False, "error": f"ID {task_id} 할 일을 찾을 수 없음"}
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    _save_tasks(data)
    # Notion 자동 동기화 (아카이브)
    try:
        from tools.notion_sync import sync_task_delete
        sync_task_delete(target)
    except Exception:
        pass
    return {"success": True, "message": f"삭제 완료: ID {task_id}"}


def update_task(task_id: int, title: str = None, description: str = None,
                due_date: str = None, priority: str = None) -> dict:
    data = _load_tasks()
    for task in data["tasks"]:
        if task["id"] == task_id:
            if title is not None: task["title"] = title
            if description is not None: task["description"] = description
            if due_date is not None: task["due_date"] = due_date
            if priority is not None: task["priority"] = priority
            task["updated_at"] = datetime.now().isoformat()
            _save_tasks(data)
            # Notion 자동 동기화
            try:
                from tools.notion_sync import sync_task_update
                sync_task_update(task)
            except Exception:
                pass
            return {"success": True, "message": f"수정 완료: [{task_id}]", "task": task}
    return {"success": False, "error": f"ID {task_id} 할 일을 찾을 수 없음"}


# Schedule 관련 도구

def add_event(title: str, date: str, time: str = "", description: str = "") -> dict:
    """일정을 추가한다. 로컬 저장 후 Google Calendar에도 자동 동기화."""
    # 1. 로컬 저장
    data = _load_schedule()
    event = {
        "id": len(data["events"]) + 1,
        "title": title,
        "date": date,
        "time": time,
        "description": description,
        "created_at": datetime.now().isoformat()
    }
    data["events"].append(event)
    _save_schedule(data)

    # 2. Google Calendar 자동 동기화
    gcal_result = None
    try:
        from tools.gcal_tools import create_event
        t = time if time else "09:00"
        start_dt = f"{date}T{t}:00+09:00"
        h, m = int(t.split(":")[0]), int(t.split(":")[1])
        end_h = (h + 1) % 24
        end_dt = f"{date}T{end_h:02d}:{m:02d}:00+09:00"
        gcal_result = create_event(title=title, start_datetime=start_dt,
                                   end_datetime=end_dt, description=description)
    except Exception as e:
        gcal_result = {"success": False, "error": str(e)}

    if gcal_result and gcal_result.get("success"):
        gcal_msg = "Google Calendar 동기화 완료"
    else:
        err = gcal_result.get("error", "알 수 없음") if gcal_result else "알 수 없음"
        gcal_msg = f"Google Calendar 동기화 실패: {err}"

    return {"success": True, "message": f"일정 추가: {date} {time} {title} / {gcal_msg}", "event": event}


def list_schedule(date_from: str = "", date_to: str = "") -> dict:
    data = _load_schedule()
    events = sorted(data["events"], key=lambda e: (e["date"], e.get("time", "")))
    if date_from:
        events = [e for e in events if e["date"] >= date_from]
    if date_to:
        events = [e for e in events if e["date"] <= date_to]
    return {"success": True, "count": len(events), "events": events}


def delete_event(event_id: int) -> dict:
    data = _load_schedule()
    before = len(data["events"])
    data["events"] = [e for e in data["events"] if e["id"] != event_id]
    if len(data["events"]) == before:
        return {"success": False, "error": f"ID {event_id} 일정을 찾을 수 없음"}
    _save_schedule(data)
    return {"success": True, "message": f"삭제 완료: ID {event_id}"}


# 툴 스키마 등록

PLANNER_TOOLS = [
    {
        "name": "add_task",
        "description": "새 할 일(To-do)을 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "할 일 제목"},
                "description": {"type": "string", "description": "세부 설명"},
                "due_date": {"type": "string", "description": "마감일 (YYYY-MM-DD 형식)"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "우선순위"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_tasks",
        "description": "할 일 목록을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_status": {"type": "string", "enum": ["all", "pending", "done"]},
                "filter_priority": {"type": "string", "enum": ["all", "high", "medium", "low"]}
            },
            "required": []
        }
    },
    {
        "name": "complete_task",
        "description": "할 일을 완료 처리한다.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer", "description": "완료할 할 일의 ID"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "할 일을 삭제한다.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer", "description": "삭제할 할 일의 ID"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "update_task",
        "description": "기존 할 일의 내용을 수정한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "수정할 할 일의 ID"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "due_date": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "add_event",
        "description": "캘린더에 새 일정을 추가한다. 로컬과 Google Calendar에 동시 저장.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "일정 제목"},
                "date": {"type": "string", "description": "날짜 (YYYY-MM-DD)"},
                "time": {"type": "string", "description": "시간 (HH:MM, 선택)"},
                "description": {"type": "string", "description": "세부 내용"}
            },
            "required": ["title", "date"]
        }
    },
    {
        "name": "list_schedule",
        "description": "일정 목록을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "조회 시작일 (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "조회 종료일 (YYYY-MM-DD)"}
            },
            "required": []
        }
    },
    {
        "name": "delete_event",
        "description": "일정을 삭제한다.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "integer", "description": "삭제할 일정의 ID"}},
            "required": ["event_id"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "add_task": add_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task,
        "delete_task": delete_task,
        "update_task": update_task,
        "add_event": add_event,
        "list_schedule": list_schedule,
        "delete_event": delete_event
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": "알 수 없는 툴: " + tool_name})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
