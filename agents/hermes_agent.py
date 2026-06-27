"""
agents/hermes_agent.py  —  헤르메스: 지식 수집 + 요약 + 대화 연동 에이전트

역할:
  1. 수동 실행: python agents/hermes_agent.py  (즉시 수집)
  2. GitHub Actions: 매주 월요일 자동 실행 (weekly_knowledge.yml)
  3. J 대화에서 "최근 논문", "트렌딩 레포", "HN 뭐 있어?" 등 질문 시 라우팅
  4. J 시스템 프롬프트에 최신 지식 요약 주입 → J가 "읽은 것처럼" 대화

비용: 수집 무료 + Haiku 요약 ~$0.01/실행 (주 1회 → 월 $0.04)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from dotenv import load_dotenv
from tools.hermes_tools import collect_all, search_kb, get_kb_summary, _load_kb

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL  = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

SUMMARY_PATH = Path(__file__).parent.parent / "data" / "hermes_digest.json"


# ──────────────────────────────────────────────────────────
# 수집 후 AI 요약 생성
# ──────────────────────────────────────────────────────────

def run_collect_and_summarize() -> dict:
    """
    수집 → Haiku 요약 → hermes_digest.json 저장
    GitHub Actions 또는 수동 실행 시 호출.
    """
    print("=" * 50)
    print(f"  헤르메스 에이전트 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    kb = collect_all()

    # ArXiv 논문 요약
    arxiv_text = ""
    for p in kb.get("arxiv", [])[:5]:
        arxiv_text += f"- {p['title']}: {p['summary'][:150]}\n"

    # GitHub 트렌딩 요약
    github_text = ""
    for r in kb.get("github", [])[:5]:
        github_text += f"- {r['repo']}: {r['desc'][:100]}\n"

    # HN 요약
    hn_text = ""
    for h in kb.get("hackernews", [])[:5]:
        hn_text += f"- {h['title']}\n"

    prompt = f"""다음은 이번 주 AI/데이터사이언스 관련 최신 자료입니다.
데이터사이언스를 공부하는 학생을 위해 핵심 인사이트를 한국어로 요약하세요.

[ArXiv 최신 논문]
{arxiv_text or '없음'}

[GitHub 주간 트렌딩]
{github_text or '없음'}

[Hacker News 주요 뉴스]
{hn_text or '없음'}

출력 형식 (JSON):
{{
  "headline": "이번 주 가장 주목할 트렌드 한 문장",
  "arxiv_pick": "주목할 논문 1개와 이유 (50자)",
  "github_pick": "주목할 레포 1개와 이유 (50자)",
  "hn_pick": "주목할 뉴스 1개와 이유 (50자)",
  "study_tip": "이번 주 공부해볼 만한 키워드/기술 1가지"
}}"""

    print("🤖 Haiku 요약 생성 중...")
    resp   = client.messages.create(
        model=MODEL, max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    digest = json.loads(resp.content[0].text.strip())
    digest["generated_at"] = datetime.now().isoformat()

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✅ 헤르메스 요약 저장 완료")
    print(f"   헤드라인: {digest.get('headline', '')}")
    return digest


# ──────────────────────────────────────────────────────────
# J 대화 연동 — 질문 응답
# ──────────────────────────────────────────────────────────

def run(user_message: str, history: list = None) -> str:
    """
    J 오케스트레이터에서 헤르메스로 라우팅될 때 호출.
    knowledge_base를 검색해서 답변.
    """
    # 키워드 추출 후 KB 검색
    search_results = search_kb(user_message, top_k=4)
    kb_context     = ""

    if search_results:
        kb_context = "\n".join(
            f"[{r['source'].upper()}] {r.get('title') or r.get('repo', '')}: "
            f"{r.get('summary') or r.get('desc', '')[:150]}"
            for r in search_results
        )

    # 최신 digest가 있으면 추가
    digest_context = ""
    if SUMMARY_PATH.exists():
        try:
            d = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
            digest_context = (
                f"\n최신 헤드라인: {d.get('headline', '')}\n"
                f"주목할 논문: {d.get('arxiv_pick', '')}\n"
                f"이번 주 키워드: {d.get('study_tip', '')}"
            )
        except Exception:
            pass

    system = (
        "당신은 Agent J의 헤르메스 에이전트입니다. "
        "ArXiv 논문, GitHub 트렌딩, Hacker News 정보를 바탕으로 "
        "데이터사이언스 학생에게 유익한 정보를 제공합니다. "
        "지식 베이스에 없는 내용은 모른다고 솔직히 말하세요. "
        "항상 한국어로 답변하되 기술 용어는 영어 유지."
    )

    messages = []
    if kb_context or digest_context:
        messages.append({
            "role": "user",
            "content": f"[지식 베이스]\n{kb_context}\n{digest_context}"
        })
        messages.append({
            "role": "assistant",
            "content": "지식 베이스를 확인했습니다. 질문해주세요."
        })
    messages.append({"role": "user", "content": user_message})

    resp = client.messages.create(
        model=MODEL, max_tokens=800,
        system=system, messages=messages
    )
    return resp.content[0].text


# ──────────────────────────────────────────────────────────
# 시스템 프롬프트 주입용
# ──────────────────────────────────────────────────────────

def get_hermes_context() -> str:
    """
    Orchestrator 시스템 프롬프트에 삽입할 최신 지식 요약.
    hermes_digest.json이 없으면 빈 문자열 반환.
    """
    if not SUMMARY_PATH.exists():
        return ""
    try:
        d = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        generated = d.get("generated_at", "")[:10]
        return (
            f"[헤르메스 최신 지식 — {generated}] "
            f"{d.get('headline', '')} | "
            f"이번 주 키워드: {d.get('study_tip', '')}"
        )
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────
# 단독 실행
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", action="store_true", help="수집 + 요약 실행")
    parser.add_argument("--status",  action="store_true", help="현재 KB 상태 출력")
    args = parser.parse_args()

    if args.status:
        print(get_kb_summary())
    else:
        run_collect_and_summarize()
