"""Extract sales-useful facts from crawled pages.

Everything returned here must come from the crawled HTML of the target domain
(spec sections 3, 4, 9, 10, 11, 14). No outside knowledge, no defaults, no
sample data: when the evidence is missing the field stays None and the frontend
renders "Not found".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from .crawler import CrawlResult, Page, clean_link, footer_text, same_company_domain

NOT_FOUND = None

# -- Company name -----------------------------------------------------------

GENERIC_TITLE_WORDS = {
    "home", "index", "main", "welcome", "untitled", "홈", "메인", "인덱스",
    "홈페이지", "환영합니다", "company", "website", "site", "관리자", "담당자",
    "운영자", "admin", "administrator", "게시판", "공지사항", "회사소개", "인사말",
}

NAME_LABELS = (
    "상호명", "상호", "회사명", "법인명", "업체명", "기업명", "회사 이름",
    "company name", "corporate name",
)

COMPANY_SUFFIXES = ("주식회사", "(주)", "㈜", "유한회사", "co., ltd", "co.,ltd", "inc.", "corp.", "ltd.")

# -- Contact ----------------------------------------------------------------

ADDRESS_LABELS = ("주소", "소재지", "본사", "본사주소", "오시는길", "address", "addr", "location")

HQ_MARKERS = ("본사", "본점", "head office", "headquarters", "본사주소")

KOREAN_REGIONS = (
    "서울특별시", "서울시", "서울", "부산광역시", "부산", "대구광역시", "대구",
    "인천광역시", "인천", "광주광역시", "광주", "대전광역시", "대전", "울산광역시", "울산",
    "세종특별자치시", "세종", "경기도", "강원특별자치도", "강원도", "충청북도", "충북",
    "충청남도", "충남", "전라북도", "전북특별자치도", "전북", "전라남도", "전남",
    "경상북도", "경북", "경상남도", "경남", "제주특별자치도", "제주도", "제주",
)

ADDRESS_RE = re.compile(
    r"(?:" + "|".join(KOREAN_REGIONS) + r")\s?[^\n<>|]{0,60}?"
    r"(?:로|길|대로|번길)\s?[\d-]{1,10}[^\n<>|]{0,50}"
)

# Dia chi Han viet romaja: "6 Jeongjail-ro 156beon-gil, Bundang-gu, Seongnam-si".
# Cac hau to hanh chinh (-ro/-gil/-gu/-si/-do) la dau hieu chac chan.
KOREAN_ROMAJA_ADDRESS_RE = re.compile(
    r"[\dA-Za-z][^\n<>|]{0,80}?(?:-ro|-gil|-daero)\b[^\n<>|]{0,60}?"
    r"(?:-gu|-si|-gun|-do)\b[^\n<>|©ⓒ]{0,60}",
    re.I,
)

# Chi nhan dia chi tieng Anh khi no thuoc Han Quoc - website cong ty Han hay
# liet ke ca van phong nuoc ngoai hoac dia chi cua doi tac.
KOREA_HINTS = (
    "korea", "seoul", "gyeonggi", "seongnam", "incheon", "busan", "daegu",
    "daejeon", "gwangju", "ulsan", "pangyo", "bundang", "sejong", "jeju",
    "gangnam", "songdo", "suwon", "yongin",
)

ENGLISH_ADDRESS_RE = re.compile(
    r"\d{1,5}[^\n<>|,]{0,40},\s?[^\n<>|,]{0,40}"
    r"(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Boulevard|Blvd\.|Tower|Building|Bldg\.)"
    r"[^\n<>|]{0,60}",
    re.I,
)

PHONE_LABELS = ("대표전화", "대표번호", "전화번호", "전화", "연락처", "tel", "phone", "t.")

# 전자상거래법 buộc website Hàn ghi 사업자등록번호 và 대표자 ở footer, nên hai
# trường này gần như luôn có và luôn nằm trong footer.
BIZ_NUMBER_LABELS = ("사업자등록번호", "사업자 등록번호", "사업자등록 번호", "사업자번호",
                     "business registration number", "business registration no", "business license")
BIZ_NUMBER_RE = re.compile(r"(\d{3})\s*-?\s*(\d{2})\s*-?\s*(\d{5})(?!\d)")
CEO_LABELS = ("대표이사", "대표자", "대표자명", "대표", "ceo", "representative")
# Chức danh phụ đứng sau 대표이사: "대표이사 사장 홍길동", "대표이사 부회장 홍길동".
SECONDARY_TITLE_RE = r"(?:\s*(?:사장|부사장|회장|부회장|전무|상무|이사))?"
FAX_LABELS = ("팩스", "fax", "f.")

# The lookarounds matter: without them a run of years ("2010 2019 2000")
# reads as a phone number.
_AREA_CODE = r"(?:2|[3-6][1-5]|70|80|10|505)"

PHONE_RE = re.compile(
    r"(?<![\d\-])(?:"
    # Dạng quốc tế bỏ số 0 đầu: +82-2-564-8525
    rf"\+?82[-\s.]?{_AREA_CODE}[-\s.)]{{1,3}}\d{{3,4}}[-\s.]{{1,3}}\d{{4}}"
    # Dạng nội địa: 02-564-8525
    rf"|0{_AREA_CODE}[-\s.)]{{1,3}}\d{{3,4}}[-\s.]{{1,3}}\d{{4}}"
    # Đầu số dịch vụ: 1588-1234
    r"|1[5-9]\d{2}[-\s.]?\d{4}"
    r")(?![\d\-])"
)

EMAIL_LABELS = ("이메일", "메일", "전자우편", "문의메일", "e-mail", "email", "mail")

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

CF_EMAIL_HREF_RE = re.compile(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)")

# Rác thường gặp: ảnh, địa chỉ mẫu của theme, hộp thư không nhận thư.
EMAIL_JUNK = (
    "noreply", "no-reply", "donotreply", "example.com", "example.org", "domain.com",
    "yourdomain", "yoursite", "email.com", "sentry.io", "wixpress.com", "godaddy",
    "sentry-next", "wordpress", "@2x", "@3x",
)
EMAIL_JUNK_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css")

# Hộp thư chung của công ty - hữu ích cho sales hơn thư cá nhân.
EMAIL_ROLE_PREFIXES = (
    "info", "contact", "sales", "help", "support", "master", "admin", "cs",
    "mail", "biz", "business", "office", "hello", "inquiry", "webmaster", "recruit",
)

# Nhiều công ty Hàn nhỏ dùng mail miễn phí; vẫn nhận nhưng ưu tiên thấp hơn.
FREE_MAIL_DOMAINS = ("gmail.com", "naver.com", "daum.net", "hanmail.net", "nate.com", "outlook.com", "hotmail.com", "yahoo.com")

INDUSTRY_LABELS = (
    "업종", "업태", "사업분야", "사업영역", "주요사업", "주요 사업", "사업내용", "종목",
    "industry", "business area", "business type", "main business",
)

INDUSTRY_KEYWORDS = (
    "소프트웨어", "시스템통합", "시스템 통합", "정보통신", "IT 서비스", "IT서비스",
    "솔루션", "플랫폼", "반도체", "전자부품", "제조", "바이오", "헬스케어", "게임",
    "콘텐츠", "물류", "건설", "화학", "금융", "교육", "이커머스", "전자상거래",
    "클라우드", "인공지능", "데이터", "보안", "네트워크", "자동차", "에너지",
    "software", "system integration", "manufacturing", "semiconductor", "biotech",
    "healthcare", "logistics", "e-commerce", "cloud", "security", "consulting",
)

# -- Key contacts (spec section 3) ------------------------------------------

# Lower index = higher priority.
CONTACT_TITLE_PRIORITY: list[tuple[str, tuple[str, ...]]] = [
    ("CTO", ("cto", "최고기술책임자", "기술총괄", "기술이사", "기술담당임원")),
    ("CIO", ("cio", "최고정보책임자", "정보화책임자")),
    ("IT 책임자", ("it 책임자", "it책임자", "it본부장", "it 본부장", "정보시스템본부장", "전산실장", "전산팀장")),
    ("개발 책임자", ("개발책임자", "개발 책임자", "개발총괄", "cpo", "최고제품책임자", "연구소장", "cto/연구소장")),
    ("개발본부장", ("개발본부장", "기술본부장", "r&d본부장", "연구개발본부장")),
    ("개발팀장", ("개발팀장", "개발실장", "기술팀장", "소프트웨어팀장")),
    ("IT Director", ("it director", "director of it", "engineering director", "head of engineering",
                     "vp of engineering", "head of development", "technical director")),
    ("CEO", ("대표이사", "대표자", "ceo", "chief executive officer", "대표", "사장", "회장", "founder", "창업자")),
]

# Roles we do not want unless the same person is also IT or CEO (spec section 3).
EXCLUDED_TITLE_TOKENS = (
    "cfo", "cmo", "chro", "인사", "회계", "총무", "재무", "영업", "마케팅", "홍보",
    "구매", "생산", "품질", "법무", "감사", "hr", "sales", "marketing", "finance",
    "accounting", "legal", "procurement",
)

# Ten Han: cho phep khoang trang giua cac am tiet vi nhieu site viet "박 한".
# Do dai va tinh hop le duoc kiem tra ky trong _plausible_name().
KOREAN_NAME_RE = r"[가-힣](?: ?[가-힣]){1,3}"

# Ho kep - dieu kien duy nhat de mot ten dai 4 am tiet la ten nguoi that.
KOREAN_COMPOUND_SURNAMES = (
    "남궁", "황보", "제갈", "사공", "선우", "서문", "독고", "동방", "망절", "강전",
)

# A Korean personal name starts with a family name. Without this check any
# 2-4 syllable noun ("플랫폼", "솔루션") next to "대표" reads as a person.
KOREAN_SURNAMES = (
    "김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구"
    "라마민진지엄채원천방공현함변염여추도소석선설길위표명기반왕금옥육인맹제모탁국"
    "봉피간연온사시어옹빈경육사"
)
ENGLISH_NAME_RE = r"[A-Z][a-z]{1,15}(?:\s[A-Z][a-z]{1,15}){1,2}"

NAME_STOPWORDS = {
    "대표이사", "대표자", "경영진", "임원진", "조직도", "회사소개", "본부장", "사업부",
    "이사회", "주식회사", "고객센터", "채용정보", "개인정보", "이용약관", "사업자",
    "홈페이지", "바로가기", "더보기", "전체보기", "회사명", "상호명", "기업", "국가",
    "한국", "이사", "회사", "사업", "고객", "기술", "정보", "시스템", "지원", "문의",
    "우리", "전체", "신규", "본사", "지사", "센터", "연구", "제품", "서비스",
    "인사말", "관리자", "담당자", "운영자", "연혁", "조직", "경영", "채용", "문의",
    # Form/table field labels sit right next to the value they describe.
    "이메일", "메일", "전화", "팩스", "주소", "연락처", "번호", "등록", "상호",
    "성명", "이름", "부서", "직위", "직책", "구분", "내용", "제목", "날짜",
    "변경", "안내", "공지", "확인", "선택", "이전", "다음", "목록",
}

# Titles loose enough to appear inside ordinary prose ("국가대표", "한국 대표").
LOOSE_TITLE_TOKENS = ("대표", "사장", "회장", "founder")

# Menu labels that fit the "Firstname Lastname" shape.
ENGLISH_NAME_STOPWORDS = {
    "about us", "contact us", "our team", "our company", "who we are", "what we do",
    "privacy policy", "terms of use", "site map", "read more", "learn more",
    "view more", "head office", "customer service", "business area", "main business",
    "key contacts", "company info", "company profile", "corporate governance",
    "board of directors", "investor relations", "press release", "news room",
}

# Role nouns that start a false "name" ("이사가 대표" from "...등기이사가 대표...").
ROLE_NOUN_PREFIXES = {
    "이사", "사장", "대표", "부장", "팀장", "본부", "상무", "전무", "감사", "회장",
    "실장", "과장", "차장", "주임", "사원", "직원", "고객", "회사", "기업", "임원",
    "인사", "소개", "사업", "조직", "경영", "관리", "담당", "운영", "개인",
}

# -- IT recruitment (spec section 4) ----------------------------------------

IT_JOB_KEYWORDS = (
    "개발자", "개발", "소프트웨어", "백엔드", "프론트엔드", "풀스택", "웹개발", "웹 개발",
    "앱개발", "앱 개발", "모바일", "안드로이드", "ios", "서버", "시스템", "인프라",
    "ai", "인공지능", "머신러닝", "딥러닝", "데이터", "빅데이터", "클라우드", "devops",
    "데브옵스", "qa", "테스트", "품질보증", "pm", "po", "프로덕트", "퍼블리셔",
    "engineer", "developer", "backend", "back-end", "frontend", "front-end", "fullstack",
    "full-stack", "software", "programmer", "architect", "sre", "machine learning",
    "data scientist", "data engineer", "cloud", "security engineer", "qa engineer",
    "product manager", "product owner", "tech lead",
)

NON_IT_JOB_KEYWORDS = (
    "영업", "마케팅", "회계", "인사", "총무", "생산", "물류", "고객상담", "상담원",
    "경리", "재무", "구매", "홍보", "디자인 인턴", "매장", "판매", "배송", "운전",
    "시공", "설비", "안전관리", "간호", "요양",
    "sales", "marketing", "accounting", "hr ", "recruiter", "logistics", "driver",
)

EMPLOYMENT_TYPES = (
    ("정규직", "정규직"), ("계약직", "계약직"), ("인턴", "인턴"), ("파견직", "파견직"),
    ("프리랜서", "프리랜서"), ("아르바이트", "아르바이트"), ("병역특례", "병역특례"),
    ("full-time", "Full-time"), ("part-time", "Part-time"), ("contract", "Contract"),
    ("intern", "Intern"), ("freelance", "Freelance"),
)

LOCATION_HINTS = (
    "서울", "경기", "판교", "성남", "부산", "인천", "대구", "대전", "광주", "울산",
    "세종", "수원", "안양", "고양", "용인", "화성", "천안", "청주", "제주", "원격",
    "재택", "remote", "seoul", "pangyo", "busan", "incheon",
)

DEADLINE_RE = re.compile(
    r"(?:마감\s*[:：]?\s*)?(?:\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}(?:\s*까지)?"
    r"|\d{1,2}[.\-/]\d{1,2}\s*까지|상시\s?채용|채용\s?시\s?마감|수시\s?채용|D-\d{1,3})"
)

# A whole menu scraped into one string looks like: several of these at once.
NAV_TOKENS = (
    "회사소개", "연혁", "제품", "고객", "사업", "조직", "인증", "수상", "홍보", "문의",
    "오시는길", "이용약관", "개인정보", "지속가능경영", "사이트맵",
    "about", "company", "contact", "sitemap", "home", "products", "solutions",
)

# A real posting says so: it names a role or announces a hiring round.
JOB_ROLE_MARKERS = (
    "모집", "채용", "공고", "구인", "경력", "신입", "인턴", "지원하기", "입사",
    "개발자", "엔지니어", "연구원", "매니저", "리드", "책임", "선임", "주임",
    "developer", "engineer", "manager", "architect", "specialist", "lead",
    "intern", "hiring", "position", "recruit", "analyst", "scientist", "administrator",
)

# Korean footers run "address Tel. ... Fax. ..." together on one line.
ADDRESS_TAIL_RE = re.compile(
    r"\s*(?:tel\b|fax\b|e-?mail\b|get directions|copyright|all rights|©|ⓒ|"
    r"전화|대표전화|팩스|이메일|메일|사업자|대표자|통신판매|고객센터).*$",
    re.I,
)

MAX_CONTACTS = 3
MAX_JOBS = 10


@dataclass
class Evidence:
    value: str
    source_url: str


def _clean(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value.replace("\xa0", " "))
    return value.strip(" \t\r\n·|/-–—:：,")


def _label_value(text: str, labels: tuple[str, ...], max_len: int = 120) -> str | None:
    """Find `label : value` in page text (Korean sites put these in footers)."""
    for label in labels:
        pattern = re.compile(
            re.escape(label) + r"\s*[:：]\s*([^\n|·••]{2," + str(max_len) + r"})",
            re.I,
        )
        match = pattern.search(text)
        if match:
            value = _clean(match.group(1))
            if value:
                return value
    return None


def _page_priority(pages: list[Page], categories: tuple[str, ...]) -> list[Page]:
    """Order pages so the most authoritative category is inspected first."""
    ordered: list[Page] = []
    seen: set[int] = set()   # by identity: comparing Page values would diff whole documents
    for category in categories:
        for page in pages:
            if page.category == category and id(page) not in seen:
                seen.add(id(page))
                ordered.append(page)
    ordered.extend(page for page in pages if id(page) not in seen)
    return ordered


def _text_sources(crawl: CrawlResult, categories: tuple[str, ...]) -> list[tuple[str, str]]:
    """(text, source_url) - footer của các trang trước, rồi mới tới toàn trang.

    Footer là nơi công ty Hàn đặt 상호 / 주소 / 전화 / 이메일 và gần như luôn
    chính xác hơn text rải rác trong thân trang (địa chỉ chi nhánh, số của
    đối tác trong bản tin...).
    """
    ordered = _page_priority(crawl.pages, categories)
    sources = [(footer_text(page), page.final_url) for page in ordered]
    sources += [(page.text, page.final_url) for page in ordered]
    return [(text, url) for text, url in sources if text]


# -- Company ---------------------------------------------------------------


def _title_candidate(page: Page) -> str | None:
    title = _clean(page.title)
    if not title:
        return None
    # "회사명 | 소개" -> "회사명"
    parts = re.split(r"\s*[|·・\-–—:]\s*", title)
    parts = [p for p in (_clean(p) for p in parts) if p]
    if not parts:
        return None
    candidate = max(parts[:2], key=len) if len(parts) > 1 else parts[0]
    if len(candidate) < 2 or len(candidate) > 60:
        return None
    if candidate.lower() in GENERIC_TITLE_WORDS:
        return None
    return candidate


ORGANIZATION_TYPES = {"organization", "corporation", "localbusiness", "ngo", "educationalorganization"}


def _organization_names(raw: str) -> list[str]:
    """Tên của đúng các đối tượng @type Organization trong JSON-LD.

    Blog WordPress đặt author (Person) và publisher (Organization) chung một
    @graph; đọc bằng regex sẽ lấy nhầm tên tác giả bài viết làm tên công ty.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    names: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            if any(isinstance(t, str) and t.lower() in ORGANIZATION_TYPES for t in types):
                name = node.get("name") or node.get("legalName")
                if isinstance(name, str):
                    names.append(name)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return names


def extract_company(crawl: CrawlResult) -> dict:
    """Multi-signal company identity check (spec section 11)."""
    pages = _page_priority(crawl.pages, ("home", "company", "contact"))
    candidates: dict[str, tuple[int, str]] = {}   # name -> (score, source)

    def add(name: str | None, score: int, source: str) -> None:
        name = _clean(name)
        if not name or len(name) < 2 or len(name) > 60:
            return
        if name.lower() in GENERIC_TITLE_WORDS:
            return
        if re.fullmatch(r"[\d\s.,\-]+", name):
            return
        previous = candidates.get(name)
        if previous is None or score > previous[0]:
            candidates[name] = (score, source)

    for page in pages:
        soup = page.soup
        source = page.final_url

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text() or ""
            for name in _organization_names(raw):
                add(name, 6, source)

        meta_site = soup.find("meta", attrs={"property": "og:site_name"})
        if meta_site:
            add(meta_site.get("content"), 5, source)

        add(_label_value(page.text, NAME_LABELS, 60), 6, source)

        copyright_match = re.search(
            r"(?:©|ⓒ|copyright|copyrights)\s*(?:\(c\)\s*)?(?:\d{4}\s*(?:-\s*\d{4})?\s*)?"
            r"(?:by\s+)?([^\n.|©ⓒ]{2,60})",
            page.text,
            re.I,
        )
        if copyright_match:
            value = _clean(copyright_match.group(1))
            value = re.sub(r"\b(all rights reserved|무단전재.*|. all right.*)$", "", value, flags=re.I)
            value = _clean(value)
            if value and not value.lower().startswith(("20", "19")):
                add(value, 4, source)

        if page.category in ("home", "company"):
            add(_title_candidate(page), 3, source)

    if not candidates:
        return {"name": NOT_FOUND, "name_source": NOT_FOUND}

    def rank(item: tuple[str, tuple[int, str]]) -> tuple:
        name, (score, _source) = item
        bonus = 2 if any(s in name.lower() for s in COMPANY_SUFFIXES) else 0
        # A name echoing the domain label is strong evidence it is really theirs.
        label = crawl.base_domain.split(".")[0]
        if label and label.lower() in re.sub(r"[^a-z0-9]", "", name.lower()):
            bonus += 2
        return (score + bonus, -len(name))

    best_name, (_score, best_source) = max(candidates.items(), key=rank)
    return {"name": best_name, "name_source": best_source}


def _in_korea(value: str) -> bool:
    lowered = value.lower()
    return any(hint in lowered for hint in KOREA_HINTS)


def _place_key(address: str) -> str:
    """Khoá nhận diện "cùng một nơi".

    "서울 강남구 논현로 34" và "서울특별시 강남구 논현로 34, 썬테크빌딩 5층" là
    một địa chỉ viết hai kiểu, nên phải bỏ hậu tố hành chính trước khi so.
    """
    compact = re.sub(r"\s+", "", address.lower())
    compact = re.sub(r"(특별자치시|특별자치도|특별시|광역시)", "", compact)
    return compact[:8]


def extract_address(crawl: CrawlResult) -> Evidence | None:
    """Địa chỉ trụ sở.

    Thứ tự ưu tiên quan trọng hơn thứ tự trang: địa chỉ tiếng Hàn thắng địa chỉ
    romaja, romaja thắng địa chỉ tiếng Anh chung. Website công ty Hàn hay liệt kê
    cả văn phòng nước ngoài — không xếp hạng thì một địa chỉ ở nước khác trên
    trang tuyển dụng có thể thắng địa chỉ trụ sở nằm ở footer trang chủ.
    """
    sources = _text_sources(crawl, ("contact", "company", "home"))
    tiers = (
        (ADDRESS_RE, False),                   # tiếng Hàn
        (KOREAN_ROMAJA_ADDRESS_RE, False),     # romaja: Jeongjail-ro, Bundang-gu
        (ENGLISH_ADDRESS_RE, True),            # tiếng Anh: bắt buộc thuộc Hàn Quốc
    )

    for pattern, require_korea in tiers:
        found: list[tuple[str, str]] = []   # (địa chỉ, nguồn), theo thứ tự ưu tiên nguồn

        for text, source_url in sources:
            labelled = _label_value(text, ADDRESS_LABELS, 140)
            if labelled:
                match = pattern.search(labelled)
                value = _clean(ADDRESS_TAIL_RE.sub("", _clean(match.group(0)) if match else labelled))
                if len(value) >= 10 and (match or pattern is ADDRESS_RE):
                    if not require_korea or _in_korea(value):
                        found.append((value, source_url))

            # Một trang có thể chứa nhiều địa chỉ (khối bản đồ, footer, chi nhánh).
            for m in pattern.finditer(text):
                value = _clean(ADDRESS_TAIL_RE.sub("", _clean(m.group(0))))
                if len(value) >= 10 and (not require_korea or _in_korea(value)):
                    found.append((value, source_url))

        if not found:
            continue

        # Trụ sở chính trước: chi nhánh liệt kê phía dưới không phải thứ sales cần.
        headquarters = next((item for item in found if any(h in item[0] for h in HQ_MARKERS)), None)
        if headquarters:
            return Evidence(headquarters[0][:160], headquarters[1])

        # Cùng một địa chỉ hay xuất hiện nhiều lần với độ chi tiết khác nhau
        # ("...논현로 34" ở footer, "...논현로 34, 썬테크빌딩 5층" ở trang giới
        # thiệu). Lấy bản đầy đủ nhất, nhưng chỉ trong nhóm cùng nơi với kết quả
        # đầu tiên — để không nhảy sang chi nhánh ở thành phố khác.
        key = _place_key(found[0][0])
        same_place = [item for item in found if _place_key(item[0]) == key]
        best = max(same_place, key=lambda item: len(item[0]))
        return Evidence(best[0][:160], best[1])
    return None


# "1997-2019" khop dang so dich vu 1[5-9]xx-xxxx nhung that ra la khoang nam.
YEAR_RANGE_RE = re.compile(r"^(?:19|20)\d{2}\s*[-~.\s]\s*(?:19|20)\d{2}$")


def _normalize_phone(raw: str) -> str:
    if YEAR_RANGE_RE.match(raw.strip()):
        return ""
    digits = re.sub(r"[^\d+]", "", raw)
    digits = re.sub(r"^\+?82", "0", digits)
    if len(digits) < 8 or len(digits) > 12:
        return ""
    if digits.startswith("02") and len(digits) in (9, 10):
        return f"{digits[:2]}-{digits[2:-4]}-{digits[-4:]}"
    if re.match(r"^1[5-9]\d{2}", digits) and len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    if len(digits) in (10, 11):
        return f"{digits[:3]}-{digits[3:-4]}-{digits[-4:]}"
    return digits


def extract_phone(crawl: CrawlResult) -> Evidence | None:
    for text, source_url in _text_sources(crawl, ("contact", "company", "home")):
        for label in PHONE_LABELS:
            pattern = re.compile(re.escape(label) + r"\s*[:：]?\s*(" + PHONE_RE.pattern + r")", re.I)
            for match in pattern.finditer(text):
                window = text[max(0, match.start() - 12):match.start()].lower()
                if any(fax in window for fax in FAX_LABELS):
                    continue
                phone = _normalize_phone(match.group(1))
                if phone:
                    return Evidence(phone, source_url)
        unlabelled: list[str] = []
        for match in PHONE_RE.finditer(text):
            window = text[max(0, match.start() - 12):match.start()].lower()
            if any(fax in window for fax in FAX_LABELS):
                continue
            phone = _normalize_phone(match.group(0))
            if phone:
                unlabelled.append(phone)
        if unlabelled:
            landline = next((p for p in unlabelled if not p.startswith("010")), None)
            return Evidence(landline or unlabelled[0], source_url)
    return None


def extract_biz_number(crawl: CrawlResult) -> Evidence | None:
    """사업자등록번호 000-00-00000 sau nhãn, footer trước."""
    for text, source_url in _text_sources(crawl, ("contact", "company", "home")):
        for label in BIZ_NUMBER_LABELS:
            pattern = re.compile(re.escape(label) + r"\s*[:：]?\s*(?:\[\s*)?" + BIZ_NUMBER_RE.pattern, re.I)
            match = pattern.search(text)
            if match:
                return Evidence(f"{match.group(1)}-{match.group(2)}-{match.group(3)}", source_url)
    return None


def extract_ceo(crawl: CrawlResult) -> Evidence | None:
    """대표자 ghi sau nhãn (대표 : 홍길동) trong footer / trang công ty.

    Khác với key contacts (đọc thân trang, cần dòng ngắn), ở đây chỉ nhận
    dạng có dấu hai chấm hoặc nhãn 대표자/대표이사 đứng ngay trước tên, vì footer
    thường là một dòng dài "상호 : A | 대표 : B | 사업자등록번호 : C".
    """
    name_alternation = f"(?:{KOREAN_NAME_RE}|{ENGLISH_NAME_RE})"
    for text, source_url in _text_sources(crawl, ("contact", "company", "home")):
        for label in CEO_LABELS:
            needs_colon = label in ("대표", "ceo")
            separator = r"\s*[:：]\s*" if needs_colon else SECONDARY_TITLE_RE + r"\s*[:：]?\s*"
            pattern = re.compile(
                r"(?<![가-힣A-Za-z])" + re.escape(label) + separator + rf"(?P<name>{name_alternation})(?![가-힣])",
                re.I,
            )
            for match in pattern.finditer(text):
                name = match.group("name").strip()
                if _plausible_name(name):
                    return Evidence(_display_name(name), source_url)
    return None


def decode_cf_email(encoded: str) -> str | None:
    """Giải mã email bị Cloudflare Email Protection che.

    Rất nhiều site Hàn đặt sau Cloudflare: email vẫn hiển thị công khai cho mọi
    khách truy cập, nhưng trong HTML chỉ còn `data-cfemail="<hex>"` và chuỗi
    "[email protected]" - trình duyệt giải mã bằng JS. Byte đầu là khoá XOR.
    """
    encoded = (encoded or "").strip()
    if len(encoded) < 4 or len(encoded) % 2:
        return None
    try:
        data = bytes.fromhex(encoded)
    except ValueError:
        return None
    key = data[0]
    try:
        return "".join(chr(byte ^ key) for byte in data[1:])
    except ValueError:
        return None


def _email_is_usable(email: str) -> bool:
    lowered = email.lower()
    if len(lowered) > 100 or lowered.count("@") != 1:
        return False
    if any(junk in lowered for junk in EMAIL_JUNK):
        return False
    if lowered.endswith(EMAIL_JUNK_SUFFIXES):
        return False
    local, _, domain = lowered.partition("@")
    if not local or "." not in domain:
        return False
    # Chuỗi dính liền từ JS/CSS đã minify thường rất dài và không có dấu chấm hợp lệ.
    return len(local) <= 64 and all(part for part in domain.split("."))


def _email_belongs_to_company(email: str, base_domain: str) -> bool:
    """Email phải thuộc domain công ty, hoặc là hộp thư miễn phí.

    Trang tin/PR trên website công ty hay kèm email nhà báo ở domain khác
    (vd nwngm@aitimes.kr) - đó là người của công ty khác, không được lấy.
    """
    domain = email.lower().partition("@")[2]
    if not domain:
        return False
    if base_domain and (domain == base_domain or domain.endswith("." + base_domain)):
        return True
    return domain in FREE_MAIL_DOMAINS


def _email_score(email: str, base_domain: str, from_mailto: bool, labelled: bool) -> int:
    lowered = email.lower()
    local, _, domain = lowered.partition("@")
    score = 0
    if from_mailto:
        score += 5
    if labelled:
        score += 4
    if base_domain and (domain == base_domain or domain.endswith("." + base_domain)):
        score += 3
    if any(local == prefix or local.startswith(prefix) for prefix in EMAIL_ROLE_PREFIXES):
        score += 2
    if domain in FREE_MAIL_DOMAINS:
        score -= 2
    return score


def extract_email(crawl: CrawlResult) -> Evidence | None:
    """Email liên hệ của công ty, ưu tiên link mailto và hộp thư cùng domain."""
    best: tuple[int, str, str] | None = None   # (score, email, source)

    def offer(email: str, page: Page, from_mailto: bool = False, labelled: bool = False) -> None:
        nonlocal best
        email = _clean(email).strip("<>()[],;:")
        if not _email_is_usable(email) or not _email_belongs_to_company(email, crawl.base_domain):
            return
        score = _email_score(email, crawl.base_domain, from_mailto, labelled)
        # Trang liên hệ đáng tin hơn trang khác.
        score += {"contact": 3, "company": 2, "home": 1}.get(page.category, 0)
        if best is None or score > best[0]:
            best = (score, email, page.final_url)

    for page in _page_priority(crawl.pages, ("contact", "company", "home")):
        # Email bị Cloudflare che: <span data-cfemail="..."> hoặc link
        # /cdn-cgi/l/email-protection#<hex>.
        for node in page.soup.find_all(attrs={"data-cfemail": True}):
            decoded = decode_cf_email(node.get("data-cfemail"))
            if decoded:
                offer(decoded, page, from_mailto=True)

        for anchor in page.soup.find_all("a", href=True):
            href = (anchor.get("href") or "").strip()
            if href.lower().startswith("mailto:"):
                offer(href[7:].split("?")[0], page, from_mailto=True)
                continue
            protected = CF_EMAIL_HREF_RE.search(href)
            if protected:
                decoded = decode_cf_email(protected.group(1))
                if decoded:
                    offer(decoded, page, from_mailto=True)

        labelled_value = _label_value(page.text, EMAIL_LABELS, 80)
        if labelled_value:
            match = EMAIL_RE.search(labelled_value)
            if match:
                offer(match.group(0), page, labelled=True)

        # Chỉ quét trong text hiển thị, không quét HTML thô, để tránh chuỗi trong JS.
        for match in EMAIL_RE.finditer(page.text):
            offer(match.group(0), page)

    if best is None:
        return None
    return Evidence(best[1], best[2])


EMAIL_IMAGE_RE = re.compile(
    r"<img[^>]+(?:alt|src|class|id)\s*=\s*[\"'][^\"']*(?:e-?mail|메일|이메일)[^\"']*[\"']", re.I
)
CONTACT_FORM_RE = re.compile(
    r"<form[^>]*>(?:(?!</form>).)*?<(?:input|textarea)[^>]+(?:type=[\"']email[\"']|name=[\"'][^\"']*(?:mail|email|contact|inquiry|message|content)[^\"']*[\"'])",
    re.I | re.S,
)


def email_hint(crawl: CrawlResult) -> dict | None:
    """Vì sao không có email — để người dùng biết phải làm gì tiếp thay vì
    chỉ thấy "찾을 수 없음".

    image: email được vẽ thành ảnh (chống thu thập tự động) -> mở nguồn đọc bằng mắt.
    form : website chỉ có mẫu 문의하기, không đăng địa chỉ email nào.
    """
    for page in _page_priority(crawl.pages, ("contact", "company", "home")):
        if EMAIL_IMAGE_RE.search(page.html or ""):
            return {"type": "image", "url": page.final_url}
    for page in _page_priority(crawl.pages, ("contact", "home", "company")):
        if CONTACT_FORM_RE.search(page.html or ""):
            return {"type": "form", "url": page.final_url}
    return None


def extract_industry(crawl: CrawlResult) -> Evidence | None:
    for page in _page_priority(crawl.pages, ("company", "home", "contact")):
        labelled = _label_value(page.text, INDUSTRY_LABELS, 60)
        if labelled and len(labelled) >= 2:
            return Evidence(labelled[:80], page.final_url)

    for page in _page_priority(crawl.pages, ("company", "home")):
        meta = page.soup.find("meta", attrs={"name": "description"}) or page.soup.find(
            "meta", attrs={"property": "og:description"}
        )
        description = _clean(meta.get("content")) if meta else ""
        headings = " ".join(
            _clean(h.get_text(" ", strip=True))
            for h in page.soup.find_all(["h1", "h2", "h3"])[:12]
        )
        # Only the headline area: deeper body text describes customers' industries,
        # not the company's own.
        haystack = f"{description} {page.title} {headings} {page.text[:800]}"
        found = [kw for kw in INDUSTRY_KEYWORDS if _keyword_in(kw.lower(), haystack.lower())]
        if found:
            unique: list[str] = []
            for keyword in found:
                if not any(keyword.lower() in other.lower() and keyword != other for other in found):
                    if keyword not in unique:
                        unique.append(keyword)
            return Evidence(", ".join(unique[:2]), page.final_url)
    return None


# -- Key contacts ----------------------------------------------------------


def _token_regex(token: str) -> re.Pattern:
    """Match a title token as a whole word.

    Without this, "Director" contains "cto" and every director becomes a CTO.
    """
    escaped = re.escape(token)
    if token.isascii():
        return re.compile(rf"\b{escaped}\b", re.I)
    return re.compile(rf"(?<![가-힣]){escaped}(?![가-힣])", re.I)


TITLE_TOKEN_PATTERNS = [
    (index, label, _token_regex(token))
    for index, (label, tokens) in enumerate(CONTACT_TITLE_PRIORITY)
    for token in tokens
]


def _title_rank(title_text: str) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for index, label, pattern in TITLE_TOKEN_PATTERNS:
        if pattern.search(title_text) and (best is None or index < best[0]):
            best = (index, label)
    return best


def _is_excluded_role(title_text: str) -> bool:
    lowered = title_text.lower()
    if not any(token in lowered for token in EXCLUDED_TITLE_TOKENS):
        return False
    # Keep it when the same person is also IT leadership or the CEO.
    rank = _title_rank(title_text)
    return rank is None


def _plausible_name(name: str) -> bool:
    name = name.strip()
    if not name or name in NAME_STOPWORDS:
        return False
    if re.fullmatch(KOREAN_NAME_RE, name):
        compact = re.sub(r"\s+", "", name)
        if compact in NAME_STOPWORDS or compact[0] not in KOREAN_SURNAMES:
            return False
        if compact[:2] in ROLE_NOUN_PREFIXES:
            return False
        if len(compact) == 4 and compact[:2] not in KOREAN_COMPOUND_SURNAMES:
            return False   # "공지사항", "인재채용"... khong phai ten nguoi
        if len(compact) == 2 and name == compact:
            return False   # ten 2 am tiet viet lien thuong la danh tu ("변경")
        return not any(stop in compact for stop in ("주식", "회사", "본부", "센터", "그룹"))
    if re.fullmatch(ENGLISH_NAME_RE, name):
        return name.lower() not in ENGLISH_NAME_STOPWORDS
    return False


def _display_name(name: str) -> str:
    """Tên Hàn viết cách trong chữ ký ("현 신 균") -> dạng thường dùng "현신균"."""
    if re.fullmatch(KOREAN_NAME_RE, name):
        return re.sub(r"\s+", "", name)
    return re.sub(r"\s+", " ", name).strip()


def extract_key_contacts(crawl: CrawlResult, company_name: str | None = None) -> list[dict]:
    """At most 3 IT/decision-maker contacts, each with a source URL."""
    found: dict[str, tuple[int, str, str, str]] = {}  # name -> (rank, name, position, source)

    banned = {crawl.base_domain.split(".")[0].lower()}
    if company_name:
        banned.update(part.lower() for part in re.split(r"[\s(),.]+", company_name) if len(part) >= 2)
    # "(주)유라클 대표이사" would otherwise read as a person called 유라클.
    for page in crawl.pages:
        for alias in re.findall(r"(?:\(주\)|㈜|주식회사)\s*([가-힣]{2,10})", page.text):
            banned.add(alias.lower())

    title_tokens = [token for _label, tokens in CONTACT_TITLE_PRIORITY for token in tokens]
    title_alternation = "|".join(
        (rf"\b{re.escape(t)}\b" if t.isascii() else re.escape(t))
        for t in sorted(title_tokens, key=len, reverse=True)
    )
    name_alternation = f"(?:{KOREAN_NAME_RE}|{ENGLISH_NAME_RE})"

    patterns = [
        # 대표이사 홍길동 / 대표이사 사장 홍길동 / CTO John Smith
        re.compile(
            rf"(?<![가-힣])(?P<title>{title_alternation}){SECONDARY_TITLE_RE}\s*[:：]?\s*"
            rf"(?P<name>{name_alternation})(?![가-힣])",
            re.I,
        ),
        # 홍길동 대표이사 / John Smith, CTO
        re.compile(
            rf"(?<![가-힣])(?P<name>{name_alternation})\s*[,/·]?\s*"
            rf"(?P<title>{title_alternation})(?![가-힣])",
            re.I,
        ),
    ]

    for page in _page_priority(crawl.pages, ("management", "company", "home", "contact")):
        lines = [line.strip() for line in page.text.split("\n") if line.strip()]
        # Cards often split the name and the title across two lines, so adjacent
        # pairs count too - but only for unambiguous titles. Across a line break,
        # a person named in a news item lands next to an unrelated "대표".
        units = [(line, False) for line in lines]
        # Chỉ ghép hai dòng khi cả hai đều ngắn như ô trong card nhân sự
        # ("노인선" / "대표이사"). Nếu một dòng là cả cụm footer thì tên công ty
        # khách hàng ở dòng trên sẽ dính vào chức danh ở dòng dưới.
        units += [
            (f"{a} {b}", True)
            for a, b in zip(lines, lines[1:])
            if len(a) <= 20 and len(b) <= 20
        ]
        for unit, joined in units:
            if len(unit) > 120:
                continue
            for pattern in patterns:
                for match in pattern.finditer(unit):
                    name = _clean(match.group("name"))
                    title_text = _clean(match.group("title"))
                    if not _plausible_name(name) or name.lower() in banned:
                        continue
                    loose = title_text.lower() in LOOSE_TITLE_TOKENS
                    if loose and joined:
                        continue
                    # Press releases name partners' executives too ("코스콤(대표 윤창현)").
                    # A directory entry is short; a news sentence is not.
                    if loose and len(unit) > 45:
                        continue
                    if loose and re.fullmatch(KOREAN_NAME_RE, name) and len(re.sub(r"\s+", "", name)) != 3:
                        continue
                    context = unit.lower()
                    if _is_excluded_role(context):
                        continue
                    rank = _title_rank(title_text)
                    if rank is None:
                        continue
                    index, label = rank
                    position = title_text if len(title_text) <= 40 else label
                    previous = found.get(name)
                    if previous is None or index < previous[0]:
                        found[name] = (index, name, position, page.final_url)

    # "Kelly Park" và "Kelly Park Go" là một người; đừng để một người chiếm
    # nhiều slot trong khi chỉ được trả tối đa 3 người.
    deduped: list[tuple[int, str, str, str]] = []
    for entry in sorted(found.values(), key=lambda item: item[0]):
        lowered = entry[1].lower()
        if any(lowered in kept[1].lower() or kept[1].lower() in lowered for kept in deduped):
            continue
        deduped.append(entry)
        if len(deduped) >= MAX_CONTACTS:
            break

    return [
        {"name": _display_name(name), "position": position, "source_url": source}
        for _rank, name, position, source in deduped
    ]


# -- IT recruitment --------------------------------------------------------


def _keyword_in(keyword: str, haystack: str) -> bool:
    """Tu khoa ASCII phai khop tron tu.

    Khong co bien tu thi "ai" khop trong "aimerfeel", "retail", "detail" - moi
    tin tuyen dung deu thanh tin IT. Tu khoa tieng Han khop chuoi con nhu cu.
    """
    if not haystack:
        return False
    if keyword.isascii():
        return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", haystack) is not None
    return keyword in haystack


def _is_it_job(title: str) -> bool:
    lowered = title.lower()
    is_it = any(_keyword_in(keyword, lowered) for keyword in IT_JOB_KEYWORDS)
    if any(_keyword_in(keyword, lowered) for keyword in NON_IT_JOB_KEYWORDS):
        # An explicitly IT-flavoured title wins over a generic non-IT word.
        return is_it
    return is_it


def _looks_like_posting(title: str, context: str) -> bool:
    """See below; also rejects navigation blobs harvested from menus."""
    if len(title) > 60 or len(title.split()) > 8:
        return False
    lowered = title.lower()
    if sum(1 for token in NAV_TOKENS if _keyword_in(token, lowered)) >= 3:
        return False
    return _has_posting_marker(title, context)


def _has_posting_marker(title: str, context: str) -> bool:
    """Guard against product links and headlines that merely contain "AI" or "개발".

    Accepted when the title names a role / announces hiring, or when the
    surrounding block carries posting metadata (employment type or deadline).
    """
    lowered = title.lower()
    if any(_keyword_in(marker, lowered) for marker in JOB_ROLE_MARKERS):
        return True
    return bool(_employment_type(context) or _deadline(context))


def _employment_type(text: str) -> str | None:
    lowered = text.lower()
    for token, label in EMPLOYMENT_TYPES:
        if _keyword_in(token, lowered):
            return label
    return None


def _location(text: str) -> str | None:
    labelled = _label_value(text, ("근무지", "근무지역", "근무장소", "지역", "location", "workplace"), 40)
    if labelled:
        return labelled[:60]
    for hint in LOCATION_HINTS:
        match = re.search(re.escape(hint) + r"[가-힣A-Za-z]{0,10}(?:\s?[가-힣]{1,6}(?:구|시|동))?", text, re.I)
        if match:
            return _clean(match.group(0))[:60]
    return None


def _deadline(text: str) -> str | None:
    match = DEADLINE_RE.search(text)
    return _clean(match.group(0))[:40] if match else None


def _job_position(title: str) -> str | None:
    lowered = title.lower()
    for keyword in IT_JOB_KEYWORDS:
        if _keyword_in(keyword, lowered):
            return keyword if keyword.isascii() is False else keyword.title()
    return None


def extract_it_jobs(crawl: CrawlResult) -> list[dict]:
    """IT/software openings only, max 10, each with a source URL."""
    jobs: dict[str, dict] = {}
    recruitment_pages = [p for p in crawl.pages if p.category == "recruitment"]

    for page in recruitment_pages:
        soup = page.soup

        # 1) Linked job entries (the common list/board layout).
        for anchor in soup.find_all("a", href=True):
            title = _clean(anchor.get_text(" ", strip=True))
            if not (4 <= len(title) <= 120) or not _is_it_job(title):
                continue
            container = anchor.find_parent(["li", "tr", "article", "div"]) or anchor
            context = _clean(container.get_text(" ", strip=True))[:400]
            if not _looks_like_posting(title, context):
                continue
            href = clean_link(page.final_url, anchor.get("href", ""))
            source = href if href and same_company_domain(href, crawl.base_domain) else page.final_url
            jobs.setdefault(title.lower(), {
                "title": title,
                "position": _job_position(title),
                "location": _location(context),
                "employment_type": _employment_type(context),
                "deadline": _deadline(context),
                "description": context[:200] if len(context) > len(title) + 10 else None,
                "source_url": source,
            })

        # 2) Headings and table/list rows without their own link. A row that
        # holds a link was already handled above, and its full text ("title +
        # 정규직 + 마감일") would otherwise be filed as a second, duplicate job.
        for element in soup.find_all(["h1", "h2", "h3", "h4", "li", "td", "strong"]):
            if element.find("a", href=True):
                continue
            title = _clean(element.get_text(" ", strip=True))
            if not (4 <= len(title) <= 120) or not _is_it_job(title):
                continue
            if any(known in title.lower() for known in jobs):
                continue
            container = element.find_parent(["li", "tr", "article", "div"]) or element
            context = _clean(container.get_text(" ", strip=True))[:400]
            if not _looks_like_posting(title, context):
                continue
            jobs.setdefault(title.lower(), {
                "title": title,
                "position": _job_position(title),
                "location": _location(context),
                "employment_type": _employment_type(context),
                "deadline": _deadline(context),
                "description": context[:200] if len(context) > len(title) + 10 else None,
                "source_url": page.final_url,
            })

    ordered = list(jobs.values())
    # Prefer entries that carry their own detail URL and more filled-in fields.
    ordered.sort(
        key=lambda job: (
            0 if urlsplit(job["source_url"]).path.count("/") > 1 else 1,
            -sum(1 for key in ("location", "employment_type", "deadline") if job[key]),
        )
    )
    return ordered[:MAX_JOBS]


def hiring_signal(job_count: int) -> str:
    """Spec section 15."""
    if job_count >= 5:
        return "High"
    if job_count >= 2:
        return "Medium"
    if job_count == 1:
        return "Low"
    return "None"


def build_result(crawl: CrawlResult) -> dict:
    company = extract_company(crawl)
    address = extract_address(crawl)
    phone = extract_phone(crawl)
    email = extract_email(crawl)
    industry = extract_industry(crawl)
    hints = {"email": email_hint(crawl)} if email is None else {}
    biz_number = extract_biz_number(crawl)
    ceo = extract_ceo(crawl)
    contacts = extract_key_contacts(crawl, company["name"])
    jobs = extract_it_jobs(crawl)

    # 대표 trong footer là người có thật của công ty; nếu key contacts còn
    # trống chỗ và chưa có người này thì bổ sung, xếp sau CTO/CIO đã tìm được.
    if ceo and len(contacts) < 3:
        compact = re.sub(r"\s+", "", ceo.value).lower()
        if not any(re.sub(r"\s+", "", c["name"]).lower() == compact for c in contacts):
            contacts.append({"name": ceo.value, "position": "대표", "source_url": ceo.source_url})

    home = crawl.pages[0].final_url if crawl.pages else crawl.start_url

    return {
        "company": {
            "name": company["name"],
            "address": address.value if address else NOT_FOUND,
            "phone": phone.value if phone else NOT_FOUND,
            "email": email.value if email else NOT_FOUND,
            "industry": industry.value if industry else NOT_FOUND,
            "biz_number": biz_number.value if biz_number else NOT_FOUND,
            "ceo": ceo.value if ceo else NOT_FOUND,
            "website": home,
        },
        "company_sources": {
            "name": company["name_source"],
            "address": address.source_url if address else NOT_FOUND,
            "phone": phone.source_url if phone else NOT_FOUND,
            "email": email.source_url if email else NOT_FOUND,
            "industry": industry.source_url if industry else NOT_FOUND,
            "biz_number": biz_number.source_url if biz_number else NOT_FOUND,
            "ceo": ceo.source_url if ceo else NOT_FOUND,
        },
        "company_hints": {key: value for key, value in hints.items() if value},
        "key_contacts": contacts,
        "it_recruitment": jobs,
        "sales_signal": {"it_hiring": hiring_signal(len(jobs))},
        "sources": [page.final_url for page in crawl.pages],
    }
