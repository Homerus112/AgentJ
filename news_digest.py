"""
news_digest.py  —  Agent J Daily Briefing
GitHub Actions에서 매일 오전 7시(KST)에 자동 실행.

기능:
  - 뉴스 수집 + Claude 요약 (tech / economy / politics / sports)
  - 오늘의 Python·AI 학습 팁 1개
  - Notion 오늘 할 일 (NOTION_API_KEY 있을 때만, 없으면 건너뜀)
  - 월요일: 주간 AI/DS 하이라이트 섹션 추가
  - 금요일: 주간 학습 회고 섹션 추가

로컬 테스트:
    python news_digest.py

GitHub Actions: .github/workflows/daily_news.yml 참조
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TODAY       = datetime.now()
DAY_OF_WEEK = TODAY.weekday()   # 0=월, 4=금, 6=일
IS_MONDAY   = DAY_OF_WEEK == 0
IS_FRIDAY   = DAY_OF_WEEK == 4


# ══════════════════════════════════════════════════════════
# 0. 환경변수 확인
# ══════════════════════════════════════════════════════════
def check_env():
    required = ["ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
    missing  = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"❌ 누락된 환경변수: {', '.join(missing)}")
        sys.exit(1)


# ══════════════════════════════════════════════════════════
# 1. 뉴스 수집
# ══════════════════════════════════════════════════════════
def fetch_all_news() -> dict:
    from tools.news_tools import fetch_news
    print("📡 뉴스 수집 중...")
    result = fetch_news(category="all")
    if not result["success"]:
        print(f"❌ 뉴스 수집 실패: {result['error']}")
        sys.exit(1)
    total = sum(len(v) for v in result["news"].values())
    print(f"✅ 기사 {total}개 수집 완료")
    return result["news"]


# ══════════════════════════════════════════════════════════
# 2. 뉴스 요약 (카테고리별)
# ══════════════════════════════════════════════════════════
def summarize_news(news_by_category: dict, client) -> dict:
    model = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

    category_instructions = {
        "tech":     "Summarize in English. Focus on the most impactful tech development.",
        "sports":   "Summarize in English. Highlight key results or upcoming events.",
        "economy":  "Summarize in English. Include both the global (EN) and Korean (KR) economic angle.",
        "politics": "Summarize in English. Include both the global (EN) and Korean (KR) political angle.",
    }

    summaries = {}
    for cat, articles in news_by_category.items():
        if not articles:
            continue
        print(f"  🤖 {cat} 요약 중...")

        articles_text = ""
        for i, art in enumerate(articles, 1):
            if "error" in art:
                continue
            lang = "(Korean source)" if art.get("lang") == "ko" else "(English source)"
            articles_text += (
                f"{i}. [{art['source']} {lang}] {art['title']}\n"
                f"   {art['summary']}\n"
                f"   URL: {art['link']}\n\n"
            )

        instruction = category_instructions.get(cat, "Summarize in English.")
        prompt = (
            f"Category: {cat.upper()}\n{instruction}\n\nArticles:\n{articles_text}\n"
            "Write a 3-5 sentence analytical summary. Be concise and insightful."
        )

        resp = client.messages.create(
            model=model, max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        summaries[cat] = {
            "summary":  resp.content[0].text,
            "articles": [a for a in articles if "error" not in a],
        }

    print(f"✅ {len(summaries)}개 카테고리 요약 완료")
    return summaries


# ══════════════════════════════════════════════════════════
# 3. 오늘의 학습 팁 (Python · AI · Data Science)
# ══════════════════════════════════════════════════════════
def generate_learning_tip(client) -> str:
    """
    매일 Python/AI/DS 관련 팁 1개를 생성한다.
    월요일엔 주간 AI 트렌드 하이라이트, 금요일엔 학습 회고 프롬프트로 대체한다.
    """
    model = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

    if IS_MONDAY:
        prompt = (
            "You are a data science mentor. It's Monday — start the week strong.\n"
            "Give ONE weekly AI/Data Science highlight: a trending technique, tool, or paper "
            "worth exploring this week. Include: what it is, why it matters, one resource link.\n"
            "Format as plain HTML snippet (no <html>/<body> tags). Keep it under 120 words."
        )
    elif IS_FRIDAY:
        prompt = (
            "You are a data science mentor. It's Friday — time to reflect.\n"
            "Give a SHORT weekly learning reflection template the user can fill out:\n"
            "  • What did I learn this week? (Python / AI / DS)\n"
            "  • What was the hardest part?\n"
            "  • What's my focus for next week?\n"
            "Format as plain HTML snippet with the questions as bold prompts and blank lines after each. "
            "Add a motivating closing line. Keep it under 100 words."
        )
    else:
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day = day_names[DAY_OF_WEEK]
        prompt = (
            f"You are a data science mentor. Today is {day}.\n"
            "Give ONE practical tip on any of: Python, data mining, AI agents, LLMs, or ML engineering.\n"
            "Format: Title (bold), 2-3 sentence explanation, one code snippet or command if applicable.\n"
            "Format as plain HTML snippet (no <html>/<body> tags). Keep it under 100 words."
        )

    print("  🤖 학습 팁 생성 중...")
    resp = client.messages.create(
        model=model, max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text


# ══════════════════════════════════════════════════════════
# 4. Notion 오늘 할 일 조회 (선택 사항)
# ══════════════════════════════════════════════════════════
def fetch_notion_tasks() -> list:
    """
    NOTION_API_KEY + NOTION_TASKS_DB_ID 가 있을 때만 실행.
    없으면 빈 리스트를 반환해 브리핑에서 해당 섹션을 생략한다.
    """
    api_key = os.getenv("NOTION_API_KEY")
    db_id   = os.getenv("NOTION_TASKS_DB_ID")
    if not api_key or not db_id:
        print("  ℹ️  Notion 키 없음 — 할 일 섹션 생략")
        return []

    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        today_str = TODAY.strftime("%Y-%m-%d")
        payload = {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {
                        "or": [
                            {"property": "Due", "date": {"equals": today_str}},
                            {"property": "Due", "date": {"is_empty": True}},
                        ]
                    },
                ]
            },
            "sorts": [{"property": "Due", "direction": "ascending"}],
            "page_size": 10,
        }
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=headers, json=payload, timeout=10,
        )
        if resp.status_code != 200:
            print(f"  ⚠️  Notion API 오류 ({resp.status_code}) — 섹션 생략")
            return []

        tasks = []
        for page in resp.json().get("results", []):
            props = page.get("properties", {})
            # "Name" / "Task" / "Title" / "이름" 속성에서 제목 추출
            for key in ("Name", "Task", "Title", "이름"):
                title_prop = props.get(key, {})
                titles = title_prop.get("title", [])
                if titles:
                    tasks.append({"title": titles[0].get("plain_text", "")})
                    break

        print(f"  ✅ Notion 할 일 {len(tasks)}개 조회")
        return tasks

    except Exception as e:
        print(f"  ⚠️  Notion 조회 실패: {e} — 섹션 생략")
        return []


# ══════════════════════════════════════════════════════════
# 5. HTML 이메일 조립
# ══════════════════════════════════════════════════════════
def build_html(summaries: dict, learning_tip: str, notion_tasks: list) -> str:
    date_str   = TODAY.strftime("%B %d, %Y (%A)")
    cat_labels = {
        "tech": "🖥️ Tech", "economy": "📈 Economy",
        "politics": "🏛️ Politics", "sports": "⚽ Sports",
    }

    html = f"""
<html><head><meta charset="UTF-8">
<style>
  body        {{ font-family: -apple-system, Arial, sans-serif; background:#f5f5f5; margin:0; padding:20px; }}
  .container  {{ max-width:680px; margin:auto; background:#fff; border-radius:12px;
                 box-shadow:0 2px 12px rgba(0,0,0,.08); overflow:hidden; }}
  .header     {{ background: linear-gradient(135deg,#1a1a2e,#16213e); color:#fff;
                 padding:28px 32px; }}
  .header h1  {{ margin:0; font-size:22px; letter-spacing:.5px; }}
  .header p   {{ margin:6px 0 0; opacity:.7; font-size:13px; }}
  .section    {{ padding:22px 32px; border-bottom:1px solid #f0f0f0; }}
  .section h2 {{ font-size:15px; color:#333; margin:0 0 12px; }}
  .tip-box    {{ background:#f0f7ff; border-left:4px solid #3b82f6;
                 border-radius:6px; padding:14px 16px; font-size:14px; line-height:1.6; }}
  .notion-box {{ background:#fafafa; border:1px solid #e8e8e8;
                 border-radius:8px; padding:14px 16px; }}
  .notion-box ul {{ margin:6px 0 0; padding-left:18px; }}
  .notion-box li {{ font-size:14px; color:#444; margin-bottom:4px; }}
  .news-item  {{ margin-bottom:16px; }}
  .news-item h3 {{ font-size:14px; color:#222; margin:0 0 6px; }}
  .news-item p  {{ font-size:13px; color:#555; line-height:1.6; margin:0; }}
  .footer     {{ padding:16px 32px; text-align:center; font-size:12px; color:#aaa; }}
</style></head><body><div class="container">

<div class="header">
  <h1>🤖 Agent J — Daily Briefing</h1>
  <p>{date_str}</p>
</div>
"""

    # 학습 팁 / 주간 하이라이트 / 금요일 회고
    if IS_MONDAY:
        tip_title = "🚀 이번 주 AI/DS 하이라이트"
    elif IS_FRIDAY:
        tip_title = "📓 주간 학습 회고"
    else:
        tip_title = "💡 오늘의 학습 팁"

    html += f"""
<div class="section">
  <h2>{tip_title}</h2>
  <div class="tip-box">{learning_tip}</div>
</div>
"""

    # Notion 할 일
    if notion_tasks:
        items_html = "".join(f"<li>{t['title']}</li>" for t in notion_tasks)
        html += f"""
<div class="section">
  <h2>✅ 오늘의 할 일 (Notion)</h2>
  <div class="notion-box"><ul>{items_html}</ul></div>
</div>
"""

    # 뉴스 카테고리
    for cat, label in cat_labels.items():
        data = summaries.get(cat)
        if not data:
            continue
        articles_html = ""
        for art in data["articles"][:3]:
            articles_html += (
                f'<div class="news-item">'
                f'<h3><a href="{art["link"]}" style="color:#1d4ed8;text-decoration:none;">'
                f'{art["title"]}</a></h3>'
                f'<p>{art["summary"]}</p></div>'
            )
        html += f"""
<div class="section">
  <h2>{label}</h2>
  <p style="font-size:13px;color:#444;line-height:1.6;margin:0 0 14px;">{data["summary"]}</p>
  {articles_html}
</div>
"""

    html += """
<div class="footer">Agent J · Powered by Claude · Auto-generated</div>
</div></body></html>
"""
    return html


# ══════════════════════════════════════════════════════════
# 6. 이메일 발송
# ══════════════════════════════════════════════════════════
def send_digest(html: str):
    from tools.news_tools import send_email
    date_str  = TODAY.strftime("%B %d, %Y")
    subject   = f"🤖 Agent J Daily Briefing — {date_str}"
    recipient = os.getenv("DIGEST_RECIPIENT", os.getenv("GMAIL_ADDRESS"))

    # 날씨 섹션 삽입 (있을 때만)
    try:
        from tools.weather_tools import format_weather_for_email
        weather_html = format_weather_for_email()
        insert_at    = html.find('<div class="section">')
        if insert_at != -1:
            html = html[:insert_at] + weather_html + html[insert_at:]
    except Exception as e:
        print(f"  ⚠️  날씨 정보 생략: {e}")

    print("📧 이메일 발송 중...")
    result = send_email(subject, html, recipient)
    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ 발송 실패: {result['error']}")
        sys.exit(1)


# ══════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════
def main():
    print("=" * 52)
    print(f"  Agent J — Daily Briefing")
    print(f"  {TODAY.strftime('%Y-%m-%d %H:%M:%S')}  "
          f"({'월' if IS_MONDAY else '금' if IS_FRIDAY else '평일'}요일 모드)")
    print("=" * 52)

    check_env()

    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    news         = fetch_all_news()
    summaries    = summarize_news(news, client)
    learning_tip = generate_learning_tip(client)
    notion_tasks = fetch_notion_tasks()

    html = build_html(summaries, learning_tip, notion_tasks)
    send_digest(html)

    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
