"""
tools/hermes_tools.py  —  헤르메스 에이전트 수집 도구

수집 소스 (API 비용 0원, 모두 무료 공개 API):
  - ArXiv: CS·AI·ML 최신 논문 (최근 3일)
  - GitHub Trending: 주간 트렌딩 Python/AI 레포
  - Hacker News: 상위 Tech 스토리

저장: data/knowledge_base.json
"""

import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from pathlib import Path

KB_PATH = Path(__file__).parent.parent / "data" / "knowledge_base.json"


# ──────────────────────────────────────────────────────────
# 파일 I/O
# ──────────────────────────────────────────────────────────

def _load_kb() -> dict:
    if KB_PATH.exists():
        try:
            return json.loads(KB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"arxiv": [], "github": [], "hackernews": [], "last_updated": None}


def _save_kb(data: dict):
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    KB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ──────────────────────────────────────────────────────────
# 1. ArXiv 논문 수집
# ──────────────────────────────────────────────────────────

def fetch_arxiv(max_results: int = 8) -> list:
    """
    CS·AI·ML 카테고리 최신 논문을 가져온다.
    ArXiv API는 무료, 인증 불필요.
    """
    query = urllib.parse.quote(
        "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:stat.ML"
    )
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml = resp.read().decode("utf-8")

        # 간단한 XML 파싱 (의존성 없이)
        entries = []
        for entry in xml.split("<entry>")[1:]:
            title   = re.search(r"<title>(.*?)</title>",   entry, re.DOTALL)
            summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
            link    = re.search(r'href="(https://arxiv\.org/abs/[^"]+)"', entry)
            authors = re.findall(r"<name>(.*?)</name>", entry)

            if title and summary:
                entries.append({
                    "title":   re.sub(r"\s+", " ", title.group(1)).strip(),
                    "summary": re.sub(r"\s+", " ", summary.group(1)).strip()[:300],
                    "link":    link.group(1) if link else "",
                    "authors": authors[:3],
                    "fetched": date.today().isoformat(),
                })
        print(f"  📄 ArXiv: {len(entries)}개 논문 수집")
        return entries
    except Exception as e:
        print(f"  ⚠️  ArXiv 수집 실패: {e}")
        return []


# ──────────────────────────────────────────────────────────
# 2. GitHub Trending 수집
# ──────────────────────────────────────────────────────────

def fetch_github_trending(language: str = "python") -> list:
    """
    GitHub Trending 페이지를 파싱한다.
    공식 API 없이 HTML 스크래핑 (robots.txt 허용 범위).
    """
    url = f"https://github.com/trending/{language}?since=weekly"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        repos = []
        # repo article 블록 파싱
        for block in re.findall(
            r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>', html, re.DOTALL
        )[:8]:
            # 레포 이름
            name_m = re.search(r'href="/([^"]+)"[^>]*>\s*\n\s*<span[^>]*>([^<]+)</span>[^<]*<span[^>]*>([^<]+)</span>', block)
            # description
            desc_m = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', block, re.DOTALL)
            # stars
            star_m = re.search(r'aria-label="(\d[\d,]*) users starred', block)

            if name_m or re.search(r'href="/[^/"]+/[^/"]+\"', block):
                href   = re.search(r'href="/([^/"]+/[^/"]+)"', block)
                full   = href.group(1) if href else ""
                desc   = re.sub(r"\s+", " ", desc_m.group(1)).strip() if desc_m else ""
                stars  = star_m.group(1) if star_m else "?"
                if full and "/" in full:
                    repos.append({
                        "repo":    full,
                        "link":    f"https://github.com/{full}",
                        "desc":    desc[:200],
                        "stars":   stars,
                        "fetched": date.today().isoformat(),
                    })

        print(f"  ⭐ GitHub Trending: {len(repos)}개 레포 수집")
        return repos
    except Exception as e:
        print(f"  ⚠️  GitHub Trending 수집 실패: {e}")
        return []


# ──────────────────────────────────────────────────────────
# 3. Hacker News Top Stories
# ──────────────────────────────────────────────────────────

def fetch_hackernews(max_items: int = 8) -> list:
    """
    HN 공식 Firebase API로 상위 스토리를 가져온다. 완전 무료.
    """
    try:
        # 상위 스토리 ID 목록
        with urllib.request.urlopen(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        ) as resp:
            ids = json.loads(resp.read())[:20]

        items = []
        for story_id in ids:
            try:
                with urllib.request.urlopen(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=8,
                ) as resp:
                    item = json.loads(resp.read())
                if item.get("type") == "story" and item.get("url"):
                    items.append({
                        "title":   item.get("title", ""),
                        "link":    item.get("url", ""),
                        "score":   item.get("score", 0),
                        "by":      item.get("by", ""),
                        "fetched": date.today().isoformat(),
                    })
                    if len(items) >= max_items:
                        break
            except Exception:
                continue

        print(f"  🔥 Hacker News: {len(items)}개 스토리 수집")
        return items
    except Exception as e:
        print(f"  ⚠️  Hacker News 수집 실패: {e}")
        return []


# ──────────────────────────────────────────────────────────
# 통합 수집 + 저장
# ──────────────────────────────────────────────────────────

def collect_all() -> dict:
    """세 소스를 모두 수집해서 knowledge_base.json에 저장한다."""
    print("🔍 헤르메스: 지식 수집 시작...")
    kb = {
        "arxiv":       fetch_arxiv(),
        "github":      fetch_github_trending(),
        "hackernews":  fetch_hackernews(),
    }
    _save_kb(kb)
    total = sum(len(v) for v in kb.values())
    print(f"✅ 총 {total}개 항목 수집 완료 → knowledge_base.json")
    return kb


# ──────────────────────────────────────────────────────────
# J 대화에서 지식 베이스 검색
# ──────────────────────────────────────────────────────────

def search_kb(query: str, top_k: int = 3) -> list:
    """
    키워드로 knowledge_base를 검색한다. (임베딩 없이 키워드 매칭)
    """
    kb    = _load_kb()
    terms = query.lower().split()
    results = []

    # ArXiv
    for item in kb.get("arxiv", []):
        text  = (item.get("title", "") + " " + item.get("summary", "")).lower()
        score = sum(1 for t in terms if t in text)
        if score > 0:
            results.append({"source": "arxiv", "score": score, **item})

    # GitHub
    for item in kb.get("github", []):
        text  = (item.get("repo", "") + " " + item.get("desc", "")).lower()
        score = sum(1 for t in terms if t in text)
        if score > 0:
            results.append({"source": "github", "score": score, **item})

    # HackerNews
    for item in kb.get("hackernews", []):
        text  = item.get("title", "").lower()
        score = sum(1 for t in terms if t in text)
        if score > 0:
            results.append({"source": "hn", "score": score, **item})

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]


def get_kb_summary() -> str:
    """최근 수집된 knowledge_base 현황을 반환한다."""
    kb   = _load_kb()
    last = kb.get("last_updated", "없음")
    return (
        f"📚 지식 베이스 현황 (마지막 수집: {last[:10] if last else '없음'})\n"
        f"  ArXiv 논문: {len(kb.get('arxiv', []))}개\n"
        f"  GitHub Trending: {len(kb.get('github', []))}개\n"
        f"  Hacker News: {len(kb.get('hackernews', []))}개"
    )


if __name__ == "__main__":
    collect_all()
    print(get_kb_summary())
