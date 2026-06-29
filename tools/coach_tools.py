"""
tools/coach_tools.py — 능동형 목표 코치 (Feature 4)

기능:
  1. 목표 드리프트 분석 (선언 vs 실제 행동 갭)
  2. 대화 패턴에서 행동 신호 추출
  3. 주간 현황 리포트 생성
  4. 구체적 개입 제안 + 과거 제안 추적

저장 구조 (data/coach_log.json):
  {"interventions": [...], "weekly_reviews": [...]}
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

COACH_FILE = Path(os.getenv("COACH_FILE", "data/coach_log.json"))


# ─────────────────────────────────────────────
# 로컬 저장소
# ─────────────────────────────────────────────

def _load() -> dict:
    if COACH_FILE.exists():
        return json.loads(COACH_FILE.read_text(encoding="utf-8"))
    return {"interventions": [], "weekly_reviews": []}


def _save(data: dict):
    COACH_FILE.parent.mkdir(parents=True, exist_ok=True)
    COACH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────
# 1. 목표 드리프트 분석
# ─────────────────────────────────────────────

def analyze_goal_drift() -> dict:
    """
    활성 목표의 진척률과 마감일을 분석해 드리프트(선언과 행동의 괴리)를 탐지한다.
    Returns:
        {"drifted": [...], "on_track": [...], "overdue": [...], "summary": str}
    """
    try:
        from tools.career_tools import list_goals
        goals_data = list_goals(status="active")
        goals = goals_data.get("goals", [])
    except Exception as e:
        return {"success": False, "error": str(e)}

    today = datetime.now().date()
    drifted = []
    on_track = []
    overdue = []

    for goal in goals:
        progress = goal.get("progress", 0)
        deadline_str = goal.get("deadline", "")
        created_str = goal.get("created_at", "")
        title = goal.get("title", "")

        # 기한 초과 체크
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                if deadline < today and progress < 100:
                    overdue.append({
                        "title": title,
                        "progress": progress,
                        "deadline": deadline_str,
                        "days_overdue": (today - deadline).days,
                    })
                    continue
            except ValueError:
                pass

        # 진척률 vs 경과 시간 비율 체크
        if created_str and deadline_str:
            try:
                created = datetime.fromisoformat(created_str).date()
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                total_days = (deadline - created).days
                elapsed_days = (today - created).days
                if total_days > 0:
                    expected_progress = min(100, int((elapsed_days / total_days) * 100))
                    actual_progress = progress
                    gap = expected_progress - actual_progress
                    if gap > 25:  # 기대 대비 25% 이상 뒤처짐
                        drifted.append({
                            "title": title,
                            "progress": actual_progress,
                            "expected": expected_progress,
                            "gap": gap,
                            "deadline": deadline_str,
                        })
                        continue
            except Exception:
                pass

        if progress < 20 and created_str:
            # 생성 후 7일 이상인데 진척률 20% 미만
            try:
                created = datetime.fromisoformat(created_str).date()
                days_since = (today - created).days
                if days_since >= 7:
                    drifted.append({
                        "title": title,
                        "progress": progress,
                        "expected": min(20, days_since * 2),
                        "gap": min(20, days_since * 2) - progress,
                        "deadline": deadline_str or "미설정",
                    })
                    continue
            except Exception:
                pass

        on_track.append({"title": title, "progress": progress, "deadline": deadline_str})

    summary_parts = []
    if overdue:
        summary_parts.append(f"⚠️ 기한 초과 {len(overdue)}개")
    if drifted:
        summary_parts.append(f"📉 드리프트 감지 {len(drifted)}개")
    if on_track:
        summary_parts.append(f"✅ 순항 중 {len(on_track)}개")

    return {
        "success": True,
        "overdue": overdue,
        "drifted": drifted,
        "on_track": on_track,
        "summary": " | ".join(summary_parts) if summary_parts else "목표 데이터 없음",
        "total_goals": len(goals),
    }


# ─────────────────────────────────────────────
# 2. 대화 패턴 행동 신호 분석
# ─────────────────────────────────────────────

def analyze_behavior_patterns(days: int = 14) -> dict:
    """
    최근 대화 히스토리에서 행동 패턴을 분석한다.
    - 어떤 에이전트를 많이 썼는지
    - 완료된 태스크 수
    - 자주 언급된 주제
    Returns:
        {"agent_usage", "task_activity", "topics", "insights"}
    """
    result = {}

    # 에이전트 사용 통계
    try:
        from memory.memory_manager import MemoryManager
        mm = MemoryManager()
        stats = mm.data.get("agent_stats", {})
        total = sum(stats.values()) or 1
        top_agents = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
        result["agent_usage"] = [
            {"agent": a, "count": c, "pct": round(c / total * 100)}
            for a, c in top_agents
        ]
    except Exception:
        result["agent_usage"] = []

    # 태스크 완료 활동
    try:
        from tools.planner_tools import load_data as _load_tasks
        data = _load_tasks()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        all_tasks = data.get("tasks", [])
        recent_completed = [t for t in all_tasks if t.get("status") == "done"
                            and t.get("updated_at", "") >= cutoff]
        pending_count = len([t for t in all_tasks if t.get("status") == "pending"])
        result["task_activity"] = {
            "completed_recent": len(recent_completed),
            "pending_now": pending_count,
            "completion_rate": round(len(recent_completed) / max(len(all_tasks), 1) * 100),
        }
    except Exception:
        result["task_activity"] = {}

    # 대화 히스토리에서 자주 언급된 주제 (간단한 키워드 빈도)
    try:
        from memory.memory_manager import MemoryManager
        mm = MemoryManager()
        history = mm.load_recent_history()
        user_msgs = " ".join([m["content"] for m in history if m["role"] == "user"])
        # 한국어 단어 빈도 (5자 이하 제외)
        words = re.findall(r'[가-힣]{3,}', user_msgs)
        freq = {}
        STOPWORDS = {"것이다", "그리고", "하지만", "있어서", "때문에", "이렇게", "그래서"}
        for w in words:
            if w not in STOPWORDS:
                freq[w] = freq.get(w, 0) + 1
        top_topics = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:8]
        result["topics"] = [{"word": w, "count": c} for w, c in top_topics]
    except Exception:
        result["topics"] = []

    # 행동 인사이트 생성
    insights = []
    agent_usage = result.get("agent_usage", [])
    task_act = result.get("task_activity", {})

    if agent_usage:
        top_agent = agent_usage[0]["agent"]
        if top_agent == "general":
            insights.append("주로 일반 대화 위주 — 구체적 목표 작업 비중이 낮아요")
        elif top_agent == "dev":
            insights.append("코딩 작업에 집중하고 있어요 — 커리어 목표와 연결되나요?")
        elif top_agent == "career":
            insights.append("커리어에 집중하고 있어요 — 좋은 신호!")

    if task_act:
        cr = task_act.get("completion_rate", 0)
        if cr < 30:
            insights.append(f"태스크 완료율이 {cr}%로 낮아요 — 태스크를 더 작게 쪼개보세요")
        elif cr > 70:
            insights.append(f"태스크 완료율 {cr}% — 훌륭한 실행력이에요!")

    result["insights"] = insights
    return {"success": True, **result}


# ─────────────────────────────────────────────
# 3. 주간 코치 리뷰 생성
# ─────────────────────────────────────────────

def generate_weekly_review() -> dict:
    """
    목표 드리프트 + 행동 패턴을 종합해 주간 코치 리뷰를 생성한다.
    LLM이 구체적 개입 제안을 만든다.
    Returns:
        {"review_text", "interventions", "saved": bool}
    """
    drift = analyze_goal_drift()
    behavior = analyze_behavior_patterns()

    # LLM으로 코치 메시지 생성
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

        drift_summary = json.dumps(drift, ensure_ascii=False, indent=2)
        behavior_summary = json.dumps({
            "agent_usage": behavior.get("agent_usage", []),
            "task_activity": behavior.get("task_activity", {}),
            "insights": behavior.get("insights", []),
        }, ensure_ascii=False, indent=2)

        prompt = f"""당신은 사용자의 개인 AI 코치입니다. 아래 데이터를 기반으로 주간 코치 리뷰를 작성해주세요.

## 목표 드리프트 분석
{drift_summary}

## 행동 패턴 분석
{behavior_summary}

다음 구조로 작성해주세요:
1. 이번 주 총평 (2-3문장, 솔직하고 건설적으로)
2. 🚨 즉각 행동 필요 (드리프트/기한초과 목표별 구체적 다음 액션)
3. 💪 잘 하고 있는 것 (격려)
4. 🎯 이번 주 집중 포커스 (단 하나만)

반드시 한국어로, 300자 이내로 간결하게 작성."""

        resp = client.messages.create(
            model=model, max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        review_text = resp.content[0].text.strip()
    except Exception as e:
        review_text = f"리뷰 생성 오류: {e}"

    # 개입 제안 기록
    interventions = []
    for goal in drift.get("drifted", []) + drift.get("overdue", []):
        interventions.append({
            "goal": goal["title"],
            "type": "overdue" if "days_overdue" in goal else "drift",
            "date": datetime.now().isoformat(),
            "acted_on": False,
        })

    # 저장
    data = _load()
    data["weekly_reviews"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "review": review_text,
        "drift_count": len(drift.get("drifted", [])) + len(drift.get("overdue", [])),
        "on_track_count": len(drift.get("on_track", [])),
    })
    data["interventions"].extend(interventions)
    # 최근 8주치만 유지
    data["weekly_reviews"] = data["weekly_reviews"][-8:]
    _save(data)

    return {
        "success": True,
        "review_text": review_text,
        "drift_summary": drift.get("summary", ""),
        "interventions": interventions,
        "saved": True,
    }


def get_coach_history(limit: int = 4) -> dict:
    """최근 주간 코치 리뷰 기록을 반환한다."""
    data = _load()
    reviews = data.get("weekly_reviews", [])[-limit:]
    reviews.reverse()
    return {"success": True, "count": len(reviews), "reviews": reviews}


# ─────────────────────────────────────────────
# Claude Tool 스키마
# ─────────────────────────────────────────────

COACH_TOOLS = [
    {
        "name": "analyze_goal_drift",
        "description": "활성 목표의 진척률과 마감일을 분석해 드리프트(선언-행동 괴리)를 탐지한다.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "analyze_behavior_patterns",
        "description": "최근 대화 히스토리와 태스크 완료율로 행동 패턴을 분석한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "분석 기간 (기본 14일)"}
            },
            "required": []
        }
    },
    {
        "name": "generate_weekly_review",
        "description": "목표 드리프트 + 행동 패턴을 종합한 주간 코치 리뷰를 생성하고 저장한다.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_coach_history",
        "description": "최근 주간 코치 리뷰 기록을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "조회할 주간 수 (기본 4)"}
            },
            "required": []
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "analyze_goal_drift":     analyze_goal_drift,
        "analyze_behavior_patterns": analyze_behavior_patterns,
        "generate_weekly_review": generate_weekly_review,
        "get_coach_history":      get_coach_history,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    try:
        return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
