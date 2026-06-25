"""
agents/personalization_agent.py
자기 성장 엔진 — 대화 히스토리를 분석해서 사용자 맞춤 프로필 생성.

분석 항목:
- 말투 & 언어 스타일
- 자주 다루는 주제
- 선호하는 응답 형식/길이
- 기술 수준
- 에이전트별 커스텀 지시 자동 생성

결과는 data/user_profile.json에 저장되고,
BaseAgent가 시스템 프롬프트에 자동 주입함.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "user_profile.json")

ANALYSIS_PROMPT = """당신은 사용자 분석 전문가입니다.
아래는 사용자가 AI 어시스턴트와 나눈 실제 대화 기록입니다.
이 대화를 분석해서 사용자 프로필을 JSON으로만 반환하세요. 설명 없이 JSON만.

반환할 JSON 형식:
{
  "language": "한국어/영어/혼용",
  "speech_style": "격식체/반말/혼용 + 특징 (예: 직접적, 간결함, 기술적)",
  "expertise_level": "입문/중급/고급/전문가",
  "frequent_topics": ["주제1", "주제2", ...],
  "preferred_response_length": "짧게/보통/길게",
  "preferred_format": "bullet/prose/code-heavy/혼용",
  "personality_notes": "사용자 성향 요약 (2~3문장)",
  "custom_instructions": "에이전트에게 전달할 맞춤 지시사항. 예: '항상 결론 먼저 말하고 예시를 들어라', '코드는 주석 포함', '한국어로 답하되 기술 용어는 영문 병기'"
}"""


def _load_history_sample(max_messages: int = 200) -> list:
    """history_db에서 최근 대화 샘플 로드"""
    try:
        from memory.history_db import search_messages, get_recent_sessions
        sessions = get_recent_sessions(limit=30)
        all_messages = []
        for s in sessions:
            from memory.history_db import get_session_history
            msgs = get_session_history(s["session_id"])
            all_messages.extend(msgs)
        # 최신순 정렬 후 max_messages개 선택
        all_messages.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return all_messages[:max_messages]
    except Exception:
        return []


def _format_messages_for_analysis(messages: list) -> str:
    """분석용 대화 텍스트 포맷"""
    lines = []
    for m in messages:
        role = "사용자" if m["role"] == "user" else "에이전트"
        content = m["content"][:300]  # 너무 긴 메시지는 자르기
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def run_personalization() -> dict:
    """
    대화 히스토리 분석 → user_profile.json 저장
    Returns: {"success": True/False, "profile": {...}, "error": "..."}
    """
    # 히스토리 로드
    messages = _load_history_sample(max_messages=200)

    if not messages:
        return {
            "success": False,
            "error": "분석할 대화 기록이 없어요. 먼저 Agent J와 대화를 나눠보세요!"
        }

    user_messages = [m for m in messages if m["role"] == "user"]
    if len(user_messages) < 3:
        return {
            "success": False,
            "error": f"대화가 너무 적어요 (현재 {len(user_messages)}개). 최소 3개 이상 필요해요."
        }

    conversation_text = _format_messages_for_analysis(messages)

    print(f"  📊 {len(messages)}개 메시지 분석 중...")

    # Claude로 분석
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=ANALYSIS_PROMPT,
        messages=[{
            "role": "user",
            "content": f"다음 대화를 분석해서 사용자 프로필 JSON을 반환하세요:\n\n{conversation_text}"
        }]
    )

    raw = response.content[0].text.strip()

    # JSON 파싱
    try:
        # ```json ... ``` 블록 제거
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        profile = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 파싱 실패: {e}\n원문: {raw[:200]}"}

    # 메타 정보 추가
    profile["last_analyzed"] = datetime.now().isoformat()
    profile["analyzed_message_count"] = len(messages)

    # 저장
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 프로필 저장 완료: {PROFILE_PATH}")
    return {"success": True, "profile": profile}


def load_profile() -> dict:
    """저장된 프로필 로드 (없으면 빈 dict)"""
    try:
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_profile_injection() -> str:
    """
    시스템 프롬프트에 주입할 사용자 맞춤 지시문 반환.
    프로필이 없으면 빈 문자열 반환.
    """
    profile = load_profile()
    if not profile:
        return ""

    parts = ["\n\n## 사용자 맞춤 설정 (자동 학습됨)"]

    if profile.get("speech_style"):
        parts.append(f"- 말투: {profile['speech_style']}")
    if profile.get("expertise_level"):
        parts.append(f"- 기술 수준: {profile['expertise_level']}")
    if profile.get("preferred_response_length"):
        parts.append(f"- 선호 응답 길이: {profile['preferred_response_length']}")
    if profile.get("preferred_format"):
        parts.append(f"- 선호 형식: {profile['preferred_format']}")
    if profile.get("custom_instructions"):
        parts.append(f"\n추가 지시:\n{profile['custom_instructions']}")

    return "\n".join(parts)


if __name__ == "__main__":
    print("🧠 사용자 프로필 분석 시작...")
    result = run_personalization()
    if result["success"]:
        print("\n✅ 분석 완료!")
        print(json.dumps(result["profile"], ensure_ascii=False, indent=2))
    else:
        print(f"\n❌ 실패: {result['error']}")
