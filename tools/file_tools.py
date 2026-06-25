"""
file_tools.py
Dev Agent가 사용하는 파일 조작 도구 모음
"""

import os
import subprocess
import sys
from pathlib import Path


def read_file(path: str) -> dict:
    """파일 내용을 읽어서 반환한다."""
    try:
        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"파일을 찾을 수 없음: {path}"}
        content = p.read_text(encoding="utf-8")
        return {"success": True, "content": content, "path": str(p.resolve())}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """파일에 내용을 작성한다. 디렉토리가 없으면 자동 생성."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "message": f"파일 저장 완료: {str(p.resolve())}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(directory: str = ".") -> dict:
    """디렉토리 내 파일/폴더 목록을 반환한다."""
    try:
        p = Path(directory)
        if not p.exists():
            return {"success": False, "error": f"디렉토리 없음: {directory}"}
        items = []
        for item in sorted(p.iterdir()):
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        return {"success": True, "directory": str(p.resolve()), "items": items}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_python(code: str) -> dict:
    """Python 코드를 실행하고 결과를 반환한다. 보안 주의: 신뢰된 코드만 실행."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30  # 30초 타임아웃
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "실행 시간 초과 (30초)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_directory(path: str) -> dict:
    """디렉토리를 생성한다 (이미 있어도 오류 없음)."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return {"success": True, "message": f"디렉토리 생성: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Dev Agent에 등록할 툴 스키마 목록
DEV_TOOLS = [
    {
        "name": "read_file",
        "description": "지정한 경로의 파일 내용을 읽어 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "읽을 파일 경로"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "지정한 경로에 파일을 생성하거나 덮어쓴다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "저장할 파일 경로"},
                "content": {"type": "string", "description": "파일에 쓸 내용"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "디렉토리 내 파일과 폴더 목록을 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "조회할 디렉토리 경로 (기본값: 현재 디렉토리)"}
            },
            "required": []
        }
    },
    {
        "name": "run_python",
        "description": "Python 코드를 실행하고 결과(stdout, stderr)를 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "실행할 Python 코드"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "create_directory",
        "description": "새 디렉토리를 생성한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "생성할 디렉토리 경로"}
            },
            "required": ["path"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """툴 이름과 입력을 받아 실행하고 결과를 문자열로 반환한다."""
    import json
    tool_map = {
        "read_file": read_file,
        "write_file": write_file,
        "list_files": list_files,
        "run_python": run_python,
        "create_directory": create_directory
    }
    if tool_name not in tool_map:
        return json.dumps({"success": False, "error": f"알 수 없는 툴: {tool_name}"})
    result = tool_map[tool_name](**tool_input)
    return json.dumps(result, ensure_ascii=False)
