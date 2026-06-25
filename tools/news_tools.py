"""
news_tools.py
News Agent용 RSS 뉴스 수집 및 이메일 발송 도구.

뉴스 소스 구성:
  Tech      → TechCrunch, The Verge (English)
  Sports    → BBC Sport, ESPN (English)
  Economy   → Reuters Business (EN) + 한국경제 (KR)
  Politics  → Reuters World (EN) + 연합뉴스 (KR)
"""

import json
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

try:
    import feedparser
except ImportError:
    feedparser = None

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


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """툴 실행 후 JSON 문자열 반환."""
    tool_map = {"fetch_news": fetch_news, "send_email": send_email}
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"알 수 없는 툴: {tool_name}"})
    return json.dumps(tool_map[tool_name](**tool_input), ensure_ascii=False)
