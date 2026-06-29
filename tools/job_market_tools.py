"""job_market_tools.py — 취업 시장 분석 도구"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def get_job_applications() -> list:
    """지원 현황 조회"""
    career_path = DATA_DIR / "career.json"
    if career_path.exists():
        try:
            career = json.loads(career_path.read_text(encoding='utf-8'))
            return career.get('applications', [])
        except: pass
    return []

def get_jobs_by_status(status: str) -> list:
    return [j for j in get_job_applications() if j.get('status') == status]

def add_job_application(company: str, role: str, status: str = 'applied') -> bool:
    """지원 기록 추가"""
    career_path = DATA_DIR / "career.json"
    try:
        career = json.loads(career_path.read_text(encoding='utf-8')) if career_path.exists() else {}
        apps   = career.get('applications', [])
        apps.append({"company": company, "role": role, "status": status})
        career['applications'] = apps
        career_path.write_text(json.dumps(career, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except: return False

def get_market_summary() -> str:
    apps = get_job_applications()
    if not apps: return "지원 기록이 없습니다."
    by_status = {}
    for a in apps:
        s = a.get('status', 'unknown')
        by_status[s] = by_status.get(s, 0) + 1
    lines = [f"총 {len(apps)}개 포지션 지원"]
    for s, c in by_status.items():
        lines.append(f"  {s}: {c}개")
    return "\n".join(lines)
