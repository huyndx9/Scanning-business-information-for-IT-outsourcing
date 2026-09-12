"""Quét lại / quét hàng loạt từ terminal, lưu thẳng vào database.

    python backend/rescan_cli.py                 # quét lại mọi công ty đã lưu
    python backend/rescan_cli.py --urls list.txt # quét + lưu từng URL trong file (mỗi dòng một URL)
    python backend/rescan_cli.py --days 7        # chỉ quét lại công ty chưa quét trong 7 ngày

Mỗi lần lưu ghi thêm một dòng `scan_history`; số tin tuyển IT tăng giữa hai lần
quét hiện thành ▲ ở trang "Công ty đã lưu". Chạy hàng tuần bằng Windows Task
Scheduler (xem README) là có "báo động" mà không cần mở app.

저장된 기업 재스캔 / URL 목록 일괄 스캔 도구. 매번 scan_history에 기록되어
IT 채용 공고 증가를 추적할 수 있습니다.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.crawler import CrawlError  # noqa: E402
from backend.app.main import run_scan  # noqa: E402
from backend.app.security import UrlNotAllowed  # noqa: E402
from backend.app.storage import list_companies, save_result  # noqa: E402

# Quét tuần tự, nghỉ giữa các site: đây là quét lại định kỳ, không cần nhanh,
# và không muốn một lúc bắn 20 kết nối vào các website nhỏ.
PAUSE_SECONDS = 2


def _arrow(delta: int | None) -> str:
    if delta is None:
        return "  new "
    if delta > 0:
        return f"▲ +{delta}"
    if delta < 0:
        return f"▼ {delta}"
    return "  =  "


async def scan_and_save(url: str, require_contact: bool = False) -> dict | None:
    try:
        result = await run_scan(url)
    except (CrawlError, UrlNotAllowed) as exc:
        print(f"  x  {url}  ({exc})")
        return None
    except Exception as exc:  # noqa: BLE001 - một site lỗi không được dừng cả đợt
        print(f"  x  {url}  ({type(exc).__name__})")
        return None
    company = result.get("company") or {}
    if require_contact and not (company.get("email") or company.get("phone")):
        print(f"  -  {url}  (khong co email/dien thoai -> khong luu)")
        return None
    summary = save_result(result)
    print(f"  {_arrow(summary.get('jobs_delta'))}  {summary['it_jobs']:>2} IT  {summary['it_hiring']:<6} "
          f"{summary.get('name') or summary['domain']}")
    return summary


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--urls", help="file chứa URL, mỗi dòng một URL (quét + lưu, không cần đã có trong DB)")
    parser.add_argument("--days", type=int, default=0, help="chỉ quét lại công ty cập nhật cách đây hơn N ngày")
    parser.add_argument("--keep-no-contact", action="store_true",
                        help="với --urls: vẫn lưu site không có email lẫn điện thoại (mặc định bỏ qua)")
    args = parser.parse_args()

    if args.urls:
        with open(args.urls, encoding="utf-8") as handle:
            targets = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        targets = [
            company["website"] or f"https://{company['domain']}"
            for company in list_companies()
            if not args.days or datetime.fromisoformat(company["updated_at"]) < cutoff
        ]

    if not targets:
        print("khong co gi de quet.")
        return 0

    print(f"{len(targets)} site")
    rising: list[dict] = []
    for index, url in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] {url}")
        summary = await scan_and_save(url, require_contact=bool(args.urls) and not args.keep_no_contact)
        if summary and (summary.get("jobs_delta") or 0) > 0:
            rising.append(summary)
        if index < len(targets):
            await asyncio.sleep(PAUSE_SECONDS)

    print()
    if rising:
        print("IT 채용 증가 / tuyển IT tăng so với lần trước:")
        for summary in sorted(rising, key=lambda s: -s["jobs_delta"]):
            print(f"  ▲ +{summary['jobs_delta']:<3} {summary.get('name') or summary['domain']}  ({summary['website']})")
    else:
        print("khong co cong ty nao tang tin tuyen IT.")
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(asyncio.run(main()))
