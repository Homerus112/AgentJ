"""behavior_tools.py — 행동 패턴 분석 도구"""
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def analyze_patterns() -> str:
    """대화 히스토리에서 행동 패턴 분석

    history_db에는 get_recent_history()가 없으므로
    search_messages()를 활용한다.
    """
    try:
        from memory.history_db import search_messages
        # 빈 쿼리로 최근 메시지 100개 가져오기
        history = search_messages("", limit=100)
        if not history:
            return "분석할 히스토리가 없습니다."
        agent_usage = {}
        for h in history:
            agent = h.get("agent") or "unknown"
            agent_usage[agent] = agent_usage.get(agent, 0) + 1
        result = "에이전트 사용 패턴:\n"
        for agent, count in sorted(agent_usage.items(), key=lambda x: -x[1]):
            result += f"  {agent}: {count}회\n"
        return result
    except Exception as e:
        return f"패턴 분석 오류: {e}"


def get_productivity_score() -> dict:
    """생산성 점수 계산

    history_db의 get_stats()를 사용한다 (get_agent_stats()는 존재하지 않음).
    """
    try:
        from memory.history_db import get_stats
        stats = get_stats()
        total = stats.get("total_messages", 0)
        return {"score": min(100, total * 2), "total": total}
    except Exception:
        return {"score": 0, "total": 0}
