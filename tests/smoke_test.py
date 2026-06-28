from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ROOT_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

TABLE_ORDER = [
    "meta",
    "users",
    "sheets",
    "tasks",
    "floors",
    "units",
    "progress",
    "unit_extra",
    "extra_fields",
    "unit_extra_values",
]


def fetch_sqlite_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLE_ORDER}


def redact_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    hostname = parts.hostname or ""
    if parts.port:
        hostname = f"{hostname}:{parts.port}"
    if parts.username:
        netloc = f"{parts.username}:***@{hostname}"
    else:
        netloc = hostname
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def create_sample_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE sheets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER,
            col_index INTEGER NOT NULL UNIQUE,
            vendor TEXT,
            location TEXT,
            name TEXT NOT NULL
        );
        CREATE TABLE floors (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER,
            sort_order INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            block_name TEXT,
            unit_count INTEGER NOT NULL
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY,
            floor_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE progress (
            unit_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            value TEXT NOT NULL,
            updated_by INTEGER,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (unit_id, task_id)
        );
        CREATE TABLE unit_extra (
            unit_id INTEGER PRIMARY KEY,
            initial_check TEXT NOT NULL,
            recheck_1 TEXT NOT NULL,
            recheck_2 TEXT NOT NULL,
            handover TEXT NOT NULL,
            updated_by INTEGER,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE extra_fields (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            name TEXT NOT NULL,
            field_type TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            is_builtin INTEGER NOT NULL,
            active INTEGER NOT NULL
        );
        CREATE TABLE unit_extra_values (
            unit_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_by INTEGER,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (unit_id, field_key)
        );
        """
    )
    conn.execute("INSERT INTO meta (key, value) VALUES ('site_title', 'demo')")
    conn.execute(
        """
        INSERT INTO users (id, username, display_name, password_hash, role, created_at)
        VALUES (1, 'admin', 'Admin', 'hash', 'admin', '2026-06-27T00:00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO users (id, username, display_name, password_hash, role, created_at)
        VALUES (2, 'member', 'Member', 'hash', 'member', '2026-06-27T00:05:00')
        """
    )
    conn.execute(
        "INSERT INTO sheets (id, name, sort_order, created_at) VALUES (1, 'Sheet A', 1, '2026-06-27T00:00:00')"
    )
    conn.execute(
        """
        INSERT INTO tasks (id, sheet_id, col_index, vendor, location, name)
        VALUES (1, 1, 4, 'Vendor', 'Room', 'Task')
        """
    )
    conn.execute(
        """
        INSERT INTO floors (id, sheet_id, sort_order, name, block_name, unit_count)
        VALUES (1, 1, 1, '1F', 'A', 1)
        """
    )
    conn.execute("INSERT INTO units (id, floor_id, sort_order, name) VALUES (1, 1, 1, '101')")
    conn.execute(
        """
        INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at)
        VALUES (1, 1, 'X', 1, '2026-06-27T00:00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO unit_extra (unit_id, initial_check, recheck_1, recheck_2, handover, updated_by, updated_at)
        VALUES (1, '', '', '', 'X', 1, '2026-06-27T00:00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO extra_fields (id, sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (1, 1, 'handover', 'Handover', 'status', 1, 1, 1)
        """
    )
    conn.execute(
        """
        INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at)
        VALUES (1, 'handover', 'X', 1, '2026-06-27T00:00:00')
        """
    )
    conn.commit()
    conn.close()


def run_help(script_name: str) -> None:
    result = subprocess.run(
        [sys.executable, str(TOOLS_DIR / script_name), "--help"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "usage:" not in result.stdout.lower():
        raise AssertionError(f"{script_name} did not print help output.")


def run_script(
    script_name: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(TOOLS_DIR / script_name), *(args or [])],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
        env=merged_env,
    )


def run_floor_helper_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sqlite3
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.update_floor_fields_sqlite(conn, 1, name="1F-updated", block_name="B")
conn.commit()
row = conn.execute("SELECT name, block_name, unit_count FROM floors WHERE id = 1").fetchone()
conn.close()
if row["name"] != "1F-updated" or row["block_name"] != "B" or row["unit_count"] != 1:
    raise SystemExit("floor helper smoke failed")
print("floor helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "floor helper smoke PASS" not in result.stdout:
        raise AssertionError("floor helper smoke subprocess did not report PASS.")


def run_user_helper_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sqlite3
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.update_user_display_name_sqlite(conn, 1, display_name="Admin Updated")
conn.commit()
row = conn.execute("SELECT username, display_name, role FROM users WHERE id = 1").fetchone()
conn.close()
if row["username"] != "admin" or row["display_name"] != "Admin Updated" or row["role"] != "admin":
    raise SystemExit("user helper smoke failed")
print("user helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "user helper smoke PASS" not in result.stdout:
        raise AssertionError("user helper smoke subprocess did not report PASS.")


def run_user_role_helper_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sqlite3
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.update_user_role_sqlite(conn, 2, role="admin")
conn.commit()
row = conn.execute("SELECT username, display_name, role FROM users WHERE id = 2").fetchone()
conn.close()
if row["username"] != "member" or row["display_name"] != "Member" or row["role"] != "admin":
    raise SystemExit("user role helper smoke failed")
print("user role helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "user role helper smoke PASS" not in result.stdout:
        raise AssertionError("user role helper smoke subprocess did not report PASS.")


def run_user_create_helper_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sqlite3
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
user_row = module.create_user_sqlite(
    conn,
    username="new_member",
    display_name="New Member",
    password_hash="hash-created-once",
    role="member",
)
conn.commit()
row = conn.execute(
    "SELECT username, display_name, password_hash, role, created_at FROM users WHERE id = ?",
    (user_row["id"],),
).fetchone()
conn.close()
if row["username"] != "new_member" or row["display_name"] != "New Member" or row["password_hash"] != "hash-created-once" or row["role"] != "member":
    raise SystemExit("user create helper smoke failed")
if user_row["username"] != "new_member" or user_row["password_hash"] != "hash-created-once":
    raise SystemExit("user create helper result mismatch")
if not user_row["created_at"]:
    raise SystemExit("user create helper missing created_at")
print("user create helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "user create helper smoke PASS" not in result.stdout:
        raise AssertionError("user create helper smoke subprocess did not report PASS.")


def run_users_create_readiness_guard_smoke(db_path: Path) -> None:
    from check_users_create_readiness import (
        build_next_sqlite_collision_report,
        fetch_next_sqlite_user_id,
    )

    postgres_rows = {
        3: {
            "id": 3,
            "username": "test",
            "display_name": "Test User",
            "role": "member",
            "created_at": "2026-06-28T00:00:00",
        }
    }

    next_sqlite_user_id = fetch_next_sqlite_user_id(db_path)
    if next_sqlite_user_id != 3:
        raise AssertionError(f"Unexpected next sqlite user id: {next_sqlite_user_id}")

    collision_report = build_next_sqlite_collision_report(next_sqlite_user_id, postgres_rows)
    if collision_report["status"] != "risk":
        raise AssertionError("Expected next sqlite collision status=risk.")
    if collision_report["reason"] != "next_sqlite_user_id_collides_with_postgres":
        raise AssertionError("Expected next sqlite collision reason.")
    if collision_report["postgres_collision"]["username"] != "test":
        raise AssertionError("Expected postgres collision username=test.")

    safe_report = build_next_sqlite_collision_report(next_sqlite_user_id, {})
    if safe_report["status"] != "ok":
        raise AssertionError("Expected next sqlite collision status=ok.")
    if safe_report["reason"] != "next_sqlite_user_id_not_present_in_postgres":
        raise AssertionError("Expected safe next sqlite collision reason.")


def run_users_id_allocation_smoke(db_path: Path) -> None:
    from check_users_id_allocation import fetch_sqlite_users_schema

    report = fetch_sqlite_users_schema(db_path)
    if report["has_autoincrement"]:
        raise AssertionError("Sample SQLite users table should not use AUTOINCREMENT.")
    if report["sqlite_sequence_exists"] and report["sqlite_sequence_value"] is not None:
        raise AssertionError("Sample SQLite users table should not have a sqlite_sequence row.")
    if report["user_count"] != 2:
        raise AssertionError(f"Unexpected sample SQLite user_count: {report['user_count']}")
    if report["max_user_id"] != 2:
        raise AssertionError(f"Unexpected sample SQLite max_user_id: {report['max_user_id']}")
    if report["next_sqlite_user_id"] != 3:
        raise AssertionError(f"Unexpected sample SQLite next user id: {report['next_sqlite_user_id']}")
    if "CREATE TABLE users" not in str(report["create_sql"]):
        raise AssertionError("Expected users schema SQL to be present.")


def run_users_sqlite_sequence_bump_plan_smoke() -> None:
    from plan_users_sqlite_sequence_bump import build_sequence_bump_plan

    sqlite_report = {
        "has_autoincrement": True,
        "sqlite_sequence_exists": True,
        "sqlite_sequence_value": 1,
        "max_user_id": 1,
        "next_sqlite_user_id": 2,
    }
    plan = build_sequence_bump_plan(sqlite_report, postgres_max_user_id=3)
    if not plan["bump_needed"]:
        raise AssertionError("Expected sqlite sequence bump to be needed.")
    if plan["recommended_sqlite_sequence_value"] != 3:
        raise AssertionError(
            f"Unexpected recommended sqlite sequence value: {plan['recommended_sqlite_sequence_value']}"
        )
    if plan["expected_next_sqlite_user_id_after_bump"] != 4:
        raise AssertionError(
            "Unexpected expected next sqlite user id after bump: "
            f"{plan['expected_next_sqlite_user_id_after_bump']}"
        )
    if plan["recommended_sql"] != "UPDATE sqlite_sequence SET seq = 3 WHERE name = 'users';":
        raise AssertionError(f"Unexpected recommended SQL: {plan['recommended_sql']}")

    already_safe_plan = build_sequence_bump_plan(
        {
            "has_autoincrement": True,
            "sqlite_sequence_exists": True,
            "sqlite_sequence_value": 4,
            "max_user_id": 4,
            "next_sqlite_user_id": 5,
        },
        postgres_max_user_id=3,
    )
    if already_safe_plan["bump_needed"]:
        raise AssertionError("Expected sqlite sequence bump to be unnecessary when already safe.")


def run_users_sqlite_sequence_apply_guard_smoke() -> None:
    from bump_users_sqlite_sequence import validate_apply_preconditions

    sqlite_report = {
        "has_autoincrement": True,
        "sqlite_sequence_exists": True,
        "sqlite_sequence_value": 1,
    }
    bump_plan = {
        "recommended_sqlite_sequence_value": 3,
        "expected_next_sqlite_user_id_after_bump": 4,
        "postgres_max_user_id": 3,
    }
    failures = validate_apply_preconditions(sqlite_report, {1: {"username": "admin"}}, bump_plan)
    if failures:
        raise AssertionError(f"Unexpected apply precondition failures: {failures}")

    bad_failures = validate_apply_preconditions(
        {
            "has_autoincrement": True,
            "sqlite_sequence_exists": True,
            "sqlite_sequence_value": 3,
        },
        {1: {"username": "admin"}},
        bump_plan,
    )
    if "target_sequence_value_must_exceed_current_sqlite_sequence_value" not in bad_failures:
        raise AssertionError("Expected apply guard to reject non-increasing sqlite sequence target.")


def run_admin_user_role_update_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sqlite3
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.app.test_client() as client:
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    response = client.post(
        "/admin/users",
        data={"action": "update_user:2", "role": "admin"},
        follow_redirects=True,
    )
    if response.status_code != 200:
        raise SystemExit("admin update other user role request failed")

    response = client.post(
        "/admin/users",
        data={"action": "update_user:1", "role": "member"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    if "本階段不允許修改自己的角色" not in body:
        raise SystemExit("self role update rejection message missing")

conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
other_user = conn.execute("SELECT role FROM users WHERE id = 2").fetchone()
self_user = conn.execute("SELECT role FROM users WHERE id = 1").fetchone()
conn.close()
if other_user["role"] != "admin":
    raise SystemExit("other user role update smoke failed")
if self_user["role"] != "admin":
    raise SystemExit("self role should remain unchanged")
print("admin user role update smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "admin user role update smoke PASS" not in result.stdout:
        raise AssertionError("admin user role update smoke subprocess did not report PASS.")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sample.db"
        create_sample_sqlite(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        counts = fetch_sqlite_counts(conn)
        conn.close()

        if list(counts) != TABLE_ORDER:
            raise AssertionError("Table order changed unexpectedly.")
        expected_counts = {"users": 2}
        if any(count != expected_counts.get(table_name, 1) for table_name, count in counts.items()):
            raise AssertionError(f"Unexpected sample counts: {counts}")

        run_floor_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_user_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_user_role_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_users_create_readiness_guard_smoke(db_path)
        run_users_id_allocation_smoke(db_path)
        run_users_sqlite_sequence_bump_plan_smoke()
        run_users_sqlite_sequence_apply_guard_smoke()
        run_user_create_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_admin_user_role_update_smoke(db_path, Path(tmpdir) / "app-smoke.db")

    if redact_database_url("postgresql://user:secret@localhost:5432/demo") != "postgresql://user:***@localhost:5432/demo":
        raise AssertionError("DATABASE_URL redaction failed.")

    run_help("check_controlled_dual_write.py")
    run_help("check_users_secondary_update.py")
    run_help("check_users_baseline_and_sequence.py")
    run_help("check_users_create_readiness.py")
    run_help("check_users_id_allocation.py")
    run_help("plan_users_sqlite_sequence_bump.py")
    run_help("bump_users_sqlite_sequence.py")
    run_help("fix_users_postgres_sequence.py")
    run_help("backfill_users_display_name_to_postgres.py")

    controlled_result = run_script("check_controlled_dual_write.py")
    if "PASS controlled dual-write floors/users update/create wiring looks correct." not in controlled_result.stdout:
        raise AssertionError("check_controlled_dual_write.py did not report PASS.")

    floors_result = run_script("check_floors_secondary_update.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in floors_result.stdout or "PASS" not in floors_result.stdout:
        raise AssertionError("check_floors_secondary_update.py did not report expected PASS without DATABASE_URL.")

    users_result = run_script("check_users_secondary_update.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in users_result.stdout or "PASS" not in users_result.stdout:
        raise AssertionError("check_users_secondary_update.py did not report expected PASS without DATABASE_URL.")
    users_role_result = run_script("check_users_secondary_update.py", args=["--field", "role"], env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in users_role_result.stdout or "PASS" not in users_role_result.stdout:
        raise AssertionError("check_users_secondary_update.py --field role did not report expected PASS without DATABASE_URL.")
    baseline_result = run_script("check_users_baseline_and_sequence.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in baseline_result.stdout or "PASS" not in baseline_result.stdout:
        raise AssertionError("check_users_baseline_and_sequence.py did not report expected PASS without DATABASE_URL.")
    readiness_result = run_script("check_users_create_readiness.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in readiness_result.stdout or "PASS" not in readiness_result.stdout:
        raise AssertionError("check_users_create_readiness.py did not report expected PASS without DATABASE_URL.")
    readiness_probe_result = run_script(
        "check_users_create_readiness.py",
        args=["--username", "dw_test_create_probe"],
        env={"DATABASE_URL": ""},
    )
    if "DATABASE_URL is not configured." not in readiness_probe_result.stdout or "PASS" not in readiness_probe_result.stdout:
        raise AssertionError(
            "check_users_create_readiness.py --username dw_test_create_probe did not report expected PASS without DATABASE_URL."
        )
    allocation_result = run_script("check_users_id_allocation.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in allocation_result.stdout or "PASS" not in allocation_result.stdout:
        raise AssertionError("check_users_id_allocation.py did not report expected PASS without DATABASE_URL.")
    plan_result = run_script("plan_users_sqlite_sequence_bump.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in plan_result.stdout or "PASS" not in plan_result.stdout:
        raise AssertionError("plan_users_sqlite_sequence_bump.py did not report expected PASS without DATABASE_URL.")
    if "DRY RUN ONLY. No data was modified." not in plan_result.stdout:
        raise AssertionError("plan_users_sqlite_sequence_bump.py did not report dry-run-only status.")
    bump_result = run_script("bump_users_sqlite_sequence.py", env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in bump_result.stdout or "PASS" not in bump_result.stdout:
        raise AssertionError("bump_users_sqlite_sequence.py did not report expected PASS without DATABASE_URL.")
    if "DRY RUN ONLY. No data was modified." not in bump_result.stdout:
        raise AssertionError("bump_users_sqlite_sequence.py did not report dry-run-only status.")
    bump_apply_reject = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "bump_users_sqlite_sequence.py"),
            "--apply",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": ""},
    )
    if bump_apply_reject.returncode == 0:
        raise AssertionError("bump_users_sqlite_sequence.py --apply should fail without DATABASE_URL.")
    if "FAIL users sqlite sequence bump apply requires DATABASE_URL." not in bump_apply_reject.stdout:
        raise AssertionError("bump_users_sqlite_sequence.py --apply did not report expected DATABASE_URL guard.")
    fix_sequence_result = run_script("fix_users_postgres_sequence.py", args=["--dry-run"], env={"DATABASE_URL": ""})
    if "DATABASE_URL is not configured." not in fix_sequence_result.stdout or "PASS" not in fix_sequence_result.stdout:
        raise AssertionError("fix_users_postgres_sequence.py --dry-run did not report expected PASS without DATABASE_URL.")

    backfill_result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "backfill_users_display_name_to_postgres.py"),
            "--dry-run",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "DATABASE_URL": ""},
    )
    if "DATABASE_URL is not configured." not in backfill_result.stdout or "PASS" not in backfill_result.stdout:
        raise AssertionError(
            "backfill_users_display_name_to_postgres.py did not report expected PASS without DATABASE_URL."
        )

    print("smoke_test PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
