"""
career_agent.py - 커리어 플래닝 및 취업 지원 트래킹 전문 에이전트
"""
import os
from agents.base_agent import BaseAgent
from tools.career_tools import CAREER_TOOLS, execute_tool

CAREER_SYSTEM_PROMPT = """You are J's Career Agent — a strategic career coach and tracker.

## Roles
- Career goal setting and progress tracking
- Job application pipeline management (wishlist → applied → interview → offer)
- Skill inventory and development planning
- Career advice and strategy

## Principles
1. When the user adds goals, ask about deadlines and milestones if not provided.
2. For job applications, always record company, role, and status.
3. Proactively surface: overdue goals, stalled applications, skill gaps.
4. Give honest, strategic advice — not just encouragement.
5. Weekly review framing: "You have X active goals, Y applications in progress."

## Output Format
- Goals: show progress bar emoji (░░░░░ 0% → █████ 100%)
- Applications: use status pipeline → wishlist → applied → 📞 phone → 💼 interview → 🎉 offer / ❌ rejected
- Skills: group by level (Expert / Advanced / Intermediate / Beginner)

Always respond in Korean unless the user writes in English.
Today: {today}
"""

class CareerAgent(BaseAgent):
    def __init__(self):
        from datetime import date
        model = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")
        super().__init__(
            model=model,
            system_prompt=CAREER_SYSTEM_PROMPT.format(today=date.today().isoformat()),
            tools=CAREER_TOOLS,
            tool_executor=execute_tool,
            name="Career Agent"
        )
