"""build_server.py — FastAPI 서버를 PyInstaller로 .exe로 빌드"""
import subprocess, sys, shutil, os, stat
from pathlib import Path

ROOT = Path(__file__).parent

def _force_remove(func, path, exc_info):
    try: os.chmod(path, stat.S_IWRITE); func(path)
    except: pass

def build():
    print("=" * 50)
    print("  Agent J — FastAPI 서버 빌드 시작")
    print("=" * 50)

    try:
        import PyInstaller
        print(f"[✓] PyInstaller {PyInstaller.__version__} 확인")
    except ImportError:
        print("[!] PyInstaller 미설치 — 설치 중...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    for d in ["build", "server_dist"]:
        if (ROOT / d).exists():
            shutil.rmtree(ROOT / d, onexc=_force_remove)
            print(f"[✓] {d}/ 초기화")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole",
        "--name", "api_server",
        "--distpath", str(ROOT / "server_dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
        "--add-data", f"{ROOT / 'agents'};agents",
        "--add-data", f"{ROOT / 'tools'};tools",
        "--add-data", f"{ROOT / 'memory'};memory",
        "--add-data", f"{ROOT / 'orchestrator'};orchestrator",
        "--add-data", f"{ROOT / 'data'};data",
        "--hidden-import", "anthropic",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "notion_client",
        "--hidden-import", "google.auth",
        "--hidden-import", "googleapiclient",
        # requirements.txt 기반 추가 hidden import
        "--hidden-import", "rich",
        "--hidden-import", "rich.console",
        "--hidden-import", "rich.markdown",
        "--hidden-import", "dotenv",
        "--hidden-import", "multipart",
        "--hidden-import", "feedparser",
        "--hidden-import", "requests",
        "--hidden-import", "pypdf",
        "--hidden-import", "docx",
        "--hidden-import", "pptx",
        "--hidden-import", "plyer",
        "--hidden-import", "sqlite3",
        "--collect-all", "anthropic",
        "--collect-all", "fastapi",
        "--collect-all", "rich",
        str(ROOT / "server" / "api.py"),
    ]

    print("\n[→] PyInstaller 빌드 실행 중... (2-5분 소요)\n")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode == 0:
        exe_path = ROOT / "server_dist" / "api_server.exe"
        size_mb  = exe_path.stat().st_size / 1024 / 1024 if exe_path.exists() else 0
        print(f"\n{'='*50}\n  ✅ 빌드 성공!\n  📦 server_dist/api_server.exe ({size_mb:.1f} MB)\n{'='*50}")
    else:
        print("\n❌ 빌드 실패 — 위 오류 메시지 확인")
        sys.exit(1)

if __name__ == "__main__":
    build()
