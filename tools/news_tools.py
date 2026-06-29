"""
news_tools.py
News Agent용 RSS 뉴스 수집 및 이메일 발송 도구.

뉴스 소스 구성:
  Tech      → TechCrunch, The Verge (English)
  Sports    → BBC Sport, ESPN (English)
  Economy   → Reuters Business (EN) + 한국경제 (KR)
  Politics  → Reuters World (EN) + 연합뉴스 (KR)

추가 (Feature 1):
  Morning Brief → 태스크 + 목표 + GitHub Trending + 기술 뉴스 통합
"""

import json
import smtplib
import os
import re
import html as html_module
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ── RSS 피드 설정 ──────────────────────────────────────────
RSS_FEEDS = {
    "tech": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "lang": "en"},
        {"name": "The Verge",  "url": "https://www.theverge.com/rss/index.xml", "lang": "en"},
    ],
    "sports": [
        {"name": "BBC Sport",  "url": "https://feeds.bbci.co.uk/sport/rss.xml", "lang": "en"},
        {"name": "ESPN",       "url": "https://www.espn.com/espn/rss/news", "lang": "en"},
    ],
    "economy": [
        {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews", "lang": "en"},
        {"name": "한국경제",          "url": "https://www.hankyung.com/feed/all-news", "lang": "ko"},
    ],
    "politics": [
        {"name": "Reuters World", "url": "https://feeds.reuters.com/Reuters/worldNews", "lang": "en"},
        {"name": "연합뉴스",       "url": "https://www.yonhapnewstv.co.kr/category/news/headline/feed/", "lang": "ko"},
    ],
}

ARTICLES_PER_SOURCE = 3  # 소스당 가져올 기사 수


def fetch_news(category: str = "all") -> dict:
    """
    RSS 피드에서 뉴스를 수집한다.
    Args:
        category: tech / sports / economy / politics / all
    Returns:
        카테고리별 기사 목록
    """
    if feedparser is None:
        return {"success": False, "error": "feedparser 미설치. pip install feedparser 실행 필요"}

    categories = list(RSS_FEEDS.keys()) if category == "all" else [category]
    result = {}

    for cat in categories:
        if cat not in RSS_FEEDS:
            continue
        result[cat] = []
        for source in RSS_FEEDS[cat]:
            try:
                feed = feedparser.parse(source["url"])
                articles = []
                for entry in feed.entries[:ARTICLES_PER_SOURCE]:
                    articles.append({
                        "title":   entry.get("title", "No title"),
                        "link":    entry.get("link", ""),
                        "summary": entry.get("summary", entry.get("description", ""))[:300],
                        "source":  source["name"],
                        "lang":    source["lang"],
                    })
                result[cat].extend(articles)
            except Exception as e:
                result[cat].append({"error": f"{source['name']}: {str(e)}"})

    return {"success": True, "fetched_at": datetime.now().isoformat(), "news": result}


def send_email(subject: str, html_body: str, recipient: str = None) -> dict:
    """
    Gmail SMTP로 HTML 이메일을 발송한다.
    .env에서 GMAIL_ADDRESS, GMAIL_APP_PASSWORD를 읽는다.
    Args:
        subject: 이메일 제목
        html_body: HTML 형식 본문
        recipient: 수신자 이메일 (없으면 GMAIL_ADDRESS 사용)
    """
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    app_password   = os.getenv("GMAIL_APP_PASSWORD")
    to_address     = recipient or os.getenv("DIGEST_RECIPIENT", gmail_address)

    if not gmail_address or not app_password:
        return {
            "success": False,
            "error": ".env에 GMAIL_ADDRESS, GMAIL_APP_PASSWORD가 설정되지 않았습니다."
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = gmail_address
        msg["To"]      = to_address
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, app_password)
            server.sendmail(gmail_address, to_address, msg.as_string())

        return {"success": True, "message": f"이메일 발송 완료 → {to_address}"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Gmail 인증 실패. 앱 비밀번호를 확인하세요."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_digest_html(summaries: dict, date_str: str = None) -> str:
    """
    카테고리별 뉴스 요약을 HTML 이메일 형식으로 변환한다.
    Args:
        summaries: {category: {"summary": str, "articles": [...]}} 형태
        date_str: 날짜 문자열 (없으면 오늘 날짜)
    Returns:
        HTML 문자열
    """
    date_str = date_str or datetime.now().strftime("%B %d, %Y")
    category_icons = {
        "tech": "💻", "sports": "⚽", "economy": "📈", "politics": "🏛️"
    }

    sections_html = ""
    for cat, data in summaries.items():
        icon = category_icons.get(cat, "📰")
        summary_text = data.get("summary", "").replace("\n", "<br>")
        articles = data.get("articles", [])

        links_html = ""
        for art in articles:
            lang_badge = "🇰🇷" if art.get("lang") == "ko" else "🇺🇸"
            links_html += f"""
            <div style="margin:6px 0;">
              {lang_badge} <a href="{art['link']}" style="color:#2563eb;text-decoration:none;">
                {art['title']}
              </a>
              <span style="color:#6b7280;font-size:12px;"> — {art['source']}</span>
            </div>"""

        sections_html += f"""
        <div style="background:#f9fafb;border-left:4px solid #2563eb;padding:16px 20px;margin:20px 0;border-radius:0 8px 8px 0;">
          <h2 style="color:#1e3a5f;margin:0 0 10px 0;font-size:18px;">{icon} {cat.upper()}</h2>
          <p style="color:#374151;line-height:1.7;margin:0 0 12px 0;">{summary_text}</p>
          <div style="border-top:1px solid #e5e7eb;padding-top:10px;font-size:13px;">
            <strong style="color:#6b7280;">Sources:</strong>
            {links_html}
          </div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#111;">
      <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:24px;border-radius:12px;margin-bottom:24px;">
        <h1 style="color:white;margin:0;font-size:24px;">🤖 Agent J — Daily Briefing</h1>
        <p style="color:#93c5fd;margin:6px 0 0 0;font-size:14px;">{date_str}</p>
      </div>
      {sections_html}
      <p style="color:#9ca3af;font-size:12px;text-align:center;margin-top:32px;">
        Powered by Agent J · Summaries generated by Claude AI
      </p>
    </body>
    </html>"""


# ── 툴 스키마 ──────────────────────────────────────────────
NEWS_TOOLS = [
    {
        "name": "fetch_news",
        "description": "RSS 피드에서 최신 뉴스 기사를 가져온다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["tech", "sports", "economy", "politics", "all"],
                    "description": "가져올 뉴스 카테고리"
                }
            },
            "required": []
        }
    },
    {
        "name": "send_email",
        "description": "Gmail로 HTML 이메일을 발송한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject":   {"type": "string", "description": "이메일 제목"},
                "html_body": {"type": "string", "description": "HTML 형식 본문"},
                "recipient": {"type": "string", "description": "수신자 이메일 (선택, 기본값: 본인)"}
            },
            "required": ["subject", "html_body"]
        }
    }
]


def fetch_github_trending(language: str = "", since: str = "daily") -> dict:
    """
    GitHub Trending 페이지를 스크래핑해 인기 레포지토리 목록을 반환한다.
    Args:
        language: 필터링할 언어 (python, javascript 등, 빈 문자열이면 전체)
        since:    daily / weekly / monthly
    Returns:
        {"success": True, "repos": [{"name", "desc", "stars", "language", "url"}]}
    """
    if not REQUESTS_AVAILABLE:
        return {"success": False, "error": "requests 미설치. pip install requests 실행 필요"}
    try:
        url = "https://github.com/trending"
        if language:
            url += f"/{language.lower()}"
        url += f"?since={since}"
        headers = {"Accept": "text/html", "User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        # 정규식으로 레포 블록 파싱
        repos = []
        # h2 > a 패턴에서 레포명 추출
        name_pattern = re.findall(
            r'<h2[^>]*>\s*<a[^>]*href="(/[^"]+)"[^>]*>(.*?)</a>', resp.text, re.DOTALL
        )
        desc_pattern = re.findall(r'<p class="col-9[^"]*">(.*?)</p>', resp.text, re.DOTALL)
        star_pattern = re.findall(r'octicon-star.*?</svg>\s*([\d,]+)', resp.text)

        for i, (path, raw_name) in enumerate(name_pattern[:10]):
            name = html_module.unescape(re.sub(r'\s+', ' ', raw_name).strip())
            desc = html_module.unescape(re.sub(r'<[^>]+>', '', desc_pattern[i]).strip()) if i < len(desc_pattern) else ""
            stars = star_pattern[i].strip() if i < len(star_pattern) else "?"
            repos.append({
                "name": name,
                "desc": desc[:120],
                "stars": stars,
                "url": f"https://github.com{path}",
            })
        return {"success": True, "since": since, "language": language or "all", "repos": repos}
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_morning_brief() -> dict:
    """
    모닝 인텔리전스 브리핑 데이터를 수집한다.
    - 오늘의 할 일 (planner)
    - 활성 목표 현황 (career)
    - GitHub Trending (Python/전체)
    - 기술 뉴스 헤드라인 (tech RSS)
    Returns:
        {"success": True, "tasks", "goals", "github", "tech_news", "date"}
    """
    result = {"success": True, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}

    # 1. 오늘의 할 일
    try:
        from tools.planner_tools import load_data as _load_tasks
        data = _load_tasks()
        pending = [t for t in data.get("tasks", []) if t.get("status") == "pending"]
        today = datetime.now().strftime("%Y-%m-%d")
        today_tasks = [t for t in pending if t.get("due_date", "") == today]
        result["tasks"] = {
            "total_pending": len(pending),
            "today": [{"title": t["title"], "priority": t.get("priority", "medium")}
                      for t in today_tasks[:5]],
        }
    except Exception as e:
        result["tasks"] = {"error": str(e)}

    # 2. 활성 목표 현황
    try:
        from tools.career_tools import list_goals
        goals_data = list_goals(status="active")
        goals = goals_data.get("goals", [])
        result["goals"] = {
            "count": len(goals),
            "items": [{"title": g["title"], "progress": g.get("progress", 0),
                       "deadline": g.get("deadline", "")} for g in goals[:4]]
        }
    except Exception as e:
        result["goals"] = {"error": str(e)}

    # 3. GitHub Trending (Python)
    trending = fetch_github_trending(language="python", since="daily")
    result["github"] = trending.get("repos", [])[:5] if trending.get("success") else []

    # 4. 기술 뉴스 헤드라인 (feedparser 사용)
    try:
        news_data = fetch_news(category="tech")
        tech_articles = news_data.get("news", {}).get("tech", [])
        result["tech_news"] = [
            {"title": a["title"], "source": a["source"], "link": a["link"]}
            for a in tech_articles[:5] if "error" not in a
        ]
    except Exception as e:
        result["tech_news"] = []

    return result


# ── 툴 스키마 ──────────────────────────────────────────────
NEWS_TOOLS = [
    {
        "name": "fetch_news",
        "description": "RSS 피드에서 최신 뉴스 기사를 가져온다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["tech", "sports", "economy", "politics", "all"],
                    "description": "가져올 뉴스 카테고리"
                }
            },
            "required": []
        }
    },
    {
        "name": "send_email",
        "description": "Gmail로 HTML 이메일을 발송한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject":   {"type": "string", "description": "이메일 제목"},
                "html_body": {"type": "string", "description": "HTML 형식 본문"},
                "recipient": {"type": "string", "description": "수신자 이메일 (선택, 기본값: 본인)"}
            },
            "required": ["subject", "html_body"]
        }
    },
    {
        "name": "fetch_github_trending",
        "description": "GitHub Trending에서 인기 레포지토리 목록을 가져온다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "언어 필터 (python, javascript 등)"},
                "since":    {"type": "string", "enum": ["daily", "weekly", "monthly"]}
            },
            "required": []
        }
    },
    {
        "name": "fetch_morning_brief",
        "description": "모닝 브리핑용 통합 데이터(할 일, 목표, GitHub Trending, 기술 뉴스)를 수집한다.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """툴 실행 후 JSON 문자열 반환."""
    tool_map = {
        "fetch_news":           fetch_news,
        "send_email":           send_email,
        "fetch_github_trending": fetch_github_trending,
        "fetch_morning_brief":  fetch_morning_brief,
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"알 수 없는 툴: {tool_name}"})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
