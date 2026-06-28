from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType


BASE_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

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
from check_users_delete_readiness import (  # noqa: E402
    ALLOWED_DELETE_USERNAME_PREFIX,
    build_persistence_report,
    print_target_row,
)
from check_users_secondary_update import (  # noqa: E402
    connect_postgres,
    redact_database_url,
    resolve_sqlite_source_path,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect or execute a users delete submit through the formal /admin/users POST route "
            "using Flask test_client with an injected admin session."
        )
    )
    parser.add_argument(
        "--username",
        required=True,
        help=f"Target username to inspect or delete. Must start with {ALLOWED_DELETE_USERNAME_PREFIX!r}.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually submit delete_user:<id> through /admin/users. Defaults to inspect only.",
    )
    return parser.parse_args(argv)


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
    if DUAL_WRITE_DRY_RUN:
        failures.append("DUAL_WRITE_DRY_RUN_must_be_false")
    if DUAL_WRITE_STRICT:
        failures.append("DUAL_WRITE_STRICT_must_be_false")
    if USE_SQLALCHEMY_WRITES:
        failures.append("USE_SQLALCHEMY_WRITES_must_be_false")

    return failures


def print_persistence_report(sqlite_path: Path) -> list[str]:
    failures: list[str] = []
    report = build_persistence_report(sqlite_path)
    print("Persistence check:")
    print(f"- sqlite_path: {sqlite_path}")
    print(f"- persistence_status: {report['status']}")
    print(f"- reason: {report['reason']}")
    if report["status"] != "ok":
        failures.append("sqlite_runtime_not_persistent")
    return failures


def load_target_rows(
    username: str,
    sqlite_path: Path,
    database_url: str,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    sqlite_rows = fetch_sqlite_users(sqlite_path)
    sqlite_row = next((row for row in sqlite_rows.values() if row["username"] == username), None)
    with connect_postgres(database_url) as pg_conn:
        postgres_rows = fetch_postgres_users(pg_conn)
    postgres_row = next((row for row in postgres_rows.values() if row["username"] == username), None)
    return sqlite_row, postgres_row


def print_target_probe(
    *,
    username: str,
    sqlite_row: dict[str, object] | None,
    postgres_row: dict[str, object] | None,
    mode: str,
) -> None:
    target_row = sqlite_row or postgres_row
    print("Target user:")
    print(f"- selector_username: {username!r}")
    print(f"- sqlite_exists: {str(sqlite_row is not None).lower()}")
    print(f"- postgres_exists: {str(postgres_row is not None).lower()}")
    print(f"- mode: {mode}")
    if target_row is not None:
        print(f"- target_user_id: {target_row['id']}")
        print(f"- target_username: {target_row['username']!r}")
        print(f"- target_role: {target_row['role']!r}")
        print(f"- target_created_at: {target_row['created_at']!r}")
    else:
        print("- target_user_id: none")
        print("- target_username: none")
        print("- target_role: none")
        print("- target_created_at: none")
    print_target_row("sqlite_row", sqlite_row)
    print_target_row("postgres_row", postgres_row)


def build_submit_guard_failures(
    *,
    username: str,
    sqlite_row: dict[str, object] | None,
    postgres_row: dict[str, object] | None,
) -> list[str]:
    failures: list[str] = []

    if not username.startswith(ALLOWED_DELETE_USERNAME_PREFIX):
        failures.append("target_user_not_allowed_for_stage_4a")

    target_row = sqlite_row or postgres_row
    if target_row is None:
        failures.append("target_user_not_found")
        return failures

    target_id = int(target_row["id"])
    target_username = str(target_row["username"])
    target_role = str(target_row["role"])

    if target_id == 1 or target_username == "admin" or target_role == "admin":
        failures.append("protected_user")

    if sqlite_row is None:
        failures.append("target_user_missing_in_sqlite")
    if postgres_row is None:
        failures.append("target_user_missing_in_postgres")

    if sqlite_row is not None and postgres_row is not None:
        if int(sqlite_row["id"]) != int(postgres_row["id"]):
            failures.append("target_user_id_mismatch")
        if str(sqlite_row["username"]) != str(postgres_row["username"]):
            failures.append("target_user_username_mismatch")

    return failures


@contextmanager
def temporary_env(name: str, value: str):
    old_value = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old_value


def load_app_module(sqlite_path: Path) -> ModuleType:
    module_name = f"users_delete_submit_app_{os.getpid()}_{sqlite_path.stat().st_mtime_ns}"
    spec = importlib.util.spec_from_file_location(module_name, str(BASE_DIR / "app.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create app.py import spec.")
    module = importlib.util.module_from_spec(spec)
    with temporary_env("APP_DB_PATH", str(sqlite_path)):
        spec.loader.exec_module(module)
    return module


def submit_delete_post(sqlite_path: Path, target_id: int) -> dict[str, object]:
    module = load_app_module(sqlite_path)
    module.app.testing = True

    with module.app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "admin"
            session["display_name"] = "Admin"
            session["role"] = "admin"

        response = client.post(
            "/admin/users",
            data={"action": f"delete_user:{target_id}"},
            follow_redirects=True,
        )
        return {
            "status_code": response.status_code,
            "body": response.get_data(as_text=True),
        }


def print_post_submit_probe(
    *,
    username: str,
    sqlite_row: dict[str, object] | None,
    postgres_row: dict[str, object] | None,
) -> None:
    print("Post-submit target user:")
    print(f"- selector_username: {username!r}")
    print(f"- sqlite_exists: {str(sqlite_row is not None).lower()}")
    print(f"- postgres_exists: {str(postgres_row is not None).lower()}")
    print_target_row("sqlite_row", sqlite_row)
    print_target_row("postgres_row", postgres_row)


def determine_post_submit_outcome(
    *,
    sqlite_row: dict[str, object] | None,
    postgres_row: dict[str, object] | None,
) -> tuple[int, str]:
    if sqlite_row is None and postgres_row is None:
        return 0, "PASS users delete submit verifier passed."
    if sqlite_row is not None and postgres_row is not None:
        return 1, "FAIL users delete submit did not land."
    return 1, "FAIL users delete inconsistent state."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    failures = print_runtime_flags()

    sqlite_path = resolve_sqlite_source_path()
    failures.extend(print_persistence_report(sqlite_path))

    database_url = DATABASE_URL.strip() if DATABASE_URL else os.environ.get("DATABASE_URL", "").strip()
    print(f"SQLite source: {sqlite_path}")
    if database_url:
        print(f"PostgreSQL target: {redact_database_url(database_url)}")
    else:
        print("PostgreSQL target: missing_DATABASE_URL")
        failures.append("DATABASE_URL_required_for_cross_db_verification")

    sqlite_row = None
    postgres_row = None
    if database_url:
        sqlite_row, postgres_row = load_target_rows(args.username, sqlite_path, database_url)

    print_target_probe(
        username=args.username,
        sqlite_row=sqlite_row,
        postgres_row=postgres_row,
        mode="execute" if args.execute else "inspect_only",
    )
    failures.extend(
        build_submit_guard_failures(
            username=args.username,
            sqlite_row=sqlite_row,
            postgres_row=postgres_row,
        )
    )

    if failures:
        print(f"FAIL users delete submit verifier: {', '.join(failures)}")
        return 1

    if not args.execute:
        print("PASS users delete submit verifier inspect completed.")
        return 0

    assert sqlite_row is not None
    target_id = int(sqlite_row["id"])
    submit_result = submit_delete_post(sqlite_path, target_id)
    print("Delete submit response:")
    print(f"- status_code: {submit_result['status_code']}")

    sqlite_row_after, postgres_row_after = load_target_rows(args.username, sqlite_path, database_url)
    print_post_submit_probe(
        username=args.username,
        sqlite_row=sqlite_row_after,
        postgres_row=postgres_row_after,
    )
    exit_code, message = determine_post_submit_outcome(
        sqlite_row=sqlite_row_after,
        postgres_row=postgres_row_after,
    )
    print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
