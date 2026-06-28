from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (  # noqa: E402
    DATABASE_URL,
    DUAL_WRITE_DRY_RUN,
    DUAL_WRITE_ENABLED,
    DUAL_WRITE_STRICT,
    DUAL_WRITE_TABLES,
    USE_SQLALCHEMY_WRITES,
)
from check_users_baseline_and_sequence import (  # noqa: E402
    USER_COLUMNS,
    fetch_postgres_users,
    fetch_sequence_report,
    fetch_sqlite_users,
)
from check_users_secondary_update import (  # noqa: E402
    connect_sqlite,
    connect_postgres,
    redact_database_url,
    resolve_sqlite_source_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether runtime flags, users baseline, and PostgreSQL sequence state are ready for users create dual-write."
    )
    parser.add_argument(
        "--username",
        help="Optional probe username to verify is absent from both SQLite and PostgreSQL.",
    )
    parser.add_argument(
        "--strict-baseline",
        action="store_true",
        help="Treat users baseline drift as a failure instead of a warning.",
    )
    return parser.parse_args()


def print_runtime_flags() -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    dual_write_tables_csv = ",".join(DUAL_WRITE_TABLES)

    print("Runtime flags:")
    print(f"- DUAL_WRITE_ENABLED: {str(DUAL_WRITE_ENABLED).lower()}")
    print(f"- DUAL_WRITE_DRY_RUN: {str(DUAL_WRITE_DRY_RUN).lower()}")
    print(f"- DUAL_WRITE_STRICT: {str(DUAL_WRITE_STRICT).lower()}")
    print(f"- DUAL_WRITE_TABLES: {dual_write_tables_csv}")
    print(f"- USE_SQLALCHEMY_WRITES: {str(USE_SQLALCHEMY_WRITES).lower()}")

    if "users" not in DUAL_WRITE_TABLES:
        failures.append("DUAL_WRITE_TABLES_missing_users")
    if DUAL_WRITE_STRICT:
        failures.append("DUAL_WRITE_STRICT_must_be_false")
    if USE_SQLALCHEMY_WRITES:
        failures.append("USE_SQLALCHEMY_WRITES_must_be_false")

    if failures:
        warnings.extend(failures)

    return failures, warnings


def build_baseline_summary(
    sqlite_rows: dict[int, dict[str, object]],
    postgres_rows: dict[int, dict[str, object]],
) -> dict[str, object]:
    common_ids = sorted(set(sqlite_rows) & set(postgres_rows))
    only_in_sqlite = sorted(set(sqlite_rows) - set(postgres_rows))
    only_in_postgres = sorted(set(postgres_rows) - set(sqlite_rows))
    field_mismatches: list[dict[str, object]] = []

    for user_id in common_ids:
        sqlite_row = sqlite_rows[user_id]
        postgres_row = postgres_rows[user_id]
        mismatches = [
            field
            for field in USER_COLUMNS[1:]
            if sqlite_row[field] != postgres_row[field]
        ]
        if mismatches:
            field_mismatches.append(
                {
                    "id": user_id,
                    "username": sqlite_row["username"],
                    "fields": mismatches,
                    "sqlite": sqlite_row,
                    "postgres": postgres_row,
                }
            )

    return {
        "common_ids": common_ids,
        "only_in_sqlite": only_in_sqlite,
        "only_in_postgres": only_in_postgres,
        "field_mismatches": field_mismatches,
    }


def print_baseline_summary(
    summary: dict[str, object],
    sqlite_rows: dict[int, dict[str, object]],
    postgres_rows: dict[int, dict[str, object]],
) -> bool:
    only_in_sqlite = summary["only_in_sqlite"]
    only_in_postgres = summary["only_in_postgres"]
    field_mismatches = summary["field_mismatches"]

    print("Users baseline drift:")
    print(f"- common row count: {len(summary['common_ids'])}")
    print(f"- only_in_sqlite count: {len(only_in_sqlite)}")
    print(f"- only_in_postgres count: {len(only_in_postgres)}")
    print(f"- field mismatch count: {len(field_mismatches)}")

    print("common row mismatches:")
    if field_mismatches:
        for mismatch in field_mismatches:
            print(
                f"  users id={mismatch['id']}: username={mismatch['username']!r} "
                f"fields={', '.join(mismatch['fields'])}"
            )
            for field in mismatch["fields"]:
                print(
                    f"    sqlite.{field}={mismatch['sqlite'][field]!r} "
                    f"postgres.{field}={mismatch['postgres'][field]!r}"
                )
    else:
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

    return bool(only_in_sqlite or only_in_postgres or field_mismatches)


def print_sequence_report(report: dict[str, object]) -> bool:
    print("PostgreSQL users.id sequence:")
    print(f"- max_user_id: {report['max_user_id']}")
    print(f"- sequence_name: {report['sequence_name']!r}")
    print(f"- last_value: {report.get('last_value')}")
    print(f"- is_called: {report.get('is_called')}")
    print(f"- increment_by: {report.get('increment_by')}")
    print(f"- next_insert_id: {report.get('next_insert_id')}")
    print(f"- status: {report['status']}")
    print(f"- reason: {report['reason']}")
    return report["status"] != "ok"


def probe_username_rows(
    username: str,
    sqlite_rows: dict[int, dict[str, object]],
    postgres_rows: dict[int, dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    sqlite_hits = [row for row in sqlite_rows.values() if row["username"] == username]
    postgres_hits = [row for row in postgres_rows.values() if row["username"] == username]
    return sqlite_hits, postgres_hits


def print_username_probe(
    username: str,
    sqlite_hits: list[dict[str, object]],
    postgres_hits: list[dict[str, object]],
) -> bool:
    print("Probe username:")
    print(f"- username: {username!r}")
    print(f"- sqlite_exists: {bool(sqlite_hits)}")
    print(f"- postgres_exists: {bool(postgres_hits)}")

    if sqlite_hits:
        for row in sqlite_hits:
            print(
                f"  sqlite users id={row['id']}: display_name={row['display_name']!r} "
                f"role={row['role']!r} created_at={row['created_at']!r}"
            )
    if postgres_hits:
        for row in postgres_hits:
            print(
                f"  postgres users id={row['id']}: display_name={row['display_name']!r} "
                f"role={row['role']!r} created_at={row['created_at']!r}"
            )

    return bool(sqlite_hits or postgres_hits)


def fetch_next_sqlite_user_id(sqlite_path: Path) -> int:
    sqlite_conn = connect_sqlite(sqlite_path)
    try:
        row = sqlite_conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users").fetchone()
        return int(row[0])
    finally:
        sqlite_conn.close()


def build_next_sqlite_collision_report(
    next_sqlite_user_id: int,
    postgres_rows: dict[int, dict[str, object]],
) -> dict[str, object]:
    postgres_row = postgres_rows.get(next_sqlite_user_id)
    return {
        "next_sqlite_user_id": next_sqlite_user_id,
        "postgres_collision": postgres_row,
        "status": "risk" if postgres_row else "ok",
        "reason": (
            "next_sqlite_user_id_collides_with_postgres"
            if postgres_row
            else "next_sqlite_user_id_not_present_in_postgres"
        ),
    }


def print_next_sqlite_collision_report(report: dict[str, object]) -> bool:
    print("Next SQLite users.id guard:")
    print(f"- next_sqlite_user_id: {report['next_sqlite_user_id']}")
    print(f"- status: {report['status']}")
    print(f"- reason: {report['reason']}")

    postgres_collision = report["postgres_collision"]
    if postgres_collision:
        print(
            f"- postgres_existing_user: id={postgres_collision['id']} "
            f"username={postgres_collision['username']!r} "
            f"display_name={postgres_collision['display_name']!r} "
            f"role={postgres_collision['role']!r} "
            f"created_at={postgres_collision['created_at']!r}"
        )

    return report["status"] != "ok"


def main() -> int:
    args = parse_args()
    failures, local_warnings = print_runtime_flags()

    database_url = DATABASE_URL.strip() if DATABASE_URL else os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is not configured.")
        if local_warnings:
            print(
                "SKIP runtime enforcement without DATABASE_URL: "
                f"{', '.join(local_warnings)}"
            )
        print("PASS users create readiness check skipped PostgreSQL checks without DATABASE_URL.")
        return 0

    sqlite_path = resolve_sqlite_source_path()
    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    sqlite_rows = fetch_sqlite_users(sqlite_path)
    next_sqlite_user_id = fetch_next_sqlite_user_id(sqlite_path)
    with connect_postgres(database_url) as pg_conn:
        postgres_rows = fetch_postgres_users(pg_conn)
        sequence_report = fetch_sequence_report(pg_conn)

    baseline_summary = build_baseline_summary(sqlite_rows, postgres_rows)
    has_baseline_drift = print_baseline_summary(baseline_summary, sqlite_rows, postgres_rows)
    has_sequence_failure = print_sequence_report(sequence_report)
    next_sqlite_collision_report = build_next_sqlite_collision_report(next_sqlite_user_id, postgres_rows)
    has_next_sqlite_collision = print_next_sqlite_collision_report(next_sqlite_collision_report)
    if has_sequence_failure:
        failures.append("users_sequence_not_healthy")
    if has_next_sqlite_collision:
        failures.append("next_sqlite_user_id_collides_with_postgres")

    if args.username:
        sqlite_hits, postgres_hits = probe_username_rows(args.username, sqlite_rows, postgres_rows)
        if print_username_probe(args.username, sqlite_hits, postgres_hits):
            failures.append("probe_username_already_exists")
    else:
        print("Probe username:")
        print("- username: none")

    if has_baseline_drift and args.strict_baseline:
        failures.append("baseline_drift_present")

    if has_baseline_drift and not args.strict_baseline:
        print("WARN users baseline drift is present but tolerated without --strict-baseline.")

    if failures:
        print(f"FAIL users create readiness: {', '.join(failures)}")
        return 1

    print("PASS users create readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
