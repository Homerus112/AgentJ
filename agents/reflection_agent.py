"""
agents/reflection_agent.py
Daily Reflection Agent — 하루 회고 작성 + Notion 저장 + 주간 회고 생성
"""

import os
import sys
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.reflection_tools import (
    get_today_summary,
    get_completed_tasks_today,
    save_reflection_to_notion,
    load_past_reflections
)

load_dotenv()

# 모듈 임포트 시점에 즉시 초기화하면 .env 로드 전일 수 있음 → lazy init
_client = None

def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """당신은 Agent J의 Daily Reflection 전문가입니다.
사용자의 하루를 따뜻하고 통찰 있게 정리해주는 역할을 합니다.

회고 작성 원칙:
1. 오늘 한 일을 구체적으로 정리
2. 잘된 점 / 개선할 점 균형 있게 분석
3. 내일을 위한 실행 가능한 제안 1~2가지
4. 전체 톤: 따뜻하고 격려적으로
5. 길이: 300~500자 (간결하게)

항상 한국어로 작성하세요."""


def run_reflection(user_input: str = None, auto_mode: bool = False) -> str:
    """
    회고 실행
    - auto_mode=True: 자동 실행 (하루 요약 기반으로 AI가 작성)
    - auto_mode=False: 대화형 (사용자 입력 받아 작성)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    today_data = get_today_summary()
    completed = get_completed_tasks_today()

    context_parts = [f"오늘 날짜: {today}"]

    if today_data["message_count"] > 0:
        context_parts.append(f"오늘 대화 수: {today_data['message_count']}개")
        if today_data["user_messages"]:
            sample = today_data["user_messages"][:5]
            context_parts.append("오늘 주요 요청:\n" + "\n".join(f"- {m[:80]}" for m in sample))

    if completed:
        context_parts.append("오늘 완료한 할 일:\n" + "\n".join(f"- {t.get('title','')}" for t in completed))

    context = "\n".join(context_parts)

    if auto_mode or not user_input:
        prompt = f"""다음 데이터를 바탕으로 오늘의 회고를 작성해주세요:

{context}

데이터가 부족하더라도 격려와 성찰이 담긴 짧은 회고를 작성해주세요."""
    else:
        prompt = f"""사용자가 직접 오늘 하루를 이야기합니다:

{user_input}

참고 데이터:
{context}

위 내용을 바탕으로 회고를 작성해주세요."""

    messages = [{"role": "user", "content": prompt}]

    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    reflection_text = response.content[0].text

    # Notion 저장
    notion_result = save_reflection_to_notion(today, reflection_text)

    output_lines = [
        f"\n📝 **{today} 회고**\n",
        reflection_text,
        ""
    ]

    if notion_result.get("success"):
        output_lines.append(f"✅ Notion 저장 완료: {notion_result.get('title', '')}")
    else:
        output_lines.append(f"⚠️ Notion 저장 실패: {notion_result.get('error', '')}")

    return "\n".join(output_lines)


def run_weekly_reflection() -> str:
    """지난 7일 회고를 모아 주간 회고 생성"""
    past = load_past_reflections(days=7)

    if not past:
        return "지난 7일간 저장된 회고가 없어요. 먼저 /reflect로 일일 회고를 작성해보세요!"

    prompt = f"""지난 7일간 {len(past)}개의 일일 회고가 있습니다.
    
제목 목록:
{chr(10).join(f'- {r["title"]}' for r in past)}

위 회고들을 종합해서 주간 회고를 작성해주세요:
1. 이번 주 핵심 성과 3가지
2. 반복된 패턴 / 습관
3. 다음 주 집중할 것 2가지
4. 한 줄 이번 주 평가"""

    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    weekly_text = response.content[0].text
    today = datetime.now().strftime("%Y-%m-%d")
    save_reflection_to_notion(f"{today}-weekly", f"[주간 회고]\n\n{weekly_text}")

    return f"\n📊 **주간 회고**\n\n{weekly_text}"


# CLI 직접 실행 지원 (python agents/reflection_agent.py)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="자동 모드 (대화 없이 실행)")
    parser.add_argument("--weekly", action="store_true", help="주간 회고 생성")
    args = parser.parse_args()

    if args.weekly:
        print(run_weekly_reflection())
    else:
        print(run_reflection(auto_mode=args.auto))
