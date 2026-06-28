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
)
from check_users_id_allocation import (  # noqa: E402
    fetch_sqlite_users_schema,
    print_postgres_report,
    print_sqlite_report,
)
from check_users_baseline_and_sequence import fetch_sqlite_users  # noqa: E402
from check_users_secondary_update import (  # noqa: E402
    connect_postgres,
    redact_database_url,
    resolve_sqlite_source_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan a SQLite users sqlite_sequence bump without modifying data."
    )
    return parser.parse_args()


def build_sequence_bump_plan(
    sqlite_report: dict[str, object],
    postgres_max_user_id: int,
) -> dict[str, object]:
    has_autoincrement = bool(sqlite_report["has_autoincrement"])
    sqlite_sequence_exists = bool(sqlite_report["sqlite_sequence_exists"])
    current_sqlite_sequence_value = sqlite_report["sqlite_sequence_value"]
    current_next_sqlite_user_id = int(sqlite_report["next_sqlite_user_id"])

    recommended_sqlite_sequence_value = max(
        postgres_max_user_id,
        int(sqlite_report["max_user_id"]),
    )
    expected_next_sqlite_user_id_after_bump = recommended_sqlite_sequence_value + 1
    bump_needed = current_next_sqlite_user_id <= postgres_max_user_id

    if not has_autoincrement:
        recommended_sql = None
        reason = "users_table_not_autoincrement"
    elif not sqlite_sequence_exists:
        recommended_sql = None
        reason = "sqlite_sequence_table_missing"
    elif current_sqlite_sequence_value is None:
        recommended_sql = (
            "INSERT INTO sqlite_sequence (name, seq) "
            f"VALUES ('users', {recommended_sqlite_sequence_value});"
        )
        reason = "sqlite_sequence_row_missing_for_users"
    else:
        recommended_sql = (
            "UPDATE sqlite_sequence "
            f"SET seq = {recommended_sqlite_sequence_value} "
            "WHERE name = 'users';"
        )
        reason = "sqlite_sequence_row_present_for_users"

    return {
        "current_sqlite_sequence_value": current_sqlite_sequence_value,
        "current_next_sqlite_user_id": current_next_sqlite_user_id,
        "postgres_max_user_id": postgres_max_user_id,
        "recommended_sqlite_sequence_value": recommended_sqlite_sequence_value,
        "expected_next_sqlite_user_id_after_bump": expected_next_sqlite_user_id_after_bump,
        "bump_needed": bump_needed,
        "reason": reason,
        "recommended_sql": recommended_sql,
    }


def print_bump_plan(plan: dict[str, object]) -> None:
    print("SQLite users sequence bump plan:")
    print(f"- current_sqlite_sequence_value: {plan['current_sqlite_sequence_value']}")
    print(f"- current_next_sqlite_user_id: {plan['current_next_sqlite_user_id']}")
    print(f"- postgres_max_user_id: {plan['postgres_max_user_id']}")
    print(f"- recommended_sqlite_sequence_value: {plan['recommended_sqlite_sequence_value']}")
    print(
        "- expected_next_sqlite_user_id_after_bump: "
        f"{plan['expected_next_sqlite_user_id_after_bump']}"
    )
    print(f"- bump_needed: {str(plan['bump_needed']).lower()}")
    print(f"- planning_reason: {plan['reason']}")
    print("- recommended_sql:")
    if plan["recommended_sql"] is None:
        print("  none")
    else:
        print(f"  {plan['recommended_sql']}")


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
        print("DRY RUN ONLY. No data was modified.")
        print("PASS users sqlite sequence bump plan skipped PostgreSQL checks without DATABASE_URL.")
        return 0

    print(f"PostgreSQL target: {redact_database_url(database_url)}")
    with connect_postgres(database_url) as pg_conn:
        postgres_rows = fetch_postgres_users(pg_conn)

    print_postgres_report(postgres_rows)
    postgres_max_user_id = max(postgres_rows, default=0)
    bump_plan = build_sequence_bump_plan(sqlite_report, postgres_max_user_id)
    print_bump_plan(bump_plan)
    print("DRY RUN ONLY. No data was modified.")
    print("PASS users sqlite sequence bump plan generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
