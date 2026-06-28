from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from check_users_baseline_and_sequence import fetch_postgres_users, fetch_sqlite_users  # noqa: E402
from check_users_id_allocation import fetch_sqlite_users_schema  # noqa: E402
from check_users_secondary_update import (  # noqa: E402
    connect_postgres,
    connect_sqlite,
    redact_database_url,
    resolve_sqlite_source_path,
)
from plan_users_sqlite_sequence_bump import build_sequence_bump_plan  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or apply a controlled SQLite users sqlite_sequence bump."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the SQLite users sqlite_sequence bump. Defaults to dry-run only.",
    )
    return parser.parse_args()


def validate_apply_preconditions(
    sqlite_report: dict[str, object],
    postgres_rows: dict[int, dict[str, object]],
    bump_plan: dict[str, object],
) -> list[str]:
    failures: list[str] = []

    if not sqlite_report["has_autoincrement"]:
        failures.append("users_table_not_autoincrement")
    if not sqlite_report["sqlite_sequence_exists"]:
        failures.append("sqlite_sequence_table_missing")
    if sqlite_report["sqlite_sequence_value"] is None:
        failures.append("sqlite_sequence_row_missing_for_users")
    if not postgres_rows and int(bump_plan["postgres_max_user_id"]) != 0:
        failures.append("postgres_users_max_id_unreadable")

    target_sequence_value = int(bump_plan["recommended_sqlite_sequence_value"])
    postgres_max_user_id = int(bump_plan["postgres_max_user_id"])
    if target_sequence_value != postgres_max_user_id:
        failures.append("target_sequence_value_must_equal_postgres_max_id")

    current_sqlite_sequence_value = sqlite_report["sqlite_sequence_value"]
    if current_sqlite_sequence_value is not None and target_sequence_value <= int(current_sqlite_sequence_value):
        failures.append("target_sequence_value_must_exceed_current_sqlite_sequence_value")

    expected_next_sqlite_user_id_after_bump = int(bump_plan["expected_next_sqlite_user_id_after_bump"])
    if expected_next_sqlite_user_id_after_bump != postgres_max_user_id + 1:
        failures.append("expected_next_sqlite_user_id_after_bump_mismatch")

    return failures


def print_sqlite_apply_state(sqlite_report: dict[str, object], sqlite_rows: dict[int, dict[str, object]]) -> None:
    print("SQLite users sequence apply check:")
    print(f"- user_count: {sqlite_report['user_count']}")
    print(f"- max_user_id: {sqlite_report['max_user_id']}")
    print(f"- has_autoincrement: {str(sqlite_report['has_autoincrement']).lower()}")
    print(f"- sqlite_sequence_exists: {str(sqlite_report['sqlite_sequence_exists']).lower()}")
    print(f"- sqlite_sequence_value: {sqlite_report['sqlite_sequence_value']}")
    print(f"- next_sqlite_user_id: {sqlite_report['next_sqlite_user_id']}")
    print("- existing_users:")
    if sqlite_rows:
        for user_id, row in sqlite_rows.items():
            print(f"  id={user_id} username={row['username']!r}")
    else:
        print("  none")


def print_postgres_apply_state(postgres_rows: dict[int, dict[str, object]]) -> None:
    print("PostgreSQL users sequence apply check:")
    print(f"- user_count: {len(postgres_rows)}")
    print(f"- max_user_id: {max(postgres_rows, default=0)}")
    print("- existing_users:")
    if postgres_rows:
        for user_id in sorted(postgres_rows):
            row = postgres_rows[user_id]
            print(f"  id={user_id} username={row['username']!r}")
    else:
        print("  none")


def print_bump_summary(bump_plan: dict[str, object]) -> None:
    print("SQLite users sequence bump summary:")
    print(f"- old_sqlite_sequence_value: {bump_plan['current_sqlite_sequence_value']}")
    print(f"- new_sqlite_sequence_value: {bump_plan['recommended_sqlite_sequence_value']}")
    print(f"- old_next_sqlite_user_id: {bump_plan['current_next_sqlite_user_id']}")
    print(
        "- new_next_sqlite_user_id: "
        f"{bump_plan['expected_next_sqlite_user_id_after_bump']}"
    )
    print(f"- postgres_max_user_id: {bump_plan['postgres_max_user_id']}")
    print(f"- bump_needed: {str(bump_plan['bump_needed']).lower()}")
    print(f"- recommended_sql: {bump_plan['recommended_sql']}")


def apply_bump(sqlite_path: Path, target_sequence_value: int) -> None:
    sqlite_conn = connect_sqlite(sqlite_path)
    try:
        sqlite_conn.execute(
            "UPDATE sqlite_sequence SET seq = ? WHERE name = 'users'",
            (target_sequence_value,),
        )
        sqlite_conn.commit()
    finally:
        sqlite_conn.close()


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    sqlite_path = resolve_sqlite_source_path()
    sqlite_report = fetch_sqlite_users_schema(sqlite_path)
    sqlite_rows = fetch_sqlite_users(sqlite_path)

    print(f"SQLite source: {sqlite_path}")
    print_sqlite_apply_state(sqlite_report, sqlite_rows)

    if not database_url:
        print("DATABASE_URL is not configured.")
        if args.apply:
            print("FAIL users sqlite sequence bump apply requires DATABASE_URL.")
            return 1
        print("DRY RUN ONLY. No data was modified.")
        print("PASS users sqlite sequence bump dry-run skipped PostgreSQL checks without DATABASE_URL.")
        return 0

    print(f"PostgreSQL target: {redact_database_url(database_url)}")
    with connect_postgres(database_url) as pg_conn:
        postgres_rows = fetch_postgres_users(pg_conn)

    print_postgres_apply_state(postgres_rows)
    postgres_max_user_id = max(postgres_rows, default=0)
    bump_plan = build_sequence_bump_plan(sqlite_report, postgres_max_user_id)
    print_bump_summary(bump_plan)

    precondition_failures = validate_apply_preconditions(sqlite_report, postgres_rows, bump_plan)
    if precondition_failures:
        print(f"FAIL users sqlite sequence bump preconditions: {', '.join(precondition_failures)}")
        return 1

    if not args.apply:
        print("DRY RUN ONLY. No data was modified.")
        print("PASS users sqlite sequence bump dry-run plan is apply-ready.")
        return 0

    target_sequence_value = int(bump_plan["recommended_sqlite_sequence_value"])
    apply_bump(sqlite_path, target_sequence_value)
    post_apply_report = fetch_sqlite_users_schema(sqlite_path)

    if int(post_apply_report["sqlite_sequence_value"]) != target_sequence_value:
        print("FAIL users sqlite sequence bump post-apply sqlite_sequence verification failed.")
        return 1
    if int(post_apply_report["next_sqlite_user_id"]) != int(bump_plan["expected_next_sqlite_user_id_after_bump"]):
        print("FAIL users sqlite sequence bump post-apply next id verification failed.")
        return 1

    print("PASS users sqlite sequence bump applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
