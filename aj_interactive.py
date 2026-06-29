"""
aj_interactive.py - File Analysis + Interactive Q&A via Orchestrator

Usage:
  python aj_interactive.py "path/to/file.pdf"

Flow:
  1. Analyze file (vision_agent)
  2. Show structured result
  3. Enter Q&A loop - all follow-up questions go through Orchestrator
     with the file content pre-loaded as context
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()

SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SUPPORTED_DOCS   = {".pdf"}


def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage: python aj_interactive.py <file_path>[/red]")
        sys.exit(1)

    file_path = sys.argv[1].strip('"')
    path      = Path(file_path)

    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)

    suffix = path.suffix.lower()

    # ── Step 1: Initial analysis ────────────────────────────
    from agents.vision_agent import analyze_pdf, analyze_image

    console.print(f"\n[cyan]Analyzing: {path.name}...[/cyan]")

    if suffix in SUPPORTED_IMAGES:
        analysis = analyze_image(file_path)
    elif suffix in SUPPORTED_DOCS:
        analysis = analyze_pdf(file_path)
    else:
        console.print(f"[red]Unsupported format: {suffix}[/red]")
        sys.exit(1)

    console.print(Panel(
        Markdown(analysis),
        title=f"Analysis: {path.name}",
        border_style="green"
    ))

    # ── Step 2: Interactive Q&A loop ────────────────────────
    console.print(
        "\n[bold cyan]Agent J[/bold cyan] - "
        "Ask anything about this file. "
        "[dim](type 'exit' to quit)[/dim]"
    )

    from orchestrator.router import Orchestrator
    orch = Orchestrator()

    # Pre-load file context into conversation history
    orch.conversation_history.append({
        "role": "user",
        "content": f'Please analyze this file for me: "{file_path}"'
    })
    orch.conversation_history.append({
        "role": "assistant",
        "content": f"Here is the analysis of **{path.name}**:\n\n{analysis}"
    })

    while True:
        try:
            question = Prompt.ask("\n[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            break

        # Route through orchestrator - file context is already in history
        response = orch.route(question)
        console.print(Panel(Markdown(response), border_style="cyan"))

    console.print("\n[dim]Session ended.[/dim]")


if __name__ == "__main__":
    main()
