"""
base_agent.py
모든 하위 에이전트의 기반 클래스.
공통 API 호출 로직, 툴 실행 루프를 여기서 관리한다.
"""

import json
import os
from typing import Callable
import anthropic
from rich.console import Console
from rich.markdown import Markdown

console = Console()


class BaseAgent:
    """
    하위 에이전트들이 상속받는 기반 클래스.

    - self.client: Anthropic API 클라이언트
    - self.model: 사용할 모델명
    - self.system_prompt: 에이전트의 역할 지시문
    - self.tools: API에 등록할 툴 스키마 목록
    - self.tool_executor: 툴 이름 → 실행 함수 매핑
    """

    def __init__(
        self,
        model: str,
        system_prompt: str,
        tools: list,
        tool_executor: Callable[[str, dict], str],
        name: str = "Agent"
    ):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.tools = tools
        self.tool_executor = tool_executor
        self.name = name

        # 사용자 맞춤 프로필을 시스템 프롬프트에 자동 주입
        try:
            from agents.personalization_agent import get_profile_injection
            self.system_prompt = system_prompt + get_profile_injection()
        except Exception:
            self.system_prompt = system_prompt

    def run(self, user_message: str, conversation_history: list = None) -> str:
        """
        사용자 메시지를 받아 에이전트를 실행하고 최종 응답을 반환한다.

        내부적으로 툴 호출이 필요하면 자동으로 실행 후 결과를 다시 LLM에 전달한다.
        (agentic loop)

        Args:
            user_message: 사용자 입력
            conversation_history: 이전 대화 내역 (멀티턴 지원)
        Returns:
            에이전트의 최종 텍스트 응답
        """
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        console.print(f"\n[dim]▶ {self.name} 처리 중...[/dim]")

        while True:
            # API 호출
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools if self.tools else [],
                messages=messages
            )

            # 툴 호출이 없는 경우 → 최종 텍스트 반환
            if response.stop_reason == "end_turn":
                final_text = self._extract_text(response)
                return final_text

            # 툴 호출이 있는 경우 → 실행 후 결과를 messages에 추가
            if response.stop_reason == "tool_use":
                # 어시스턴트 메시지 (툴 호출 포함) 추가
                messages.append({"role": "assistant", "content": response.content})

                # 각 툴 실행
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        console.print(f"[dim]  🔧 툴 실행: {block.name}({json.dumps(block.input, ensure_ascii=False)})[/dim]")
                        result = self.tool_executor(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # 툴 결과를 user 역할로 추가 (Anthropic API 규격)
                messages.append({"role": "user", "content": tool_results})
                # 루프 계속 → 다시 LLM 호출
                continue

            # 예상치 못한 stop_reason
            break

        return "[오류] 응답을 처리할 수 없습니다."

    def _extract_text(self, response) -> str:
        """응답에서 텍스트 블록만 추출해 합친다."""
        texts = []
        for block in response.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts)
