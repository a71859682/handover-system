from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_temp_db() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="users-orm-check-"))
    db_path = temp_dir / "site.db"
    os.environ["APP_DB_PATH"] = str(db_path)
    return db_path


def comparable_user(row):
    return {
        "username": row["username"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row.username,
        "display_name": row["display_name"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row.display_name,
        "role": row["role"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row.role,
        "created_at": row["created_at"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row.created_at,
    }


def main() -> int:
    db_path = prepare_temp_db()

    import app
    from services.users_orm_service import get_user_by_id_orm, get_user_by_username_orm, list_users_orm

    app.bootstrap()

    with app.db() as conn:
        sqlite_users = conn.execute(
            "SELECT id, username, display_name, role, created_at FROM users ORDER BY id"
        ).fetchall()

    with app.app.app_context():
        orm_users = list_users_orm()
        admin_user = get_user_by_username_orm("admin")
        admin_by_id = get_user_by_id_orm(admin_user.id if admin_user else None)

    differences = []

    if len(sqlite_users) != len(orm_users):
        differences.append(f"user count mismatch: sqlite3={len(sqlite_users)} orm={len(orm_users)}")

    for sqlite_row, orm_row in zip(sqlite_users, orm_users):
        sqlite_payload = {
            "username": sqlite_row["username"],
            "display_name": sqlite_row["display_name"],
            "role": sqlite_row["role"],
            "created_at": sqlite_row["created_at"],
        }
        orm_payload = {
            "username": orm_row.username,
            "display_name": orm_row.display_name,
            "role": orm_row.role,
            "created_at": orm_row.created_at,
        }
        if sqlite_payload != orm_payload:
            differences.append(
                f"user mismatch for id={sqlite_row['id']}: sqlite3={sqlite_payload!r} orm={orm_payload!r}"
            )

    if not admin_user:
        differences.append('get_user_by_username_orm("admin") returned None')
    if admin_user and admin_user.username != "admin":
        differences.append(f'get_user_by_username_orm("admin") returned unexpected username: {admin_user.username!r}')
    if admin_user and not admin_by_id:
        differences.append(f"get_user_by_id_orm({admin_user.id}) returned None")
    if admin_user and admin_by_id and admin_by_id.username != admin_user.username:
        differences.append(
            f"get_user_by_id_orm({admin_user.id}) username mismatch: username lookup={admin_user.username!r} id lookup={admin_by_id.username!r}"
        )

    print(f"Database: {db_path}")
    if differences:
        print("FAIL")
        for diff in differences:
            print(f"- {diff}")
        return 1

    print("PASS")
    print(f"- user count: {len(sqlite_users)}")
    for user in orm_users:
        print(
            f"- id={user.id} username={user.username!r} display_name={user.display_name!r} role={user.role!r} created_at={user.created_at!r}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
