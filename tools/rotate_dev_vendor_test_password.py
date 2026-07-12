from __future__ import annotations

import argparse
import getpass
import os
import sqlite3
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlite_db_path import SqliteDbPathResolution, resolve_sqlite_db_path  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


EXPECTED_SERVICE = "handover-system-dev"
EXPECTED_DB_PATH = Path("/var/data/site.db")
TARGET_ID = 1
TARGET_USERNAME = "devdata001_vendor_heping_test2_01"
TARGET_VENDOR_NAME = "測試廠商-和平-TEST2-01"
EXPECTED_SHEET_ID = 3


class RotationError(RuntimeError):
    pass


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or rotate the fixed DEV vendor test credential. Defaults to dry-run."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Inspect guards without changing the database.")
    mode.add_argument("--apply", action="store_true", help="Rotate the fixed DEV test credential.")
    parser.add_argument(
        "--confirm-username",
        help="Required with --apply and must exactly match the fixed DEV test username.",
    )
    args = parser.parse_args(argv)
    if args.apply:
        if args.confirm_username != TARGET_USERNAME:
            parser.error(f"--apply requires --confirm-username {TARGET_USERNAME}")
    elif args.confirm_username is not None:
        parser.error("--confirm-username is only valid with --apply")
    return args


def validate_runtime(
    environ: Mapping[str, str],
    *,
    expected_path: Path = EXPECTED_DB_PATH,
    path_resolver: Callable[[str | None], SqliteDbPathResolution] = resolve_sqlite_db_path,
) -> Path:
    if environ.get("RENDER_SERVICE_NAME", "").strip() != EXPECTED_SERVICE:
        raise RotationError("service_guard_failed")
    raw_path = environ.get("APP_DB_PATH", "").strip()
    if not raw_path:
        raise RotationError("app_db_path_required")
    resolution = path_resolver(raw_path)
    if resolution.source != "env_APP_DB_PATH":
        raise RotationError("app_db_path_source_rejected")
    resolved = resolution.path.resolve(strict=False)
    if resolved != expected_path.resolve(strict=False):
        raise RotationError("app_db_path_target_rejected")
    if not TARGET_USERNAME.startswith("devdata001_vendor_"):
        raise RotationError("target_username_prefix_rejected")
    if not TARGET_VENDOR_NAME.startswith("測試廠商-"):
        raise RotationError("target_vendor_prefix_rejected")
    return resolved


def validate_exact_account_rows(rows: Sequence[sqlite3.Row]) -> sqlite3.Row:
    if len(rows) != 1:
        raise RotationError("target_account_count_invalid")
    account = rows[0]
    if (
        int(account["id"]) != TARGET_ID
        or str(account["username"]) != TARGET_USERNAME
        or str(account["vendor_name"]) != TARGET_VENDOR_NAME
    ):
        raise RotationError("target_identity_mismatch")
    if int(account["is_active"] or 0) != 1:
        raise RotationError("target_account_inactive")
    return account


def validate_trusted_target_rows(rows: Sequence[sqlite3.Row]) -> int:
    sheet_ids = [int(row["id"]) for row in rows]
    if sheet_ids != [EXPECTED_SHEET_ID]:
        raise RotationError("trusted_target_mismatch")
    return sheet_ids[0]


def validate_database_state(conn: sqlite3.Connection) -> tuple[sqlite3.Row, int]:
    conn.row_factory = sqlite3.Row
    account_rows = conn.execute(
        """
        SELECT id, username, vendor_name, is_active, created_at, updated_at
        FROM vendor_accounts
        WHERE id = ? AND username = ? AND vendor_name = ?
        ORDER BY id
        """,
        (TARGET_ID, TARGET_USERNAME, TARGET_VENDOR_NAME),
    ).fetchall()
    account = validate_exact_account_rows(account_rows)
    trusted_rows = conn.execute(
        """
        SELECT DISTINCT s.id
        FROM sheets s
        JOIN sites site ON site.id = s.site_id
        JOIN tasks t ON t.sheet_id = s.id
        WHERE site.is_active = 1
          AND t.vendor = ?
        ORDER BY s.id
        """,
        (TARGET_VENDOR_NAME,),
    ).fetchall()
    return account, validate_trusted_target_rows(trusted_rows)


def inspect_target(
    environ: Mapping[str, str],
    *,
    expected_path: Path = EXPECTED_DB_PATH,
    path_resolver: Callable[[str | None], SqliteDbPathResolution] = resolve_sqlite_db_path,
    readonly_connect: Callable[[str], sqlite3.Connection] | None = None,
) -> tuple[Path, sqlite3.Row, int]:
    path = validate_runtime(environ, expected_path=expected_path, path_resolver=path_resolver)
    uri = f"file:{path.as_posix()}?mode=ro"
    connect = readonly_connect or (lambda value: sqlite3.connect(value, uri=True))
    conn = connect(uri)
    try:
        conn.execute("PRAGMA query_only=1")
        account, trusted_sheet = validate_database_state(conn)
        return path, account, trusted_sheet
    finally:
        conn.close()


def rotate_password(
    environ: Mapping[str, str],
    password: str,
    *,
    expected_path: Path = EXPECTED_DB_PATH,
    path_resolver: Callable[[str | None], SqliteDbPathResolution] = resolve_sqlite_db_path,
    write_connect: Callable[[Path], sqlite3.Connection] = sqlite3.connect,
    hash_factory: Callable[[str], str] = generate_password_hash,
) -> None:
    path = validate_runtime(environ, expected_path=expected_path, path_resolver=path_resolver)
    conn = write_connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        validate_runtime(environ, expected_path=expected_path, path_resolver=path_resolver)
        validate_database_state(conn)
        password_hash = hash_factory(password)
        cursor = conn.execute(
            """
            UPDATE vendor_accounts
            SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND username = ? AND vendor_name = ? AND is_active = 1
            """,
            (password_hash, TARGET_ID, TARGET_USERNAME, TARGET_VENDOR_NAME),
        )
        if cursor.rowcount != 1:
            raise RotationError("target_update_count_invalid")
        validate_database_state(conn)
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def print_inventory(path: Path, account: sqlite3.Row, trusted_sheet: int) -> None:
    print("service_guard: PASS")
    print(f"sqlite_source: {path}")
    print("sqlite_source_kind: env_APP_DB_PATH")
    print(f"target_id: {int(account['id'])}")
    print(f"target_username: {account['username']}")
    print(f"target_vendor_identity: {account['vendor_name']}")
    print(f"target_active: {str(int(account['is_active']) == 1).lower()}")
    print(f"trusted_sheet: {trusted_sheet}")
    print("planned_fields: password_hash, updated_at")


def execute(
    args: argparse.Namespace,
    environ: Mapping[str, str],
    *,
    expected_path: Path = EXPECTED_DB_PATH,
    path_resolver: Callable[[str | None], SqliteDbPathResolution] = resolve_sqlite_db_path,
    input_func: Callable[[str], str] = input,
    password_reader: Callable[[str], str] = getpass.getpass,
    readonly_connect: Callable[[str], sqlite3.Connection] | None = None,
    write_connect: Callable[[Path], sqlite3.Connection] = sqlite3.connect,
    hash_factory: Callable[[str], str] = generate_password_hash,
) -> int:
    path, account, trusted_sheet = inspect_target(
        environ,
        expected_path=expected_path,
        path_resolver=path_resolver,
        readonly_connect=readonly_connect,
    )
    print_inventory(path, account, trusted_sheet)
    if not args.apply:
        print("mode: dry-run")
        print("DB unchanged")
        return 0

    confirmation = input_func(f"Type {TARGET_USERNAME} to confirm credential rotation: ").strip()
    if confirmation != TARGET_USERNAME:
        raise RotationError("interactive_confirmation_failed")
    password_1 = password_reader("New DEV vendor password: ")
    password_2 = password_reader("Confirm new DEV vendor password: ")
    if password_1 != password_2:
        del password_1, password_2
        raise RotationError("password_confirmation_mismatch")
    try:
        rotate_password(
            environ,
            password_1,
            expected_path=expected_path,
            path_resolver=path_resolver,
            write_connect=write_connect,
            hash_factory=hash_factory,
        )
    finally:
        del password_1, password_2
    print("mode: apply")
    print("PASS DEV vendor test credential rotated")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return execute(args, os.environ)
    except RotationError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("FAIL credential_rotation_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
