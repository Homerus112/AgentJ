"""
web/app.py
Agent J 대화 히스토리 웹 대시보드 (Flask)
실행: python web/app.py
접속: http://localhost:5000
"""

import sys
import os
import argparse

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, jsonify, request
from memory.history_db import (
    get_recent_sessions, get_session_history,
    search_messages, get_stats
)

app = Flask(__name__)


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    print(f"Agent J 대시보드 → http://localhost:{args.port}")
    app.run(debug=False, port=args.port)
