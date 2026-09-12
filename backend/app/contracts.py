"""Khach hang da ky hop dong — hop dong, gia tri, thoi han, xep hang khach hang.

Mot dong `contracts` = mot hop dong. Khach hang (customer) la tap hop dong cua
cung mot cong ty (khoa theo domain, khong co domain thi theo ten). Tu do tinh:

  total_value   tong gia tri hop dong da ky (LTV)
  active_value  gia tri hop dong dang thuc hien
  next_expiry   hop dong sap het han -> co hoi 재계약 / 업셀 (resell)
  grade         S / A / B / C theo quy tac ro rang trong `grade_customer`

Dac thu thi truong Han:
  project_type  파견 / 도급 / SI / SM / ODC
  monthly_rate  don gia thang (M/M) — 파견/ODC tinh tien theo thang x so nguoi
  payment_terms 월말 청구 / 선금·중도·잔금 / 분기 ...
  renewal_notice_days  so ngay truoc het han can bao (mac dinh 60: hop dong
                       Han thuong yeu cau thong bao gia han truoc 1-2 thang)
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

from .crm import PROJECT_TYPES, _clean, _iso_date, _one_of, normalize_budget, normalize_phone, normalize_rank
from .crm import _domain_from_website
from .storage import connect

STATUSES = ("active", "completed", "renewed", "terminated")
PAYMENT_TERMS = ("monthly", "milestone", "quarterly", "upfront", "other")
RENEWAL_NOTICE_DAYS = 60

# Xep hang theo tong gia tri da ky + so hop dong (khach quay lai quan trong
# hon khach mot lan). Nguong KRW: 5억 / 2억 / 5천만.
GRADE_RULES = (
    ("S", 500_000_000, 1),
    ("S", 200_000_000, 3),
    ("A", 200_000_000, 1),
    ("A", 50_000_000, 2),
    ("B", 50_000_000, 1),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id         INTEGER,
    company_id      INTEGER,
    domain          TEXT,
    company_name    TEXT    NOT NULL,
    website         TEXT,
    biz_number      TEXT,
    title           TEXT,
    contract_no     TEXT,
    project_type    TEXT,
    status          TEXT    NOT NULL DEFAULT 'active',
    start_date      TEXT,
    end_date        TEXT,
    signed_date     TEXT,
    amount          INTEGER,
    monthly_rate    INTEGER,
    team_size       INTEGER,
    payment_terms   TEXT,
    contact_name    TEXT,
    rank            TEXT,
    department      TEXT,
    phone           TEXT,
    email           TEXT,
    our_pm          TEXT,
    tech            TEXT    NOT NULL DEFAULT '[]',
    satisfaction    INTEGER,
    renewal_notice_days INTEGER NOT NULL DEFAULT 60,
    memo            TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS contracts_domain ON contracts(domain);
CREATE INDEX IF NOT EXISTS contracts_end ON contracts(end_date);
"""

EDITABLE = (
    "lead_id", "company_id", "domain", "company_name", "website", "biz_number", "title",
    "contract_no", "project_type", "status", "start_date", "end_date", "signed_date", "amount",
    "monthly_rate", "team_size", "payment_terms", "contact_name", "rank", "department", "phone",
    "email", "our_pm", "tech", "satisfaction", "renewal_notice_days", "memo",
)


class ContractError(ValueError):
    """Ma loi ngan de client dich."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _open() -> sqlite3.Connection:
    connection = connect()
    connection.executescript(SCHEMA)
    return connection


def init_db() -> None:
    with closing(_open()):
        pass


def _int(value) -> int | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return int(float(str(text).replace(",", "")))
    except ValueError:
        return None


def normalize_contract(payload: dict, existing: dict | None = None) -> dict:
    data = dict(existing or {})
    for key in EDITABLE:
        if key in payload:
            data[key] = payload[key]

    company_name = _clean(data.get("company_name"))
    if not company_name:
        raise ContractError("company_required")

    amount = normalize_budget(data.get("amount"))
    monthly = normalize_budget(data.get("monthly_rate"))
    team = _int(data.get("team_size"))
    start = _iso_date(data.get("start_date"))
    end = _iso_date(data.get("end_date"))
    if start and end and end < start:
        raise ContractError("dates_invalid")

    # 파견/ODC: khong nhap tong tien thi tinh = don gia thang x nguoi x so thang.
    if amount is None and monthly and start and end:
        months = _months_between(start, end)
        amount = int(monthly * (team or 1) * months)
    if amount is None:
        raise ContractError("amount_required")

    website = _clean(data.get("website"))
    domain = _clean(data.get("domain")) or _domain_from_website(website)
    from .crm import normalize_tech  # tranh import vong o muc module

    satisfaction = _int(data.get("satisfaction"))
    if satisfaction is not None and not 1 <= satisfaction <= 5:
        satisfaction = None

    email = _clean(data.get("email"))
    return {
        "lead_id": _int(data.get("lead_id")),
        "company_id": _int(data.get("company_id")),
        "domain": domain,
        "company_name": company_name[:120],
        "website": website,
        "biz_number": _clean(data.get("biz_number")),
        "title": _clean(data.get("title")),
        "contract_no": _clean(data.get("contract_no")),
        "project_type": _one_of(data.get("project_type"), PROJECT_TYPES, None),
        "status": _one_of(data.get("status"), STATUSES, "active"),
        "start_date": start,
        "end_date": end,
        "signed_date": _iso_date(data.get("signed_date")) or start,
        "amount": amount,
        "monthly_rate": monthly,
        "team_size": team,
        "payment_terms": _one_of(data.get("payment_terms"), PAYMENT_TERMS, None),
        "contact_name": _clean(data.get("contact_name")),
        "rank": normalize_rank(data.get("rank")),
        "department": _clean(data.get("department")),
        "phone": normalize_phone(data.get("phone")),
        "email": email.lower() if email else None,
        "our_pm": _clean(data.get("our_pm")),
        "tech": normalize_tech(data.get("tech")),
        "satisfaction": satisfaction,
        "renewal_notice_days": _int(data.get("renewal_notice_days")) or RENEWAL_NOTICE_DAYS,
        "memo": _clean(data.get("memo")),
    }


def _months_between(start: str, end: str) -> float:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    return max(1.0, round(((last - first).days + 1) / 30.4, 1))


# -- CRUD --------------------------------------------------------------------


def _row(row: sqlite3.Row) -> dict:
    contract = dict(row)
    try:
        contract["tech"] = json.loads(contract.get("tech") or "[]")
    except json.JSONDecodeError:
        contract["tech"] = []
    today = date.today()
    end = contract.get("end_date")
    contract["days_left"] = (date.fromisoformat(end) - today).days if end else None
    notice = contract.get("renewal_notice_days") or RENEWAL_NOTICE_DAYS
    contract["expiring"] = bool(
        contract["status"] == "active" and contract["days_left"] is not None and contract["days_left"] <= notice
    )
    contract["overdue_end"] = bool(contract["status"] == "active" and contract["days_left"] is not None and contract["days_left"] < 0)
    return contract


def _write(connection: sqlite3.Connection, contract: dict, contract_id: int | None) -> int:
    columns = list(EDITABLE) + ["updated_at"]
    values = {**contract, "tech": json.dumps(contract["tech"], ensure_ascii=False), "updated_at": _now()}
    if contract_id is None:
        columns.append("created_at")
        values["created_at"] = values["updated_at"]
        cursor = connection.execute(
            f"INSERT INTO contracts ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            [values.get(column) for column in columns],
        )
        return int(cursor.lastrowid)
    connection.execute(
        f"UPDATE contracts SET {', '.join(f'{c} = ?' for c in columns)} WHERE id = ?",
        [values.get(column) for column in columns] + [contract_id],
    )
    return contract_id


def list_contracts() -> list[dict]:
    with closing(_open()) as connection, connection:
        rows = connection.execute(
            "SELECT * FROM contracts ORDER BY COALESCE(end_date, start_date, signed_date) DESC, id DESC"
        ).fetchall()
    return [_row(row) for row in rows]


def get_contract(contract_id: int) -> dict | None:
    with closing(_open()) as connection, connection:
        row = connection.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    return _row(row) if row else None


def create_contract(payload: dict) -> dict:
    contract = normalize_contract(payload)
    with closing(_open()) as connection, connection:
        contract_id = _write(connection, contract, None)
        row = connection.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    return _row(row)


def update_contract(contract_id: int, payload: dict) -> dict | None:
    with closing(_open()) as connection, connection:
        row = connection.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
        if row is None:
            return None
        contract = normalize_contract(payload, _row(row))
        _write(connection, contract, contract_id)
        row = connection.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    return _row(row)


def delete_contract(contract_id: int) -> bool:
    with closing(_open()) as connection, connection:
        cursor = connection.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
    return cursor.rowcount > 0


# -- Khach hang (gop theo cong ty) ----------------------------------------------


def _customer_key(contract: dict) -> str:
    return (contract.get("domain") or contract["company_name"].strip().lower())


def grade_customer(total_value: int, contract_count: int) -> str:
    for grade, min_value, min_count in GRADE_RULES:
        if total_value >= min_value and contract_count >= min_count:
            return grade
    return "C"


def list_customers() -> list[dict]:
    """Moi cong ty mot dong: tong gia tri, so hop dong, hop dong dang chay, sap het han, hang."""
    groups: dict[str, list[dict]] = {}
    for contract in list_contracts():
        groups.setdefault(_customer_key(contract), []).append(contract)

    today = date.today()
    customers = []
    for key, contracts in groups.items():
        contracts.sort(key=lambda c: (c.get("start_date") or c.get("signed_date") or ""), reverse=True)
        latest = contracts[0]
        active = [c for c in contracts if c["status"] == "active"]
        total = sum(c["amount"] or 0 for c in contracts if c["status"] != "terminated")
        active_value = sum(c["amount"] or 0 for c in active)
        expiring = [c for c in active if c["expiring"]]
        next_end = min((c["end_date"] for c in active if c.get("end_date")), default=None)
        last_end = max((c["end_date"] for c in contracts if c.get("end_date")), default=None)
        dormant_days = None
        if not active and last_end:
            dormant_days = (today - date.fromisoformat(last_end)).days
        ratings = [c["satisfaction"] for c in contracts if c.get("satisfaction")]
        first_signed = min((c["signed_date"] for c in contracts if c.get("signed_date")), default=None)
        customers.append({
            "key": key,
            "domain": latest.get("domain"),
            "company_name": latest["company_name"],
            "website": latest.get("website"),
            "biz_number": next((c["biz_number"] for c in contracts if c.get("biz_number")), None),
            "company_id": next((c["company_id"] for c in contracts if c.get("company_id")), None),
            "contact_name": latest.get("contact_name"),
            "rank": latest.get("rank"),
            "phone": latest.get("phone"),
            "email": latest.get("email"),
            "our_pm": latest.get("our_pm"),
            "grade": grade_customer(total, len([c for c in contracts if c["status"] != "terminated"])),
            "total_value": total,
            "active_value": active_value,
            "contract_count": len(contracts),
            "active_count": len(active),
            "renewed_count": len([c for c in contracts if c["status"] == "renewed"]),
            "first_signed": first_signed,
            "last_end": last_end,
            "next_end": next_end,
            "expiring_count": len(expiring),
            "dormant_days": dormant_days,
            "satisfaction": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "project_types": sorted({c["project_type"] for c in contracts if c.get("project_type")}),
            "tech": sorted({item for c in contracts for item in (c.get("tech") or [])})[:8],
            "contracts": contracts,
        })
    customers.sort(key=lambda c: (-c["total_value"], c["company_name"]))
    return customers


def summary() -> dict:
    contracts = list_contracts()
    year = str(date.today().year)
    active = [c for c in contracts if c["status"] == "active"]
    expiring = [c for c in active if c["expiring"]]
    return {
        "total_value": sum(c["amount"] or 0 for c in contracts if c["status"] != "terminated"),
        "active_value": sum(c["amount"] or 0 for c in active),
        "active_count": len(active),
        "year_value": sum(c["amount"] or 0 for c in contracts if (c.get("signed_date") or "").startswith(year) and c["status"] != "terminated"),
        "year_count": len([c for c in contracts if (c.get("signed_date") or "").startswith(year) and c["status"] != "terminated"]),
        "expiring_count": len(expiring),
        "expiring_value": sum(c["amount"] or 0 for c in expiring),
        "customer_count": len({_customer_key(c) for c in contracts}),
    }


# -- Lien ket voi CRM / scanner -------------------------------------------------


def contract_from_lead(lead: dict) -> dict:
    """Hop dong dien san tu lead vua 수주: cong ty, nguoi lien he, ngan sach, so nguoi, thang bat dau."""
    start = None
    if lead.get("expected_start"):
        start = lead["expected_start"] + "-01"
    return {
        "lead_id": lead.get("id"),
        "company_id": lead.get("company_id"),
        "domain": lead.get("domain"),
        "company_name": lead.get("company_name"),
        "website": lead.get("website"),
        "biz_number": lead.get("biz_number"),
        "project_type": lead.get("project_type"),
        "amount": lead.get("budget"),
        "team_size": lead.get("team_size"),
        "start_date": start,
        "contact_name": lead.get("contact_name"),
        "rank": lead.get("rank"),
        "department": lead.get("department"),
        "phone": lead.get("mobile") or lead.get("phone"),
        "email": lead.get("email"),
        "our_pm": lead.get("assignee"),
        "tech": lead.get("tech") or [],
        "memo": lead.get("memo"),
    }


def resell_lead_from_customer(customer: dict) -> dict:
    """Lead 재계약/업셀 tao tu khach hang da ky: nguon 'customer', ghi ro lich su hop dong."""
    latest = customer["contracts"][0] if customer.get("contracts") else {}
    history = "; ".join(
        f"{c.get('title') or c.get('project_type') or '계약'} {c.get('start_date') or ''}~{c.get('end_date') or ''} ₩{(c.get('amount') or 0):,}"
        for c in customer.get("contracts", [])[:5]
    )
    return {
        "company_id": customer.get("company_id"),
        "domain": customer.get("domain"),
        "company_name": customer["company_name"],
        "website": customer.get("website"),
        "biz_number": customer.get("biz_number"),
        "contact_name": customer.get("contact_name"),
        "rank": customer.get("rank"),
        "phone": customer.get("phone"),
        "email": customer.get("email"),
        "source": "customer",
        "project_type": latest.get("project_type"),
        "tech": customer.get("tech") or [],
        "budget": latest.get("amount"),
        "team_size": latest.get("team_size"),
        "assignee": customer.get("our_pm"),
        "status": "contacted",
        "next_action": "재계약 / 추가 인력 제안",
        "memo": f"기존 고객 (등급 {customer.get('grade')}, 누적 ₩{customer.get('total_value', 0):,}). 계약 이력: {history}",
    }


def calendar_events() -> list[dict]:
    """Ngay het han hop dong dang chay, cho file .ics chung voi CRM."""
    events = []
    for contract in list_contracts():
        if contract["status"] != "active" or not contract.get("end_date"):
            continue
        notice = contract.get("renewal_notice_days") or RENEWAL_NOTICE_DAYS
        remind = (date.fromisoformat(contract["end_date"]) - timedelta(days=notice)).isoformat()
        events.append({
            "uid": f"contract-{contract['id']}-notice",
            "date": remind,
            "summary": f"[계약 만료 {notice}일 전] {contract['company_name']} — 재계약 제안",
            "description": f"{contract.get('title') or ''}\n만료 {contract['end_date']} · ₩{(contract['amount'] or 0):,}\n{contract.get('contact_name') or ''} {contract.get('phone') or ''} {contract.get('email') or ''}".strip(),
        })
        events.append({
            "uid": f"contract-{contract['id']}-end",
            "date": contract["end_date"],
            "summary": f"[계약 만료] {contract['company_name']}",
            "description": contract.get("title") or "",
        })
    return events
