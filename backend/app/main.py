"""FastAPI entrypoint.

POST /api/scan            -> crawl + extract, returns the result JSON
GET  /api/scan/stream     -> same work, streaming real progress over SSE
GET  /                    -> the scanner UI (frontend/index.html)
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .crawler import Crawler, CrawlError
from .extractor import build_result
from .security import DomainNotResolved, UrlNotAllowed, normalize_input_url, validate_url
from .storage import (
    delete_company,
    get_company,
    init_db,
    list_companies,
    save_result,
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

RESPECT_ROBOTS = os.environ.get("RESPECT_ROBOTS", "1") not in ("0", "false", "False")
ALLOW_PLAYWRIGHT = os.environ.get("ALLOW_PLAYWRIGHT", "1") not in ("0", "false", "False")

# Spec section 18 messages, keyed by error code.
ERROR_MESSAGES = {
    "invalid_url": "Invalid URL.",
    "unreachable": "Unable to access website.",
    "timeout": "Website request timed out.",
    "blocked": "Website blocked the request.",
    "internal": "Scan failed.",
}

app = FastAPI(title="Company Scanner", version="1.0.0")


class NoCacheStaticFiles(StaticFiles):
    """Buoc trinh duyet hoi lai server truoc khi dung ban trong cache.

    Khong co header nay, sua app.js/app.css xong trinh duyet van chay ban cu
    (no tu quyet dinh giu cache vi response khong noi gi ve cache).
    ETag van hoat dong nen lan sau chi ton mot request 304.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


def _page(name: str) -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / name,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


class ScanRequest(BaseModel):
    url: str


async def run_scan(raw_url: str, on_progress=None) -> dict:
    """Crawl the target site and extract the result. Raises CrawlError/UrlNotAllowed."""
    url = normalize_input_url(raw_url)
    validate_url(url)

    crawler = Crawler(url, respect_robots=RESPECT_ROBOTS, allow_playwright=ALLOW_PLAYWRIGHT)
    crawl = await crawler.run(on_progress=on_progress)

    if on_progress:
        await on_progress("extract", "Đang trích xuất thông tin...")
    result = build_result(crawl)
    result["scanned_url"] = url
    result["pages_crawled"] = len(crawl.pages)
    if on_progress:
        await on_progress("done", "Hoàn thành.")
    return result


def _error_payload(code: str, detail: str | None = None) -> dict:
    return {"error": {"code": code, "message": detail or ERROR_MESSAGES.get(code, "Scan failed.")}}


@app.post("/api/scan")
async def scan(request: ScanRequest) -> JSONResponse:
    try:
        result = await run_scan(request.url)
    except DomainNotResolved:
        return JSONResponse(status_code=502, content=_error_payload("unreachable"))
    except UrlNotAllowed as exc:
        return JSONResponse(status_code=400, content=_error_payload("invalid_url", str(exc)))
    except CrawlError as exc:
        return JSONResponse(status_code=502, content=_error_payload(exc.code, exc.message))
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content=_error_payload("timeout"))
    except Exception:
        return JSONResponse(status_code=500, content=_error_payload("internal"))
    return JSONResponse(content=result)


@app.get("/api/scan/stream")
async def scan_stream(url: str) -> StreamingResponse:
    """Server-sent events carrying the crawler's actual stage transitions."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def emit(event: str, data: dict) -> None:
        queue.put_nowait(f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n")

    async def on_progress(stage: str, message: str) -> None:
        emit("progress", {"stage": stage, "message": message})

    async def worker() -> None:
        try:
            result = await run_scan(url, on_progress=on_progress)
            emit("result", result)
        except DomainNotResolved:
            emit("scan_error", _error_payload("unreachable")["error"])
        except UrlNotAllowed as exc:
            emit("scan_error", _error_payload("invalid_url", str(exc))["error"])
        except CrawlError as exc:
            emit("scan_error", _error_payload(exc.code, exc.message)["error"])
        except asyncio.TimeoutError:
            emit("scan_error", _error_payload("timeout")["error"])
        except Exception:
            emit("scan_error", _error_payload("internal")["error"])
        finally:
            queue.put_nowait(None)

    async def stream():
        task = asyncio.create_task(worker())
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# -- Danh sach cong ty da luu ----------------------------------------------


class SaveRequest(BaseModel):
    result: dict


@app.post("/api/companies")
def save_company(request: SaveRequest) -> JSONResponse:
    """Luu ket qua scan. Quet lai cung domain se cap nhat dong da co."""
    try:
        summary = save_result(request.result)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_result", "message": str(exc)}})
    except Exception:
        return JSONResponse(status_code=500, content={"error": {"code": "storage", "message": "Could not save."}})
    return JSONResponse(content=summary)


@app.get("/api/companies")
def companies(full: int = 0) -> JSONResponse:
    """full=1 kem theo ket qua scan day du cua tung cong ty (dung khi xuat file)."""
    return JSONResponse(content={"companies": list_companies(include_results=bool(full))})


@app.get("/api/companies/{company_id}")
def company_detail(company_id: int) -> JSONResponse:
    saved = get_company(company_id)
    if saved is None:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Not found."}})
    return JSONResponse(content=saved)


@app.delete("/api/companies/{company_id}")
def company_delete(company_id: int) -> JSONResponse:
    if not delete_company(company_id):
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Not found."}})
    return JSONResponse(content={"deleted": company_id})


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "respect_robots": RESPECT_ROBOTS, "playwright": ALLOW_PLAYWRIGHT}


@app.get("/")
async def index() -> FileResponse:
    """Trang quét mới."""
    return _page("index.html")


@app.get("/saved")
async def saved_page() -> FileResponse:
    """Trang danh sách công ty đã lưu."""
    return _page("saved.html")


app.mount("/static", NoCacheStaticFiles(directory=str(FRONTEND_DIR)), name="static")
