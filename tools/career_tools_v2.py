"""
tools/career_tools_v2.py
Job Application Tracker — Notion DB 연동 버전
기존 career_tools.py에 추가할 함수들 (기존 파일에 병합하세요)
"""

import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def add_job_application(
    company: str,
    role: str,
    status: str = "Applied",
    applied_date: str = None,
    link: str = "",
    notes: str = ""
) -> dict:
    """채용 지원 내역을 Notion DB에 추가"""
    try:
        from notion_client import Client
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        jobs_db_id = os.getenv("NOTION_JOBS_DB_ID")

        if not jobs_db_id:
            return {"success": False, "error": "NOTION_JOBS_DB_ID 미설정"}

        date_str = applied_date or datetime.now().strftime("%Y-%m-%d")

        properties = {
            "Company": {"title": [{"text": {"content": company}}]},
            "Role": {"rich_text": [{"text": {"content": role}}]},
            "Status": {"select": {"name": status}},
            "Applied Date": {"date": {"start": date_str}},
        }
        if link:
            properties["Link"] = {"url": link}
        if notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": notes}}]}

        page = notion.pages.create(
            parent={"database_id": jobs_db_id},
            properties=properties
        )
        return {
            "success": True,
            "company": company,
            "role": role,
            "status": status,
            "url": page.get("url", "")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_job_applications(status_filter: str = None) -> list:
    """채용 지원 목록 조회"""
    try:
        from notion_client import Client
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        jobs_db_id = os.getenv("NOTION_JOBS_DB_ID")

        if not jobs_db_id:
            return []

        query_params = {"database_id": jobs_db_id, "sorts": [{"property": "Applied Date", "direction": "descending"}]}

        if status_filter:
            query_params["filter"] = {"property": "Status", "select": {"equals": status_filter}}

        results = notion.databases.query(**query_params).get("results", [])

        jobs = []
        for page in results:
            props = page.get("properties", {})
            company = props.get("Company", {}).get("title", [{}])
            company_name = company[0].get("text", {}).get("content", "") if company else ""
            role_rt = props.get("Role", {}).get("rich_text", [{}])
            role_name = role_rt[0].get("text", {}).get("content", "") if role_rt else ""
            status = props.get("Status", {}).get("select", {})
            status_name = status.get("name", "") if status else ""
            date = props.get("Applied Date", {}).get("date", {})
            date_str = date.get("start", "") if date else ""

            jobs.append({
                "company": company_name,
                "role": role_name,
                "status": status_name,
                "applied_date": date_str,
                "url": page.get("url", "")
            })

        return jobs
    except Exception as e:
        return []


def update_job_status(company: str, new_status: str) -> dict:
    """회사명으로 지원 상태 업데이트"""
    try:
        from notion_client import Client
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        jobs_db_id = os.getenv("NOTION_JOBS_DB_ID")

        if not jobs_db_id:
            return {"success": False, "error": "NOTION_JOBS_DB_ID 미설정"}

        results = notion.databases.query(
            database_id=jobs_db_id,
            filter={"property": "Company", "title": {"contains": company}}
        ).get("results", [])

        if not results:
            return {"success": False, "error": f"'{company}' 지원 내역 없음"}

        page_id = results[0]["id"]
        notion.pages.update(
            page_id=page_id,
            properties={"Status": {"select": {"name": new_status}}}
        )
        return {"success": True, "company": company, "new_status": new_status}

    except Exception as e:
        return {"success": False, "error": str(e)}


def format_jobs_summary(jobs: list) -> str:
    """채용 현황 텍스트 포맷"""
    if not jobs:
        return "등록된 지원 내역이 없어요."

    status_groups = {}
    for job in jobs:
        s = job["status"] or "Unknown"
        status_groups.setdefault(s, []).append(job)

    STATUS_EMOJI = {
        "Applied": "📤", "Interview": "🎤", "Offer": "🎉", "Rejected": "❌"
    }

    lines = [f"📋 **채용 지원 현황** (총 {len(jobs)}개)\n"]
    for status, group in status_groups.items():
        emoji = STATUS_EMOJI.get(status, "📌")
        lines.append(f"{emoji} **{status}** ({len(group)}개)")
        for j in group:
            lines.append(f"  • {j['company']} — {j['role']} ({j['applied_date']})")
        lines.append("")

    return "\n".join(lines)
