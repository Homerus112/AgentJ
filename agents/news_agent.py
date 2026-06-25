"""
news_agent.py
뉴스 수집, 요약, 이메일 발송을 담당하는 News Agent.
Claude Haiku 사용 (빠르고 저렴한 요약 최적화).
"""

import os
from agents.base_agent import BaseAgent
from tools.news_tools import NEWS_TOOLS, execute_tool

NEWS_SYSTEM_PROMPT = """You are J's News Agent — a sharp news analyst and briefing writer.

## Roles
- Fetch and summarize news by category (tech, sports, economy, politics)
- Write concise, insight-driven summaries in English
- For economy and politics: include both English and Korean sources
- Send formatted news digests via email on request

## Summary Style
- 3–5 sentences per category, analytical tone
- Lead with the most significant development
- Note key implications or "why it matters"
- Economy/Politics: briefly contrast the Korean and global perspective

## Output Format (when summarizing for chat)
**[CATEGORY ICON] CATEGORY**
[3–5 sentence summary]
Sources: [Article 1 title](url) · [Article 2 title](url)

## Tool Usage
1. Call fetch_news first to get raw articles
2. Summarize the fetched content
3. If asked to send email, call send_email with the formatted HTML

Today's date: {today}
"""

class NewsAgent(BaseAgent):
    """뉴스 수집 및 이메일 브리핑 전문 에이전트."""

    def __init__(self):
        from datetime import date
        model = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")
        system = NEWS_SYSTEM_PROMPT.format(today=date.today().isoformat())
        super().__init__(
            model=model,
            system_prompt=system,
            tools=NEWS_TOOLS,
            tool_executor=execute_tool,
            name="News Agent"
        )
