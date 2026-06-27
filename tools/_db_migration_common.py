from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg


BASE_DIR = Path(__file__).resolve().parents[1]
TABLE_ORDER = [
    "meta",
    "users",
    "sheets",
    "tasks",
    "floors",
    "units",
    "progress",
    "unit_extra",
    "extra_fields",
    "unit_extra_values",
]
REVERSE_DELETE_ORDER = list(reversed(TABLE_ORDER))
PRIMARY_KEYS = {
    "meta": ("key",),
    "users": ("id",),
    "sheets": ("id",),
    "tasks": ("id",),
    "floors": ("id",),
    "units": ("id",),
    "progress": ("unit_id", "task_id"),
    "unit_extra": ("unit_id",),
    "extra_fields": ("id",),
    "unit_extra_values": ("unit_id", "field_key"),
}
SEQUENCE_TABLES = ("users", "sheets", "tasks", "floors", "units", "extra_fields")


def resolve_sqlite_source_path() -> Path:
    source = os.environ.get("APP_SQLITE_SOURCE_PATH")
    if source:
        return Path(source).expanduser().resolve()
    return (BASE_DIR / "site.db").resolve()


def require_postgres_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")

    scheme = urlsplit(database_url).scheme.lower()
    if scheme not in {"postgresql", "postgres"}:
        raise SystemExit(f"DATABASE_URL must point to PostgreSQL, got scheme '{scheme or 'missing'}'.")
    return database_url


def redact_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    hostname = parts.hostname or ""
    if parts.port:
        hostname = f"{hostname}:{parts.port}"
    if parts.username:
        netloc = f"{parts.username}:***@{hostname}"
    else:
        netloc = hostname
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def connect_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise SystemExit(f"SQLite source not found: {path}")

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_postgres(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def fetch_sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise SystemExit(f"SQLite table not found or has no columns: {table}")
    return [row["name"] for row in rows]


def fetch_sqlite_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLE_ORDER}


def fetch_postgres_counts(conn: psycopg.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in TABLE_ORDER:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    return counts
