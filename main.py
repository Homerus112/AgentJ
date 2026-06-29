"""
main.py - Agent J 메인 진입점 (Phase 6 업그레이드)

실행: python main.py
커맨드 팔레트: python main.py --cmd "질문"
자동 회고: python main.py --reflect
"""
import os, sys, uuid, argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()
console = Console()


def check_setup() -> bool:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        console.print(Panel(
            "[red]ANTHROPIC_API_KEY가 설정되지 않았습니다.[/red]\n\n"
            "1. .env.example 을 .env 로 복사\n"
            "2. .env 파일에 API 키 입력\n\n"
            "발급: [link]https://console.anthropic.com[/link]",
            title="설정 필요", border_style="red"
        ))
        return False
    return True


def print_welcome(history_turns: int = 0):
    memory_note = f"\n[dim]이전 대화 {history_turns}턴 기억 중[/dim]" if history_turns > 0 else ""
    console.print(Panel(
        "[bold cyan]Agent J[/bold cyan] — 나만의 AI 어시스턴트\n\n"
        "💻 [green]Dev[/green]      코드·파일 조작\n"
        "📅 [blue]Planner[/blue]   할 일·일정 관리\n"
        "✍️  [yellow]Writer[/yellow]    에세이·문서 첨삭\n"
        "📰 [magenta]News[/magenta]      뉴스 브리핑\n"
        "🎯 [red]Career[/red]    커리어·취업 관리\n"
        "🔬 [white]Research[/white]  웹 조사 + Notion 저장\n"
        "🔍 [green]Hermes[/green]   논문·GitHub·HN 지식 수집\n"
        "👁️  [yellow]Vision[/yellow]   이미지·PDF 분석\n\n"
        "[dim]/help  /memory  /stats  /tasks  /schedule  /career  /jobs[/dim]\n"
        "[dim]/git [push|status|log|diff]  /reflect  /weekly  /learning  /compress  /jlog  /evolve  /clear[/dim]"
        + memory_note,
        title="🤖 J", border_style="cyan"
    ))


def print_help():
    console.print(Markdown("""
## 사용 예시
**Dev** — "파이썬으로 CSV 읽는 코드 짜줘"
**Planner** — "내일 오후 3시 팀 미팅 추가해줘"
**Writer** — "이 이메일 다듬어줘: [내용]"
**News** — "오늘 테크 뉴스 요약해줘"

**Career** — "Google SWE 지원했어, 추가해줘"

## 명령어
| 명령어 | 기능 |
|--------|------|
| `/memory` | J가 기억하는 내용 보기 |
| `/remember [내용]` | 중요한 것 영구 저장 |
| `/stats` | 에이전트 사용 통계 |
| `/tasks` | 할 일 목록 |
| `/schedule` | 일정 보기 |
| `/career` | 커리어 현황 |
| `/jobs` | 채용 지원 현황 |
| `/reflect` | 오늘 회고 작성 |
| `/weekly` | 주간 회고 생성 |
| `/evolve` | 대화 분석 → 에이전트 자기 최적화 |
| `/clear` | 대화 초기화 |
"""))


def handle_special_commands(cmd: str, orchestrator) -> bool:
    """/ 로 시작하는 명령어를 처리한다. True 반환 시 일반 처리 건너뜀."""

    if cmd == "/clear":
        orchestrator.clear_history()
        return True

    elif cmd == "/help":
        print_help()
        return True

    elif cmd == "/memory":
        console.print(Panel(
            Markdown(orchestrator.memory.get_memory_summary()),
            title="🧠 J의 기억", border_style="cyan"
        ))
        return True

    elif cmd == "/stats":
        console.print(Panel(
            orchestrator.memory.get_stats_summary(),
            title="📊 사용 통계", border_style="yellow"
        ))
        return True

    elif cmd.startswith("/remember "):
        note = cmd[len("/remember "):].strip()
        if note:
            msg = orchestrator.memory.add_note(note)
            console.print(f"[green]✅ {msg}[/green]")
        return True

    elif cmd == "/tasks":
        response = orchestrator.planner_agent.run("현재 pending 할 일 전체 목록 보여줘")
        console.print(Panel(Markdown(response), title="📋 할 일", border_style="blue"))
        return True

    elif cmd == "/schedule":
        from datetime import date
        response = orchestrator.planner_agent.run(f"오늘({date.today()}) 이후 일정 모두 보여줘")
        console.print(Panel(Markdown(response), title="📅 일정", border_style="blue"))
        return True

    elif cmd == "/career":
        response = orchestrator.career_agent.run("내 커리어 현황 전체 요약해줘: 목표, 지원 현황, 스킬 목록")
        console.print(Panel(Markdown(response), title="🎯 커리어 현황", border_style="red"))
        return True

    elif cmd == "/jobs":
        try:
            from tools.career_tools import get_job_applications, format_jobs_summary
            jobs = get_job_applications()
            console.print(Panel(Markdown(format_jobs_summary(jobs)), title="💼 채용 지원 현황", border_style="red"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd.startswith("/git"):
        import subprocess
        from pathlib import Path
        repo_dir = str(Path(__file__).parent)
        arg = cmd[4:].strip()   # /git 이후 인자

        try:
            if arg in ("", "status"):
                result = subprocess.run(
                    ["git", "status", "--short"], capture_output=True, text=True, cwd=repo_dir
                )
                output = result.stdout or "(변경사항 없음)"
                console.print(Panel(output, title="📁 Git Status", border_style="yellow"))

            elif arg == "log":
                result = subprocess.run(
                    ["git", "log", "--oneline", "-10"], capture_output=True, text=True, cwd=repo_dir
                )
                console.print(Panel(result.stdout, title="📜 Git Log (최근 10개)", border_style="yellow"))

            elif arg.startswith("push"):
                # 커밋 메시지 추출: /git push "메시지" 또는 기본값 사용
                import re
                msg_match = re.search(r'"(.+)"', arg)
                commit_msg = msg_match.group(1) if msg_match else \
                    f"Agent J: auto commit {datetime.now().strftime('%Y-%m-%d %H:%M')}"

                console.print(f"[dim]  📤 git add → commit → push 중...[/dim]")
                subprocess.run(["git", "add", "-A"], cwd=repo_dir)
                commit = subprocess.run(
                    ["git", "commit", "-m", commit_msg],
                    capture_output=True, text=True, cwd=repo_dir
                )
                if "nothing to commit" in commit.stdout:
                    console.print("[yellow]변경사항이 없어요.[/yellow]")
                else:
                    push = subprocess.run(
                        ["git", "push"], capture_output=True, text=True, cwd=repo_dir
                    )
                    if push.returncode == 0:
                        console.print(f"[green]✅ Push 완료: {commit_msg}[/green]")
                    else:
                        console.print(f"[red]❌ Push 실패:\n{push.stderr}[/red]")

            elif arg == "diff":
                result = subprocess.run(
                    ["git", "diff", "--stat"], capture_output=True, text=True, cwd=repo_dir
                )
                console.print(Panel(result.stdout or "(변경사항 없음)", title="📊 Git Diff", border_style="yellow"))

            else:
                console.print(
                    "[yellow]사용법:\n"
                    "  /git status   — 변경사항 확인\n"
                    '  /git push     — 자동 커밋 + push\n'
                    '  /git push "메시지" — 커밋 메시지 지정\n'
                    "  /git log      — 최근 커밋 10개\n"
                    "  /git diff     — 변경 파일 통계[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]Git 오류: {e}[/red]")
        return True

    elif cmd == "/compress":
        try:
            from memory.long_term_memory import compress, get_summary_display
            console.print("[dim]  🧠 장기 메모리 압축 중...[/dim]")
            result = compress(force=True)
            if result.get("success") and not result.get("skipped"):
                console.print(f"[green]✅ 압축 완료 ({result.get('week')}): {result.get('summary')}[/green]")
            console.print(Panel(Markdown(get_summary_display()), title="🧠 장기 메모리", border_style="cyan"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd == "/jlog":
        try:
            from memory.self_reflection import get_reflection_display
            console.print(Panel(Markdown(get_reflection_display()), title="🔄 J의 자기 반성", border_style="magenta"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd.startswith("/learning") or cmd == "/learn":
        try:
            from tools.learning_tools import get_stats_summary, get_recent_logs, get_streak
            summary = get_stats_summary()
            console.print(Panel(Markdown(summary), title="📚 학습 진도", border_style="green"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd.startswith("/reflect"):
        try:
            from agents.reflection_agent import run_reflection
            extra = cmd.replace("/reflect", "").strip()
            console.print("[dim]  회고 작성 중...[/dim]")
            result = run_reflection(user_input=extra if extra else None)
            console.print(Panel(Markdown(result), title="📝 Daily Reflection", border_style="magenta"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd == "/weekly":
        try:
            from agents.reflection_agent import run_weekly_reflection
            console.print("[dim]  주간 회고 생성 중...[/dim]")
            result = run_weekly_reflection()
            console.print(Panel(Markdown(result), title="📊 주간 회고", border_style="magenta"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd == "/evolve":
        try:
            from agents.personalization_agent import run_personalization
            console.print("[dim]  대화 히스토리 분석 중... (30초~1분 소요)[/dim]")
            result = run_personalization()
            if result["success"]:
                p = result["profile"]
                summary = (
                    f"**분석 완료!** {p.get('analyzed_message_count', '?')}개 메시지 학습\n\n"
                    f"**말투:** {p.get('speech_style', '-')}\n"
                    f"**기술 수준:** {p.get('expertise_level', '-')}\n"
                    f"**자주 다루는 주제:** {', '.join(p.get('frequent_topics', []))}\n"
                    f"**선호 형식:** {p.get('preferred_format', '-')}\n\n"
                    f"**커스텀 지시:**\n{p.get('custom_instructions', '-')}\n\n"
                    f"_이제 모든 에이전트가 이 프로필을 반영해서 응답합니다._"
                )
                console.print(Panel(Markdown(summary), title="🧠 사용자 프로필 업데이트", border_style="magenta"))
            else:
                console.print(f"[red]{result['error']}[/red]")
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    return False


def main():
    # CLI 인자 파싱 (커맨드 팔레트 / 자동 회고 지원)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cmd", type=str, default=None)
    parser.add_argument("--reflect", action="store_true")
    args, _ = parser.parse_known_args()

    if not check_setup():
        sys.exit(1)

    os.chdir(Path(__file__).parent)

    # 대화 히스토리 DB 초기화
    try:
        from memory.history_db import save_message, init_db
        init_db()
        history_enabled = True
    except Exception:
        history_enabled = False

    session_id = str(uuid.uuid4())[:8]

    # --reflect 플래그: 자동 회고 후 종료
    if args.reflect:
        from agents.reflection_agent import run_reflection
        print(run_reflection(auto_mode=True))
        sys.exit(0)

    from orchestrator.router import Orchestrator
    orchestrator = Orchestrator()

    # --cmd 플래그: 단일 명령 실행 후 종료 (커맨드 팔레트용)
    if args.cmd:
        if history_enabled:
            save_message(session_id, "user", args.cmd)
        response = orchestrator.route(args.cmd)
        if history_enabled:
            save_message(session_id, "agent", response)
        console.print(Panel(Markdown(response), title="[bold green]J[/bold green]", border_style="green"))
        sys.exit(0)

    history_turns = len(orchestrator.conversation_history) // 2
    print_welcome(history_turns)

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]").strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                # 인자 포함 명령어는 원본 대소문자를 보존해야 함
                _cmd_lower = user_input.lower()
                _preserve_case = (
                    _cmd_lower.startswith("/remember") or   # 메모 내용 보존
                    _cmd_lower.startswith("/git ") or       # 커밋 메시지 보존
                    _cmd_lower.startswith("/reflect ") or   # 회고 내용 보존
                    _cmd_lower.startswith("/learning")      # 학습 내용 보존
                )
                handle_special_commands(user_input if _preserve_case else _cmd_lower, orchestrator)
                continue

            # 히스토리 저장 (user)
            if history_enabled:
                save_message(session_id, "user", user_input)

            response = orchestrator.route(user_input)
            console.print(Panel(Markdown(response), title="[bold green]J[/bold green]", border_style="green"))

            # 히스토리 저장 (agent)
            if history_enabled:
                save_message(session_id, "agent", response, agent=getattr(orchestrator, "last_agent", None))

        except KeyboardInterrupt:
            orchestrator.save_and_exit()
            console.print("\n[yellow]세션 저장 완료. (Ctrl+C)[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")


if __name__ == "__main__":
    main()
