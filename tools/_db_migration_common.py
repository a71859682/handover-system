from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SEED_PATH = BASE_DIR / "seeds" / "default_seed.json"
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


@dataclass
class SQLiteSource:
    path: Path
    is_temporary_seeded: bool = False


def resolve_sqlite_source_path() -> Path | None:
    source = os.environ.get("APP_SQLITE_SOURCE_PATH")
    if source:
        return Path(source).expanduser().resolve()

    default_path = (BASE_DIR / "site.db").resolve()
    if default_path.exists():
        return default_path
    return None


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


def _restore_environment_variable(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


@contextmanager
def temporary_seeded_sqlite_source():
    if not SEED_PATH.exists():
        raise SystemExit(f"Seed file not found: {SEED_PATH}")

    original_app_db_path = os.environ.get("APP_DB_PATH")
    original_database_url = os.environ.get("DATABASE_URL")
    had_app_module = "app" in sys.modules
    app_module = sys.modules.get("app")

    temp_dir = Path(tempfile.mkdtemp(prefix="sqlite-seeded-source-"))
    temp_db_path = temp_dir / "site.db"
    try:
        os.environ["APP_DB_PATH"] = str(temp_db_path)
        os.environ.pop("DATABASE_URL", None)

        if app_module is None:
            app_module = importlib.import_module("app")
        app_module = importlib.reload(app_module)
        app_module.bootstrap()

        yield SQLiteSource(path=temp_db_path, is_temporary_seeded=True)
    finally:
        _restore_environment_variable("APP_DB_PATH", original_app_db_path)
        _restore_environment_variable("DATABASE_URL", original_database_url)

        if had_app_module and app_module is not None:
            importlib.reload(app_module)
        else:
            sys.modules.pop("app", None)


@contextmanager
def resolved_sqlite_source():
    path = resolve_sqlite_source_path()
    if path is not None:
        yield SQLiteSource(path=path, is_temporary_seeded=False)
        return

    with temporary_seeded_sqlite_source() as temporary_source:
        yield temporary_source


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
