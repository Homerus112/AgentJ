"""
dev_agent.py
코드 작성, 디버깅, 파일 조작을 담당하는 Dev Agent.
Claude Sonnet 사용 (코드 품질 최우선).
"""

import os
from agents.base_agent import BaseAgent
from tools.file_tools import DEV_TOOLS, execute_tool

DEV_SYSTEM_PROMPT = """당신은 'J'의 Dev Agent입니다. 숙련된 풀스택 개발자이자 코드 멘토 역할을 합니다.

## 역할
- 코드 작성, 수정, 디버깅
- 파일 읽기/쓰기/실행
- 기술적 문제 해결 및 설명

## 원칙
1. 코드에는 항상 한국어 주석을 포함하라.
2. 코드 실행 전 반드시 계획을 먼저 설명하라.
3. 오류 발생 시 원인과 해결방법을 명확히 설명하라.
4. 초보자도 이해할 수 있게 로직을 단계별로 설명하라.
5. 보안 위험이 있는 코드(rm -rf, 시스템 파일 삭제 등)는 실행하지 말고 경고하라.

## 출력 형식
- 코드는 항상 마크다운 코드블록(```python)으로 감싸라.
- 설명 → 코드 → 실행 결과 순서로 구성하라.
- 마지막에 "다음에 시도해볼 것:" 섹션을 추가하라.

오늘 날짜: {today}
"""

GIT_KEYWORDS = ["git push", "git commit", "git status", "git log", "git pull",
                "커밋해줘", "푸시해줘", "push해줘", "commit해줘", "깃 상태", "깃 푸시"]


class DevAgent(BaseAgent):
    """코드 작성 및 파일 조작 전문 에이전트."""

    def __init__(self):
        from datetime import date
        model = os.getenv("DEV_MODEL", "claude-sonnet-4-6")
        system = DEV_SYSTEM_PROMPT.format(today=date.today().isoformat())
        super().__init__(
            model=model,
            system_prompt=system,
            tools=DEV_TOOLS,
            tool_executor=execute_tool,
            name="Dev Agent"
        )

    def run(self, user_message: str, history: list = None) -> str:
        """git 관련 요청은 git_tools로 직접 처리, 나머지는 기본 agentic loop."""
        msg_lower = user_message.lower()
        if any(kw in msg_lower for kw in GIT_KEYWORDS):
            import re
            from tools.git_tools import handle_git_command, git_status, git_log, git_pull
            if "status" in msg_lower or "상태" in msg_lower:
                return git_status()
            elif "log" in msg_lower or "로그" in msg_lower:
                return git_log()
            elif "pull" in msg_lower:
                r = git_pull()
                return f"✅ Pull 완료\n```\n{r['output']}\n```" if r["success"] else f"❌ {r['output']}"
            else:
                quote = re.search(r'["\'](.+?)["\']', user_message)
                args  = f'push "{quote.group(1)}"' if quote else "push"
                return handle_git_command(args)
        return super().run(user_message, history)
