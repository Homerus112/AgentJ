# 🤖 Agent J — 나만의 로컬 AI 어시스턴트

> **Claude API 기반 멀티 에이전트 AI 어시스턴트**  
> 오케스트레이터가 질문을 분석해 전문 서브에이전트에게 라우팅하는 구조

---

## 📌 프로젝트 개요

Agent J는 하나의 LLM이 모든 것을 처리하는 대신, **오케스트레이터 + 전문 서브에이전트** 구조로 작동합니다.  
사용자의 질문 의도를 분석해 가장 적합한 에이전트에게 작업을 위임하고, 각 에이전트는 전용 도구(tool)를 활용해 결과를 반환합니다.

---

## 🏗️ 아키텍처

```
사용자 입력
    │
    ▼
Orchestrator (claude-haiku)
├── 키워드 선처리 (날씨, 채용 추가 등) → 직접 tool 호출 (토큰 절약)
└── LLM 라우팅 → 에이전트 선택
        │
        ├── 💻 Dev Agent (claude-sonnet)
        ├── 📅 Planner Agent (claude-haiku) ← Google Calendar 자동 동기화
        ├── ✍️  Writer Agent (claude-sonnet)
        ├── 📰 News Agent (claude-haiku)
        ├── 📊 Slide Agent (claude-sonnet)
        ├── 🎯 Career Agent (claude-haiku)
        └── 🔬 Research Agent (claude-sonnet)
```

---

## ✅ 구축된 기능 (Phase 0 ~ 6)

### Phase 0 — 프로젝트 구조 및 환경 설정
- 폴더 구조 설계, `.env` 기반 API 키 관리
- `venv` 가상환경, `requirements.txt`

### Phase 1 — 오케스트레이터 + 핵심 에이전트
- **Orchestrator**: LLM 라우팅 + 키워드 폴백
- **Dev Agent**: 코드 작성, 디버깅, 파일 조작
- **Planner Agent**: 할 일 관리, 일정 추가/조회

### Phase 2 — Writer · News · 뉴스 자동화
- **Writer Agent**: 에세이 첨삭, 문서 정리
- **News Agent**: RSS 피드 기반 뉴스 브리핑
- **GitHub Actions**: 매일 오전 7시 KST 뉴스 이메일 자동 발송

### Phase 3 — Slide · Career
- **Slide Agent**: `python-pptx` 기반 발표자료 자동 생성
- **Career Agent**: 커리어 목표·기술 스택 관리

### Phase 4 — 지속 메모리 시스템
- `memory/memory_manager.py`: 세션 간 대화 히스토리 유지
- `/remember`, `/memory`, `/stats` 명령어
- 에이전트 사용 통계 추적

### Phase 5 — 외부 서비스 연동
- **Notion**: 할 일 동기화, 리서치 결과 페이지 저장
- **Google Calendar**: OAuth 2.0 기반 일정 추가·조회
- **Research Agent**: DuckDuckGo 무료 검색 → 요약 → Notion 저장

### Phase 6 — 대시보드 · Reflection · Job Tracker · 날씨
- **웹 대시보드** (`Flask`): `localhost:5000`에서 대화 히스토리 검색·열람
- **Reflection Agent**: `/reflect`로 오늘 하루 회고 생성 → Notion 저장
- **Job Tracker**: 채용 지원 내역 Notion DB 관리 (`/jobs`)
- **Weather Tool**: OpenWeatherMap API 실시간 날씨 조회 (토큰 소모 없음)
- **Daily Reflection 자동화**: `python main.py --reflect` (작업 스케줄러 연동 가능)

### 버그픽스 및 개선
- `/schedule` 일정 추가 시 **로컬 저장 + Google Calendar 자동 동기화** 동시 실행
- Planner Agent 툴 이름 중복(`delete_event`) 제거 → `delete_gcal_event`로 분리
- 날씨 키워드(`날씨`, `기온`, `비 오나` 등) 라우터 선처리 추가

---

## 🗂️ 폴더 구조

```
Agent J/
├── main.py                          ← 진입점
├── orchestrator/
│   └── router.py                    ← LLM 라우팅 + 키워드 선처리
├── agents/
│   ├── base_agent.py
│   ├── dev_agent.py
│   ├── planner_agent.py
│   ├── writer_agent.py
│   ├── news_agent.py
│   ├── slide_agent.py
│   ├── career_agent.py
│   ├── research_agent.py
│   └── reflection_agent.py
├── tools/
│   ├── file_tools.py
│   ├── planner_tools.py             ← 일정 추가 시 Google Calendar 자동 동기화
│   ├── news_tools.py
│   ├── slide_tools.py
│   ├── career_tools_v2.py           ← Notion Job Tracker
│   ├── notion_tools.py
│   ├── gcal_tools.py
│   ├── research_tools.py
│   ├── reflection_tools.py
│   └── weather_tools.py
├── memory/
│   ├── memory_manager.py            ← 세션 간 지속 메모리
│   ├── history_db.py                ← 대화 히스토리 DB (SQLite)
│   └── context.json
├── web/
│   ├── app.py                       ← Flask 대시보드
│   └── templates/index.html
├── data/
│   ├── tasks.json
│   ├── schedule.json
│   └── career.json
├── news_digest.py                   ← GitHub Actions 뉴스 이메일
├── .github/workflows/daily_news.yml ← 매일 7시 KST 자동 실행
├── setup_google_auth.py             ← Google Calendar OAuth 초기 인증 (1회)
├── run.bat                          ← Agent J 실행
├── start_dashboard.bat              ← 웹 대시보드 실행
└── requirements.txt
```

---

## ⚙️ 설치 및 실행

### 1. 환경 설정

```bash
git clone https://github.com/your-username/agent-j.git
cd agent-j

python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install flask requests notion-client
```

### 2. `.env` 파일 생성

```env
# 필수
ANTHROPIC_API_KEY=sk-ant-...

# 날씨 (https://openweathermap.org 무료 발급)
OPENWEATHER_API_KEY=...
OPENWEATHER_CITY=Seoul

# Notion
NOTION_API_KEY=ntn_...
NOTION_TASKS_DB_ID=...
NOTION_PARENT_PAGE_ID=...
NOTION_JOBS_DB_ID=...

# 모델 설정 (비용 최적화)
ORCHESTRATOR_MODEL=claude-haiku-4-5-20251001
PLANNER_MODEL=claude-haiku-4-5-20251001
DEV_MODEL=claude-sonnet-4-6
```

### 3. Google Calendar 초기 인증 (1회)

```bash
python setup_google_auth.py
```

### 4. 실행

```bash
# Agent J 시작
python main.py

# 또는 배치 파일
run.bat

# 오늘 회고 자동 생성
python main.py --reflect

# 웹 대시보드 (localhost:5000)
start_dashboard.bat
```

---

## 💬 사용 예시

| 입력 | 라우팅 |
|------|--------|
| "파이썬으로 CSV 읽는 코드 짜줘" | Dev Agent |
| "내일 오후 3시 팀 미팅 추가해줘" | Planner Agent + Google Calendar |
| "오늘 테크 뉴스 요약해줘" | News Agent |
| "AI 트렌드 발표자료 8장 만들어줘" | Slide Agent |
| "Google SWE 인턴 지원 추가해줘" | Career → Notion Job Tracker |
| "GPT-4o 논문 조사해줘" | Research Agent → Notion 저장 |
| "오늘 날씨 어때?" | Weather Tool (토큰 소모 없음) |
| `/reflect` | Reflection Agent → Notion 저장 |
| `/jobs` | Job Tracker 조회 |
| `/schedule` | 일정 조회 |
| `/stats` | 에이전트 사용 통계 |
| `/dashboard` | 웹 대시보드 열기 |

---

## 🔧 주요 설계 결정

- **비용 최적화**: 라우터는 Haiku, 고품질 작업(Dev·Writer·Slide)만 Sonnet 사용
- **키워드 선처리**: 날씨 등 반복 요청은 LLM 없이 tool 직접 호출로 토큰 절약
- **Google Calendar 이중 저장**: `add_event` 호출 시 로컬 JSON + Google Calendar 동시 저장 (gcal 실패해도 로컬 보존)
- **세션 지속 메모리**: 종료 후에도 이전 대화 히스토리 유지 (SQLite)
- **GitHub Actions**: 뉴스 이메일 자동화 (Anthropic 크레딧 사용)

---

## 📦 주요 의존성

| 패키지 | 용도 |
|--------|------|
| `anthropic` | Claude API |
| `rich` | 터미널 UI |
| `python-pptx` | 슬라이드 생성 |
| `notion-client` | Notion 연동 |
| `google-api-python-client` | Google Calendar |
| `feedparser` | RSS 뉴스 파싱 |
| `flask` | 웹 대시보드 |
| `requests` | 날씨·검색 API |

---

## 🚧 향후 계획

- [ ] 음성 입력 지원
- [ ] 모바일 인터페이스
- [ ] 에이전트 간 협업 (multi-hop routing)
- [ ] 벡터 DB 기반 장기 메모리
