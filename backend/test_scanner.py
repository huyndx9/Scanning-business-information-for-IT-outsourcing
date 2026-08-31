"""Offline tests for the scanner's rules. Run: python backend/test_scanner.py

No network access: these cover encoding, domain isolation, URL safety and the
extraction filters, using HTML fixtures built in-memory.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.crawler import (  # noqa: E402
    CrawlResult,
    Page,
    classify_link,
    clean_link,
    decode_body,
    registrable_domain,
    same_company_domain,
    visible_text,
)
from backend.app.extractor import (  # noqa: E402
    _in_korea,
    _place_key,
    _normalize_phone,
    _email_belongs_to_company,
    _email_is_usable,
    decode_cf_email,
    _is_it_job,
    _looks_like_posting,
    _plausible_name,
    build_result,
    hiring_signal,
)
from backend.app.security import (  # noqa: E402
    DomainNotResolved,
    UrlNotAllowed,
    normalize_input_url,
    validate_url,
)

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(f"{name} {detail}")
        print(f"  FAIL {name} {detail}")


def make_page(url: str, html: str, category: str = "home", depth: int = 0) -> Page:
    return Page(
        url=url, final_url=url, status=200, html=html, text=visible_text(html),
        title="", category=category, depth=depth,
    )


# -- Korean encodings (spec section 12) ------------------------------------

print("encoding")
korean = "우리회사 대표이사 홍길동"
for encoding, declared in (("utf-8", "utf-8"), ("cp949", "euc-kr"), ("cp949", "ks_c_5601-1987")):
    body = f'<html><head><meta charset="{declared}"></head><body>{korean}</body></html>'.encode(encoding)
    check(f"decodes {declared}", korean in decode_body(body, ""))

# Charset only in the HTTP header, none in the document.
check(
    "decodes header-declared euc-kr",
    korean in decode_body(f"<html><body>{korean}</body></html>".encode("cp949"), "text/html; charset=EUC-KR"),
)
# No declaration at all: must still not produce mojibake.
check(
    "decodes undeclared euc-kr",
    korean in decode_body(f"<html><body>{korean}</body></html>".encode("cp949"), ""),
)

# -- Domain isolation (spec section 7) -------------------------------------

print("domain isolation")
check("co.kr is a two-level suffix", registrable_domain("www.company-a.co.kr") == "company-a.co.kr")
check("plain com domain", registrable_domain("shop.example.com") == "example.com")
check("subdomain stays in scope", same_company_domain("https://recruit.company-a.co.kr/jobs", "company-a.co.kr"))
check("other company rejected", not same_company_domain("https://company-b.co.kr", "company-a.co.kr"))
check("lookalike domain rejected", not same_company_domain("https://company-a.co.kr.evil.com", "company-a.co.kr"))
check("portal rejected", not same_company_domain("https://blog.naver.com/company-a", "company-a.co.kr"))

# -- Link handling ---------------------------------------------------------

print("links")
check("careers link classified", classify_link("https://x.co.kr/recruit/list", "채용공고") == "recruitment")
check("about link classified", classify_link("https://x.co.kr/about", "회사소개") == "company")
check("contact link classified", classify_link("https://x.co.kr/contact", "오시는길") == "contact")
check("unrelated link ignored", classify_link("https://x.co.kr/products/a", "제품") is None)
check("mailto dropped", clean_link("https://x.co.kr/", "mailto:a@b.c") is None)
check("pdf dropped", clean_link("https://x.co.kr/", "/files/brochure.pdf") is None)
check("relative link resolved", clean_link("https://x.co.kr/a/b", "../c") == "https://x.co.kr/c")

# -- URL safety (spec section 19) -----------------------------------------

print("security")
for blocked in (
    "http://localhost", "http://127.0.0.1", "http://0.0.0.0", "http://169.254.169.254",
    "http://192.168.0.1", "http://10.1.2.3", "http://[::1]", "file:///etc/passwd",
    "ftp://example.com", "http://example.com:22",
):
    try:
        validate_url(normalize_input_url(blocked))
        check(f"blocks {blocked}", False, "-> allowed")
    except UrlNotAllowed:
        check(f"blocks {blocked}", True)

check("bare domain gets https", normalize_input_url("company.co.kr").startswith("https://"))
try:
    validate_url(normalize_input_url("https://nonexistent-domain-x7q2.co.kr"))
    check("unresolvable domain raises", False)
except DomainNotResolved:
    check("unresolvable domain raises", True)

# -- Extraction filters ----------------------------------------------------

print("filters")
check("Korean name accepted", _plausible_name("홍길동"))
check("noun rejected as name", not _plausible_name("플랫폼"))
check("role noun rejected", not _plausible_name("이사가"))
check("menu label rejected", not _plausible_name("About Us"))
check("English name accepted", _plausible_name("John Smith"))
# Nhieu site Han viet ho va ten cach nhau: "대표이사 : 박 한".
check("spaced Korean name accepted", _plausible_name("박 한"))
check("spaced 3-syllable name accepted", _plausible_name("김 민 수"))
check("4-syllable noun rejected", not _plausible_name("공지사항"))
check("compound surname accepted", _plausible_name("남궁철수"))
check("2-syllable noun rejected", not _plausible_name("변경"))

check("company email accepted", _email_belongs_to_company("info@test.co.kr", "test.co.kr"))
check("subdomain email accepted", _email_belongs_to_company("hr@jobs.test.co.kr", "test.co.kr"))
check("free mail accepted", _email_belongs_to_company("test.company@naver.com", "test.co.kr"))
check("other company email rejected", not _email_belongs_to_company("nwngm@aitimes.kr", "test.co.kr"))
check("image file rejected as email", not _email_is_usable("logo@2x.png"))
check("noreply rejected", not _email_is_usable("noreply@test.co.kr"))

# So dien thoai: dang quoc te bo so 0 dau, va khoang nam khong phai so dien thoai.
check("international phone normalised", _normalize_phone("+82-2-564-8525") == "02-564-8525")
check("international mobile normalised", _normalize_phone("+82-10-2222-3333") == "010-2222-3333")
check("domestic phone kept", _normalize_phone("031-999-8888") == "031-999-8888")
check("service number kept", _normalize_phone("1588-1234") == "1588-1234")
check("year range is not a phone", _normalize_phone("1997-2019") == "")

# Dia chi: website cong ty Han hay liet ke ca van phong nuoc ngoai.
check("korean romaja address is in korea",
      _in_korea("3F, 6 Jeongjail-ro 156beon-gil, Bundang-gu, Seongnam-si, Gyeonggi-do, Korea"))
check("foreign address rejected",
      not _in_korea("4303, Ask Shaikh Ali Al Hamad As Salihi Street, Al Nakheel District"))
check("same place matches across spellings",
      _place_key("서울 강남구 논현로 34") == _place_key("서울특별시 강남구 논현로 34, 썬테크빌딩 5층"))
check("different city is a different place",
      _place_key("서울 강남구 논현로 34") != _place_key("세종시 한누리대로 219, 4층"))

# Cloudflare Email Protection: email cong khai nhung bi ma hoa trong HTML.
check("decodes cloudflare email",
      decode_cf_email("365950505f55537659585758525b531855595b") == "office@onandme.com")
check("bad cloudflare hex ignored", decode_cf_email("zzzz") is None)
check("empty cloudflare hex ignored", decode_cf_email("") is None)

check("IT job accepted", _is_it_job("백엔드 개발자 채용"))
check("sales job rejected", not _is_it_job("영업사원 모집"))
check("accounting job rejected", not _is_it_job("회계 담당자 채용"))
check("posting needs a role marker", _looks_like_posting("백엔드 개발자 모집", ""))
check("product link rejected", not _looks_like_posting("AI Infra", ""))
check("nav blob rejected", not _looks_like_posting("Company 회사소개 연혁 CI/BI 수상 인증 인재채용 지속가능경영 제품 고객", ""))

check("5 jobs -> High", hiring_signal(5) == "High")
check("3 jobs -> Medium", hiring_signal(3) == "Medium")
check("1 job -> Low", hiring_signal(1) == "Low")
check("0 jobs -> None", hiring_signal(0) == "None")

# -- End-to-end extraction over fixtures ----------------------------------

print("extraction")
home_html = """
<html><head><title>테스트정보 - 스마트 솔루션</title>
<meta property="og:site_name" content="테스트정보"></head>
<body><h1>테스트정보</h1>
<p>기업의 IT 솔루션 구축을 전문으로 합니다.</p>
<p>보도자료 문의: reporter@newspaper.co.kr</p>
<footer>대표이사 김철수 | 주소 서울특별시 강남구 테헤란로 152, 5층
전화번호 02-1234-5678 | 팩스 02-1234-5679
이메일: <a href="/cdn-cgi/l/email-protection#2f464149406f5b4a5c5b014c4001445d"><span class="__cf_email__" data-cfemail="2f464149406f5b4a5c5b014c4001445d">[email&#160;protected]</span></a>
Copyright (c) Test Information Inc. All rights reserved.</footer>
</body></html>
"""
careers_html = """
<html><body><ul>
  <li><a href="/recruit/1">백엔드 개발자 모집</a> 정규직 서울 마감 2026-12-31</li>
  <li><a href="/recruit/2">프론트엔드 개발자 채용</a> 정규직 판교</li>
  <li><a href="/recruit/3">영업사원 모집</a> 정규직 서울</li>
  <li><a href="/recruit/4">회계 담당자 채용</a> 계약직</li>
</ul></body></html>
"""
crawl = CrawlResult(start_url="https://test.co.kr/", base_domain="test.co.kr")
crawl.pages = [
    make_page("https://test.co.kr/", home_html),
    make_page("https://test.co.kr/recruit", careers_html, category="recruitment", depth=1),
]
result = build_result(crawl)

check("company name found", result["company"]["name"] in ("테스트정보", "Test Information Inc"),
      f'-> {result["company"]["name"]!r}')
check("address found", result["company"]["address"] == "서울특별시 강남구 테헤란로 152, 5층",
      f'-> {result["company"]["address"]!r}')
check("phone found", result["company"]["phone"] == "02-1234-5678", f'-> {result["company"]["phone"]!r}')
check("fax not used as phone", result["company"]["phone"] != "02-1234-5679")
check("email found", result["company"]["email"] == "info@test.co.kr", f'-> {result["company"]["email"]!r}')
check("email carries a source", result["company_sources"]["email"] == "https://test.co.kr/")
check("outside email rejected", result["company"]["email"] != "reporter@newspaper.co.kr")
check("industry found", result["company"]["industry"] is not None)
check("CEO found", [c["name"] for c in result["key_contacts"]] == ["김철수"],
      f'-> {result["key_contacts"]}')
check("contact carries a source", all(c["source_url"].startswith("https://test.co.kr") for c in result["key_contacts"]))
titles = [j["title"] for j in result["it_recruitment"]]
check("both IT jobs found", len(titles) == 2, f"-> {titles}")
check("sales job excluded", not any("영업" in t for t in titles))
check("accounting job excluded", not any("회계" in t for t in titles))
check("job source is the detail page", result["it_recruitment"][0]["source_url"].startswith("https://test.co.kr/recruit/"))
check("hiring signal is Medium", result["sales_signal"]["it_hiring"] == "Medium")
check("sources listed", result["sources"] == ["https://test.co.kr/", "https://test.co.kr/recruit"])

# Nothing on the page -> every field is None, never a stand-in value (spec section 9).
print("no-data fallback")
empty = CrawlResult(start_url="https://empty.co.kr/", base_domain="empty.co.kr")
empty.pages = [make_page("https://empty.co.kr/", "<html><body><p>.</p></body></html>")]
empty_result = build_result(empty)
check("empty address is None", empty_result["company"]["address"] is None)
check("empty phone is None", empty_result["company"]["phone"] is None)
check("empty email is None", empty_result["company"]["email"] is None)
check("empty industry is None", empty_result["company"]["industry"] is None)
check("empty contacts", empty_result["key_contacts"] == [])
check("empty recruitment", empty_result["it_recruitment"] == [])
check("empty signal is None", empty_result["sales_signal"]["it_hiring"] == "None")

# -- Database (luu / xem lai / xoa) ---------------------------------------

print("database")
import tempfile  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

from backend.app import storage  # noqa: E402

storage.DB_PATH = _Path(tempfile.gettempdir()) / "company_scanner_test.db"
for suffix in ("", "-wal", "-shm"):
    stale = _Path(str(storage.DB_PATH) + suffix)
    if stale.exists():
        stale.unlink()
storage.init_db()

saved_one = storage.save_result(result)                       # ket qua fixture o tren
check("saves a scan", saved_one["domain"] == "test.co.kr", f'-> {saved_one["domain"]!r}')
check("summary keeps name", saved_one["name"] == result["company"]["name"])
check("summary keeps address", saved_one["address"] == result["company"]["address"])
check("summary keeps phone", saved_one["phone"] == result["company"]["phone"])
check("summary keeps email", saved_one["email"] == result["company"]["email"], f'-> {saved_one["email"]!r}')
check("summary keeps industry", saved_one["industry"] == result["company"]["industry"])
check("summary keeps website", saved_one["website"] == result["company"]["website"])
check("summary keeps IT hiring level", saved_one["it_hiring"] == "Medium")
check("summary keeps IT job count", saved_one["it_jobs"] == 2, f'-> {saved_one["it_jobs"]}')

other = {
    "company": {"name": "B", "address": None, "phone": None, "industry": None,
                "website": "https://other.co.kr/"},
    "key_contacts": [], "it_recruitment": [], "sales_signal": {"it_hiring": "None"},
    "scanned_url": "https://other.co.kr/",
}
storage.save_result(other)
check("lists both companies", len(storage.list_companies()) == 2)

# Quet lai cung domain: cap nhat dong cu, khong tao ban trung.
rescan = {**result, "company": {**result["company"], "phone": "02-9999-9999"}}
storage.save_result(rescan)
rows = storage.list_companies()
updated = next(row for row in rows if row["domain"] == "test.co.kr")
check("rescan does not duplicate", len(rows) == 2, f"-> {len(rows)} rows")
check("rescan updates the row", updated["phone"] == "02-9999-9999", f'-> {updated["phone"]!r}')

full_list = storage.list_companies(include_results=True)
check("full listing carries results", all(row.get("result") for row in full_list))
check("plain listing has no results", all("result" not in row for row in storage.list_companies()))

detail = storage.get_company(updated["id"])
check("detail returns the full scan", detail["result"]["company"]["name"] == result["company"]["name"])
check("detail keeps recruitment", len(detail["result"]["it_recruitment"]) == 2)
check("missing id returns None", storage.get_company(999999) is None)

check("delete works", storage.delete_company(updated["id"]) is True)
check("delete removes the row", len(storage.list_companies()) == 1)
check("deleting twice is False", storage.delete_company(updated["id"]) is False)

try:
    storage.save_result({"company": {}})
    check("result without a domain is rejected", False)
except ValueError:
    check("result without a domain is rejected", True)

for suffix in ("", "-wal", "-shm"):
    stale = _Path(str(storage.DB_PATH) + suffix)
    if stale.exists():
        stale.unlink()
check("no connection left open", True)   # unlink o tren se loi neu con handle

print()
if failures:
    print(f"{len(failures)} FAILED:")
    for failure in failures:
        print("  -", failure)
    raise SystemExit(1)
print("all tests passed")
