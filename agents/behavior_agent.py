"""behavior_agent.py — 행동/습관 패턴 분석 에이전트"""
import os
from agents.base_agent import BaseAgent

BEHAVIOR_SYSTEM_PROMPT = """당신은 Jeremy의 행동 패턴 분석 전문가입니다.
대화 내역과 메모리를 분석하여 생산성 패턴, 습관, 행동 트렌드를 파악합니다.
한국어로 답변하며, 데이터 기반의 구체적인 인사이트를 제공합니다."""


class BehaviorAgent(BaseAgent):
    def __init__(self):
        # BaseAgent는 model, system_prompt, tools, tool_executor 모두 필요
        super().__init__(
            model=os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001"),
            system_prompt=BEHAVIOR_SYSTEM_PROMPT,
            tools=[],
            tool_executor=lambda name, inp: "{}",
            name="Behavior Agent"
        )

    def run(self, message: str, history: list = None) -> str:
        try:
            from tools.behavior_tools import analyze_patterns
            patterns = analyze_patterns()
            augmented = f"행동 패턴 데이터:\n{patterns}\n\n요청: {message}" if patterns else message
        except Exception:
            augmented = message
        # BaseAgent.run()으로 정상 실행 (tool 없이 순수 LLM 호출)
        return super().run(augmented, history)
