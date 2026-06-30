from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "site.db"


def resolve_db_path() -> Path:
    raw = os.environ.get("APP_DB_PATH")
    return Path(raw).expanduser().resolve() if raw else DEFAULT_DB_PATH.resolve()


def import_app_module(db_path: Path):
    os.environ["APP_DB_PATH"] = str(db_path)
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    spec = importlib.util.spec_from_file_location("app_site_permission_readiness", str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def create_user(conn: sqlite3.Connection, module, *, username: str, role: str = "member") -> sqlite3.Row:
    password_hash = module.generate_password_hash("x")
    conn.execute(
        """
        INSERT INTO users (username, display_name, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (username, username, password_hash, role),
    )
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def login_admin(client) -> None:
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check internal site permission management readiness.")
    parser.parse_args()

    db_path = resolve_db_path()
    print("site_permission_readiness_scope: sqlite_only")
    print(f"sqlite_source: {db_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    tmpdir = Path(tempfile.mkdtemp(prefix="site-permission-readiness-"))
    try:
        analysis_db = tmpdir / "site.db"
        shutil.copy2(db_path, analysis_db)
        print(f"analysis_db_copy: {analysis_db}")
        module = import_app_module(analysis_db)

        conn = sqlite3.connect(analysis_db)
        conn.row_factory = sqlite3.Row
        issues: list[str] = []

        table_names = {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        expect("user_site_permissions" in table_names, "missing_table:user_site_permissions", issues)
        print(f"user_site_permissions_table_exists: {'user_site_permissions' in table_names}")

        unique_indexes = conn.execute("PRAGMA index_list('user_site_permissions')").fetchall()
        unique_found = False
        for index_row in unique_indexes:
            if int(index_row["unique"]) != 1:
                continue
            columns = [
                info["name"]
                for info in conn.execute(f"PRAGMA index_info('{index_row['name']}')").fetchall()
            ]
            if columns == ["user_id", "site_id"]:
                unique_found = True
                break
        print(f"user_site_permissions_unique_user_site: {unique_found}")
        expect(unique_found, "missing_unique:user_site_permissions.user_id_site_id", issues)

        default_site_id = module.get_default_site_id(conn)
        expect(default_site_id is not None, "default_site_missing", issues)

        secondary_site = conn.execute(
            """
            INSERT INTO sites (site_name, site_code, is_active)
            VALUES (?, ?, 1)
            RETURNING id, site_name
            """,
            ("__permission_secondary__", "perm-secondary"),
        ).fetchone()
        inactive_site = conn.execute(
            """
            INSERT INTO sites (site_name, site_code, is_active)
            VALUES (?, ?, 0)
            RETURNING id, site_name
            """,
            ("__permission_inactive__", "perm-inactive"),
        ).fetchone()

        member = create_user(conn, module, username="__perm_member__", role="member")
        other_member = create_user(conn, module, username="__perm_member_two__", role="member")
        conn.commit()

        client = module.app.test_client()
        login_admin(client)

        users_page = client.get("/admin/users")
        page_text = users_page.get_data(as_text=True)
        expect(users_page.status_code == 200, "admin_users_page_failed", issues)
        expect("Global Admin（全站可存取）" in page_text, "admin_compatibility_text_missing", issues)

        create_response = client.post(
            "/admin/users",
            data={
                "action": f"add_site_permission:{member['id']}",
                "site_id": str(secondary_site["id"]),
                "site_role": "supervisor",
            },
            follow_redirects=False,
        )
        expect(create_response.status_code == 302, "permission_create_redirect_failed", issues)
        created_permission = conn.execute(
            "SELECT * FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
            (member["id"], secondary_site["id"]),
        ).fetchone()
        expect(created_permission is not None, "permission_create_failed", issues)
        if created_permission is not None:
            print(f"permission_create_role: {created_permission['role']}")
            expect(created_permission["role"] == "supervisor", "permission_create_role_mismatch", issues)

        duplicate_response = client.post(
            "/admin/users",
            data={
                "action": f"add_site_permission:{member['id']}",
                "site_id": str(secondary_site["id"]),
                "site_role": "member",
            },
            follow_redirects=False,
        )
        expect(duplicate_response.status_code == 302, "duplicate_permission_redirect_failed", issues)
        duplicate_count = conn.execute(
            "SELECT COUNT(*) AS count FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
            (member["id"], secondary_site["id"]),
        ).fetchone()["count"]
        print(f"duplicate_permission_prevented: {duplicate_count == 1}")
        expect(duplicate_count == 1, "duplicate_permission_not_prevented", issues)

        invalid_user_response = client.post(
            "/admin/users",
            data={
                "action": "add_site_permission:999999",
                "site_id": str(secondary_site["id"]),
                "site_role": "member",
            },
            follow_redirects=False,
        )
        expect(invalid_user_response.status_code == 302, "invalid_user_redirect_failed", issues)
        invalid_user_exists = conn.execute(
            "SELECT 1 FROM user_site_permissions WHERE user_id = 999999"
        ).fetchone()
        print(f"invalid_user_rejected: {invalid_user_exists is None}")
        expect(invalid_user_exists is None, "invalid_user_not_rejected", issues)

        invalid_site_response = client.post(
            "/admin/users",
            data={
                "action": f"add_site_permission:{member['id']}",
                "site_id": str(inactive_site["id"]),
                "site_role": "member",
            },
            follow_redirects=False,
        )
        expect(invalid_site_response.status_code == 302, "inactive_site_redirect_failed", issues)
        inactive_site_permission = conn.execute(
            "SELECT 1 FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
            (member["id"], inactive_site["id"]),
        ).fetchone()
        print(f"invalid_site_rejected: {inactive_site_permission is None}")
        expect(inactive_site_permission is None, "inactive_site_not_rejected", issues)

        invalid_role_response = client.post(
            "/admin/users",
            data={
                "action": f"add_site_permission:{other_member['id']}",
                "site_id": str(secondary_site["id"]),
                "site_role": "invalid",
            },
            follow_redirects=False,
        )
        expect(invalid_role_response.status_code == 302, "invalid_role_redirect_failed", issues)
        invalid_role_permission = conn.execute(
            "SELECT 1 FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
            (other_member["id"], secondary_site["id"]),
        ).fetchone()
        print(f"invalid_role_rejected: {invalid_role_permission is None}")
        expect(invalid_role_permission is None, "invalid_role_not_rejected", issues)

        admin_permission_response = client.post(
            "/admin/users",
            data={
                "action": "add_site_permission:1",
                "site_id": str(secondary_site["id"]),
                "site_role": "member",
            },
            follow_redirects=False,
        )
        expect(admin_permission_response.status_code == 302, "admin_permission_redirect_failed", issues)
        admin_permission = conn.execute(
            "SELECT 1 FROM user_site_permissions WHERE user_id = 1 AND site_id = ?",
            (secondary_site["id"],),
        ).fetchone()
        print(f"admin_compatibility_preserved: {admin_permission is None}")
        expect(admin_permission is None, "admin_should_not_receive_site_permission_rows", issues)

        expect(created_permission is not None, "permission_row_missing_before_update", issues)
        if created_permission is not None:
            update_response = client.post(
                "/admin/users",
                data={
                    "action": f"update_site_permission:{created_permission['id']}",
                    "site_role": "member",
                },
                follow_redirects=False,
            )
            expect(update_response.status_code == 302, "permission_update_redirect_failed", issues)
            updated_permission = conn.execute(
                "SELECT role FROM user_site_permissions WHERE id = ?",
                (created_permission["id"],),
            ).fetchone()
            print(f"permission_update_role: {updated_permission['role'] if updated_permission else 'missing'}")
            expect(
                updated_permission is not None and updated_permission["role"] == "member",
                "permission_update_failed",
                issues,
            )

            delete_response = client.post(
                "/admin/users",
                data={"action": f"delete_site_permission:{created_permission['id']}"},
                follow_redirects=False,
            )
            expect(delete_response.status_code == 302, "permission_delete_redirect_failed", issues)
            deleted_permission = conn.execute(
                "SELECT 1 FROM user_site_permissions WHERE id = ?",
                (created_permission["id"],),
            ).fetchone()
            print(f"permission_delete_success: {deleted_permission is None}")
            expect(deleted_permission is None, "permission_delete_failed", issues)

        non_admin_client = module.app.test_client()
        with non_admin_client.session_transaction() as session:
            session["user_id"] = member["id"]
            session["username"] = member["username"]
            session["display_name"] = member["display_name"]
            session["role"] = member["role"]
        forbidden_response = non_admin_client.post(
            "/admin/users",
            data={
                "action": f"add_site_permission:{other_member['id']}",
                "site_id": str(default_site_id),
                "site_role": "member",
            },
            follow_redirects=False,
        )
        print(f"non_admin_forbidden_status: {forbidden_response.status_code}")
        expect(forbidden_response.status_code in (302, 403), "non_admin_permission_crud_not_blocked", issues)

        if issues:
            print("FAIL site permission readiness check failed.")
            for issue in issues:
                print(f"- {issue}")
            return 1

        print("PASS site permission readiness check passed.")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
