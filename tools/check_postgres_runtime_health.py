from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import DATABASE_URL


TABLES = (
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
)


def require_postgres_database_url() -> str:
    database_url = DATABASE_URL.strip()
    if not database_url:
        raise SystemExit("FAIL DATABASE_URL is not set.")

    scheme = urlsplit(database_url).scheme.lower()
    if scheme not in {"postgresql", "postgres", "postgresql+psycopg"}:
        raise SystemExit(f"FAIL DATABASE_URL must point to PostgreSQL, got scheme '{scheme or 'missing'}'.")
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


def connect_postgres(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def fetch_table_existence_and_counts(pg_conn: psycopg.Connection) -> tuple[list[str], dict[str, int]]:
    missing: list[str] = []
    counts: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        for table in TABLES:
            cur.execute("SELECT to_regclass(%s)", (table,))
            exists = cur.fetchone()[0]
            if exists is None:
                missing.append(table)
                continue
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            counts[table] = cur.fetchone()[0]
    return missing, counts


def run_representative_orm_queries() -> list[str]:
    import app as app_module
    from models import Meta, Progress, Sheet, User

    checks: list[str] = []
    with app_module.app.app_context():
        checks.append(f"Meta.first={bool(Meta.query.order_by(Meta.key).first())}")
        checks.append(f"User.admin={bool(User.query.filter_by(username='admin').first())}")
        checks.append(f"Sheet.first={bool(Sheet.query.order_by(Sheet.sort_order, Sheet.id).first())}")
        checks.append(f"Progress.first={bool(Progress.query.order_by(Progress.unit_id, Progress.task_id).first())}")
    return checks


def main() -> int:
    database_url = require_postgres_database_url()
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    try:
        with connect_postgres(database_url) as pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT 1")
                select_one = cur.fetchone()[0]
            missing_tables, counts = fetch_table_existence_and_counts(pg_conn)
    except Exception as exc:
        print(f"FAIL PostgreSQL connection/query error: {exc}")
        return 1

    if select_one != 1:
        print(f"FAIL SELECT 1 returned unexpected value: {select_one!r}")
        return 1

    if missing_tables:
        print("FAIL Missing required tables:")
        for table in missing_tables:
            print(f"- {table}")
        return 1

    try:
        orm_checks = run_representative_orm_queries()
    except Exception as exc:
        print(f"FAIL ORM query error: {exc}")
        return 1

    print("PostgreSQL row counts:")
    for table in TABLES:
        print(f"- {table}: {counts[table]}")

    print("Representative checks:")
    print("- SELECT 1=1")
    for check in orm_checks:
        print(f"- {check}")

    print("PASS PostgreSQL runtime health check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
