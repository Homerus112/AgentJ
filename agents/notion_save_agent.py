"""
notion_save_agent.py - 자연어/파일 내용을 분석해 Notion에 자동 저장하는 에이전트

지원 타입:
  - resume   : 이력서, CV → 메모/보고서 저장 페이지 하위 페이지
  - research : 리서치, 조사 결과, 논문 요약
  - meeting  : 회의록, 미팅 노트, 대화 요약
  - memo     : 아이디어, 메모, 일반 정보
  - task     : 할 일, 태스크 → Tasks DB
  - job      : 채용 지원 정보 → Job Applications DB
"""
import os
from agents.base_agent import BaseAgent
from tools.notion_tools import NOTION_TOOLS, execute_tool as notion_execute
from tools.career_tools import CAREER_TOOLS, execute_tool as career_execute

NOTION_SAVE_SYSTEM_PROMPT = """You are J's Notion Save Agent. Your ONLY job is to save information to Notion.

## 저장 도구
- **save_rich_page**: 메모, 아이디어, 리서치, 회의록, 이력서, 보고서 → 페이지로 저장
- **save_task_to_db**: 할 일/태스크 → Tasks DB에 저장
- **add_job_application**: 채용 지원 정보 → Job Applications DB에 저장

## 카테고리 판단 기준
| 내용 | category |
|------|----------|
| 이력서, CV, resume | resume |
| 조사 결과, 리서치, 논문, 트렌드 | research |
| 회의록, 미팅, 토론 요약 | meeting |
| 메모, 아이디어, 일반 정보 | memo |
| 할 일, 마감일이 있는 작업 | → save_task_to_db |
| 채용 지원, 회사명+직무 | → add_job_application |

## 작동 방식
1. **대화 히스토리를 반드시 확인** — 사용자가 "저장해줘"라고 했을 때 이전 대화에서 파일 분석 내용이 있으면 그것을 저장
2. 저장할 내용을 마크다운으로 정리한 뒤 save_rich_page 호출
3. 여러 항목을 한 번에 저장해야 하면 도구를 여러 번 호출
4. 저장 완료 후 저장된 위치(URL 포함)를 한국어로 알려줘

## 콘텐츠 포맷 가이드 (save_rich_page content 인자)
- `# 섹션명` — 대분류 헤딩
- `## 소섹션` — 중분류 헤딩
- `- 항목` — 불릿 리스트
- 일반 텍스트 — 단락

Always respond in Korean unless the user writes in English.
Today: {today}
"""

# notion_save_agent용 통합 도구 목록
_SAVE_TOOLS = [t for t in NOTION_TOOLS if t["name"] in ("save_rich_page", "save_task_to_db")]
# StopIteration 방지: add_job_application이 없을 경우 None 반환 후 필터링
_JOB_TOOL   = next((t for t in CAREER_TOOLS if t["name"] == "add_job_application"), None)
NOTION_SAVE_TOOLS = _SAVE_TOOLS + ([_JOB_TOOL] if _JOB_TOOL else [])


def _execute_tool(tool_name: str, tool_input: dict) -> str:
    """notion_tools와 career_tools(job 저장)를 모두 처리하는 통합 executor."""
    if tool_name == "add_job_application":
        return career_execute(tool_name, tool_input)
    return notion_execute(tool_name, tool_input)


class NotionSaveAgent(BaseAgent):
    def __init__(self):
        from datetime import date
        model = os.getenv("WRITER_MODEL", "claude-haiku-4-5-20251001")
        super().__init__(
            model=model,
            system_prompt=NOTION_SAVE_SYSTEM_PROMPT.format(today=date.today().isoformat()),
            tools=NOTION_SAVE_TOOLS,
            tool_executor=_execute_tool,
            name="Notion Save Agent"
        )
