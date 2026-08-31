"""Command-line scan: python backend/scan_cli.py https://www.example.co.kr"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.main import run_scan
from backend.app.crawler import CrawlError
from backend.app.security import UrlNotAllowed

async def main():
    if len(sys.argv) < 2:
        print("usage: python backend/scan_cli.py <url>"); return 2
    async def progress(stage, message):
        print(f"[{stage}] {message}", file=sys.stderr)
    try:
        result = await run_scan(sys.argv[1], on_progress=progress)
    except (CrawlError, UrlNotAllowed) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

raise SystemExit(asyncio.run(main()))
