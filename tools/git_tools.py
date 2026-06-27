"""
tools/git_tools.py  —  Agent J Git 통합 도구

사용 방법:
  대화: "git push해줘", "변경사항 커밋해줘", "git 상태 확인해줘"
  명령어: /git push | /git status | /git "커밋 메시지" | /git log

J가 자동으로 커밋 메시지를 생성하거나, 사용자가 직접 지정할 수 있다.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent   # Agent J 폴더


def _run(cmd: list, cwd: str = None) -> dict:
    """Git 명령어를 실행하고 결과를 반환한다."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        return {
            "success":   result.returncode == 0,
            "stdout":    stdout,
            "stderr":    stderr,
            "output":    stdout or stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "⏱️ 타임아웃 (30초)", "stdout": "", "stderr": ""}
    except FileNotFoundError:
        return {"success": False, "output": "❌ git이 설치되지 않았거나 PATH에 없습니다.", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"success": False, "output": str(e), "stdout": "", "stderr": ""}


# ──────────────────────────────────────────────────────────
# 개별 Git 작업
# ──────────────────────────────────────────────────────────

def git_status() -> str:
    """현재 변경 사항을 보여준다."""
    r = _run(["git", "status", "--short"])
    if not r["success"]:
        return f"❌ {r['output']}"
    if not r["output"]:
        return "✅ 변경 사항 없음. 작업 트리가 깨끗해요."
    branch = _run(["git", "branch", "--show-current"])["output"]
    return f"**브랜치:** `{branch}`\n\n**변경 파일:**\n```\n{r['output']}\n```"


def git_diff() -> str:
    """변경된 내용의 diff를 반환한다."""
    r = _run(["git", "diff", "--stat"])
    return r["output"] or "변경 사항 없음"


def git_log(n: int = 5) -> str:
    """최근 커밋 로그를 반환한다."""
    r = _run(["git", "log", f"--oneline", f"-{n}"])
    if not r["success"]:
        return f"❌ {r['output']}"
    return f"**최근 {n}개 커밋:**\n```\n{r['output']}\n```"


def git_add_all() -> dict:
    """모든 변경 파일을 스테이징한다."""
    return _run(["git", "add", "-A"])


def git_commit(message: str) -> dict:
    """스테이징된 파일을 커밋한다."""
    return _run(["git", "commit", "-m", message])


def git_push(remote: str = "origin", branch: str = None) -> dict:
    """원격 저장소에 푸시한다."""
    if not branch:
        branch_r = _run(["git", "branch", "--show-current"])
        branch   = branch_r["output"] or "main"
    return _run(["git", "push", remote, branch])


def git_pull() -> dict:
    """원격 저장소에서 최신 변경을 가져온다."""
    return _run(["git", "pull"])


# ──────────────────────────────────────────────────────────
# 자동 커밋 메시지 생성 (Haiku)
# ──────────────────────────────────────────────────────────

def generate_commit_message() -> str:
    """
    변경된 파일 목록 + diff 요약을 바탕으로
    Claude Haiku가 커밋 메시지를 자동 생성한다.
    """
    status = _run(["git", "status", "--short"])["output"]
    diff   = _run(["git", "diff", "--stat"])["output"]

    if not status:
        return ""

    try:
        import anthropic, os
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = (
            "다음 git 변경 사항을 보고 한 줄 커밋 메시지를 작성해주세요.\n"
            "형식: `[타입] 변경 내용 요약` (50자 이내, 한국어 또는 영어)\n"
            "타입 예시: feat, fix, refactor, docs, chore\n\n"
            f"변경 파일:\n{status}\n\nDiff 요약:\n{diff}"
        )
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=80,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip().strip("`")
    except Exception:
        from datetime import datetime
        return f"chore: auto-commit {datetime.now().strftime('%Y-%m-%d %H:%M')}"


# ──────────────────────────────────────────────────────────
# 통합 명령어 처리 (/git 명령어용)
# ──────────────────────────────────────────────────────────

def handle_git_command(args: str) -> str:
    """
    /git [args] 명령어를 파싱해서 실행한다.

    /git status          → 변경 사항 확인
    /git log             → 최근 커밋 로그
    /git push            → 자동 커밋 메시지 생성 후 add + commit + push
    /git push "메시지"   → 지정 메시지로 add + commit + push
    /git pull            → pull
    """
    args = args.strip()

    # status
    if not args or args == "status":
        return git_status()

    # log
    if args.startswith("log"):
        try:
            n = int(args.split()[-1])
        except Exception:
            n = 5
        return git_log(n)

    # pull
    if args == "pull":
        r = git_pull()
        return f"✅ Pull 완료\n```\n{r['output']}\n```" if r["success"] else f"❌ Pull 실패\n{r['output']}"

    # push (자동 또는 메시지 지정)
    if args.startswith("push"):
        # 메시지 추출 (따옴표 안)
        import re
        quote_match = re.search(r'["\'](.+?)["\']', args)
        if quote_match:
            commit_msg = quote_match.group(1)
        else:
            commit_msg = generate_commit_message()
            if not commit_msg:
                return "⚠️ 커밋할 변경 사항이 없어요."

        lines = [f"**커밋 메시지:** `{commit_msg}`\n"]

        add_r = git_add_all()
        if not add_r["success"]:
            return f"❌ git add 실패: {add_r['output']}"
        lines.append("✅ `git add -A` 완료")

        commit_r = git_commit(commit_msg)
        if not commit_r["success"]:
            return f"❌ 커밋 실패: {commit_r['output']}"
        lines.append("✅ 커밋 완료")

        push_r = git_push()
        if push_r["success"]:
            lines.append("✅ Push 완료!")
        else:
            lines.append(f"❌ Push 실패: {push_r['output']}")

        return "\n".join(lines)

    # 그 외: 직접 메시지로 add + commit + push
    commit_msg = args.strip('"\'')
    lines = [f"**커밋 메시지:** `{commit_msg}`\n"]
    git_add_all()
    commit_r = git_commit(commit_msg)
    if not commit_r["success"]:
        return f"❌ 커밋 실패: {commit_r['output']}"
    push_r = git_push()
    lines.append("✅ 커밋 + Push 완료!" if push_r["success"] else f"❌ Push 실패: {push_r['output']}")
    return "\n".join(lines)
