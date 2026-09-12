"""Chụp ảnh thật của app cho README: python backend/take_screenshots.py
README용 실제 화면 캡처 도구.

Cần app đang chạy ở http://127.0.0.1:8000 và Playwright + Chromium đã cài
(`python -m playwright install chromium`). Ảnh lưu vào docs/screenshots/.

Ảnh chụp ở viewport 1280px, tỉ lệ 2x cho chữ Hàn sắc nét. Kết quả quét là
dữ liệu thật từ website được chỉ định — không có ảnh dựng.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"

# Site dùng để chụp kết quả: có đủ liên hệ, lãnh đạo và nhiều tin tuyển dụng IT.
DEMO_SITE = "https://www.scatterlab.co.kr"


async def clip_union(page, selectors: list[str], pad: int = 0) -> dict:
    """Vùng bao quanh nhiều phần tử, để chụp hai thẻ nằm cạnh nhau làm một ảnh.

    bounding_box() đo theo viewport, còn ảnh full-page tính theo toạ độ trang.
    Cuộn về đầu trang trước thì hai hệ toạ độ trùng nhau.
    """
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(150)
    boxes = []
    for selector in selectors:
        box = await page.locator(selector).first.bounding_box()
        if box:
            boxes.append(box)
    if not boxes:
        raise RuntimeError(f"khong tim thay phan tu: {selectors}")
    x = min(b["x"] for b in boxes) - pad
    y = min(b["y"] for b in boxes) - pad
    right = max(b["x"] + b["width"] for b in boxes) + pad
    bottom = max(b["y"] + b["height"] for b in boxes) + pad
    return {"x": max(0, x), "y": max(0, y), "width": right - x, "height": bottom - y}


async def shot_full_clip(page, name: str, selectors: list[str], pad: int = 12) -> None:
    """Chụp vùng bao của các phần tử trên ảnh full-page (không cần cuộn)."""
    clip = await clip_union(page, selectors, pad)
    await page.screenshot(path=str(OUT / name), full_page=True, clip=clip)
    print(f"  {name}")


async def shot_viewport(page, name: str) -> None:
    await page.screenshot(path=str(OUT / name))
    print(f"  {name}")


async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        # --lang: ô chọn ngày/tháng của Chromium hiển thị theo ngôn ngữ trình duyệt,
        # không theo `locale` của context, nên phải đặt ở đây để không lẫn tiếng Việt.
        browser = await pw.chromium.launch(args=["--lang=ko-KR"])
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=2,
            locale="ko-KR",
        )
        page = await context.new_page()

        # -- 1. Trang quét, tiếng Hàn mặc định ---------------------------------
        await page.goto(BASE + "/")
        await page.evaluate("localStorage.removeItem('company-scanner-lang')")
        await page.goto(BASE + "/")
        await page.wait_for_load_state("networkidle")
        await shot_viewport(page, "01-scan-home.png")

        # -- 2. Tiến trình quét thật ---------------------------------------------
        await page.fill("#url-input", DEMO_SITE)
        await page.click("#scan-btn")
        await page.wait_for_selector("#progress .stage-active", timeout=15000)
        await page.wait_for_timeout(1200)
        await shot_full_clip(page, "02-scan-progress.png", ["#url-input >> xpath=ancestor::div[contains(@class,'rounded-[20px]')]"])

        # -- 3-5. Kết quả -------------------------------------------------------
        await page.wait_for_selector("#results:not(.hidden)", timeout=120000)
        await page.wait_for_timeout(500)
        cards = "#results .lg\\:grid-cols-12 > div"
        await shot_full_clip(page, "03-result-company-contacts.png",
                             [f"{cards}:nth-child(1)", f"{cards}:nth-child(2)"])
        await shot_full_clip(page, "04-result-jobs.png", [f"{cards}:nth-child(3)"])
        await shot_full_clip(page, "05-result-sources.png", [f"{cards}:nth-child(4)"])

        # -- 6. JSON viewer -------------------------------------------------------
        await page.click("#json-btn")
        await page.wait_for_selector("#results pre")
        await shot_full_clip(page, "06-json-view.png", ["#results"])
        await page.click("#json-btn")

        # -- 7. Lưu vào database + trang đã lưu -------------------------------------
        await page.click("#save-btn")
        await page.wait_for_function("document.getElementById('save-btn').textContent.includes('저장됨')", timeout=10000)
        await shot_full_clip(page, "07-save-button.png", ["#results > div:first-child"])

        await page.goto(BASE + "/saved")
        await page.wait_for_selector("#saved-rows tr", timeout=10000)
        await shot_viewport(page, "08-saved-list.png")

        # -- 9. Tìm kiếm + menu xuất --------------------------------------------------
        await page.fill("#saved-filter", "ai")
        await page.wait_for_timeout(300)
        await page.click("#export-btn")
        await page.wait_for_selector("#export-menu:not(.hidden)")
        await shot_full_clip(page, "09-saved-search-export.png",
                             ["#saved-rows >> xpath=ancestor::div[contains(@class,'rounded-[20px]')]", "#export-menu"], pad=16)

        # -- 10. Chuyển ngôn ngữ ----------------------------------------------------
        await page.click("[data-lang-btn='vi']")
        await page.wait_for_timeout(300)
        await page.goto(BASE + "/")
        await page.wait_for_load_state("networkidle")
        await shot_viewport(page, "10-language-vietnamese.png")
        await page.click("[data-lang-btn='ko']")

        # -- 11. Thông báo lỗi ----------------------------------------------------------
        await page.fill("#url-input", "http://localhost:8000")
        await page.click("#scan-btn")
        await page.wait_for_selector("#error-box:not(.hidden)", timeout=15000)
        await shot_full_clip(page, "11-error.png", ["#error-box"])

        # -- 17. Quét hàng loạt: 2 site thật, tự lưu ---------------------------------
        await page.goto(BASE + "/")
        await page.wait_for_load_state("networkidle")
        await page.click("#batch-toggle")
        await page.fill("#batch-input", "https://www.inswave.com\nhttps://www.uracle.co.kr")
        await page.click("#batch-start")
        await page.wait_for_function(
            "document.querySelectorAll('#batch-rows tr').length === 2 && "
            "[...document.querySelectorAll('#batch-rows tr')].every(tr => !/대기|스캔 중/.test(tr.innerText))",
            timeout=240000,
        )
        await page.wait_for_timeout(300)
        await shot_full_clip(page, "17-batch-scan.png", ["#url-input >> xpath=ancestor::div[contains(@class,'rounded-[20px]')]"])

        # -- 12-15. CRM ----------------------------------------------------------------
        # Lead trong DB: tạo từ các công ty đã quét (nút "CRM 리드로 추가"), phần
        # sales (ngân sách, trạng thái, lịch) nhập tay. Không có lead thì bỏ qua.
        await page.goto(BASE + "/crm")
        await page.wait_for_load_state("networkidle")
        if await page.locator("#crm-rows tr").count() > 0:
            await shot_viewport(page, "12-crm-table.png")

            # Modal cao hơn viewport và nằm trên lớp phủ cố định, nên nới viewport
            # rồi chụp riêng phần tử thay vì cắt từ ảnh full-page.
            await page.set_viewport_size({"width": 1280, "height": 1900})
            await page.locator("#crm-rows tr").first.click()
            await page.wait_for_selector("#lead-modal:not(.hidden)")
            await page.wait_for_timeout(300)
            await page.locator("#lead-modal .crm-modal").screenshot(path=str(OUT / "13-crm-lead.png"))
            print("  13-crm-lead.png")

            # Mail nháp tiếng Hàn: chữ ký mẫu chỉ để minh hoạ, không lưu lại.
            await page.evaluate("localStorage.removeItem('company-scanner-mail-signature')")
            await page.click("#lead-mail-btn")
            await page.wait_for_selector("#lead-mail:not(.hidden)")
            await page.fill("#mail-signature", "홍길동 | ○○ IT 아웃소싱 영업팀 | 010-0000-0000")
            await page.wait_for_timeout(200)
            await page.locator("#lead-mail").screenshot(path=str(OUT / "16-crm-mail.png"))
            print("  16-crm-mail.png")
            await page.evaluate("localStorage.removeItem('company-scanner-mail-signature')")
            await page.keyboard.press("Escape")
            await page.set_viewport_size({"width": 1280, "height": 800})

            await page.click("[data-view='kanban']")
            await page.wait_for_timeout(300)
            await shot_full_clip(page, "14-crm-kanban.png", ["#crm-kpis", "#crm-kanban"])
            await page.click("[data-view='table']")

            # Xem trước nhập file: dùng chính CSV mẫu app cung cấp, không ghi vào DB.
            await page.click("#crm-import-btn")
            sample = await page.evaluate("fetch('/api/leads/sample.csv').then(r => r.text())")
            await page.set_input_files("#import-file", {
                "name": "leads_sample.csv", "mimeType": "text/csv", "buffer": sample.encode("utf-8"),
            })
            await page.wait_for_selector("#import-preview:not(.hidden)")
            await page.wait_for_timeout(300)
            await page.locator("#import-modal .crm-modal").screenshot(path=str(OUT / "15-crm-import.png"))
            print("  15-crm-import.png")
            await page.keyboard.press("Escape")

        # -- 18-19. Khách hàng / hợp đồng -----------------------------------------------
        await page.goto(BASE + "/customers")
        await page.wait_for_load_state("networkidle")
        if await page.locator(".cust-card").count() > 0:
            await page.locator(".cust-card-head").first.click()
            await page.wait_for_timeout(300)
            await shot_viewport(page, "18-customers.png")
            await page.set_viewport_size({"width": 1280, "height": 1400})
            await page.locator("[data-edit]").first.click()
            await page.wait_for_selector("#contract-modal:not(.hidden)")
            await page.wait_for_timeout(300)
            await page.locator("#contract-modal .crm-modal").screenshot(path=str(OUT / "19-contract-form.png"))
            print("  19-contract-form.png")
            await page.keyboard.press("Escape")
            await page.set_viewport_size({"width": 1280, "height": 800})

        await browser.close()

    total = sum(f.stat().st_size for f in OUT.glob("*.png"))
    print(f"\n{len(list(OUT.glob('*.png')))} anh, tong {total / 1024:.0f} KB -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
