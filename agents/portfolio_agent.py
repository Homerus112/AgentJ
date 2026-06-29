"""portfolio_agent.py - 프로젝트 설명 → 4가지 포트폴리오 자산 자동 생성"""
import os
from agents.base_agent import BaseAgent

PORTFOLIO_SYSTEM = """You are J's Portfolio Builder. Transform project details into polished career assets.

## Output Format (REQUIRED — use EXACT delimiters)

### README ###
[Full GitHub README: title, badges row, description paragraph, key features (bullets), tech stack, quick-start commands, architecture note if relevant]

### LINKEDIN ###
[LinkedIn post: compelling hook → brief story → key achievement → lesson/insight → CTA question → 5-8 hashtags]
[English or Korean based on project language/audience]

### RESUME_BULLET ###
[2-3 bullet points in XYZ format: "Accomplished [X] by implementing [Y], resulting in [Z]" — use numbers/percentages wherever possible]

### INTERVIEW_SCRIPT ###
[2-3 minute spoken answer for "이 프로젝트에 대해 설명해 주세요": situation → your specific role and actions → technical decisions → measurable outcome → what you learned]
[Natural speech, first person, ~350-450 words]

## Quality Rules
- README: Professional, proper markdown, include code blocks for installation
- LinkedIn: Hook MUST be a compelling first sentence people will stop scrolling for
- Resume bullets: Start with strong action verbs (Built, Developed, Reduced, Improved, Designed, Led)
- Interview script: Make it sound natural when spoken aloud, not like reading a report

NEVER skip any delimiter. Output all 4 sections in order.
Respond section labels in Korean context, content in appropriate language for audience.
"""

class PortfolioAgent(BaseAgent):
    def __init__(self):
        model = os.getenv("DEV_MODEL", "claude-sonnet-4-6")
        super().__init__(
            model=model,
            system_prompt=PORTFOLIO_SYSTEM,
            tools=[],
            tool_executor=lambda name, inp: "{}",
            name="Portfolio Agent"
        )
