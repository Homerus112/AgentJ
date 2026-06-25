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
Agents:
- dev: code, files, debugging, programming, 코드, 파일, 버그, 파이썬
- planner: tasks, schedule, calendar, Google Calendar, 할 일, 일정, 스케줄, 캘린더, 구글 캘린더, 등록, 예약
- writer: editing, essay, translation, 에세이, 문서, 첨삭, 번역
- news: news, briefing, 뉴스, 브리핑
- slide: presentation, pptx, 발표, 슬라이드
- career: career, resume, job applications, 커리어, 이력서, 취업
- research: web search, investigate, 조사, 리서치, 검색해줘, 찾아봐줘
- general: everything else
Reply ONLY in JSON: {"agent": "dev"|"planner"|"writer"|"news"|"slide"|"career"|"research"|"general", "reason": "one line"}"""

GENERAL_SYSTEM_PROMPT = f"""You are 'J', a friendly AI assistant. Answer in Korean unless the user writes in English. Today: {date.today().isoformat()}"""


class Orchestrator:
    def __init__(self):
        self.api_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        from memory.memory_manager import MemoryManager
        self.memory = MemoryManager()

        self.conversation_history = self.memory.load_recent_history()
        if self.conversation_history:
            console.print(f"[dim]  이전 대화 {len(self.conversation_history)//2}턴 로드됨[/dim]")

        self._dev_agent = self._planner_agent = self._writer_agent = None
        self._news_agent = self._slide_agent = self._career_agent = None
        self._research_agent = None
        self.last_agent = None

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
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        self.memory.update_agent_stat(agent_name)

    def _handle_weather(self, user_message: str) -> str:
        try:
            from tools.weather_tools import get_weather_summary
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

    def _handle_job_add(self, user_message: str) -> str:
        try:
            from tools.career_tools_v2 import add_job_application
            parse_resp = self.api_client.messages.create(
                model=ROUTER_MODEL, max_tokens=200,
                system='사용자 입력에서 채용 정보를 추출해서 JSON으로만 응답하세요: {"company":"","role":"","status":"Applied","applied_date":null,"link":"","notes":""}',
                messages=[{"role": "user", "content": user_message}]
            )
            info = json.loads(parse_resp.content[0].text)
            result = add_job_application(**{k: v for k, v in info.items() if v})
            if result["success"]:
                return f"✅ **{result['company']}** — {result['role']} 지원 내역을 Notion에 추가했어요!"
            return f"❌ 추가 실패: {result.get('error')}"
        except Exception as e:
            return f"채용 정보를 파싱하지 못했어요. 예시: 'Google SWE 인턴 지원 추가해줘'\n오류: {e}"

    def save_and_exit(self):
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
            "dev":      ["code","python","bug","debug","function","script","execute","implement","코드","파이썬","버그","오류","함수","실행","구현"],
            "planner":  ["todo","task","schedule","deadline","reminder","calendar","할 일","일정","스케줄","추가","완료","삭제","목록","캘린더","구글 캘린더","예약","등록해"],
            "writer":   ["edit","essay","translate","draft","report","rewrite","proofread","첨삭","문서","에세이","번역","보고서","글쓰기","편집"],
            "news":     ["news","briefing","headline","latest","뉴스","테크","경제","스포츠","정치","브리핑"],
            "slide":    ["slide","presentation","pptx","deck","발표","슬라이드","프레젠테이션","피티"],
            "career":   ["career","resume","job","application","interview","goal","skill","커리어","이력서","취업","지원","면접","목표","스킬"],
            "research": ["조사","리서치","검색해줘","알아봐줘","찾아봐줘","research","investigate","lookup","찾아줘"],
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
