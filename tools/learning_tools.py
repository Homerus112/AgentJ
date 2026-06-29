"""
tools/learning_tools.py  —  Agent J 학습 진도 추적 도구

기능:
  - 학습 로그 저장 (data/learning_log.json)
  - 통계 조회: 연속 학습일, 주제별 빈도, 최근 로그
  - 학습 감지: 대화에서 키워드 기반으로 학습 여부 판단 (API 0원)
  - 주제 추출: Claude Haiku 호출로 핵심 주제 1~2줄 추출 (~$0.001)

데이터 구조 (data/learning_log.json):
  [
    {
      "date": "2026-06-27",
      "topic": "pandas groupby + agg 사용법",
      "category": "Python",
      "source": "auto"   # "auto" | "manual"
    },
    ...
  ]
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "data" / "learning_log.json"

# 학습으로 판단할 키워드 (API 비용 없이 1차 필터링)
LEARNING_KEYWORDS = [
    "배웠", "공부했", "이해했", "알게됐", "알았어", "익혔", "해봤",
    "만들었", "구현했", "완성했", "학습했", "연습했", "시도했",
    "써봤", "적용했", "실험했", "테스트했", "분석했", "정리했",
    "learned", "studied", "understood", "implemented", "practiced",
]

# 학습 카테고리 키워드
CATEGORY_MAP = {
    "Python":      ["python", "파이썬", "pandas", "numpy", "matplotlib", "sklearn",
                    "pytorch", "tensorflow", "fastapi", "flask", "pip", "venv"],
    "AI/ML":       ["llm", "gpt", "claude", "agent", "에이전트", "모델", "학습",
                    "embedding", "rag", "fine-tuning", "transformer", "neural"],
    "Data Mining": ["데이터마이닝", "data mining", "크롤링", "scraping", "전처리",
                    "preprocessing", "feature", "피처", "eda", "시각화"],
    "SQL/DB":      ["sql", "쿼리", "query", "database", "db", "mongodb", "mysql",
                    "postgresql", "sqlite"],
    "Tools":       ["git", "github", "docker", "aws", "gcp", "linux", "bash",
                    "vscode", "notion", "api"],
}


# ──────────────────────────────────────────────────────────
# 파일 I/O
# ──────────────────────────────────────────────────────────

def _load() -> list:
    if not LOG_PATH.exists():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        return []
    try:
        return json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(logs: list):
    LOG_PATH.write_text(
        json.dumps(logs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ──────────────────────────────────────────────────────────
# 학습 감지 (API 비용 0원)
# ──────────────────────────────────────────────────────────

def has_learning_signal(text: str) -> bool:
    """대화 텍스트에 학습 키워드가 있는지 확인 (무료)."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in LEARNING_KEYWORDS)


def _guess_category(text: str) -> str:
    """텍스트에서 가장 가능성 높은 카테고리를 추측 (무료)."""
    text_lower = text.lower()
    scores = {cat: sum(1 for kw in kws if kw in text_lower)
              for cat, kws in CATEGORY_MAP.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"


# ──────────────────────────────────────────────────────────
# 학습 주제 추출 (Haiku 호출, ~$0.001)
# ──────────────────────────────────────────────────────────

def extract_topic(user_message: str, agent_response: str) -> str | None:
    """
    대화에서 학습 주제를 한 줄로 추출한다.
    실패 시 None 반환 (로그 저장 건너뜀).
    """
    try:
        import anthropic, os
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = (
            "다음 대화에서 사용자가 배운 핵심 내용을 한국어로 20자 이내 한 줄로 요약하세요.\n"
            "학습 내용이 없으면 'NONE'만 출력하세요.\n\n"
            f"사용자: {user_message[:300]}\n"
            f"J: {agent_response[:300]}"
        )
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=60,
            messages=[{"role": "user", "content": prompt}]
        )
        result = resp.content[0].text.strip()
        return None if result.upper() == "NONE" else result
    except Exception:
        return None


# ──────────────────────────────────────────────────────────
# 로그 저장
# ──────────────────────────────────────────────────────────

def log_learning(topic: str, category: str = None, source: str = "auto") -> dict:
    """
    학습 항목을 오늘 날짜로 저장한다.
    같은 날 같은 주제가 이미 있으면 중복 저장하지 않는다.
    """
    logs    = _load()
    today   = date.today().isoformat()
    cat     = category or _guess_category(topic)

    # 중복 체크
    for entry in logs:
        if entry["date"] == today and entry["topic"] == topic:
            return {"saved": False, "reason": "duplicate"}

    logs.append({"date": today, "topic": topic, "category": cat, "source": source})
    _save(logs)
    return {"saved": True, "topic": topic, "category": cat}


def auto_detect_and_log(user_message: str, agent_response: str) -> dict:
    """
    route() 이후 자동 호출되는 통합 함수.
    1단계: 키워드 필터 (무료)
    2단계: Haiku로 주제 추출 (~$0.001)
    3단계: 로그 저장
    """
    if not has_learning_signal(user_message + " " + agent_response):
        return {"detected": False}

    topic = extract_topic(user_message, agent_response)
    if not topic:
        return {"detected": False}

    result = log_learning(topic)
    result["detected"] = True
    return result


# ──────────────────────────────────────────────────────────
# 통계 조회
# ──────────────────────────────────────────────────────────

def get_streak() -> int:
    """오늘을 포함한 연속 학습일 수를 반환한다."""
    logs  = _load()
    dates = sorted({entry["date"] for entry in logs}, reverse=True)
    if not dates:
        return 0

    streak   = 0
    check    = date.today()
    date_set = {date.fromisoformat(d) for d in dates}

    while check in date_set:
        streak += 1
        check  -= timedelta(days=1)
    return streak


def get_days_since_last_log() -> int:
    """마지막 학습 기록으로부터 경과 일수. 기록 없으면 999."""
    logs = _load()
    if not logs:
        return 999
    latest = max(entry["date"] for entry in logs)
    delta  = date.today() - date.fromisoformat(latest)
    return delta.days


def get_stats_summary() -> str:
    """학습 통계를 사람이 읽기 좋은 문자열로 반환한다."""
    logs = _load()
    if not logs:
        return "아직 학습 기록이 없어요. 대화하면서 배운 내용이 자동으로 쌓여요!"

    total  = len(logs)
    streak = get_streak()
    days_since = get_days_since_last_log()

    # 카테고리 분포
    from collections import Counter
    cat_count = Counter(e["category"] for e in logs)
    cat_str   = " · ".join(f"{cat} {cnt}건" for cat, cnt in cat_count.most_common(4))

    # 최근 5개
    recent = sorted(logs, key=lambda x: x["date"], reverse=True)[:5]
    recent_str = "\n".join(f"  • [{e['date']}] {e['topic']} ({e['category']})"
                           for e in recent)

    gap_msg = (f"🔥 {streak}일 연속 학습 중!" if streak >= 2
               else f"⚠️ 마지막 학습 {days_since}일 전" if days_since >= 3
               else "✅ 오늘 학습 기록 있음")

    return (
        f"**📚 학습 진도 요약**\n\n"
        f"총 학습 항목: **{total}건** | {gap_msg}\n"
        f"카테고리: {cat_str}\n\n"
        f"**최근 학습:**\n{recent_str}"
    )


def get_recent_logs(n: int = 7) -> list:
    """최근 n일간의 학습 로그를 반환한다."""
    logs    = _load()
    cutoff  = (date.today() - timedelta(days=n)).isoformat()
    return [e for e in logs if e["date"] >= cutoff]


# ──────────────────────────────────────────────────────────
# 사용 예시
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 수동 저장 테스트
    r = log_learning("pandas groupby + agg 활용법", source="manual")
    print(r)
    print(get_stats_summary())
    print(f"연속 학습일: {get_streak()}일")
