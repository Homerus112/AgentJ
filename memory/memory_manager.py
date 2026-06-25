"""
memory_manager.py
세션 간 대화 기억을 유지하는 지속 메모리 시스템.

저장 구조:
  memory/context.json
    - long_term: 영구 메모 (사용자 이름, 선호도, 중요 노트)
    - recent_sessions: 최근 5개 세션 요약 + 히스토리
    - agent_stats: 에이전트별 사용 횟수
    - last_updated: 마지막 업데이트 시각
"""
import json
from pathlib import Path
from datetime import datetime

CONTEXT_FILE = Path("memory/context.json")
MAX_SESSIONS = 5        # 보관할 최대 세션 수
MAX_HISTORY  = 20       # 세션당 최대 대화 수 (turn 기준)


class MemoryManager:

    def __init__(self):
        self._data = self._load()

    # ── 내부 로드/저장 ─────────────────────────────────────

    def _load(self) -> dict:
        if CONTEXT_FILE.exists():
            try:
                return json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "long_term":       {"notes": [], "preferences": {}},
            "recent_sessions": [],
            "agent_stats":     {},
            "last_updated":    None
        }

    def _save(self):
        CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._data["last_updated"] = datetime.now().isoformat()
        CONTEXT_FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ── 세션 관리 ──────────────────────────────────────────

    def load_recent_history(self) -> list:
        """직전 세션의 대화 히스토리를 반환한다 (컨텍스트 연속성 유지)."""
        sessions = self._data.get("recent_sessions", [])
        if not sessions:
            return []
        return sessions[-1].get("history", [])

    def save_session(self, history: list, agent_used: str = None):
        """현재 세션 대화를 저장하고 에이전트 사용 통계를 업데이트한다."""
        if not history:
            return

        # 히스토리 압축 (MAX_HISTORY 초과 시 오래된 것 제거)
        trimmed = history[-MAX_HISTORY * 2:]

        session = {
            "date":    datetime.now().isoformat(),
            "turns":   len(trimmed) // 2,
            "history": trimmed
        }
        self._data.setdefault("recent_sessions", []).append(session)

        # MAX_SESSIONS 초과 시 오래된 세션 삭제
        if len(self._data["recent_sessions"]) > MAX_SESSIONS:
            self._data["recent_sessions"] = self._data["recent_sessions"][-MAX_SESSIONS:]

        # 에이전트 사용 통계 업데이트
        if agent_used:
            stats = self._data.setdefault("agent_stats", {})
            stats[agent_used] = stats.get(agent_used, 0) + 1

        self._save()

    def update_agent_stat(self, agent_name: str):
        """에이전트 호출 시마다 통계를 업데이트한다."""
        stats = self._data.setdefault("agent_stats", {})
        stats[agent_name] = stats.get(agent_name, 0) + 1

    # ── 장기 메모 ──────────────────────────────────────────

    def add_note(self, note: str) -> str:
        """장기 메모를 추가한다 (/remember 명령어용)."""
        entry = {"note": note, "date": datetime.now().strftime("%Y-%m-%d")}
        self._data.setdefault("long_term", {}).setdefault("notes", []).append(entry)
        self._save()
        return f"기억했습니다: {note}"

    def get_notes(self) -> list:
        """장기 메모 목록을 반환한다."""
        return self._data.get("long_term", {}).get("notes", [])

    def clear_notes(self):
        """장기 메모를 초기화한다."""
        self._data.setdefault("long_term", {})["notes"] = []
        self._save()

    def set_preference(self, key: str, value):
        """사용자 선호도를 저장한다."""
        self._data.setdefault("long_term", {}).setdefault("preferences", {})[key] = value
        self._save()

    def get_preference(self, key: str, default=None):
        return self._data.get("long_term", {}).get("preferences", {}).get(key, default)

    # ── 통계 및 요약 ───────────────────────────────────────

    def get_stats_summary(self) -> str:
        """사용 통계 요약 문자열을 반환한다."""
        stats  = self._data.get("agent_stats", {})
        sessions = self._data.get("recent_sessions", [])
        notes  = self._data.get("long_term", {}).get("notes", [])
        last   = self._data.get("last_updated", "없음")

        if not stats:
            return "아직 사용 기록이 없습니다."

        total = sum(stats.values())
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        lines = [
            f"총 대화: {total}회  |  세션: {len(sessions)}개  |  메모: {len(notes)}개",
            f"마지막 사용: {last[:10] if last else '없음'}",
            "",
            "에이전트별 사용 횟수:"
        ]
        icons = {"dev": "💻", "planner": "📅", "writer": "✍️", "news": "📰", "slide": "📊", "career": "🎯", "general": "💬"}
        for name, count in sorted_stats:
            bar = "█" * min(count, 20)
            lines.append(f"  {icons.get(name,'🤖')} {name:<10} {bar} {count}")
        return "\n".join(lines)

    def get_memory_summary(self) -> str:
        """현재 기억 상태 요약을 반환한다."""
        notes = self.get_notes()
        prefs = self._data.get("long_term", {}).get("preferences", {})
        sessions = self._data.get("recent_sessions", [])

        lines = ["**J의 현재 기억**", ""]
        if sessions:
            last = sessions[-1]
            lines.append(f"마지막 세션: {last['date'][:10]} ({last['turns']}번 대화)")
        lines.append(f"보관 중인 세션: {len(sessions)}개")
        lines.append("")

        if notes:
            lines.append("**저장된 메모:**")
            for n in notes[-10:]:
                lines.append(f"  • [{n['date']}] {n['note']}")
        else:
            lines.append("저장된 메모 없음 (/remember [내용]으로 추가)")

        if prefs:
            lines.append("")
            lines.append("**설정된 선호도:**")
            for k, v in prefs.items():
                lines.append(f"  • {k}: {v}")

        return "\n".join(lines)
