"""Launcher: kiem tra moi thu roi chay app.

    python start.py            -> chay tren port trong dau tien tu 8000
    python start.py 8080       -> ep dung port 8080

Moi loi deu in ra man hinh kem cach xu ly, thay vi tat cua so ngay.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn[standard]",
    "httpx": "httpx",
    "bs4": "beautifulsoup4",
    "lxml": "lxml",
}


def say(message: str = "") -> None:
    print(message, flush=True)


def check_python() -> bool:
    if sys.version_info < (3, 10):
        say(f"[LOI] Can Python 3.10 tro len. Ban dang dung {sys.version.split()[0]}.")
        say("      Tai tai: https://www.python.org/downloads/")
        return False
    return True


def missing_packages() -> list[str]:
    missing = []
    for module, package in REQUIRED.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


def install(packages: list[str]) -> bool:
    say(f"Dang cai dependencies: {', '.join(packages)}")
    say("(lan dau chay se mat 1-2 phut)")
    say()
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *packages],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        say()
        say("[LOI] Cai dependencies that bai.")
        say("      Thu chay tay:")
        say(f'      "{sys.executable}" -m pip install -r "{ROOT / "backend" / "requirements.txt"}"')
        return False
    say()
    return True


def find_port(preferred: int | None = None) -> int | None:
    candidates = [preferred] if preferred else list(range(8000, 8011))
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                if preferred:
                    say(f"[LOI] Port {port} dang bi chiem boi chuong trinh khac.")
                    say("      Chay lai khong kem so port de app tu chon port trong.")
                    return None
                say(f"  port {port} dang ban, thu port khac...")
    say("[LOI] Khong tim thay port trong trong khoang 8000-8010.")
    return None


def open_browser_when_ready(url: str, port: int) -> None:
    """Cho server len roi moi mo trinh duyet."""
    for _ in range(60):
        time.sleep(0.5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(url)
                return


def main() -> int:
    say("=" * 58)
    say("  Company Scanner")
    say("=" * 58)
    say()

    if not check_python():
        return 1

    if not (ROOT / "frontend" / "index.html").is_file():
        say(f"[LOI] Khong tim thay frontend/index.html trong {ROOT}")
        say("      Hay chay file nay tu dung thu muc project.")
        return 1

    missing = missing_packages()
    if missing and not install(missing):
        return 1

    port = None
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            say(f"[LOI] Port khong hop le: {sys.argv[1]}")
            return 1

    port = find_port(port)
    if port is None:
        return 1

    url = f"http://127.0.0.1:{port}"
    say(f"App dang chay tai:  {url}")
    say("Trinh duyet se tu mo. Neu khong, copy dia chi tren vao trinh duyet.")
    say("Nhan Ctrl+C de dung.")
    say()

    threading.Thread(target=open_browser_when_ready, args=(url, port), daemon=True).start()

    # uvicorn phai chay voi cwd = project root de import duoc backend.app
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    try:
        import uvicorn

        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="info")
    except KeyboardInterrupt:
        say()
        say("Da dung app.")
    except Exception as exc:  # noqa: BLE001 - launcher phai in loi thay vi crash im lang
        say()
        say(f"[LOI] Server khong khoi dong duoc: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
