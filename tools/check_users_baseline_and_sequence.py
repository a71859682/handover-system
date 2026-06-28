from __future__ import annotations

import argparse
import os

from psycopg import sql

from check_users_secondary_update import (
    connect_postgres,
    connect_sqlite,
    redact_database_url,
    resolve_sqlite_source_path,
)


USER_COLUMNS = ("id", "username", "display_name", "role", "created_at")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare users baseline rows and inspect PostgreSQL users.id sequence health."
    )
    return parser.parse_args()


def fetch_sqlite_users(sqlite_path):
    with connect_sqlite(sqlite_path) as sqlite_conn:
        rows = sqlite_conn.execute(
            """
            SELECT id, username, display_name, role, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()
    return {
        row["id"]: {column: row[column] for column in USER_COLUMNS}
        for row in rows
    }


def fetch_postgres_users(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, username, display_name, role, created_at
            FROM users
            ORDER BY id
            """
        )
        rows = cur.fetchall()
    return {
        row[0]: dict(zip(USER_COLUMNS, row, strict=False))
        for row in rows
    }


def print_baseline_report(sqlite_rows, postgres_rows) -> bool:
    has_failure = False
    common_ids = sorted(set(sqlite_rows) & set(postgres_rows))
    only_in_sqlite = sorted(set(sqlite_rows) - set(postgres_rows))
    only_in_postgres = sorted(set(postgres_rows) - set(sqlite_rows))

    print("Users baseline report:")
    print(f"- common row count: {len(common_ids)}")
    print(f"- only_in_sqlite count: {len(only_in_sqlite)}")
    print(f"- only_in_postgres count: {len(only_in_postgres)}")

    if common_ids:
        print("common row:")
        for user_id in common_ids:
            sqlite_row = sqlite_rows[user_id]
            postgres_row = postgres_rows[user_id]
            mismatches = [
                field
                for field in USER_COLUMNS[1:]
                if sqlite_row[field] != postgres_row[field]
            ]
            if mismatches:
                has_failure = True
                print(
                    f"FIELD_MISMATCH users id={user_id}: username={sqlite_row['username']!r} "
                    f"fields={', '.join(mismatches)}"
                )
                for field in mismatches:
                    print(
                        f"  sqlite.{field}={sqlite_row[field]!r} "
                        f"postgres.{field}={postgres_row[field]!r}"
                    )
            else:
                print(
                    f"COMMON users id={user_id}: username={sqlite_row['username']!r} "
                    "status=match"
                )
    else:
        print("common row:")
        print("  none")

    print("only_in_sqlite:")
    if only_in_sqlite:
        for user_id in only_in_sqlite:
            row = sqlite_rows[user_id]
            print(
                f"  users id={user_id}: username={row['username']!r} "
                f"display_name={row['display_name']!r} role={row['role']!r} created_at={row['created_at']!r}"
            )
    else:
        print("  none")

    print("only_in_postgres:")
    if only_in_postgres:
        for user_id in only_in_postgres:
            row = postgres_rows[user_id]
            print(
                f"  users id={user_id}: username={row['username']!r} "
                f"display_name={row['display_name']!r} role={row['role']!r} created_at={row['created_at']!r}"
            )
    else:
        print("  none")

    return has_failure


def fetch_sequence_report(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM users")
        max_user_id = cur.fetchone()[0]

        cur.execute("SELECT pg_get_serial_sequence('users', 'id')")
        sequence_name = cur.fetchone()[0]

        if not sequence_name:
            return {
                "max_user_id": max_user_id,
                "sequence_name": None,
                "status": "unknown",
                "reason": "sequence_not_found",
            }

        sequence_regclass = sequence_name.split(".", 1)[1] if "." in sequence_name else sequence_name
        schema_name = sequence_name.split(".", 1)[0] if "." in sequence_name else "public"

        cur.execute(
            """
            SELECT increment_by
            FROM pg_sequences
            WHERE schemaname = %s AND sequencename = %s
            """,
            (schema_name, sequence_regclass),
        )
        increment_row = cur.fetchone()
        increment_by = increment_row[0] if increment_row else 1

        sequence_query = sql.SQL("SELECT last_value, is_called FROM {}").format(
            sql.SQL(sequence_name)
        )
        cur.execute(sequence_query)
        last_value, is_called = cur.fetchone()

    next_insert_id = last_value + increment_by if is_called else last_value
    if next_insert_id <= max_user_id:
        status = "risk"
        reason = "next_insert_id_not_ahead_of_max_id"
    else:
        status = "ok"
        reason = "next_insert_id_ahead_of_max_id"

    return {
        "max_user_id": max_user_id,
        "sequence_name": sequence_name,
        "last_value": last_value,
        "is_called": is_called,
        "increment_by": increment_by,
        "next_insert_id": next_insert_id,
        "status": status,
        "reason": reason,
    }


def print_sequence_report(report) -> bool:
    print("PostgreSQL users.id sequence report:")
    print(f"- max_user_id: {report['max_user_id']}")
    print(f"- sequence_name: {report['sequence_name']!r}")

    if report["sequence_name"] is None:
        print(f"- status: {report['status']}")
        print(f"- reason: {report['reason']}")
        return True

    print(f"- last_value: {report['last_value']}")
    print(f"- is_called: {report['is_called']}")
    print(f"- increment_by: {report['increment_by']}")
    print(f"- next_insert_id: {report['next_insert_id']}")
    print(f"- status: {report['status']}")
    print(f"- reason: {report['reason']}")
    return report["status"] != "ok"


def main() -> int:
    parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is not configured.")
        print("PASS")
        return 0

    sqlite_path = resolve_sqlite_source_path()
    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    sqlite_rows = fetch_sqlite_users(sqlite_path)
    with connect_postgres(database_url) as pg_conn:
        postgres_rows = fetch_postgres_users(pg_conn)
        sequence_report = fetch_sequence_report(pg_conn)

    has_baseline_failure = print_baseline_report(sqlite_rows, postgres_rows)
    has_sequence_failure = print_sequence_report(sequence_report)

    if has_baseline_failure or has_sequence_failure:
        print("FAIL users baseline / sequence check found actionable issues.")
        return 1

    print("PASS users baseline / sequence check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
