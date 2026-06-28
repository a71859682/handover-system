from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from check_users_baseline_and_sequence import (  # noqa: E402
    fetch_postgres_users,
    fetch_sqlite_users,
)
from check_users_create_readiness import (  # noqa: E402
    build_next_sqlite_collision_report,
)
from check_users_secondary_update import (  # noqa: E402
    connect_postgres,
    connect_sqlite,
    redact_database_url,
    resolve_sqlite_source_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect SQLite and PostgreSQL users id allocation without modifying data."
    )
    return parser.parse_args()


def fetch_sqlite_users_schema(sqlite_path: Path) -> dict[str, object]:
    sqlite_conn = connect_sqlite(sqlite_path)
    try:
        create_sql_row = sqlite_conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        create_sql = create_sql_row["sql"] if create_sql_row else None
        has_autoincrement = bool(create_sql and "AUTOINCREMENT" in create_sql.upper())

        sqlite_sequence_exists = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
        ).fetchone() is not None

        sqlite_sequence_value = None
        if sqlite_sequence_exists:
            sequence_row = sqlite_conn.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'users'"
            ).fetchone()
            sqlite_sequence_value = sequence_row["seq"] if sequence_row else None

        count_row = sqlite_conn.execute(
            "SELECT COUNT(*) AS user_count, COALESCE(MAX(id), 0) AS max_user_id FROM users"
        ).fetchone()
        user_count = int(count_row["user_count"])
        max_user_id = int(count_row["max_user_id"])

        if has_autoincrement and sqlite_sequence_value is not None:
            next_sqlite_user_id = max(max_user_id, int(sqlite_sequence_value)) + 1
        else:
            next_sqlite_user_id = max_user_id + 1

        return {
            "create_sql": create_sql,
            "has_autoincrement": has_autoincrement,
            "sqlite_sequence_exists": sqlite_sequence_exists,
            "sqlite_sequence_value": sqlite_sequence_value,
            "user_count": user_count,
            "max_user_id": max_user_id,
            "next_sqlite_user_id": next_sqlite_user_id,
        }
    finally:
        sqlite_conn.close()


def print_sqlite_report(report: dict[str, object], sqlite_rows: dict[int, dict[str, object]]) -> None:
    print("SQLite users id allocation:")
    print(f"- user_count: {report['user_count']}")
    print(f"- max_user_id: {report['max_user_id']}")
    print(f"- has_autoincrement: {str(report['has_autoincrement']).lower()}")
    print(f"- sqlite_sequence_exists: {str(report['sqlite_sequence_exists']).lower()}")
    print(f"- sqlite_sequence_value: {report['sqlite_sequence_value']}")
    print(f"- next_sqlite_user_id: {report['next_sqlite_user_id']}")
    print("- users_schema_sql:")
    print(f"  {report['create_sql']}")
    print("- existing_users:")
    if sqlite_rows:
        for user_id, row in sqlite_rows.items():
            print(f"  id={user_id} username={row['username']!r}")
    else:
        print("  none")


def print_postgres_report(postgres_rows: dict[int, dict[str, object]]) -> None:
    max_user_id = max(postgres_rows, default=0)
    print("PostgreSQL users id allocation:")
    print(f"- user_count: {len(postgres_rows)}")
    print(f"- max_user_id: {max_user_id}")
    print("- existing_users:")
    if postgres_rows:
        for user_id in sorted(postgres_rows):
            row = postgres_rows[user_id]
            print(f"  id={user_id} username={row['username']!r}")
    else:
        print("  none")


def print_collision_report(report: dict[str, object]) -> bool:
    print("Cross-database next-id collision:")
    print(f"- next_sqlite_user_id: {report['next_sqlite_user_id']}")
    print(f"- collision: {str(report['status'] != 'ok').lower()}")
    print(f"- reason: {report['reason']}")
    postgres_collision = report["postgres_collision"]
    if postgres_collision:
        print(
            f"- postgres_existing_user: id={postgres_collision['id']} "
            f"username={postgres_collision['username']!r}"
        )
        return True
    print("- postgres_existing_user: none")
    return False


def main() -> int:
    parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    sqlite_path = resolve_sqlite_source_path()
    sqlite_report = fetch_sqlite_users_schema(sqlite_path)
    sqlite_rows = fetch_sqlite_users(sqlite_path)

    print(f"SQLite source: {sqlite_path}")
    print_sqlite_report(sqlite_report, sqlite_rows)

    if not database_url:
        print("DATABASE_URL is not configured.")
        print("PASS users id allocation inspection skipped PostgreSQL checks without DATABASE_URL.")
        return 0

    print(f"PostgreSQL target: {redact_database_url(database_url)}")
    with connect_postgres(database_url) as pg_conn:
        postgres_rows = fetch_postgres_users(pg_conn)

    print_postgres_report(postgres_rows)
    collision_report = build_next_sqlite_collision_report(
        int(sqlite_report["next_sqlite_user_id"]),
        postgres_rows,
    )
    print_collision_report(collision_report)
    print("PASS users id allocation inspection completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
