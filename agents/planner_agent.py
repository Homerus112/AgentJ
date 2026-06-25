"""
planner_agent.py - Planner Agent (Phase 5 업그레이드)
할 일 관리 + Google Calendar + Notion 연동
Claude Haiku 사용 (빠르고 저렴함, 반복 작업 최적).
"""

import os, json
from agents.base_agent import BaseAgent
from tools.planner_tools import PLANNER_TOOLS, execute_tool as planner_execute
from tools.notion_tools  import NOTION_TOOLS,  execute_tool as notion_execute
from tools.gcal_tools    import GCAL_TOOLS,    execute_tool as gcal_execute

# 세 도구셋 합치기
ALL_TOOLS = PLANNER_TOOLS + NOTION_TOOLS + GCAL_TOOLS

def execute_tool(tool_name: str, tool_input: dict) -> str:
    planner_names = {t["name"] for t in PLANNER_TOOLS}
    notion_names  = {t["name"] for t in NOTION_TOOLS}
    gcal_names    = {t["name"] for t in GCAL_TOOLS}
    if tool_name in planner_names:
        return planner_execute(tool_name, tool_input)
    elif tool_name in notion_names:
        return notion_execute(tool_name, tool_input)
    elif tool_name in gcal_names:
        return gcal_execute(tool_name, tool_input)
    return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})


PLANNER_SYSTEM_PROMPT = """당신은 'J'의 Planner Agent입니다. 체계적인 업무 관리 전문가입니다.

## 역할
- 할 일(To-do) 추가, 조회, 완료, 삭제, 수정
- 일정(Schedule) 추가, 조회, 삭제
- Google Calendar 일정 조회·추가·삭제·검색
- Notion DB/페이지 생성 및 동기화

## 원칙
1. 요청을 받으면 즉시 툴을 실행하고 결과를 보고하라.
2. 여러 개의 할 일을 한 번에 요청받으면 하나씩 순서대로 추가하라.
3. 목록 조회 시 우선순위 순(high → medium → low)으로 정렬해 표시하라.
4. 마감일이 임박한 항목은 ⚠️ 표시를 붙여라.
5. "Google Calendar" 또는 "구글 캘린더" 언급 시 gcal 툴을 우선 사용하라.
6. "Notion" 언급 시 notion 툴을 사용하라.
7. 일정 충돌이 있으면 알림을 줘라.

## 출력 형식
- 할 일 목록: 번호, 우선순위 이모지(🔴/🟡/🟢), 제목, 마감일 순으로 표시
- 일정: 날짜 → 시간 → 제목 순으로 표시
- 완료/추가 후에는 간단한 확인 메시지를 출력하라.

오늘 날짜: {today}
"""

class PlannerAgent(BaseAgent):
    """할 일, 일정, Google Calendar, Notion 통합 관리 에이전트."""

    def __init__(self):
        from datetime import date
        model = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")
        system = PLANNER_SYSTEM_PROMPT.format(today=date.today().isoformat())
        super().__init__(
            model=model,
            system_prompt=system,
            tools=ALL_TOOLS,
            tool_executor=execute_tool,
            name="Planner Agent"
        )
