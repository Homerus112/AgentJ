"""
agents/vision_agent.py  —  멀티모달 입력 에이전트

기능:
  - 이미지 (PNG/JPG/WEBP): 스크린샷, 차트, 다이어그램, 필기 노트 분석
  - PDF: 텍스트 추출 후 요약 (pypdf 사용)
  - 분석 결과 → 터미널 출력 + 선택적으로 Notion 저장

사용 방법:
  python agents/vision_agent.py --file "chart.png"
  python agents/vision_agent.py --file "paper.pdf" --notion
  python agents/vision_agent.py --file "screenshot.png" --ask "이 오류 코드가 뭐야?"

J 대화에서:
  "이 이미지 분석해줘" + 파일 경로 입력 → vision 에이전트로 라우팅

비용:
  - 이미지: Claude Sonnet 사용, 이미지당 ~$0.02~0.05
  - PDF (텍스트만): Haiku 사용, 페이지당 ~$0.002
"""

import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import anthropic
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 이미지는 Sonnet(Vision), PDF 텍스트는 Haiku로 비용 최적화
VISION_MODEL = os.getenv("DEV_MODEL",     "claude-sonnet-4-6")
TEXT_MODEL   = os.getenv("PLANNER_MODEL", "claude-haiku-4-5-20251001")

SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SUPPORTED_DOCS   = {".pdf"}


# ──────────────────────────────────────────────────────────
# 이미지 분석
# ──────────────────────────────────────────────────────────

def _encode_image(path: Path) -> tuple[str, str]:
    """이미지를 base64로 인코딩하고 미디어 타입을 반환한다."""
    ext_map = {
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif":  "image/gif",
    }
    media_type = ext_map.get(path.suffix.lower(), "image/png")
    data       = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def analyze_image(file_path: str, question: str = None) -> str:
    """
    이미지를 Claude Vision으로 분석한다.

    Args:
        file_path: 이미지 파일 경로
        question:  특정 질문 (없으면 전반적인 분석)

    Returns:
        분석 결과 텍스트
    """
    path = Path(file_path)
    if not path.exists():
        return f"❌ 파일을 찾을 수 없어요: {file_path}"
    if path.suffix.lower() not in SUPPORTED_IMAGES:
        return f"❌ 지원하지 않는 이미지 형식: {path.suffix}"

    print(f"🔍 이미지 분석 중: {path.name} (Sonnet Vision)")
    data, media_type = _encode_image(path)

    prompt = question if question else (
        "이 이미지를 분석해주세요. 다음을 포함해서 설명해주세요:\n"
        "1. 이미지 유형 (차트/스크린샷/다이어그램/코드 등)\n"
        "2. 핵심 내용 요약\n"
        "3. 주목할 인사이트나 패턴\n"
        "4. 데이터사이언스/AI 학습과 관련이 있다면 학습 포인트"
    )

    resp = client.messages.create(
        model=VISION_MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type":   "image",
                    "source": {
                        "type":       "base64",
                        "media_type": media_type,
                        "data":       data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return resp.content[0].text


# ──────────────────────────────────────────────────────────
# PDF 분석
# ──────────────────────────────────────────────────────────

def analyze_pdf(file_path: str, question: str = None) -> str:
    """
    PDF에서 텍스트를 추출하고 Haiku로 요약한다.
    pypdf가 없으면 안내 메시지 반환.
    """
    path = Path(file_path)
    if not path.exists():
        return f"❌ 파일을 찾을 수 없어요: {file_path}"

    # pypdf로 텍스트 추출
    try:
        from pypdf import PdfReader
    except ImportError:
        return "❌ pypdf가 없어요. `pip install pypdf` 실행 후 다시 시도하세요."

    print(f"📄 PDF 분석 중: {path.name} (텍스트 추출 + Haiku)")
    try:
        reader = PdfReader(str(path))
        pages  = len(reader.pages)
        text   = ""
        for i, page in enumerate(reader.pages[:20]):   # 최대 20페이지
            text += page.extract_text() or ""
            if len(text) > 8000:
                break
        text = text[:8000]
    except Exception as e:
        return f"❌ PDF 읽기 실패: {e}"

    if not text.strip():
        return "❌ PDF에서 텍스트를 추출할 수 없어요 (스캔된 이미지 PDF일 수 있어요)."

    prompt = question if question else (
        "다음 PDF 내용을 분석해주세요:\n"
        "1. 문서 유형과 주제\n"
        "2. 핵심 내용 요약 (3~5줄)\n"
        "3. 중요 개념/용어\n"
        "4. 데이터사이언스/AI 관련성 및 학습 포인트"
    )

    resp = client.messages.create(
        model=TEXT_MODEL,
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"{prompt}\n\n[PDF 내용 ({pages}페이지)]\n{text}"
        }],
    )
    return resp.content[0].text


# ──────────────────────────────────────────────────────────
# Notion 저장
# ──────────────────────────────────────────────────────────

def _save_to_notion(title: str, content: str, file_name: str) -> dict:
    """분석 결과를 Notion 페이지로 저장한다."""
    try:
        from tools.notion_tools import create_page
        result = create_page(
            title=f"[Vision] {title}",
            content=f"**파일:** {file_name}\n\n{content}",
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────
# 통합 진입점 (J 오케스트레이터 → vision 라우팅)
# ──────────────────────────────────────────────────────────

def run(user_message: str, history: list = None) -> str:
    """
    J 대화에서 파일 경로가 포함된 메시지를 처리한다.
    예: "이 이미지 분석해줘 C:/Users/.../chart.png"
         이 차트 분석해줘 "C:/path with spaces/chart.png"
    """
    import re

    EXT = r'\.(?:png|jpg|jpeg|webp|gif|pdf)'

    # 1순위: 따옴표로 감싼 경로 (공백 있는 경로 처리)
    quoted = re.search(r'"([^"]+' + EXT + r')"', user_message, re.IGNORECASE)
    if quoted:
        file_path    = quoted.group(1)
        question_part = re.sub(r'"[^"]*"', '', user_message).strip()
    else:
        # 2순위: 따옴표 없는 경로 (공백 없는 일반 경로)
        plain = re.search(
            r'([A-Za-z]:[\\/]\S+' + EXT + r'|/\S+' + EXT + r')',
            user_message, re.IGNORECASE
        )
        if not plain:
            return (
                "파일 경로를 찾을 수 없어요. 이렇게 입력해주세요:\n"
                "예시: `이 차트 분석해줘 C:/Users/sungh/Downloads/chart.png`\n"
                "공백 있는 경로: `분석해줘 \"C:/path with spaces/img.png\"`\n\n"
                "지원 형식: PNG, JPG, WEBP, GIF, PDF"
            )
        file_path     = plain.group(0)
        question_part = user_message.replace(file_path, "").strip()

    suffix   = Path(file_path).suffix.lower()
    question = question_part if len(question_part) > 5 else None

    # Notion 저장 여부
    save_notion = "notion" in user_message.lower() or "저장" in user_message

    # 분석 실행
    if suffix in SUPPORTED_IMAGES:
        result = analyze_image(file_path, question)
    elif suffix in SUPPORTED_DOCS:
        result = analyze_pdf(file_path, question)
    else:
        return f"❌ 지원하지 않는 형식이에요. PNG/JPG/WEBP/PDF 파일만 가능해요."

    # Notion 저장
    if save_notion:
        notion_result = _save_to_notion(
            title=Path(file_path).stem,
            content=result,
            file_name=Path(file_path).name,
        )
        if notion_result.get("success"):
            result += "\n\n✅ Notion에 저장했어요!"
        else:
            result += f"\n\n⚠️ Notion 저장 실패: {notion_result.get('error', '')}"

    return result


# ──────────────────────────────────────────────────────────
# CLI 실행
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from rich.console import Console
    from rich.panel   import Panel
    from rich.markdown import Markdown

    console = Console()
    parser  = argparse.ArgumentParser(description="Agent J Vision 에이전트")
    parser.add_argument("--file",   required=True, help="분석할 파일 경로 (이미지 or PDF)")
    parser.add_argument("--ask",    default=None,  help="특정 질문 (없으면 전반적 분석)")
    parser.add_argument("--notion", action="store_true", help="결과를 Notion에 저장")
    args = parser.parse_args()

    path   = Path(args.file)
    suffix = path.suffix.lower()

    if suffix in SUPPORTED_IMAGES:
        result = analyze_image(args.file, args.ask)
    elif suffix in SUPPORTED_DOCS:
        result = analyze_pdf(args.file, args.ask)
    else:
        print(f"❌ 지원하지 않는 형식: {suffix}")
        sys.exit(1)

    console.print(Panel(Markdown(result), title=f"🔍 {path.name}", border_style="green"))

    if args.notion:
        r = _save_to_notion(path.stem, result, path.name)
        if r.get("success"):
            console.print("[green]✅ Notion 저장 완료[/green]")
        else:
            console.print(f"[red]❌ Notion 저장 실패: {r.get('error')}[/red]")
