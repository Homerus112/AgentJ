"""
router.py - Orchestrator 'J' routing logic with persistent memory.
"""
import json, os, sys, io
from datetime import date
import anthropic
from rich.console import Console

# stdout이 None이거나 유효하지 않을 때 (PyInstaller --noconsole) safe fallback
def _make_safe_console() -> Console:
    try:
        if sys.stdout is None:
            raise OSError("stdout is None")
        sys.stdout.fileno()
        return Console()
    except (AttributeError, OSError, io.UnsupportedOperation):
        return Console(file=open(os.devnull, "w"), highlight=False)

console = _make_safe_console()

def _cprint(*args, **kwargs):
    """console.print safe wrapper — I/O 오류를 무시한다."""
    try:
        console.print(*args, **kwargs)  # noqa — intentional direct call
    except Exception:
        pass

ROUTER_MODEL = os.getenv("ORCHESTRATOR_MODEL", "claude-haiku-4-5-20251001")

ROUTER_SYSTEM_PROMPT = """You are the orchestrator for 'J'. Decide which agent to route to.
Agents:
- dev: code, files, debugging, git, programming, 코드, 파일, 버그, 파이썬, git
- planner: tasks, schedule, calendar, Google Calendar, 할 일, 일정, 스케줄, 캘린더, 등록, 예약
- writer: writing, editing, essay, Word document, .docx, web research + document, 문서, 에세이, 첨삭, 번역, 워드, 조사 후 문서
- news: news, briefing, morning brief, 뉴스, 브리핑, 모닝, 아침 브리핑
- career: career, resume, job applications, 커리어, 이력서, 취업, 지원 현황, 면접 준비, 채용
- research: web search, papers, arxiv, github trending, hackernews, latest AI, 조사, 리서치, 논문, 트렌딩, 검색해줘
- vision: image/PDF analysis, 이미지 분석, pdf 분석, 사진, 스크린샷, 차트
- notion_save: save to Notion, 노션에 저장, 저장해줘, 기록해줘, 노션에, save this, 노션 저장
- knowledge: URL processing, YouTube/GitHub/article analysis, 지식 저장, 지식 검색, URL이 포함된 메시지 (http:// or https://)
- coach: 목표 코치, 드리프트, 주간 리뷰, 목표 점검, goal coach, weekly review, /coach
- behavior: 행동 패턴 분석, 습관 분석, 습관 트렌드, behavior pattern, habit analysis
- general: everything else

IMPORTANT: If the user's reply is a short confirmation or follow-up, route to the SAME agent as the previous turn.
Reply ONLY in JSON: {"agent": "dev"|"planner"|"writer"|"news"|"career"|"research"|"vision"|"notion_save"|"knowledge"|"coach"|"behavior"|"general", "reason": "one line"}"""

def _build_general_prompt() -> str:
    """장기 메모리 + 자기 반성 컨텍스트를 포함한 General 시스템 프롬프트를 생성한다."""
    base = f"You are 'J', a friendly AI assistant. Answer in Korean unless the user writes in English. Today: {date.today().isoformat()}"
    extras = []
    try:
        from memory.long_term_memory import get_long_term_context
        lt = get_long_term_context()
        if lt:
            extras.append(lt)
    except Exception:
        pass
    try:
        from memory.self_reflection import get_reflection_context
        ref = get_reflection_context()
        if ref:
            extras.append(ref)
    except Exception:
        pass
    try:
        from agents.hermes_agent import get_hermes_context
        hc = get_hermes_context()
        if hc:
            extras.append(hc)
    except Exception:
        pass
    return base + ("\n\n" + "\n".join(extras) if extras else "")

# 주의: 이 값은 캐시 목적으로만 사용. _handle_general 에서 세션마다 재빌드함.
_GENERAL_PROMPT_CACHE: str = ""


class Orchestrator:
    def __init__(self):
        self.api_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        from memory.memory_manager import MemoryManager
        self.memory = MemoryManager()

        self.conversation_history = self.memory.load_recent_history()
        if self.conversation_history:
            _cprint(f"[dim]  이전 대화 {len(self.conversation_history)//2}턴 로드됨[/dim]")

        self._dev_agent = self._planner_agent = self._writer_agent = None
        self._news_agent = self._career_agent = None
        self._research_agent = self._notion_save_agent = None
        self._knowledge_agent = self._coach_agent = None
        self._behavior_agent = None
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

    @property
    def notion_save_agent(self):
        if not self._notion_save_agent:
            from agents.notion_save_agent import NotionSaveAgent
            self._notion_save_agent = NotionSaveAgent()
        return self._notion_save_agent

    @property
    def knowledge_agent(self):
        if not self._knowledge_agent:
            from agents.knowledge_agent import KnowledgeAgent
            self._knowledge_agent = KnowledgeAgent()
        return self._knowledge_agent

    @property
    def coach_agent(self):
        if not self._coach_agent:
            from agents.coach_agent import CoachAgent
            self._coach_agent = CoachAgent()
        return self._coach_agent

    @property
    def behavior_agent(self):
        if not self._behavior_agent:
            from agents.behavior_agent import BehaviorAgent
            self._behavior_agent = BehaviorAgent()
        return self._behavior_agent

    def route(self, user_message: str) -> str:
        # URL 선처리 — http/https URL이 포함된 메시지는 knowledge agent로
        if ("http://" in user_message or "https://" in user_message) and \
           not any(kw in user_message.lower() for kw in ["노션에 저장", "저장해줘", "기록해줘"]):
            self.last_agent = "knowledge"
            _cprint(f"[dim]  -> knowledge (URL detected)[/dim]")
            response = self._run_agent("knowledge", user_message)
            self._update_history(user_message, response, "knowledge")
            return response

        # 날씨 키워드 선처리
        weather_kw = ["날씨", "기온", "비 오나", "비와", "우산", "덥나", "춥나", "weather"]
        if any(kw in user_message.lower() for kw in weather_kw):
            self.last_agent = "weather"
            _cprint(f"[dim]  -> weather (keyword fallback)[/dim]")
            response = self._handle_weather(user_message)
            self._update_history(user_message, response, "weather")
            return response

        # Notion 저장 키워드 선처리
        save_kw = ["노션에 저장", "notion에 저장", "저장해줘", "저장해 줘", "기록해줘",
                   "노션에 기록", "노션 저장", "저장 해줘", "save this", "save to notion"]
        if any(kw in user_message.lower() for kw in save_kw):
            self.last_agent = "notion_save"
            _cprint(f"[dim]  -> notion_save (keyword fallback)[/dim]")
            response = self._run_agent("notion_save", user_message)
            self._update_history(user_message, response, "notion_save")
            return response

        # 채용 지원 추가 키워드 선처리
        job_add_kw = ["지원 추가", "채용 추가", "잡 추가", "지원했어", "지원함", "지원했다"]
        if any(kw in user_message for kw in job_add_kw):
            self.last_agent = "career"
            response = self._handle_job_add(user_message)
            self._update_history(user_message, response, "career")
            return response

        # 짧은 확인/긍정 답변 → 직전 에이전트로 계속 라우팅
        # 버그 수정: or 연산자 우선순위로 인해 last_agent 가드가 우회되던 문제 수정
        # "일", "시"는 너무 흔한 글자라 오탐 위험이 높아 제거
        short_confirm = ["응", "맞아", "맞아!", "yes", "네", "그래", "그렇게 해줘", "ㅇㅇ", "ok", "좋아"]
        short_followup = ["맞아", "응", "네", "ㅇㅇ"]
        if self.last_agent and self.last_agent not in ("general", "weather") and (
            any(user_message.strip().lower().startswith(w) for w in short_confirm)
            or (len(user_message.strip()) < 15 and any(w in user_message for w in short_followup))
        ):
            agent_name = self.last_agent
            _cprint(f"[dim]  -> {agent_name} (context follow-up)[/dim]")
            response = self._run_agent(agent_name, user_message)
            self._update_history(user_message, response, agent_name)
            return response

        agent_name, reason = self._decide_agent(user_message)
        _cprint(f"[dim]  -> {agent_name} ({reason})[/dim]")
        self.last_agent = agent_name

        response = self._run_agent(agent_name, user_message)
        self._update_history(user_message, response, agent_name)

        # 학습 자동 감지 — 오류가 나도 대화 흐름에 영향 없음
        try:
            from tools.learning_tools import auto_detect_and_log
            result = auto_detect_and_log(user_message, response)
            if result.get("saved"):
                _cprint(
                    f"[dim]  📚 학습 기록: {result['topic']} ({result['category']})[/dim]"
                )
        except Exception:
            pass

        return response

    def _run_agent(self, agent_name: str, user_message: str) -> str:
        self.last_agent = agent_name
        if agent_name == "dev":
            return self.dev_agent.run(user_message, self.conversation_history)
        elif agent_name == "planner":
            return self.planner_agent.run(user_message, self.conversation_history)
        elif agent_name == "writer":
            return self.writer_agent.run(user_message, self.conversation_history)
        elif agent_name == "news":
            return self.news_agent.run(user_message, self.conversation_history)
        elif agent_name == "career":
            return self.career_agent.run(user_message, self.conversation_history)
        elif agent_name == "research":
            return self._handle_research(user_message)
        elif agent_name == "notion_save":
            return self.notion_save_agent.run(user_message, self.conversation_history)
        elif agent_name == "knowledge":
            return self.knowledge_agent.run(user_message, self.conversation_history)
        elif agent_name == "coach":
            return self.coach_agent.run(user_message, self.conversation_history)
        elif agent_name == "behavior":
            return self.behavior_agent.run(user_message, self.conversation_history)
        elif agent_name == "vision":
            from agents.vision_agent import run as vision_run
            return vision_run(user_message, self.conversation_history)
        else:
            return self._handle_general(user_message)

    def _update_history(self, user_message: str, response: str, agent_name: str):
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        self.memory.update_agent_stat(agent_name)

    def _handle_research(self, user_message: str) -> str:
        """KB(헤르메스) 우선 검색 → 없으면 실시간 웹 조사."""
        kb_context = ""
        try:
            from tools.hermes_tools import search_kb
            hits = search_kb(user_message, top_k=3)
            if hits:
                lines = []
                for h in hits:
                    label = h.get("title") or h.get("repo", "")
                    body  = h.get("summary") or h.get("desc", "")
                    src   = h.get("source", "").upper()
                    lines.append(f"[{src}] {label}: {body[:200]}")
                kb_context = "\n".join(lines)
        except Exception:
            pass

        if kb_context:
            augmented = (
                f"{user_message}\n\n"
                f"[헤르메스 지식 베이스]\n{kb_context}"
            )
            return self.research_agent(augmented)
        return self.research_agent(user_message)

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
            from tools.career_tools import add_job_application
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

        # 자기 반성 루프 (3턴 이상 대화했을 때만)
        try:
            from memory.self_reflection import run_self_reflection
            result = run_self_reflection(self.conversation_history)
            if result.get("success"):
                _cprint(f"[dim]  🔄 자기 반성 저장: {result.get('next_session_note', '')}[/dim]")
        except Exception:
            pass

        # 주기가 됐으면 장기 메모리 자동 압축
        try:
            from memory.long_term_memory import compress, needs_compression
            if needs_compression():
                _cprint("[dim]  🧠 장기 메모리 압축 중...[/dim]")
                result = compress()
                if result.get("success") and not result.get("skipped"):
                    _cprint(f"[dim]  ✅ 장기 메모리 압축 완료 ({result.get('week', '')})[/dim]")
        except Exception:
            pass

    def _decide_agent(self, user_message: str) -> tuple:
        try:
            context_msgs = self.conversation_history[-2:] if self.conversation_history else []
            context_msgs.append({"role": "user", "content": user_message})
            resp = self.api_client.messages.create(
                model=ROUTER_MODEL,
                max_tokens=60,          # 라우팅 응답은 짧음 → 40자 절약으로 속도 개선
                system=ROUTER_SYSTEM_PROMPT,
                messages=context_msgs
            )
            raw = resp.content[0].text.strip()
            # JSON 블록 제거 (```json ... ``` 형태 방어)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            d = json.loads(raw)
            return d.get("agent", "general"), d.get("reason", "")
        except Exception:
            return self._keyword_fallback(user_message), "keyword fallback"

    def _keyword_fallback(self, message: str) -> str:
        msg = message.lower()
        kw = {
            "dev":      ["code","python","bug","debug","function","script","execute","implement","코드","파이썬","버그","오류","함수","실행","구현","git","push","commit","커밋","푸시"],
            "planner":  ["todo","task","schedule","deadline","reminder","calendar","할 일","일정","스케줄","추가","완료","삭제","목록","캘린더","구글 캘린더","예약","등록해"],
            "writer":   ["edit","essay","translate","draft","report","rewrite","proofread","docx","word","워드","첨삭","문서","에세이","번역","보고서","글쓰기","편집","조사 후 정리","웹서핑 후"],
            "news":     ["news","briefing","headline","latest","뉴스","테크","경제","스포츠","정치","브리핑"],
            "career":   ["career","resume","job","application","interview","goal","skill","커리어","이력서","취업","지원","면접","목표","스킬"],
            "research": ["조사","리서치","검색해줘","알아봐줘","찾아봐줘","research","investigate","lookup","찾아줘",
                         "논문","arxiv","트렌딩","깃흥 트렌딩","해커뉴스","hn","최신 ai","최신 ml","지식베이스"],
            "vision":       ["이미지 분석","사진 분석","pdf 분석","스크린샷","차트 분석",".png",".jpg",".pdf","분석해줘"],
            "notion_save":  ["노션에 저장","저장해줘","기록해줘","노션 저장","save this","노션에 기록"],
            "knowledge":    ["지식 저장","지식 검색","지식 목록","아티클 저장","유튜브 분석","youtube","github.com","youtu.be"],
            "coach":        ["목표 코치","드리프트","주간 리뷰","목표 점검","코치","weekly review"],
            "behavior":     ["행동 패턴","습관 분석","행동 분석","습관 트렌드","behavior pattern","habit"],
        }
        scores = {k: sum(1 for w in v if w in msg) for k, v in kw.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "general"

    def _handle_general(self, user_message: str) -> str:
        # 최신 장기메모리/자기반성 컨텍스트 반영 (모듈 로드 시 1회가 아닌 매 호출 시)
        system_prompt = _build_general_prompt()
        msgs = list(self.conversation_history) + [{"role": "user", "content": user_message}]
        resp = self.api_client.messages.create(
            model=ROUTER_MODEL, max_tokens=2048,
            system=system_prompt, messages=msgs
        )
        return resp.content[0].text

    def clear_history(self):
        self.conversation_history = []
        _cprint("[yellow]대화 히스토리가 초기화되었습니다[/yellow]")
