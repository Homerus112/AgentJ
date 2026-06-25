"""
main.py - Agent J 메인 진입점 (Phase 6 업그레이드)

실행: python main.py
커맨드 팔레트: python main.py --cmd "질문"
자동 회고: python main.py --reflect
"""
import os, sys, uuid, argparse
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
        "📊 [cyan]Slide[/cyan]     발표자료 생성\n"
        "🎯 [red]Career[/red]    커리어·취업 관리\n"
        "🔬 [white]Research[/white]  웹 조사 + Notion 저장\n\n"
        "[dim]/help  /memory  /stats  /tasks  /schedule  /career  /jobs[/dim]\n"
        "[dim]/reflect  /weekly  /dashboard  /clear  /exit[/dim]"
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
**Slide** — "AI 트렌드 발표자료 8장 만들어줘"
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
| `/dashboard` | 대화 히스토리 대시보드 열기 |
| `/clear` | 대화 초기화 |
| `/exit` | 저장 후 종료 |
"""))


def handle_special_commands(cmd: str, orchestrator) -> bool:
    """/ 로 시작하는 명령어를 처리한다. True 반환 시 일반 처리 건너뜀."""

    if cmd in ("/exit", "/quit"):
        orchestrator.save_and_exit()
        console.print("[yellow]세션을 저장했습니다. 다음에 만나요! 👋[/yellow]")
        sys.exit(0)

    elif cmd == "/clear":
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
            from tools.career_tools_v2 import get_job_applications, format_jobs_summary
            jobs = get_job_applications()
            console.print(Panel(Markdown(format_jobs_summary(jobs)), title="💼 채용 지원 현황", border_style="red"))
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")
        return True

    elif cmd.startswith("/reflect"):
        try:
            from agents.reflection_agent import run_reflection
            extra = cmd.replace("/reflect", "").strip()
            console.print("[dim]  회고 작성 중...[/dim]")
            result = run_reflection(user_input=extra if extra else None)
            console