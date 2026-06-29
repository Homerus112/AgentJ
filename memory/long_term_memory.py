"""
memory/long_term_memory.py  —  Agent J 장기 메모리 압축 시스템

동작 방식:
  1. 주 1회 (또는 수동 /compress) 실행
  2. memory/context.json 의 recent_sessions + data/learning_log.json 를 읽어
     Haiku로 핵심 인사이트만 압축
  3. memory/long_term.json 에 날짜별로 누적 저장
  4. Orchestrator가 시작할 때 최근 압축본을 시스템 프롬프트에 주입
     → J가 "3주 전에 배운 내용"을 기억하는 것처럼 동작

비용: Haiku 1회 호출 = ~$0.005  (주 1회 → 월 $0.02 미만)

파일 구조 (memory/long_term.json):
  {
    "compressed": [
      {
        "week":     "2026-W26",
        "date":     "2026-06-27",
        "summary":  "이번 주 요약 텍스트...",
        "topics":   ["pandas", "AI agents", "데이터마이닝"],
        "insights": ["사용자는 코드 예시 선호", "Python 질문이 가장 많음"]
      },
      ...
    ],
    "last_compressed": "2026-06-27T08:00:00"
  }
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT          = Path(__file__).parent.parent
CONTEXT_FILE  = ROOT / "memory" / "context.json"
LEARNING_FILE = ROOT / "data"   / "learning_log.json"
LT_FILE       = ROOT / "memory" / "long_term.json"

# 압축 주기: 7일 (마지막 압축 후 이 기간이 지나야 재압축)
COMPRESS_INTERVAL_DAYS = 7


# ──────────────────────────────────────────────────────────
# 파일 I/O
# ──────────────────────────────────────────────────────────

def _load_lt() -> dict:
    if LT_FILE.exists():
        try:
            return json.loads(LT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"compressed": [], "last_compressed": None}


def _save_lt(data: dict):
    LT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ──────────────────────────────────────────────────────────
# 압축 필요 여부 판단
# ──────────────────────────────────────────────────────────

def needs_compression() -> bool:
    """마지막 압축 이후 COMPRESS_INTERVAL_DAYS 가 지났으면 True."""
    lt   = _load_lt()
    last = lt.get("last_compressed")
    if not last:
        return True
    last_dt = datetime.fromisoformat(last)
    return (datetime.now() - last_dt).days >= COMPRESS_INTERVAL_DAYS


# ──────────────────────────────────────────────────────────
# 압축 소스 수집
# ──────────────────────────────────────────────────────────

def _collect_recent_conversations() -> str:
    """context.json 의 recent_sessions 에서 사용자 메시지만 추출한다."""
    if not CONTEXT_FILE.exists():
        return ""
    try:
        data     = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        sessions = data.get("recent_sessions", [])
        lines    = []
        for s in sessions[-3:]:   # 최근 3 세션만
            for msg in s.get("history", []):
                if msg.get("role") == "user":
                    lines.append(f"- {msg['content'][:100]}")
        return "\n".join(lines[:40])   # 최대 40줄
    except Exception:
        return ""


def _collect_learning_log() -> str:
    """최근 7일간 학습 로그를 텍스트로 변환한다."""
    if not LEARNING_FILE.exists():
        return ""
    try:
        logs   = json.loads(LEARNING_FILE.read_text(encoding="utf-8"))
        cutoff = (date.today() - timedelta(days=7)).isoformat()
        recent = [e for e in logs if e.get("date", "") >= cutoff]
        if not recent:
            return ""
        lines  = [f"[{e['date']}] {e['topic']} ({e['category']})" for e in recent]
        return "\n".join(lines)
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────
# Haiku 압축 실행
# ──────────────────────────────────────────────────────────

def compress(force: bool = False) -> dict:
    """
    장기 메모리 압축을 실행한다.

    Args:
        force: True면 주기 무관하게 즉시 실행

    Returns:
        {"success": bool, "week": str, "summary": str, "skipped": bool}
    """
    if not force and not needs_compression():
        return {"success": True, "skipped": True, "reason": "압축 주기 미달"}

    conversations = _collect_recent_conversations()
    learning_log  = _collect_learning_log()

    if not conversations and not learning_log:
        return {"success": False, "skipped": True, "reason": "압축할 데이터 없음"}

    # Haiku 호출
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = f"""다음은 AI 어시스턴트 'J'와 사용자(데이터사이언스 전공 학생)의 최근 대화 및 학습 기록입니다.

[최근 대화 요약]
{conversations or '(없음)'}

[학습 기록]
{learning_log or '(없음)'}

위 내용을 바탕으로 다음을 JSON으로 출력하세요:
{{
  "summary": "이번 주 전반적인 활동 요약 (100자 이내, 한국어)",
  "topics": ["주요 주제 키워드 최대 5개"],
  "insights": ["사용자 패턴/선호도 인사이트 2~3개 (예: 코드 예시 선호, Python 질문 많음 등)"],
  "focus_next": "다음 주 집중할 영역 추천 (30자 이내)"
}}

JSON만 출력하세요."""

        resp   = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        result = json.loads(resp.content[0].text.strip())

    except Exception as e:
        return {"success": False, "error": str(e)}

    # 저장
    week_label = date.today().strftime("%Y-W%W")
    entry = {
        "week":       week_label,
        "date":       date.today().isoformat(),
        "summary":    result.get("summary", ""),
        "topics":     result.get("topics", []),
        "insights":   result.get("insights", []),
        "focus_next": result.get("focus_next", ""),
    }

    lt = _load_lt()
    # 같은 주 항목이 있으면 덮어쓰기
    lt["compressed"] = [c for c in lt["compressed"] if c.get("week") != week_label]
    lt["compressed"].append(entry)
    # 최대 12주(3개월) 보관
    lt["compressed"] = lt["compressed"][-12:]
    lt["last_compressed"] = datetime.now().isoformat()
    _save_lt(lt)

    return {"success": True, "skipped": False, "week": week_label, **entry}


# ──────────────────────────────────────────────────────────
# 시스템 프롬프트 주입용 컨텍스트 생성
# ──────────────────────────────────────────────────────────

def get_long_term_context(max_weeks: int = 4) -> str:
    """
    Orchestrator 시스템 프롬프트에 삽입할 장기 메모리 텍스트를 반환한다.
    없으면 빈 문자열 반환.
    """
    lt = _load_lt()
    compressed = lt.get("compressed", [])
    if not compressed:
        return ""

    recent = sorted(compressed, key=lambda x: x.get("date", ""), reverse=True)[:max_weeks]
    lines  = ["[장기 기억 — 최근 활동]"]
    for c in recent:
        topics   = ", ".join(c.get("topics", []))
        insights = " / ".join(c.get("insights", []))
        lines.append(
            f"• {c['week']}: {c['summary']}"
            + (f" | 주제: {topics}" if topics else "")
            + (f" | 인사이트: {insights}" if insights else "")
        )
    if recent and recent[0].get("focus_next"):
        lines.append(f"→ 다음 집중 영역: {recent[0]['focus_next']}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# 주간 요약 텍스트 출력 (for /compress command)
# ──────────────────────────────────────────────────────────

def get_summary_display() -> str:
    lt         = _load_lt()
    compressed = lt.get("compressed", [])
    if not compressed:
        return "아직 장기 메모리가 없어요. `/compress` 로 지금 압축할 수 있어요."

    last = lt.get("last_compressed", "")
    lines = [f"**🧠 장기 메모리** (마지막 압축: {last[:10]})\n"]
    for c in sorted(compressed, key=lambda x: x.get("date", ""), reverse=True)[:6]:
        topics = ", ".join(c.get("topics", []))
        lines.append(f"**{c['week']}** ({c['date']})")
        lines.append(f"  {c['summary']}")
        if topics:
            lines.append(f"  📌 {topics}")
        if c.get("focus_next"):
            lines.append(f"  → {c['focus_next']}")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("압축 실행 중...")
    result = compress(force=True)
    print(result)
    print("\n--- 장기 메모리 컨텍스트 ---")
    print(get_long_term_context())
