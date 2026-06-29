"""
agents/research_agent.py
Research Agent -- web search + Hermes KB + AI summary + Notion save
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.research_tools import web_search, fetch_page_text, save_research_to_notion

load_dotenv()

# Lazy init: Anthropic client created on first call (not at import time)
_client = None

def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client

SYSTEM_PROMPT = """당신은 Agent J의 Research + Knowledge 전문가입니다.
웹 검색 결과와 로컬 지식 베이스(ArXiv 논문, GitHub 트렌딩, HN 뉴스)를 활용해 답변합니다.

요약 원칙:
1. 지식 베이스에 관련 내용이 있으면 먼저 활용
2. 핵심 내용만 간결하게 (500~800자)
3. 글머리 기호로 구조화
4. 출처 명시 (KB: 지식베이스, WEB: 웹검색)
5. 마지막에 "더 알아볼 것" 1~2가지 제안
6. 항상 한국어로 작성"""

# Keywords that trigger Hermes KB lookup
KB_KEYWORDS = ["논문","arxiv","트렌딩","트렌드","깃헙","github","해커뉴스","hackernews",
               "hn","최신 ai","최신 ml","지식베이스","이번 주","weekly","paper"]


def _get_kb_context(query: str) -> str:
    """Search Hermes knowledge base for relevant content."""
    try:
        from tools.hermes_tools import search_kb
        results = search_kb(query, top_k=3)
        if not results:
            return ""
        lines = ["[지식 베이스 검색 결과]"]
        for r in results:
            src   = r.get("source", "").upper()
            title = r.get("title") or r.get("repo", "")
            desc  = r.get("summary") or r.get("desc", "")
            lines.append(f"({src}) {title}: {desc[:150]}")
        return "\n".join(lines)
    except Exception:
        return ""


def run_research(query: str) -> str:
    """Research: KB search -> web search -> AI summary -> Notion save"""

    query_lower = query.lower()
    use_kb = any(kw in query_lower for kw in KB_KEYWORDS)

    kb_context = ""
    if use_kb:
        print("📚 지식 베이스 검색 중...")
        kb_context = _get_kb_context(query)

    print(f"🔍 '{query}' 웹 검색 중...")
    results = web_search(query, num_results=5)

    if not results and not kb_context:
        return f"'{query}'에 대한 검색 결과가 없어요."

    # Build web search text
    raw_content = ""
    for i, r in enumerate(results, 1):
        raw_content += f"\n[WEB {i}] {r.get('title', '')}\n{r.get('snippet', '')}\n"
        if i == 1 and r.get("url"):
            page_text = fetch_page_text(r["url"], max_chars=2000)
            if page_text:
                raw_content += f"(상세 내용): {page_text[:1000]}\n"

    # AI summary
    prompt = (
        f"다음은 '{query}'에 대한 검색 결과입니다:\n\n"
        f"{kb_context}\n\n"
        f"[웹 검색 결과]\n{raw_content}\n\n"
        "위 내용을 바탕으로 핵심을 정리해주세요."
    )

    response = _get_client().messages.create(
        model=os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    summary = response.content[0].text

    # Notion save
    title = query[:50]
    notion_result = save_research_to_notion(title, query, summary, results)

    output_parts = [f"\n🔬 **리서치 결과: {query}**\n", summary, ""]
    if notion_result.get("success"):
        output_parts.append(f"✅ Notion 저장 완료: {notion_result.get('title', '')}")
    else:
        output_parts.append(f"⚠️ Notion 저장 실패: {notion_result.get('error', '')}")

    return "\n".join(output_parts)
