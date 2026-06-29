"""
memory/self_reflection.py  —  Agent J 자기 반성 루프

동작 방식:
  1. 세션 종료 시 (save_and_exit) 자동 실행
  2. 이번 세션 대화를 Haiku로 분석:
     - 어떤 응답이 효과적이었나?
     - 사용자가 불명확해 보인 부분은?
     - 다음 세션에서 개선할 점은?
  3. memory/self_reflection_log.json 에 날짜별 누적
  4. 다음 세션 시작 시 최근 반성 내용을 시스템 프롬프트에 주입
     → J가 스스로 진화하는 것처럼 동작

비용: Haiku 1회 호출/세션 = ~$0.003  (하루 1세션 기준 월 $0.09)

파일 구조 (memory/self_reflection_log.json):
  [
    {
      "date":        "2026-06-27",
      "session_turns": 8,
      "what_worked":   "코드 예시를 포함했을 때 사용자 반응이 좋았음",
      "what_to_improve": "긴 설명보다 핵심 요약 먼저 제시 필요",
      "next_session_note": "Python 질문엔 반드시 실행 예시 포함"
    },
    ...
  ]
"""

import json
import os
from datetime import datetime, date
from pathlib import Path

ROOT    = Path(__file__).parent.parent
LOG_FILE = ROOT / "memory" / "self_reflection_log.json"

# 반성 로그 보관 기간 (최근 N개)
MAX_ENTRIES = 30


# ──────────────────────────────────────────────────────────
# 파일 I/O
# ──────────────────────────────────────────────────────────

def _load() -> list:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(entries: list):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(
        json.dumps(entries[-MAX_ENTRIES:], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ──────────────────────────────────────────────────────────
# 반성 실행
# ──────────────────────────────────────────────────────────

def run_self_reflection(conversation_history: list) -> dict:
    """
    세션 대화를 분석해서 자기 반성 항목을 생성하고 저장한다.

    Args:
        conversation_history: 이번 세션 대화 목록 (role/content 형식)

    Returns:
        {"success": bool, ...반성 내용}
    """
    # 너무 짧은 세션은 건너뜀 (3턴 미만)
    turns = len(conversation_history) // 2
    if turns < 3:
        return {"success": False, "reason": "세션이 너무 짧음"}

    # 대화 텍스트 구성 (최근 10턴만)
    recent = conversation_history[-20:]
    convo  = ""
    for msg in recent:
        role    = "사용자" if msg["role"] == "user" else "J"
        content = msg["content"][:150]
        convo  += f"{role}: {content}\n"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = f"""다음은 AI 어시스턴트 'J'와 사용자의 대화입니다.
J의 관점에서 이번 세션을 분석하고 JSON으로 출력하세요.

[대화]
{convo}

분석 관점:
1. 어떤 응답이 사용자에게 가장 효과적이었나?
2. 사용자가 재질문하거나 불명확해한 부분은?
3. 다음 세션에서 개선할 구체적인 행동 1가지는?

출력 형식 (JSON만, 한국어):
{{
  "what_worked": "잘 된 점 한 문장",
  "what_to_improve": "개선할 점 한 문장",
  "next_session_note": "다음 세션 적용할 구체적 행동 (30자 이내)"
}}"""

        resp   = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        result = json.loads(resp.content[0].text.strip())

    except Exception as e:
        return {"success": False, "error": str(e)}

    # 저장
    entry = {
        "date":              date.today().isoformat(),
        "session_turns":     turns,
        "what_worked":       result.get("what_worked", ""),
        "what_to_improve":   result.get("what_to_improve", ""),
        "next_session_note": result.get("next_session_note", ""),
    }
    entries = _load()
    entries.append(entry)
    _save(entries)

    return {"success": True, **entry}


# ──────────────────────────────────────────────────────────
# 다음 세션 시스템 프롬프트 주입용
# ──────────────────────────────────────────────────────────

def get_reflection_context() -> str:
    """
    가장 최근 자기 반성 메모를 반환한다.
    Orchestrator 시스템 프롬프트에 주입해서 J가 이전 반성을 반영하게 한다.
    """
    entries = _load()
    if not entries:
        return ""

    latest = entries[-1]
    note   = latest.get("next_session_note", "")
    if not note:
        return ""

    return f"[이전 세션 자기 반성] {note}"


# ──────────────────────────────────────────────────────────
# 반성 로그 표시 (/reflect_log 명령어용)
# ──────────────────────────────────────────────────────────

def get_reflection_display(n: int = 5) -> str:
    entries = _load()
    if not entries:
        return "아직 자기 반성 기록이 없어요. 세션 종료 시 자동으로 생성돼요."

    recent = entries[-n:][::-1]
    lines  = ["**🔄 J의 자기 반성 로그**\n"]
    for e in recent:
        lines.append(f"**{e['date']}** ({e['session_turns']}턴)")
        lines.append(f"  ✅ 잘된 점: {e['what_worked']}")
        lines.append(f"  🔧 개선점: {e['what_to_improve']}")
        lines.append(f"  📌 다음 메모: {e['next_session_note']}")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_history = [
        {"role": "user",      "content": "pandas groupby 어떻게 써?"},
        {"role": "assistant", "content": "groupby는 이렇게 씁니다: df.groupby('col').agg(...)"},
        {"role": "user",      "content": "예시 코드 더 보여줘"},
        {"role": "assistant", "content": "물론이죠! 예시: ..."},
        {"role": "user",      "content": "고마워"},
        {"role": "assistant", "content": "도움이 됐으면 좋겠어요!"},
    ]
    result = run_self_reflection(sample_history)
    print(result)
    print("\n--- 다음 세션 주입 텍스트 ---")
    print(get_reflection_context())
