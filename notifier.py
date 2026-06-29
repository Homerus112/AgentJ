"""
notifier.py  —  Agent J 능동적 알림 시스템

Windows Task Scheduler에 의해 하루 2회 자동 실행:
  - 오전 8:00: 아침 체크인 + Due date 임박 확인
  - 오후 9:00: 저녁 회고 리마인더 + 학습 미달 경고

setup_notifier.bat 을 한 번만 실행하면 자동 등록된다.

로컬 테스트:
    python notifier.py --mode morning
    python notifier.py --mode evening
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


# ──────────────────────────────────────────────────────────
# Windows 알림 헬퍼
# ──────────────────────────────────────────────────────────

def notify(title: str, message: str, duration: int = 8):
    """
    Windows 토스트 알림을 표시한다.
    plyer가 없으면 콘솔 출력으로 폴백.
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Agent J",
            timeout=duration,
        )
    except Exception:
        # 폴백: 콘솔 출력
        print(f"\n[Agent J 알림] {title}\n{message}\n")


# ──────────────────────────────────────────────────────────
# Notion 할 일 조회 (Due 임박)
# ──────────────────────────────────────────────────────────

def get_due_tasks(days_ahead: int = 1) -> list:
    """
    오늘 ~ days_ahead일 이내 Due인 Notion 할 일 목록을 반환한다.
    NOTION_API_KEY / NOTION_TASKS_DB_ID 없으면 빈 리스트.
    """
    api_key = os.getenv("NOTION_API_KEY")
    db_id   = os.getenv("NOTION_TASKS_DB_ID")
    if not api_key or not db_id:
        return []

    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        today    = date.today().isoformat()
        deadline = (date.today() + timedelta(days=days_ahead)).isoformat()
        payload  = {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Due",    "date":   {"on_or_before": deadline}},
                    {"property": "Due",    "date":   {"on_or_after":  today}},
                ]
            },
            "sorts": [{"property": "Due", "direction": "ascending"}],
            "page_size": 5,
        }
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=headers, json=payload, timeout=8,
        )
        if resp.status_code != 200:
            return []

        tasks = []
        for page in resp.json().get("results", []):
            props = page.get("properties", {})
            for key in ("Name", "Task", "Title", "이름"):
                titles = props.get(key, {}).get("title", [])
                if titles:
                    due_prop = props.get("Due", {}).get("date", {}) or {}
                    tasks.append({
                        "title": titles[0].get("plain_text", ""),
                        "due":   due_prop.get("start", ""),
                    })
                    break
        return tasks
    except Exception:
        return []


# ──────────────────────────────────────────────────────────
# 학습 미달 체크
# ──────────────────────────────────────────────────────────

def check_learning_gap() -> int:
    """마지막 학습 기록 이후 경과 일수를 반환한다. 기록 없으면 999."""
    try:
        from tools.learning_tools import get_days_since_last_log
        return get_days_since_last_log()
    except Exception:
        return 0


# ──────────────────────────────────────────────────────────
# 오전 모드 (8:00 AM)
# ──────────────────────────────────────────────────────────

def run_morning():
    today_str = date.today().strftime("%m/%d (%a)")
    print(f"[{datetime.now().strftime('%H:%M')}] 아침 알림 실행 중...")

    # 1. 아침 체크인
    notify(
        title=f"🌅 Good morning! — {today_str}",
        message="Agent J: 오늘도 좋은 하루! /tasks 로 오늘 할 일을 확인하세요.",
        duration=6,
    )

    # 2. Due date 임박 (오늘 + 내일)
    due_tasks = get_due_tasks(days_ahead=1)
    if due_tasks:
        task_list = "\n".join(f"• {t['title']}" + (f" ({t['due']})" if t["due"] else "")
                              for t in due_tasks[:3])
        notify(
            title=f"📋 마감 임박 — {len(due_tasks)}건",
            message=task_list,
            duration=10,
        )
        print(f"  📋 Due 임박 {len(due_tasks)}건 알림 전송")

    # 3. 학습 미달 경고 (3일 이상 기록 없으면)
    gap = check_learning_gap()
    if gap >= 3:
        notify(
            title=f"📚 학습 알림 — {gap}일째 기록 없음",
            message="Agent J와 대화하면서 배운 내용이 자동으로 기록돼요!\n오늘 뭔가 배워볼까요?",
            duration=8,
        )
        print(f"  📚 학습 미달 경고: {gap}일째 기록 없음")

    print("  ✅ 아침 알림 완료")


# ──────────────────────────────────────────────────────────
# 저녁 모드 (9:00 PM)
# ──────────────────────────────────────────────────────────

def run_evening():
    print(f"[{datetime.now().strftime('%H:%M')}] 저녁 알림 실행 중...")

    # 1. 회고 리마인더
    notify(
        title="🌙 저녁 회고 시간이에요",
        message="Agent J: '/reflect' 명령어로 오늘 하루를 기록해보세요.\n꾸준한 회고가 성장을 만들어요!",
        duration=10,
    )
    print("  🌙 저녁 회고 리마인더 전송")

    # 2. 오늘 학습 기록 확인
    try:
        from tools.learning_tools import get_recent_logs
        today_logs = [e for e in get_recent_logs(1) if e["date"] == date.today().isoformat()]
        if today_logs:
            topics = ", ".join(e["topic"] for e in today_logs[:2])
            notify(
                title=f"📚 오늘 학습 {len(today_logs)}건 기록됨",
                message=f"훌륭해요! 오늘 배운 것:\n{topics}",
                duration=6,
            )
        else:
            notify(
                title="📚 오늘 학습 기록 없음",
                message="아직 오늘 학습 기록이 없어요.\nJ와 대화하면 자동으로 기록돼요!",
                duration=6,
            )
    except Exception:
        pass

    print("  ✅ 저녁 알림 완료")


# ──────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Agent J 알림 시스템")
    parser.add_argument(
        "--mode",
        choices=["morning", "evening"],
        default="morning",
        help="morning (8AM) | evening (9PM)",
    )
    args = parser.parse_args()

    if args.mode == "morning":
        run_morning()
    else:
        run_evening()


if __name__ == "__main__":
    main()
