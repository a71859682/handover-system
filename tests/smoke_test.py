from __future__ import annotations

import os
import shutil
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


def run_users_template_delete_ui_smoke() -> None:
    template_path = ROOT_DIR / "templates" / "users.html"
    template = template_path.read_text(encoding="utf-8")
    required_snippets = [
        "delete_user:{{ user.id }}",
        "user.username.startswith('dw_test_')",
        "user.id != 1",
        "user.username != 'admin'",
        "user.role != 'admin'",
        "users delete dual-write",
        "&#21034;&#38500;",
    ]
    for snippet in required_snippets:
        if snippet not in template:
            raise AssertionError(f"users.html missing delete UI snippet: {snippet}")
    if "password_hash" in template:
        raise AssertionError("users.html delete UI should not include password_hash.")


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


def run_user_delete_helper_smoke(db_path: Path, app_db_path: Path) -> None:
    isolated_db_path = db_path.with_name(f"{db_path.stem}-delete{db_path.suffix}")
    if isolated_db_path.exists():
        isolated_db_path.unlink()
    create_sample_sqlite(isolated_db_path)
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
deleted_user_row = module.delete_user_sqlite(conn, 2)
conn.commit()
row = conn.execute("SELECT COUNT(*) AS count FROM users WHERE id = 2").fetchone()
conn.close()
if row["count"] != 0:
    raise SystemExit("user delete helper did not delete the target row")
if "password_hash" in deleted_user_row:
    raise SystemExit("user delete helper leaked password_hash")
if deleted_user_row["username"] != "member" or deleted_user_row["role"] != "member":
    raise SystemExit("user delete helper returned unexpected row")
print("user delete helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(isolated_db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "user delete helper smoke PASS" not in result.stdout:
        raise AssertionError("user delete helper smoke subprocess did not report PASS.")
    isolated_db_path.unlink(missing_ok=True)


def run_protected_user_delete_guard_smoke(db_path: Path, app_db_path: Path) -> None:
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
try:
    module.delete_user_sqlite(conn, 1)
except ValueError:
    pass
else:
    raise SystemExit("protected user delete guard did not reject admin")
row = conn.execute("SELECT username, role FROM users WHERE id = 1").fetchone()
conn.close()
if row["username"] != "admin" or row["role"] != "admin":
    raise SystemExit("protected user delete guard changed admin row")
print("protected user delete guard smoke PASS")
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
    if "protected user delete guard smoke PASS" not in result.stdout:
        raise AssertionError("protected user delete guard smoke subprocess did not report PASS.")


def run_user_delete_dual_write_dry_run_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
os.environ["DUAL_WRITE_ENABLED"] = "true"
os.environ["DUAL_WRITE_DRY_RUN"] = "true"
os.environ["DUAL_WRITE_STRICT"] = "false"
os.environ["USE_SQLALCHEMY_WRITES"] = "false"
os.environ["DUAL_WRITE_TABLES"] = "meta,sheets,extra_fields,units,floors,tasks,users"
spec.loader.exec_module(module)
logs = []
module.dual_write_log = logs.append

def fail_connection():
    raise RuntimeError("postgres connection should not be used in dry-run delete smoke")

module.get_primary_postgres_connection = fail_connection
module.maybe_dual_write_user_delete(
    {
        "id": 5,
        "username": "dw_test_delete_real_20260628",
        "display_name": "Delete Real",
        "role": "member",
        "created_at": "2026-06-28 15:17:02",
    }
)
joined = "\\n".join(logs)
if "DUAL_WRITE_DRY_RUN operation=delete table=users user_id=5 username='dw_test_delete_real_20260628'" not in joined:
    raise SystemExit("delete dry-run log missing")
if "dry_run=true postgres_result=success" not in joined:
    raise SystemExit("delete dry-run success log missing")
if "password_hash" in joined:
    raise SystemExit("delete dry-run log leaked password_hash")
print("user delete dual write dry-run smoke PASS")
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
    if "user delete dual write dry-run smoke PASS" not in result.stdout:
        raise AssertionError("user delete dual write dry-run smoke subprocess did not report PASS.")


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


def run_users_create_readiness_autoincrement_sequence_smoke() -> None:
    from check_users_create_readiness import (
        build_next_sqlite_collision_report,
        fetch_next_sqlite_user_id,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "autoincrement-users.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users (id, username, display_name, password_hash, role, created_at)
            VALUES (1, 'admin', 'Admin', 'hash', 'admin', '2026-06-28T00:00:00');
            UPDATE sqlite_sequence SET seq = 3 WHERE name = 'users';
            """
        )
        conn.commit()
        conn.close()

        next_sqlite_user_id = fetch_next_sqlite_user_id(db_path)
        if next_sqlite_user_id != 4:
            raise AssertionError(
                "Expected AUTOINCREMENT sqlite sequence guard to return next user id 4, "
                f"got {next_sqlite_user_id}."
            )

        postgres_rows = {
            2: {
                "id": 2,
                "username": "zhong",
                "display_name": "zhong",
                "role": "admin",
                "created_at": "2026-06-25T15:35:52",
            },
            3: {
                "id": 3,
                "username": "test",
                "display_name": "test",
                "role": "member",
                "created_at": "2026-06-27T04:20:36",
            },
        }
        collision_report = build_next_sqlite_collision_report(next_sqlite_user_id, postgres_rows)
        if collision_report["status"] != "ok":
            raise AssertionError("Expected bumped AUTOINCREMENT sqlite next id to avoid PostgreSQL collision.")
        if collision_report["reason"] != "next_sqlite_user_id_not_present_in_postgres":
            raise AssertionError("Expected bumped AUTOINCREMENT sqlite next id to report no collision.")
        if collision_report["postgres_collision"] is not None:
            raise AssertionError("Expected no PostgreSQL collision row for bumped AUTOINCREMENT sqlite next id.")


def run_users_delete_readiness_guard_smoke(db_path: Path) -> None:
    script = """
import os
import subprocess
import sys
from pathlib import Path

root_dir, sample_db_path = sys.argv[1:3]
tool_path = Path(root_dir) / "tools" / "check_users_delete_readiness.py"
base_env = os.environ.copy()
base_env["APP_DB_PATH"] = sample_db_path
base_env["DATABASE_URL"] = ""
base_env["DUAL_WRITE_ENABLED"] = "true"
base_env["DUAL_WRITE_DRY_RUN"] = "false"
base_env["DUAL_WRITE_STRICT"] = "false"
base_env["USE_SQLALCHEMY_WRITES"] = "false"
base_env["DUAL_WRITE_TABLES"] = "meta,sheets,extra_fields,units,floors,tasks,users"

result_ok = subprocess.run(
    [sys.executable, str(tool_path), "--username", "dw_test_delete_real_20260628"],
    cwd=root_dir,
    capture_output=True,
    text=True,
    env=base_env,
)
if result_ok.returncode != 0 or "PASS users delete readiness check passed." not in result_ok.stdout:
    raise SystemExit("delete readiness allowed-user smoke failed")

result_admin = subprocess.run(
    [sys.executable, str(tool_path), "--username", "admin"],
    cwd=root_dir,
    capture_output=True,
    text=True,
    env=base_env,
)
if result_admin.returncode == 0 or "FAIL users delete readiness: protected_user" not in result_admin.stdout:
    raise SystemExit("delete readiness protected-user smoke failed")

print("users delete readiness smoke PASS")
"""
    isolated_db_path = db_path.parent / "delete-readiness-sample.db"
    shutil.copy2(db_path, isolated_db_path)
    conn = sqlite3.connect(isolated_db_path)
    conn.execute(
        """
        INSERT INTO users (id, username, display_name, password_hash, role, created_at)
        VALUES (3, 'dw_test_delete_real_20260628', 'Delete Real', 'hash', 'member', '2026-06-28T00:10:00')
        """
    )
    conn.commit()
    conn.close()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(ROOT_DIR),
            str(isolated_db_path),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "users delete readiness smoke PASS" not in result.stdout:
        raise AssertionError("users delete readiness smoke subprocess did not report PASS.")


def run_users_delete_submit_verifier_smoke(db_path: Path) -> None:
    script = """
import contextlib
import copy
import importlib.util
import io
import sys
from pathlib import Path

root_dir, sample_db_path = sys.argv[1:3]
tool_path = Path(root_dir) / "tools" / "check_users_delete_submit.py"
spec = importlib.util.spec_from_file_location("check_users_delete_submit_under_test", str(tool_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

module.DUAL_WRITE_ENABLED = True
module.DUAL_WRITE_DRY_RUN = False
module.DUAL_WRITE_STRICT = False
module.USE_SQLALCHEMY_WRITES = False
module.DUAL_WRITE_TABLES = ("meta", "sheets", "extra_fields", "units", "floors", "tasks", "users")
module.DATABASE_URL = "postgresql://user:secret@localhost:5432/demo"
module.resolve_sqlite_source_path = lambda: Path(sample_db_path)

initial_state = {
    "sqlite": {
        1: {
            "id": 1,
            "username": "admin",
            "display_name": "Admin",
            "role": "admin",
            "created_at": "2026-06-28T00:00:00",
        },
        2: {
            "id": 2,
            "username": "member",
            "display_name": "Member",
            "role": "member",
            "created_at": "2026-06-28T00:05:00",
        },
        3: {
            "id": 3,
            "username": "dw_test_delete_real_20260628",
            "display_name": "Delete Real",
            "role": "member",
            "created_at": "2026-06-28T00:10:00",
        },
    },
    "postgres": {
        1: {
            "id": 1,
            "username": "admin",
            "display_name": "Admin",
            "role": "admin",
            "created_at": "2026-06-28T00:00:00",
        },
        2: {
            "id": 2,
            "username": "member",
            "display_name": "Member",
            "role": "member",
            "created_at": "2026-06-28T00:05:00",
        },
        3: {
            "id": 3,
            "username": "dw_test_delete_real_20260628",
            "display_name": "Delete Real",
            "role": "member",
            "created_at": "2026-06-28T00:10:00",
        },
    },
}
state = copy.deepcopy(initial_state)
submit_calls = []

def fake_load_target_rows(username, sqlite_path, database_url):
    sqlite_row = next((row for row in state["sqlite"].values() if row["username"] == username), None)
    postgres_row = next((row for row in state["postgres"].values() if row["username"] == username), None)
    return sqlite_row, postgres_row

def fake_submit_delete_post(sqlite_path, target_id):
    submit_calls.append((str(sqlite_path), target_id))
    state["sqlite"].pop(target_id, None)
    state["postgres"].pop(target_id, None)
    return {"status_code": 200, "body": "ok"}

module.load_target_rows = fake_load_target_rows
module.submit_delete_post = fake_submit_delete_post

def run_main(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = module.main(args)
    return rc, buf.getvalue()

rc, output = run_main(["--username", "dw_test_delete_real_20260628"])
if rc != 0 or "PASS users delete submit verifier inspect completed." not in output:
    raise SystemExit("delete submit verifier inspect smoke failed")
if submit_calls:
    raise SystemExit("inspect mode should not submit delete POST")
if 3 not in state["sqlite"] or 3 not in state["postgres"]:
    raise SystemExit("inspect mode should not delete any rows")

rc, output = run_main(["--username", "admin"])
if rc == 0 or "protected_user" not in output:
    raise SystemExit("delete submit verifier admin guard smoke failed")
if len(submit_calls) != 0:
    raise SystemExit("admin guard should not submit delete POST")

rc, output = run_main(["--username", "member"])
if rc == 0 or "target_user_not_allowed_for_stage_4a" not in output:
    raise SystemExit("delete submit verifier non-test-user guard smoke failed")
if len(submit_calls) != 0:
    raise SystemExit("non-test-user guard should not submit delete POST")

state = copy.deepcopy(initial_state)
submit_calls.clear()
module.load_target_rows = fake_load_target_rows
module.submit_delete_post = fake_submit_delete_post

rc, output = run_main(["--username", "dw_test_delete_real_20260628", "--execute"])
if rc != 0 or "PASS users delete submit verifier passed." not in output:
    raise SystemExit("delete submit verifier execute smoke failed")
if len(submit_calls) != 1:
    raise SystemExit("execute mode should submit exactly one delete POST")
if "password_hash" in output:
    raise SystemExit("delete submit verifier output leaked password_hash")

print("users delete submit verifier smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(ROOT_DIR),
            str(db_path),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "users delete submit verifier smoke PASS" not in result.stdout:
        raise AssertionError("users delete submit verifier smoke subprocess did not report PASS.")


def run_users_read_inventory_smoke() -> None:
    result = run_script("check_users_read_inventory.py")
    output = result.stdout
    if result.returncode != 0:
        raise AssertionError(f"check_users_read_inventory.py failed:\n{output}")
    required_snippets = [
        "Users read route inventory:",
        "- get_user_by_username: ",
        "- get_user_by_id: ",
        "- list_users: ",
        "active_endpoint=login",
        "active_endpoint=users",
        "active_endpoint=api_reset_sheet",
        "- login: helper=get_user_by_username helper_used=true direct_users_select=false",
        "- api_reset_sheet: helper=get_user_by_id helper_used=true direct_users_select=false",
        "- users: helper=list_users helper_used=true direct_users_select=false",
        "PASS users read inventory completed.",
    ]
    for snippet in required_snippets:
        if snippet not in output:
            raise AssertionError(f"check_users_read_inventory.py missing expected snippet: {snippet}")


def run_users_read_helper_smoke(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]

spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

for helper_name in ("get_user_by_username", "get_user_by_id", "list_users"):
    if not hasattr(module, helper_name):
        raise SystemExit(f"missing helper: {helper_name}")

admin_user = module.get_user_by_username("admin")
if admin_user is None or admin_user["username"] != "admin":
    raise SystemExit("get_user_by_username smoke failed")

admin_by_id = module.get_user_by_id(1)
if admin_by_id is None or admin_by_id["id"] != 1:
    raise SystemExit("get_user_by_id smoke failed")

listed_users = module.list_users()
if not listed_users:
    raise SystemExit("list_users smoke returned no users")
first_payload = dict(listed_users[0])
if "password_hash" in first_payload:
    raise SystemExit("list_users should not expose password_hash")
if not any(row["username"] == "admin" for row in listed_users):
    raise SystemExit("list_users smoke missing admin user")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route smoke failed")

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    users_response = client.get("/admin/users")
    if users_response.status_code != 200:
        raise SystemExit("/admin/users GET smoke failed")

    reset_response = client.post(
        "/api/reset-sheet",
        json={"sheet_id": 1, "password": "admin"},
    )
    if reset_response.status_code != 200:
        raise SystemExit("/api/reset-sheet smoke failed")

print("users read helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "users read helper smoke PASS" not in result.stdout:
        raise AssertionError("users read helper smoke subprocess did not report PASS.")


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


def run_sqlite_db_path_resolver_smoke() -> None:
    from sqlite_db_path import resolve_sqlite_db_path

    default_resolution = resolve_sqlite_db_path("")
    if default_resolution.source != "default_project_site_db":
        raise AssertionError(f"Unexpected default sqlite db path source: {default_resolution.source}")
    if default_resolution.path.name != "site.db":
        raise AssertionError(f"Unexpected default sqlite db path name: {default_resolution.path}")

    env_resolution = resolve_sqlite_db_path(str(ROOT_DIR / "site.db"))
    if env_resolution.source != "env_APP_DB_PATH":
        raise AssertionError(f"Unexpected env sqlite db path source: {env_resolution.source}")
    if env_resolution.path.name != "site.db":
        raise AssertionError(f"Unexpected env sqlite db path name: {env_resolution.path}")

    invalid_windows_env_resolution = resolve_sqlite_db_path(r"I:\公司web\大英新埔\site.db")
    if os.name == "nt":
        if invalid_windows_env_resolution.source != "env_APP_DB_PATH":
            raise AssertionError("Expected Windows-style APP_DB_PATH to remain valid on Windows.")
    else:
        if invalid_windows_env_resolution.source != "fallback_default_invalid_windows_env_on_non_windows":
            raise AssertionError(
                "Expected Windows-style APP_DB_PATH to fall back to project site.db on non-Windows."
            )


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
        run_user_delete_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_protected_user_delete_guard_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_user_delete_dual_write_dry_run_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_users_create_readiness_guard_smoke(db_path)
        run_users_create_readiness_autoincrement_sequence_smoke()
        run_users_delete_readiness_guard_smoke(db_path)
        run_users_delete_submit_verifier_smoke(db_path)
        run_users_read_inventory_smoke()
        run_users_read_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_users_id_allocation_smoke(db_path)
        run_users_sqlite_sequence_bump_plan_smoke()
        run_users_sqlite_sequence_apply_guard_smoke()
        run_sqlite_db_path_resolver_smoke()
        run_users_template_delete_ui_smoke()
        run_user_create_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_admin_user_role_update_smoke(db_path, Path(tmpdir) / "app-smoke.db")

    if redact_database_url("postgresql://user:secret@localhost:5432/demo") != "postgresql://user:***@localhost:5432/demo":
        raise AssertionError("DATABASE_URL redaction failed.")

    run_help("check_controlled_dual_write.py")
    run_help("check_users_secondary_update.py")
    run_help("check_users_baseline_and_sequence.py")
    run_help("check_users_create_readiness.py")
    run_help("check_users_delete_readiness.py")
    run_help("check_users_delete_submit.py")
    run_help("check_users_read_inventory.py")
    run_help("check_sqlite_runtime_persistence.py")
    run_help("check_users_id_allocation.py")
    run_help("plan_users_sqlite_sequence_bump.py")
    run_help("bump_users_sqlite_sequence.py")
    run_help("fix_users_postgres_sequence.py")
    run_help("backfill_users_display_name_to_postgres.py")

    controlled_result = run_script("check_controlled_dual_write.py")
    if "PASS controlled dual-write floors/users update/create/delete wiring looks correct." not in controlled_result.stdout:
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
    persistence_result = run_script("check_sqlite_runtime_persistence.py", env={"DATABASE_URL": ""})
    if "resolved_sqlite_source_path:" not in persistence_result.stdout or "PASS" not in persistence_result.stdout:
        raise AssertionError("check_sqlite_runtime_persistence.py did not report expected PASS output.")
    if "persistence_status:" not in persistence_result.stdout or "recommended_action:" not in persistence_result.stdout:
        raise AssertionError("check_sqlite_runtime_persistence.py did not report persistence status output.")
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
