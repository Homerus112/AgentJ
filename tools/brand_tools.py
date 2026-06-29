"""brand_tools.py — 브랜드 콘텐츠 생성 도구"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def get_brand_context() -> str:
    """브랜딩에 활용할 컨텍스트 수집"""
    ctx_parts = []
    profile_path = DATA_DIR / "user_profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding='utf-8'))
            name  = profile.get('name', 'Jeremy')
            goals = profile.get('goals', [])
            skills = profile.get('skills', [])
            ctx_parts.append(f"이름: {name}")
            if goals:  ctx_parts.append(f"목표: {', '.join(str(g) for g in goals[:3])}")
            if skills: ctx_parts.append(f"스킬: {', '.join(str(s) for s in skills[:5])}")
        except: pass

    career_path = DATA_DIR / "career.json"
    if career_path.exists():
        try:
            career = json.loads(career_path.read_text(encoding='utf-8'))
            apps   = career.get('applications', [])
            if apps: ctx_parts.append(f"최근 지원: {len(apps)}개 포지션")
        except: pass

    return "\n".join(ctx_parts) if ctx_parts else ""

def format_linkedin_post(topic: str, content: str) -> str:
    return f"LinkedIn 포스트 — {topic}\n\n{content}"

def format_instagram_post(topic: str, content: str) -> str:
    return f"Instagram 포스트 — {topic}\n\n{content}"
