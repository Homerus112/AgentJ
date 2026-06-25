"""
main.py
Agent J의 메인 진입점. 터미널에서 실행한다.

실행 방법:
    python main.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# .env 파일 로드 (API 키 등)
load_dotenv()

console = Console()


def check_setup() -> bool:
    """실행 전 필수 환경 확인."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        console.print(Panel(
            "[red]❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.[/red]\n\n"
            "1. .env.example 파일을 .env로 복사하세요:\n"
            "   [cyan]copy .env.example .env[/cyan] (Windows)\n\n"
            "2. .env 파일을 열고 API 키를 입력하세요:\n"
            "   [cyan]ANTHROPIC_API_KEY=sk-ant-...[/cyan]\n\n"
            "API 키 발급: [link]https://console.anthropic.com[/link]",
            title="설정 필요", border_style="red"
        ))
        return False
    return True


def print_welcome():
    """시작 화면 출력."""
    console.print(Panel(
        "[bold cyan]Agent J[/bold cyan] — 나만의 AI 어시스턴트\n\n"
        "🤖 [green]Dev Agent[/green]    → 코드 작성, 디버깅, 파일 조작\n"
        "📅 [blue]Planner Agent[/blue] → 할 일 관리, 일정 관리\n"
        "💬 [yellow]General[/yellow]       → 일반 대화 및 질문\n\n"
        "[dim]명령어: /clear (대화 초기화) | /exit (종료) | /help (도움말)[/dim]",
        title="🚀 J 시작",
        border_style="cyan"
    ))


def print_help():
    """도움말 출력."""
    help_text = """
## 사용 예시

**Dev Agent (자동 감지)**
- "파이썬으로 피보나치 수열 코드 짜줘"
- "이 파일 읽어서 버그 찾아줘: main.py"
- "폴더에 있는 파일 목록 보여줘"

**Planner Agent (자동 감지)**
- "오늘 할 일 추가해줘: 보고서 작성"
- "내 할 일 목록 보여줘"
- "7월 1일 오후 2시에 팀 미팅 일정 추가해줘"
- "3번 할 일 완료 처리해줘"

**일반 대화**
- "AI 트렌드에 대해 설명해줘"
- "오늘 뭐 먹을까?"

## 특수 명령어
- `/clear` — 대화 히스토리 초기화
- `/tasks` — 할 일 목록 바로 조회
- `/schedule` — 오늘 일정 바로 조회
- `/exit` — 종료
"""
    console.print(Markdown(help_text))


def handle_special_commands(cmd: str, orchestrator) -> bool:
    """
    /로 시작하는 특수 명령어를 처리한다.
    Returns: True이면 일반 처리 건너뜀
    """
    if cmd == "/exit" or cmd == "/quit":
        console.print("[yellow]J를 종료합니다. 수고하셨습니다! 👋[/yellow]")
        sys.exit(0)

    elif cmd == "/clear":
        orchestrator.clear_history()
        return True

    elif cmd == "/help":
        print_help()
        return True

    elif cmd == "/tasks":
        # Planner Agent에 직접 요청
        response = orchestrator.planner_agent.run("현재 pending 상태인 할 일 전체 목록을 보여줘")
        console.print(Panel(Markdown(response), title="📋 할 일 목록", border_style="blue"))
        return True

    elif cmd == "/schedule":
        from datetime import date
        today = date.today().isoformat()
        response = orchestrator.planner_agent.run(f"오늘({today}) 이후 일정을 모두 보여줘")
        console.print(Panel(Markdown(response), title="📅 일정", border_style="blue"))
        return True

    return False


def main():
    """메인 실행 함수."""
    # 환경 확인
    if not check_setup():
        sys.exit(1)

    # 작업 디렉토리를 main.py가 있는 곳으로 설정
    os.chdir(Path(__file__).parent)

    # 오케스트레이터 초기화
    from orchestrator.router import Orchestrator
    orchestrator = Orchestrator()

    print_welcome()

    # 메인 대화 루프
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]").strip()

            if not user_input:
                continue

            # 특수 명령어 처리
            if user_input.startswith("/"):
                handle_special_commands(user_input.lower(), orchestrator)
                continue

            # 일반 메시지 → 오케스트레이터로 전달
            response = orchestrator.route(user_input)

            # 응답 출력
            console.print(Panel(
                Markdown(response),
                title="[bold green]J[/bold green]",
                border_style="green"
            ))

        except KeyboardInterrupt:
            console.print("\n[yellow]종료합니다. (Ctrl+C)[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]오류 발생: {e}[/red]")
            console.print("[dim]계속 사용하려면 Enter를 누르세요.[/dim]")


if __name__ == "__main__":
    main()
