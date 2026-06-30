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
    module_name = "app_site_selection_readiness"
    spec = importlib.util.spec_from_file_location(module_name, str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def expect(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def expect_login_wiring(
    module,
    *,
    user: sqlite3.Row,
    password: str,
    expected_site_id: int | None,
    expected_site_name: str | None,
    expected_site_selection_required: bool | None,
    issues: list[str],
    label: str,
) -> None:
    client = module.app.test_client()
    response = client.post(
        "/login",
        data={
            "username": user["username"],
            "display_name": user["display_name"] or user["username"],
            "password": password,
        },
        follow_redirects=False,
    )
    expect(response.status_code == 302, f"{label}_login_not_redirected", issues)
    expect(response.headers.get("Location", "").endswith("/sheet"), f"{label}_login_redirect_changed", issues)
    with client.session_transaction() as session:
        expect(session.get("user_id") == user["id"], f"{label}_user_id_missing", issues)
        expect(session.get("username") == user["username"], f"{label}_username_missing", issues)
        expect(session.get("role") == user["role"], f"{label}_role_missing", issues)
        expect(session.get("current_site_id") == expected_site_id, f"{label}_current_site_id_mismatch", issues)
        expect(session.get("current_site_name") == expected_site_name, f"{label}_current_site_name_mismatch", issues)
        if expected_site_selection_required is None:
            expect(
                session.get("site_selection_required") is None,
                f"{label}_site_selection_required_should_be_absent",
                issues,
            )
        else:
            expect(
                bool(session.get("site_selection_required")) is expected_site_selection_required,
                f"{label}_site_selection_required_mismatch",
                issues,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check internal site selection readiness.")
    parser.parse_args()

    db_path = resolve_db_path()
    print("site_selection_readiness_scope: sqlite_only")
    print(f"sqlite_source: {db_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    tmpdir = Path(tempfile.mkdtemp(prefix="site-selection-readiness-"))
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
        expect("sites" in table_names, "missing_table:sites", issues)
        expect("user_site_permissions" in table_names, "missing_table:user_site_permissions", issues)

        default_site_rows = conn.execute(
            "SELECT id, site_name, is_active FROM sites WHERE site_name = ?",
            (module.DEFAULT_SITE_NAME,),
        ).fetchall()
        print(f"default_site_exists: {bool(default_site_rows)}")
        print(f"default_site_unique: {len(default_site_rows) == 1}")
        expect(bool(default_site_rows), "default_site_missing", issues)
        expect(len(default_site_rows) == 1, "default_site_not_unique", issues)
        default_site_id = int(default_site_rows[0]["id"]) if default_site_rows else None

        sheets_total = conn.execute("SELECT COUNT(*) AS count FROM sheets").fetchone()["count"]
        sheets_non_null = conn.execute("SELECT COUNT(*) AS count FROM sheets WHERE site_id IS NOT NULL").fetchone()["count"]
        sheets_valid_fk = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM sheets s
            JOIN sites st ON st.id = s.site_id
            """
        ).fetchone()["count"]
        print(f"sheets_count: {sheets_total}")
        print(f"sheets_site_id_non_null_count: {sheets_non_null}")
        print(f"sheets_site_id_existing_site_count: {sheets_valid_fk}")
        expect(sheets_total == sheets_non_null, "sheet_site_id_null_found", issues)
        expect(sheets_total == sheets_valid_fk, "sheet_site_id_missing_site_reference", issues)

        admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        print(f"admin_exists: {admin is not None}")
        expect(admin is not None, "admin_missing", issues)

        secondary_site = conn.execute(
            """
            INSERT INTO sites (site_name, site_code, is_active)
            VALUES (?, ?, 1)
            RETURNING id, site_name, site_code, is_active
            """,
            ("__site_selection_secondary__", "secondary"),
        ).fetchone()
        inactive_site = conn.execute(
            """
            INSERT INTO sites (site_name, site_code, is_active)
            VALUES (?, ?, 0)
            RETURNING id, site_name, site_code, is_active
            """,
            ("__site_selection_inactive__", "inactive"),
        ).fetchone()

        single_user = create_user(conn, module, username="__site_single__", role="member")
        multi_user = create_user(conn, module, username="__site_multi__", role="member")
        zero_user = create_user(conn, module, username="__site_zero__", role="member")

        conn.executemany(
            """
            INSERT INTO user_site_permissions (user_id, site_id, role)
            VALUES (?, ?, ?)
            """,
            [
                (single_user["id"], secondary_site["id"], "member"),
                (multi_user["id"], default_site_id, "member"),
                (multi_user["id"], secondary_site["id"], "supervisor"),
            ],
        )
        conn.commit()

        admin_accessible = module.get_user_accessible_sites(admin["id"])
        admin_accessible_ids = {int(site["id"]) for site in admin_accessible}
        print(f"admin_accessible_site_ids: {sorted(admin_accessible_ids)}")
        expect(module.is_global_admin(admin), "admin_not_recognized_as_global_admin", issues)
        expect(default_site_id in admin_accessible_ids, "admin_missing_default_site_access", issues)
        expect(int(secondary_site["id"]) in admin_accessible_ids, "admin_missing_secondary_site_access", issues)
        expect(int(inactive_site["id"]) not in admin_accessible_ids, "admin_should_not_include_inactive_site", issues)
        expect(module.user_can_access_site(admin["id"], int(secondary_site["id"])), "admin_cannot_access_active_site", issues)
        expect(
            not module.user_can_access_site(admin["id"], int(inactive_site["id"])),
            "admin_should_not_access_inactive_site",
            issues,
        )
        expect(module.get_user_role_for_site(admin["id"], int(secondary_site["id"])) == "admin", "admin_role_lookup_failed", issues)

        single_accessible = module.get_user_accessible_sites(single_user["id"])
        multi_accessible = module.get_user_accessible_sites(multi_user["id"])
        zero_accessible = module.get_user_accessible_sites(zero_user["id"])
        print(f"single_accessible_site_ids: {[site['id'] for site in single_accessible]}")
        print(f"multi_accessible_site_ids: {[site['id'] for site in multi_accessible]}")
        print(f"zero_accessible_site_count: {len(zero_accessible)}")

        with module.app.test_request_context("/"):
            admin_result = module.normalize_current_site_for_user(admin)
            print(f"decision_admin_no_session: {admin_result['status']} site_id={admin_result['site_id']}")
            expect(admin_result["status"] == "resolved", "admin_no_session_not_resolved", issues)
            expect(int(admin_result["site_id"]) == default_site_id, "admin_no_session_not_default_site", issues)
            expect(module.get_current_site_id() == default_site_id, "admin_session_not_written", issues)

        with module.app.test_request_context("/"):
            module.set_current_site_id(int(inactive_site["id"]))
            admin_stale = module.normalize_current_site_for_user(admin)
            print(f"decision_admin_stale: {admin_stale['status']} site_id={admin_stale['site_id']}")
            expect(admin_stale["status"] == "resolved", "admin_stale_not_resolved", issues)
            expect(int(admin_stale["site_id"]) == default_site_id, "admin_stale_not_reset_to_default", issues)

        with module.app.test_request_context("/"):
            single_result = module.normalize_current_site_for_user(single_user)
            print(f"decision_single_no_session: {single_result['status']} site_id={single_result['site_id']}")
            expect(single_result["status"] == "resolved", "single_site_user_not_resolved", issues)
            expect(
                int(single_result["site_id"]) == int(secondary_site["id"]),
                "single_site_user_not_auto_selected",
                issues,
            )

        with module.app.test_request_context("/"):
            module.set_current_site_id(int(inactive_site["id"]))
            single_stale = module.normalize_current_site_for_user(single_user)
            print(f"decision_single_stale: {single_stale['status']} site_id={single_stale['site_id']}")
            expect(single_stale["status"] == "resolved", "single_site_stale_not_resolved", issues)
            expect(
                int(single_stale["site_id"]) == int(secondary_site["id"]),
                "single_site_stale_not_reset_to_only_site",
                issues,
            )

        with module.app.test_request_context("/"):
            multi_result = module.normalize_current_site_for_user(multi_user)
            print(
                "decision_multi_no_session: "
                f"{multi_result['status']} site_selection_required={multi_result['site_selection_required']}"
            )
            expect(multi_result["status"] == "site_selection_required", "multi_site_user_should_require_selector", issues)
            expect(module.get_current_site_id() is None, "multi_site_user_should_not_set_current_site", issues)
            expect(bool(module.session.get("site_selection_required")) is True, "multi_site_user_missing_selector_flag", issues)

        with module.app.test_request_context("/"):
            module.set_current_site_id(int(inactive_site["id"]))
            multi_stale = module.normalize_current_site_for_user(multi_user)
            print(
                "decision_multi_stale: "
                f"{multi_stale['status']} site_selection_required={multi_stale['site_selection_required']}"
            )
            expect(multi_stale["status"] == "site_selection_required", "multi_site_stale_should_require_selector", issues)
            expect(module.get_current_site_id() is None, "multi_site_stale_should_clear_current_site", issues)
            expect(bool(module.session.get("site_selection_required")) is True, "multi_site_stale_missing_selector_flag", issues)

        with module.app.test_request_context("/"):
            zero_result = module.normalize_current_site_for_user(zero_user)
            print(f"decision_zero_site: {zero_result['status']}")
            expect(
                zero_result["status"] == "access_denied_no_site_permission",
                "zero_site_user_should_be_blocked",
                issues,
            )
            expect(module.get_current_site_id() is None, "zero_site_user_should_not_keep_current_site", issues)

        print("login_wiring_checks: start")
        expect_login_wiring(
            module,
            user=admin,
            password="admin",
            expected_site_id=default_site_id,
            expected_site_name=module.DEFAULT_SITE_NAME,
            expected_site_selection_required=False,
            issues=issues,
            label="admin",
        )
        expect_login_wiring(
            module,
            user=single_user,
            password="x",
            expected_site_id=int(secondary_site["id"]),
            expected_site_name=str(secondary_site["site_name"]),
            expected_site_selection_required=False,
            issues=issues,
            label="single_site",
        )
        expect_login_wiring(
            module,
            user=multi_user,
            password="x",
            expected_site_id=None,
            expected_site_name=None,
            expected_site_selection_required=True,
            issues=issues,
            label="multi_site",
        )
        expect_login_wiring(
            module,
            user=zero_user,
            password="x",
            expected_site_id=None,
            expected_site_name=None,
            expected_site_selection_required=None,
            issues=issues,
            label="zero_site",
        )
        print("login_wiring_checks: complete")

        conn.close()

        if issues:
            print("FAIL site selection readiness check:")
            for issue in issues:
                print(f"- {issue}")
            return 1

        print("PASS site selection readiness check passed.")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
