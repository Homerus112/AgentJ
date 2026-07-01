"""
server/api.py — Agent J FastAPI 서버 (v3)
- POST /chat, WebSocket /ws/chat
- GET  /health, /memory, /stats, /career, /tasks, /schedule, /history
- POST /memory/remember
- GET/POST/DELETE/PUT /quick-actions
- POST /upload            — 파일 업로드 → 텍스트 추출
- GET  /briefing          — 일일 브리핑 생성 (캐시 1일)
- POST /portfolio/generate — 포트폴리오 자산 생성
- POST /interview/chat    — 면접 코치 대화
- GET  /goal-status       — 목표 드리프트 분석
- POST /notion/push       — 콘텐츠 Notion 저장
"""
import os, sys, json, uuid
from pathlib import Path

# ── PyInstaller --noconsole 모드 대응 ────────────────────────────────────────
# --noconsole 빌드에서 sys.stdout/stderr = None → rich.Console이
# os.get_terminal_size() 호출 시 [Errno 22] Invalid argument 발생.
# 모든 모듈 import 전에 devnull 로 리다이렉트하여 방지.
import io as _io
def _safe_devnull():
    try:
        return open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        return _io.StringIO()

if sys.stdout is None:
    sys.stdout = _safe_devnull()
elif hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        sys.stdout = _safe_devnull()
else:
    try:
        sys.stdout.fileno()
    except (AttributeError, OSError, _io.UnsupportedOperation):
        sys.stdout = _safe_devnull()

if sys.stderr is None:
    sys.stderr = _safe_devnull()
elif hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        sys.stderr = _safe_devnull()
else:
    try:
        sys.stderr.fileno()
    except (AttributeError, OSError, _io.UnsupportedOperation):
        sys.stderr = _safe_devnull()

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
from datetime import date, datetime
from typing import List, Optional, Any

# BASE_DIR 먼저 설정 — .env 경로 탐색에 필요
if getattr(sys, 'frozen', False):
    # PyInstaller exe: resources/server_dist/api_server.exe
    # .env 위치:       resources/.env  (한 단계 위)
    BASE_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(BASE_DIR))
    _env_candidates = [
        BASE_DIR / ".env",           # resources/server_dist/.env
        BASE_DIR.parent / ".env",    # resources/.env  ← 실제 위치
        BASE_DIR.parent.parent / ".env",  # 설치 루트/.env (fallback)
    ]
else:
    BASE_DIR = Path(__file__).parent.parent
    _env_candidates = [BASE_DIR / ".env"]

# .env 파일을 가장 먼저 로드 — Electron spawn 시 환경변수 미상속 문제 방지
from dotenv import load_dotenv
for _env_path in _env_candidates:
    if _env_path.exists():
        load_dotenv(_env_path)
        break
else:
    load_dotenv()  # fallback: 기본 탐색

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Agent J API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 오케스트레이터 ───────────────────────────────────────────────────────────
try:
    from orchestrator.router import Orchestrator
    orchestrator = Orchestrator()
    print("[API] 오케스트레이터 로드 완료")
except Exception as e:
    print(f"[API] 오케스트레이터 로드 실패: {e}")
    orchestrator = None

# ── 전용 에이전트 인스턴스 (lazy) ────────────────────────────────────────────
_interview_agent = None
_portfolio_agent = None
_briefing_agent  = None

def _get_interview_agent():
    global _interview_agent
    if not _interview_agent:
        from agents.interview_agent import InterviewAgent
        _interview_agent = InterviewAgent()
    return _interview_agent

def _get_portfolio_agent():
    global _portfolio_agent
    if not _portfolio_agent:
        from agents.portfolio_agent import PortfolioAgent
        _portfolio_agent = PortfolioAgent()
    return _portfolio_agent

def _get_briefing_agent():
    global _briefing_agent
    if not _briefing_agent:
        from agents.briefing_agent import BriefingAgent
        _briefing_agent = BriefingAgent()
    return _briefing_agent

# ── 퀵 액션 ──────────────────────────────────────────────────────────────────
QUICK_ACTIONS_FILE = DATA_DIR / "quick_actions.json"
DEFAULT_QUICK_ACTIONS = [
    {"id": "qa-stats",    "label": "통계",       "icon": "📊", "command": "/stats",    "send_immediately": True},
    {"id": "qa-memory",   "label": "메모리",      "icon": "🧠", "command": "/memory",   "send_immediately": True},
    {"id": "qa-tasks",    "label": "할 일",       "icon": "✅", "command": "/tasks",    "send_immediately": True},
    {"id": "qa-schedule", "label": "일정",        "icon": "📅", "command": "/schedule", "send_immediately": True},
    {"id": "qa-compress", "label": "메모리 압축", "icon": "💾", "command": "/compress", "send_immediately": True},
    {"id": "qa-reflect",  "label": "오늘 회고",   "icon": "📝", "command": "/reflect",  "send_immediately": True},
    {"id": "qa-weekly",   "label": "주간 리뷰",   "icon": "📆", "command": "/weekly",   "send_immediately": True},
    {"id": "qa-coach",    "label": "목표 코치",   "icon": "🏆", "command": "/coach",    "send_immediately": True},
]

def _load_quick_actions() -> List[dict]:
    if QUICK_ACTIONS_FILE.exists():
        try: return json.loads(QUICK_ACTIONS_FILE.read_text(encoding='utf-8'))
        except: pass
    _save_quick_actions(DEFAULT_QUICK_ACTIONS)
    return DEFAULT_QUICK_ACTIONS

def _save_quick_actions(actions: List[dict]):
    QUICK_ACTIONS_FILE.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding='utf-8')

# ── 슬래시 명령어 ─────────────────────────────────────────────────────────────
def handle_slash_command(message: str):
    msg = message.strip()
    if not msg.startswith('/'):
        return None
    cmd = msg.split()[0].lower()
    args = msg[len(cmd):].strip()

    if not orchestrator:
        return ("서버 초기화 중입니다. 잠시 후 다시 시도해주세요.", "system")

    if cmd == '/help':
        return ("""**Agent J 명령어 목록**

📊 `/stats` — 에이전트 사용 통계
🧠 `/memory` — 저장된 메모리 보기
✅ `/tasks` — 할 일 목록
📅 `/schedule` — 오늘 일정
🎯 `/career` — 커리어 현황
📣 `/brand [주제]` — 브랜드 콘텐츠 생성
📝 `/reflect` — 오늘 회고
📆 `/weekly` — 주간 리뷰
🎓 `/learning` — 학습 진도
🏆 `/coach` — 목표 코치
💾 `/compress` — 장기 메모리 압축
📌 `/remember [내용]` — 영구 메모 저장
❓ `/help` — 이 도움말""", "system")

    if cmd == '/memory':
        try:
            from memory.memory_manager import MemoryManager
            mm = MemoryManager()
            notes = mm.get_notes()
            if notes:
                lines = [f"• [{n['date']}] {n['note']}" for n in notes[-20:]]
                return ("\n".join(lines), "memory")
            return ("저장된 메모가 없습니다.", "memory")
        except Exception as e:
            return (f"메모리 조회 오류: {e}", "memory")

    if cmd == '/stats':
        try:
            from memory.history_db import get_stats
            stats = get_stats()
            lines = ["**에이전트 사용 통계**\n"]
            for item in (stats.get('agent_usage') or []):
                lines.append(f"• {item.get('agent', '?')}: {item.get('c', 0)}회")
            lines.append(f"\n총 메시지: {stats.get('total_messages', 0)}개")
            lines.append(f"총 세션: {stats.get('total_sessions', 0)}개")
            return ("\n".join(lines), "system")
        except Exception as e:
            return (f"통계 조회 오류: {e}", "system")

    if cmd == '/tasks':
        return (orchestrator.route("/tasks 목록을 보여줘"), "planner")

    if cmd == '/schedule':
        today = date.today().strftime('%Y년 %m월 %d일')
        return (orchestrator.route(f"오늘 {today} 일정을 알려줘"), "planner")

    if cmd == '/career':
        full_cmd = f"/career {args}" if args else "/career"
        return (orchestrator.route(full_cmd), "career")

    if cmd == '/brand':
        return (orchestrator.route(f"/brand {args}" if args else "브랜드 콘텐츠를 만들어줘"), "brand")

    if cmd == '/reflect':
        return (orchestrator.route("오늘 하루를 회고해줘"), "reflection")

    if cmd == '/weekly':
        return (orchestrator.route("이번 주 활동을 정리해서 주간 리뷰를 작성해줘"), "reflection")

    if cmd == '/learning':
        return (orchestrator.route("학습 진도와 통계를 알려줘"), "knowledge")

    if cmd == '/coach':
        return (orchestrator.route("목표 드리프트를 점검하고 코칭해줘"), "coach")

    if cmd == '/compress':
        try:
            from memory.long_term_memory import compress
            result = compress(force=True)
            if result.get("success") and not result.get("skipped"):
                return (f"✅ 메모리 압축 완료 ({result.get('week', '')}): {result.get('summary', '')}", "memory")
            return ("메모리 압축 완료 (변경사항 없음)", "memory")
        except Exception as e:
            return (f"메모리 압축 오류: {e}", "memory")

    if cmd == '/remember':
        if not args:
            return ("저장할 내용을 입력해주세요. 예: /remember 파이썬 공부 중", "memory")
        try:
            from memory.memory_manager import MemoryManager
            msg = MemoryManager().add_note(args)
            return (f"✓ {msg}", "memory")
        except Exception as e:
            return (f"저장 오류: {e}", "memory")

    if cmd == '/clear':
        if orchestrator: orchestrator.clear_history()
        return ("대화 히스토리가 초기화되었습니다.", "system")

    return None

# ── Pydantic 모델 ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    agent:    str

class RememberRequest(BaseModel):
    note: str

class QuickActionCreate(BaseModel):
    label:            str
    icon:             str = "⚡"
    command:          str
    send_immediately: bool = True

class InterviewChatRequest(BaseModel):
    message:  str
    history:  List[dict] = []

class PortfolioRequest(BaseModel):
    project_name:  str
    description:   str
    tech_stack:    str
    duration:      Optional[str] = ""
    impact:        Optional[str] = ""
    github_url:    Optional[str] = ""

class NotionPushRequest(BaseModel):
    title:    str
    content:  str
    category: str = "memo"

# ── 기본 엔드포인트 ───────────────────────────────────────────────────────────
@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    slash_result = handle_slash_command(req.message)
    if slash_result:
        return {"response": slash_result[0], "agent": slash_result[1]}
    if not orchestrator:
        raise HTTPException(503, "오케스트레이터 초기화 중")
    response = orchestrator.route(req.message)
    agent    = getattr(orchestrator, 'last_agent', 'general') or 'general'
    return {"response": response, "agent": agent}

@app.get("/memory")
def memory():
    try:
        from memory.memory_manager import MemoryManager
        mm = MemoryManager()
        notes = mm.get_notes()
        return {"notes": [{"date": n.get("date",""), "note": n.get("note","")} for n in notes[-20:]]}
    except: return {"notes": []}

@app.post("/memory/remember")
def remember(req: RememberRequest):
    try:
        from memory.memory_manager import MemoryManager
        msg = MemoryManager().add_note(req.note)
        return {"status": "ok", "message": msg}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/stats")
def stats():
    try:
        from memory.history_db import get_stats
        data = get_stats()
        if "agent_counts" not in data:
            usage = data.get("agent_usage", [])
            data["agent_counts"] = {a.get("agent", ""): a.get("c", 0) for a in usage if a.get("agent")}
        if "total_conversations" not in data:
            data["total_conversations"] = data.get("total_messages", 0)
        return data
    except:
        return {"total_messages": 0, "total_sessions": 0, "total_conversations": 0,
                "agent_usage": [], "agent_counts": {}, "last_used": None}

@app.get("/career")
def career():
    path = DATA_DIR / "career.json"
    if path.exists():
        try: return json.loads(path.read_text(encoding='utf-8'))
        except: pass
    return {"goals": [], "applications": [], "skills": []}

@app.get("/tasks")
def tasks():
    path = DATA_DIR / "tasks.json"
    if path.exists():
        try: return json.loads(path.read_text(encoding='utf-8'))
        except: pass
    return {"tasks": []}

@app.get("/schedule")
def schedule():
    path = DATA_DIR / "schedule.json"
    if path.exists():
        try: return json.loads(path.read_text(encoding='utf-8'))
        except: pass
    return {"events": []}

@app.get("/history")
def history():
    try:
        from memory.history_db import search_messages
        return {"history": search_messages("", limit=50)}
    except: return {"history": []}

# ── 퀵 액션 CRUD ──────────────────────────────────────────────────────────────
@app.get("/quick-actions")
def get_quick_actions():
    return _load_quick_actions()

@app.post("/quick-actions", status_code=201)
def create_quick_action(body: QuickActionCreate):
    actions = _load_quick_actions()
    new_action = {"id": f"qa-{uuid.uuid4().hex[:8]}", **body.dict()}
    actions.append(new_action)
    _save_quick_actions(actions)
    return new_action

@app.delete("/quick-actions/{action_id}", status_code=204)
def delete_quick_action(action_id: str):
    actions = _load_quick_actions()
    updated = [a for a in actions if a["id"] != action_id]
    if len(updated) == len(actions):
        raise HTTPException(404, "퀵 액션을 찾을 수 없습니다")
    _save_quick_actions(updated)

@app.put("/quick-actions/reorder")
def reorder_quick_actions(ids: List[str]):
    actions = _load_quick_actions()
    id_map  = {a["id"]: a for a in actions}
    reordered = [id_map[i] for i in ids if i in id_map]
    _save_quick_actions(reordered)
    return reordered

# ── 파일 업로드 & 텍스트 추출 ─────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 → 텍스트 추출 → {filename, content, chars} 반환"""
    content_bytes = await file.read()
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    text = ""
    try:
        if ext in ("txt", "md", "py", "js", "ts", "tsx", "json", "csv", "html", "css"):
            text = content_bytes.decode("utf-8", errors="ignore")
        elif ext == "pdf":
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join(pages)
        elif ext in ("docx", "doc"):
            import io
            from docx import Document
            doc = Document(io.BytesIO(content_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
        elif ext in ("png", "jpg", "jpeg", "gif", "webp", "bmp"):
            # 이미지: base64 인코딩 후 메타데이터 반환 (채팅창에서 vision agent 통해 분석)
            import base64
            b64 = base64.b64encode(content_bytes).decode()
            size_kb = len(content_bytes) // 1024
            text = (
                f"[첨부 이미지: {filename} ({size_kb}KB)]\n"
                f"이미지 파일이 첨부되었습니다. 채팅창에서 '이 이미지를 분석해줘'라고 입력하면 "
                f"Vision Agent가 상세 분석을 제공합니다.\n"
                f"[BASE64_PREVIEW:{b64[:100]}]"
            )
        else:
            text = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        text = f"[파일 파싱 오류: {e}]"

    # 토큰 초과 방지: 10,000자 제한
    if len(text) > 10000:
        text = text[:10000] + "\n\n[... 내용이 길어 앞부분만 추출됨]"

    return {"filename": filename, "content": text, "chars": len(text)}

# ── 일일 브리핑 ───────────────────────────────────────────────────────────────
BRIEFING_CACHE = DATA_DIR / "briefing_cache.json"

@app.get("/briefing")
def get_briefing(refresh: bool = False):
    """오늘의 브리핑 반환. 당일 캐시 있으면 즉시 반환, 없으면 AI 생성."""
    today_str = date.today().isoformat()

    # 캐시 확인
    if not refresh and BRIEFING_CACHE.exists():
        try:
            cached = json.loads(BRIEFING_CACHE.read_text(encoding="utf-8"))
            if cached.get("date") == today_str:
                return cached
        except: pass

    # 컨텍스트 수집
    schedule_data = {"events": []}
    tasks_data    = {"tasks": []}
    career_data   = {"goals": [], "applications": [], "skills": []}
    try:
        path = DATA_DIR / "schedule.json"
        if path.exists(): schedule_data = json.loads(path.read_text(encoding="utf-8"))
    except: pass
    try:
        path = DATA_DIR / "tasks.json"
        if path.exists(): tasks_data = json.loads(path.read_text(encoding="utf-8"))
    except: pass
    try:
        path = DATA_DIR / "career.json"
        if path.exists(): career_data = json.loads(path.read_text(encoding="utf-8"))
    except: pass

    # D+N 계산
    apps = career_data.get("applications", [])
    app_alerts = []
    for a in apps:
        if a.get("status") in ("applied", "interview") and a.get("applied_date"):
            try:
                from datetime import timedelta
                applied = datetime.strptime(a["applied_date"], "%Y-%m-%d").date()
                days = (date.today() - applied).days
                if days >= 14:
                    app_alerts.append(f"⚠️ {a.get('company','?')} ({a.get('role','?')}) — D+{days} follow-up 시점")
                elif a.get("status") == "interview":
                    app_alerts.append(f"📞 {a.get('company','?')} — 면접 준비 필요")
            except: pass

    context = (
        f"오늘 날짜: {today_str}\n\n"
        f"[일정]\n{json.dumps(schedule_data.get('events', []), ensure_ascii=False)}\n\n"
        f"[할 일]\n{json.dumps(tasks_data.get('tasks', []), ensure_ascii=False)}\n\n"
        f"[지원 알림]\n" + ("\n".join(app_alerts) if app_alerts else "활성 알림 없음")
    )

    try:
        agent = _get_briefing_agent()
        briefing_text = agent.run(context, [])
    except Exception as e:
        briefing_text = f"브리핑 생성 오류: {e}"

    result = {"date": today_str, "briefing": briefing_text, "generated_at": datetime.now().isoformat()}
    try:
        BRIEFING_CACHE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except: pass
    return result

# ── 포트폴리오 생성 ───────────────────────────────────────────────────────────
@app.post("/portfolio/generate")
def portfolio_generate(req: PortfolioRequest):
    """프로젝트 정보 → README + LinkedIn + 이력서 불릿 + 면접 스크립트 생성"""
    prompt = (
        f"프로젝트명: {req.project_name}\n"
        f"설명: {req.description}\n"
        f"기술 스택: {req.tech_stack}\n"
        f"기간: {req.duration or '미입력'}\n"
        f"성과/임팩트: {req.impact or '미입력'}\n"
        f"GitHub URL: {req.github_url or '미입력'}\n\n"
        "위 정보를 바탕으로 4가지 포트폴리오 자산을 생성해주세요."
    )
    try:
        agent = _get_portfolio_agent()
        result = agent.run(prompt, [])
        return {"result": result, "project": req.project_name}
    except Exception as e:
        raise HTTPException(500, f"포트폴리오 생성 오류: {e}")

# ── 면접 코치 대화 ────────────────────────────────────────────────────────────
@app.post("/interview/chat")
def interview_chat(req: InterviewChatRequest):
    """면접 코치와 대화. history는 [{role, content}] 형식."""
    try:
        agent = _get_interview_agent()
        result = agent.run(req.message, req.history)
        return {"response": result, "agent": "interview"}
    except Exception as e:
        raise HTTPException(500, f"면접 코치 오류: {e}")

# ── 목표 드리프트 분석 ────────────────────────────────────────────────────────
@app.get("/goal-status")
def goal_status():
    """최근 대화 패턴 vs 설정 목표 비교 → 드리프트 점수 반환"""
    try:
        from memory.history_db import search_messages
        recent = search_messages("", limit=30)

        career_path = DATA_DIR / "career.json"
        career_data = {}
        if career_path.exists():
            career_data = json.loads(career_path.read_text(encoding="utf-8"))

        goals = career_data.get("goals", [])
        if not goals:
            return {"status": "no_goals", "message": "설정된 목표가 없습니다", "alerts": []}

        # 최근 메시지에서 활동 패턴 추출
        recent_text = " ".join(m.get("content", "") for m in recent if m.get("role") == "user")
        alerts = []
        for g in goals:
            title = g.get("title", "")
            # 간단한 키워드 매칭으로 목표 관련 대화 감지
            keywords = title.lower().split()
            found = any(kw in recent_text.lower() for kw in keywords if len(kw) > 2)
            if not found and g.get("status", "active") == "active":
                alerts.append({
                    "goal": title,
                    "message": f"'{title}' 관련 활동이 최근 대화에서 감지되지 않았습니다",
                    "severity": "warning"
                })

        return {
            "status": "analyzed",
            "total_goals": len(goals),
            "alerts": alerts,
            "alert_count": len(alerts),
            "analyzed_messages": len(recent)
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "alerts": []}

# ── Notion 푸시 ───────────────────────────────────────────────────────────────
@app.post("/notion/push")
def notion_push(req: NotionPushRequest):
    """콘텐츠를 Notion 페이지로 저장"""
    try:
        from tools.notion_tools import save_rich_page
        result = save_rich_page(
            title=req.title,
            content=req.content,
            category=req.category
        )
        if result.get("success"):
            return {"success": True, "url": result.get("url", ""), "message": "Notion 저장 완료"}
        else:
            raise HTTPException(500, result.get("error", "Notion 저장 실패"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Notion 오류: {e}")

# ── 자동 메모리 압축 스케줄러 ──────────────────────────────────────────────────
import asyncio as _asyncio
import asyncio as _ws_asyncio   # WebSocket 핸들러에서도 같은 모듈 사용
import datetime as _dt_mod

async def _auto_compress_loop():
    """주 1회(일요일 새벽 3시) 자동 메모리 압축"""
    print("[스케줄러] 자동 메모리 압축 루프 시작")
    while True:
        now = _dt_mod.datetime.now()
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 3:
            days_until_sunday = 7
        next_run = (now + _dt_mod.timedelta(days=days_until_sunday)).replace(
            hour=3, minute=0, second=0, microsecond=0)
        wait_sec = (next_run - now).total_seconds()
        print(f"[스케줄러] 다음 압축: {next_run.strftime('%Y-%m-%d %H:%M')} (대기 {int(wait_sec//3600)}h)")
        await _asyncio.sleep(wait_sec)
        try:
            from memory.long_term_memory import compress, needs_compression
            if needs_compression():
                result = compress()
                if result.get("success") and not result.get("skipped"):
                    print(f"[스케줄러] ✅ 압축 완료 ({result.get('week', '')})")
        except Exception as e:
            print(f"[스케줄러] 압축 오류: {e}")

@app.on_event("startup")
async def _on_startup():
    _asyncio.create_task(_auto_compress_loop())
    # 에이전트 선행 로딩 (첫 요청 지연 제거)
    _asyncio.create_task(_preload_agents())

async def _preload_agents():
    """startup 시 lazy 에이전트를 미리 초기화해 첫 요청 속도 개선"""
    loop = _asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _get_briefing_agent)
        print("[API] Briefing agent 선행 로드 완료")
    except Exception as e:
        print(f"[API] Briefing agent 선행 로드 실패: {e}")

# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    current_task: "_ws_asyncio.Task | None" = None
    cancelled = False
    loop = _ws_asyncio.get_running_loop()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            message  = data.get("message", "")

            # keepalive ping → pong
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # 취소 신호 처리
            if msg_type == "cancel":
                if current_task and not current_task.done():
                    current_task.cancel()
                cancelled = True
                continue

            if not message:
                continue

            cancelled = False

            await websocket.send_json({
                "type": "thinking",
                "message": "처리 중...",
                "timestamp": _dt_mod.datetime.now().isoformat()
            })

            agent = "general"

            async def process():
                nonlocal agent
                slash_result = handle_slash_command(message)
                if slash_result:
                    return slash_result
                if not orchestrator:
                    return ("서버 초기화 중입니다.", "system")
                resp = await loop.run_in_executor(None, orchestrator.route, message)
                agt  = getattr(orchestrator, 'last_agent', 'general') or 'general'
                return (resp, agt)

            current_task = _ws_asyncio.create_task(process())
            try:
                response, agent = await current_task
            except _ws_asyncio.CancelledError:
                # 취소됨 — 클라이언트가 이미 cancel 처리했으미로 응답 불필요
                continue

            if cancelled:
                continue

            await websocket.send_json({
                "type": "response",
                "content": response,
                "agent": agent,
                "timestamp": _dt_mod.datetime.now().isoformat()
            })

    except WebSocketDisconnect:
        if current_task and not current_task.done():
            current_task.cancel()
    except Exception as e:
        try: await websocket.send_json({"type": "error", "message": str(e)})
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
        reload=False,
        access_log=False,
        log_level="warning",
    )
