"""Real website crawler.

Spec sections 5, 6, 7, 12, 13, 18, 19:
  - actually fetches pages over HTTP (no simulated timers, no mock data)
  - MAX_PAGES = 20, MAX_DEPTH = 2, TIMEOUT = 15s
  - stays on the target's own registrable domain
  - decodes UTF-8 / EUC-KR / CP949 correctly
  - falls back to Playwright only for pages whose HTML is empty because of JS
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from .security import UrlNotAllowed, validate_url

MAX_PAGES = 20
MAX_DEPTH = 2
TIMEOUT = 15.0
MAX_BYTES = 3_000_000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 CompanyScanner/1.0"
)

# Pages worth visiting, by category (spec section 6).
PRIORITY_PATTERNS: dict[str, tuple[str, ...]] = {
    "company": (
        "회사소개", "회사 소개", "회사정보", "회사개요", "기업소개", "기업정보", "회사",
        "기업", "소개", "개요", "about", "aboutus", "about-us", "company", "corporate",
        "overview", "introduction", "greeting", "인사말",
    ),
    "contact": (
        "연락처", "오시는길", "오시는 길", "찾아오시는길", "찾아오시는 길", "주소", "문의",
        "contact", "contactus", "contact-us", "location", "directions", "map", "inquiry",
    ),
    "management": (
        "대표이사", "대표", "경영진", "임원", "조직도", "조직", "ceo", "cto", "cio",
        "개발책임자", "leadership", "management", "executive", "team", "people", "board",
    ),
    "recruitment": (
        "채용공고", "채용정보", "인재채용", "인재영입", "채용안내", "채용", "입사지원",
        "recruit", "recruitment", "career", "careers", "job", "jobs", "hiring", "apply",
        "employment", "wanted",
    ),
}

CATEGORY_WEIGHT = {"recruitment": 40, "management": 34, "company": 30, "contact": 28}

# Site đa ngôn ngữ (lgcns.com/kr, /en, /jp): bản tiếng Hàn là bản đầy đủ nhất
# (대표이사, 사업자등록번호, 채용) và extractor được viết cho tiếng Hàn. Link sang
# thư mục ngôn ngữ khác bị trừ điểm để xếp sau mọi trang tiếng Hàn — vẫn crawl
# nếu còn hạn mức, nên site chỉ có tiếng Anh không bị ảnh hưởng.
KOREAN_LANG_SEGMENTS = {"kr", "ko", "kor", "korean", "ko-kr"}
FOREIGN_LANG_SEGMENTS = {
    "en", "eng", "english", "en-us", "en-gb", "us", "uk", "global",
    "jp", "ja", "jpn", "japanese", "ja-jp",
    "cn", "zh", "chn", "chinese", "zh-cn", "zh-tw", "tw",
    "vi", "vn", "vie", "de", "fr", "es", "ru", "th", "id",
}
FOREIGN_LANG_PENALTY = 30

# Một site có thể có hàng chục trang tin tuyển dụng; không để chúng chiếm hết
# hạn mức trước khi tới trang công ty / lãnh đạo.
MAX_RECRUITMENT_PAGES = 8

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".zip", ".rar",
    ".exe", ".dmg", ".mp4", ".mp3", ".avi", ".mov", ".hwp", ".doc", ".docx", ".xls",
    ".xlsx", ".ppt", ".pptx", ".css", ".js", ".xml", ".json", ".rss",
)

# Paths that never carry company data but are common on Korean CMS sites.
SKIP_PATH_HINTS = (
    "/login", "/logout", "/join", "/member", "/mypage", "/cart", "/order", "/search",
    "/privacy", "/terms", "/sitemap", "/rss", "/download", "/wp-admin", "/wp-login",
    "/admin", "/board/write", "/bbs/write", "/password",
)

KOREAN_ENCODINGS = ("utf-8", "cp949", "euc-kr")

# Anchor dài hơn mức này là tiêu đề bài viết, không phải nhãn điều hướng.
NAV_ANCHOR_MAX = 30

# Dấu hiệu nhận ra trang tuyển dụng / ban lãnh đạo từ chính nội dung trang.
# Chỉ những cụm xuất hiện trong tin tuyển dụng thật. "인재채용"/"채용안내" bị loại
# vì đó thường là tên mục menu, có mặt trên mọi trang của site.
RECRUITMENT_STRONG_MARKERS = (
    "모집분야", "모집부문", "입사지원", "지원자격", "채용절차", "우대사항", "담당업무",
    "자격요건", "전형절차", "채용공고", "job opening", "job openings", "we are hiring",
    "open positions", "job description",
)
MANAGEMENT_MARKERS = ("대표이사", "경영진", "임원진", "조직도", "인사말", "ceo", "cto")

# Trang tin/bài viết hiếm khi chứa thông tin công ty; đừng tiêu ngân sách vào đó
# khi crawl thêm để dùng hết hạn mức trang.
LOW_VALUE_PATH_HINTS = (
    "/news", "/press", "/blog", "/insight", "/media", "/gallery", "/portfolio",
    "/column", "/archive", "/event", "/faq", "/notice", "/story", "/case",
)


class CrawlError(Exception):
    """Fatal crawl problem; `code` maps to a spec section 18 message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Page:
    url: str
    final_url: str
    status: int
    html: str
    text: str
    title: str
    category: str
    depth: int
    rendered: bool = False

    @property
    def soup(self) -> BeautifulSoup:
        if not hasattr(self, "_soup"):
            self._soup = BeautifulSoup(self.html, "lxml")
        return self._soup


@dataclass
class CrawlResult:
    start_url: str
    base_domain: str
    pages: list[Page] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def by_category(self, category: str) -> list[Page]:
        return [p for p in self.pages if p.category == category]


def registrable_domain(host: str) -> str:
    """Best-effort eTLD+1 without an external PSL dependency.

    Handles the Korean second-level suffixes this tool actually meets
    (co.kr, or.kr, ne.kr, ...) plus the usual generic ones.
    """
    host = (host or "").lower().strip(".")
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    two_level = {
        "co", "or", "ne", "go", "re", "pe", "kg", "ac", "ms", "hs", "es", "sc",
        "com", "net", "org", "gov", "edu", "mil",
    }
    if parts[-2] in two_level and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_company_domain(url: str, base_domain: str) -> bool:
    """Domain isolation (spec section 7): only the target's own domain/subdomains."""
    host = (urlsplit(url).hostname or "").lower().strip(".")
    if not host:
        return False
    return registrable_domain(host) == base_domain


def decode_body(content: bytes, content_type: str) -> str:
    """Decode HTML honouring HTTP charset, then <meta charset>, then CP949/EUC-KR."""
    declared: list[str] = []

    match = re.search(r"charset\s*=\s*[\"']?([\w\-]+)", content_type or "", re.I)
    if match:
        declared.append(match.group(1))

    head = content[:4096].decode("ascii", errors="ignore")
    for pattern in (
        r"<meta[^>]+charset\s*=\s*[\"']?([\w\-]+)",
        r"<\?xml[^>]+encoding\s*=\s*[\"']([\w\-]+)",
    ):
        m = re.search(pattern, head, re.I)
        if m:
            declared.append(m.group(1))

    candidates: list[str] = []
    for name in declared + list(KOREAN_ENCODINGS):
        normalized = name.lower().replace("_", "-").strip()
        if normalized in {"euc-kr", "ks-c-5601-1987", "ksc5601", "korean"}:
            normalized = "cp949"  # CP949 is a strict superset of EUC-KR.
        if normalized == "utf8":
            normalized = "utf-8"
        if normalized not in candidates:
            candidates.append(normalized)

    best_text, best_score = "", -1e9
    for enc in candidates:
        try:
            text = content.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue
        bad = text.count("�")
        # Mojibake check: EUC-KR bytes force-decoded as UTF-8 give U+FFFD, while
        # UTF-8 bytes decoded as CP949 give Latin-1 gibberish such as "ì°ë¦¬".
        mojibake = len(re.findall(r"[À-ÿ][-ÿ]", text))
        score = -(bad * 3 + mojibake)
        if score > best_score:
            best_text, best_score = text, score
        if bad == 0 and mojibake == 0:
            return text
    return best_text


def visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def footer_nodes(page: "Page") -> list:
    """Các khối footer của trang, theo thẻ <footer> hoặc class/id chứa 'footer'."""
    found = []
    for selector in ("footer", "[class*='footer']", "[id*='footer']", "address"):
        try:
            found.extend(page.soup.select(selector))
        except Exception:
            continue
    # Bỏ node lồng nhau: giữ node ngoài cùng.
    outermost = [n for n in found if not any(n is not other and other in n.parents for other in found)]
    return outermost[:6]


def footer_text(page: "Page") -> str:
    """Text vùng footer.

    Website Hàn hầu như luôn đặt 상호 / 대표이사 / 주소 / 전화 / 이메일 /
    사업자등록번호 ở footer, lặp trên mọi trang. Đọc chỗ này trước thì thường
    không phải mở thêm trang nào nữa.
    """
    parts = [node.get_text("\n", strip=True) for node in footer_nodes(page)]

    # Luôn kèm phần cuối trang: nhiều site đặt khối liên hệ ngoài thẻ <footer>,
    # và class chứa chữ "footer" đôi khi lại là carousel hay thanh điều hướng.
    lines = [line for line in page.text.split("\n") if line.strip()]
    parts.append("\n".join(lines[int(len(lines) * 0.75):]))

    text = "\n".join(part for part in parts if part.strip())
    return re.sub(r"\n{3,}", "\n\n", text)[:8000]


def _token_in(token: str, haystack: str) -> bool:
    """ASCII tokens must match as whole words.

    Without the boundaries, an article titled "Amazon DynamoDB now supports
    management" reads as the company's leadership page. Trailing digits stay
    allowed because Korean CMS URLs look like `bo_table=recruit01`.
    """
    if not haystack:
        return False
    if token.isascii():
        return re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", haystack) is not None
    return token in haystack


def _lang_segment(url: str) -> str | None:
    """Thư mục ngôn ngữ đứng đầu path ("/kr/company" -> "kr"), nếu có."""
    path = (urlsplit(url).path or "/").lower()
    first = path.strip("/").split("/", 1)[0] if path.strip("/") else ""
    if first in KOREAN_LANG_SEGMENTS or first in FOREIGN_LANG_SEGMENTS:
        return first
    return None


def foreign_language_link(url: str, home_url: str) -> bool:
    """Link thuộc thư mục ngôn ngữ khác với trang chủ (hoặc không phải tiếng Hàn)."""
    link_lang = _lang_segment(url)
    if link_lang is None:
        return False
    home_lang = _lang_segment(home_url)
    if home_lang is None:
        return link_lang in FOREIGN_LANG_SEGMENTS
    return link_lang != home_lang


def foreign_language_sitemap(url: str) -> int:
    """1 nếu tên file sitemap chỉ ra ngôn ngữ không phải tiếng Hàn (en-sitemap, jp...)."""
    name = (urlsplit(url).path or "").lower().rsplit("/", 1)[-1]
    tokens = set(re.split(r"[^a-z]+", name)) - {""}
    if tokens & KOREAN_LANG_SEGMENTS:
        return 0
    return 1 if tokens & FOREIGN_LANG_SEGMENTS else 0


def classify_link(url: str, anchor_text: str) -> str | None:
    """Return the priority category for a link, or None if it is not interesting."""
    split = urlsplit(url)
    target = f"{(split.path or '').lower()} {(split.query or '').lower()}"
    anchor = (anchor_text or "").strip().lower()
    # Navigation labels are short ("회사소개", "Careers"); a long anchor is an
    # article title and its wording must not decide the category.
    if len(anchor) > NAV_ANCHOR_MAX:
        anchor = ""
    segments = {
        segment.rsplit(".", 1)[0] for segment in (split.path or "").lower().split("/") if segment
    }
    for category in ("recruitment", "management", "company", "contact"):
        for token in PRIORITY_PATTERNS[category]:
            if category == "management" and token.isascii() and token not in ("ceo", "cto", "cio"):
                # "management" / "team" / "board" xuất hiện trong tên sản phẩm
                # ("process-management", "team-collaboration"): chỉ nhận khi là
                # nguyên một đoạn path hoặc là nhãn của link.
                if token in segments or _token_in(token, anchor):
                    return category
                continue
            if _token_in(token, target) or _token_in(token, anchor):
                return category
    return None


def content_category(page_text: str, title: str) -> str | None:
    """Classify a page by what it actually contains.

    Some sites link their careers board with a plain label ("공지사항", "N개
    포지션"), so the link alone never looks like recruitment. Reading the page
    settles it - and IT job extraction only looks at recruitment pages.
    """
    haystack = f"{title} {page_text[:4000]}".lower()
    if any(marker in haystack for marker in RECRUITMENT_STRONG_MARKERS):
        return "recruitment"
    if sum(1 for marker in MANAGEMENT_MARKERS if marker in haystack) >= 2:
        return "management"
    return None


def clean_link(base_url: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:", "file:")):
        return None
    try:
        absolute = urljoin(base_url, href)
    except ValueError:
        return None
    parts = urlsplit(absolute)
    if parts.scheme not in ("http", "https"):
        return None
    path = (parts.path or "/").lower()
    if path.endswith(SKIP_EXTENSIONS):
        return None
    if any(hint in path for hint in SKIP_PATH_HINTS):
        return None
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _looks_js_rendered(html: str, text: str) -> bool:
    """True when the served HTML has almost no content (SPA shell)."""
    if len(text) >= 400:
        return False
    lowered = html.lower()
    spa_markers = ('id="root"', "id='root'", 'id="app"', "id='app'", "__next", "ng-app", "v-app")
    return any(marker in lowered for marker in spa_markers) or len(text) < 200


class Crawler:
    def __init__(self, start_url: str, respect_robots: bool = True, allow_playwright: bool = True):
        self.start_url = start_url
        self.respect_robots = respect_robots
        self.allow_playwright = allow_playwright
        self.base_domain = ""
        self._robots: RobotFileParser | None = None
        self._robots_loaded = False
        self._seen: set[str] = set()
        self._spare: dict[str, int] = {}   # link cung domain chua phan loai -> do sau path
        self._seen_final: set[str] = set()  # URL DICH da luu, chan ban sao sau redirect
        self._seen_content: set[int] = set()  # van tay noi dung, chan trang trung noi dung

    # -- HTTP ---------------------------------------------------------------

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        """Fetch one URL, re-validating each redirect hop against the SSRF rules."""
        current = url
        for _ in range(6):
            validate_url(current)
            response = await client.get(current, follow_redirects=False)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    return response
                current = urljoin(current, location)
                continue
            return response
        raise CrawlError("unreachable", "Too many redirects.")

    async def _robots_allows(self, client: httpx.AsyncClient, url: str) -> bool:
        if not self.respect_robots:
            return True
        if not self._robots_loaded:
            self._robots_loaded = True
            parts = urlsplit(url)
            robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
            try:
                response = await client.get(robots_url, follow_redirects=True)
                if response.status_code == 200 and len(response.content) < 500_000:
                    body = decode_body(response.content, response.headers.get("content-type", ""))
                    parser = RobotFileParser()
                    parser.parse(body.splitlines())
                    self._robots = parser
            except (httpx.HTTPError, UrlNotAllowed, ValueError):
                self._robots = None
        if self._robots is None:
            return True
        try:
            return self._robots.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    async def _render_with_playwright(self, url: str) -> str | None:
        """Only used when the plain HTML is an empty JS shell (spec section 13)."""
        if not self.allow_playwright:
            return None
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(args=["--no-sandbox"])
                try:
                    context = await browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
                    page = await context.new_page()
                    await page.goto(url, timeout=int(TIMEOUT * 1000), wait_until="domcontentloaded")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    return await page.content()
                finally:
                    await browser.close()
        except Exception:
            return None

    async def _build_page(
        self, response: httpx.Response, requested_url: str, category: str, depth: int
    ) -> Page:
        content_type = response.headers.get("content-type", "")
        html = decode_body(response.content[:MAX_BYTES], content_type)
        text = visible_text(html)
        rendered = False
        if _looks_js_rendered(html, text):
            js_html = await self._render_with_playwright(str(response.url))
            if js_html:
                html, rendered = js_html, True
                text = visible_text(html)
        soup = BeautifulSoup(html, "lxml")
        return Page(
            url=requested_url,
            final_url=str(response.url),
            status=response.status_code,
            html=html,
            text=text,
            title=(soup.title.get_text(strip=True) if soup.title else ""),
            category=category,
            depth=depth,
            rendered=rendered,
        )

    async def _fetch_page(
        self, client: httpx.AsyncClient, url: str, category: str, depth: int
    ) -> Page | None:
        """Fetch a non-homepage URL. A single failure never aborts the scan."""
        if not await self._robots_allows(client, url):
            return None
        try:
            response = await self._get(client, url)
        except (UrlNotAllowed, httpx.HTTPError, CrawlError, asyncio.TimeoutError):
            return None

        if response.status_code >= 400:
            return None
        content_type = response.headers.get("content-type", "")
        if content_type and not any(k in content_type.lower() for k in ("html", "text")):
            return None

        page = await self._build_page(response, url, category, depth)
        # Trang được lấy về vì lý do khác vẫn có thể là trang tuyển dụng /
        # ban lãnh đạo; nội dung mới là bằng chứng thật.
        if page.category in ("other", "company", "contact"):
            better = content_category(page.text, page.title)
            if better:
                page.category = better
        return page

    # -- Crawl loop ---------------------------------------------------------

    @staticmethod
    def _dedupe_key(url: str) -> str:
        """www and non-www serve the same page; treat them as one."""
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return f"{host}{(parts.path or '/').rstrip('/')}?{parts.query}"

    def _collect_links(self, page: Page) -> list[tuple[str, str, int]]:
        """Return (url, category, score) for on-domain priority links on a page.

        Link cung domain nhung khong thuoc 4 nhom uu tien duoc giu lai trong
        `self._spare` de dung not han muc trang neu con thua.
        """
        found: dict[str, tuple[str, int]] = {}

        # Site cũ dùng <frameset>: trang chủ rỗng, toàn bộ nội dung (và menu)
        # nằm trong <frame src="...">. Không đọc frame thì crawl dừng ngay.
        for frame in page.soup.find_all(["frame", "iframe"], src=True):
            url = clean_link(page.final_url, frame.get("src", ""))
            if not url or not same_company_domain(url, self.base_domain):
                continue
            category = classify_link(url, "") or "company"
            found[url] = (category, max(CATEGORY_WEIGHT.values()) + 10)

        for anchor in page.soup.find_all("a", href=True):
            url = clean_link(page.final_url, anchor.get("href", ""))
            if not url or not same_company_domain(url, self.base_domain):
                continue
            anchor_text = anchor.get_text(" ", strip=True)[:120]
            category = classify_link(url, anchor_text)
            if not category:
                path = (urlsplit(url).path or "/").lower()
                if not any(hint in path for hint in LOW_VALUE_PATH_HINTS):
                    self._spare.setdefault(url, path.count("/"))
                continue
            score = CATEGORY_WEIGHT[category]
            # Shallow URLs are usually the section index, not a stray detail page.
            score -= min((urlsplit(url).path or "/").count("/"), 5)
            previous = found.get(url)
            if previous is None or score > previous[1]:
                found[url] = (category, score)
        return [(url, category, score) for url, (category, score) in found.items()]

    async def _discover_from_sitemap(
        self, client: httpx.AsyncClient, home_url: str
    ) -> list[tuple[str, str, int]]:
        """Pull priority URLs out of sitemap.xml (bounded, same domain only)."""
        parts = urlsplit(home_url)
        candidates = [urlunsplit((parts.scheme, parts.netloc, "/sitemap.xml", "", ""))]
        if self._robots is not None:
            candidates.extend(getattr(self._robots, "sitemaps", None) or [])

        found: dict[str, tuple[str, int]] = {}
        checked = 0
        visited: set[str] = set()
        while candidates and checked < 6:
            # Site đa ngôn ngữ có sitemap riêng cho từng tiếng: đọc bản tiếng Hàn
            # trước, bản nước ngoài để cuối - hạn mức file có thể không tới lượt.
            candidates.sort(key=lambda url: (foreign_language_sitemap(url), 0))
            sitemap_url = candidates.pop(0)
            if sitemap_url in visited:
                continue
            visited.add(sitemap_url)
            checked += 1
            try:
                validate_url(sitemap_url)
                response = await client.get(sitemap_url, follow_redirects=True, timeout=8.0)
            except (httpx.HTTPError, UrlNotAllowed, ValueError):
                continue
            if response.status_code != 200 or len(response.content) > 5_000_000:
                continue
            body = decode_body(response.content, response.headers.get("content-type", ""))
            locations = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body, re.I)[:2000]
            is_index = "<sitemapindex" in body.lower()
            for location in locations:
                if is_index:
                    if location not in visited and location not in candidates and len(candidates) < 8:
                        candidates.append(location)
                    continue
                url = clean_link(sitemap_url, location)
                if not url or not same_company_domain(url, self.base_domain):
                    continue
                category = classify_link(url, "")
                if not category:
                    continue
                score = CATEGORY_WEIGHT[category] - min((urlsplit(url).path or "/").count("/"), 5)
                previous = found.get(url)
                if previous is None or score > previous[1]:
                    found[url] = (category, score)
        return [(url, category, score) for url, (category, score) in found.items()]

    @staticmethod
    def _covered_by_footer(page: Page) -> set[str]:
        """Nhóm trang không cần ưu tiên nữa vì footer đã có sẵn dữ liệu.

        Import muộn để tránh vòng import: extractor import crawler ở mức module.
        """
        from .extractor import ADDRESS_RE, EMAIL_RE, NAME_LABELS, PHONE_RE, _label_value

        text = footer_text(page)
        if not text:
            return set()

        has_contact = bool(
            ADDRESS_RE.search(text) and PHONE_RE.search(text)
            and (EMAIL_RE.search(text) or page.soup.find(attrs={"data-cfemail": True}))
        )
        covered = {"contact"} if has_contact else set()
        if has_contact and _label_value(text, NAME_LABELS, 60):
            covered.add("company")
        return covered

    def _accept_page(self, result: CrawlResult, page: Page) -> bool:
        """Luu trang neu no thuc su moi.

        Nhieu URL khong ton tai lai redirect ve trang chu; neu chi khu trung lap
        theo URL yeu cau thi ca han muc 20 trang bi dot vao ban sao trang chu.
        """
        if not same_company_domain(page.final_url, self.base_domain):
            return False   # redirect ra ngoai domain (spec muc 7)
        key = self._dedupe_key(page.final_url)
        if key in self._seen_final:
            return False

        # CMS Hàn hay phục vụ cùng một nội dung dưới nhiều tham số URL khác nhau
        # (?me_code=..., thứ tự query khác). So theo nội dung mới hết trùng.
        if len(page.text) >= 200:
            fingerprint = hash(page.text[:2000])
            if fingerprint in self._seen_content:
                return False
            self._seen_content.add(fingerprint)

        self._seen_final.add(key)
        self._seen.add(key)
        result.pages.append(page)
        return True

    async def run(
        self, on_progress: Callable[[str, str], Awaitable[None]] | None = None
    ) -> CrawlResult:
        async def notify(stage: str, message: str) -> None:
            if on_progress:
                await on_progress(stage, message)

        validated = validate_url(self.start_url)
        self.base_domain = registrable_domain(validated.host)
        result = CrawlResult(start_url=self.start_url, base_domain=self.base_domain)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8,vi;q=0.7",
        }
        limits = httpx.Limits(max_connections=6, max_keepalive_connections=6)
        async with httpx.AsyncClient(
            headers=headers, timeout=TIMEOUT, limits=limits, verify=False
        ) as client:
            await notify("homepage", "Đang truy cập trang chủ...")
            home = await self._try_homepage(client, validated.url)
            if home is None:
                raise CrawlError("unreachable", "Unable to access website.")
            self._seen.add(self._dedupe_key(home.final_url))
            self._seen_final.add(self._dedupe_key(home.final_url))
            result.pages.append(home)

            # Footer trang chủ thường đã đủ thông tin liên hệ. Nếu vậy thì hạ ưu
            # tiên các trang chỉ để lấy lại đúng những thứ đó, dành hạn mức trang
            # cho ban lãnh đạo và tuyển dụng - phần hay thiếu.
            covered = self._covered_by_footer(home)
            penalty = {category: (25 if category in covered else 0) for category in CATEGORY_WEIGHT}

            def lang_penalty(url: str) -> int:
                return FOREIGN_LANG_PENALTY if foreign_language_link(url, home.final_url) else 0

            frontier: list[tuple[int, str, str, int]] = [
                (score - penalty.get(category, 0) - lang_penalty(url), url, category, 1)
                for url, category, score in self._collect_links(home)
            ]
            # Careers pages are often absent from the nav but present in sitemap.xml.
            for url, category, score in await self._discover_from_sitemap(client, home.final_url):
                frontier.append((score - lang_penalty(url), url, category, 1))

            stage_messages = {
                "company": ("company", "Đang tìm trang công ty..."),
                "contact": ("contact", "Đang tìm thông tin liên hệ..."),
                "management": ("management", "Đang tìm ban lãnh đạo..."),
                "recruitment": ("recruitment", "Đang tìm tuyển dụng..."),
            }
            announced: set[str] = set()
            recruitment_pages = 0
            cap_recruitment = True
            deferred: list[tuple[int, str, str, int]] = []   # tin tuyển dụng vượt hạn mức, đọc sau cùng

            while (frontier or deferred) and len(result.pages) < MAX_PAGES:
                if not frontier:
                    frontier, deferred, cap_recruitment = deferred, [], False
                frontier.sort(key=lambda item: -item[0])
                _score, url, category, depth = frontier.pop(0)
                key = self._dedupe_key(url)
                if key in self._seen:
                    continue
                if cap_recruitment and category == "recruitment" and recruitment_pages >= MAX_RECRUITMENT_PAGES:
                    deferred.append((_score, url, category, depth))
                    continue
                self._seen.add(key)
                if depth > MAX_DEPTH:
                    continue
                if category == "recruitment":
                    recruitment_pages += 1

                if category not in announced:
                    announced.add(category)
                    stage, message = stage_messages[category]
                    await notify(stage, message)

                page = await self._fetch_page(client, url, category, depth)
                if page is None:
                    result.errors.append(f"skipped: {url}")
                    continue
                if not self._accept_page(result, page):
                    continue

                if depth < MAX_DEPTH:
                    for child_url, child_category, child_score in self._collect_links(page):
                        if self._dedupe_key(child_url) in self._seen:
                            continue
                        # Job detail pages under a recruitment index are the useful ones.
                        bonus = 6 if child_category == category == "recruitment" else 0
                        frontier.append(
                            (child_score + bonus - 5 - lang_penalty(child_url), child_url, child_category, depth + 1)
                        )

            # Nhieu site khong dat thong tin o trang chu va cung khong dat ten
            # link theo tu khoa quen thuoc. Con han muc thi doc them cac trang
            # cung domain, uu tien trang nong nhat.
            if len(result.pages) < MAX_PAGES and self._spare:
                for url, depth_hint in sorted(self._spare.items(), key=lambda item: (item[1], len(item[0]))):
                    if len(result.pages) >= MAX_PAGES:
                        break
                    key = self._dedupe_key(url)
                    if key in self._seen:
                        continue
                    self._seen.add(key)
                    page = await self._fetch_page(client, url, "other", 1)
                    if page is None:
                        continue
                    self._accept_page(result, page)

            for category in ("company", "contact", "management", "recruitment"):
                if category not in announced:
                    stage, message = stage_messages[category]
                    await notify(stage, message)

        return result

    async def _try_homepage(self, client: httpx.AsyncClient, url: str) -> Page | None:
        """Try the URL as given, then the www/non-www and http/https variants."""
        parts = urlsplit(url)
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        alt_host = host[4:] if host.startswith("www.") else "www." + host
        other_scheme = "http" if parts.scheme == "https" else "https"
        candidates = [
            url,
            urlunsplit((parts.scheme, alt_host + port, parts.path, parts.query, "")),
            urlunsplit((other_scheme, parts.netloc, parts.path, parts.query, "")),
        ]

        blocked = False
        timed_out = False
        for candidate in candidates:
            if not await self._robots_allows(client, candidate):
                blocked = True
                continue
            try:
                response = await self._get(client, candidate)
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout, asyncio.TimeoutError):
                timed_out = True
                continue
            except (UrlNotAllowed, httpx.HTTPError, CrawlError):
                continue

            if response.status_code in (401, 403, 429, 451):
                blocked = True
                continue
            if response.status_code >= 400:
                continue

            page = await self._build_page(response, candidate, "home", 0)
            self.base_domain = registrable_domain(urlsplit(page.final_url).hostname or "")
            return page

        if blocked:
            raise CrawlError("blocked", "Website blocked the request.")
        if timed_out:
            raise CrawlError("timeout", "Website request timed out.")
        return None
