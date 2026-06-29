from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "site.db"


def resolve_db_path() -> Path:
    raw = os.environ.get("APP_DB_PATH")
    return Path(raw).expanduser().resolve() if raw else DEFAULT_DB_PATH.resolve()


def fetch_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def unique_index_exists(conn: sqlite3.Connection, table_name: str, columns: tuple[str, ...]) -> bool:
    for index_row in conn.execute(f"PRAGMA index_list({table_name})").fetchall():
        if not index_row["unique"]:
            continue
        index_columns = tuple(
            row["name"] for row in conn.execute(f"PRAGMA index_info({index_row['name']})").fetchall()
        )
        if index_columns == columns:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check site foundation SQLite schema.")
    parser.parse_args()

    db_path = resolve_db_path()
    os.environ["APP_DB_PATH"] = str(db_path)
    sys.path.insert(0, str(ROOT_DIR))
    import app  # noqa: F401

    print("site_schema_scope: sqlite_only")
    print(f"sqlite_path: {db_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    issues: list[str] = []

    table_names = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    required_tables = {"sites", "sheets", "user_site_permissions", "vendor_accounts"}
    print(f"tables_present: {sorted(required_tables & table_names)}")
    for table_name in sorted(required_tables):
        if table_name not in table_names:
            issues.append(f"missing_table:{table_name}")

    sites_columns = fetch_columns(conn, "sites") if "sites" in table_names else []
    sheets_columns = fetch_columns(conn, "sheets") if "sheets" in table_names else []
    permissions_columns = (
        fetch_columns(conn, "user_site_permissions") if "user_site_permissions" in table_names else []
    )
    vendor_account_columns = fetch_columns(conn, "vendor_accounts") if "vendor_accounts" in table_names else []

    print(f"sites_columns: {sites_columns}")
    print(f"sheets_columns: {sheets_columns}")
    print(f"user_site_permissions_columns: {permissions_columns}")
    print(f"vendor_accounts_columns: {vendor_account_columns}")

    expected_sites = {"id", "site_name", "site_code", "is_active", "created_at", "updated_at"}
    expected_permissions = {"id", "user_id", "site_id", "role", "created_at", "updated_at"}
    expected_vendor_accounts = {
        "id",
        "username",
        "password_hash",
        "vendor_name",
        "is_active",
        "created_at",
        "updated_at",
    }

    for column_name in sorted(expected_sites - set(sites_columns)):
        issues.append(f"missing_sites_column:{column_name}")
    if "site_id" not in sheets_columns:
        issues.append("missing_sheets_column:site_id")
    for column_name in sorted(expected_permissions - set(permissions_columns)):
        issues.append(f"missing_user_site_permissions_column:{column_name}")
    for column_name in sorted(expected_vendor_accounts - set(vendor_account_columns)):
        issues.append(f"missing_vendor_accounts_column:{column_name}")

    unique_sites = unique_index_exists(conn, "sites", ("site_name",)) if "sites" in table_names else False
    unique_permissions = (
        unique_index_exists(conn, "user_site_permissions", ("user_id", "site_id"))
        if "user_site_permissions" in table_names
        else False
    )
    unique_vendor_accounts = (
        unique_index_exists(conn, "vendor_accounts", ("username",))
        if "vendor_accounts" in table_names
        else False
    )

    print(f"sites_unique_site_name: {unique_sites}")
    print(f"user_site_permissions_unique_user_site: {unique_permissions}")
    print(f"vendor_accounts_unique_username: {unique_vendor_accounts}")

    if not unique_sites:
        issues.append("missing_unique:sites.site_name")
    if not unique_permissions:
        issues.append("missing_unique:user_site_permissions.user_id_site_id")
    if not unique_vendor_accounts:
        issues.append("missing_unique:vendor_accounts.username")

    conn.close()

    if issues:
        print("FAIL site schema check:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("PASS site schema check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
