"""
tools/github_tools.py — GitHub → 커리어 자동 기록 파이프라인 (Feature 2)

기능:
  1. GitHub API로 최근 커밋/PR/이벤트 수집
  2. LLM으로 기술 활동 → 커리어 임팩트 문장 변환
  3. career.json + Notion에 자동 반영
  4. 스킬 자동 감지 및 업데이트

필요 환경변수:
  GITHUB_TOKEN   — GitHub Personal Access Token (read:user, repo)
  GITHUB_USERNAME — 본인 GitHub 유저명
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    """GitHub API 요청 헤더 반환."""
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ─────────────────────────────────────────────
# 1. GitHub 데이터 수집
# ─────────────────────────────────────────────

def get_recent_events(username: str = None, days: int = 7) -> dict:
    """
    사용자의 최근 GitHub 이벤트(커밋, PR, 이슈)를 가져온다.
    Args:
        username: GitHub 유저명 (없으면 .env의 GITHUB_USERNAME)
        days: 최근 며칠치 데이터
    Returns:
        {"success": True, "commits", "prs", "repos_touched", "languages"}
    """
    if not REQUESTS_AVAILABLE:
        return {"success": False, "error": "requests 미설치"}

    username = username or os.getenv("GITHUB_USERNAME", "")
    if not username:
        return {"success": False, "error": "GITHUB_USERNAME이 .env에 없습니다"}

    cutoff = (datetime.now() - timedelta(days=days)).isoformat() + "Z"

    try:
        # 공개 이벤트 가져오기
        resp = requests.get(
            f"{GITHUB_API}/users/{username}/events",
            headers=_headers(), params={"per_page": 100}, timeout=10
        )
        resp.raise_for_status()
        events = resp.json()

        commits = []
        prs = []
        repos_touched = set()
        languages = set()

        for event in events:
            created_at = event.get("created_at", "")
            if created_at < cutoff:
                continue

            repo_name = event.get("repo", {}).get("name", "")
            repos_touched.add(repo_name)

            if event["type"] == "PushEvent":
                payload = event.get("payload", {})
                for commit in payload.get("commits", []):
                    msg = commit.get("message", "").split("\n")[0]  # 첫 줄만
                    if msg and not msg.lower().startswith("merge"):
                        commits.append({
                            "message": msg,
                            "repo": repo_name,
                            "date": created_at[:10],
                        })

            elif event["type"] == "PullRequestEvent":
                pr = event.get("payload", {}).get("pull_request", {})
                if event["payload"].get("action") in ("opened", "closed", "merged"):
                    prs.append({
                        "title": pr.get("title", ""),
                        "state": pr.get("state", ""),
                        "merged": pr.get("merged", False),
                        "repo": repo_name,
                        "date": created_at[:10],
                        "additions": pr.get("additions", 0),
                        "deletions": pr.get("deletions", 0),
                    })

        # 주요 레포 언어 감지 (최대 5개)
        for repo in list(repos_touched)[:5]:
            try:
                lang_resp = requests.get(
                    f"{GITHUB_API}/repos/{repo}/languages",
                    headers=_headers(), timeout=5
                )
                if lang_resp.ok:
                    languages.update(lang_resp.json().keys())
            except Exception:
                pass

        return {
            "success": True,
            "username": username,
            "period_days": days,
            "commits": commits[:30],          # 최대 30개
            "prs": prs[:10],                  # 최대 10개
            "repos_touched": list(repos_touched),
            "languages_detected": list(languages),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_repo_summary(repo_full_name: str) -> dict:
    """
    특정 레포지토리 정보를 가져온다.
    Args:
        repo_full_name: "username/repo-name" 형태
    """
    if not REQUESTS_AVAILABLE:
        return {"success": False, "error": "requests 미설치"}
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{repo_full_name}",
            headers=_headers(), timeout=10
        )
        resp.raise_for_status()
        r = resp.json()
        return {
            "success": True,
            "name": r.get("name", ""),
            "description": r.get("description", ""),
            "language": r.get("language", ""),
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "topics": r.get("topics", []),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# 2. 커밋 → 커리어 임팩트 변환 (LLM)
# ─────────────────────────────────────────────

def generate_impact_statements(events: dict, model: str = None) -> list:
    """
    GitHub 활동 데이터를 커리어 임팩트 문장으로 변환한다.
    Args:
        events: get_recent_events() 반환값
        model:  사용할 Claude 모델 (기본: haiku)
    Returns:
        [{"statement": str, "category": str, "skills": [str]}]
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = model or os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

        commits = events.get("commits", [])
        prs = events.get("prs", [])
        repos = events.get("repos_touched", [])
        langs = events.get("languages_detected", [])

        if not commits and not prs:
            return []

        # 데이터 요약 텍스트 생성
        commit_lines = "\n".join([f"- [{c['repo']}] {c['message']}" for c in commits[:15]])
        pr_lines = "\n".join([
            f"- [{p['repo']}] {p['title']} ({'merged' if p['merged'] else p['state']}, +{p['additions']}/-{p['deletions']})"
            for p in prs[:5]
        ])

        prompt = f"""아래는 최근 {events.get('period_days', 7)}일간의 GitHub 활동입니다.

## 커밋 메시지
{commit_lines or '없음'}

## Pull Requests
{pr_lines or '없음'}

## 관련 기술/언어
{', '.join(langs) if langs else '미감지'}

이 활동들을 이력서/포트폴리오에 쓸 수 있는 임팩트 문장으로 변환해줘.
- 최대 3~5개 문장
- 구체적 수치나 기술명 포함
- "~를 구현함", "~를 최적화해 X% 개선" 형식
- 다음 JSON 배열로만 응답 (다른 텍스트 없이):
[{{"statement": "임팩트 문장", "category": "dev|data|infra|other", "skills": ["Python", "React", ...]}}]"""

        resp = client.messages.create(
            model=model, max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip()
        # JSON 추출
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        return [{"statement": f"오류: {e}", "category": "other", "skills": []}]


# ─────────────────────────────────────────────
# 3. career.json + Notion 자동 반영
# ─────────────────────────────────────────────

def sync_github_to_career(username: str = None, days: int = 7) -> dict:
    """
    GitHub 활동을 분석해 career.json의 스킬/목표에 자동 반영하고
    Notion에 활동 요약 페이지를 저장한다.
    Args:
        username: GitHub 유저명
        days: 분석할 기간 (일)
    Returns:
        {"success": True, "impact_statements", "skills_updated", "notion_url"}
    """
    # 1. 이벤트 수집
    events = get_recent_events(username=username, days=days)
    if not events.get("success"):
        return events

    # 2. 임팩트 문장 생성
    impacts = generate_impact_statements(events)

    # 3. 감지된 언어/스킬 → career.json 자동 업데이트
    skills_updated = []
    detected_langs = events.get("languages_detected", [])
    # 알려진 언어를 스킬로 매핑
    LANG_LEVEL_MAP = {
        "Python": "advanced", "JavaScript": "intermediate", "TypeScript": "intermediate",
        "Rust": "beginner", "Go": "beginner", "Java": "intermediate",
        "C++": "intermediate", "Swift": "beginner", "Kotlin": "beginner",
    }
    try:
        from tools.career_tools import add_skill
        for lang in detected_langs:
            level = LANG_LEVEL_MAP.get(lang, "intermediate")
            add_skill(skill=lang, level=level, resource="GitHub 활동 자동 감지")
            skills_updated.append(lang)
    except Exception:
        pass

    # 4. Notion에 GitHub 활동 요약 저장
    notion_url = ""
    try:
        from tools.notion_tools import save_rich_page
        date_str = datetime.now().strftime("%Y-%m-%d")
        content_lines = [
            f"## GitHub 활동 요약 ({date_str})",
            f"- 기간: 최근 {days}일",
            f"- 커밋: {len(events.get('commits', []))}개",
            f"- PR: {len(events.get('prs', []))}개",
            f"- 작업한 레포: {', '.join(events.get('repos_touched', [])[:5])}",
            f"- 감지된 기술: {', '.join(detected_langs)}",
            "",
            "## 커리어 임팩트 문장",
        ]
        for imp in impacts:
            content_lines.append(f"- {imp.get('statement', '')}")
            if imp.get("skills"):
                content_lines.append(f"  - 기술: {', '.join(imp['skills'])}")

        result = save_rich_page(
            title=f"GitHub 활동 — {date_str}",
            content="\n".join(content_lines),
            category="other"
        )
        notion_url = result.get("url", "")
    except Exception:
        pass

    return {
        "success": True,
        "username": events.get("username"),
        "commits_analyzed": len(events.get("commits", [])),
        "prs_analyzed": len(events.get("prs", [])),
        "impact_statements": impacts,
        "skills_updated": skills_updated,
        "notion_url": notion_url,
    }


# ─────────────────────────────────────────────
# Claude Tool 스키마
# ─────────────────────────────────────────────

GITHUB_TOOLS = [
    {
        "name": "get_recent_events",
        "description": "GitHub에서 최근 커밋/PR/이벤트를 가져온다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "GitHub 유저명 (없으면 .env 설정값)"},
                "days":     {"type": "integer", "description": "최근 며칠치 (기본 7)"}
            },
            "required": []
        }
    },
    {
        "name": "sync_github_to_career",
        "description": "GitHub 활동을 분석해 커리어 임팩트 문장을 생성하고 Notion에 저장한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "days":     {"type": "integer", "description": "분석 기간 (기본 7일)"}
            },
            "required": []
        }
    },
    {
        "name": "get_repo_summary",
        "description": "특정 GitHub 레포지토리의 정보를 가져온다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_full_name": {"type": "string", "description": "예: 'username/repo-name'"}
            },
            "required": ["repo_full_name"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """툴 실행 후 JSON 문자열 반환."""
    tool_map = {
        "get_recent_events":      get_recent_events,
        "sync_github_to_career":  sync_github_to_career,
        "get_repo_summary":       get_repo_summary,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    try:
        return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
