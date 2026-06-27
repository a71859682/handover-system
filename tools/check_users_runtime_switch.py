from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_temp_db() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="users-runtime-switch-"))
    return temp_dir / "site.db"


def load_app_with_flag(db_path: Path, use_sqlalchemy_reads: bool):
    os.environ["APP_DB_PATH"] = str(db_path)
    os.environ["USE_SQLALCHEMY_READS"] = "true" if use_sqlalchemy_reads else "false"

    config_module = importlib.import_module("config")
    importlib.reload(config_module)

    app_module = importlib.import_module("app")
    app_module = importlib.reload(app_module)
    app_module.bootstrap()
    return app_module


def comparable_user(row: dict[str, object] | None) -> dict[str, object] | None:
    if row is None:
        return None
    payload = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "created_at": row["created_at"],
    }
    if "password_hash" in row:
        payload["password_hash"] = row["password_hash"]
    return payload


def main() -> int:
    db_path = prepare_temp_db()

    app_sqlite = load_app_with_flag(db_path, use_sqlalchemy_reads=False)
    sqlite_users = [comparable_user(user) for user in app_sqlite.list_users()]
    sqlite_admin = comparable_user(app_sqlite.get_user_by_username("admin"))
    sqlite_admin_by_id = comparable_user(
        app_sqlite.get_user_by_id(sqlite_admin["id"]) if sqlite_admin else None
    )

    app_orm = load_app_with_flag(db_path, use_sqlalchemy_reads=True)
    orm_users = [comparable_user(user) for user in app_orm.list_users()]
    orm_admin = comparable_user(app_orm.get_user_by_username("admin"))
    orm_admin_by_id = comparable_user(app_orm.get_user_by_id(orm_admin["id"]) if orm_admin else None)

    differences: list[str] = []
    if sqlite_users != orm_users:
        differences.append(f"list_users mismatch: sqlite3={sqlite_users!r} orm={orm_users!r}")
    if sqlite_admin != orm_admin:
        differences.append(
            f"get_user_by_username('admin') mismatch: sqlite3={sqlite_admin!r} orm={orm_admin!r}"
        )
    if sqlite_admin_by_id != orm_admin_by_id:
        differences.append(
            f"get_user_by_id(admin_id) mismatch: sqlite3={sqlite_admin_by_id!r} orm={orm_admin_by_id!r}"
        )

    print(f"Database: {db_path}")
    if differences:
        print("FAIL")
        for difference in differences:
            print(f"- {difference}")
        return 1

    print("PASS")
    print(f"- user count: {len(sqlite_users)}")
    for user in sqlite_users:
        print(
            f"- id={user['id']} username={user['username']!r} display_name={user['display_name']!r} role={user['role']!r}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
