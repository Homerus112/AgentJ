"""
career_tools.py - Career Agent용 목표/지원/스킬 관리 도구
"""
import json, os
from pathlib import Path
from datetime import datetime

CAREER_FILE = Path(os.getenv("CAREER_FILE", "data/career.json"))


def _load():
    if CAREER_FILE.exists():
        return json.loads(CAREER_FILE.read_text(encoding="utf-8"))
    return {"goals": [], "applications": [], "skills": [], "next_goal_id": 1, "next_app_id": 1}


def _save(data):
    CAREER_FILE.parent.mkdir(parents=True, exist_ok=True)
    CAREER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_goal(title: str, category: str = "general", deadline: str = "", milestones: list = None, notes: str = "") -> dict:
    """커리어 목표를 추가한다. category: job_search / skill / project / education / general"""
    data = _load()
    goal = {
        "id": data["next_goal_id"], "title": title, "category": category,
        "deadline": deadline, "milestones": milestones or [],
        "notes": notes, "progress": 0, "status": "active",
        "created_at": datetime.now().isoformat()
    }
    data["goals"].append(goal)
    data["next_goal_id"] += 1
    _save(data)
    return {"success": True, "message": f"목표 추가: [{goal['id']}] {title}", "goal": goal}


def list_goals(status: str = "active", category: str = "all") -> dict:
    """목표 목록을 조회한다."""
    data = _load()
    goals = data["goals"]
    if status != "all":
        goals = [g for g in goals if g["status"] == status]
    if category != "all":
        goals = [g for g in goals if g["category"] == category]
    return {"success": True, "count": len(goals), "goals": goals}


def update_goal_progress(goal_id: int, progress: int, note: str = "") -> dict:
    """목표 진행률을 업데이트한다 (0-100)."""
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            goal["progress"] = max(0, min(100, progress))
            if note:
                goal.setdefault("updates", []).append({"note": note, "date": datetime.now().isoformat(), "progress": progress})
            if progress >= 100:
                goal["status"] = "completed"
            _save(data)
            return {"success": True, "message": f"진행률 업데이트: {progress}%", "goal": goal}
    return {"success": False, "error": f"ID {goal_id} 목표를 찾을 수 없음"}


def add_application(company: str, role: str, status: str = "applied", applied_date: str = "", notes: str = "") -> dict:
    """취업 지원 내역을 추가한다. status: wishlist/applied/phone_screen/interview/offer/rejected"""
    data = _load()
    app = {
        "id": data["next_app_id"], "company": company, "role": role,
        "status": status, "applied_date": applied_date or datetime.now().strftime("%Y-%m-%d"),
        "notes": notes, "history": [{"status": status, "date": datetime.now().isoformat()}],
        "created_at": datetime.now().isoformat()
    }
    data["applications"].append(app)
    data["next_app_id"] += 1
    _save(data)
    return {"success": True, "message": f"지원 추가: {company} - {role}", "application": app}


def list_applications(status: str = "all") -> dict:
    """지원 내역을 조회한다."""
    data = _load()
    apps = data["applications"]
    if status != "all":
        apps = [a for a in apps if a["status"] == status]
    return {"success": True, "count": len(apps), "applications": apps}


def update_application(app_id: int, status: str, notes: str = "") -> dict:
    """지원 상태를 업데이트한다."""
    data = _load()
    for app in data["applications"]:
        if app["id"] == app_id:
            app["status"] = status
            app["history"].append({"status": status, "date": datetime.now().isoformat(), "notes": notes})
            if notes:
                app["notes"] = notes
            _save(data)
            return {"success": True, "message": f"상태 업데이트: {app['company']} -> {status}"}
    return {"success": False, "error": f"ID {app_id} 지원 내역을 찾을 수 없음"}


def add_skill(skill: str, level: str = "beginner", resource: str = "") -> dict:
    """스킬을 추가한다. level: beginner/intermediate/advanced/expert"""
    data = _load()
    existing = next((s for s in data["skills"] if s["skill"].lower() == skill.lower()), None)
    if existing:
        existing["level"] = level
        if resource:
            existing["resource"] = resource
        _save(data)
        return {"success": True, "message": f"스킬 업데이트: {skill} -> {level}"}
    data["skills"].append({"skill": skill, "level": level, "resource": resource, "added_at": datetime.now().isoformat()})
    _save(data)
    return {"success": True, "message": f"스킬 추가: {skill} ({level})"}


def list_skills() -> dict:
    """스킬 목록을 조회한다."""
    data = _load()
    level_order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    skills = sorted(data["skills"], key=lambda s: level_order.get(s["level"], 4))
    return {"success": True, "count": len(skills), "skills": skills}


CAREER_TOOLS = [
    {
        "name": "add_goal",
        "description": "커리어 목표를 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":      {"type": "string", "description": "목표 제목"},
                "category":   {"type": "string", "enum": ["job_search","skill","project","education","general"], "description": "카테고리"},
                "deadline":   {"type": "string", "description": "목표 기한 (YYYY-MM-DD)"},
                "milestones": {"type": "array", "items": {"type": "string"}, "description": "중간 마일스톤 목록"},
                "notes":      {"type": "string", "description": "추가 메모"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_goals",
        "description": "커리어 목표 목록을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status":   {"type": "string", "enum": ["active","completed","all"], "description": "상태 필터"},
                "category": {"type": "string", "description": "카테고리 필터"}
            },
            "required": []
        }
    },
    {
        "name": "update_goal_progress",
        "description": "목표 진행률을 업데이트한다 (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id":  {"type": "integer", "description": "목표 ID"},
                "progress": {"type": "integer", "description": "진행률 (0-100)"},
                "note":     {"type": "string", "description": "업데이트 메모"}
            },
            "required": ["goal_id", "progress"]
        }
    },
    {
        "name": "add_application",
        "description": "취업 지원 내역을 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company":      {"type": "string", "description": "회사명"},
                "role":         {"type": "string", "description": "지원 포지션"},
                "status":       {"type": "string", "enum": ["wishlist","applied","phone_screen","interview","offer","rejected"], "description": "현재 상태"},
                "applied_date": {"type": "string", "description": "지원일 (YYYY-MM-DD)"},
                "notes":        {"type": "string", "description": "메모"}
            },
            "required": ["company", "role"]
        }
    },
    {
        "name": "list_applications",
        "description": "취업 지원 내역을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "상태 필터 (all/applied/interview/offer/rejected 등)"}
            },
            "required": []
        }
    },
    {
        "name": "update_application",
        "description": "취업 지원 상태를 업데이트한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {"type": "integer", "description": "지원 ID"},
                "status": {"type": "string", "description": "새 상태"},
                "notes":  {"type": "string", "description": "메모"}
            },
            "required": ["app_id", "status"]
        }
    },
    {
        "name": "add_skill",
        "description": "스킬을 추가하거나 레벨을 업데이트한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill":    {"type": "string", "description": "스킬명"},
                "level":    {"type": "string", "enum": ["beginner","intermediate","advanced","expert"], "description": "숙련도"},
                "resource": {"type": "string", "description": "학습 자료/링크"}
            },
            "required": ["skill"]
        }
    },
    {
        "name": "list_skills",
        "description": "스킬 목록을 조회한다.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "add_goal": add_goal, "list_goals": list_goals,
        "update_goal_progress": update_goal_progress,
        "add_application": add_application, "list_applications": list_applications,
        "update_application": update_application,
        "add_skill": add_skill, "list_skills": list_skills,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
