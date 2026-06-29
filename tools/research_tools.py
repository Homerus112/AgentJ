"""
tools/research_tools.py
웹 검색 + 내용 요약 + Notion 저장
"""

import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def web_search(query: str, num_results: int = 5) -> list:
    """
    DuckDuckGo Instant Answer API로 무료 검색
    (API 키 불필요)
    """
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8,
            headers={"User-Agent": "AgentJ/1.0"}
        )
        data = resp.json()
        results = []

        # Abstract (위키피디아 등)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["AbstractText"][:500],
                "url": data.get("AbstractURL", "")
            })

        # Related Topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:60],
                    "snippet": topic.get("Text", "")[:300],
                    "url": topic.get("FirstURL", "")
                })

        return results[:num_results]
    except Exception as e:
        return [{"title": "검색 오류", "snippet": str(e), "url": ""}]


def fetch_page_text(url: str, max_chars: int = 3000) -> str:
    """URL에서 본문 텍스트 추출 (간단 버전)"""
    if not url:
        return ""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "AgentJ/1.0"})
        resp.raise_for_status()
        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def save_research_to_notion(title: str, query: str, summary: str, sources: list) -> dict:
    """리서치 결과를 Notion에 저장"""
    try:
        from notion_client import Client
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        parent_id = os.getenv("NOTION_PARENT_PAGE_ID")

        if not parent_id or not os.getenv("NOTION_API_KEY"):
            return {"success": False, "error": "Notion 환경변수 미설정"}

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        page_title = f"🔬 Research: {title} ({date_str})"

        # 본문 블록 구성
        children = [
            # 쿼리 섹션
            {
                "object": "block", "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"검색어: {query}"}}],
                    "icon": {"emoji": "🔍"}
                }
            },
            # 요약
            {"object": "block", "type": "heading_2",
             "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📋 요약"}}]}},
        ]

        # 요약 내용 (2000자 제한으로 분할)
        for chunk in [summary[i:i+1900] for i in range(0, len(summary), 1900)]:
            children.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
            })

        # 출처
        if sources:
            children.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🔗 출처"}}]}
            })
            for src in sources[:5]:
                if src.get("url"):
                    children.append({
                        "object": "block", "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": src.get("title", src["url"])[:100], "link": {"url": src["url"]}}
                            }]
                        }
                    })

        page = notion.pages.create(
            parent={"page_id": parent_id},
            properties={"title": {"title": [{"text": {"content": page_title}}]}},
            children=children
        )
        return {"success": True, "url": page.get("url", ""), "title": page_title}

    except Exception as e:
        return {"success": False, "error": str(e)}
