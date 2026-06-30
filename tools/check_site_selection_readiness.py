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
    expected_location: str,
    expected_user_retained: bool,
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
    expect(
        response.headers.get("Location", "").endswith(expected_location),
        f"{label}_login_redirect_changed",
        issues,
    )
    with client.session_transaction() as session:
        if expected_user_retained:
            expect(session.get("user_id") == user["id"], f"{label}_user_id_missing", issues)
            expect(session.get("username") == user["username"], f"{label}_username_missing", issues)
            expect(session.get("role") == user["role"], f"{label}_role_missing", issues)
        else:
            expect(session.get("user_id") is None, f"{label}_user_id_should_be_cleared", issues)
            expect(session.get("username") is None, f"{label}_username_should_be_cleared", issues)
            expect(session.get("role") is None, f"{label}_role_should_be_cleared", issues)

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
        tertiary_site = conn.execute(
            """
            INSERT INTO sites (site_name, site_code, is_active)
            VALUES (?, ?, 1)
            RETURNING id, site_name, site_code, is_active
            """,
            ("__site_selection_tertiary__", "tertiary"),
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
        expect(int(tertiary_site["id"]) in admin_accessible_ids, "admin_missing_tertiary_site_access", issues)
        expect(int(inactive_site["id"]) not in admin_accessible_ids, "admin_should_not_include_inactive_site", issues)

        with module.app.test_request_context("/"):
            admin_result = module.normalize_current_site_for_user(admin)
            print(f"decision_admin_no_session: {admin_result['status']} site_id={admin_result['site_id']}")
            expect(admin_result["status"] == "resolved", "admin_no_session_not_resolved", issues)
            expect(int(admin_result["site_id"]) == default_site_id, "admin_no_session_not_default_site", issues)

        with module.app.test_request_context("/"):
            single_result = module.normalize_current_site_for_user(single_user)
            print(f"decision_single_no_session: {single_result['status']} site_id={single_result['site_id']}")
            expect(single_result["status"] == "resolved", "single_site_user_not_resolved", issues)
            expect(int(single_result["site_id"]) == int(secondary_site["id"]), "single_site_user_not_auto_selected", issues)

        with module.app.test_request_context("/"):
            multi_result = module.normalize_current_site_for_user(multi_user)
            print(
                "decision_multi_no_session: "
                f"{multi_result['status']} site_selection_required={multi_result['site_selection_required']}"
            )
            expect(multi_result["status"] == "site_selection_required", "multi_site_user_should_require_selector", issues)
            expect(module.get_current_site_id() is None, "multi_site_user_should_not_set_current_site", issues)

        with module.app.test_request_context("/"):
            zero_result = module.normalize_current_site_for_user(zero_user)
            print(f"decision_zero_site: {zero_result['status']}")
            expect(zero_result["status"] == "access_denied_no_site_permission", "zero_site_user_should_be_blocked", issues)

        rules = {rule.rule for rule in module.app.url_map.iter_rules()}
        print(f"selector_route_exists: {'/site-selector' in rules}")
        expect("/site-selector" in rules, "site_selector_route_missing", issues)

        client = module.app.test_client()
        expect_login_wiring(
            module,
            user=admin,
            password="admin",
            expected_location="/sheet",
            expected_user_retained=True,
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
            expected_location="/sheet",
            expected_user_retained=True,
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
            expected_location="/site-selector",
            expected_user_retained=True,
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
            expected_location="/login",
            expected_user_retained=False,
            expected_site_id=None,
            expected_site_name=None,
            expected_site_selection_required=None,
            issues=issues,
            label="zero_site",
        )

        with client.session_transaction() as session:
            session.clear()
            session["user_id"] = admin["id"]
            session["username"] = admin["username"]
            session["display_name"] = admin["display_name"] or admin["username"]
            session["role"] = admin["role"]
            session["current_site_id"] = default_site_id
            session["current_site_name"] = module.DEFAULT_SITE_NAME
            session["site_selection_required"] = False
        selector_get = client.get("/site-selector")
        expect(selector_get.status_code == 200, "selector_get_should_render", issues)
        selector_html = selector_get.get_data(as_text=True)
        expect('name="site_id"' in selector_html, "selector_page_missing_site_radio", issues)
        expect('type="radio"' in selector_html, "selector_page_missing_radio_inputs", issues)
        expect('method="post"' in selector_html, "selector_page_missing_post_form", issues)

        with client.session_transaction() as session:
            session.clear()
            session["user_id"] = multi_user["id"]
            session["username"] = multi_user["username"]
            session["display_name"] = multi_user["display_name"] or multi_user["username"]
            session["role"] = multi_user["role"]
            session["site_selection_required"] = True
        recovery_response = client.get("/sheet", follow_redirects=False)
        expect(recovery_response.status_code == 302, "sheet_recovery_should_redirect", issues)
        expect(recovery_response.headers.get("Location", "").endswith("/site-selector"), "sheet_recovery_target_wrong", issues)

        with client.session_transaction() as session:
            session.clear()
            session["user_id"] = multi_user["id"]
            session["username"] = multi_user["username"]
            session["display_name"] = multi_user["display_name"] or multi_user["username"]
            session["role"] = multi_user["role"]
            session["site_selection_required"] = True
        post_ok = client.post("/site-selector", data={"site_id": secondary_site["id"]}, follow_redirects=False)
        expect(post_ok.status_code == 302, "selector_post_should_redirect", issues)
        expect(post_ok.headers.get("Location", "").endswith("/sheet"), "selector_post_redirect_wrong", issues)
        with client.session_transaction() as session:
            expect(session.get("current_site_id") == int(secondary_site["id"]), "selector_post_current_site_id_missing", issues)
            expect(session.get("current_site_name") == str(secondary_site["site_name"]), "selector_post_current_site_name_missing", issues)
            expect(bool(session.get("site_selection_required")) is False, "selector_post_should_clear_selector_flag", issues)

        with client.session_transaction() as session:
            session.clear()
            session["user_id"] = multi_user["id"]
            session["username"] = multi_user["username"]
            session["display_name"] = multi_user["display_name"] or multi_user["username"]
            session["role"] = multi_user["role"]
            session["site_selection_required"] = True
        invalid_post = client.post("/site-selector", data={"site_id": "not-a-number"}, follow_redirects=False)
        expect(invalid_post.status_code == 400, "selector_invalid_post_should_fail_400", issues)
        with client.session_transaction() as session:
            expect(session.get("current_site_id") is None, "selector_invalid_post_should_not_write_site_id", issues)
            expect(session.get("current_site_name") is None, "selector_invalid_post_should_not_write_site_name", issues)
            expect(bool(session.get("site_selection_required")) is True, "selector_invalid_post_should_keep_selector_flag", issues)

        with client.session_transaction() as session:
            session.clear()
            session["user_id"] = single_user["id"]
            session["username"] = single_user["username"]
            session["display_name"] = single_user["display_name"] or single_user["username"]
            session["role"] = single_user["role"]
            session["current_site_id"] = secondary_site["id"]
            session["current_site_name"] = secondary_site["site_name"]
            session["site_selection_required"] = False
        forbidden_post = client.post("/site-selector", data={"site_id": default_site_id}, follow_redirects=False)
        expect(forbidden_post.status_code == 403, "selector_forbidden_post_should_fail_403", issues)
        with client.session_transaction() as session:
            expect(session.get("current_site_id") == int(secondary_site["id"]), "selector_forbidden_post_should_keep_existing_site_id", issues)
            expect(session.get("current_site_name") == str(secondary_site["site_name"]), "selector_forbidden_post_should_keep_existing_site_name", issues)

        with client.session_transaction() as session:
            session.clear()
            session["user_id"] = admin["id"]
            session["username"] = admin["username"]
            session["display_name"] = admin["display_name"] or admin["username"]
            session["role"] = admin["role"]
            session["current_site_id"] = default_site_id
            session["current_site_name"] = module.DEFAULT_SITE_NAME
            session["site_selection_required"] = False
        logout_response = client.post("/logout", follow_redirects=False)
        expect(logout_response.status_code == 302, "logout_should_redirect", issues)
        with client.session_transaction() as session:
            expect("current_site_id" not in session, "logout_should_clear_current_site_id", issues)
            expect("current_site_name" not in session, "logout_should_clear_current_site_name", issues)
            expect("site_selection_required" not in session, "logout_should_clear_site_selection_required", issues)

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
