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
    fetch_postgres_users,
    fetch_sqlite_users,
)
from check_users_secondary_update import (  # noqa: E402
    connect_postgres,
    redact_database_url,
    resolve_sqlite_source_path,
)


ALLOWED_DELETE_USERNAME_PREFIX = "dw_test_"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether runtime flags and target-user state are ready for users delete dual-write."
    )
    selector_group = parser.add_mutually_exclusive_group(required=True)
    selector_group.add_argument(
        "--username",
        help="Target username to inspect for Stage 4A delete readiness.",
    )
    selector_group.add_argument(
        "--user-id",
        type=int,
        help="Target user id to inspect for Stage 4A delete readiness.",
    )
    return parser.parse_args()


def print_runtime_flags() -> list[str]:
    failures: list[str] = []
    dual_write_tables_csv = ",".join(DUAL_WRITE_TABLES)

    print("Runtime flags:")
    print(f"- DUAL_WRITE_ENABLED: {str(DUAL_WRITE_ENABLED).lower()}")
    print(f"- DUAL_WRITE_DRY_RUN: {str(DUAL_WRITE_DRY_RUN).lower()}")
    print(f"- DUAL_WRITE_STRICT: {str(DUAL_WRITE_STRICT).lower()}")
    print(f"- DUAL_WRITE_TABLES: {dual_write_tables_csv}")
    print(f"- USE_SQLALCHEMY_WRITES: {str(USE_SQLALCHEMY_WRITES).lower()}")

    if not DUAL_WRITE_ENABLED:
        failures.append("DUAL_WRITE_ENABLED_must_be_true")
    if "users" not in DUAL_WRITE_TABLES:
        failures.append("DUAL_WRITE_TABLES_missing_users")
    if DUAL_WRITE_STRICT:
        failures.append("DUAL_WRITE_STRICT_must_be_false")
    if USE_SQLALCHEMY_WRITES:
        failures.append("USE_SQLALCHEMY_WRITES_must_be_false")

    return failures


def build_persistence_report(sqlite_path: Path) -> dict[str, str]:
    sqlite_path_text = sqlite_path.as_posix()
    if sqlite_path_text.startswith("/opt/render/project/src"):
        return {
            "status": "risk",
            "reason": "path_is_under_render_source_tree",
        }
    return {
        "status": "ok",
        "reason": "sqlite_path_not_under_render_source_tree",
    }


def print_persistence_report(sqlite_path: Path) -> bool:
    report = build_persistence_report(sqlite_path)
    print("Persistence check:")
    print(f"- sqlite_path: {sqlite_path}")
    print(f"- persistence_status: {report['status']}")
    print(f"- reason: {report['reason']}")
    return report["status"] != "ok"


def select_target_rows(
    *,
    username: str | None,
    user_id: int | None,
    sqlite_rows: dict[int, dict[str, object]],
    postgres_rows: dict[int, dict[str, object]] | None,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    if username is not None:
        sqlite_match = next(
            (row for row in sqlite_rows.values() if row["username"] == username),
            None,
        )
        postgres_match = None
        if postgres_rows is not None:
            postgres_match = next(
                (row for row in postgres_rows.values() if row["username"] == username),
                None,
            )
        return sqlite_match, postgres_match

    assert user_id is not None
    sqlite_match = sqlite_rows.get(user_id)
    postgres_match = postgres_rows.get(user_id) if postgres_rows is not None else None
    return sqlite_match, postgres_match


def print_target_row(label: str, row: dict[str, object] | None) -> None:
    if row is None:
        print(f"- {label}: none")
        return
    print(
        f"- {label}: id={row['id']} username={row['username']!r} "
        f"display_name={row['display_name']!r} role={row['role']!r} "
        f"created_at={row['created_at']!r}"
    )


def print_target_probe(
    *,
    username: str | None,
    user_id: int | None,
    sqlite_row: dict[str, object] | None,
    postgres_row: dict[str, object] | None,
    postgres_checked: bool,
) -> None:
    print("Target user:")
    print(f"- selector_username: {username!r}")
    print(f"- selector_user_id: {user_id}")
    print(f"- sqlite_exists: {str(sqlite_row is not None).lower()}")
    print_target_row("sqlite_row", sqlite_row)
    if postgres_checked:
        print(f"- postgres_exists: {str(postgres_row is not None).lower()}")
        print_target_row("postgres_row", postgres_row)
    else:
        print("- postgres_exists: skipped_without_DATABASE_URL")
        print("- postgres_row: skipped_without_DATABASE_URL")


def build_delete_guard_failures(
    sqlite_row: dict[str, object] | None,
    postgres_row: dict[str, object] | None,
    postgres_checked: bool,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    target_row = sqlite_row or postgres_row
    if target_row is None:
        failures.append("target_user_not_found")
        return failures, warnings

    username = str(target_row["username"])
    role = str(target_row["role"])
    user_id = int(target_row["id"])

    if user_id == 1 or username == "admin" or role == "admin":
        failures.append("protected_user")

    if not username.startswith(ALLOWED_DELETE_USERNAME_PREFIX):
        failures.append("target_user_not_allowed_for_stage_4a")

    if sqlite_row is None:
        failures.append("target_user_missing_in_sqlite")

    if postgres_checked:
        if sqlite_row is not None and postgres_row is None:
            warnings.append("target_only_exists_in_sqlite")
        if sqlite_row is not None and postgres_row is not None:
            if int(sqlite_row["id"]) != int(postgres_row["id"]) or str(sqlite_row["username"]) != str(
                postgres_row["username"]
            ):
                failures.append("target_user_mismatch")

    return failures, warnings


def main() -> int:
    args = parse_args()
    failures = print_runtime_flags()

    sqlite_path = resolve_sqlite_source_path()
    if print_persistence_report(sqlite_path):
        failures.append("sqlite_runtime_not_persistent")

    sqlite_rows = fetch_sqlite_users(sqlite_path)
    database_url = DATABASE_URL.strip() if DATABASE_URL else os.environ.get("DATABASE_URL", "").strip()
    postgres_rows: dict[int, dict[str, object]] | None = None
    postgres_checked = bool(database_url)

    print(f"SQLite source: {sqlite_path}")
    if database_url:
        print(f"PostgreSQL target: {redact_database_url(database_url)}")
        with connect_postgres(database_url) as pg_conn:
            postgres_rows = fetch_postgres_users(pg_conn)
    else:
        print("DATABASE_URL is not configured.")
        print("PostgreSQL target: skipped_without_DATABASE_URL")

    sqlite_row, postgres_row = select_target_rows(
        username=args.username,
        user_id=args.user_id,
        sqlite_rows=sqlite_rows,
        postgres_rows=postgres_rows,
    )
    print_target_probe(
        username=args.username,
        user_id=args.user_id,
        sqlite_row=sqlite_row,
        postgres_row=postgres_row,
        postgres_checked=postgres_checked,
    )

    guard_failures, warnings = build_delete_guard_failures(
        sqlite_row=sqlite_row,
        postgres_row=postgres_row,
        postgres_checked=postgres_checked,
    )
    failures.extend(guard_failures)

    for warning in warnings:
        if warning == "target_only_exists_in_sqlite":
            print("WARN target only exists in SQLite")

    if failures:
        print(f"FAIL users delete readiness: {', '.join(failures)}")
        return 1

    print("PASS users delete readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
