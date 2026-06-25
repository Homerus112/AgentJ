"""
news_digest.py
GitHub Actions에서 매일 7시(KST)에 실행되는 독립 스크립트.
뉴스 수집 → Claude 요약 → Gmail 발송을 순서대로 처리한다.

로컬 테스트:
    python news_digest.py

GitHub Actions에서는 자동으로 실행됨 (.github/workflows/daily_news.yml 참조).
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── 환경변수 확인 ──────────────────────────────────────────
def check_env():
    required = ["ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"❌ 누락된 환경변수: {', '.join(missing)}")
        print("   .env 파일 또는 GitHub Secrets를 확인하세요.")
        sys.exit(1)

# ── 뉴스 수집 ──────────────────────────────────────────────
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

# ── Claude로 카테고리별 요약 생성 ──────────────────────────
def summarize_news(news_by_category: dict) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model  = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")
    summaries = {}

    category_instructions = {
        "tech":     "Summarize in English. Focus on the most impactful tech development.",
        "sports":   "Summarize in English. Highlight key results or upcoming events.",
        "economy":  "Summarize in English. Include both the global (EN) and Korean (KR) economic angle separately.",
        "politics": "Summarize in English. Include both the global (EN) and Korean (KR) political angle separately.",
    }

    for cat, articles in news_by_category.items():
        if not articles:
            continue
        print(f"  🤖 {cat} 요약 중...")

        # 기사 텍스트 구성
        articles_text = ""
        for i, art in enumerate(articles, 1):
            if "error" in art:
                continue
            lang_label = "(Korean source)" if art.get("lang") == "ko" else "(English source)"
            articles_text += f"{i}. [{art['source']} {lang_label}] {art['title']}\n   {art['summary']}\n   URL: {art['link']}\n\n"

        instruction = category_instructions.get(cat, "Summarize in English.")
        prompt = f"""Category: {cat.upper()}
{instruction}

Articles:
{articles_text}

Write a 3-5 sentence analytical summary. Be concise and insightful."""

        response = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        summaries[cat] = {
            "summary":  response.content[0].text,
            "articles": [a for a in articles if "error" not in a]
        }

    print(f"✅ {len(summaries)}개 카테고리 요약 완료")
    return summaries

# ── 이메일 발송 ────────────────────────────────────────────
def send_digest(summaries: dict):
    from tools.news_tools import format_digest_html, send_email

    date_str = datetime.now().strftime("%B %d, %Y")
    subject  = f"🤖 Agent J Daily Briefing — {date_str}"
    html     = format_digest_html(summaries, date_str)

    print("📧 이메일 발송 중...")
    recipient = os.getenv("DIGEST_RECIPIENT", os.getenv("GMAIL_ADDRESS"))
    result = send_email(subject, html, recipient)

    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ 발송 실패: {result['error']}")
        sys.exit(1)

# ── 메인 ──────────────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"  Agent J — Daily News Digest")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    check_env()
    news      = fetch_all_news()
    summaries = summarize_news(news)
    send_digest(summaries)

    print("\n✅ 완료!")

if __name__ == "__main__":
    main()
