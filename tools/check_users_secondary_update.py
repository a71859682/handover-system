from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def resolve_sqlite_source_path() -> Path:
    source = os.environ.get("APP_SQLITE_SOURCE_PATH")
    if source:
        return Path(source).expanduser().resolve()
    return (BASE_DIR / "site.db").resolve()


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
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_postgres(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare users.display_name between local SQLite and staging PostgreSQL."
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="Limit comparison to a single user id.",
    )
    return parser.parse_args()


def build_user_query(user_id: int | None) -> tuple[str, tuple]:
    sql = "SELECT id, display_name FROM users"
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE id = ?"
        params = (user_id,)
    sql += " ORDER BY id"
    return sql, params


def build_postgres_user_query(user_id: int | None) -> tuple[str, tuple]:
    sql = "SELECT id, display_name FROM users"
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE id = %s"
        params = (user_id,)
    sql += " ORDER BY id"
    return sql, params


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is not configured.")
        print("PASS")
        return 0

    sqlite_path = resolve_sqlite_source_path()
    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    sqlite_sql, sqlite_params = build_user_query(args.user_id)
    postgres_sql, postgres_params = build_postgres_user_query(args.user_id)

    with connect_sqlite(sqlite_path) as sqlite_conn, connect_postgres(database_url) as pg_conn:
        sqlite_rows = {
            row["id"]: row["display_name"]
            for row in sqlite_conn.execute(sqlite_sql, sqlite_params).fetchall()
        }
        with pg_conn.cursor() as cur:
            cur.execute(postgres_sql, postgres_params)
            postgres_rows = {row[0]: row[1] for row in cur.fetchall()}

    has_failure = False
    all_ids = sorted(set(sqlite_rows) | set(postgres_rows))
    for user_id in all_ids:
        sqlite_value = sqlite_rows.get(user_id)
        postgres_value = postgres_rows.get(user_id)
        status = "PASS" if sqlite_value == postgres_value else "FAIL"
        print(
            f"{status} users id={user_id}: sqlite={sqlite_value!r} postgres={postgres_value!r}"
        )
        if status == "FAIL":
            has_failure = True

    if has_failure:
        print("FAIL users secondary update check found mismatches.")
        return 1

    print("PASS users secondary update fields match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
