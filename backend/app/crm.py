"""CRM lead — luu, cham diem, nhap file.

Mot lead = mot dong trong bang `leads`. Lead co the noi voi mot cong ty da
quet (`company_id`) de biet lead do den tu scanner va mo lai ket qua quet.

Cac truong dac thu thi truong Han Quoc:
  biz_number    사업자등록번호 (000-00-00000) — ma so doanh nghiep, dung de
                doi chieu tren 국세청 / 크레탑 truoc khi ky hop dong.
  rank          직급 (사원 → 대표이사, CTO/CIO/CEO) — quyet dinh ai co quyen
                ky va cach xung ho trong email/전화.
  department    부서 (개발, IT기획, 구매, 경영지원...).
  mobile        휴대폰 010 — sales Han lien he chu yeu qua 휴대폰 + 카카오톡.
  kakao         카카오톡 ID.
  project_type  사업 유형: 파견 / 도급 / SI / SM / ODC — hinh thuc hop dong
                outsourcing pho bien tai Han.
  company_size  대기업 / 중견기업 / 중소기업 / 스타트업 / 공공기관.
  budget        예산 KRW.

Diem lead (`score`) tinh theo quy tac ro rang trong `score_lead`, khong
ngau nhien: du lieu tu scanner (IT 채용, chuc danh, email, dien thoai) va
du lieu sales nhap (ngan sach, nguon, hinh thuc du an).
"""
from __future__ import annotations

import base64
import csv
import io
import json
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from .crawler import registrable_domain
from .storage import connect

# Pipeline theo chu ky ban hang B2B tai Han: tiep can -> mit tinh nhu cau ->
# gui 제안서/견적서 -> 협상, 계약 검토 -> 수주. 보류 la khach dang chua co ngan sach.
STATUSES = ("new", "contacted", "meeting", "proposal", "negotiation", "won", "lost", "hold")
OPEN_STATUSES = ("new", "contacted", "meeting", "proposal", "negotiation")
LOST_REASONS = ("price", "schedule", "competitor", "inhouse", "budget", "language", "other")
ACTIVITY_TYPES = ("call", "email", "kakao", "meeting", "proposal", "quote", "other")

RANKS = ("staff", "assistant", "manager", "deputy", "general", "director",
         "md", "evp", "svp", "ceo", "cto", "cio", "other")
SOURCES = ("scanner", "referral", "exhibition", "linkedin", "wanted", "saramin",
           "jobkorea", "coldcall", "website", "naver", "customer", "other")
PROJECT_TYPES = ("dispatch", "contract", "si", "sm", "odc", "other")
COMPANY_SIZES = ("enterprise", "midsize", "sme", "startup", "public")

# Chuc danh tieng Han / tieng Anh -> ma `rank`. Dung khi chuyen key contact
# cua scanner thanh lead va khi nhap file.
RANK_ALIASES = {
    "사원": "staff", "주임": "staff", "staff": "staff",
    "대리": "assistant", "assistant manager": "assistant",
    "과장": "manager", "manager": "manager", "매니저": "manager",
    "차장": "deputy", "deputy general manager": "deputy",
    "부장": "general", "general manager": "general", "팀장": "general",
    "이사": "director", "director": "director", "본부장": "director", "실장": "director",
    "상무": "md", "managing director": "md",
    "전무": "evp", "executive vice president": "evp",
    "부사장": "svp", "senior vice president": "svp", "vice president": "svp", "vp": "svp",
    "대표이사": "ceo", "대표": "ceo", "사장": "ceo", "회장": "ceo", "ceo": "ceo",
    "founder": "ceo", "president": "ceo",
    "cto": "cto", "최고기술책임자": "cto", "기술이사": "cto",
    "cio": "cio", "최고정보책임자": "cio", "정보이사": "cio",
}

# Diem theo chuc danh: nguoi co quyen quyet dinh outsourcing cang cao cang tot.
RANK_SCORE = {
    "cto": 25, "cio": 25, "ceo": 22, "svp": 20, "evp": 20, "md": 18,
    "director": 18, "general": 12, "deputy": 10, "manager": 6,
    "assistant": 3, "staff": 2, "other": 4,
}
HIRING_SCORE = {"High": 25, "Medium": 15, "Low": 6, "None": 0}
SOURCE_SCORE = {"referral": 10, "exhibition": 8, "website": 8, "scanner": 4,
                "linkedin": 4, "wanted": 5, "saramin": 5, "jobkorea": 5, "coldcall": 0,
                "naver": 3, "customer": 12, "other": 0}   # khach cu quay lai: ty le chot cao nhat

# Cong nghe nhan ra trong tieu de tin tuyen dung cua scanner -> tech stack.
TECH_KEYWORDS = [
    "Java", "Spring", "Kotlin", "Python", "Django", "Node", "React", "Vue", "Angular",
    "Next.js", "TypeScript", "JavaScript", "Flutter", "iOS", "Android", "Swift", "C#",
    ".NET", "C++", "Go", "PHP", "Ruby", "Unity", "Unreal", "AWS", "Azure", "GCP",
    "Kubernetes", "Docker", "DevOps", "MSA", "AI", "ML", "LLM", "Data", "Blockchain",
    "QA", "Embedded", "Linux", "SAP", "Oracle", "MySQL", "PostgreSQL", "MongoDB",
]

BIZ_NUMBER_RE = re.compile(r"^\d{3}-\d{2}-\d{5}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER,
    domain        TEXT,
    company_name  TEXT    NOT NULL,
    website       TEXT,
    biz_number    TEXT,
    industry      TEXT,
    company_size  TEXT,
    contact_name  TEXT,
    rank          TEXT,
    department    TEXT,
    phone         TEXT,
    mobile        TEXT,
    email         TEXT,
    kakao         TEXT,
    source        TEXT    NOT NULL DEFAULT 'other',
    project_type  TEXT,
    tech          TEXT    NOT NULL DEFAULT '[]',
    budget        INTEGER,
    team_size     INTEGER,
    expected_start TEXT,
    bridge_se     INTEGER NOT NULL DEFAULT 0,
    competitor    TEXT,
    lost_reason   TEXT,
    it_hiring     TEXT,
    score         INTEGER NOT NULL DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'new',
    assignee      TEXT,
    next_action   TEXT,
    next_date     TEXT,
    last_contact  TEXT,
    memo          TEXT,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS leads_company ON leads(company_id);
CREATE TABLE IF NOT EXISTS activities (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id    INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    type       TEXT    NOT NULL DEFAULT 'other',
    note       TEXT,
    at         TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS activities_lead ON activities(lead_id);
"""

# Cot cho phep client gui len (khong co id / score / created_at).
EDITABLE = (
    "company_id", "domain", "company_name", "website", "biz_number", "industry",
    "company_size", "contact_name", "rank", "department", "phone", "mobile", "email",
    "kakao", "source", "project_type", "tech", "budget", "team_size", "expected_start",
    "bridge_se", "competitor", "lost_reason", "it_hiring", "status",
    "assignee", "next_action", "next_date", "last_contact", "memo",
)


class LeadError(ValueError):
    """Du lieu lead khong hop le; message la ma loi ngan de client dich."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_leads(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)


def init_db() -> None:
    with closing(_open()):
        pass


def _open() -> sqlite3.Connection:
    connection = connect()
    connection.execute("PRAGMA foreign_keys=ON")   # xoa lead thi xoa ca hoat dong
    init_leads(connection)
    return connection


# -- Chuan hoa ---------------------------------------------------------------


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_rank(value) -> str | None:
    """'CTO / 최고기술책임자' -> 'cto'; chuoi la thi 'other'; trong thi None."""
    text = _clean(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered in RANKS:
        return lowered
    # Ưu tiên chức danh cao nhất xuất hiện trong chuỗi (예: "부사장 겸 CTO").
    best, best_score = None, -1
    for alias, code in RANK_ALIASES.items():
        # Alias ASCII phai dung nguyen tu: "director" chua "cto" ben trong.
        if alias.isascii():
            hit = re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", lowered) is not None
        else:
            hit = alias in lowered
        if hit and RANK_SCORE[code] > best_score:
            best, best_score = code, RANK_SCORE[code]
    return best or "other"


def normalize_biz_number(value) -> str | None:
    """'1208112345' / '120 81 12345' -> '120-81-12345'. Sai dinh dang thi giu nguyen."""
    text = _clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return text


def normalize_phone(value) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if digits.startswith("82") and len(digits) >= 10:
        digits = "0" + digits[2:]
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits.startswith("02"):
        return f"02-{digits[2:6]}-{digits[6:]}"
    if len(digits) == 9 and digits.startswith("02"):
        return f"02-{digits[2:5]}-{digits[5:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return text


def normalize_tech(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                value = parsed
        except (json.JSONDecodeError, TypeError):
            pass
    if isinstance(value, str):
        value = re.split(r"[|;,/]", value)
    seen: list[str] = []
    for item in value:
        text = _clean(item)
        if text and text.lower() not in {s.lower() for s in seen}:
            seen.append(text[:30])
    return seen[:8]


def normalize_budget(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    # "2.5억", "3000만", "₩ 1억 5000만" — don vi tien Han.
    total, matched = 0, False
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(억|만|원)?", text):
        if not number:
            continue
        matched = True
        amount = float(number)
        if unit == "억":
            amount *= 100_000_000
        elif unit == "만":
            amount *= 10_000
        total += amount
    return int(total) if matched else None


def _one_of(value, allowed: tuple[str, ...], default: str | None) -> str | None:
    text = _clean(value)
    if not text:
        return default
    lowered = text.lower()
    return lowered if lowered in allowed else default


def _iso_date(value) -> str | None:
    text = _clean(value)
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10], pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _domain_from_website(website: str | None) -> str | None:
    if not website:
        return None
    candidate = website if "://" in website else "http://" + website
    host = urlsplit(candidate).hostname
    return registrable_domain(host) if host else None


def normalize_lead(payload: dict, existing: dict | None = None) -> dict:
    """Chuan hoa du lieu tu client / file thanh mot dong lead day du."""
    data = dict(existing or {})
    for key in EDITABLE:
        if key in payload:
            data[key] = payload[key]

    company_name = _clean(data.get("company_name"))
    if not company_name:
        raise LeadError("company_required")

    email = _clean(data.get("email"))
    if email:
        email = email.lower()
        if not EMAIL_RE.match(email):
            raise LeadError("email_invalid")

    website = _clean(data.get("website"))
    domain = _clean(data.get("domain")) or _domain_from_website(website)

    rank = normalize_rank(data.get("rank"))
    lead = {
        "company_id": int(data["company_id"]) if data.get("company_id") not in (None, "") else None,
        "domain": domain,
        "company_name": company_name[:120],
        "website": website,
        "biz_number": normalize_biz_number(data.get("biz_number")),
        "industry": _clean(data.get("industry")),
        "company_size": _one_of(data.get("company_size"), COMPANY_SIZES, None),
        "contact_name": _clean(data.get("contact_name")),
        "rank": rank,
        "department": _clean(data.get("department")),
        "phone": normalize_phone(data.get("phone")),
        "mobile": normalize_phone(data.get("mobile")),
        "email": email,
        "kakao": _clean(data.get("kakao")),
        "source": _one_of(data.get("source"), SOURCES, "other"),
        "project_type": _one_of(data.get("project_type"), PROJECT_TYPES, None),
        "tech": normalize_tech(data.get("tech")),
        "budget": normalize_budget(data.get("budget")),
        "team_size": _int_or_none(data.get("team_size")),
        "expected_start": _year_month(data.get("expected_start")),
        "bridge_se": 1 if str(data.get("bridge_se") or "").strip().lower() in ("1", "true", "yes", "y", "필요", "o") else 0,
        "competitor": _clean(data.get("competitor")),
        "lost_reason": _one_of(data.get("lost_reason"), LOST_REASONS, None),
        "it_hiring": _one_of(data.get("it_hiring"), ("high", "medium", "low", "none"), None),
        "status": _one_of(data.get("status"), STATUSES, "new"),
        "assignee": _clean(data.get("assignee")),
        "next_action": _clean(data.get("next_action")),
        "next_date": _iso_date(data.get("next_date")),
        "last_contact": _iso_date(data.get("last_contact")),
        "memo": _clean(data.get("memo")),
    }
    if lead["it_hiring"]:
        lead["it_hiring"] = lead["it_hiring"].capitalize()
    if lead["status"] != "lost":
        lead["lost_reason"] = None
    lead["score"] = score_lead(lead)
    return lead


def _int_or_none(value) -> int | None:
    text = _clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def _year_month(value) -> str | None:
    """'2026-11', '2026.11', '2026년 11월', '2026-11-05' -> '2026-11'."""
    text = _clean(value)
    if not text:
        return None
    match = re.search(r"(20\d{2})\D{0,3}(\d{1,2})", text)
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}"


def _months_until(year_month: str | None) -> int | None:
    if not year_month:
        return None
    year, month = int(year_month[:4]), int(year_month[5:7])
    today = date.today()
    return (year - today.year) * 12 + (month - today.month)


# -- Cham diem ---------------------------------------------------------------


def score_lead(lead: dict) -> int:
    """Diem 0-100 theo quy tac co the giai thich duoc cho sales.

    Tin hieu tu scanner:  IT 채용 (toi da 25), chuc danh nguoi lien he (25).
    Kha nang lien he:     email 10, dien thoai/휴대폰 10, 카카오톡 5.
    Du lieu sales nhap:   ngan sach (toi da 15), nguon (toi da 10),
                          hinh thuc du an 5, 사업자등록번호 hop le 3,
                          발주 예정 trong 3 thang 8 (6 thang 4), 필요 인원 >= 3 la 5.
    """
    score = 0
    score += HIRING_SCORE.get(lead.get("it_hiring") or "None", 0)
    score += RANK_SCORE.get(lead.get("rank") or "", 0)
    if lead.get("email"):
        score += 10
    if lead.get("phone") or lead.get("mobile"):
        score += 10
    if lead.get("kakao"):
        score += 5
    budget = lead.get("budget") or 0
    if budget >= 300_000_000:
        score += 15
    elif budget >= 100_000_000:
        score += 12
    elif budget >= 30_000_000:
        score += 7
    elif budget > 0:
        score += 3
    score += SOURCE_SCORE.get(lead.get("source") or "other", 0)
    if lead.get("project_type"):
        score += 5
    if lead.get("biz_number") and BIZ_NUMBER_RE.match(lead["biz_number"]):
        score += 3
    months = _months_until(lead.get("expected_start"))
    if months is not None and months <= 3:
        score += 8
    elif months is not None and months <= 6:
        score += 4
    if (lead.get("team_size") or 0) >= 3:
        score += 5
    return max(0, min(100, score))


def score_breakdown(lead: dict) -> list[dict]:
    """Tung khoan diem, de hien 'vi sao 85 diem' trong UI."""
    parts = []
    hiring = HIRING_SCORE.get(lead.get("it_hiring") or "None", 0)
    if hiring:
        parts.append({"key": "hiring", "points": hiring})
    rank = RANK_SCORE.get(lead.get("rank") or "", 0)
    if rank:
        parts.append({"key": "rank", "points": rank})
    if lead.get("email"):
        parts.append({"key": "email", "points": 10})
    if lead.get("phone") or lead.get("mobile"):
        parts.append({"key": "phone", "points": 10})
    if lead.get("kakao"):
        parts.append({"key": "kakao", "points": 5})
    budget = lead.get("budget") or 0
    budget_points = 15 if budget >= 300_000_000 else 12 if budget >= 100_000_000 else 7 if budget >= 30_000_000 else 3 if budget > 0 else 0
    if budget_points:
        parts.append({"key": "budget", "points": budget_points})
    source = SOURCE_SCORE.get(lead.get("source") or "other", 0)
    if source:
        parts.append({"key": "source", "points": source})
    if lead.get("project_type"):
        parts.append({"key": "project", "points": 5})
    if lead.get("biz_number") and BIZ_NUMBER_RE.match(lead["biz_number"]):
        parts.append({"key": "biz", "points": 3})
    months = _months_until(lead.get("expected_start"))
    if months is not None and months <= 3:
        parts.append({"key": "timing", "points": 8})
    elif months is not None and months <= 6:
        parts.append({"key": "timing", "points": 4})
    if (lead.get("team_size") or 0) >= 3:
        parts.append({"key": "team", "points": 5})
    return parts


# -- Tu ket qua scan -----------------------------------------------------------


def tech_from_jobs(jobs: list[dict]) -> list[str]:
    """Cong nghe xuat hien trong tieu de/mo ta tin tuyen dung IT da quet."""
    text = " ".join(f"{job.get('title') or ''} {job.get('description') or ''}" for job in jobs or [])
    found = []
    for keyword in TECH_KEYWORDS:
        pattern = r"(?<![A-Za-z0-9])" + re.escape(keyword) + r"(?![A-Za-z0-9])"
        if re.search(pattern, text, re.I):
            found.append(keyword)
    return found[:8]


def lead_from_company(saved: dict) -> dict:
    """Payload lead dien san tu mot cong ty da luu (ket qua scan that)."""
    result = saved.get("result") or {}
    company = result.get("company") or {}
    contacts = result.get("key_contacts") or []
    first = contacts[0] if contacts else {}
    ceo = company.get("ceo") or saved.get("ceo")
    return {
        "company_id": saved.get("id"),
        "domain": saved.get("domain"),
        "company_name": company.get("name") or saved.get("name") or saved.get("domain") or "",
        "website": company.get("website") or saved.get("website"),
        "industry": company.get("industry") or saved.get("industry"),
        "biz_number": company.get("biz_number") or saved.get("biz_number"),
        "contact_name": first.get("name") or ceo,
        "rank": first.get("position") or ("대표이사" if ceo else None),
        "phone": company.get("phone") or saved.get("phone"),
        "email": company.get("email") or saved.get("email"),
        "source": "scanner",
        "tech": tech_from_jobs(result.get("it_recruitment") or []),
        "it_hiring": (result.get("sales_signal") or {}).get("it_hiring") or saved.get("it_hiring"),
        "memo": _scan_memo(company, contacts, result),
    }


def _scan_memo(company: dict, contacts: list[dict], result: dict) -> str | None:
    lines = []
    if company.get("address"):
        lines.append(f"주소: {company['address']}")
    for contact in contacts[1:3]:
        if contact.get("name"):
            lines.append(f"담당자: {contact['name']} {contact.get('position') or ''}".strip())
    jobs = result.get("it_recruitment") or []
    if jobs:
        lines.append("채용: " + ", ".join(job.get("title") for job in jobs[:5] if job.get("title")))
    return "\n".join(lines) or None


# -- CRUD ----------------------------------------------------------------------


def _row_to_lead(row: sqlite3.Row) -> dict:
    lead = dict(row)
    try:
        lead["tech"] = json.loads(lead.get("tech") or "[]")
    except json.JSONDecodeError:
        lead["tech"] = []
    lead["overdue"] = bool(
        lead.get("next_date") and lead["status"] in OPEN_STATUSES
        and lead["next_date"] < date.today().isoformat()
    )
    return lead


def _write(connection: sqlite3.Connection, lead: dict, lead_id: int | None) -> int:
    columns = list(EDITABLE) + ["score", "updated_at"]
    values = {**lead, "tech": json.dumps(lead["tech"], ensure_ascii=False), "updated_at": _now()}
    if lead_id is None:
        columns.append("created_at")
        values["created_at"] = values["updated_at"]
        placeholders = ", ".join("?" for _ in columns)
        cursor = connection.execute(
            f"INSERT INTO leads ({', '.join(columns)}) VALUES ({placeholders})",
            [values.get(column) for column in columns],
        )
        return int(cursor.lastrowid)
    assignments = ", ".join(f"{column} = ?" for column in columns)
    connection.execute(
        f"UPDATE leads SET {assignments} WHERE id = ?",
        [values.get(column) for column in columns] + [lead_id],
    )
    return lead_id


def list_leads() -> list[dict]:
    with closing(_open()) as connection, connection:
        rows = connection.execute("SELECT * FROM leads ORDER BY updated_at DESC, id DESC").fetchall()
    return [_row_to_lead(row) for row in rows]


def get_lead(lead_id: int) -> dict | None:
    with closing(_open()) as connection, connection:
        row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return _row_to_lead(row) if row else None


def create_lead(payload: dict) -> dict:
    lead = normalize_lead(payload)
    with closing(_open()) as connection, connection:
        lead_id = _write(connection, lead, None)
        row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return _row_to_lead(row)


def update_lead(lead_id: int, payload: dict) -> dict | None:
    with closing(_open()) as connection, connection:
        row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if row is None:
            return None
        existing = _row_to_lead(row)
        lead = normalize_lead(payload, existing)
        _write(connection, lead, lead_id)
        row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return _row_to_lead(row)


def delete_leads(ids: list[int]) -> int:
    if not ids:
        return 0
    with closing(_open()) as connection, connection:
        cursor = connection.execute(
            f"DELETE FROM leads WHERE id IN ({', '.join('?' for _ in ids)})", ids
        )
    return cursor.rowcount


def find_lead_for_company(company_id: int | None, domain: str | None) -> dict | None:
    """Lead da tao tu cong ty nay (theo company_id, khong co thi theo domain)."""
    with closing(_open()) as connection, connection:
        row = None
        if company_id is not None:
            row = connection.execute(
                "SELECT * FROM leads WHERE company_id = ? ORDER BY id LIMIT 1", (company_id,)
            ).fetchone()
        if row is None and domain:
            row = connection.execute(
                "SELECT * FROM leads WHERE domain = ? ORDER BY id LIMIT 1", (domain,)
            ).fetchone()
    return _row_to_lead(row) if row else None


# -- Nhat ky hoat dong ----------------------------------------------------------


def list_activities(lead_id: int) -> list[dict]:
    with closing(_open()) as connection, connection:
        rows = connection.execute(
            "SELECT * FROM activities WHERE lead_id = ? ORDER BY at DESC, id DESC", (lead_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def add_activity(lead_id: int, payload: dict) -> dict | None:
    """Ghi mot hoat dong va cap nhat `last_contact` cua lead."""
    kind = _one_of(payload.get("type"), ACTIVITY_TYPES, "other")
    note = _clean(payload.get("note"))
    at = _iso_date(payload.get("at")) or date.today().isoformat()
    with closing(_open()) as connection, connection:
        if connection.execute("SELECT 1 FROM leads WHERE id = ?", (lead_id,)).fetchone() is None:
            return None
        cursor = connection.execute(
            "INSERT INTO activities (lead_id, type, note, at, created_at) VALUES (?, ?, ?, ?, ?)",
            (lead_id, kind, note, at, _now()),
        )
        connection.execute(
            "UPDATE leads SET last_contact = MAX(COALESCE(last_contact, ''), ?), updated_at = ? WHERE id = ?",
            (at, _now(), lead_id),
        )
        row = connection.execute("SELECT * FROM activities WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def delete_activity(activity_id: int) -> bool:
    with closing(_open()) as connection, connection:
        cursor = connection.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    return cursor.rowcount > 0


# -- Nhap file (CSV / JSON) ------------------------------------------------------

# Ten cot trong file -> ten truong. Nhan tieng Han (Excel Han), tieng Viet, tieng Anh.
HEADER_ALIASES = {
    "company_name": ("company_name", "company", "회사명", "기업명", "회사", "tên công ty", "công ty"),
    "website": ("website", "url", "웹사이트", "홈페이지", "website công ty"),
    "biz_number": ("biz_number", "business_number", "사업자등록번호", "사업자번호", "mã số doanh nghiệp", "mã số thuế"),
    "industry": ("industry", "업종", "사업분야", "lĩnh vực", "ngành"),
    "company_size": ("company_size", "size", "기업규모", "규모", "quy mô"),
    "contact_name": ("contact_name", "contact", "name", "담당자명", "담당자", "이름", "tên liên hệ", "liên hệ", "người liên hệ"),
    "rank": ("rank", "title", "position", "직급", "직책", "chức vụ", "chức danh"),
    "department": ("department", "부서", "phòng ban", "bộ phận"),
    "phone": ("phone", "tel", "전화", "전화번호", "회사전화", "sđt", "số điện thoại", "điện thoại"),
    "mobile": ("mobile", "cell", "휴대폰", "핸드폰", "휴대전화", "di động"),
    "email": ("email", "e-mail", "이메일", "메일"),
    "kakao": ("kakao", "kakaotalk", "카카오톡", "카카오", "카톡"),
    "source": ("source", "유입경로", "출처", "nguồn"),
    "project_type": ("project_type", "사업유형", "사업 유형", "계약형태", "loại dự án", "hình thức"),
    "tech": ("tech", "tech_stack", "기술스택", "기술", "công nghệ"),
    "budget": ("budget", "예산", "ngân sách"),
    "team_size": ("team_size", "headcount", "필요인원", "필요 인원", "인원", "số người", "nhân sự"),
    "expected_start": ("expected_start", "start", "발주예정", "발주 예정", "착수예정", "dự kiến bắt đầu"),
    "bridge_se": ("bridge_se", "브릿지", "브릿지se", "한국어브릿지", "bridge"),
    "competitor": ("competitor", "경쟁사", "협력사", "현재협력사", "đối thủ", "vendor hiện tại"),
    "lost_reason": ("lost_reason", "실패사유", "실패 사유", "lý do thất bại"),
    "status": ("status", "상태", "trạng thái"),
    "assignee": ("assignee", "owner", "담당영업", "담당 영업", "영업담당", "phụ trách", "sales"),
    "next_action": ("next_action", "다음액션", "다음 액션", "hành động tiếp"),
    "next_date": ("next_date", "다음일정", "다음 일정", "예정일", "ngày tiếp theo"),
    "memo": ("memo", "note", "notes", "메모", "비고", "ghi chú"),
}

SOURCE_ALIASES = {
    "소개": "referral", "추천": "referral", "referral": "referral", "giới thiệu": "referral",
    "전시회": "exhibition", "박람회": "exhibition", "exhibition": "exhibition", "triển lãm": "exhibition",
    "linkedin": "linkedin", "링크드인": "linkedin",
    "wanted": "wanted", "원티드": "wanted",
    "사람인": "saramin", "saramin": "saramin",
    "잡코리아": "jobkorea", "jobkorea": "jobkorea",
    "콜드콜": "coldcall", "cold call": "coldcall", "coldcall": "coldcall", "gọi lạnh": "coldcall",
    "홈페이지": "website", "웹사이트": "website", "website": "website", "inbound": "website",
    "네이버": "naver", "naver": "naver",
    "스캐너": "scanner", "scanner": "scanner",
    "기존고객": "customer", "기존 고객": "customer", "재계약": "customer", "customer": "customer", "khách cũ": "customer",
}
STATUS_ALIASES = {
    "신규": "new", "new": "new", "mới": "new",
    "접촉": "contacted", "접촉시도": "contacted", "contacted": "contacted", "đã liên hệ": "contacted",
    "미팅": "meeting", "meeting": "meeting", "họp": "meeting",
    "제안": "proposal", "제안/견적": "proposal", "견적": "proposal", "proposal": "proposal", "đề xuất": "proposal",
    "협상": "negotiation", "계약검토": "negotiation", "negotiation": "negotiation", "đàm phán": "negotiation",
    "수주": "won", "won": "won", "계약": "won", "thắng": "won",
    "실패": "lost", "lost": "lost", "thua": "lost",
    "보류": "hold", "hold": "hold", "tạm dừng": "hold",
}
PROJECT_ALIASES = {
    "파견": "dispatch", "dispatch": "dispatch", "phái cử": "dispatch",
    "도급": "contract", "contract": "contract", "khoán": "contract",
    "si": "si", "sm": "sm", "odc": "odc", "오프쇼어": "odc", "offshore": "odc",
}
SIZE_ALIASES = {
    "대기업": "enterprise", "enterprise": "enterprise", "tập đoàn": "enterprise",
    "중견기업": "midsize", "중견": "midsize", "midsize": "midsize",
    "중소기업": "sme", "중소": "sme", "sme": "sme",
    "스타트업": "startup", "startup": "startup",
    "공공기관": "public", "공공": "public", "public": "public",
}


def _decode_upload(content: bytes) -> str:
    """CSV tu Excel Han thuong la CP949, khong phai UTF-8."""
    if content.startswith(b"\xef\xbb\xbf"):
        return content[3:].decode("utf-8", errors="replace")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp949", errors="replace")


def _header_key(header: str) -> str | None:
    lowered = header.strip().lower().lstrip("﻿")
    for key, aliases in HEADER_ALIASES.items():
        if lowered in aliases:
            return key
    return None


def _map_row(raw: dict) -> dict:
    mapped: dict = {}
    for header, value in raw.items():
        if header is None:
            continue
        key = _header_key(str(header))
        if key and value not in (None, ""):
            mapped[key] = value
    if "source" in mapped:
        mapped["source"] = SOURCE_ALIASES.get(str(mapped["source"]).strip().lower(), mapped["source"])
    if "status" in mapped:
        mapped["status"] = STATUS_ALIASES.get(str(mapped["status"]).strip().lower(), mapped["status"])
    if "project_type" in mapped:
        mapped["project_type"] = PROJECT_ALIASES.get(str(mapped["project_type"]).strip().lower(), mapped["project_type"])
    if "company_size" in mapped:
        mapped["company_size"] = SIZE_ALIASES.get(str(mapped["company_size"]).strip().lower(), mapped["company_size"])
    return mapped


def parse_upload(filename: str, content_base64: str) -> list[dict]:
    """Doc file CSV / JSON nguoi dung tai len thanh danh sach dict theo cot goc."""
    content = base64.b64decode(content_base64 or "")
    text = _decode_upload(content)
    if filename.lower().endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LeadError("file_invalid") from exc
        if isinstance(data, dict):
            data = data.get("leads") or data.get("data") or [data]
        if not isinstance(data, list):
            raise LeadError("file_invalid")
        return [row for row in data if isinstance(row, dict)]

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return [row for row in reader if any((value or "").strip() for value in row.values() if value)]


def _dedupe_key(lead: dict) -> tuple:
    if lead.get("email"):
        return ("email", lead["email"])
    return ("pair", (lead.get("company_name") or "").lower(), (lead.get("contact_name") or "").lower())


def import_leads(filename: str, content_base64: str, commit: bool) -> dict:
    """Xem truoc (commit=False) hoac ghi (commit=True) lead tu file.

    Trung lap: cung email, hoac cung (cong ty + nguoi lien he) voi lead da co
    hay voi dong khac trong file. Dong loi (thieu ten cong ty, email sai) duoc
    liet ke rieng, khong chan cac dong hop le.
    """
    raw_rows = parse_upload(filename, content_base64)
    existing_keys = {_dedupe_key(lead) for lead in list_leads()}
    seen: set = set()
    valid, duplicates, errors, preview = [], 0, [], []

    for index, raw in enumerate(raw_rows, start=1):
        mapped = _map_row(raw)
        try:
            lead = normalize_lead(mapped)
        except LeadError as exc:
            errors.append({"row": index, "code": str(exc)})
            continue
        key = _dedupe_key(lead)
        if key in existing_keys or key in seen:
            duplicates += 1
            continue
        seen.add(key)
        valid.append(lead)
        if len(preview) < 5:
            preview.append({k: lead.get(k) for k in ("company_name", "contact_name", "rank", "phone", "mobile", "email", "source", "budget", "expected_start")})

    inserted = 0
    if commit and valid:
        with closing(_open()) as connection, connection:
            for lead in valid:
                _write(connection, lead, None)
                inserted += 1

    return {
        "total": len(raw_rows),
        "valid": len(valid),
        "duplicates": duplicates,
        "errors": errors,
        "preview": preview,
        "inserted": inserted,
    }


def calendar_ics() -> str:
    """Lịch .ics: một sự kiện cả ngày cho mỗi lead đang mở có ngày hành động tiếp.

    Nhập vào Google/Naver Calendar/Outlook để được nhắc mà không cần mở app.
    """
    def escape(text: str) -> str:
        return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Company Scanner//CRM//KO", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:CRM 리드 일정"]
    events = []
    for lead in list_leads():
        if not lead.get("next_date") or lead["status"] not in OPEN_STATUSES:
            continue
        summary = f"[CRM] {lead['company_name']}" + (f" — {lead['next_action']}" if lead.get("next_action") else "")
        details = [part for part in (
            lead.get("contact_name"), lead.get("mobile") or lead.get("phone"), lead.get("email"), lead.get("memo"),
        ) if part]
        events.append({"uid": f"lead-{lead['id']}", "date": lead["next_date"], "summary": summary,
                       "description": chr(10).join(details)})
    # Hop dong sap het han: nhac truoc N ngay de de xuat 재계약.
    from .contracts import calendar_events  # noqa: E402 - tranh import vong
    events.extend(calendar_events())
    for event in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{event['uid']}@company-scanner",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{event['date'].replace('-', '')}",
            f"SUMMARY:{escape(event['summary'])}",
            f"DESCRIPTION:{escape(event.get('description') or '')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def _fold(line: str, limit: int = 74) -> str:
    """RFC 5545: dong dai hon 75 octet phai ngat bang CRLF + space (dem theo byte UTF-8)."""
    parts, current, size = [], "", 0
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > limit:
            parts.append(current)
            current, size = " " + char, 1 + width
        else:
            current, size = current + char, size + width
    parts.append(current)
    return "\r\n".join(parts)


def sample_csv() -> str:
    """CSV mau voi dung cac cot ma import hieu, de nguoi dung dien theo."""
    rows = [
        ["회사명", "사업자등록번호", "담당자명", "직급", "부서", "전화", "휴대폰", "이메일", "카카오톡",
         "유입경로", "사업유형", "기술스택", "예산", "필요인원", "발주예정", "브릿지SE", "경쟁사",
         "기업규모", "담당영업", "다음일정", "메모"],
        ["예시기업", "123-45-67890", "홍길동", "부장", "개발팀", "02-1234-5678", "010-1234-5678",
         "hong@example.co.kr", "hong_gd", "전시회", "도급", "Java|Spring|AWS", "150000000", "4",
         "2026-11", "필요", "A사", "중견기업", "Huy", "2026-10-01", "AWS 마이그레이션 검토 중"],
    ]
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return "﻿" + buffer.getvalue()
