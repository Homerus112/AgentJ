"""
tools/career_tools.py  —  Career Agent 통합 도구

구조:
  - Goals / Skills → 로컬 JSON (data/career.json)
  - Job Applications → Notion DB (NOTION_JOBS_DB_ID 설정 시)
                       Notion 미설정 시 로컬 JSON 폴백
"""
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

CAREER_FILE = Path(os.getenv("CAREER_FILE", "data/career.json"))


# ──────────────────────────────────────────────────────────
# 로컬 JSON 헬퍼
# ──────────────────────────────────────────────────────────

def _load():
    if CAREER_FILE.exists():
        return json.loads(CAREER_FILE.read_text(encoding="utf-8"))
    return {"goals": [], "applications": [], "skills": [],
            "next_goal_id": 1, "next_app_id": 1}


def _save(data):
    CAREER_FILE.parent.mkdir(parents=True, exist_ok=True)
    CAREER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ──────────────────────────────────────────────────────────
# Goals (로컬 JSON)
# ──────────────────────────────────────────────────────────

def add_goal(title: str, category: str = "general", deadline: str = "",
             milestones: list = None, notes: str = "") -> dict:
    """커리어 목표를 추가한다. category: job_search/skill/project/education/general"""
    data = _load()
    goal = {
        "id": data["next_goal_id"], "title": title, "category": category,
        "deadline": deadline, "milestones": milestones or [],
        "notes": notes, "progress": 0, "status": "active",
        "created_at": datetime.now().isoformat(),
        "notion_page_id": None,
    }
    data["goals"].append(goal)
    data["next_goal_id"] += 1
    _save(data)
    # Notion 자동 동기화
    try:
        from tools.notion_sync import sync_goal_add
        page_id = sync_goal_add(goal)
        if page_id:
            goal["notion_page_id"] = page_id
            _save(data)
    except Exception:
        pass
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
                goal.setdefault("updates", []).append(
                    {"note": note, "date": datetime.now().isoformat(), "progress": progress}
                )
            if progress >= 100:
                goal["status"] = "completed"
            _save(data)
            # Notion 자동 동기화
            try:
                from tools.notion_sync import sync_goal_update
                sync_goal_update(goal)
            except Exception:
                pass
            return {"success": True, "message": f"진행률 업데이트: {progress}%", "goal": goal}
    return {"success": False, "error": f"ID {goal_id} 목표를 찾을 수 없음"}


# ──────────────────────────────────────────────────────────
# Skills (로컬 JSON)
# ──────────────────────────────────────────────────────────

def add_skill(skill: str, level: str = "beginner", resource: str = "") -> dict:
    """스킬을 추가하거나 레벨을 업데이트한다. level: beginner/intermediate/advanced/expert"""
    data = _load()
    existing = next((s for s in data["skills"] if s["skill"].lower() == skill.lower()), None)
    if existing:
        existing["level"] = level
        if resource:
            existing["resource"] = resource
        _save(data)
        # Notion 자동 동기화 (업데이트)
        try:
            from tools.notion_sync import sync_skill
            sync_skill(existing)
        except Exception:
            pass
        return {"success": True, "message": f"스킬 업데이트: {skill} -> {level}"}
    skill_entry = {
        "skill": skill, "level": level, "resource": resource,
        "added_at": datetime.now().isoformat()
    }
    data["skills"].append(skill_entry)
    _save(data)
    # Notion 자동 동기화 (추가)
    try:
        from tools.notion_sync import sync_skill
        sync_skill(skill_entry)
    except Exception:
        pass
    return {"success": True, "message": f"스킬 추가: {skill} ({level})"}


def list_skills() -> dict:
    """스킬 목록을 조회한다."""
    data = _load()
    level_order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    skills = sorted(data["skills"], key=lambda s: level_order.get(s["level"], 4))
    return {"success": True, "count": len(skills), "skills": skills}


# ──────────────────────────────────────────────────────────
# Job Applications — Notion 우선, 로컬 JSON 폴백
# ──────────────────────────────────────────────────────────

def _notion_client():
    """Notion 클라이언트를 반환한다. 설정이 없으면 None."""
    api_key = os.getenv("NOTION_API_KEY")
    db_id   = os.getenv("NOTION_JOBS_DB_ID")
    if not api_key or not db_id:
        return None, None
    try:
        from notion_client import Client
        return Client(auth=api_key), db_id
    except ImportError:
        return None, None


def add_job_application(company: str, role: str, status: str = "Applied",
                        applied_date: str = None, link: str = "", notes: str = "") -> dict:
    """채용 지원 내역을 추가한다 (Notion 우선, 폴백 로컬 JSON)."""
    notion, db_id = _notion_client()
    if notion and db_id:
        try:
            date_str = applied_date or datetime.now().strftime("%Y-%m-%d")
            props = {
                "Company":      {"title":     [{"text": {"content": company}}]},
                "Role":         {"rich_text": [{"text": {"content": role}}]},
                "Status":       {"select":    {"name": status}},
                "Applied Date": {"date":      {"start": date_str}},
            }
            if link:
                props["Link"] = {"url": link}
            if notes:
                props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
            page = notion.pages.create(parent={"database_id": db_id}, properties=props)
            return {"success": True, "company": company, "role": role,
                    "status": status, "url": page.get("url", ""), "storage": "notion"}
        except Exception as e:
            pass  # Notion 실패 → 로컬 폴백

    # 로컬 JSON 폴백
    return add_application(company=company, role=role, status=status,
                           applied_date=applied_date or "", notes=notes)


def get_job_applications(status_filter: str = None) -> list:
    """채용 지원 목록을 조회한다 (Notion 우선, 폴백 로컬 JSON)."""
    notion, db_id = _notion_client()
    if notion and db_id:
        try:
            params = {
                "database_id": db_id,
                "sorts": [{"property": "Applied Date", "direction": "descending"}]
            }
            if status_filter:
                params["filter"] = {"property": "Status", "select": {"equals": status_filter}}
            results = notion.databases.query(**params).get("results", [])
            jobs = []
            for page in results:
                props = page.get("properties", {})
                def _txt(key):
                    t = props.get(key, {}).get("title") or props.get(key, {}).get("rich_text", [])
                    return t[0].get("text", {}).get("content", "") if t else ""
                status_obj = props.get("Status", {}).get("select") or {}
                date_obj   = props.get("Applied Date", {}).get("date") or {}
                jobs.append({
                    "company":      _txt("Company"),
                    "role":         _txt("Role"),
                    "status":       status_obj.get("name", ""),
                    "applied_date": date_obj.get("start", ""),
                    "url":          page.get("url", ""),
                })
            return jobs
        except Exception:
            pass

    # 로컬 폴백
    data = _load()
    apps = data["applications"]
    if status_filter:
        apps = [a for a in apps if a["status"] == status_filter]
    return apps


def update_job_status(company: str, new_status: str) -> dict:
    """회사명으로 지원 상태를 업데이트한다 (Notion 우선, 폴백 로컬 JSON)."""
    notion, db_id = _notion_client()
    if notion and db_id:
        try:
            results = notion.databases.query(
                database_id=db_id,
                filter={"property": "Company", "title": {"contains": company}}
            ).get("results", [])
            if not results:
                return {"success": False, "error": f"'{company}' 지원 내역 없음"}
            notion.pages.update(
                page_id=results[0]["id"],
                properties={"Status": {"select": {"name": new_status}}}
            )
            return {"success": True, "company": company, "new_status": new_status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # 로컬 폴백
    data = _load()
    for app in data["applications"]:
        if company.lower() in app["company"].lower():
            app["status"] = new_status
            app["history"].append({"status": new_status, "date": datetime.now().isoformat()})
            _save(data)
            return {"success": True, "company": company, "new_status": new_status}
    return {"success": False, "error": f"'{company}' 지원 내역 없음 (로컬)"}


def format_jobs_summary(jobs: list) -> str:
    """채용 현황 텍스트 포맷"""
    if not jobs:
        return "등록된 지원 내역이 없어요."
    STATUS_EMOJI = {"Applied": "📤", "Interview": "🎤", "Offer": "🎉", "Rejected": "❌"}
    groups = {}
    for j in jobs:
        groups.setdefault(j["status"] or "Unknown", []).append(j)
    lines = [f"📋 **채용 지원 현황** (총 {len(jobs)}개)\n"]
    for s, group in groups.items():
        lines.append(f"{STATUS_EMOJI.get(s, '📌')} **{s}** ({len(group)}개)")
        for j in group:
            lines.append(f"  • {j['company']} — {j['role']} ({j['applied_date']})")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# 로컬 JSON 전용 application 함수 (내부 폴백용)
# ──────────────────────────────────────────────────────────

def add_application(company: str, role: str, status: str = "applied",
                    applied_date: str = "", notes: str = "") -> dict:
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
    return {"success": True, "message": f"지원 추가: {company} - {role}", "application": app, "storage": "local"}


def list_applications(status: str = "all") -> dict:
    data = _load()
    apps = data["applications"]
    if status != "all":
        apps = [a for a in apps if a["status"] == status]
    return {"success": True, "count": len(apps), "applications": apps}


def update_application(company: str = "", app_id: int = None,
                       status: str = "", notes: str = "") -> dict:
    if company:
        return update_job_status(company, status)
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


# ──────────────────────────────────────────────────────────
# Claude Tool 스키마 정의
# ──────────────────────────────────────────────────────────

CAREER_TOOLS = [
    {
        "name": "add_goal",
        "description": "커리어 목표를 추가한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":      {"type": "string", "description": "목표 제목"},
                "category":   {"type": "string", "enum": ["job_search","skill","project","education","general"]},
                "deadline":   {"type": "string", "description": "목표 기한 (YYYY-MM-DD)"},
                "milestones": {"type": "array", "items": {"type": "string"}},
                "notes":      {"type": "string"}
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
                "status":   {"type": "string", "enum": ["active","completed","all"]},
                "category": {"type": "string"}
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
                "goal_id":  {"type": "integer"},
                "progress": {"type": "integer"},
                "note":     {"type": "string"}
            },
            "required": ["goal_id", "progress"]
        }
    },
    {
        "name": "add_job_application",
        "description": "채용 지원 내역을 추가한다 (Notion 저장).",
        "input_schema": {
            "type": "object",
            "properties": {
                "company":      {"type": "string"},
                "role":         {"type": "string"},
                "status":       {"type": "string", "enum": ["Applied","Interview","Offer","Rejected"], "default": "Applied"},
                "applied_date": {"type": "string", "description": "YYYY-MM-DD"},
                "link":         {"type": "string"},
                "notes":        {"type": "string"}
            },
            "required": ["company", "role"]
        }
    },
    {
        "name": "get_job_applications",
        "description": "채용 지원 목록을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {"type": "string", "description": "Applied/Interview/Offer/Rejected"}
            },
            "required": []
        }
    },
    {
        "name": "update_job_status",
        "description": "회사명으로 지원 상태를 업데이트한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company":    {"type": "string"},
                "new_status": {"type": "string", "enum": ["Applied","Interview","Offer","Rejected"]}
            },
            "required": ["company", "new_status"]
        }
    },
    {
        "name": "add_skill",
        "description": "스킬을 추가하거나 레벨을 업데이트한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill":    {"type": "string"},
                "level":    {"type": "string", "enum": ["beginner","intermediate","advanced","expert"]},
                "resource": {"type": "string"}
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


# ──────────────────────────────────────────────────────────
# Tool Executor (CareerAgent에서 호출)
# ──────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "add_goal":            add_goal,
        "list_goals":          list_goals,
        "update_goal_progress": update_goal_progress,
        "add_job_application": add_job_application,
        "get_job_applications": lambda **kw: {"success": True, "applications": get_job_applications(kw.get("status_filter"))},
        "update_job_status":   update_job_status,
        "add_skill":           add_skill,
        "list_skills":         list_skills,
        # 하위 호환 (구 tool명)
        "add_application":     lambda **kw: add_job_application(
                                   company=kw.get("company",""), role=kw.get("role",""),
                                   status=kw.get("status","Applied"), applied_date=kw.get("applied_date"),
                                   notes=kw.get("notes","")),
        "list_applications":   lambda **kw: {"success": True, "applications": get_job_applications(
                                   kw.get("status") if kw.get("status") != "all" else None)},
        "update_application":  update_application,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    try:
        result = tool_map[tool_name](**tool_input)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
