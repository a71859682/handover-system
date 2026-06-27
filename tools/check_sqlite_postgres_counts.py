from __future__ import annotations

import argparse

from _db_migration_common import (
    TABLE_ORDER,
    connect_postgres,
    connect_sqlite,
    fetch_postgres_counts,
    fetch_sqlite_counts,
    redact_database_url,
    require_postgres_database_url,
    resolve_sqlite_source_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare row counts between local SQLite and staging PostgreSQL."
    )
    return parser.parse_args()


def main() -> int:
    parse_args()
    sqlite_path = resolve_sqlite_source_path()
    database_url = require_postgres_database_url()

    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    with connect_sqlite(sqlite_path) as sqlite_conn, connect_postgres(database_url) as pg_conn:
        sqlite_counts = fetch_sqlite_counts(sqlite_conn)
        postgres_counts = fetch_postgres_counts(pg_conn)

    has_failure = False
    for table in TABLE_ORDER:
        sqlite_count = sqlite_counts[table]
        postgres_count = postgres_counts[table]
        status = "PASS" if sqlite_count == postgres_count else "FAIL"
        print(f"{status} {table}: sqlite={sqlite_count} postgres={postgres_count}")
        if status == "FAIL":
            has_failure = True

    if has_failure:
        print("FAIL SQLite/PostgreSQL row counts do not match.")
        return 1

    print("PASS SQLite/PostgreSQL row counts match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
