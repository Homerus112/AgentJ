"""
agents/research_agent.py
Research Agent — 웹 검색 + AI 요약 + Notion 저장
"""

import os
import sys
from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.research_tools import web_search, fetch_page_text, save_research_to_notion

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """당신은 Agent J의 Research 전문가입니다.
웹에서 수집한 정보를 바탕으로 핵심을 정리하는 역할을 합니다.

요약 원칙:
1. 핵심 내용만 간결하게 (500~800자)
2. 글머리 기호로 구조화
3. 신뢰성 낮은 정보는 명시
4. 마지막에 "더 알아볼 것" 1~2가지 제안
5. 항상 한국어로 작성"""


def run_research(query: str) -> str:
    """리서치 실행: 검색 → 수집 → 요약 → Notion 저장"""

    print(f"🔍 '{query}' 검색 중...")
    results = web_search(query, num_results=5)

    if not results:
        return f"'{query}'에 대한 검색 결과가 없어요."

    # 검색 결과 텍스트 합치기
    raw_content = ""
    for i, r in enumerate(results, 1):
        raw_content += f"\n[{i}] {r.get('title', '')}\n{r.get('snippet', '')}\n"
        # 첫 번째 결과는 본문 추가 시도
        if i == 1 and r.get("url"):
            page_text = fetch_page_text(r["url"], max_chars=2000)
            if page_text:
                raw_content += f"(상세 내용): {page_text[:1000]}\n"

    # AI 요약
    prompt = f"""다음은 '{query}'에 대한 웹 검색 결과입니다:

{raw_content}

위 내용을 바탕으로 핵심을 정리해주세요."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    summary = response.content[0].text

    # Notion 저장
    title = query[:50]
    notion_result = save_research_to_notion(title, query, summary, results)

    output_lines = [
        f"\n🔬 **리서치 결과: {query}**\n",
        summary,
        ""
    ]

    if notion_result.get("success"):
        output_lines.append(f"✅ Notion 저장 완료: {notion_result.get('title', '')}")
    else:
        output_lines.append(f"⚠️ Notion 저장 실패: {notion_result.get('error', '')}")

    return "\n".join(output_lines)
