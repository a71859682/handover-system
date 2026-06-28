from __future__ import annotations

import argparse
import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlite_db_path import get_sqlite_db_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect users read shadow compare readiness without changing the active read source."
    )
    return parser.parse_args()


def _format_fields(fields: list[str]) -> str:
    return ",".join(fields) if fields else "none"


def main() -> int:
    parse_args()
    source_db_path = get_sqlite_db_path()
    temp_dir = Path(tempfile.mkdtemp(prefix="users-read-compare-"))
    analysis_db_path = temp_dir / source_db_path.name
    shutil.copy2(source_db_path, analysis_db_path)
    os.environ["APP_DB_PATH"] = str(analysis_db_path)
    app = importlib.import_module("app")

    issues: list[str] = []

    print(f"USERS_READ_COMPARE: {str(app.users_read_compare_enabled()).lower()}")
    print(f"sqlite_source: {source_db_path}")
    print(f"analysis_db_copy: {analysis_db_path}")

    primary_admin = app._sqlite_get_user_by_username("admin")
    primary_admin_by_id = app._sqlite_get_user_by_id(1)
    listed_users = app._sqlite_list_users()

    shadow_admin = None
    shadow_admin_by_id = None
    shadow_listed_users = []
    try:
        shadow_admin = app._shadow_get_user_by_username("admin")
    except Exception as exc:
        issues.append(f"shadow_username_lookup_error:{type(exc).__name__}")
    try:
        shadow_admin_by_id = app._shadow_get_user_by_id(1)
    except Exception as exc:
        issues.append(f"shadow_id_lookup_error:{type(exc).__name__}")
    try:
        shadow_listed_users = app._shadow_list_users()
    except Exception as exc:
        issues.append(f"shadow_list_error:{type(exc).__name__}")

    print(f"sqlite_admin_exists: {str(primary_admin is not None).lower()}")
    print(f"shadow_admin_exists: {str(shadow_admin is not None).lower()}")
    print(f"sqlite_admin_by_id_exists: {str(primary_admin_by_id is not None).lower()}")
    print(f"shadow_admin_by_id_exists: {str(shadow_admin_by_id is not None).lower()}")
    print(f"sqlite_user_count: {len(listed_users)}")
    print(f"shadow_user_count: {len(shadow_listed_users)}")

    username_compare = app.run_users_read_compare_by_username("admin", log_result=False)
    id_compare = app.run_users_read_compare_by_id(1, log_result=False)
    list_compare = app.run_users_list_compare(log_result=False)

    print(
        "compare get_user_by_username('admin'): "
        f"status={username_compare['status']} "
        f"fields={_format_fields(username_compare['fields'])} "
        f"password_hash_match={str(username_compare['password_hash_match']).lower()}"
    )
    print(
        "compare get_user_by_id(1): "
        f"status={id_compare['status']} "
        f"fields={_format_fields(id_compare['fields'])} "
        f"password_hash_match={str(id_compare['password_hash_match']).lower()}"
    )
    print(
        "compare list_users: "
        f"status={list_compare['status']} "
        f"row_count_match={str(list_compare['row_count_match']).lower()} "
        f"ordered_ids_match={str(list_compare['ordered_ids_match']).lower()}"
    )
    for detail in list_compare["details"]:
        print(
            f"compare list_users detail: id={detail['id']} fields={_format_fields(detail['fields'])}"
        )

    if primary_admin is None:
        issues.append("sqlite_admin_missing")
    if shadow_admin is None:
        issues.append("shadow_admin_missing")
    if username_compare["status"] != "match":
        issues.append(f"get_user_by_username_mismatch:{_format_fields(username_compare['fields'])}")
    if id_compare["status"] != "match":
        issues.append(f"get_user_by_id_mismatch:{_format_fields(id_compare['fields'])}")
    if list_compare["status"] != "match":
        issues.append(
            "list_users_mismatch:"
            f"row_count_match={str(list_compare['row_count_match']).lower()},"
            f"ordered_ids_match={str(list_compare['ordered_ids_match']).lower()}"
        )

    if issues:
        print(f"FAIL users read compare readiness: {', '.join(issues)}")
        return 1

    print("PASS users read compare readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
