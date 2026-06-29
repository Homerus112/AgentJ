"""
server/webhook_server.py  —  Agent J 가상 서버 (Railway 배포용)

Railway 무료 플랜에서 24/7 작동하는 J의 원격 두뇌.
컴퓨터가 꺼져 있어도 외부 이벤트에 반응하고 작업을 실행한다.

엔드포인트:
  GET  /            → 서버 상태 확인
  GET  /health      → Railway 헬스체크
  POST /ask         → J에게 질문 (JSON: {"message": "..."})
  POST /webhook/notion → Notion 이벤트 수신 (DB 업데이트 등)
  POST /run/hermes  → 헤르메스 즉시 실행
  POST /run/digest  → 데일리 브리핑 즉시 발송

보안: X-Agent-Key 헤더로 간단한 API 키 인증

Railway 배포 방법:
  1. railway.com 가입 → New Project → Deploy from GitHub
  2. 환경변수 설정 (ANTHROPIC_API_KEY, GMAIL_* 등)
  3. AGENT_SERVER_KEY 환경변수 추가 (임의의 긴 문자열)
  4. 배포 완료 → URL 발급 (예: agent-j.up.railway.app)
"""

import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

app = Flask(__name__)

# 간단한 API 키 인증 (환경변수로 설정)
AGENT_KEY = os.getenv("AGENT_SERVER_KEY", "")


# ──────────────────────────────────────────────────────────
# 인증 헬퍼
# ──────────────────────────────────────────────────────────

def _authorized() -> bool:
    """X-Agent-Key 헤더 또는 ?key= 쿼리 파라미터로 인증."""
    if not AGENT_KEY:
        return True  # 키 미설정 시 비인증 모드 (개발용)
    provided = request.headers.get("X-Agent-Key") or request.args.get("key", "")
    return provided == AGENT_KEY


def _auth_error():
    return jsonify({"error": "Unauthorized", "hint": "X-Agent-Key 헤더를 확인하세요"}), 401


# ──────────────────────────────────────────────────────────
# 기본 엔드포인트
# ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return jsonify({
        "name":    "Agent J Server",
        "status":  "running",
        "time":    datetime.now().isoformat(),
        "version": "Phase C",
    })


@app.route("/health")
def health():
    """Railway 헬스체크 — 항상 200 반환."""
    return jsonify({"status": "ok"}), 200


# ──────────────────────────────────────────────────────────
# J에게 질문 (비동기 처리)
# ──────────────────────────────────────────────────────────

@app.route("/ask", methods=["POST"])
def ask():
    """
    J에게 원격으로 질문한다.
    Body: {"message": "pandas groupby 어떻게 써?"}
    응답: {"response": "...", "agent": "dev"}
    """
    if not _authorized():
        return _auth_error()

    data    = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message 필드가 없습니다"}), 400

    try:
        from orchestrator.router import Orchestrator
        orch     = Orchestrator()
        response = orch.route(message)
        return jsonify({
            "response": response,
            "agent":    orch.last_agent,
            "time":     datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────
# Notion 웹훅 (Notion Automations → POST /webhook/notion)
# ──────────────────────────────────────────────────────────

@app.route("/webhook/notion", methods=["POST"])
def webhook_notion():
    """
    Notion 자동화 → J 알림 트리거.
    Notion Automations에서 "HTTP Request" 액션으로 이 엔드포인트 호출.

    예시 사용: Notion DB에 새 할 일 추가 → J가 자동으로 알림 이메일 발송
    """
    if not _authorized():
        return _auth_error()

    payload  = request.get_json(silent=True) or {}
    event    = payload.get("event", "unknown")
    page_id  = payload.get("page_id", "")
    title    = payload.get("title", "새 항목")

    print(f"[Notion Webhook] event={event}, title={title}")

    # 백그라운드에서 처리 (응답을 빠르게 반환)
    def _handle():
        try:
            from tools.news_tools import send_email
            subject = f"[Agent J] Notion 업데이트: {title}"
            body    = f"<p>Notion 이벤트: <b>{event}</b><br>페이지: {title} ({page_id})</p>"
            recipient = os.getenv("DIGEST_RECIPIENT", os.getenv("GMAIL_ADDRESS", ""))
            if recipient:
                send_email(subject, body, recipient)
        except Exception as e:
            print(f"[Notion Webhook] 처리 오류: {e}")

    threading.Thread(target=_handle, daemon=True).start()
    return jsonify({"received": True, "event": event}), 200


# ──────────────────────────────────────────────────────────
# 헤르메스 즉시 실행
# ──────────────────────────────────────────────────────────

@app.route("/run/hermes", methods=["POST"])
def run_hermes():
    """헤르메스 지식 수집을 원격으로 트리거한다."""
    if not _authorized():
        return _auth_error()

    def _run():
        try:
            from agents.hermes_agent import run_collect_and_summarize
            run_collect_and_summarize()
        except Exception as e:
            print(f"[Hermes] 오류: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "message": "헤르메스 수집을 시작했습니다"}), 202


# ──────────────────────────────────────────────────────────
# 데일리 브리핑 즉시 발송
# ──────────────────────────────────────────────────────────

@app.route("/run/digest", methods=["POST"])
def run_digest():
    """데일리 브리핑 이메일을 즉시 발송한다 (수동 트리거용)."""
    if not _authorized():
        return _auth_error()

    def _run():
        try:
            import subprocess, sys
            subprocess.run([sys.executable, str(ROOT / "news_digest.py")])
        except Exception as e:
            print(f"[Digest] 오류: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "message": "브리핑 발송을 시작했습니다"}), 202


# ──────────────────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))   # Railway는 PORT 환경변수 자동 설정
    print(f"Agent J 서버 시작 — port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
