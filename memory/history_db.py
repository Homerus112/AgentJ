"""
memory/history_db.py
대화 히스토리를 SQLite에 저장하고 조회하는 모듈
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "history.db")


def _get_conn():
    """DB 연결 반환 (없으면 자동 생성)"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """테이블 초기화 (최초 1회)"""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                agent TEXT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")


def save_message(session_id: str, role: str, content: str, agent: str = None):
    """메시지 저장"""
    init_db()
    timestamp = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, agent, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, agent, content, timestamp)
        )
    return timestamp


def get_session_history(session_id: str) -> list:
    """특정 세션의 전체 대화 반환"""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_sessions(limit: int = 20) -> list:
    """최근 세션 목록 반환"""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT session_id,
                   MIN(timestamp) as started_at,
                   MAX(timestamp) as last_at,
                   COUNT(*) as message_count,
                   (SELECT content FROM messages m2
                    WHERE m2.session_id = m.session_id AND m2.role = 'user'
                    ORDER BY timestamp ASC LIMIT 1) as first_message
            FROM messages m
            GROUP BY session_id
            ORDER BY last_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def search_messages(query: str, limit: int = 50) -> list:
    """키워드로 메시지 검색"""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """전체 통계 - 프론트엔드 호환 필드 포함"""
    init_db()
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
        sessions = conn.execute("SELECT COUNT(DISTINCT session_id) as c FROM messages").fetchone()["c"]
        # FIX: role = 'agent' 필터 제거 (실제 저장 role은 'user'/'assistant')
        agents = conn.execute("""
            SELECT agent, COUNT(*) as c FROM messages
            WHERE agent IS NOT NULL
            GROUP BY agent ORDER BY c DESC
        """).fetchall()
        last_row = conn.execute(
            "SELECT MAX(timestamp) as last_used FROM messages"
        ).fetchone()
        last_used = last_row["last_used"] if last_row else None

    agent_list = [dict(a) for a in agents]
    return {
        "total_messages": total,
        "total_sessions": sessions,
        "total_conversations": total,
        "agent_usage": agent_list,
        "agent_counts": {a["agent"]: a["c"] for a in agent_list if a.get("agent")},
        "last_used": last_used,
    }
