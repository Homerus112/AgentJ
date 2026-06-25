# Phase 5 설정 가이드 — Notion & Google Calendar 연동

## 1단계: 패키지 설치

```bash
pip install -r requirements.txt
```

---

## 2단계: Notion 연동

### 2-1. Notion Integration 만들기
1. https://www.notion.so/my-integrations 접속
2. **+ New integration** 클릭
3. 이름: `Agent J` → **Submit**
4. **Internal Integration Secret** 복사 → `.env` 파일에 붙여넣기

```
NOTION_API_KEY=secret_xxxxxxxxxxxx
```

### 2-2. Tasks DB 만들기 (선택)
1. Notion에서 새 페이지 생성 → `/database` → **Table** 선택
2. 컬럼 추가: `Name`(제목), `Status`(선택), `Priority`(선택), `Due`(날짜)
3. 페이지 우상단 `···` → **연결** → **Agent J** 선택
4. 페이지 URL에서 DB ID 복사:
   - URL: `notion.so/워크스페이스/[여기가DB_ID]?v=...`
5. `.env` 에 추가:

```
NOTION_TASKS_DB_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2-3. 기본 상위 페이지 설정 (선택)
메모/보고서를 저장할 Notion 페이지 ID:
```
NOTION_PARENT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2-4. 사용 예시
```
"Notion에 오늘 회의 메모 저장해줘"
"할 일 목록을 Notion DB에 동기화해줘"
"Notion에서 프로젝트 페이지 찾아줘"
```

---

## 3단계: Google Calendar 연동

### 3-1. Google Cloud Console 설정
1. https://console.cloud.google.com 접속
2. 새 프로젝트 만들기 (예: `agent-j`)
3. **APIs & Services** → **Library** → `Google Calendar API` 검색 → **Enable**
4. **APIs & Services** → **Credentials**
   - **+ Create Credentials** → **OAuth 2.0 Client IDs**
   - Application type: **Desktop app**
   - 이름: `Agent J`
   - **Create** 후 **Download JSON** 클릭
5. 다운로드된 파일을 `Agent J` 폴더에 **`credentials.json`** 으로 저장

### 3-2. 최초 인증 (1회만)
```bash
python setup_google_auth.py
```
- 브라우저에서 Google 로그인 → 캘린더 접근 허용
- `data/google_token.json` 자동 생성 (이후 자동 갱신)

### 3-3. 사용 예시
```
"내일 오후 2시 팀 미팅 구글 캘린더에 추가해줘"
"이번 주 구글 캘린더 일정 보여줘"
"'스터디' 관련 캘린더 일정 찾아줘"
```

---

## 현재 가능한 Planner 명령어 전체

| 기능 | 예시 |
|------|------|
| 할 일 추가 | "보고서 작성 할 일 추가해줘, 마감 7월 1일" |
| 할 일 목록 | "/tasks" 또는 "오늘 할 일 보여줘" |
| 일정 추가 | "내일 오후 3시 팀 미팅 일정 추가" |
| 일정 보기 | "/schedule" |
| Google Calendar 조회 | "구글 캘린더 이번 주 일정 보여줘" |
| Google Calendar 추가 | "6월 30일 오전 10시 면접 구글에 추가" |
| Notion 동기화 | "할 일 목록 Notion에 동기화해줘" |
| Notion 메모 | "Notion에 회의록 페이지 만들어줘" |

---

## 트러블슈팅

| 오류 | 해결 |
|------|------|
| `notion-client 미설치` | `pip install notion-client` |
| `NOTION_API_KEY 없음` | `.env` 파일 확인 |
| `credentials.json 없음` | Google Cloud Console에서 재다운로드 |
| `Google 인증 필요` | `python setup_google_auth.py` 재실행 |
| `google 패키지 미설치` | `pip install -r requirements.txt` |
