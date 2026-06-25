"""
router.py - Orchestrator 'J' routing logic with persistent memory.
"""
import json, os
from datetime import date
import anthropic
from rich.console import Console

console = Console()
ROUTER_MODEL = os.getenv("ORCHESTRATOR_MODEL", "claude-haiku-4-5-20251001")

ROUTER_SYSTEM_PROMPT = """You are the orchestrator for 'J'. Decide which agent to route to.
Agents: dev (code/files), planner (tasks/schedule), writer (editing/drafts), news (news/briefing), slide (presentations/pptx), career (goals/job applications/skills), general (other)
Reply ONLY in JSON: {"agent": "dev"|"planner"|"writer"|"news"|"slide"|"career"|"general", "reason": "one line"}"""

GENERAL_SYSTEM_PROMPT = f"""You are 'J', a friendly AI assistant. Answer in Korean unless the user writes in English. Today: {date.today().isoformat()}"""


class Orchestrator:
    def __init__(self):
        self.api_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # 메모리 매니저 초기화 (세션 간 기억 유지)
        from memory.memory_manager import MemoryManager
        self.memory = MemoryManager()

        # 이전 세션 히스토리 불러오기
        self.conversation_history = self.memory.load_recent_history()
        if self.conversation_history:
            console.print(f"[dim]  이전 대화 {len(self.conversation_history)//2}턴 로드됨[/dim]")

        self._dev_agent = self._planner_agent = self._writer_agent = None
        self._news_agent = self._slide_agent = self._career_agent = None

    @property
    def dev_agent(self):
        if not self._dev_agent:
            from agents.dev_agent import DevAgent
            self._dev_agent = DevAgent()
        return self._dev_agent

    @property
    def planner_agent(self):
        if not self._planner_agent:
            from agents.planner_agent import PlannerAgent
            self._planner_agent = PlannerAgent()
        return self._planner_agent

    @property
    def writer_agent(self):
        if not self._writer_agent:
            from agents.writer_agent import WriterAgent
            self._writer_agent = WriterAgent()
        return self._writer_agent

    @property
    def news_agent(self):
        if not self._news_agent:
            from agents.news_agent import NewsAgent
            self._news_agent = NewsAgent()
        return self._news_agent

    @property
    def slide_agent(self):
        if not self._slide_agent:
            from agents.slide_agent import SlideAgent
            self._slide_agent = SlideAgent()
        return self._slide_agent

    @property
    def career_agent(self):
        if not self._career_agent:
            from agents.career_agent import CareerAgent
            self._career_agent = CareerAgent()
        return self._career_agent

    def route(self, user_message: str) -> str:
        agent_name, reason = self._decide_agent(user_message)
        console.print(f"[dim]  -> {agent_name} ({reason})[/dim]")

        if agent_name == "dev":
            response = self.dev_agent.run(user_message, self.conversation_history)
        elif agent_name == "planner":
            response = self.planner_agent.run(user_message, self.conversation_history)
        elif agent_name == "writer":
            response = self.writer_agent.run(user_message, self.conversation_history)
        elif agent_name == "news":
            response = self.news_agent.run(user_message, self.conversation_history)
        elif agent_name == "slide":
            response = self.slide_agent.run(user_message, self.conversation_history)
        elif agent_name == "career":
            response = self.career_agent.run(user_message, self.conversation_history)
        else:
            response = self._handle_general(user_message)

        # 히스토리 + 통계 업데이트
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        self.memory.update_agent_stat(agent_name)
        return response

    def save_and_exit(self):
        """종료 시 현재 세션을 메모리에 저장한다."""
        self.memory.save_session(self.conversation_history)

    def _decide_agent(self, user_message: str) -> tuple:
        try:
            resp = self.api_client.messages.create(
                model=ROUTER_MODEL, max_tokens=100,
                system=ROUTER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}]
            )
            d = json.loads(resp.content[0].text.strip())
            return d.get("agent", "general"), d.get("reason", "")
        except Exception:
            return self._keyword_fallback(user_message), "keyword fallback"

    def _keyword_fallback(self, message: str) -> str:
        msg = message.lower()
        kw = {
            "dev":     ["code","python","bug","debug","function","script","execute","implement","코드","파이썬","버그","오류","함수","실행","구현"],
            "planner": ["todo","task","schedule","deadline","reminder","할 일","일정","스케줄","추가","완료","삭제","목록"],
            "writer":  ["edit","essay","translate","draft","report","rewrite","proofread","첨삭","문서","에세이","번역","보고서","글쓰기","편집"],
            "news":    ["news","briefing","headline","latest","뉴스","테크","경제","스포츠","정치","브리핑"],
            "slide":   ["slide","presentation","pptx","deck","발표","슬라이드","프레젠테이션","피티"],
            "career":  ["career","resume","job","application","interview","goal","skill","커리어","이력서","취업","지원","면접","목표","스킬"],
        }
        scores = {k: sum(1 for w in v if w in msg) for k, v in kw.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "general"

    def _handle_general(self, user_message: str) -> str:
        msgs = list(self.conversation_history) + [{"role": "user", "content": user_message}]
        resp = self.api_client.messages.create(
            model=ROUTER_MODEL, max_tokens=1024,
            system=GENERAL_SYSTEM_PROMPT, messages=msgs
        )
        return resp.content[0].text

    def clear_history(self):
        self.conversation_history = []
        console.print("[yellow]대화 히스토리가 초기화되었습니다.[/yellow]")
