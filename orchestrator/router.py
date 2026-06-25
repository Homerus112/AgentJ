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
Agents: dev (code/files), planner (tasks/schedule), writer (editing/drafts), news (news/briefing), slide (presentations/pptx), career (goals/job applications/skills), research (web search/investigate/lookup), general (other)
Reply ONLY in JSON: {"agent": "dev"|"planner"|"writer"|"news"|"slide"|"career"|"research"|"general", "reason": "one line"}"""

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
        self._research_agent = None
        self.last_agent = None  # 마지막 사용 에이전트 (히스토리 저장용)

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

    @property
    def research_agent(self):
        if not self._research_agent:
            from agents.research_agent import run_research
            self._research_agent = run_research
        return self._research_agent

    def route(self, user_message: str) -> str:
        # 날씨 키워드 선처리
        weather_kw = ["날씨", "기온", "비 오나", "비와", "우산", "덥나", "춥나", "weather"]
        if any(kw in user_message.lower() for kw in weather_kw):
            self.last_agent = "weather"
            console.print(f"[dim]  -> weather (keyword fallback)[/dim]")
            response = self._handle_weather(user_message)
            self._update_history(user_message, response, "weather")
            return response

        # 채용 지원 추가 키워드 선처리
        job_add_kw = ["지원 추가", "채용 추가", "잡 추가", "지원했어", "지원함", "지원했다"]
        if any(kw in user_message for kw in job_add_kw):
            self.last_agent = "career"
            response = self._handle_job_add(user_message)
            self._update_history(user_message, response, "career")
            return response

        agent_name, reason = self._decide_agent(user_message)
        console.print(f"[dim]  -> {agent_name} ({reason})[/dim]")
        self.last_agent = agent_name

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
        elif agent_name == "research":
            response = self.research_agent(user_message)
        else:
            response = self._handle_general(user_message)

        self._update_history(user_message, response, agent_name)
        return response

    def _update_history(self, user_message: str, response: str, agent_name: str):
        """히스토리 + 통계 업데이트 (공통)"""
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        self.memory.update_agent_stat(agent_name)

    def _handle_weather(self, user_message: str) -> str:
        """날씨 정보 처리"""
        try:
            from tools.weather_tools import get_weather_summary
            # 도시명 추출 (간단한 키워드 매핑)
            city = None
            city_map = {"부산": "Busan", "인천": "Incheon", "대구": "Daegu",
                        "대전": "Daejeon", "광주": "Gwangju", "제주": "Jeju"}
            for kor, eng in city_map.items():
                if kor in user_message:
                    city = eng
                    break
            return get_weather_summary(city)
        except Exception as e:
            return f"날씨 정보를 가져오지 못했어요. 오류: {e}"

    def _handle_job_add(self, user_messa