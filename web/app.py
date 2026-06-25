"""
web/app.py
Agent J 대화 히스토리 웹 대시보드 (Flask)
실행: python web/app.py
접속: http://localhost:5000
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, jsonify, request
from memory.history_db import (
    get_recent_sessions, get_session_history,
    search_messages, get_stats
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB 제한


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sessions")
def api_sessions():
    limit = int(request.args.get("limit", 20))
    return jsonify(get_recent_sessions(limit))


@app.route("/api/session/<session_id>")
def api_session(session_id):
    return jsonify(get_session_history(session_id))


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    return jsonify(search_messages(query))


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/upload-essay", methods=["POST"])
def api_upload_essay():
    """텍스트 첨삭 요청 → Writer Agent → 결과 반환"""
    try:
        instruction = request.form.get("instruction", "이 글을 다듬어줘")
        content = request.form.get("content", "")

        if not content:
            file = request.files.get("file")
            if file:
                content = file.read().decode("utf-8", errors="ignore")

        if not content:
            return jsonify({"error": "내용이 없습니다."}), 400

        from agents.writer_agent import WriterAgent
        writer = WriterAgent()
        result = writer.run(f"{instruction}\n\n---\n{content}", [])
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    print(f"Agent J 대시보드: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
