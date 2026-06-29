"""brand_agent.py - Personal branding content generation agent (v2)

Platform modes:
  - both (default): generates ### LINKEDIN ### + ### INSTAGRAM ### blocks
  - linkedin only: generates only ### LINKEDIN ### block
  - instagram only: generates only ### INSTAGRAM ### block

Pass [PLATFORM:linkedin] or [PLATFORM:instagram] tag in the message to select single-platform mode.
"""
import os
import re
from agents.base_agent import BaseAgent

# ── 공통 원칙 ──────────────────────────────────────────────────────────────────
_COMMON = (
    "You are Jeremy's personal branding expert and social media copywriter.\n"
    "Transform Jeremy's career, learning, and insights into compelling social media posts.\n\n"
)

_LI_PRINCIPLE = (
    "## LinkedIn Principles\n"
    "- Professional and insightful tone\n"
    "- Start with a hook sentence (storytelling)\n"
    "- Use 3-point structure for key learnings when applicable\n"
    "- End with a Call-to-Action ('What do you think?' style)\n"
    "- English or Korean based on topic\n"
    "- 200-400 words ideal\n"
    "- Include 5-8 relevant hashtags\n\n"
)

_IG_PRINCIPLE = (
    "## Instagram Principles\n"
    "- Emotional, relatable tone\n"
    "- Use emojis actively (1-2 per paragraph)\n"
    "- Short, impactful sentences\n"
    "- Story-driven narrative\n"
    "- Korean preferred\n"
    "- 150-250 characters ideal\n"
    "- Include 10-15 hashtags\n\n"
)

# ── 모드별 시스템 프롬프트 ─────────────────────────────────────────────────────
BRAND_SYSTEM_BOTH = (
    _COMMON
    + "## Output Format (REQUIRED — use EXACT delimiters)\n\n"
    + "### LINKEDIN ###\n[LinkedIn post content]\n[5-8 hashtags]\n\n"
    + "### INSTAGRAM ###\n[Instagram post content with emojis]\n[10-15 hashtags]\n\n"
    + _LI_PRINCIPLE
    + _IG_PRINCIPLE
    + "NEVER omit either delimiter. The two platforms MUST have different content."
)

BRAND_SYSTEM_LINKEDIN = (
    _COMMON
    + "## Output Format (LinkedIn ONLY — use EXACT delimiter)\n\n"
    + "### LINKEDIN ###\n[LinkedIn post content]\n[5-8 hashtags]\n\n"
    + _LI_PRINCIPLE
    + "Generate LinkedIn content ONLY. Do NOT include Instagram section."
)

BRAND_SYSTEM_INSTAGRAM = (
    _COMMON
    + "## Output Format (Instagram ONLY — use EXACT delimiter)\n\n"
    + "### INSTAGRAM ###\n[Instagram post content with emojis]\n[10-15 hashtags]\n\n"
    + _IG_PRINCIPLE
    + "Generate Instagram content ONLY. Do NOT include LinkedIn section."
)

_PLATFORM_PROMPTS = {
    "linkedin":  BRAND_SYSTEM_LINKEDIN,
    "instagram": BRAND_SYSTEM_INSTAGRAM,
    "both":      BRAND_SYSTEM_BOTH,
}


def _extract_platform(message: str) -> tuple[str, str]:
    """메시지에서 [PLATFORM:xxx] 태그를 추출. 반환: (platform, cleaned_message)"""
    match = re.search(r'\[PLATFORM:(linkedin|instagram|both)\]', message, re.IGNORECASE)
    if match:
        platform = match.group(1).lower()
        cleaned  = message[:match.start()].strip() + " " + message[match.end():].strip()
        return platform, cleaned.strip()
    return "both", message


class BrandAgent(BaseAgent):
    def __init__(self):
        # 초기화 시에는 'both' 모드 프롬프트로 시작; run()에서 동적으로 교체
        super().__init__(
            model=os.getenv("DEV_MODEL", "claude-sonnet-4-6"),
            system_prompt=BRAND_SYSTEM_BOTH,
            tools=[],
            tool_executor=lambda name, inp: "{}",
            name="Brand Agent"
        )

    def run(self, message: str, history: list = None) -> str:
        platform, clean_msg = _extract_platform(message)

        # 플랫폼에 따라 시스템 프롬프트 동적 교체
        self.system_prompt = _PLATFORM_PROMPTS.get(platform, BRAND_SYSTEM_BOTH)

        # 브랜드 컨텍스트 주입
        try:
            from tools.brand_tools import get_brand_context
            ctx = get_brand_context()
            if ctx:
                augmented = (
                    f"[Jeremy's Profile Context]\n{ctx}\n\n"
                    f"[Request] {clean_msg}\n\n"
                    "IMPORTANT: Follow the output format in your system prompt exactly."
                )
            else:
                augmented = (
                    f"{clean_msg}\n\n"
                    "IMPORTANT: Follow the output format in your system prompt exactly."
                )
        except Exception:
            augmented = clean_msg

        return super().run(augmented, history)
