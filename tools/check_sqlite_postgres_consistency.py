from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


TABLE_SPECS = {
    "meta": {
        "key": ("key",),
        "fields": ("value",),
        "timestamps": (),
    },
    "users": {
        "key": ("id",),
        "fields": ("username", "display_name", "role", "created_at"),
        "timestamps": ("created_at",),
    },
    "sheets": {
        "key": ("id",),
        "fields": ("name", "sort_order", "created_at"),
        "timestamps": ("created_at",),
    },
    "tasks": {
        "key": ("id",),
        "fields": ("sheet_id", "col_index", "vendor", "location", "name"),
        "timestamps": (),
    },
    "floors": {
        "key": ("id",),
        "fields": ("sheet_id", "sort_order", "name", "block_name", "unit_count"),
        "timestamps": (),
    },
    "units": {
        "key": ("id",),
        "fields": ("floor_id", "sort_order", "name"),
        "timestamps": (),
    },
    "progress": {
        "key": ("unit_id", "task_id"),
        "fields": ("value", "updated_by", "updated_at"),
        "timestamps": ("updated_at",),
    },
    "unit_extra": {
        "key": ("unit_id",),
        "fields": ("initial_check", "recheck_1", "recheck_2", "handover", "updated_by", "updated_at"),
        "timestamps": ("updated_at",),
    },
    "extra_fields": {
        "key": ("id",),
        "fields": ("sheet_id", "field_key", "name", "field_type", "sort_order", "is_builtin", "active"),
        "timestamps": (),
    },
    "unit_extra_values": {
        "key": ("unit_id", "field_key"),
        "fields": ("value", "updated_by", "updated_at"),
        "timestamps": ("updated_at",),
    },
}


def resolve_sqlite_path() -> Path:
    configured = os.environ.get("APP_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (BASE_DIR / "site.db").resolve()


def require_postgres_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")

    scheme = urlsplit(database_url).scheme.lower()
    if scheme not in {"postgresql", "postgres", "postgresql+psycopg"}:
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


def fetch_sqlite_rows(conn: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> list[dict[str, object]]:
    spec = TABLE_SPECS[table]
    order_by = ", ".join(spec["key"])
    rows = conn.execute(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order_by}"
    ).fetchall()
    return [{column: row[column] for column in columns} for row in rows]


def fetch_postgres_rows(pg_conn: psycopg.Connection, table: str, columns: tuple[str, ...]) -> list[dict[str, object]]:
    spec = TABLE_SPECS[table]
    query = sql.SQL("SELECT {columns} FROM {table} ORDER BY {order_by}").format(
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        table=sql.Identifier(table),
        order_by=sql.SQL(", ").join(sql.Identifier(column) for column in spec["key"]),
    )
    with pg_conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return [dict(zip(columns, row, strict=False)) for row in rows]


def row_key(table: str, row: dict[str, object]) -> tuple[object, ...]:
    return tuple(row[column] for column in TABLE_SPECS[table]["key"])


def latest_timestamp(rows: list[dict[str, object]], timestamp_fields: tuple[str, ...]) -> dict[str, object]:
    summary: dict[str, object] = {}
    for field in timestamp_fields:
        values = [row[field] for row in rows if row.get(field) not in (None, "")]
        summary[field] = max(values) if values else None
    return summary


def compare_table(
    table: str,
    sqlite_rows: list[dict[str, object]],
    postgres_rows: list[dict[str, object]],
) -> list[str]:
    spec = TABLE_SPECS[table]
    differences: list[str] = []

    if len(sqlite_rows) != len(postgres_rows):
        differences.append(
            f"{table} key=(count) field=count sqlite={len(sqlite_rows)!r} postgres={len(postgres_rows)!r}"
        )

    sqlite_map = {row_key(table, row): row for row in sqlite_rows}
    postgres_map = {row_key(table, row): row for row in postgres_rows}

    for key in sorted(set(sqlite_map) | set(postgres_map)):
        sqlite_row = sqlite_map.get(key)
        postgres_row = postgres_map.get(key)
        if sqlite_row is None:
            differences.append(f"{table} key={key} field=row sqlite=None postgres={postgres_row!r}")
            continue
        if postgres_row is None:
            differences.append(f"{table} key={key} field=row sqlite={sqlite_row!r} postgres=None")
            continue

        for field in spec["fields"]:
            if sqlite_row.get(field) != postgres_row.get(field):
                differences.append(
                    f"{table} key={key} field={field} sqlite={sqlite_row.get(field)!r} postgres={postgres_row.get(field)!r}"
                )

    sqlite_latest = latest_timestamp(sqlite_rows, spec["timestamps"])
    postgres_latest = latest_timestamp(postgres_rows, spec["timestamps"])
    for field in spec["timestamps"]:
        if sqlite_latest[field] != postgres_latest[field]:
            differences.append(
                f"{table} key=(latest) field={field} sqlite={sqlite_latest[field]!r} postgres={postgres_latest[field]!r}"
            )

    return differences


def main() -> int:
    sqlite_path = resolve_sqlite_path()
    database_url = require_postgres_database_url()

    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    has_failure = False
    with connect_sqlite(sqlite_path) as sqlite_conn, connect_postgres(database_url) as pg_conn:
        for table, spec in TABLE_SPECS.items():
            columns = spec["key"] + spec["fields"]
            sqlite_rows = fetch_sqlite_rows(sqlite_conn, table, columns)
            postgres_rows = fetch_postgres_rows(pg_conn, table, columns)
            differences = compare_table(table, sqlite_rows, postgres_rows)

            if differences:
                has_failure = True
                print(f"FAIL {table}")
                for difference in differences:
                    print(f"  {difference}")
            else:
                print(f"PASS {table}")

    if has_failure:
        print("FAIL SQLite/PostgreSQL consistency check found differences.")
        return 1

    print("PASS SQLite/PostgreSQL consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
