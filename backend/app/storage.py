"""Luu ket qua scan vao SQLite.

Mot cong ty = mot dong, khoa theo domain: quet lai cung website thi cap nhat
dong cu chu khong tao ban trung. Toan bo ket qua scan duoc giu nguyen trong
`result_json` de mo lai xem chi tiet ma khong phai quet lai.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .crawler import registrable_domain

DB_PATH = Path(os.environ.get("SCANNER_DB") or (Path(__file__).resolve().parents[2] / "data" / "companies.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    domain      TEXT    NOT NULL UNIQUE,
    name        TEXT,
    address     TEXT,
    phone       TEXT,
    email       TEXT,
    industry    TEXT,
    website     TEXT,
    it_hiring   TEXT    NOT NULL DEFAULT 'None',
    it_jobs     INTEGER NOT NULL DEFAULT 0,
    contacts    INTEGER NOT NULL DEFAULT 0,
    result_json TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""


# Cot them vao sau khi da co DB dang chay: ten -> kieu.
MIGRATIONS = {
    "email": "TEXT",
}


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Tao bang neu chua co, roi them cac cot moi vao DB da ton tai."""
    connection.executescript(SCHEMA)
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(companies)")}
    for column, column_type in MIGRATIONS.items():
        if column not in existing:
            connection.execute(f"ALTER TABLE companies ADD COLUMN {column} {column_type}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    """Mo ket noi moi. Luon dung kem `closing()`: `with sqlite3.connect(...)`
    chi commit chu khong dong connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_db() -> None:
    with closing(connect()) as connection, connection:
        _ensure_schema(connection)


def _domain_of(result: dict) -> str:
    company = result.get("company") or {}
    for candidate in (company.get("website"), result.get("scanned_url")):
        host = urlsplit(candidate or "").hostname
        if host:
            return registrable_domain(host)
    return ""


def _summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "domain": row["domain"],
        "name": row["name"],
        "address": row["address"],
        "phone": row["phone"],
        "email": row["email"],
        "industry": row["industry"],
        "website": row["website"],
        "it_hiring": row["it_hiring"],
        "it_jobs": row["it_jobs"],
        "contacts": row["contacts"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_result(result: dict) -> dict:
    """Them moi hoac cap nhat cong ty theo domain. Tra ve ban tom tat."""
    domain = _domain_of(result)
    if not domain:
        raise ValueError("Ket qua scan khong co domain hop le.")

    company = result.get("company") or {}
    signal = (result.get("sales_signal") or {}).get("it_hiring") or "None"
    jobs = len(result.get("it_recruitment") or [])
    contacts = len(result.get("key_contacts") or [])
    now = _now()

    with closing(connect()) as connection, connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO companies (domain, name, address, phone, email, industry, website,
                                   it_hiring, it_jobs, contacts, result_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                name = excluded.name,
                address = excluded.address,
                phone = excluded.phone,
                email = excluded.email,
                industry = excluded.industry,
                website = excluded.website,
                it_hiring = excluded.it_hiring,
                it_jobs = excluded.it_jobs,
                contacts = excluded.contacts,
                result_json = excluded.result_json,
                updated_at = excluded.updated_at
            """,
            (
                domain,
                company.get("name"),
                company.get("address"),
                company.get("phone"),
                company.get("email"),
                company.get("industry"),
                company.get("website"),
                signal,
                jobs,
                contacts,
                json.dumps(result, ensure_ascii=False),
                now,
                now,
            ),
        )
        row = connection.execute("SELECT * FROM companies WHERE domain = ?", (domain,)).fetchone()
    return _summary(row)


def list_companies(include_results: bool = False) -> list[dict]:
    """Danh sach tom tat. `include_results` kem theo ca ket qua scan day du,
    dung khi xuat file tu trang "Cong ty da luu"."""
    with closing(connect()) as connection, connection:
        _ensure_schema(connection)
        rows = connection.execute("SELECT * FROM companies ORDER BY updated_at DESC, id DESC").fetchall()

    companies = []
    for row in rows:
        summary = _summary(row)
        if include_results:
            try:
                summary["result"] = json.loads(row["result_json"])
            except json.JSONDecodeError:
                summary["result"] = None
        companies.append(summary)
    return companies


def get_company(company_id: int) -> dict | None:
    """Tra ve ban tom tat kem toan bo ket qua scan da luu."""
    with closing(connect()) as connection, connection:
        _ensure_schema(connection)
        row = connection.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    if row is None:
        return None
    summary = _summary(row)
    try:
        summary["result"] = json.loads(row["result_json"])
    except json.JSONDecodeError:
        summary["result"] = None
    return summary


def delete_company(company_id: int) -> bool:
    with closing(connect()) as connection, connection:
        _ensure_schema(connection)
        cursor = connection.execute("DELETE FROM companies WHERE id = ?", (company_id,))
    return cursor.rowcount > 0
