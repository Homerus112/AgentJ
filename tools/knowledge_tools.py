"""
tools/knowledge_tools.py — 개인 지식 그래프 (Feature 3)

기능:
  1. URL 유형 감지 후 내용 추출 (YouTube / 웹 아티클 / GitHub README)
  2. LLM으로 핵심 인사이트 추출 + 태그 자동 생성
  3. data/knowledge.json에 로컬 저장 + Notion 동기화
  4. 기존 노트와 유사도 기반 연결 고리 탐지

저장 구조 (data/knowledge.json):
  [{"id", "title", "source_url", "type", "summary", "insights", "tags",
    "related_ids", "notion_page_id", "created_at"}]
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

KNOWLEDGE_FILE = Path(os.getenv("KNOWLEDGE_FILE", "data/knowledge.json"))


# ─────────────────────────────────────────────
# 로컬 JSON 헬퍼
# ─────────────────────────────────────────────

def _load() -> list:
    if KNOWLEDGE_FILE.exists():
        return json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    return []


def _save(data: list):
    KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_id(data: list) -> int:
    return max((item.get("id", 0) for item in data), default=0) + 1


# ─────────────────────────────────────────────
# 1. URL 유형 감지 & 콘텐츠 추출
# ─────────────────────────────────────────────

def _detect_url_type(url: str) -> str:
    """URL 유형을 감지한다: youtube / github / article"""
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "github.com" in u:
        return "github"
    return "article"


def _fetch_youtube_info(url: str) -> dict:
    """YouTube URL에서 영상 ID를 추출하고 oEmbed로 제목/설명을 가져온다."""
    vid_match = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    if not vid_match:
        return {"title": "YouTube 영상", "content": "영상 ID를 추출할 수 없습니다.", "type": "youtube"}
    vid_id = vid_match.group(1)
    try:
        oembed = requests.get(
            f"https://www.youtube.com/oembed?url={url}&format=json", timeout=8
        ).json()
        title = oembed.get("title", "YouTube 영상")
        author = oembed.get("author_name", "")
        return {
            "title": title,
            "content": f"YouTube 영상 — {title} (by {author})\nURL: {url}",
            "type": "youtube",
            "video_id": vid_id,
        }
    except Exception:
        return {"title": "YouTube 영상", "content": url, "type": "youtube"}


def _fetch_github_readme(url: str) -> dict:
    """GitHub 레포 URL에서 README를 가져온다."""
    match = re.search(r'github\.com/([^/]+/[^/\s?#]+)', url)
    if not match:
        return {"title": "GitHub", "content": url, "type": "github"}
    repo = match.group(1).rstrip("/")
    try:
        readme = requests.get(
            f"https://raw.githubusercontent.com/{repo}/main/README.md",
            timeout=8
        )
        if not readme.ok:
            readme = requests.get(
                f"https://raw.githubusercontent.com/{repo}/master/README.md",
                timeout=8
            )
        content = readme.text[:3000] if readme.ok else f"README를 가져올 수 없음: {repo}"
        return {"title": repo.split("/")[-1], "content": content, "type": "github", "repo": repo}
    except Exception as e:
        return {"title": "GitHub", "content": str(e), "type": "github"}


def _fetch_article(url: str) -> dict:
    """일반 웹 아티클에서 텍스트를 추출한다."""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        # 간단한 HTML 텍스트 추출
        text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # 제목 추출
        title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "웹 아티클"
        return {"title": title[:100], "content": text[:4000], "type": "article"}
    except Exception as e:
        return {"title": "웹 아티클", "content": f"가져오기 실패: {e}", "type": "article"}


def extract_from_url(url: str) -> dict:
    """
    URL 유형을 감지하고 내용을 추출한다.
    Args:
        url: YouTube / GitHub / 일반 웹 URL
    Returns:
        {"title", "content", "type", "url"}
    """
    if not REQUESTS_AVAILABLE:
        return {"success": False, "error": "requests 미설치"}
    url_type = _detect_url_type(url)
    if url_type == "youtube":
        result = _fetch_youtube_info(url)
    elif url_type == "github":
        result = _fetch_github_readme(url)
    else:
        result = _fetch_article(url)
    result["url"] = url
    result["success"] = True
    return result


# ─────────────────────────────────────────────
# 2. LLM 인사이트 추출
# ─────────────────────────────────────────────

def extract_insights(title: str, content: str, url_type: str,
                     model: str = None) -> dict:
    """
    LLM으로 콘텐츠에서 핵심 인사이트와 태그를 추출한다.
    Returns:
        {"summary", "insights": [str], "tags": [str], "key_concepts": [str]}
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = model or os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

        type_hint = {
            "youtube": "YouTube 영상 제목/정보",
            "github": "GitHub 레포지토리 README",
            "article": "웹 아티클/블로그 포스트"
        }.get(url_type, "콘텐츠")

        prompt = f"""다음 {type_hint}에서 핵심 인사이트를 추출해줘.

제목: {title}
내용 (앞부분):
{content[:2000]}

다음 JSON 형식으로만 응답 (다른 텍스트 없이):
{{
  "summary": "2-3문장 요약",
  "insights": ["핵심 인사이트 1", "핵심 인사이트 2", "핵심 인사이트 3"],
  "tags": ["태그1", "태그2", "태그3"],
  "key_concepts": ["개념1", "개념2"]
}}"""

        resp = client.messages.create(
            model=model, max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "summary": title,
        "insights": [],
        "tags": [],
        "key_concepts": []
    }


# ─────────────────────────────────────────────
# 3. 연결 고리 탐지
# ─────────────────────────────────────────────

def find_related_knowledge(tags: list, concepts: list, exclude_id: int = None) -> list:
    """
    태그/개념 기반으로 기존 지식 베이스에서 연관 항목을 찾는다.
    Returns:
        [{"id", "title", "reason"}] (최대 3개)
    """
    data = _load()
    if not data:
        return []

    scores = []
    search_terms = set(t.lower() for t in tags + concepts)

    for item in data:
        if item.get("id") == exclude_id:
            continue
        item_terms = set(t.lower() for t in item.get("tags", []) + item.get("key_concepts", []))
        overlap = search_terms & item_terms
        if overlap:
            scores.append({
                "id": item["id"],
                "title": item["title"],
                "reason": f"공통 키워드: {', '.join(list(overlap)[:3])}",
                "score": len(overlap)
            })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:3]


# ─────────────────────────────────────────────
# 4. 저장 & Notion 동기화
# ─────────────────────────────────────────────

def save_to_knowledge_base(title: str, content: str, source_url: str,
                           insights_data: dict, url_type: str = "article") -> dict:
    """
    인사이트를 knowledge.json에 저장하고 Notion에 동기화한다.
    Returns:
        {"success", "id", "related", "notion_url"}
    """
    data = _load()
    new_id = _next_id(data)

    tags = insights_data.get("tags", [])
    concepts = insights_data.get("key_concepts", [])
    related = find_related_knowledge(tags, concepts, exclude_id=new_id)

    entry = {
        "id": new_id,
        "title": title,
        "source_url": source_url,
        "type": url_type,
        "summary": insights_data.get("summary", ""),
        "insights": insights_data.get("insights", []),
        "tags": tags,
        "key_concepts": concepts,
        "related_ids": [r["id"] for r in related],
        "notion_page_id": None,
        "created_at": datetime.now().isoformat(),
    }

    data.append(entry)
    _save(data)

    # Notion 저장
    notion_url = ""
    try:
        from tools.notion_tools import save_rich_page
        related_section = ""
        if related:
            related_section = "\n\n## 🔗 연관 노트\n" + "\n".join(
                [f"- [{r['title']}] ({r['reason']})" for r in related]
            )

        md_content = (
            f"## 📌 요약\n{entry['summary']}\n\n"
            f"## 💡 핵심 인사이트\n" +
            "\n".join([f"- {ins}" for ins in entry["insights"]]) +
            f"\n\n## 🏷️ 태그\n{', '.join(tags)}\n\n"
            f"## 📚 핵심 개념\n{', '.join(concepts)}\n\n"
            f"## 🔗 원본\n{source_url}" +
            related_section
        )
        result = save_rich_page(
            title=f"📚 {title}",
            content=md_content,
            category="research"
        )
        notion_url = result.get("url", "")
        if result.get("page_id"):
            entry["notion_page_id"] = result["page_id"]
            _save(data)
    except Exception:
        pass

    return {
        "success": True,
        "id": new_id,
        "title": title,
        "summary": entry["summary"],
        "tags": tags,
        "related": related,
        "notion_url": notion_url,
    }


def process_url(url: str) -> dict:
    """
    URL을 받아 전체 파이프라인을 실행한다:
    추출 → 인사이트 분석 → 연결 탐지 → 저장.
    Args:
        url: 처리할 URL
    Returns:
        저장 결과 + 연관 노트
    """
    # 1. 콘텐츠 추출
    extracted = extract_from_url(url)
    if not extracted.get("success"):
        return extracted

    # 2. 인사이트 추출
    insights = extract_insights(
        title=extracted["title"],
        content=extracted["content"],
        url_type=extracted["type"]
    )

    # 3. 저장
    result = save_to_knowledge_base(
        title=extracted["title"],
        content=extracted["content"],
        source_url=url,
        insights_data=insights,
        url_type=extracted["type"]
    )
    return result


def list_knowledge(tag: str = None, limit: int = 10) -> dict:
    """
    저장된 지식 목록을 조회한다.
    Args:
        tag:   특정 태그로 필터링 (없으면 전체)
        limit: 최대 반환 개수
    """
    all_data = _load()
    total = len(all_data)
    data = all_data
    if tag:
        data = [item for item in data if tag.lower() in [t.lower() for t in item.get("tags", [])]]
    # 최신순 정렬
    data.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    items = data[:limit]
    return {
        "success": True,
        "total": total,
        "count": len(items),
        "items": [{
            "id": i["id"],
            "title": i["title"],
            "type": i["type"],
            "summary": i["summary"][:100],
            "tags": i["tags"],
            "date": i["created_at"][:10]
        } for i in items]
    }


def search_knowledge(query: str) -> dict:
    """
    제목/태그/인사이트에서 키워드 검색.
    Args:
        query: 검색어
    """
    data = _load()
    query_lower = query.lower()
    results = []
    for item in data:
        searchable = " ".join([
            item.get("title", ""),
            item.get("summary", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("insights", [])),
        ]).lower()
        if query_lower in searchable:
            results.append({
                "id": item["id"],
                "title": item["title"],
                "summary": item["summary"][:120],
                "tags": item["tags"],
                "source_url": item["source_url"],
            })
    return {"success": True, "query": query, "count": len(results), "results": results[:5]}


# ─────────────────────────────────────────────
# Claude Tool 스키마
# ─────────────────────────────────────────────

KNOWLEDGE_TOOLS = [
    {
        "name": "process_url",
        "description": "URL(YouTube/GitHub/아티클)에서 내용을 추출하고 인사이트를 분석해 지식 베이스에 저장한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "처리할 URL"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "list_knowledge",
        "description": "저장된 지식 목록을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tag":   {"type": "string", "description": "태그 필터 (선택)"},
                "limit": {"type": "integer", "description": "최대 결과 수 (기본 10)"}
            },
            "required": []
        }
    },
    {
        "name": "search_knowledge",
        "description": "지식 베이스에서 키워드로 검색한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어"}
            },
            "required": ["query"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "process_url":     process_url,
        "list_knowledge":  list_knowledge,
        "search_knowledge": search_knowledge,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    try:
        return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
