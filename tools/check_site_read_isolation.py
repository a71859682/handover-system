from __future__ import annotations

import argparse
import hashlib
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
    spec = importlib.util.spec_from_file_location("app_site_read_isolation", str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def create_user(conn: sqlite3.Connection, module, *, username: str) -> sqlite3.Row:
    password_hash = module.generate_password_hash("x")
    conn.execute(
        """
        INSERT INTO users (username, display_name, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (username, username, password_hash, "member"),
    )
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def attach_sheet_clone(conn: sqlite3.Connection, *, source_sheet_id: int, site_id: int, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?)",
        (name, site_id + 100, site_id),
    )
    target_sheet_id = int(cur.lastrowid)

    task_id_map: dict[int, int] = {}
    for task in conn.execute(
        "SELECT col_index, vendor, location, name FROM tasks WHERE sheet_id = ? ORDER BY col_index, id",
        (source_sheet_id,),
    ).fetchall():
        task_cur = conn.execute(
            "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
            (target_sheet_id, task["col_index"], task["vendor"], task["location"], task["name"]),
        )
        task_id_map[int(task["col_index"])] = int(task_cur.lastrowid)

    floor_id_map: dict[int, int] = {}
    unit_id_map: dict[int, int] = {}
    for floor in conn.execute(
        "SELECT * FROM floors WHERE sheet_id = ? ORDER BY sort_order, id",
        (source_sheet_id,),
    ).fetchall():
        floor_cur = conn.execute(
            "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, ?)",
            (target_sheet_id, floor["sort_order"], floor["name"], floor["block_name"], floor["unit_count"]),
        )
        new_floor_id = int(floor_cur.lastrowid)
        floor_id_map[int(floor["id"])] = new_floor_id
        for unit in conn.execute(
            "SELECT * FROM units WHERE floor_id = ? ORDER BY sort_order, id",
            (floor["id"],),
        ).fetchall():
            unit_cur = conn.execute(
                "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
                (new_floor_id, unit["sort_order"], unit["name"]),
            )
            unit_id_map[int(unit["id"])] = int(unit_cur.lastrowid)

    for old_unit_id, new_unit_id in unit_id_map.items():
        extra = conn.execute("SELECT * FROM unit_extra WHERE unit_id = ?", (old_unit_id,)).fetchone()
        if extra is not None:
            conn.execute(
                """
                INSERT INTO unit_extra
                (unit_id, initial_check, recheck_1, recheck_2, handover, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_unit_id,
                    extra["initial_check"],
                    extra["recheck_1"],
                    extra["recheck_2"],
                    extra["handover"],
                    extra["updated_by"],
                    extra["updated_at"],
                ),
            )

    source_tasks = conn.execute(
        "SELECT id, col_index FROM tasks WHERE sheet_id = ?",
        (source_sheet_id,),
    ).fetchall()
    source_task_by_id = {int(row["id"]): int(row["col_index"]) for row in source_tasks}

    for old_unit_id, new_unit_id in unit_id_map.items():
        for progress in conn.execute(
            "SELECT task_id, value, updated_by, updated_at FROM progress WHERE unit_id = ?",
            (old_unit_id,),
        ).fetchall():
            new_task_id = task_id_map[source_task_by_id[int(progress["task_id"])]]
            conn.execute(
                """
                INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    new_unit_id,
                    new_task_id,
                    progress["value"],
                    progress["updated_by"],
                    progress["updated_at"],
                ),
            )

    for field in conn.execute(
        "SELECT * FROM extra_fields WHERE sheet_id = ? ORDER BY sort_order, id",
        (source_sheet_id,),
    ).fetchall():
        conn.execute(
            """
            INSERT INTO extra_fields
            (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_sheet_id,
                field["field_key"],
                field["name"],
                field["field_type"],
                field["sort_order"],
                field["is_builtin"],
                field["active"],
            ),
        )

    for old_unit_id, new_unit_id in unit_id_map.items():
        for extra_value in conn.execute(
            "SELECT field_key, value, updated_by, updated_at FROM unit_extra_values WHERE unit_id = ?",
            (old_unit_id,),
        ).fetchall():
            conn.execute(
                """
                INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    new_unit_id,
                    extra_value["field_key"],
                    extra_value["value"],
                    extra_value["updated_by"],
                    extra_value["updated_at"],
                ),
            )

    return target_sheet_id


def login_session(client, user_row: sqlite3.Row, *, current_site_id=None, current_site_name=None, site_selection_required=False) -> None:
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(user_row["id"])
        session["username"] = str(user_row["username"])
        session["display_name"] = str(user_row["display_name"] or user_row["username"])
        session["role"] = str(user_row["role"])
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
        if current_site_name is not None:
            session["current_site_name"] = str(current_site_name)
        if site_selection_required:
            session["site_selection_required"] = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check site read isolation readiness.")
    parser.parse_args()

    db_path = resolve_db_path()
    source_sha256_before = hashlib.sha256(db_path.read_bytes()).hexdigest() if db_path.exists() else ""
    print("site_read_isolation_scope: sqlite_only")
    print(f"sqlite_source: {db_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    tmpdir = Path(tempfile.mkdtemp(prefix="site-read-isolation-"))
    try:
        analysis_db = tmpdir / "site.db"
        shutil.copy2(db_path, analysis_db)
        print(f"analysis_db_copy: {analysis_db}")
        module = import_app_module(analysis_db)
        module.app.testing = True

        conn = sqlite3.connect(analysis_db)
        conn.row_factory = sqlite3.Row
        issues: list[str] = []

        default_site_id = module.get_default_site_id(conn)
        expect(default_site_id is not None, "default_site_missing", issues)
        default_sheet_row = conn.execute("SELECT id, site_id FROM sheets ORDER BY sort_order, id LIMIT 1").fetchone()
        expect(default_sheet_row is not None, "default_sheet_missing", issues)
        default_sheet_id = int(default_sheet_row["id"]) if default_sheet_row else 0

        secondary_site = conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id, site_name",
            ("__read_secondary__", "read-secondary"),
        ).fetchone()
        default_site_extra_sheet_id = int(
            conn.execute(
                "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                ("__read_default_extra_sheet__", 998, int(default_site_id)),
            ).lastrowid
        )
        secondary_sheet_id = int(
            conn.execute(
                "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                ("__read_secondary_sheet__", 999, int(secondary_site["id"])),
            ).lastrowid
        )
        secondary_extra_sheet_id = int(
            conn.execute(
                "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                ("__read_secondary_extra_sheet__", 1000, int(secondary_site["id"])),
            ).lastrowid
        )
        inactive_site = conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 0) RETURNING id, site_name",
            ("__read_inactive__", "read-inactive"),
        ).fetchone()

        single_user = create_user(conn, module, username="__read_single__")
        multi_user = create_user(conn, module, username="__read_multi__")
        removed_user = create_user(conn, module, username="__read_removed__")
        conn.executemany(
            "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
            [
                (int(single_user["id"]), int(default_site_id), "member"),
                (int(multi_user["id"]), int(default_site_id), "member"),
                (int(multi_user["id"]), int(secondary_site["id"]), "supervisor"),
                (int(removed_user["id"]), int(default_site_id), "member"),
            ],
        )
        conn.commit()

        admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        expect(admin is not None, "admin_missing", issues)

        client = module.app.test_client()

        login_session(
            client,
            admin,
            current_site_id=int(default_site_id),
            current_site_name=str(module.DEFAULT_SITE_NAME),
        )
        default_site_sheet_ids = [
            int(row["id"])
            for row in conn.execute(
                "SELECT id FROM sheets WHERE site_id = ? ORDER BY sort_order, id",
                (default_site_id,),
            ).fetchall()
        ]
        secondary_site_sheet_ids = [secondary_sheet_id, secondary_extra_sheet_id]

        admin_sheet = client.get("/sheet", follow_redirects=False)
        admin_sheet_html = admin_sheet.get_data(as_text=True)
        expect(admin_sheet.status_code == 200, "admin_current_site_sheet_page_failed", issues)
        for sheet_id in default_site_sheet_ids:
            expect(
                f"/sheet/{sheet_id}" in admin_sheet_html,
                "admin_current_site_sheet_list_missing",
                issues,
            )
        for sheet_id, sheet_name in (
            (secondary_sheet_id, "__read_secondary_sheet__"),
            (secondary_extra_sheet_id, "__read_secondary_extra_sheet__"),
        ):
            expect(
                f"/sheet/{sheet_id}" not in admin_sheet_html and sheet_name not in admin_sheet_html,
                "admin_current_site_sheet_list_leak",
                issues,
            )
        with client.session_transaction() as session:
            expect(
                int(session.get("sheet_id") or 0) == default_site_sheet_ids[0],
                "admin_wrong_default_sheet",
                issues,
            )

        admin_grid = client.get(f"/api/grid?sheet_id={default_sheet_id}")
        admin_grid_payload = admin_grid.get_json(silent=True) or {}
        expect(admin_grid.status_code == 200, "admin_current_site_grid_read_failed", issues)
        expect(
            [int(row["id"]) for row in admin_grid_payload.get("sheets", [])] == default_site_sheet_ids,
            "admin_current_site_grid_sheet_list_leak",
            issues,
        )

        admin_cross_sheet = client.get(f"/sheet/{secondary_sheet_id}", follow_redirects=False)
        admin_cross_sheet_html = admin_cross_sheet.get_data(as_text=True)
        expect(admin_cross_sheet.status_code == 302, "admin_cross_site_sheet_read_allowed", issues)
        expect(
            "__read_secondary_sheet__" not in admin_cross_sheet_html
            and f"/sheet/{secondary_sheet_id}" not in admin_cross_sheet_html,
            "admin_cross_site_sheet_content_leak",
            issues,
        )
        admin_cross_grid = client.get(f"/api/grid?sheet_id={secondary_sheet_id}")
        admin_cross_grid_payload = admin_cross_grid.get_json(silent=True) or {}
        expect(admin_cross_grid.status_code == 403, "admin_cross_site_grid_read_allowed", issues)
        expect(
            (admin_cross_grid_payload.get("error") or {}).get("code") == "sheet_not_in_current_site",
            "admin_cross_site_grid_error_code_mismatch",
            issues,
        )
        expect(
            "__read_secondary_sheet__" not in admin_cross_grid.get_data(as_text=True),
            "admin_cross_site_grid_content_leak",
            issues,
        )

        with client.session_transaction() as session:
            session["sheet_id"] = default_site_extra_sheet_id
        admin_switch = client.post(
            "/site-selector",
            data={"site_id": str(secondary_site["id"])},
            follow_redirects=False,
        )
        expect(admin_switch.status_code == 302, "admin_site_switch_failed", issues)
        with client.session_transaction() as session:
            expect("sheet_id" not in session, "admin_stale_sheet_session_retained", issues)
            expect(
                int(session.get("current_site_id") or 0) == int(secondary_site["id"]),
                "admin_site_switch_current_site_mismatch",
                issues,
            )
        switched_sheet = client.get("/sheet", follow_redirects=False)
        switched_sheet_html = switched_sheet.get_data(as_text=True)
        expect(switched_sheet.status_code == 200, "admin_switched_sheet_page_failed", issues)
        for sheet_id in secondary_site_sheet_ids:
            expect(f"/sheet/{sheet_id}" in switched_sheet_html, "admin_switched_site_sheet_missing", issues)
        for sheet_id in default_site_sheet_ids:
            expect(f"/sheet/{sheet_id}" not in switched_sheet_html, "admin_switched_site_sheet_leak", issues)
        with client.session_transaction() as session:
            expect(
                int(session.get("sheet_id") or 0) == secondary_sheet_id,
                "admin_switched_site_wrong_default_sheet",
                issues,
            )

        with client.session_transaction() as session:
            preserved_site_id = int(session["current_site_id"])
            preserved_sheet_id = int(session["sheet_id"])
        invalid_switch = client.post(
            "/site-selector",
            data={"site_id": "999999"},
            follow_redirects=False,
        )
        expect(invalid_switch.status_code == 403, "admin_invalid_site_switch_not_rejected", issues)
        with client.session_transaction() as session:
            expect(
                int(session.get("current_site_id") or 0) == preserved_site_id
                and int(session.get("sheet_id") or 0) == preserved_sheet_id,
                "admin_invalid_site_switch_polluted_session",
                issues,
            )
        inactive_switch = client.post(
            "/site-selector",
            data={"site_id": str(inactive_site["id"])},
            follow_redirects=False,
        )
        expect(inactive_switch.status_code == 403, "admin_inactive_site_switch_not_rejected", issues)
        with client.session_transaction() as session:
            expect(
                int(session.get("current_site_id") or 0) == preserved_site_id
                and int(session.get("sheet_id") or 0) == preserved_sheet_id,
                "admin_inactive_site_switch_polluted_session",
                issues,
            )

        login_session(
            client,
            single_user,
            current_site_id=int(default_site_id),
            current_site_name=str(module.DEFAULT_SITE_NAME),
        )
        single_sheet = client.get("/sheet", follow_redirects=False)
        expect(single_sheet.status_code == 200, "single_site_sheet_failed", issues)
        single_grid = client.get(f"/api/grid?sheet_id={default_sheet_id}")
        expect(single_grid.status_code == 200, "single_site_grid_failed", issues)

        login_session(
            client,
            multi_user,
            current_site_id=int(default_site_id),
            current_site_name=str(module.DEFAULT_SITE_NAME),
        )
        multi_grid = client.get(f"/api/grid?sheet_id={default_sheet_id}")
        expect(multi_grid.status_code == 200, "multi_site_current_site_grid_failed", issues)
        cross_site_grid = client.get(f"/api/grid?sheet_id={secondary_sheet_id}")
        cross_site_payload = cross_site_grid.get_json(silent=True) or {}
        expect(cross_site_grid.status_code == 403, "cross_site_grid_should_be_403", issues)
        expect(
            ((cross_site_payload.get("error") or {}).get("code") == "sheet_not_in_current_site"),
            "cross_site_grid_error_code_mismatch",
            issues,
        )

        with client.session_transaction() as session:
            session["sheet_id"] = secondary_sheet_id
        stale_session_grid = client.get("/api/grid")
        stale_payload = stale_session_grid.get_json(silent=True) or {}
        expect(stale_session_grid.status_code == 403, "stale_session_sheet_id_should_be_403", issues)
        expect(
            ((stale_payload.get("error") or {}).get("code") == "sheet_not_in_current_site"),
            "stale_session_sheet_id_error_code_mismatch",
            issues,
        )

        with client.session_transaction() as session:
            session.pop("current_site_id", None)
            session.pop("current_site_name", None)
        missing_current_site_grid = client.get(f"/api/grid?sheet_id={default_sheet_id}")
        missing_site_payload = missing_current_site_grid.get_json(silent=True) or {}
        expect(missing_current_site_grid.status_code == 403, "missing_current_site_should_be_403", issues)
        expect(
            ((missing_site_payload.get("error") or {}).get("code") == "site_context_invalid"),
            "missing_current_site_error_code_mismatch",
            issues,
        )

        login_session(
            client,
            removed_user,
            current_site_id=int(default_site_id),
            current_site_name=str(module.DEFAULT_SITE_NAME),
        )
        conn.execute("DELETE FROM user_site_permissions WHERE user_id = ?", (int(removed_user["id"]),))
        conn.commit()
        removed_permission_grid = client.get(f"/api/grid?sheet_id={default_sheet_id}")
        removed_payload = removed_permission_grid.get_json(silent=True) or {}
        expect(removed_permission_grid.status_code == 403, "permission_removed_should_be_403", issues)
        expect(
            ((removed_payload.get("error") or {}).get("code") == "site_permission_missing"),
            "permission_removed_error_code_mismatch",
            issues,
        )

        login_session(
            client,
            multi_user,
            current_site_id=int(default_site_id),
            current_site_name=str(module.DEFAULT_SITE_NAME),
        )
        crew_ok = client.get(f"/api/crew-forms?sheet_id={default_sheet_id}")
        crew_forbidden = client.get(f"/api/crew-forms?sheet_id={secondary_sheet_id}")
        crew_forbidden_payload = crew_forbidden.get_json(silent=True) or {}
        expect(crew_ok.status_code == 200, "crew_current_site_read_failed", issues)
        expect(crew_forbidden.status_code == 403, "crew_cross_site_should_be_403", issues)
        expect(
            ((crew_forbidden_payload.get("error") or {}).get("code") == "sheet_not_in_current_site"),
            "crew_cross_site_error_code_mismatch",
            issues,
        )

        non_existent_grid = client.get("/api/grid?sheet_id=999999")
        non_existent_payload = non_existent_grid.get_json(silent=True) or {}
        expect(non_existent_grid.status_code == 404, "missing_sheet_should_be_404", issues)
        expect(
            ((non_existent_payload.get("error") or {}).get("code") == "sheet_not_found"),
            "missing_sheet_error_code_mismatch",
            issues,
        )

        login_session(
            client,
            single_user,
            current_site_id=int(default_site_id),
            current_site_name=str(module.DEFAULT_SITE_NAME),
        )
        unit_row = conn.execute(
            """
            SELECT u.id AS unit_id, t.id AS task_id
            FROM units u
            JOIN floors f ON f.id = u.floor_id
            JOIN tasks t ON t.sheet_id = f.sheet_id
            WHERE f.sheet_id = ?
            ORDER BY u.id, t.id
            LIMIT 1
            """,
            (default_sheet_id,),
        ).fetchone()
        expect(unit_row is not None, "default_sheet_unit_task_missing", issues)
        if unit_row is not None:
            progress_response = client.post(
                "/api/progress",
                json={"unit_id": int(unit_row["unit_id"]), "task_id": int(unit_row["task_id"]), "value": module.DONE_VALUE},
            )
            expect(progress_response.status_code == 200, "progress_write_regression", issues)
            extra_response = client.post(
                "/api/unit-extra",
                json={"unit_id": int(unit_row["unit_id"]), "field": "handover", "value": module.DONE_VALUE},
            )
            expect(extra_response.status_code == 200, "unit_extra_write_regression", issues)

        source_sha256_after = hashlib.sha256(db_path.read_bytes()).hexdigest()
        expect(source_sha256_after == source_sha256_before, "source_db_changed", issues)
        print(f"issues_count: {len(issues)}")
        if issues:
            for issue in issues:
                print(f"ISSUE {issue}")
            raise SystemExit("FAIL site read isolation check failed.")

        print("admin_current_site_sheet_isolation: PASS")
        print("member_current_site_sheet_isolation: PASS")
        print("cross_site_content_non_leakage: PASS")
        print("db_unchanged: PASS")
        print("PASS site read isolation check passed.")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
