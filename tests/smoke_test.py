from __future__ import annotations

import os
import inspect
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
    "vendor_contacts",
    "vendor_work_entries",
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
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (unit_id, task_id)
        );
        CREATE TABLE unit_extra (
            unit_id INTEGER PRIMARY KEY,
            initial_check TEXT NOT NULL DEFAULT '',
            recheck_1 TEXT NOT NULL DEFAULT '',
            recheck_2 TEXT NOT NULL DEFAULT '',
            handover TEXT NOT NULL DEFAULT 'X',
            updated_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        CREATE TABLE vendor_contacts (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            contact_title TEXT NOT NULL DEFAULT '',
            contact_phone TEXT NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            contact_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE vendor_work_entries (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            business_date TEXT NOT NULL,
            planned_at TEXT NOT NULL,
            planned_headcount INTEGER NOT NULL,
            actual_headcount INTEGER NOT NULL,
            work_content TEXT NOT NULL,
            pre_entry_requirement TEXT,
            requirement_status TEXT DEFAULT 'pending',
            requirement_confirmed_by TEXT,
            requirement_confirmed_at TEXT,
            work_headcount INTEGER NOT NULL,
            entry_order INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute("INSERT INTO meta (key, value) VALUES ('site_title', 'demo')")
    conn.execute("INSERT INTO meta (key, value) VALUES ('excel_seeded', '1')")
    conn.execute("INSERT INTO meta (key, value) VALUES ('unit_layout_version', '2026-06-26-ab')")
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
        "Global Admin（全站可存取）",
        "add_site_permission:{{ user.id }}",
        "update_site_permission:{{ permission.id }}",
        "delete_site_permission:{{ permission.id }}",
        "site_permission_roles",
        "active_sites",
    ]
    for snippet in required_snippets:
        if snippet not in template:
            raise AssertionError(f"users.html missing delete UI snippet: {snippet}")
    if "password_hash" in template:
        raise AssertionError("users.html delete UI should not include password_hash.")


def run_site_foundation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def columns(conn, table_name):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

required_tables = {"sites", "user_site_permissions", "vendor_accounts", "sheets"}
existing_tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
missing_tables = sorted(required_tables - existing_tables)
if missing_tables:
    raise SystemExit(f"missing tables: {missing_tables}")

site_columns = columns(conn, "sites")
if {"site_name", "site_code", "is_active", "created_at", "updated_at"} - site_columns:
    raise SystemExit("sites table missing required columns")

sheet_columns = columns(conn, "sheets")
if "site_id" not in sheet_columns:
    raise SystemExit("sheets.site_id missing after bootstrap")

default_rows = conn.execute(
    "SELECT id, site_name FROM sites WHERE site_name = ?",
    (module.DEFAULT_SITE_NAME,),
).fetchall()
if len(default_rows) != 1:
    raise SystemExit(f"default site count mismatch: {len(default_rows)}")
default_site_id = default_rows[0]["id"]

sheet_rows = conn.execute("SELECT id, site_id FROM sheets ORDER BY id").fetchall()
if not sheet_rows:
    raise SystemExit("expected at least one sheet")
if any(row["site_id"] is None for row in sheet_rows):
    raise SystemExit("sheet site_id backfill missing")
if any(row["site_id"] != default_site_id for row in sheet_rows):
    raise SystemExit("sheet site_id did not backfill to default site")

conn.close()
module.bootstrap()
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
default_site_count = conn.execute(
    "SELECT COUNT(*) AS count FROM sites WHERE site_name = ?",
    (module.DEFAULT_SITE_NAME,),
).fetchone()["count"]
conn.close()
if default_site_count != 1:
    raise SystemExit("default site seed is not idempotent")
print("site foundation smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "site foundation smoke PASS" not in result.stdout:
        raise AssertionError("site foundation smoke subprocess did not report PASS.")


def run_site_selection_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_id = module.get_default_site_id(conn)
    if default_site_id is None:
        raise SystemExit("default site id missing")

    secondary_site = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id, site_name, site_code, is_active",
        ("__smoke_secondary_site__", "secondary"),
    ).fetchone()
    inactive_site = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 0) RETURNING id, site_name, site_code, is_active",
        ("__smoke_inactive_site__", "inactive"),
    ).fetchone()

    def create_user(username):
        conn.execute(
            "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, username, module.generate_password_hash("x"), "member"),
        )
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    single = create_user("__smoke_single__")
    multi = create_user("__smoke_multi__")
    zero = create_user("__smoke_zero__")
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = 'admin'",
        (module.generate_password_hash("admin"),),
    )
    admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()

    conn.executemany(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        [
            (single["id"], secondary_site["id"], "member"),
            (multi["id"], default_site_id, "member"),
            (multi["id"], secondary_site["id"], "supervisor"),
        ],
    )
    conn.commit()

if not module.is_global_admin(admin):
    raise SystemExit("admin should be global admin")
if not module.user_can_access_site(admin["id"], secondary_site["id"]):
    raise SystemExit("admin should access secondary active site")
if module.user_can_access_site(admin["id"], inactive_site["id"]):
    raise SystemExit("admin should not access inactive site")
if module.get_user_role_for_site(admin["id"], secondary_site["id"]) != "admin":
    raise SystemExit("admin role lookup failed")

with module.app.test_request_context("/"):
    result = module.normalize_current_site_for_user(admin)
    if result["status"] != "resolved" or result["site_id"] != default_site_id:
        raise SystemExit("admin should fallback to default site")
    if module.get_current_site_id() != default_site_id:
        raise SystemExit("admin current site should be written")

with module.app.test_request_context("/"):
    result = module.normalize_current_site_for_user(single)
    if result["status"] != "resolved" or result["site_id"] != secondary_site["id"]:
        raise SystemExit("single-site user should auto-select sole site")

with module.app.test_request_context("/"):
    module.set_current_site_id(inactive_site["id"])
    result = module.normalize_current_site_for_user(single)
    if result["status"] != "resolved" or result["site_id"] != secondary_site["id"]:
        raise SystemExit("single-site stale session should reset to sole site")

with module.app.test_request_context("/"):
    result = module.normalize_current_site_for_user(multi)
    if result["status"] != "site_selection_required":
        raise SystemExit("multi-site user should require selector")
    if module.get_current_site_id() is not None:
        raise SystemExit("multi-site user should not keep current site")
    if not module.session.get("site_selection_required"):
        raise SystemExit("multi-site user should set selector flag")

with module.app.test_request_context("/"):
    module.set_current_site_id(inactive_site["id"])
    result = module.normalize_current_site_for_user(multi)
    if result["status"] != "site_selection_required":
        raise SystemExit("multi-site stale session should require selector")
    if module.get_current_site_id() is not None:
        raise SystemExit("multi-site stale session should clear current site")

with module.app.test_request_context("/"):
    result = module.normalize_current_site_for_user(zero)
    if result["status"] != "access_denied_no_site_permission":
        raise SystemExit("zero-site user should be blocked")
    if module.get_current_site_id() is not None:
        raise SystemExit("zero-site user should not keep current site")

client = module.app.test_client()
with client.session_transaction() as session:
    session.clear()

admin_login = client.post(
    "/login",
    data={"username": "admin", "display_name": "Admin", "password": "admin"},
    follow_redirects=False,
)
if admin_login.status_code != 302 or not admin_login.headers.get("Location", "").endswith("/sheet"):
    raise SystemExit("admin login should keep redirect to /sheet")
with client.session_transaction() as session:
    if session.get("current_site_id") != default_site_id:
        raise SystemExit("admin login should write default current_site_id")
    if session.get("current_site_name") != module.DEFAULT_SITE_NAME:
        raise SystemExit("admin login should write default current_site_name")
    if session.get("site_selection_required"):
        raise SystemExit("admin login should not require site selection")

admin_selector = client.get("/site-selector")
if admin_selector.status_code != 200:
    raise SystemExit("admin should be able to open /site-selector")
admin_selector_html = admin_selector.get_data(as_text=True)
if 'name="site_id"' not in admin_selector_html or 'method="post"' not in admin_selector_html:
    raise SystemExit("site selector page should render site selection form")
admin_sheet = client.get("/sheet")
if admin_sheet.status_code != 200:
    raise SystemExit("admin should be able to open /sheet after login")
admin_sheet_html = admin_sheet.get_data(as_text=True)
if "/site-selector" not in admin_sheet_html or module.DEFAULT_SITE_NAME not in admin_sheet_html:
    raise SystemExit("header should show current site and switch-site entry")

single_login = client.post(
    "/login",
    data={"username": single["username"], "display_name": single["display_name"], "password": "x"},
    follow_redirects=False,
)
if single_login.status_code != 302 or not single_login.headers.get("Location", "").endswith("/sheet"):
    raise SystemExit("single-site login should keep redirect to /sheet")
with client.session_transaction() as session:
    if session.get("current_site_id") != secondary_site["id"]:
        raise SystemExit("single-site login should auto-select sole accessible site")
    if session.get("current_site_name") != secondary_site["site_name"]:
        raise SystemExit("single-site login should write sole site name")
    if session.get("site_selection_required"):
        raise SystemExit("single-site login should not require site selection")

single_selector = client.get("/site-selector")
if single_selector.status_code != 200:
    raise SystemExit("single-site user should be able to open /site-selector")
single_selector_html = single_selector.get_data(as_text=True)
if 'name="site_id"' not in single_selector_html or secondary_site["site_name"] not in single_selector_html:
    raise SystemExit("single-site selector should show sole accessible site")
single_selector_post = client.post("/site-selector", data={"site_id": secondary_site["id"]}, follow_redirects=False)
if single_selector_post.status_code != 302 or not single_selector_post.headers.get("Location", "").endswith("/sheet"):
    raise SystemExit("single-site selector submit should return /sheet")

multi_login = client.post(
    "/login",
    data={"username": multi["username"], "display_name": multi["display_name"], "password": "x"},
    follow_redirects=False,
)
if multi_login.status_code != 302 or not multi_login.headers.get("Location", "").endswith("/site-selector"):
    raise SystemExit("multi-site login should redirect to /site-selector")
with client.session_transaction() as session:
    if session.get("current_site_id") is not None:
        raise SystemExit("multi-site login should not guess current_site_id")
    if session.get("current_site_name") is not None:
        raise SystemExit("multi-site login should not write current_site_name")
    if session.get("site_selection_required") is not True:
        raise SystemExit("multi-site login should set site_selection_required")

multi_selector = client.get("/site-selector")
if multi_selector.status_code != 200:
    raise SystemExit("multi-site user should be able to open /site-selector")
multi_selector_post = client.post("/site-selector", data={"site_id": secondary_site["id"]}, follow_redirects=False)
if multi_selector_post.status_code != 302 or not multi_selector_post.headers.get("Location", "").endswith("/sheet"):
    raise SystemExit("multi-site selector submit should return /sheet")
with client.session_transaction() as session:
    if session.get("current_site_id") != secondary_site["id"]:
        raise SystemExit("multi-site selector should write selected current_site_id")
    if session.get("current_site_name") != secondary_site["site_name"]:
        raise SystemExit("multi-site selector should write selected current_site_name")
    if session.get("site_selection_required"):
        raise SystemExit("multi-site selector should clear selector flag")

zero_login = client.post(
    "/login",
    data={"username": zero["username"], "display_name": zero["display_name"], "password": "x"},
    follow_redirects=False,
)
if zero_login.status_code != 302 or not zero_login.headers.get("Location", "").endswith("/login"):
    raise SystemExit("zero-site login should return to /login")
with client.session_transaction() as session:
    if session.get("user_id") is not None:
        raise SystemExit("zero-site login should not retain authenticated session")
    if session.get("username") is not None:
        raise SystemExit("zero-site login should not retain username")
    if session.get("role") is not None:
        raise SystemExit("zero-site login should not retain role")
    if session.get("current_site_id") is not None:
        raise SystemExit("zero-site login should not set current_site_id")
    if session.get("current_site_name") is not None:
        raise SystemExit("zero-site login should not set current_site_name")
    if session.get("site_selection_required") is not None:
        raise SystemExit("zero-site login should not set site_selection_required")

with client.session_transaction() as session:
    session.clear()
    session["user_id"] = multi["id"]
    session["username"] = multi["username"]
    session["display_name"] = multi["display_name"] or multi["username"]
    session["role"] = multi["role"]
    session["site_selection_required"] = True
sheet_recovery = client.get("/sheet", follow_redirects=False)
if sheet_recovery.status_code != 302 or not sheet_recovery.headers.get("Location", "").endswith("/site-selector"):
    raise SystemExit("/sheet should recover stale multi-site session by redirecting to /site-selector")

with client.session_transaction() as session:
    session.clear()
    session["user_id"] = multi["id"]
    session["username"] = multi["username"]
    session["display_name"] = multi["display_name"] or multi["username"]
    session["role"] = multi["role"]
    session["current_site_id"] = default_site_id
    session["current_site_name"] = module.DEFAULT_SITE_NAME
    session["site_selection_required"] = True
invalid_selector_post = client.post("/site-selector", data={"site_id": "invalid"}, follow_redirects=False)
if invalid_selector_post.status_code != 400:
    raise SystemExit("invalid selector submission should return 400")
with client.session_transaction() as session:
    if session.get("current_site_id") is not None or session.get("current_site_name") is not None:
        raise SystemExit("invalid selector submission should not write current site")
    if session.get("site_selection_required") is not True:
        raise SystemExit("invalid selector submission should keep selector flag")

with client.session_transaction() as session:
    session.clear()
    session["user_id"] = single["id"]
    session["username"] = single["username"]
    session["display_name"] = single["display_name"] or single["username"]
    session["role"] = single["role"]
    session["current_site_id"] = secondary_site["id"]
    session["current_site_name"] = secondary_site["site_name"]
    session["site_selection_required"] = False
forbidden_selector_post = client.post("/site-selector", data={"site_id": default_site_id}, follow_redirects=False)
if forbidden_selector_post.status_code != 403:
    raise SystemExit("non-accessible selector submission should return 403")
with client.session_transaction() as session:
    if session.get("current_site_id") != secondary_site["id"] or session.get("current_site_name") != secondary_site["site_name"]:
        raise SystemExit("forbidden selector submission should keep existing current site")

with client.session_transaction() as session:
    session.clear()
    session["user_id"] = multi["id"]
    session["username"] = multi["username"]
    session["display_name"] = multi["display_name"] or multi["username"]
    session["role"] = multi["role"]
    session["current_site_id"] = default_site_id
    session["current_site_name"] = module.DEFAULT_SITE_NAME
    session["site_selection_required"] = True
forbidden_selector_post_during_required_selection = client.post("/site-selector", data={"site_id": inactive_site["id"]}, follow_redirects=False)
if forbidden_selector_post_during_required_selection.status_code != 403:
    raise SystemExit("forbidden selector submission during required selection should return 403")
with client.session_transaction() as session:
    if session.get("current_site_id") is not None or session.get("current_site_name") is not None:
        raise SystemExit("forbidden selector submission during required selection should clear stale current site")
    if session.get("site_selection_required") is not True:
        raise SystemExit("forbidden selector submission during required selection should keep selector flag")

with client.session_transaction() as session:
    session["user_id"] = admin["id"]
    session["username"] = "admin"
    session["role"] = "admin"
    session["current_site_id"] = default_site_id
    session["current_site_name"] = module.DEFAULT_SITE_NAME
    session["site_selection_required"] = True

response = client.post("/logout", follow_redirects=False)
if response.status_code != 302:
    raise SystemExit("logout should redirect")
with client.session_transaction() as session:
    if "current_site_id" in session or "current_site_name" in session or "site_selection_required" in session:
        raise SystemExit("logout should clear site selection session keys")

print("site selection smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "site selection smoke PASS" not in result.stdout:
        raise AssertionError("site selection smoke subprocess did not report PASS.")


def run_crew_schema_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "vendor_contacts" not in tables:
        raise SystemExit("vendor_contacts table should exist after bootstrap")
    if "vendor_work_entries" not in tables:
        raise SystemExit("vendor_work_entries table should exist after bootstrap")
    if "formal_approvals" not in tables:
        raise SystemExit("formal_approvals table should exist after bootstrap")

    vendor_contacts_columns = [row["name"] for row in conn.execute("PRAGMA table_info(vendor_contacts)").fetchall()]
    for required in (
        "id",
        "sheet_id",
        "vendor_name",
        "contact_name",
        "contact_title",
        "contact_phone",
        "is_primary",
        "contact_order",
        "created_at",
        "updated_at",
    ):
        if required not in vendor_contacts_columns:
            raise SystemExit(f"vendor_contacts missing required column: {required}")

    vendor_work_entries_columns = [row["name"] for row in conn.execute("PRAGMA table_info(vendor_work_entries)").fetchall()]
    for required in (
        "id",
        "sheet_id",
        "vendor_name",
        "business_date",
        "planned_at",
        "planned_headcount",
        "actual_headcount",
        "work_content",
        "work_headcount",
        "entry_order",
        "pre_entry_requirement",
        "requirement_status",
        "requirement_confirmed_by",
        "requirement_confirmed_at",
        "created_at",
        "updated_at",
    ):
        if required not in vendor_work_entries_columns:
            raise SystemExit(f"vendor_work_entries missing required column: {required}")

    formal_approvals_columns = [row["name"] for row in conn.execute("PRAGMA table_info(formal_approvals)").fetchall()]
    for required in (
        "id",
        "entry_id",
        "sheet_id",
        "action",
        "approval_status",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    ):
        if required not in formal_approvals_columns:
            raise SystemExit(f"formal_approvals missing required column: {required}")

    contact_indexes = {row["name"] for row in conn.execute("PRAGMA index_list(vendor_contacts)").fetchall()}
    for required in ("idx_vendor_contacts_sheet_id", "idx_vendor_contacts_sheet_vendor", "idx_vendor_contacts_sheet_vendor_order"):
        if required not in contact_indexes:
            raise SystemExit(f"vendor_contacts missing expected index: {required}")

    work_indexes = {row["name"] for row in conn.execute("PRAGMA index_list(vendor_work_entries)").fetchall()}
    for required in (
        "idx_vendor_work_entries_sheet_business_date",
        "idx_vendor_work_entries_sheet_vendor_date",
        "idx_vendor_work_entries_business_date",
    ):
        if required not in work_indexes:
            raise SystemExit(f"vendor_work_entries missing expected index: {required}")

    formal_indexes = conn.execute("PRAGMA index_list(formal_approvals)").fetchall()
    formal_index_names = {row["name"] for row in formal_indexes}
    for required in ("idx_formal_approvals_entry_action_unique", "idx_formal_approvals_sheet_id"):
        if required not in formal_index_names:
            raise SystemExit(f"formal_approvals missing expected index: {required}")
    unique_entry_action_present = False
    for row in formal_indexes:
        if row["unique"]:
            cols = tuple(index_row["name"] for index_row in conn.execute(f"PRAGMA index_info({row['name']})").fetchall())
            if cols == ("entry_id", "action"):
                unique_entry_action_present = True
                break
    if not unique_entry_action_present:
        raise SystemExit("formal_approvals should enforce UNIQUE(entry_id, action)")

    approval_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            ''',
            (1, "Formal Schema Vendor", "2000-01-01", "", 0, 0, "Formal Schema Work", 0, 0),
        ).fetchone()["id"]
    )
    conn.execute(
        "INSERT INTO formal_approvals (entry_id, sheet_id) VALUES (?, ?)",
        (approval_entry_id, 1),
    )
    duplicate_rejected = False
    try:
        conn.execute(
            "INSERT INTO formal_approvals (entry_id, sheet_id) VALUES (?, ?)",
            (approval_entry_id, 1),
        )
    except sqlite3.IntegrityError:
        duplicate_rejected = True
    if not duplicate_rejected:
        raise SystemExit("formal_approvals should reject duplicate (entry_id, action)")

    legacy_unique_present = False
    for row in conn.execute("PRAGMA index_list(vendor_contacts)").fetchall():
        if row["unique"]:
            cols = tuple(index_row["name"] for index_row in conn.execute(f"PRAGMA index_info({row['name']})").fetchall())
            if cols == ("sheet_id", "vendor_name"):
                legacy_unique_present = True
                break
    if legacy_unique_present:
        raise SystemExit("vendor_contacts should not enforce legacy UNIQUE(sheet_id, vendor_name)")

    conn.execute(
        \"INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?)\",
        (1, "Vendor", "Alice", "", "0900000001", 1, 0),
    )
    conn.execute(
        \"INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?)\",
        (1, "Vendor", "Bob", "主任", "0900000002", 0, 1),
    )
    vendor_contact_count = conn.execute(
        \"SELECT COUNT(*) FROM vendor_contacts WHERE sheet_id = 1 AND vendor_name = ?\",
        ("Vendor",),
    ).fetchone()[0]
    if vendor_contact_count != 2:
        raise SystemExit("vendor_contacts should allow multiple rows for the same sheet/vendor")

if module.resolve_crew_business_date(datetime(2026, 6, 29, 8, 29, 0)) != "2026-06-28":
    raise SystemExit("resolve_crew_business_date should use previous day before 08:30")
if module.resolve_crew_business_date(datetime(2026, 6, 29, 8, 30, 0)) != "2026-06-29":
    raise SystemExit("resolve_crew_business_date should use same day at 08:30")
if module.resolve_crew_business_date(datetime(2026, 6, 29, 23, 59, 0)) != "2026-06-29":
    raise SystemExit("resolve_crew_business_date should use same day late night")

print("crew schema smoke PASS")
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
    if "crew schema smoke PASS" not in result.stdout:
        raise AssertionError("crew schema smoke subprocess did not report PASS.")


def run_crew_api_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    sheet_row = conn.execute("SELECT id FROM sheets ORDER BY sort_order, id LIMIT 1").fetchone()
    if sheet_row is None:
        raise SystemExit("expected a seeded sheet for crew API smoke")
    sheet_id = int(sheet_row["id"])
    sheet_site_id = int(
        conn.execute("SELECT site_id FROM sheets WHERE id = ?", (sheet_id,)).fetchone()["site_id"]
    )
    member_password_hash = module.generate_password_hash("x")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("crew_read_member", "crew_read_member", member_password_hash, "member"),
    )
    crew_read_member_id = int(
        conn.execute("SELECT id FROM users WHERE username = ?", ("crew_read_member",)).fetchone()["id"]
    )
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (crew_read_member_id, sheet_site_id, "member"),
    )
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__crew_read_site_b__", "crew-read-site-b"),
        ).fetchone()["id"]
    )
    conn.execute(
        "INSERT OR IGNORE INTO sheets (id, name, sort_order, site_id, created_at) VALUES (2, 'Sheet B', 2, ?, CURRENT_TIMESTAMP)",
        (secondary_site_id,),
    )

    task_rows = conn.execute(
        "SELECT id FROM tasks WHERE sheet_id = ? ORDER BY col_index, id LIMIT 4",
        (sheet_id,),
    ).fetchall()
    if len(task_rows) < 4:
        raise SystemExit("expected at least four tasks for crew API smoke")
    task_ids = [int(row["id"]) for row in task_rows]
    conn.execute("UPDATE tasks SET vendor = ?, name = ? WHERE id = ?", ("VendorA", "Pending Paint", task_ids[0]))
    conn.execute("UPDATE tasks SET vendor = ?, name = ? WHERE id = ?", ("VendorA", "Pending Patch", task_ids[1]))
    conn.execute("UPDATE tasks SET vendor = ?, name = ? WHERE id = ?", ("VendorC", "Pending Tile", task_ids[2]))
    conn.execute("UPDATE tasks SET vendor = ?, name = ? WHERE id = ?", ("VendorB", "Closed Task", task_ids[3]))

    conn.execute(
        "UPDATE progress SET value = ? WHERE task_id = ?",
        (module.DONE_VALUE, task_ids[3]),
    )
    next_col_index = conn.execute("SELECT COALESCE(MAX(col_index), 0) FROM tasks").fetchone()[0]
    for vendor_name in ("VendorZ", "VendorTitleOnly", "VendorNameOnly", "VendorEmptyDisplay"):
        next_col_index += 1
        conn.execute(
            '''
            INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (sheet_id, next_col_index, vendor_name, "Room", f"{vendor_name} Placeholder"),
        )
    next_col_index += 1
    conn.execute(
        '''
        INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (2, next_col_index, "VendorZ", "Room", "VendorZ Cross Sheet Placeholder"),
    )

    conn.execute(
        "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_phone) VALUES (?, ?, ?, ?)",
        (sheet_id, "VendorA", "Alice", "0900000001"),
    )
    conn.execute(
        "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_phone) VALUES (?, ?, ?, ?)",
        (sheet_id, "VendorB", "Bob", "0900000002"),
    )

    pending_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, requirement_status,
                requirement_confirmed_by, requirement_confirmed_at, work_headcount, entry_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            ''',
            (sheet_id, "VendorA", business_date, "2000-01-01 09:00", 3, 0, "Missing Crew", "Need power off", "pending", None, None, 0, 0),
        ).fetchone()["id"]
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, requirement_status,
                requirement_confirmed_by, requirement_confirmed_at, work_headcount, entry_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            ''',
            (sheet_id, "VendorA", business_date, "2000-01-01 10:00", 2, 2, "Summary Crew", "Need lift access", "confirmed", "confirm_member", "2026-07-06 09:30:00", 2, 1),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (approved_entry_id, sheet_id, "crew_formal_approve_entry", "approved", "formal_member", "2026-07-06 10:00:00"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, requirement_status,
            requirement_confirmed_by, requirement_confirmed_at, work_headcount, entry_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (sheet_id, "VendorC", business_date, "", 1, 0, "No Requirement Crew", "", "pending", None, None, 0, 0),
    )

with module.app.test_client() as client:
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    crew_forms_response = client.get(f"/api/crew-forms?sheet_id={sheet_id}")
    if crew_forms_response.status_code != 200:
        raise SystemExit("/api/crew-forms should return 200")
    crew_forms = crew_forms_response.get_json()
    if not crew_forms.get("ok"):
        raise SystemExit("/api/crew-forms should report ok=true")
    if crew_forms.get("sheet_id") != sheet_id:
        raise SystemExit("/api/crew-forms returned unexpected sheet_id")
    if crew_forms.get("business_date") != business_date:
        raise SystemExit("/api/crew-forms should use resolve_crew_business_date() by default")

    active_vendors = {item["vendor_name"]: item for item in crew_forms["active_vendors"]}
    if "VendorA" not in active_vendors or "VendorC" not in active_vendors:
        raise SystemExit("/api/crew-forms should include active vendors")
    if "VendorB" in active_vendors:
        raise SystemExit("/api/crew-forms should not include inactive vendor in active_vendors")
    if active_vendors["VendorA"]["contact"]["contact_name"] != "Alice":
        raise SystemExit("/api/crew-forms should include vendor contact data")
    if not isinstance(active_vendors["VendorA"].get("contacts"), list) or len(active_vendors["VendorA"]["contacts"]) != 1:
        raise SystemExit("/api/crew-forms should include contacts array for active vendors")
    if active_vendors["VendorA"]["contacts"][0]["contact_title"] != "":
        raise SystemExit("/api/crew-forms active vendor contacts should include contact_title")
    if active_vendors["VendorA"]["contacts"][0]["display_name"] != "Alice":
        raise SystemExit("/api/crew-forms contact display_name should fall back to contact_name only")
    if active_vendors["VendorA"]["contact"]["id"] != active_vendors["VendorA"]["contacts"][0]["id"]:
        raise SystemExit("compatibility contact should equal first contact in contacts array")
    if active_vendors["VendorA"]["contact"]["display_name"] != active_vendors["VendorA"]["contacts"][0]["display_name"]:
        raise SystemExit("compatibility contact display_name should match contacts[0]")
    if not active_vendors["VendorA"]["contacts"][0]["created_at"] or not active_vendors["VendorA"]["contacts"][0]["updated_at"]:
        raise SystemExit("/api/crew-forms contacts should include created_at and updated_at")
    if len(active_vendors["VendorA"]["work_entries"]) != 2:
        raise SystemExit("/api/crew-forms should include current business_date work entries")
    first_work_entry = active_vendors["VendorA"]["work_entries"][0]
    second_work_entry = active_vendors["VendorA"]["work_entries"][1]
    expected_requirement_keys = {
        "id",
        "sheet_id",
        "vendor_name",
        "business_date",
        "planned_at",
        "planned_headcount",
        "actual_headcount",
        "work_content",
        "pre_entry_requirement",
        "requirement_status",
        "requirement_confirmed_by",
        "requirement_confirmed_at",
        "readiness_state",
        "readiness_reason",
        "scheduling_gate_state",
        "scheduling_gate_reason",
        "formal_approval_state",
        "formal_approval_status",
        "formal_approved_by",
        "formal_approved_at",
        "work_headcount",
        "entry_order",
        "created_at",
        "updated_at",
    }
    if not expected_requirement_keys.issubset(first_work_entry.keys()):
        raise SystemExit("/api/crew-forms work_entries should include requirement confirmation fields")
    if first_work_entry["pre_entry_requirement"] != "Need power off":
        raise SystemExit("/api/crew-forms should expose pending pre_entry_requirement text")
    if first_work_entry["requirement_status"] != "pending":
        raise SystemExit("/api/crew-forms should expose pending requirement_status")
    if first_work_entry["requirement_confirmed_by"] is not None or first_work_entry["requirement_confirmed_at"] is not None:
        raise SystemExit("/api/crew-forms pending requirement should keep confirmation fields empty")
    if first_work_entry["readiness_state"] != "not_ready" or first_work_entry["readiness_reason"] != "requirement_pending":
        raise SystemExit("/api/crew-forms pending requirement entry should be not_ready with requirement_pending reason")
    if first_work_entry["scheduling_gate_state"] != "warning" or first_work_entry["scheduling_gate_reason"] != "requirement_pending":
        raise SystemExit("/api/crew-forms pending requirement entry should map to scheduling warning with requirement_pending reason")
    if int(first_work_entry["id"]) != pending_entry_id:
        raise SystemExit("/api/crew-forms pending requirement entry should preserve entry identity")
    if first_work_entry["formal_approval_state"] != "pending" or first_work_entry["formal_approval_status"] != "pending":
        raise SystemExit("/api/crew-forms pending requirement entry should expose pending formal approval state")
    if first_work_entry["formal_approved_by"] != "" or first_work_entry["formal_approved_at"] != "":
        raise SystemExit("/api/crew-forms pending requirement entry should keep formal approval actor fields empty")
    if second_work_entry["pre_entry_requirement"] != "Need lift access":
        raise SystemExit("/api/crew-forms should expose confirmed pre_entry_requirement text")
    if second_work_entry["requirement_status"] != "confirmed":
        raise SystemExit("/api/crew-forms should expose confirmed requirement_status")
    if second_work_entry["requirement_confirmed_by"] != "confirm_member":
        raise SystemExit("/api/crew-forms should expose requirement_confirmed_by for confirmed entries")
    if second_work_entry["requirement_confirmed_at"] != "2026-07-06 09:30:00":
        raise SystemExit("/api/crew-forms should expose requirement_confirmed_at for confirmed entries")
    if second_work_entry["readiness_state"] != "ready" or second_work_entry["readiness_reason"] != "requirement_confirmed":
        raise SystemExit("/api/crew-forms confirmed requirement entry should be ready with requirement_confirmed reason")
    if second_work_entry["scheduling_gate_state"] != "allowed" or second_work_entry["scheduling_gate_reason"] != "requirement_confirmed":
        raise SystemExit("/api/crew-forms confirmed requirement entry should map to scheduling allowed with requirement_confirmed reason")
    if int(second_work_entry["id"]) != approved_entry_id:
        raise SystemExit("/api/crew-forms approved formal entry should preserve entry identity")
    if second_work_entry["formal_approval_state"] != "approved" or second_work_entry["formal_approval_status"] != "approved":
        raise SystemExit("/api/crew-forms approved entry should expose approved formal approval state")
    if second_work_entry["formal_approved_by"] != "formal_member" or second_work_entry["formal_approved_at"] != "2026-07-06 10:00:00":
        raise SystemExit("/api/crew-forms approved entry should expose persisted formal approval actor fields")
    vendor_c = active_vendors["VendorC"]
    if len(vendor_c["work_entries"]) != 1:
        raise SystemExit("/api/crew-forms should include no-requirement work entry for active vendor")
    vendor_c_entry = vendor_c["work_entries"][0]
    if vendor_c_entry["pre_entry_requirement"] != "":
        raise SystemExit("/api/crew-forms no-requirement entry should preserve empty requirement text")
    if vendor_c_entry["readiness_state"] != "ready" or vendor_c_entry["readiness_reason"] != "no_requirement":
        raise SystemExit("/api/crew-forms no-requirement entry should be ready with no_requirement reason")
    if vendor_c_entry["scheduling_gate_state"] != "allowed" or vendor_c_entry["scheduling_gate_reason"] != "no_requirement":
        raise SystemExit("/api/crew-forms no-requirement entry should map to scheduling allowed with no_requirement reason")
    if vendor_c_entry["formal_approval_state"] != "pending" or vendor_c_entry["formal_approval_status"] != "pending":
        raise SystemExit("/api/crew-forms no-requirement entry without approval should expose pending formal approval state")
    if vendor_c_entry["formal_approved_by"] != "" or vendor_c_entry["formal_approved_at"] != "":
        raise SystemExit("/api/crew-forms no-requirement pending approval entry should keep actor fields empty")
    if vendor_c["contact"]["id"] is not None:
        raise SystemExit("active vendor without contacts should use empty compatibility contact")
    if vendor_c["contact"]["display_name"] != "":
        raise SystemExit("empty compatibility contact should use empty display_name")
    if vendor_c["contacts"] != []:
        raise SystemExit("active vendor without contacts should return empty contacts array")
    if vendor_c["contact"]["contact_name"] != "" or vendor_c["contact"]["contact_phone"] != "":
        raise SystemExit("empty compatibility contact should preserve readonly-safe blank fields")

    scheduling_gate_snapshot = {
        ("VendorA", "Need power off"): (
            first_work_entry["scheduling_gate_state"],
            first_work_entry["scheduling_gate_reason"],
        ),
        ("VendorA", "Need lift access"): (
            second_work_entry["scheduling_gate_state"],
            second_work_entry["scheduling_gate_reason"],
        ),
        ("VendorC", ""): (
            vendor_c_entry["scheduling_gate_state"],
            vendor_c_entry["scheduling_gate_reason"],
        ),
    }
    expected_scheduling_gate_snapshot = {
        ("VendorA", "Need power off"): ("warning", "requirement_pending"),
        ("VendorA", "Need lift access"): ("allowed", "requirement_confirmed"),
        ("VendorC", ""): ("allowed", "no_requirement"),
    }
    if scheduling_gate_snapshot != expected_scheduling_gate_snapshot:
        raise SystemExit(
            f"/api/crew-forms scheduling gate contract regression: {scheduling_gate_snapshot!r}"
        )
    if {state for state, _reason in scheduling_gate_snapshot.values()} != {"warning", "allowed"}:
        raise SystemExit("/api/crew-forms scheduling gate state set should remain warning/allowed only")

    inactive_names = {item["vendor_name"] for item in crew_forms["inactive_contacts"]}
    if "VendorB" not in inactive_names:
        raise SystemExit("inactive vendor contacts should remain visible in inactive_contacts")
    vendor_b = next(item for item in crew_forms["inactive_contacts"] if item["vendor_name"] == "VendorB")
    if not isinstance(vendor_b.get("contacts"), list) or len(vendor_b["contacts"]) != 1:
        raise SystemExit("inactive_contacts should be grouped by vendor with contacts array")
    if vendor_b["contact"]["contact_name"] != "Bob":
        raise SystemExit("inactive vendor compatibility contact should remain available")

    contact_insert = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Zoe",
            "contact_title": "Lead",
            "contact_phone": "0900000009",
            "is_primary": 1,
        },
    )
    if contact_insert.status_code != 200 or not contact_insert.get_json().get("ok"):
        raise SystemExit("/api/vendor-contact insert should succeed")
    inserted_payload = contact_insert.get_json()
    inserted_contact = inserted_payload["contact"]
    if inserted_contact["contact_name"] != "Zoe":
        raise SystemExit("/api/vendor-contact insert returned unexpected contact_name")
    if inserted_contact["contact_title"] != "Lead":
        raise SystemExit("/api/vendor-contact insert should persist contact_title")
    if inserted_contact["display_name"] != "Lead Zoe":
        raise SystemExit("/api/vendor-contact insert should build display_name from title + name")
    if inserted_contact["is_primary"] != 1 or inserted_contact["contact_order"] != 0:
        raise SystemExit("/api/vendor-contact insert should return expected primary/order defaults")
    if len(inserted_payload["contacts"]) != 1:
        raise SystemExit("/api/vendor-contact insert should return vendor contacts list")
    if inserted_payload["contact"]["id"] != inserted_payload["contacts"][0]["id"]:
        raise SystemExit("/api/vendor-contact response contract should keep contact == contacts[0]")

    second_contact_insert = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Zara",
            "contact_title": "Supervisor",
            "contact_phone": "0900000010",
            "is_primary": 0,
        },
    )
    if second_contact_insert.status_code != 200 or not second_contact_insert.get_json().get("ok"):
        raise SystemExit("/api/vendor-contact second insert should succeed")
    second_payload = second_contact_insert.get_json()
    if second_payload["contact"]["id"] != second_payload["contacts"][0]["id"]:
        raise SystemExit("/api/vendor-contact should keep compatibility contact == contacts[0] after second insert")
    if len(second_payload["contacts"]) != 2:
        raise SystemExit("/api/vendor-contact should allow multiple rows per sheet/vendor")
    second_contact = next(
        (item for item in second_payload["contacts"] if item["contact_name"] == "Zara"),
        None,
    )
    if second_contact is None:
        raise SystemExit("/api/vendor-contact should include the second inserted contact in contacts array")
    if second_contact["id"] == inserted_contact["id"]:
        raise SystemExit("/api/vendor-contact should assign a distinct id to the second contact")
    if second_contact["contact_order"] != 1:
        raise SystemExit("/api/vendor-contact should auto increment contact_order")
    if [item["contact_name"] for item in second_payload["contacts"]] != ["Zoe", "Zara"]:
        raise SystemExit("/api/vendor-contact contacts should remain sorted by primary/order")
    if second_payload["contacts"][1]["display_name"] != "Supervisor Zara":
        raise SystemExit("/api/vendor-contact should serialize display_name for all contacts")

    contact_update = client.post(
        "/api/vendor-contact",
        json={
            "id": second_contact["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Zara Updated",
            "contact_title": "Coordinator",
            "contact_phone": "0900000011",
            "is_primary": 1,
            "contact_order": 1,
        },
    )
    if contact_update.status_code != 200 or not contact_update.get_json().get("ok"):
        raise SystemExit("/api/vendor-contact update should succeed")
    updated_payload = contact_update.get_json()
    updated_contact = updated_payload["contact"]
    if updated_contact["id"] != second_contact["id"]:
        raise SystemExit("/api/vendor-contact update should target the requested id")
    if updated_contact["contact_name"] != "Zara Updated" or updated_contact["contact_title"] != "Coordinator":
        raise SystemExit("/api/vendor-contact update returned unexpected payload")
    if updated_contact["display_name"] != "Coordinator Zara Updated":
        raise SystemExit("/api/vendor-contact update should refresh display_name")
    if [item["contact_name"] for item in updated_payload["contacts"]] != ["Zara Updated", "Zoe"]:
        raise SystemExit("/api/vendor-contact update should return sorted contacts after primary switch")
    if updated_payload["contacts"][1]["is_primary"] != 0:
        raise SystemExit("/api/vendor-contact should clear sibling primary flags")
    if updated_payload["contact"]["id"] != updated_payload["contacts"][0]["id"]:
        raise SystemExit("/api/vendor-contact update should keep contact compatibility contract")

    zero_primary_update = client.post(
        "/api/vendor-contact",
        json={
            "id": inserted_contact["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Zoe",
            "contact_title": "Lead",
            "contact_phone": "0900000009",
            "is_primary": 0,
            "contact_order": 0,
        },
    )
    if zero_primary_update.status_code != 200 or not zero_primary_update.get_json().get("ok"):
        raise SystemExit("/api/vendor-contact should allow clearing one contact primary flag")
    zero_primary_update_2 = client.post(
        "/api/vendor-contact",
        json={
            "id": second_contact["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Zara Updated",
            "contact_title": "Coordinator",
            "contact_phone": "0900000011",
            "is_primary": 0,
            "contact_order": 1,
        },
    )
    if zero_primary_update_2.status_code != 200 or not zero_primary_update_2.get_json().get("ok"):
        raise SystemExit("/api/vendor-contact should allow all contacts to be non-primary")
    if any(item["is_primary"] != 0 for item in zero_primary_update_2.get_json()["contacts"]):
        raise SystemExit("/api/vendor-contact should allow all is_primary values to be 0")
    if zero_primary_update_2.get_json()["contact"]["id"] != zero_primary_update_2.get_json()["contacts"][0]["id"]:
        raise SystemExit("compatibility contact should still be derived from contacts[0] when all primaries are zero")

    long_title = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Title Too Long",
            "contact_title": "T" * 101,
            "contact_phone": "0900000000",
        },
    )
    if long_title.status_code != 400:
        raise SystemExit("invalid contact_title should return HTTP 400")

    long_phone = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorZ",
            "contact_name": "Phone Too Long",
            "contact_title": "",
            "contact_phone": "9" * 51,
        },
    )
    if long_phone.status_code != 400:
        raise SystemExit("invalid contact_phone should return HTTP 400")

    cross_sheet_update = client.post(
        "/api/vendor-contact",
        json={
            "id": second_contact["id"],
            "sheet_id": 2,
            "vendor_name": "VendorZ",
            "contact_name": "Cross Sheet",
            "contact_title": "",
            "contact_phone": "0900000000",
        },
    )
    if cross_sheet_update.status_code != 400:
        raise SystemExit("cross-sheet update should fail before allowing a write")
    if cross_sheet_update.get_json()["error"]["code"] != "cross_sheet_update_not_allowed":
        raise SystemExit("cross-sheet update should use cross_sheet_update_not_allowed")

    title_only_contact = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorTitleOnly",
            "contact_name": "",
            "contact_title": "工地主任",
            "contact_phone": "",
            "is_primary": 1,
        },
    )
    if title_only_contact.status_code != 200 or title_only_contact.get_json()["contact"]["display_name"] != "工地主任":
        raise SystemExit("display_name should support title-only contacts")

    name_only_contact = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorNameOnly",
            "contact_name": "王小明",
            "contact_title": "",
            "contact_phone": "",
            "is_primary": 1,
        },
    )
    if name_only_contact.status_code != 200 or name_only_contact.get_json()["contact"]["display_name"] != "王小明":
        raise SystemExit("display_name should support name-only contacts")

    both_empty_contact = client.post(
        "/api/vendor-contact",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorEmptyDisplay",
            "contact_name": "",
            "contact_title": "",
            "contact_phone": "",
            "is_primary": 1,
        },
    )
    if both_empty_contact.status_code != 200 or both_empty_contact.get_json()["contact"]["display_name"] != "":
        raise SystemExit("display_name should support empty title/name contacts")

    entry_insert = client.post(
        "/api/vendor-work-entry",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "planned_at": "",
            "planned_headcount": 4,
            "actual_headcount": 0,
            "work_content": "Insert Crew",
            "pre_entry_requirement": "Insert Requirement",
            "work_headcount": 0,
            "entry_order": 2,
        },
    )
    if entry_insert.status_code != 200 or not entry_insert.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry insert should succeed")
    inserted_entry = entry_insert.get_json()["entry"]
    if inserted_entry["business_date"] != business_date:
        raise SystemExit("/api/vendor-work-entry insert should default business_date from helper")
    for unexpected in ("requirement_status", "requirement_confirmed_by", "requirement_confirmed_at"):
        if unexpected in inserted_entry:
            raise SystemExit(f"/api/vendor-work-entry insert should not expose {unexpected} in response payload")
    if inserted_entry.get("pre_entry_requirement") != "Insert Requirement":
        raise SystemExit("/api/vendor-work-entry insert should return persisted pre_entry_requirement")
    inserted_row = conn.execute(
        "SELECT pre_entry_requirement FROM vendor_work_entries WHERE id = ?",
        (inserted_entry["id"],),
    ).fetchone()
    if inserted_row is None or inserted_row["pre_entry_requirement"] != "Insert Requirement":
        raise SystemExit("/api/vendor-work-entry insert should persist pre_entry_requirement in DB")

    entry_update = client.post(
        "/api/vendor-work-entry",
        json={
            "id": inserted_entry["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "business_date": business_date,
            "planned_at": "2000-01-01 11:00",
            "planned_headcount": 4,
            "actual_headcount": 1,
            "work_content": "Insert Crew Updated",
            "pre_entry_requirement": "Insert Requirement Updated",
            "work_headcount": 1,
            "entry_order": 2,
        },
    )
    if entry_update.status_code != 200 or not entry_update.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry update should succeed")
    updated_entry = entry_update.get_json()["entry"]
    if updated_entry["actual_headcount"] != 1 or updated_entry["work_content"] != "Insert Crew Updated":
        raise SystemExit("/api/vendor-work-entry update returned unexpected payload")
    for unexpected in ("requirement_status", "requirement_confirmed_by", "requirement_confirmed_at"):
        if unexpected in updated_entry:
            raise SystemExit(f"/api/vendor-work-entry update should not expose {unexpected} in response payload")
    if updated_entry.get("pre_entry_requirement") != "Insert Requirement Updated":
        raise SystemExit("/api/vendor-work-entry update should return updated pre_entry_requirement")
    updated_row = conn.execute(
        "SELECT pre_entry_requirement FROM vendor_work_entries WHERE id = ?",
        (inserted_entry["id"],),
    ).fetchone()
    if updated_row is None or updated_row["pre_entry_requirement"] != "Insert Requirement Updated":
        raise SystemExit("/api/vendor-work-entry update should persist pre_entry_requirement in DB")

    missing_requirement_create = client.post(
        "/api/vendor-work-entry",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "planned_at": "",
            "planned_headcount": 1,
            "actual_headcount": 0,
            "work_content": "Missing Requirement Create",
            "work_headcount": 0,
            "entry_order": 3,
        },
    )
    if missing_requirement_create.status_code != 200 or not missing_requirement_create.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry create without pre_entry_requirement should succeed")
    missing_requirement_create_entry = missing_requirement_create.get_json()["entry"]
    if missing_requirement_create_entry.get("pre_entry_requirement") != "":
        raise SystemExit("/api/vendor-work-entry create without pre_entry_requirement should normalize to empty string")
    missing_create_row = conn.execute(
        "SELECT pre_entry_requirement FROM vendor_work_entries WHERE id = ?",
        (missing_requirement_create_entry["id"],),
    ).fetchone()
    if missing_create_row is None or missing_create_row["pre_entry_requirement"] != "":
        raise SystemExit("/api/vendor-work-entry create without pre_entry_requirement should persist empty string")

    whitespace_requirement_update = client.post(
        "/api/vendor-work-entry",
        json={
            "id": inserted_entry["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "business_date": business_date,
            "planned_at": "2000-01-01 11:00",
            "planned_headcount": 4,
            "actual_headcount": 1,
            "work_content": "Insert Crew Updated",
            "pre_entry_requirement": "   Trim Me   ",
            "work_headcount": 1,
            "entry_order": 2,
        },
    )
    if whitespace_requirement_update.status_code != 200 or not whitespace_requirement_update.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry update with whitespace pre_entry_requirement should succeed")
    whitespace_requirement_entry = whitespace_requirement_update.get_json()["entry"]
    if whitespace_requirement_entry.get("pre_entry_requirement") != "Trim Me":
        raise SystemExit("/api/vendor-work-entry update should trim pre_entry_requirement")

    missing_requirement_update = client.post(
        "/api/vendor-work-entry",
        json={
            "id": inserted_entry["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "business_date": business_date,
            "planned_at": "2000-01-01 11:00",
            "planned_headcount": 4,
            "actual_headcount": 1,
            "work_content": "Insert Crew Updated",
            "work_headcount": 1,
            "entry_order": 2,
        },
    )
    if missing_requirement_update.status_code != 200 or not missing_requirement_update.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry update without pre_entry_requirement should succeed")
    missing_requirement_update_entry = missing_requirement_update.get_json()["entry"]
    if missing_requirement_update_entry.get("pre_entry_requirement") != "":
        raise SystemExit("/api/vendor-work-entry update without pre_entry_requirement should normalize to empty string")
    missing_update_row = conn.execute(
        "SELECT pre_entry_requirement FROM vendor_work_entries WHERE id = ?",
        (inserted_entry["id"],),
    ).fetchone()
    if missing_update_row is None or missing_update_row["pre_entry_requirement"] != "":
        raise SystemExit("/api/vendor-work-entry update without pre_entry_requirement should persist empty string")

    over_limit_requirement = "R" * 501
    unchanged_before_invalid_requirement = conn.execute(
        "SELECT pre_entry_requirement, updated_at FROM vendor_work_entries WHERE id = ?",
        (inserted_entry["id"],),
    ).fetchone()
    invalid_requirement_entry = client.post(
        "/api/vendor-work-entry",
        json={
            "id": inserted_entry["id"],
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "business_date": business_date,
            "planned_at": "2000-01-01 11:00",
            "planned_headcount": 4,
            "actual_headcount": 1,
            "work_content": "Insert Crew Updated",
            "pre_entry_requirement": over_limit_requirement,
            "work_headcount": 1,
            "entry_order": 2,
        },
    )
    if invalid_requirement_entry.status_code != 400:
        raise SystemExit("over-limit pre_entry_requirement should return HTTP 400")
    invalid_requirement_payload = invalid_requirement_entry.get_json()
    if invalid_requirement_payload.get("error", {}).get("code") != "invalid_pre_entry_requirement":
        raise SystemExit("over-limit pre_entry_requirement should use invalid_pre_entry_requirement error code")
    if invalid_requirement_payload.get("error", {}).get("message") != "pre_entry_requirement must be 500 characters or fewer.":
        raise SystemExit("over-limit pre_entry_requirement should return the expected error message")
    unchanged_after_invalid_requirement = conn.execute(
        "SELECT pre_entry_requirement, updated_at FROM vendor_work_entries WHERE id = ?",
        (inserted_entry["id"],),
    ).fetchone()
    if tuple(unchanged_before_invalid_requirement) != tuple(unchanged_after_invalid_requirement):
        raise SystemExit("over-limit pre_entry_requirement should not modify DB state")

    invalid_entry = client.post(
        "/api/vendor-work-entry",
        json={
            "sheet_id": sheet_id,
            "vendor_name": "VendorA",
            "planned_headcount": -1,
            "actual_headcount": 0,
            "work_content": "",
            "work_headcount": 0,
            "entry_order": 0,
        },
    )
    if invalid_entry.status_code != 400:
        raise SystemExit("invalid headcount should return HTTP 400")
    invalid_payload = invalid_entry.get_json()
    if invalid_payload.get("ok") is not False or "error" not in invalid_payload:
        raise SystemExit("invalid headcount should use standard error payload")

    followups_response = client.get(f"/api/crew-followups?sheet_id={sheet_id}&business_date={business_date}")
    if followups_response.status_code != 200:
        raise SystemExit("/api/crew-followups should return 200")
    followups = followups_response.get_json()
    followup_names = {item["vendor_name"] for item in followups["items"]}
    if "VendorC" not in followup_names:
        raise SystemExit("/api/crew-followups should include active vendor without planned_at")
    if "VendorA" in followup_names:
        raise SystemExit("/api/crew-followups should exclude vendor with planned_at entries")

    invalid_followups_response = client.get(
        f"/api/crew-followups?sheet_id={sheet_id}&business_date=abc"
    )
    if invalid_followups_response.status_code != 400:
        raise SystemExit("/api/crew-followups invalid business_date should return 400")
    invalid_followups_payload = invalid_followups_response.get_json()
    if invalid_followups_payload.get("ok") is not False:
        raise SystemExit("/api/crew-followups invalid business_date should return ok=false")
    invalid_followups_error = invalid_followups_payload.get("error") or {}
    if invalid_followups_error.get("code") != "invalid_business_date":
        raise SystemExit("/api/crew-followups invalid business_date should preserve invalid_business_date")
    if invalid_followups_error.get("message") != "business_date must use YYYY-MM-DD.":
        raise SystemExit("/api/crew-followups invalid business_date should return deterministic error message")

    impossible_followups_response = client.get(
        f"/api/crew-followups?sheet_id={sheet_id}&business_date=2026-02-30"
    )
    if impossible_followups_response.status_code != 400:
        raise SystemExit("/api/crew-followups impossible business_date should return 400")
    impossible_followups_payload = impossible_followups_response.get_json()
    if impossible_followups_payload.get("ok") is not False:
        raise SystemExit("/api/crew-followups impossible business_date should return ok=false")
    impossible_followups_error = impossible_followups_payload.get("error") or {}
    if impossible_followups_error.get("code") != "invalid_business_date":
        raise SystemExit("/api/crew-followups impossible business_date should preserve invalid_business_date")
    if impossible_followups_error.get("message") != "business_date must use YYYY-MM-DD.":
        raise SystemExit("/api/crew-followups impossible business_date should return deterministic error message")

    summary_response = client.get(f"/api/crew-daily-summary?sheet_id={sheet_id}&business_date={business_date}")
    if summary_response.status_code != 200:
        raise SystemExit("/api/crew-daily-summary should return 200")
    summary = summary_response.get_json()
    expected_summary_top_level_keys = {"ok", "sheet_id", "business_date", "items", "totals"}
    if set(summary.keys()) != expected_summary_top_level_keys:
        raise SystemExit("/api/crew-daily-summary should keep stable top-level response shape")
    expected_summary_item_keys = {
        "id",
        "vendor_name",
        "actual_headcount",
        "work_content",
        "work_headcount",
        "planned_at",
        "planned_headcount",
        "entry_order",
    }
    for item in summary["items"]:
        if set(item.keys()) != expected_summary_item_keys:
            raise SystemExit("/api/crew-daily-summary items should keep stable response shape")
    expected_summary_totals_keys = {
        "vendors",
        "actual_headcount_sum",
        "work_headcount_sum",
    }
    if set(summary["totals"].keys()) != expected_summary_totals_keys:
        raise SystemExit("/api/crew-daily-summary totals should keep stable response shape")
    if not summary.get("ok"):
        raise SystemExit("/api/crew-daily-summary should report ok=true")
    summary_contents = {item["work_content"] for item in summary["items"]}
    if "Summary Crew" not in summary_contents or "Insert Crew Updated" not in summary_contents:
        raise SystemExit("/api/crew-daily-summary should include actual_headcount > 0 entries")
    if summary["totals"]["actual_headcount_sum"] != 3:
        raise SystemExit("/api/crew-daily-summary returned unexpected actual_headcount_sum")
    if summary["totals"]["work_headcount_sum"] != 3:
        raise SystemExit("/api/crew-daily-summary returned unexpected work_headcount_sum")
    empty_business_date = "2099-01-01"
    empty_summary_response = client.get(
        f"/api/crew-daily-summary?sheet_id={sheet_id}&business_date={empty_business_date}"
    )
    if empty_summary_response.status_code != 200:
        raise SystemExit("/api/crew-daily-summary should return 200 for empty business_date results")
    empty_summary = empty_summary_response.get_json()
    if empty_summary != {
        "ok": True,
        "sheet_id": sheet_id,
        "business_date": empty_business_date,
        "items": [],
        "totals": {
            "vendors": 0,
            "actual_headcount_sum": 0,
            "work_headcount_sum": 0,
        },
    }:
        raise SystemExit("/api/crew-daily-summary should return deterministic empty-result payload")

    invalid_summary_sheet_response = client.get(
        f"/api/crew-daily-summary?sheet_id=abc&business_date={business_date}"
    )
    if invalid_summary_sheet_response.status_code != 400:
        raise SystemExit("/api/crew-daily-summary invalid sheet_id should return 400")
    invalid_summary_sheet_payload = invalid_summary_sheet_response.get_json()
    if invalid_summary_sheet_payload.get("ok") is not False:
        raise SystemExit("/api/crew-daily-summary invalid sheet_id should return ok=false")
    invalid_summary_sheet_error = invalid_summary_sheet_payload.get("error") or {}
    if invalid_summary_sheet_error.get("code") != "invalid_sheet_id":
        raise SystemExit("/api/crew-daily-summary invalid sheet_id should preserve invalid_sheet_id")
    if invalid_summary_sheet_error.get("message") != "sheet_id is required and must be a valid integer.":
        raise SystemExit("/api/crew-daily-summary invalid sheet_id should return deterministic error message")

    invalid_summary_response = client.get(
        f"/api/crew-daily-summary?sheet_id={sheet_id}&business_date=abc"
    )
    if invalid_summary_response.status_code != 400:
        raise SystemExit("/api/crew-daily-summary invalid business_date should return 400")
    invalid_summary_payload = invalid_summary_response.get_json()
    if invalid_summary_payload.get("ok") is not False:
        raise SystemExit("/api/crew-daily-summary invalid business_date should return ok=false")
    invalid_summary_error = invalid_summary_payload.get("error") or {}
    if invalid_summary_error.get("code") != "invalid_business_date":
        raise SystemExit("/api/crew-daily-summary invalid business_date should preserve invalid_business_date")
    if invalid_summary_error.get("message") != "business_date must use YYYY-MM-DD.":
        raise SystemExit("/api/crew-daily-summary invalid business_date should return deterministic error message")

    impossible_summary_response = client.get(
        f"/api/crew-daily-summary?sheet_id={sheet_id}&business_date=2026-02-30"
    )
    if impossible_summary_response.status_code != 400:
        raise SystemExit("/api/crew-daily-summary impossible business_date should return 400")
    impossible_summary_payload = impossible_summary_response.get_json()
    if impossible_summary_payload.get("ok") is not False:
        raise SystemExit("/api/crew-daily-summary impossible business_date should return ok=false")
    impossible_summary_error = impossible_summary_payload.get("error") or {}
    if impossible_summary_error.get("code") != "invalid_business_date":
        raise SystemExit("/api/crew-daily-summary impossible business_date should preserve invalid_business_date")
    if impossible_summary_error.get("message") != "business_date must use YYYY-MM-DD.":
        raise SystemExit("/api/crew-daily-summary impossible business_date should return deterministic error message")

    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = crew_read_member_id
        session["username"] = "crew_read_member"
        session["display_name"] = "crew_read_member"
        session["role"] = "member"
    missing_site_summary_response = client.get(
        f"/api/crew-daily-summary?sheet_id={sheet_id}&business_date={business_date}"
    )
    if missing_site_summary_response.status_code != 403:
        raise SystemExit("/api/crew-daily-summary missing current site should return 403")
    missing_site_summary_payload = missing_site_summary_response.get_json()
    if missing_site_summary_payload.get("ok") is not False:
        raise SystemExit("/api/crew-daily-summary missing current site should return ok=false")
    error = missing_site_summary_payload.get("error") or {}
    if error.get("code") != "site_context_invalid":
        raise SystemExit("/api/crew-daily-summary missing current site should preserve site_context_invalid")
    if error.get("message") != "current_site_id is missing or invalid.":
        raise SystemExit("/api/crew-daily-summary missing current site should return deterministic error message")

    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = crew_read_member_id
        session["username"] = "crew_read_member"
        session["display_name"] = "crew_read_member"
        session["role"] = "member"
    missing_site_missing_response = client.get(
        f"/api/crew-missing?sheet_id={sheet_id}&business_date={business_date}"
    )
    if missing_site_missing_response.status_code != 403:
        raise SystemExit("/api/crew-missing missing current site should return 403")
    missing_site_missing_payload = missing_site_missing_response.get_json()
    if missing_site_missing_payload.get("ok") is not False:
        raise SystemExit("/api/crew-missing missing current site should return ok=false")
    missing_site_missing_error = missing_site_missing_payload.get("error") or {}
    if missing_site_missing_error.get("code") != "site_context_invalid":
        raise SystemExit("/api/crew-missing missing current site should preserve site_context_invalid")
    if missing_site_missing_error.get("message") != "current_site_id is missing or invalid.":
        raise SystemExit("/api/crew-missing missing current site should return deterministic error message")

    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = crew_read_member_id
        session["username"] = "crew_read_member"
        session["display_name"] = "crew_read_member"
        session["role"] = "member"
        session["current_site_id"] = sheet_site_id
        session["current_site_name"] = module.DEFAULT_SITE_NAME
    cross_site_missing_response = client.get(
        f"/api/crew-missing?sheet_id=2&business_date={business_date}"
    )
    if cross_site_missing_response.status_code != 403:
        raise SystemExit("/api/crew-missing cross-site read should return 403")
    cross_site_missing_payload = cross_site_missing_response.get_json()
    if cross_site_missing_payload.get("ok") is not False:
        raise SystemExit("/api/crew-missing cross-site read should return ok=false")
    cross_site_missing_error = cross_site_missing_payload.get("error") or {}
    if cross_site_missing_error.get("code") != "sheet_not_in_current_site":
        raise SystemExit("/api/crew-missing cross-site read should preserve sheet_not_in_current_site")
    if cross_site_missing_error.get("message") != "sheet_id does not belong to the current site.":
        raise SystemExit("/api/crew-missing cross-site read should return deterministic error message")

    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = crew_read_member_id
        session["username"] = "crew_read_member"
        session["display_name"] = "crew_read_member"
        session["role"] = "member"
        session["current_site_id"] = sheet_site_id
        session["current_site_name"] = module.DEFAULT_SITE_NAME
    with module.db() as conn:
        conn.execute("DELETE FROM user_site_permissions WHERE user_id = ?", (crew_read_member_id,))
        conn.commit()
    permission_missing_response = client.get(
        f"/api/crew-missing?sheet_id={sheet_id}&business_date={business_date}"
    )
    if permission_missing_response.status_code != 403:
        raise SystemExit("/api/crew-missing permission removed should return 403")
    permission_missing_payload = permission_missing_response.get_json()
    if permission_missing_payload.get("ok") is not False:
        raise SystemExit("/api/crew-missing permission removed should return ok=false")
    permission_missing_error = permission_missing_payload.get("error") or {}
    if permission_missing_error.get("code") != "site_permission_missing":
        raise SystemExit("/api/crew-missing permission removed should preserve site_permission_missing")
    if permission_missing_error.get("message") != "current user no longer has permission for the current site.":
        raise SystemExit("/api/crew-missing permission removed should return deterministic error message")

    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    missing_response = client.get(f"/api/crew-missing?sheet_id={sheet_id}&business_date={business_date}")
    if missing_response.status_code != 200:
        raise SystemExit("/api/crew-missing should return 200")
    missing = missing_response.get_json()
    expected_missing_top_level_keys = {"ok", "sheet_id", "business_date", "items"}
    if set(missing.keys()) != expected_missing_top_level_keys:
        raise SystemExit("/api/crew-missing should keep stable top-level response shape")
    expected_missing_item_keys = {
        "vendor_name",
        "contact_name",
        "contact_phone",
        "planned_at",
        "planned_headcount",
        "actual_headcount",
        "pending_items",
    }
    for item in missing["items"]:
        if set(item.keys()) != expected_missing_item_keys:
            raise SystemExit("/api/crew-missing items should keep stable response shape")
    missing_names = {item["vendor_name"] for item in missing["items"]}
    if "VendorA" not in missing_names:
        raise SystemExit("/api/crew-missing should include planned vendor with zero actual headcount")
    if "VendorC" in missing_names:
        raise SystemExit("/api/crew-missing should ignore vendors without planned_at")
    missing_item = next(item for item in missing["items"] if item["vendor_name"] == "VendorA")
    if missing_item["contact_name"] != "Alice" or missing_item["planned_headcount"] != 3:
        raise SystemExit("/api/crew-missing returned unexpected vendor payload")
    if "Pending Paint" not in missing_item["pending_items"] and "Pending Patch" not in missing_item["pending_items"]:
        raise SystemExit("/api/crew-missing should include pending_items for active vendor")

    empty_missing_business_date = "2099-01-01"
    empty_missing_response = client.get(
        f"/api/crew-missing?sheet_id={sheet_id}&business_date={empty_missing_business_date}"
    )
    if empty_missing_response.status_code != 200:
        raise SystemExit("/api/crew-missing should return 200 for empty business_date results")
    empty_missing = empty_missing_response.get_json()
    if set(empty_missing.keys()) != expected_missing_top_level_keys:
        raise SystemExit("/api/crew-missing empty result should keep stable top-level response shape")
    if empty_missing != {
        "ok": True,
        "sheet_id": sheet_id,
        "business_date": empty_missing_business_date,
        "items": [],
    }:
        raise SystemExit("/api/crew-missing should return deterministic empty-result payload")

    invalid_missing_sheet_response = client.get(
        f"/api/crew-missing?sheet_id=abc&business_date={business_date}"
    )
    if invalid_missing_sheet_response.status_code != 400:
        raise SystemExit("/api/crew-missing invalid sheet_id should return 400")
    invalid_missing_sheet_payload = invalid_missing_sheet_response.get_json()
    if invalid_missing_sheet_payload.get("ok") is not False:
        raise SystemExit("/api/crew-missing invalid sheet_id should return ok=false")
    invalid_missing_sheet_error = invalid_missing_sheet_payload.get("error") or {}
    if invalid_missing_sheet_error.get("code") != "invalid_sheet_id":
        raise SystemExit("/api/crew-missing invalid sheet_id should preserve invalid_sheet_id")
    if invalid_missing_sheet_error.get("message") != "sheet_id is required and must be a valid integer.":
        raise SystemExit("/api/crew-missing invalid sheet_id should return deterministic error message")

    invalid_missing_response = client.get(
        f"/api/crew-missing?sheet_id={sheet_id}&business_date=abc"
    )
    if invalid_missing_response.status_code != 400:
        raise SystemExit("/api/crew-missing invalid business_date should return 400")
    invalid_missing_payload = invalid_missing_response.get_json()
    if invalid_missing_payload.get("ok") is not False:
        raise SystemExit("/api/crew-missing invalid business_date should return ok=false")
    invalid_missing_error = invalid_missing_payload.get("error") or {}
    if invalid_missing_error.get("code") != "invalid_business_date":
        raise SystemExit("/api/crew-missing invalid business_date should preserve invalid_business_date")
    if invalid_missing_error.get("message") != "business_date must use YYYY-MM-DD.":
        raise SystemExit("/api/crew-missing invalid business_date should return deterministic error message")

    impossible_missing_response = client.get(
        f"/api/crew-missing?sheet_id={sheet_id}&business_date=2026-02-30"
    )
    if impossible_missing_response.status_code != 400:
        raise SystemExit("/api/crew-missing impossible business_date should return 400")
    impossible_missing_payload = impossible_missing_response.get_json()
    if impossible_missing_payload.get("ok") is not False:
        raise SystemExit("/api/crew-missing impossible business_date should return ok=false")
    impossible_missing_error = impossible_missing_payload.get("error") or {}
    if impossible_missing_error.get("code") != "invalid_business_date":
        raise SystemExit("/api/crew-missing impossible business_date should preserve invalid_business_date")
    if impossible_missing_error.get("message") != "business_date must use YYYY-MM-DD.":
        raise SystemExit("/api/crew-missing impossible business_date should return deterministic error message")

    refreshed_crew_forms = client.get(f"/api/crew-forms?sheet_id={sheet_id}").get_json()
    refreshed_inactive_names = {item["vendor_name"] for item in refreshed_crew_forms["inactive_contacts"]}
    if "VendorZ" not in refreshed_inactive_names:
        raise SystemExit("inactive vendor contact should persist after upsert")
    refreshed_vendor_z = next(item for item in refreshed_crew_forms["inactive_contacts"] if item["vendor_name"] == "VendorZ")
    if len(refreshed_vendor_z["contacts"]) != 2:
        raise SystemExit("inactive vendor should return all saved contacts")
    if refreshed_vendor_z["contact"]["id"] != refreshed_vendor_z["contacts"][0]["id"]:
        raise SystemExit("compatibility contact should use the first sorted contact")
    if refreshed_vendor_z["contact"]["display_name"] != refreshed_vendor_z["contacts"][0]["display_name"]:
        raise SystemExit("compatibility contact should share display_name with contacts[0]")
    with module.db() as conn:
        vendor_z_work_entries = conn.execute(
            "SELECT COUNT(*) FROM vendor_work_entries WHERE vendor_name = ?",
            ("VendorZ",),
        ).fetchone()[0]
    if vendor_z_work_entries != 0:
        raise SystemExit("/api/vendor-contact should not create vendor_work_entries")
    with module.db() as conn:
        order_vendor = "VendorOrderTest"
        if module.next_contact_order(conn, sheet_id=sheet_id, vendor_name=order_vendor) != 0:
            raise SystemExit("next_contact_order should start at 0 for first contact")
        conn.execute(
            "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sheet_id, order_vendor, "One", "", "", 0, 0),
        )
        if module.next_contact_order(conn, sheet_id=sheet_id, vendor_name=order_vendor) != 1:
            raise SystemExit("next_contact_order should increment to 1 for second contact")
        conn.execute(
            "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sheet_id, order_vendor, "Two", "", "", 0, 1),
        )
        if module.next_contact_order(conn, sheet_id=sheet_id, vendor_name=order_vendor) != 2:
            raise SystemExit("next_contact_order should increment to 2 for third contact")
        primary_vendor = "VendorPrimaryTest"
        conn.execute(
            "INSERT INTO vendor_contacts (id, sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (9001, sheet_id, primary_vendor, "Primary A", "", "", 1, 0),
        )
        conn.execute(
            "INSERT INTO vendor_contacts (id, sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (9002, sheet_id, primary_vendor, "Primary B", "", "", 0, 1),
        )
        conn.execute(
            "INSERT INTO vendor_contacts (id, sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (9003, 2, primary_vendor, "Other Sheet", "", "", 1, 0),
        )
        conn.execute(
            "INSERT INTO vendor_contacts (id, sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (9004, sheet_id, 'OtherVendor', 'Other Vendor', '', '', 1, 0),
        )
        module.set_primary_contact(conn, sheet_id=sheet_id, vendor_name=primary_vendor, contact_id=9002)
        primary_rows = conn.execute(
            "SELECT id, is_primary FROM vendor_contacts WHERE sheet_id = ? AND vendor_name = ? ORDER BY id",
            (sheet_id, primary_vendor),
        ).fetchall()
        if [(row["id"], row["is_primary"]) for row in primary_rows] != [(9001, 0), (9002, 1)]:
            raise SystemExit("set_primary_contact should only update contacts within same sheet/vendor")
        other_sheet_row = conn.execute(
            "SELECT is_primary FROM vendor_contacts WHERE id = 9003"
        ).fetchone()
        other_vendor_row = conn.execute(
            "SELECT is_primary FROM vendor_contacts WHERE id = 9004"
        ).fetchone()
        if other_sheet_row["is_primary"] != 1 or other_vendor_row["is_primary"] != 1:
            raise SystemExit("set_primary_contact should not affect other sheets or vendors")

print("crew API smoke PASS")
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix="-crew-api-smoke.py", delete=False) as handle:
        handle.write(script)
        script_path = Path(handle.name)
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(app_db_path),
                str(ROOT_DIR),
            ],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        script_path.unlink(missing_ok=True)
    if "crew API smoke PASS" not in result.stdout:
        raise AssertionError("crew API smoke subprocess did not report PASS.")


def create_legacy_vendor_contacts_sqlite(path: Path) -> None:
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
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (unit_id, task_id)
        );
        CREATE TABLE unit_extra (
            unit_id INTEGER PRIMARY KEY,
            initial_check TEXT NOT NULL DEFAULT '',
            recheck_1 TEXT NOT NULL DEFAULT '',
            recheck_2 TEXT NOT NULL DEFAULT '',
            handover TEXT NOT NULL DEFAULT 'X',
            updated_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        CREATE TABLE vendor_contacts (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(sheet_id, vendor_name)
        );
        CREATE TABLE vendor_work_entries (
            id INTEGER PRIMARY KEY,
            sheet_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            business_date TEXT NOT NULL,
            planned_at TEXT NOT NULL,
            planned_headcount INTEGER NOT NULL,
            actual_headcount INTEGER NOT NULL,
            work_content TEXT NOT NULL,
            pre_entry_requirement TEXT,
            work_headcount INTEGER NOT NULL,
            entry_order INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute("INSERT INTO meta (key, value) VALUES ('site_title', 'demo')")
    conn.execute("INSERT INTO meta (key, value) VALUES ('excel_seeded', '2026-06-27T00:00:00')")
    conn.execute(
        "INSERT INTO users (id, username, display_name, password_hash, role, created_at) VALUES (1, 'admin', 'Admin', 'hash', 'admin', '2026-06-27T00:00:00')"
    )
    conn.execute(
        "INSERT INTO sheets (id, name, sort_order, created_at) VALUES (1, 'Sheet A', 1, '2026-06-27T00:00:00')"
    )
    conn.execute(
        "INSERT INTO tasks (id, sheet_id, col_index, vendor, location, name) VALUES (1, 1, 4, 'VendorA', 'Room', 'Task')"
    )
    conn.execute(
        "INSERT INTO floors (id, sheet_id, sort_order, name, block_name, unit_count) VALUES (1, 1, 1, '1F', 'A', 1)"
    )
    conn.execute("INSERT INTO units (id, floor_id, sort_order, name) VALUES (1, 1, 1, '101')")
    conn.execute(
        "INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at) VALUES (1, 1, 'X', 1, '2026-06-27T00:00:00')"
    )
    conn.execute(
        "INSERT INTO unit_extra (unit_id, initial_check, recheck_1, recheck_2, handover, updated_by, updated_at) VALUES (1, '', '', '', 'X', 1, '2026-06-27T00:00:00')"
    )
    conn.execute(
        "INSERT INTO extra_fields (id, sheet_id, field_key, name, field_type, sort_order, is_builtin, active) VALUES (1, 1, 'handover', 'Handover', 'status', 1, 1, 1)"
    )
    conn.execute(
        "INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at) VALUES (1, 'handover', 'X', 1, '2026-06-27T00:00:00')"
    )
    conn.execute(
        "INSERT INTO vendor_contacts (id, sheet_id, vendor_name, contact_name, contact_phone, created_at, updated_at) VALUES (1, 1, 'VendorA', 'Alice', '0900000001', '2026-06-27T00:00:00', '2026-06-27T00:00:00')"
    )
    conn.commit()
    conn.close()


def run_crew_schema_smoke_v2(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "vendor_contacts" not in tables:
        raise SystemExit("vendor_contacts table should exist after bootstrap")
    if "vendor_work_entries" not in tables:
        raise SystemExit("vendor_work_entries table should exist after bootstrap")
    if "formal_approvals" not in tables:
        raise SystemExit("formal_approvals table should exist after bootstrap")

    vendor_contacts_columns = [row["name"] for row in conn.execute("PRAGMA table_info(vendor_contacts)").fetchall()]
    for required in (
        "id", "sheet_id", "vendor_name", "contact_name", "contact_title",
        "contact_phone", "is_primary", "contact_order", "created_at", "updated_at",
    ):
        if required not in vendor_contacts_columns:
            raise SystemExit(f"vendor_contacts missing required column: {required}")

    vendor_work_entries_columns = [row["name"] for row in conn.execute("PRAGMA table_info(vendor_work_entries)").fetchall()]
    for required in (
        "id", "sheet_id", "vendor_name", "business_date", "planned_at",
        "planned_headcount", "actual_headcount", "work_content", "work_headcount",
        "entry_order", "pre_entry_requirement", "requirement_status",
        "requirement_confirmed_by", "requirement_confirmed_at", "created_at", "updated_at",
    ):
        if required not in vendor_work_entries_columns:
            raise SystemExit(f"vendor_work_entries missing required column: {required}")

    formal_approvals_columns = [row["name"] for row in conn.execute("PRAGMA table_info(formal_approvals)").fetchall()]
    for required in (
        "id", "entry_id", "sheet_id", "action", "approval_status",
        "approved_by", "approved_at", "created_at", "updated_at",
    ):
        if required not in formal_approvals_columns:
            raise SystemExit(f"formal_approvals missing required column: {required}")

    contact_indexes = conn.execute("PRAGMA index_list(vendor_contacts)").fetchall()
    contact_index_names = {row["name"] for row in contact_indexes}
    for required in ("idx_vendor_contacts_sheet_id", "idx_vendor_contacts_sheet_vendor", "idx_vendor_contacts_sheet_vendor_order"):
        if required not in contact_index_names:
            raise SystemExit(f"vendor_contacts missing expected index: {required}")

    for row in contact_indexes:
        if row["unique"]:
            cols = tuple(index_row["name"] for index_row in conn.execute(f"PRAGMA index_info({row['name']})").fetchall())
            if cols == ("sheet_id", "vendor_name"):
                raise SystemExit("vendor_contacts should not enforce legacy UNIQUE(sheet_id, vendor_name)")

    formal_indexes = conn.execute("PRAGMA index_list(formal_approvals)").fetchall()
    formal_index_names = {row["name"] for row in formal_indexes}
    for required in ("idx_formal_approvals_entry_action_unique", "idx_formal_approvals_sheet_id"):
        if required not in formal_index_names:
            raise SystemExit(f"formal_approvals missing expected index: {required}")

    conn.execute(
        "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Vendor", "Alice", "", "0900000001", 1, 0),
    )
    conn.execute(
        "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Vendor", "Bob", "Lead", "0900000002", 0, 1),
    )
    vendor_contact_count = conn.execute(
        "SELECT COUNT(*) FROM vendor_contacts WHERE sheet_id = 1 AND vendor_name = ?",
        ("Vendor",),
    ).fetchone()[0]
    if vendor_contact_count != 2:
        raise SystemExit("vendor_contacts should allow multiple rows for the same sheet/vendor")

if module.resolve_crew_business_date(datetime(2026, 6, 29, 8, 29, 0)) != "2026-06-28":
    raise SystemExit("resolve_crew_business_date should use previous day before 08:30")
if module.resolve_crew_business_date(datetime(2026, 6, 29, 8, 30, 0)) != "2026-06-29":
    raise SystemExit("resolve_crew_business_date should use same day at 08:30")
if module.resolve_crew_business_date(datetime(2026, 6, 29, 23, 59, 0)) != "2026-06-29":
    raise SystemExit("resolve_crew_business_date should use same day late night")

print("crew schema smoke v2 PASS")
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
    if "crew schema smoke v2 PASS" not in result.stdout:
        raise AssertionError("crew schema smoke v2 subprocess did not report PASS.")


def run_crew_schema_migration_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    create_legacy_vendor_contacts_sqlite(app_db_path)
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    migrated = conn.execute(
        "SELECT sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order FROM vendor_contacts ORDER BY id"
    ).fetchall()
    if len(migrated) != 1:
        raise SystemExit("legacy vendor_contacts migration should preserve row count")
    row = migrated[0]
    if row["contact_title"] != "":
        raise SystemExit("legacy vendor_contacts migration should default contact_title to empty string")
    if row["is_primary"] != 1:
        raise SystemExit("legacy vendor_contacts migration should default is_primary to 1")
    if row["contact_order"] != 0:
        raise SystemExit("legacy vendor_contacts migration should default contact_order to 0")

    contact_indexes = conn.execute("PRAGMA index_list(vendor_contacts)").fetchall()
    for index_row in contact_indexes:
        if index_row["unique"]:
            cols = tuple(
                info_row["name"] for info_row in conn.execute(f"PRAGMA index_info({index_row['name']})").fetchall()
            )
            if cols == ("sheet_id", "vendor_name"):
                raise SystemExit("legacy unique(sheet_id, vendor_name) should be removed after migration")

    work_columns = [col["name"] for col in conn.execute("PRAGMA table_info(vendor_work_entries)").fetchall()]
    for required in (
        "sheet_id",
        "vendor_name",
        "business_date",
        "entry_order",
        "pre_entry_requirement",
        "requirement_status",
        "requirement_confirmed_by",
        "requirement_confirmed_at",
    ):
        if required not in work_columns:
            raise SystemExit("vendor_work_entries should remain intact after vendor_contacts migration")

    formal_tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "formal_approvals" not in formal_tables:
        raise SystemExit("formal_approvals table should exist after migration")
    formal_columns = [col["name"] for col in conn.execute("PRAGMA table_info(formal_approvals)").fetchall()]
    for required in (
        "entry_id",
        "sheet_id",
        "action",
        "approval_status",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    ):
        if required not in formal_columns:
            raise SystemExit("formal_approvals should include the persistent schema baseline columns")
    formal_indexes = conn.execute("PRAGMA index_list(formal_approvals)").fetchall()
    unique_entry_action_present = False
    for index_row in formal_indexes:
        if index_row["unique"]:
            cols = tuple(
                info_row["name"] for info_row in conn.execute(f"PRAGMA index_info({index_row['name']})").fetchall()
            )
            if cols == ("entry_id", "action"):
                unique_entry_action_present = True
                break
    if not unique_entry_action_present:
        raise SystemExit("formal_approvals should enforce UNIQUE(entry_id, action) after migration")

print("crew schema migration smoke PASS")
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
    if "crew schema migration smoke PASS" not in result.stdout:
        raise AssertionError("crew schema migration smoke subprocess did not report PASS.")


def run_scheduler_schema_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    legacy_db_path = app_db_path.with_name(f"{app_db_path.stem}-legacy{app_db_path.suffix}")
    if legacy_db_path.exists():
        legacy_db_path.unlink()
    create_sample_sqlite(legacy_db_path)
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

bootstrap_db_path, legacy_db_path, root_dir = sys.argv[1:4]

def load_module(db_path: str):
    os.environ["APP_DB_PATH"] = db_path
    spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def assert_scheduler_schema(conn: sqlite3.Connection, *, label: str):
    conn.row_factory = sqlite3.Row
    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "scheduling_entries" not in tables:
        raise SystemExit(f"{label}: scheduling_entries table should exist")

    scheduling_columns = [row["name"] for row in conn.execute("PRAGMA table_info(scheduling_entries)").fetchall()]
    for required in (
        "id",
        "entry_id",
        "sheet_id",
        "action",
        "schedule_status",
        "scheduled_date",
        "scheduled_time",
        "scheduled_by",
        "scheduled_at",
        "created_at",
        "updated_at",
    ):
        if required not in scheduling_columns:
            raise SystemExit(f"{label}: scheduling_entries missing required column: {required}")

    scheduling_indexes = conn.execute("PRAGMA index_list(scheduling_entries)").fetchall()
    scheduling_index_names = {row["name"] for row in scheduling_indexes}
    for required in (
        "idx_scheduling_entries_entry_action_unique",
        "idx_scheduling_entries_sheet_id",
        "idx_scheduling_entries_scheduled_date",
    ):
        if required not in scheduling_index_names:
            raise SystemExit(f"{label}: scheduling_entries missing expected index: {required}")

    unique_entry_action_present = False
    for row in scheduling_indexes:
        if row["unique"]:
            cols = tuple(index_row["name"] for index_row in conn.execute(f"PRAGMA index_info({row['name']})").fetchall())
            if cols == ("entry_id", "action"):
                unique_entry_action_present = True
                break
    if not unique_entry_action_present:
        raise SystemExit(f"{label}: scheduling_entries should enforce UNIQUE(entry_id, action)")

    row_count = int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0])
    if row_count != 0:
        raise SystemExit(f"{label}: scheduling_entries row count should remain 0 in schema baseline")

bootstrap_module = load_module(bootstrap_db_path)
with bootstrap_module.db() as conn:
    assert_scheduler_schema(conn, label="bootstrap")

legacy_module = load_module(legacy_db_path)
with legacy_module.db() as conn:
    assert_scheduler_schema(conn, label="migration")

print("scheduler schema smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(app_db_path),
            str(legacy_db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "scheduler schema smoke PASS" not in result.stdout:
        raise AssertionError("scheduler schema smoke subprocess did not report PASS.")


def run_crew_readonly_render_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import re
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
js_text = (Path(root_dir) / "static" / "app.js").read_text(encoding="utf-8")

if '<section class="crew-form-shell"' not in template_text:
    raise SystemExit("sheet.html should render a .crew-form-shell section")
if 'data-mode="readonly"' not in template_text:
    raise SystemExit("crew readonly shell should expose data-mode=readonly")
if 'data-testid="crew-work-hub-shell"' not in template_text:
    raise SystemExit("sheet.html should render a crew work hub shell")
if 'data-testid="crew-management-insight-summary"' not in template_text:
    raise SystemExit("sheet.html should render a management insight summary container")
if 'data-testid="crew-work-hub-cards"' not in template_text:
    raise SystemExit("sheet.html should render a crew work hub cards container")
if not re.search(r'<section class="table-shell">.*?</section>\\s*<section class="crew-form-shell"', template_text, re.S):
    raise SystemExit(".crew-form-shell should be a sibling after .table-shell, not nested inside it")

required_entities = (
    "crewFollowupsBtn",
    "crewDailySummaryBtn",
    "crewMissingBtn",
    "disabled",
    "&#24453;&#32879;&#32363;",
    "&#20170;&#26085;&#20986;&#24037;&#32113;&#35336;&#65288;8&#40670;30&#37325;&#32622;&#65289;",
    "&#26410;&#36914;&#22580;&#24037;&#29677;&#26597;&#35426;",
)
for snippet in required_entities:
    if snippet not in template_text:
        raise SystemExit(f"sheet.html missing readonly crew snippet: {snippet}")

if "/api/vendor-contact" in template_text or "/api/vendor-work-entry" in template_text:
    raise SystemExit("sheet.html readonly crew render should not contain crew POST endpoints")

for required in (
    "async function loadCrewForms",
    "async function confirmCrewWorkEntryRequirement",
    "async function approveCrewWorkEntryFormal",
    "function buildCrewRequirementMeta",
    "function buildCrewReadinessMeta",
    "function buildCrewSchedulingGateMeta",
    "function buildCrewWorkHubCardMeta",
    "function buildCrewManagementInsightMetricMeta",
    "function buildCrewManagementInsightNotes",
    "function renderCrewManagementInsightSummary",
    "function renderCrewWorkHubCards",
    "function buildCrewFormalApprovalIndicatorMeta",
    "function buildCrewFormalApproveMeta",
    "function renderCrewForms",
    "function renderCrewFormError",
    "function formatCrewDate",
    "function formatCrewDateTime",
    "async function loadCrewWorkHubSummary",
    "/api/work-hub-runtime?sheet_id=",
    "/api/dashboard?sheet_id=",
    "/api/scheduling?sheet_id=",
    "/api/crew-forms?sheet_id=",
    "/api/crew-work-entry-requirement-confirm",
    "/api/crew-work-entry/formal-approve",
    "const schedulingGateMeta = buildCrewSchedulingGateMeta(entry);",
    "const formalApprovalIndicatorMeta = buildCrewFormalApprovalIndicatorMeta(entry);",
    "const formalApproveMeta = buildCrewFormalApproveMeta(entry);",
    'setAttribute("data-testid", "crew-work-entry-pre-entry-requirement")',
    'setAttribute("data-testid", "crew-work-entry-requirement-status")',
    'setAttribute("data-testid", "crew-work-entry-readiness-indicator")',
    'setAttribute("data-testid", "crew-work-entry-scheduling-gate-indicator")',
    'setAttribute("data-testid", "crew-work-entry-formal-approval-indicator")',
    'setAttribute("data-testid", "crew-work-entry-formal-approve-slot")',
    'setAttribute("data-scheduling-gate-state", schedulingGateMeta.schedulingGateState)',
    'setAttribute("data-scheduling-gate-reason", schedulingGateMeta.schedulingGateReason)',
    'setAttribute("data-formal-approval-state", formalApprovalIndicatorMeta.formalApprovalState)',
    'setAttribute("data-formal-approval-status", formalApprovalIndicatorMeta.formalApprovalStatus)',
    "if (schedulingGateMeta.schedulingGateLabel) {",
    "row.appendChild(schedulingGateNode);",
    "row.appendChild(formalApprovalNode);",
    'data-testid="crew-work-entry-requirement-confirm-action"',
    'data-testid="crew-work-entry-formal-approve-action"',
    'data-testid="crew-work-entry-formal-approve-feedback"',
    'data-testid="crew-work-entry-formal-approved-by"',
    'data-testid="crew-work-entry-formal-approved-at"',
    'data-testid="${card.testId}"',
    'data-testid="crew-work-hub-card-value-${card.summaryKey}"',
    'const actionMarkup = isConfirmed',
    "尚未具備進場條件",
    "需求已確認",
    "無進場前需求",
    "排程提醒：進場前需求尚未確認",
    "可排程：進場前需求已確認",
    "可排程：無進場前需求",
    "正式核准：待核准",
    "正式核准：已完成",
    "\u6b63\u5f0f\u6838\u51c6",
    "\u5df2\u5b8c\u6210\u6b63\u5f0f\u6838\u51c6",
    "\u7121\u6cd5\u5b8c\u6210\u6b63\u5f0f\u6838\u51c6\uff1a\u9032\u5834\u524d\u9700\u6c42\u5c1a\u672a\u78ba\u8a8d",
    "Blocked",
    "可排程",
    "待正式核准",
    "待確認需求",
    "今日進場",
    "blocked_count",
    "schedulable_count",
    "pending_approval_count",
    "pending_requirement_count",
    "today_entry_count",
    "await loadCrewForms(sheetId);",
):
    if required not in js_text:
        raise SystemExit(f"app.js missing readonly crew helper: {required}")

for readiness_required in (
    'setAttribute("data-readiness-state", readinessMeta.readinessState)',
    'setAttribute("data-readiness-reason", readinessMeta.readinessReason)',
    "尚未具備進場條件",
    "需求已確認",
    "無進場前需求",
):
    if readiness_required not in js_text:
        raise SystemExit(f"app.js missing readiness indicator guardrail: {readiness_required}")

for scheduling_gate_required in (
    'setAttribute("data-scheduling-gate-state", schedulingGateMeta.schedulingGateState)',
    'setAttribute("data-scheduling-gate-reason", schedulingGateMeta.schedulingGateReason)',
    '<span class="crew-label">排程提醒</span>',
    'schedulingGateState === "warning" && schedulingGateReason === "requirement_pending"',
    'schedulingGateState === "allowed" && schedulingGateReason === "requirement_confirmed"',
    'schedulingGateState === "allowed" && schedulingGateReason === "no_requirement"',
    "排程提醒：進場前需求尚未確認",
    "可排程：進場前需求已確認",
    "可排程：無進場前需求",
):
    if scheduling_gate_required not in js_text:
        raise SystemExit(f"app.js missing scheduling gate indicator guardrail: {scheduling_gate_required}")

for formal_approve_required in (
    'const slot = button?.closest("[data-testid=\\\'crew-work-entry-formal-approve-slot\\\']");',
    'const feedback = slot?.querySelector("[data-testid=\\\'crew-work-entry-formal-approve-feedback\\\']");',
    'button.textContent = "\\u6838\\u51c6\\u4e2d...";',
    'action: "crew_formal_approve_entry"',
    'if (data?.error?.code === "entry_not_ready") {',
    'setCrewFormalApproveFeedback(button, "\\u7121\\u6cd5\\u5b8c\\u6210\\u6b63\\u5f0f\\u6838\\u51c6\\uff1a\\u9032\\u5834\\u524d\\u9700\\u6c42\\u5c1a\\u672a\\u78ba\\u8a8d", "blocked");',
    'setCrewFormalApproveFeedback(button, "\\u5df2\\u5b8c\\u6210\\u6b63\\u5f0f\\u6838\\u51c6", "success");',
    'const crewFormalApprove = event.target.closest("[data-testid=\\\'crew-work-entry-formal-approve-action\\\']");',
    "if (crewFormalApprove) return approveCrewWorkEntryFormal(crewFormalApprove);",
):
    if formal_approve_required not in js_text:
        raise SystemExit(f"app.js missing formal approve UI guardrail: {formal_approve_required}")

for formal_approval_indicator_required in (
    'setAttribute("data-testid", "crew-work-entry-formal-approval-indicator")',
    'setAttribute("data-formal-approval-state", formalApprovalIndicatorMeta.formalApprovalState)',
    'setAttribute("data-formal-approval-status", formalApprovalIndicatorMeta.formalApprovalStatus)',
    'data-testid="crew-work-entry-formal-approved-by"',
    'data-testid="crew-work-entry-formal-approved-at"',
    "正式核准：待核准",
    "正式核准：已完成",
    "核准資訊",
):
    if formal_approval_indicator_required not in js_text:
        raise SystemExit(f"app.js missing formal approval indicator guardrail: {formal_approval_indicator_required}")

for dashboard_required in (
    'data-testid="crew-work-hub-cards"',
    "crew-work-hub-card-blocked",
    "crew-work-hub-card-schedulable",
    "crew-work-hub-card-scheduled",
    "crew-work-hub-card-pending-approval",
    "crew-work-hub-card-pending-requirement",
    "crew-work-hub-card-today-entry",
    "loadCrewWorkHubSummary(crewFormShell.dataset.sheetId);",
):
    if dashboard_required not in js_text and dashboard_required not in template_text:
        raise SystemExit(f"crew work hub dashboard baseline missing guardrail: {dashboard_required}")

for forbidden in (
    'fetch("/api/vendor-contact"',
    "fetch('/api/vendor-contact'",
    'fetch("/api/vendor-work-entry"',
    "fetch('/api/vendor-work-entry'",
):
    if forbidden in js_text:
        raise SystemExit(f"readonly crew frontend should not send crew POST requests: {forbidden}")

if 'return `${match[1]}年${match[2]}月${match[3]}日`;' not in js_text:
    raise SystemExit("formatCrewDate should render YYYY年MM月DD日")
if 'return match[2] ? `${formattedDate} ${match[2]}` : formattedDate;' not in js_text:
    raise SystemExit("formatCrewDateTime should append HH:MM when present")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect for crew readonly smoke")

    sheet_response = client.get("/sheet")
    if sheet_response.status_code != 200:
        raise SystemExit("/sheet GET should render successfully with crew readonly shell")
    html = sheet_response.get_data(as_text=True)
    for snippet in (
        'class="crew-form-shell"',
        'data-mode="readonly"',
        'data-testid="crew-work-hub-shell"',
        'data-testid="crew-work-hub-cards"',
        'id="crewVendorList"',
    ):
        if snippet not in html:
            raise SystemExit(f"rendered /sheet missing crew readonly markup: {snippet}")

    crew_forms_response = client.get("/api/crew-forms?sheet_id=1")
    if crew_forms_response.status_code != 200:
        raise SystemExit("/api/crew-forms?sheet_id=1 should remain healthy for readonly crew render")

print("crew readonly render smoke PASS")
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
    if "crew readonly render smoke PASS" not in result.stdout:
        raise AssertionError("crew readonly render smoke subprocess did not report PASS.")


def run_work_hub_quick_action_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
js_text = (Path(root_dir) / "static" / "app.js").read_text(encoding="utf-8")

required_js = (
    "function findCrewWorkHubTarget",
    "function scrollCrewWorkHubToTarget",
    'data-work-hub-action="${card.action}"',
    'row.setAttribute("data-work-hub-entry", "today-entry")',
    'row.setAttribute("data-work-hub-blocked", "true")',
    'row.setAttribute("data-work-hub-scheduled", "true")',
    'row.setAttribute("data-work-hub-pending-approval", "true")',
    'row.setAttribute("data-work-hub-pending-requirement", "true")',
    "function activateCrewReadonlyDrilldown(control) {",
    'if (control.matches("[data-work-hub-action]")) {',
    "scrollCrewWorkHubToTarget(control.dataset.workHubAction);",
    'const focusSectionTarget = findCrewWorkHubFocusSectionTarget(action);',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-blocked=\\\'true\\\']") || crewVendorList;',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-scheduled=\\\'true\\\']") || crewVendorList;',
    'return crewVendorList.querySelector("[data-work-hub-pending-approval=\\\'true\\\']") || crewVendorList;',
    'return crewVendorList.querySelector("[data-work-hub-pending-requirement=\\\'true\\\']") || crewVendorList;',
    'target.scrollIntoView({ behavior: "smooth", block: "start" });',
)
for snippet in required_js:
    if snippet not in js_text:
        raise SystemExit(f"work hub quick action missing js guardrail: {snippet}")

if 'data-testid="crew-work-hub-target-today-entries"' not in template_text:
    raise SystemExit("work hub quick action should expose today entries target")

quick_action_helper = js_text.split("function findCrewWorkHubTarget", 1)[1].split("function buildCrewRequirementMeta", 1)[0]
if "fetch(" in quick_action_helper:
    raise SystemExit("work hub quick action helper must stay read-only and must not fetch")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect for work hub quick action smoke")

    sheet_response = client.get("/sheet")
    if sheet_response.status_code != 200:
        raise SystemExit("/sheet GET should render successfully for work hub quick action smoke")
    html = sheet_response.get_data(as_text=True)
    for snippet in (
        'data-testid="crew-work-hub-shell"',
        'data-testid="crew-work-hub-cards"',
        'data-testid="crew-work-hub-target-today-entries"',
    ):
        if snippet not in html:
            raise SystemExit(f"rendered /sheet missing work hub quick action target: {snippet}")

print("work hub quick action smoke PASS")
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
    if "work hub quick action smoke PASS" not in result.stdout:
        raise AssertionError("work hub quick action smoke subprocess did not report PASS.")


def run_work_hub_scheduling_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
js_text = (Path(root_dir) / "static" / "app.js").read_text(encoding="utf-8")

required_js = (
    "/api/management-read-model?sheet_id=",
    "/api/work-hub-runtime?sheet_id=",
    "/api/dashboard?sheet_id=",
    "/api/scheduling?sheet_id=",
    "const managementReadModelResponse = await fetch(",
    "const managementReadModelData = await managementReadModelResponse.json().catch(() => ({}));",
    "if (!managementReadModelResponse.ok || !managementReadModelData?.management_summary) {",
    "const managementSummary = managementReadModelData.management_summary;",
    "const workHubRuntimeResponse = await fetch(",
    "const workHubRuntimeData = await workHubRuntimeResponse.json().catch(() => ({}));",
    "if (!workHubRuntimeResponse.ok || !workHubRuntimeData?.work_hub?.summary) {",
    "Promise.allSettled([",
    'testId: "crew-work-hub-card-blocked"',
    'testId: "crew-work-hub-card-schedulable"',
    'testId: "crew-work-hub-card-scheduled"',
    'title: "Blocked"',
    'title: "可排程"',
    'title: "已正式排程"',
    'value: summary.blocked_count ?? 0',
    'value: summary.schedulable_count ?? 0',
    'value: summary.scheduled_count ?? 0',
    'summaryKey: "blocked_count"',
    'summaryKey: "schedulable_count"',
    'summaryKey: "scheduled_count"',
    'blocked_count: managementSummary.blocked_count ?? 0,',
    'schedulable_count: managementSummary.schedulable_count ?? 0,',
    'scheduled_count: managementSummary.scheduled_count ?? 0,',
    'pending_approval_count: managementSummary.pending_approval_count ?? 0,',
    'pending_requirement_count: managementSummary.pending_requirement_count ?? 0,',
    'today_entry_count: managementSummary.today_entry_count ?? 0,',
    'today_schedule_count: managementSummary.today_schedule_count ?? 0,',
    'renderCrewManagementInsightSummary({',
    'drilldown_refs: managementReadModelData.drilldown_refs,',
    'summary.pending_approval_count = dashboardData.summary.pending_approval_count ?? 0;',
    'summary.pending_requirement_count = dashboardData.summary.pending_requirement_count ?? 0;',
    'summary.today_entry_count = dashboardData.summary.today_entry_count ?? 0;',
    'summary.scheduled_count = dashboardData.summary.scheduled_count ?? 0;',
    'summary.blocked_count = schedulingData.summary.blocked_count ?? 0;',
    'summary.schedulable_count = schedulingData.summary.schedulable_count ?? 0;',
    'schedulable_count: 0',
    'scheduled_count: 0',
    'crewScheduledEntryIds = new Set(',
    'const focusSectionTarget = findCrewWorkHubFocusSectionTarget(action);',
    'row.setAttribute("data-work-hub-schedulable", "true");',
    'row.setAttribute("data-work-hub-scheduled", "true");',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-schedulable=\\\'true\\\']") || crewVendorList;',
)
for snippet in required_js:
    if snippet not in js_text:
        raise SystemExit(f"work hub scheduling missing js guardrail: {snippet}")

if 'data-testid="crew-work-hub-cards"' not in template_text:
    raise SystemExit("work hub scheduling baseline should keep work hub mount container")

if "fetch(" in js_text.split("function findCrewWorkHubTarget", 1)[1].split("function buildCrewRequirementMeta", 1)[0]:
    raise SystemExit("work hub scroll helpers must remain read-only and fetch-free")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect for work hub scheduling smoke")

    sheet_response = client.get("/sheet")
    if sheet_response.status_code != 200:
        raise SystemExit("/sheet GET should render successfully for work hub scheduling smoke")
    html = sheet_response.get_data(as_text=True)
    for snippet in (
        'data-testid="crew-work-hub-shell"',
        'data-testid="crew-work-hub-cards"',
    ):
        if snippet not in html:
            raise SystemExit(f"rendered /sheet missing work hub scheduling shell: {snippet}")

print("work hub scheduling smoke PASS")
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
    if "work hub scheduling smoke PASS" not in result.stdout:
        raise AssertionError("work hub scheduling smoke subprocess did not report PASS.")


def run_work_hub_scheduled_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
js_text = (Path(root_dir) / "static" / "app.js").read_text(encoding="utf-8")

required_js = (
    'testId: "crew-work-hub-card-scheduled"',
    'title: "已正式排程"',
    'value: summary.scheduled_count ?? 0',
    'summaryKey: "scheduled_count"',
    "/api/management-read-model?sheet_id=",
    "/api/work-hub-runtime?sheet_id=",
    "const managementSummary = managementReadModelData.management_summary;",
    'scheduled_count: managementSummary.scheduled_count ?? 0,',
    'Array.isArray(workHubRuntimeData?.work_hub?.scheduled_entries)',
    'workHubRuntimeData.work_hub.scheduled_entries.map((entry) => String(entry?.id ?? "").trim()).filter(Boolean)',
    'summary.scheduled_count = dashboardData.summary.scheduled_count ?? 0;',
    'crewScheduledEntryIds = new Set(',
    'const focusSectionTarget = findCrewWorkHubFocusSectionTarget(action);',
    'row.setAttribute("data-work-hub-scheduled", "true");',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-scheduled=\\\'true\\\']") || crewVendorList;',
    'data-entry-id="${escapeHtml(entry.id ?? "")}"',
)
for snippet in required_js:
    if snippet not in js_text:
        raise SystemExit(f"work hub scheduled ui missing js guardrail: {snippet}")

quick_action_helper = js_text.split("function findCrewWorkHubTarget", 1)[1].split("function buildCrewRequirementMeta", 1)[0]
if "fetch(" in quick_action_helper:
    raise SystemExit("work hub scheduled quick action must stay read-only and fetch-free")

if 'data-testid="crew-work-hub-target-today-entries"' not in template_text:
    raise SystemExit("work hub scheduled baseline should keep readonly list scroll target")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect for work hub scheduled smoke")

    sheet_response = client.get("/sheet")
    if sheet_response.status_code != 200:
        raise SystemExit("/sheet GET should render successfully for work hub scheduled smoke")
    html = sheet_response.get_data(as_text=True)
    for snippet in (
        'data-testid="crew-work-hub-shell"',
        'data-testid="crew-work-hub-cards"',
        'data-testid="crew-work-hub-target-today-entries"',
    ):
        if snippet not in html:
            raise SystemExit(f"rendered /sheet missing work hub scheduled shell: {snippet}")

print("work hub scheduled smoke PASS")
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
    if "work hub scheduled smoke PASS" not in result.stdout:
        raise AssertionError("work hub scheduled smoke subprocess did not report PASS.")


def run_work_hub_scheduled_guardrail_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
js_text = (Path(root_dir) / "static" / "app.js").read_text(encoding="utf-8")

required_js = (
    'testId: "crew-work-hub-card-scheduled"',
    'title: "已正式排程"',
    'value: summary.scheduled_count ?? 0',
    'summaryKey: "scheduled_count"',
    'summary.scheduled_count = dashboardData.summary.scheduled_count ?? 0;',
    'row.setAttribute("data-work-hub-scheduled", "true");',
    'const focusSectionTarget = findCrewWorkHubFocusSectionTarget(action);',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-scheduled=\\\'true\\\']") || crewVendorList;',
    'data-entry-id="${escapeHtml(entry.id ?? "")}"',
    "function activateCrewReadonlyDrilldown(control) {",
    'if (control.matches("[data-work-hub-action]")) {',
    'target.scrollIntoView({ behavior: "smooth", block: "start" });',
)
for snippet in required_js:
    if snippet not in js_text:
        raise SystemExit(f"work hub scheduled guardrail missing js snippet: {snippet}")

quick_action_helper = js_text.split("function findCrewWorkHubTarget", 1)[1].split("function buildCrewRequirementMeta", 1)[0]
if "fetch(" in quick_action_helper:
    raise SystemExit("work hub scheduled guardrail should keep quick action fetch-free")
if "POST" in quick_action_helper:
    raise SystemExit("work hub scheduled guardrail should keep quick action write-free")

if 'data-testid="crew-work-hub-target-today-entries"' not in template_text:
    raise SystemExit("work hub scheduled guardrail should keep readonly list scroll target")

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for work hub scheduled guardrail smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for work hub scheduled guardrail smoke")
    sheet_id = int(sheet_row["id"])
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("work_hub_guard_member", "work_hub_guard_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("work_hub_guard_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, requirement_status,
                work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Guardrail", business_date, "2000-01-01 09:00", 2, 0, "Scheduled Work", "", "pending", 0, 0),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, "work_hub_guard_member"),
    )
    conn.execute(
        '''
        INSERT INTO scheduling_entries (
            entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time,
            scheduled_by, scheduled_at, created_at, updated_at
        ) VALUES (?, ?, 'schedule_entry', 'scheduled', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, business_date, "09:30", "work_hub_guard_member"),
    )
    conn.commit()

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
            "scheduling_entries": int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0]),
        }

client = module.app.test_client()
with client.session_transaction() as session:
    session.clear()
    session["user_id"] = int(member_id)
    session["username"] = "work_hub_guard_member"
    session["display_name"] = "work_hub_guard_member"
    session["role"] = "member"
    session["current_site_id"] = int(default_site_id)
    session["current_site_name"] = str(default_site_name)
    session["site_selection_required"] = False

before = fetch_db_snapshot()
response = client.get(f"/api/dashboard?sheet_id={sheet_id}")
if response.status_code != 200:
    raise SystemExit("work hub scheduled guardrail should allow dashboard read")
payload = response.get_json()
if set(payload.keys()) != {
    "summary",
    "blocked_items",
    "pending_approvals",
    "pending_requirements",
    "today_entries",
    "scheduled_entries",
    "today_schedule",
    "quick_actions",
}:
    raise SystemExit("work hub scheduled guardrail should freeze dashboard top-level contract")
summary = payload["summary"]
if set(summary.keys()) != {
    "blocked_count",
    "pending_approval_count",
    "pending_requirement_count",
    "today_entry_count",
    "approved_today_count",
    "scheduled_count",
    "today_schedule_count",
}:
    raise SystemExit("work hub scheduled guardrail should freeze dashboard summary contract")
if summary["scheduled_count"] != 1 or summary["today_schedule_count"] != 1:
    raise SystemExit("work hub scheduled guardrail should freeze scheduled summary counts")
if len(payload["scheduled_entries"]) != 1 or int(payload["scheduled_entries"][0]["id"]) != int(approved_entry_id):
    raise SystemExit("work hub scheduled guardrail should freeze scheduled_entries membership")
if len(payload["today_schedule"]) != 1 or int(payload["today_schedule"][0]["id"]) != int(approved_entry_id):
    raise SystemExit("work hub scheduled guardrail should freeze today_schedule membership")
if fetch_db_snapshot() != before:
    raise SystemExit("work hub scheduled guardrail should keep dashboard aggregation read-only")

sheet_response = client.get("/sheet")
if sheet_response.status_code != 200:
    raise SystemExit("work hub scheduled guardrail should render /sheet")
html = sheet_response.get_data(as_text=True)
for snippet in (
    'data-testid="crew-work-hub-shell"',
    'data-testid="crew-work-hub-cards"',
    'data-testid="crew-work-hub-target-today-entries"',
):
    if snippet not in html:
        raise SystemExit(f"work hub scheduled guardrail should keep readonly shell marker: {snippet}")

print("work hub scheduled guardrail smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "work hub scheduled guardrail smoke PASS" not in result.stdout:
        raise AssertionError("work hub scheduled guardrail smoke subprocess did not report PASS.")


def run_work_hub_runtime_helper_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    sheet_row = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for work hub runtime helper smoke")
    sheet_id = int(sheet_row["id"])
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Helper", business_date, "2000-01-01 09:00", 2, 0, "Blocked Work", "Need permit", 0, 0),
        ).fetchone()["id"]
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Helper", business_date, "2000-01-01 10:00", 1, 0, "Approved Work", "", 0, 1),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, "helper_member"),
    )
    conn.execute(
        '''
        INSERT INTO scheduling_entries (
            entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time,
            scheduled_by, scheduled_at, created_at, updated_at
        ) VALUES (?, ?, 'schedule_entry', 'scheduled', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, business_date, "09:30", "helper_member"),
    )
    conn.commit()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    dashboard_payload = module.build_dashboard_payload(conn, sheet_id=sheet_id, business_date=business_date)
    scheduling_payload = module.build_scheduling_payload(conn, sheet_id=sheet_id, business_date=business_date)
    helper_payload = module.build_work_hub_runtime_payload(conn, sheet_id=sheet_id, business_date=business_date)

if set(helper_payload.keys()) != {"sheet_id", "business_date", "dashboard", "scheduling", "work_hub"}:
    raise SystemExit("work hub runtime helper should keep the expected top-level shape")
if helper_payload["sheet_id"] != sheet_id or helper_payload["business_date"] != business_date:
    raise SystemExit("work hub runtime helper should preserve sheet_id and business_date context")
if helper_payload["dashboard"] != dashboard_payload:
    raise SystemExit("work hub runtime helper should reuse dashboard payload without contract drift")
if helper_payload["scheduling"] != scheduling_payload:
    raise SystemExit("work hub runtime helper should reuse scheduling payload without contract drift")

work_hub = helper_payload["work_hub"]
if set(work_hub.keys()) != {
    "summary",
    "blocked_entries",
    "schedulable_entries",
    "today_entries",
    "scheduled_entries",
    "today_schedule",
}:
    raise SystemExit("work hub runtime helper should keep the expected internal work_hub shape")
if set(work_hub["summary"].keys()) != {
    "blocked_count",
    "schedulable_count",
    "pending_approval_count",
    "pending_requirement_count",
    "today_entry_count",
    "scheduled_count",
    "today_schedule_count",
}:
    raise SystemExit("work hub runtime helper should expose the expected summary shape")
if work_hub["summary"]["blocked_count"] != scheduling_payload["summary"]["blocked_count"]:
    raise SystemExit("work hub runtime helper should source blocked_count from scheduling summary")
if work_hub["summary"]["schedulable_count"] != scheduling_payload["summary"]["schedulable_count"]:
    raise SystemExit("work hub runtime helper should source schedulable_count from scheduling summary")
if work_hub["summary"]["scheduled_count"] != dashboard_payload["summary"]["scheduled_count"]:
    raise SystemExit("work hub runtime helper should source scheduled_count from dashboard summary")
if work_hub["summary"]["today_schedule_count"] != dashboard_payload["summary"]["today_schedule_count"]:
    raise SystemExit("work hub runtime helper should source today_schedule_count from dashboard summary")
if {int(entry["id"]) for entry in work_hub["blocked_entries"]} != {int(entry["id"]) for entry in scheduling_payload["blocked_entries"]}:
    raise SystemExit("work hub runtime helper should reuse scheduling blocked_entries membership")
if {int(entry["id"]) for entry in work_hub["schedulable_entries"]} != {int(entry["id"]) for entry in scheduling_payload["schedulable_entries"]}:
    raise SystemExit("work hub runtime helper should reuse scheduling schedulable_entries membership")
if {int(entry["id"]) for entry in work_hub["scheduled_entries"]} != {int(entry["id"]) for entry in dashboard_payload["scheduled_entries"]}:
    raise SystemExit("work hub runtime helper should reuse dashboard scheduled_entries membership")
if {int(entry["id"]) for entry in work_hub["today_schedule"]} != {int(entry["id"]) for entry in dashboard_payload["today_schedule"]}:
    raise SystemExit("work hub runtime helper should reuse dashboard today_schedule membership")
if blocked_entry_id not in {int(entry["id"]) for entry in work_hub["blocked_entries"]}:
    raise SystemExit("work hub runtime helper should include the blocked entry in blocked_entries")
if approved_entry_id not in {int(entry["id"]) for entry in work_hub["scheduled_entries"]}:
    raise SystemExit("work hub runtime helper should include the scheduled entry in scheduled_entries")

print("work hub runtime helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "work hub runtime helper smoke PASS" not in result.stdout:
        raise AssertionError("work hub runtime helper smoke subprocess did not report PASS.")


def run_management_read_model_helper_smoke(db_path: Path) -> None:
    script = """
import inspect
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    sheet_row = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for management read model helper smoke")
    sheet_id = int(sheet_row["id"])
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Management Helper", business_date, "2000-01-01 09:00", 2, 0, "Blocked Work", "Need permit", 0, 0),
        ).fetchone()["id"]
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Management Helper", business_date, "2000-01-01 10:00", 1, 0, "Approved Work", "", 0, 1),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, "management_helper_member"),
    )
    conn.execute(
        '''
        INSERT INTO scheduling_entries (
            entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time,
            scheduled_by, scheduled_at, created_at, updated_at
        ) VALUES (?, ?, 'schedule_entry', 'scheduled', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, business_date, "09:45", "management_helper_member"),
    )
    conn.commit()
    before_counts = {
        "vendor_work_entries": conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0],
        "formal_approvals": conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0],
        "scheduling_entries": conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0],
    }

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    dashboard_payload = module.build_dashboard_payload(conn, sheet_id=sheet_id, business_date=business_date)
    scheduling_payload = module.build_scheduling_payload(conn, sheet_id=sheet_id, business_date=business_date)
    helper_payload = module.build_management_read_model_payload(conn, sheet_id=sheet_id, business_date=business_date)
    helper_source = inspect.getsource(module.build_management_read_model_payload)
    after_counts = {
        "vendor_work_entries": conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0],
        "formal_approvals": conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0],
        "scheduling_entries": conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0],
    }

if before_counts != after_counts:
    raise SystemExit("management read model helper prototype should stay read-only and preserve DB counts")
if "build_dashboard_payload(" not in helper_source or "build_scheduling_payload(" not in helper_source:
    raise SystemExit("management read model helper should depend on dashboard and scheduling payload helpers")
if "build_work_hub_runtime_payload(" in helper_source:
    raise SystemExit("management read model helper should not depend on work hub runtime payload")
if any(term in helper_source for term in ('label', 'title', 'priority', 'ranking', 'prediction', 'format', 'html', 'aria')):
    raise SystemExit("management read model helper should stay free of presentation, ranking, and prediction semantics")
if set(helper_payload.keys()) != {
    "management_summary",
    "scheduling_overview",
    "approval_overview",
    "requirement_overview",
    "operational_risk_overview",
    "drilldown_refs",
}:
    raise SystemExit("management read model helper should expose the expected prototype top-level shape")
if helper_payload["management_summary"] != {
    "today_entry_count": dashboard_payload["summary"]["today_entry_count"],
    "scheduled_count": dashboard_payload["summary"]["scheduled_count"],
    "today_schedule_count": dashboard_payload["summary"]["today_schedule_count"],
    "schedulable_count": scheduling_payload["summary"]["schedulable_count"],
    "blocked_count": scheduling_payload["summary"]["blocked_count"],
    "pending_approval_count": dashboard_payload["summary"]["pending_approval_count"],
    "pending_requirement_count": dashboard_payload["summary"]["pending_requirement_count"],
}:
    raise SystemExit("management_summary should only project existing dashboard and scheduling summary counts")

scheduling_overview = helper_payload["scheduling_overview"]
if scheduling_overview["schedulable_count"] != scheduling_payload["summary"]["schedulable_count"]:
    raise SystemExit("scheduling_overview should source schedulable_count from scheduling summary")
if scheduling_overview["blocked_count"] != scheduling_payload["summary"]["blocked_count"]:
    raise SystemExit("scheduling_overview should source blocked_count from scheduling summary")
if scheduling_overview["scheduled_count"] != dashboard_payload["summary"]["scheduled_count"]:
    raise SystemExit("scheduling_overview should source scheduled_count from dashboard summary")
if scheduling_overview["today_schedule_count"] != dashboard_payload["summary"]["today_schedule_count"]:
    raise SystemExit("scheduling_overview should source today_schedule_count from dashboard summary")
if set(scheduling_overview["schedulable_entry_ids"]) != {int(entry["id"]) for entry in scheduling_payload["schedulable_entries"]}:
    raise SystemExit("scheduling_overview should reuse scheduling schedulable entry membership")
if set(scheduling_overview["scheduled_entry_ids"]) != {int(entry["id"]) for entry in dashboard_payload["scheduled_entries"]}:
    raise SystemExit("scheduling_overview should reuse dashboard scheduled entry membership")

approval_overview = helper_payload["approval_overview"]
if approval_overview["pending_approval_count"] != dashboard_payload["summary"]["pending_approval_count"]:
    raise SystemExit("approval_overview should source pending_approval_count from dashboard summary")
if approval_overview["approved_today_count"] != dashboard_payload["summary"]["approved_today_count"]:
    raise SystemExit("approval_overview should source approved_today_count from dashboard summary")
if set(approval_overview["pending_approval_entry_ids"]) != {int(entry["id"]) for entry in dashboard_payload["pending_approvals"]}:
    raise SystemExit("approval_overview should reuse dashboard pending_approvals membership")

requirement_overview = helper_payload["requirement_overview"]
if requirement_overview["pending_requirement_count"] != dashboard_payload["summary"]["pending_requirement_count"]:
    raise SystemExit("requirement_overview should source pending_requirement_count from dashboard summary")
if set(requirement_overview["pending_requirement_entry_ids"]) != {int(entry["id"]) for entry in dashboard_payload["pending_requirements"]}:
    raise SystemExit("requirement_overview should reuse dashboard pending_requirements membership")

operational_risk_overview = helper_payload["operational_risk_overview"]
if operational_risk_overview["blocked_count"] != scheduling_payload["summary"]["blocked_count"]:
    raise SystemExit("operational_risk_overview should source blocked_count from scheduling summary")
if operational_risk_overview["pending_approval_count"] != dashboard_payload["summary"]["pending_approval_count"]:
    raise SystemExit("operational_risk_overview should source pending_approval_count from dashboard summary")
if operational_risk_overview["pending_requirement_count"] != dashboard_payload["summary"]["pending_requirement_count"]:
    raise SystemExit("operational_risk_overview should source pending_requirement_count from dashboard summary")
if any(key in operational_risk_overview for key in ("priority", "rank", "ranking", "top_risk", "primary_risk")):
    raise SystemExit("operational_risk_overview should not introduce priority or ranking semantics")

drilldown_refs = helper_payload["drilldown_refs"]
expected_targets = {
    "blocked": "blocked",
    "schedulable": "schedulable",
    "scheduled": "scheduled",
    "pending_approval": "pending-approval",
    "pending_requirement": "pending-requirement",
    "today_entries": "today-entries",
    "today_schedule": "today-schedule",
}
if set(drilldown_refs.keys()) != set(expected_targets.keys()):
    raise SystemExit("drilldown_refs should expose only the expected read-side references")
for key, target in expected_targets.items():
    if set(drilldown_refs[key].keys()) != {"target", "count"}:
        raise SystemExit("drilldown_refs should stay as read-side target/count references only")
    if drilldown_refs[key]["target"] != target:
        raise SystemExit("drilldown_refs should keep the expected static drilldown target mapping")

if blocked_entry_id not in operational_risk_overview["blocked_entry_ids"]:
    raise SystemExit("operational_risk_overview should include the blocked entry as a read-side risk reference")
if approved_entry_id not in scheduling_overview["scheduled_entry_ids"]:
    raise SystemExit("scheduling_overview should include the scheduled entry as a read-side reference")

print("management read model helper smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "management read model helper smoke PASS" not in result.stdout:
        raise AssertionError("management read model helper smoke subprocess did not report PASS.")


def run_management_read_model_api_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site is None:
        raise SystemExit("expected a default site for management read model api smoke")
    default_site_id = int(default_site["id"])
    default_site_name = str(default_site["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for management read model api smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__management_read_model_site_b__", "management-read-model-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            '''
            INSERT INTO sheets (name, sort_order, created_at, site_id)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            RETURNING id
            ''',
            ("Management Read Model Sheet B", 2, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        '''
        INSERT INTO users (username, display_name, password_hash, role)
        VALUES (?, ?, ?, ?)
        ''',
        ("management_read_model_member", "management_read_model_member", member_password_hash, "member"),
    )
    member_id = int(
        conn.execute("SELECT id FROM users WHERE username = ?", ("management_read_model_member",)).fetchone()["id"]
    )
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("management_read_model_vendor", module.generate_password_hash("vendor-pass"), "Vendor Management Read Model", 1),
    )
    vendor_account_id = int(
        conn.execute(
            "SELECT id FROM vendor_accounts WHERE username = ?",
            ("management_read_model_vendor",),
        ).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Management Read Model", business_date, "2000-01-01 09:00", 2, 0, "Blocked Work", "Need permit", 0, 0),
        ).fetchone()["id"]
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Management Read Model", business_date, "2000-01-01 10:00", 1, 0, "Approved Work", "", 0, 1),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, "management_read_model_member"),
    )
    conn.execute(
        '''
        INSERT INTO scheduling_entries (
            entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time,
            scheduled_by, scheduled_at, created_at, updated_at
        ) VALUES (?, ?, 'schedule_entry', 'scheduled', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, business_date, "09:45", "management_read_model_member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (secondary_sheet_id, "Vendor Management Read Model", business_date, "2000-01-01 11:00", 1, 0, "Cross Site Work", "", 0, 0),
    )
    conn.commit()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    expected_payload = module.build_management_read_model_payload(conn, sheet_id=sheet_id, business_date=business_date)

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
            "scheduling_entries": int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "management_read_model_member"
        session["display_name"] = "management_read_model_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

success_before = fetch_db_snapshot()
set_member_session()
success = client.get(f"/api/management-read-model?sheet_id={sheet_id}")
if success.status_code != 200:
    raise SystemExit("management read model success path should return 200")
payload = success.get_json()
if set(payload.keys()) != {
    "management_summary",
    "scheduling_overview",
    "approval_overview",
    "requirement_overview",
    "operational_risk_overview",
    "drilldown_refs",
}:
    raise SystemExit("management read model API should keep the exact top-level response contract")
if payload != expected_payload:
    raise SystemExit("management read model API should match build_management_read_model_payload output without contract drift")
if payload["management_summary"] != expected_payload["management_summary"]:
    raise SystemExit("management read model API should preserve management_summary without recomposition drift")
if payload["scheduling_overview"] != expected_payload["scheduling_overview"]:
    raise SystemExit("management read model API should preserve scheduling_overview without recomposition drift")
if blocked_entry_id not in payload["operational_risk_overview"]["blocked_entry_ids"]:
    raise SystemExit("management read model API should include blocked entry risk refs")
if approved_entry_id not in payload["scheduling_overview"]["scheduled_entry_ids"]:
    raise SystemExit("management read model API should include scheduled entry refs")
if fetch_db_snapshot() != success_before:
    raise SystemExit("management read model API must not modify DB state")

unauthenticated = module.app.test_client().get(f"/api/management-read-model?sheet_id={sheet_id}")
if unauthenticated.status_code != 403:
    raise SystemExit("unauthenticated protected management read model API should reject with 403")
unauthenticated_payload = unauthenticated.get_json()
if unauthenticated_payload.get("ok") is not False or unauthenticated_payload["error"]["code"] != "auth_required":
    raise SystemExit("unauthenticated management read model rejection should preserve auth_required")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "management_read_model_vendor"
    session["vendor_name"] = "Vendor Management Read Model"
vendor_response = client.get(f"/api/management-read-model?sheet_id={sheet_id}")
if vendor_response.status_code != 403:
    raise SystemExit("vendor session should be forbidden from management read model API")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor management read model rejection should preserve vendor_auth_forbidden")

set_member_session(with_current_site=False)
missing_site_before = fetch_db_snapshot()
missing_site = client.get(f"/api/management-read-model?sheet_id={sheet_id}")
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject management read model API with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site management read model rejection should preserve site_context_invalid")
if fetch_db_snapshot() != missing_site_before:
    raise SystemExit("missing current site management read model rejection must not modify DB state")

set_member_session()
cross_site_before = fetch_db_snapshot()
cross_site = client.get(f"/api/management-read-model?sheet_id={secondary_sheet_id}")
if cross_site.status_code != 403:
    raise SystemExit("cross-site management read model read should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "sheet_not_in_current_site":
    raise SystemExit("cross-site management read model rejection should preserve sheet_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("cross-site management read model rejection must not modify DB state")

print("management read model api smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "management read model api smoke PASS" not in result.stdout:
        raise AssertionError("management read model api smoke subprocess did not report PASS.")


def run_work_hub_runtime_api_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site is None:
        raise SystemExit("expected a default site for work hub runtime api smoke")
    default_site_id = int(default_site["id"])
    default_site_name = str(default_site["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for work hub runtime api smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__work_hub_runtime_site_b__", "work-hub-runtime-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            '''
            INSERT INTO sheets (name, sort_order, created_at, site_id)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            RETURNING id
            ''',
            ("Sheet B", 2, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        '''
        INSERT INTO users (username, display_name, password_hash, role)
        VALUES (?, ?, ?, ?)
        ''',
        ("work_hub_runtime_member", "work_hub_runtime_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("work_hub_runtime_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("work_hub_runtime_vendor", module.generate_password_hash("vendor-pass"), "Vendor Work Hub Runtime", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("work_hub_runtime_vendor",)).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Work Hub Runtime", business_date, "2000-01-01 09:00", 2, 0, "Blocked Work", "Need permit", 0, 0),
        ).fetchone()["id"]
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Work Hub Runtime", business_date, "2000-01-01 10:00", 1, 0, "Approved Work", "", 0, 1),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, "work_hub_runtime_member"),
    )
    conn.execute(
        '''
        INSERT INTO scheduling_entries (
            entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time,
            scheduled_by, scheduled_at, created_at, updated_at
        ) VALUES (?, ?, 'schedule_entry', 'scheduled', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, business_date, "09:30", "work_hub_runtime_member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (secondary_sheet_id, "Vendor Work Hub Runtime", business_date, "2000-01-01 11:00", 1, 0, "Cross Site Work", "", 0, 0),
    )
    conn.commit()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    expected_payload = module.build_work_hub_runtime_payload(conn, sheet_id=sheet_id, business_date=business_date)

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
            "scheduling_entries": int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "work_hub_runtime_member"
        session["display_name"] = "work_hub_runtime_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

success_before = fetch_db_snapshot()
set_member_session()
success = client.get(f"/api/work-hub-runtime?sheet_id={sheet_id}")
if success.status_code != 200:
    raise SystemExit("work hub runtime success path should return 200")
payload = success.get_json()
if set(payload.keys()) != {"sheet_id", "business_date", "dashboard", "scheduling", "work_hub"}:
    raise SystemExit("work hub runtime API should keep the exact top-level response contract")
if payload != expected_payload:
    raise SystemExit("work hub runtime API should match build_work_hub_runtime_payload output without contract drift")
if payload["dashboard"] != expected_payload["dashboard"]:
    raise SystemExit("work hub runtime API should source dashboard facts from dashboard payload")
if payload["scheduling"] != expected_payload["scheduling"]:
    raise SystemExit("work hub runtime API should source scheduling decisions from scheduling payload")
if payload["work_hub"]["scheduled_entries"] != expected_payload["work_hub"]["scheduled_entries"]:
    raise SystemExit("work hub runtime API should preserve dashboard-backed scheduled facts in work_hub")
if payload["work_hub"]["schedulable_entries"] != expected_payload["work_hub"]["schedulable_entries"]:
    raise SystemExit("work hub runtime API should preserve scheduling-backed decisions in work_hub")
if blocked_entry_id not in {int(entry["id"]) for entry in payload["work_hub"]["blocked_entries"]}:
    raise SystemExit("work hub runtime API should include the blocked entry in blocked_entries")
if approved_entry_id not in {int(entry["id"]) for entry in payload["work_hub"]["scheduled_entries"]}:
    raise SystemExit("work hub runtime API should include the scheduled fact entry in scheduled_entries")
if fetch_db_snapshot() != success_before:
    raise SystemExit("work hub runtime API must not modify DB state")

unauthenticated = module.app.test_client().get(f"/api/work-hub-runtime?sheet_id={sheet_id}")
if unauthenticated.status_code != 403:
    raise SystemExit("unauthenticated protected work hub runtime API should reject with 403")
unauthenticated_payload = unauthenticated.get_json()
if unauthenticated_payload.get("ok") is not False or unauthenticated_payload["error"]["code"] != "auth_required":
    raise SystemExit("unauthenticated work hub runtime rejection should preserve auth_required")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "work_hub_runtime_vendor"
    session["vendor_name"] = "Vendor Work Hub Runtime"
vendor_response = client.get(f"/api/work-hub-runtime?sheet_id={sheet_id}")
if vendor_response.status_code != 403:
    raise SystemExit("vendor session should be forbidden from work hub runtime API")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor work hub runtime rejection should preserve vendor_auth_forbidden")

set_member_session(with_current_site=False)
missing_site_before = fetch_db_snapshot()
missing_site = client.get(f"/api/work-hub-runtime?sheet_id={sheet_id}")
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject work hub runtime API with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site work hub runtime rejection should preserve site_context_invalid")
if fetch_db_snapshot() != missing_site_before:
    raise SystemExit("missing current site work hub runtime rejection must not modify DB state")

set_member_session()
cross_site_before = fetch_db_snapshot()
cross_site = client.get(f"/api/work-hub-runtime?sheet_id={secondary_sheet_id}")
if cross_site.status_code != 403:
    raise SystemExit("cross-site work hub runtime read should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "sheet_not_in_current_site":
    raise SystemExit("cross-site work hub runtime rejection should preserve sheet_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("cross-site work hub runtime rejection must not modify DB state")

print("work hub runtime api smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "work hub runtime api smoke PASS" not in result.stdout:
        raise AssertionError("work hub runtime api smoke subprocess did not report PASS.")


def run_work_hub_runtime_consumption_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import re
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
js_text = (Path(root_dir) / "static" / "app.js").read_text(encoding="utf-8")
load_section = js_text.split("async function loadCrewWorkHubSummary", 1)[1].split("function setCrewFormalApproveFeedback", 1)[0]
status_meta_section = js_text.split("function buildCrewManagementInsightStatusMeta", 1)[1].split("function renderCrewManagementInsightSummary", 1)[0]
cards_render_section = js_text.split("function renderCrewWorkHubCards", 1)[1].split("function buildCrewWorkHubFocusSectionMeta", 1)[0]
focus_summary_section = js_text.split("function buildCrewWorkHubPrimaryTimeline", 1)[1].split("function renderCrewWorkHubFocusSections", 1)[0]
focus_interaction_section = js_text.split("function mapCrewWorkHubSectionKeyToAction", 1)[1].split("function syncCrewScheduledRowMarkers", 1)[0]
drilldown_interaction_section = js_text.split("function findCrewWorkHubFocusSectionTarget", 1)[1].split("function syncCrewScheduledRowMarkers", 1)[0]
target_boundary_section = js_text.split("function findCrewWorkHubTarget", 1)[1].split("function clearCrewWorkHubDestinationActiveState", 1)[0]
section_action_mapping = js_text.split("function mapCrewWorkHubSectionKeyToAction", 1)[1].split("function findCrewWorkHubEntryRow", 1)[0]
event_delegation_section = js_text.split('document.addEventListener("click"', 1)[1].split('document.addEventListener("focusin"', 1)[0]
reset_derived_state_section = js_text.split("function resetCrewWorkHubDerivedState", 1)[1].split("function buildCrewRequirementMeta", 1)[0]

required_load_snippets = (
    "/api/management-read-model?sheet_id=",
    "const managementReadModelResponse = await fetch(",
    "const managementReadModelData = await managementReadModelResponse.json().catch(() => ({}));",
    "if (!managementReadModelResponse.ok || !managementReadModelData?.management_summary) {",
    "const managementSummary = managementReadModelData.management_summary;",
    "/api/work-hub-runtime?sheet_id=",
    "const workHubRuntimeResponse = await fetch(",
    "const workHubRuntimeData = await workHubRuntimeResponse.json().catch(() => ({}));",
    "if (!workHubRuntimeResponse.ok || !workHubRuntimeData?.work_hub?.summary) {",
    "blocked_count: managementSummary.blocked_count ?? 0,",
    "schedulable_count: managementSummary.schedulable_count ?? 0,",
    "scheduled_count: managementSummary.scheduled_count ?? 0,",
    "pending_approval_count: managementSummary.pending_approval_count ?? 0,",
    "pending_requirement_count: managementSummary.pending_requirement_count ?? 0,",
    "today_entry_count: managementSummary.today_entry_count ?? 0,",
    "today_schedule_count: managementSummary.today_schedule_count ?? 0,",
    "drilldown_refs: managementReadModelData.drilldown_refs,",
    "Array.isArray(workHubRuntimeData?.work_hub?.scheduled_entries)",
    'workHubRuntimeData.work_hub.scheduled_entries.map((entry) => String(entry?.id ?? "").trim()).filter(Boolean)',
    "Promise.allSettled([",
    "/api/dashboard?sheet_id=",
    "/api/scheduling?sheet_id=",
    "summary.pending_approval_count = dashboardData.summary.pending_approval_count ?? 0;",
    "summary.pending_requirement_count = dashboardData.summary.pending_requirement_count ?? 0;",
    "summary.today_entry_count = dashboardData.summary.today_entry_count ?? 0;",
    "summary.scheduled_count = dashboardData.summary.scheduled_count ?? 0;",
    "summary.blocked_count = schedulingData.summary.blocked_count ?? 0;",
    "summary.schedulable_count = schedulingData.summary.schedulable_count ?? 0;",
    "let dashboardApplied = false;",
    "let schedulingApplied = false;",
    'focusSections.state = dashboardApplied ? "fallback" : "degraded";',
    'const renderState = dashboardApplied && schedulingApplied ? "fallback" : "degraded";',
    "crewScheduledEntryIds = new Set(",
    "resetCrewWorkHubDerivedState();",
    "syncCrewScheduledRowMarkers();",
    'renderCrewManagementInsightSummary({ state: renderState, summary, drilldown_refs: {} });',
    'renderCrewManagementInsightSummary({ state: "empty", summary: emptySummary, drilldown_refs: {} });',
    'renderCrewWorkHubCards({ state: renderState, summary });',
    'renderCrewWorkHubCards({ state: "empty", summary: emptySummary });',
    'renderCrewWorkHubFocusSections({ state: "empty", summary: emptySummary });',
)
for snippet in required_load_snippets:
    if snippet not in load_section:
        raise SystemExit(f"work hub runtime consumption missing load path guardrail: {snippet}")

allowed_fetch_targets = {
    "/api/management-read-model?sheet_id=${encodeURIComponent(sheetId)}",
    "/api/work-hub-runtime?sheet_id=${encodeURIComponent(sheetId)}",
    "/api/dashboard?sheet_id=${encodeURIComponent(sheetId)}",
    "/api/scheduling?sheet_id=${encodeURIComponent(sheetId)}",
}
actual_fetch_targets = {
    target
    for target in re.findall(r"fetch\\(`/api/([^`]+)`\\)", load_section)
}
normalized_fetch_targets = {f"/api/{target}" for target in actual_fetch_targets}
if normalized_fetch_targets != allowed_fetch_targets:
    raise SystemExit(
        "work hub runtime consumption should keep exact API dependency set: "
        f"{sorted(normalized_fetch_targets)}"
    )

if load_section.count("fetch(`/api/") != 4:
    raise SystemExit("work hub runtime consumption should keep exactly four API fetch callsites")

if "Promise.allSettled([" not in load_section:
    raise SystemExit("work hub runtime consumption should keep dashboard+scheduling fallback boundary")

if load_section.count("resetCrewWorkHubDerivedState();") != 2:
    raise SystemExit("work hub fallback and empty paths should both reset derived drilldown state")

if "managementReadModelData.management_summary" not in load_section:
    raise SystemExit("management insight primary consumer should depend on public management_summary shape")

if "workHubRuntimeData.work_hub.summary" not in load_section:
    raise SystemExit("work hub primary consumer should depend on public work_hub.summary shape")

for required_state in ('"primary"', '"fallback"', '"degraded"', '"empty"'):
    if required_state not in load_section:
        raise SystemExit(f"work hub runtime consumption should preserve render state: {required_state}")

for required_state_label in ('stateLabel: "primary"', 'stateLabel: "fallback"', 'stateLabel: "degraded"', 'stateLabel: "empty"'):
    if required_state_label not in status_meta_section:
        raise SystemExit(f"management insight status marker should preserve render state: {required_state_label}")

for forbidden_snippet in (
    "/api/crew-work-entry-requirement-confirm",
    "/api/crew-work-entry/formal-approve",
    'method: "POST"',
    "method: 'POST'",
    "fetch(`/api/analytics",
    "build_dashboard_payload(",
    "build_scheduling_payload(",
    "build_work_hub_runtime_payload(",
    "build_management_read_model_payload(",
):
    if forbidden_snippet in load_section:
        raise SystemExit(f"work hub runtime consumption load section should remain read-only: {forbidden_snippet}")

if 'data-testid="crew-work-hub-cards"' not in template_text:
    raise SystemExit("work hub runtime consumption should keep work hub cards mount container")
if 'data-testid="crew-management-insight-summary"' not in template_text:
    raise SystemExit("work hub runtime consumption should keep management insight summary mount container")
if 'data-testid="crew-work-hub-focus-sections"' not in template_text:
    raise SystemExit("work hub runtime consumption should keep work hub focus sections mount container")
if '<section class="crew-form-shell" data-mode="readonly"' not in template_text:
    raise SystemExit("work hub runtime consumption should keep readonly crew shell container")
for snippet in (
    ".crew-management-insight-summary",
    ".crew-management-insight-summary-grid",
    ".crew-management-insight-metric",
    ".crew-management-insight-metric:hover",
    ".crew-management-insight-metric:focus-visible",
    '.crew-management-insight-metric[data-management-insight-active="true"]',
    ".crew-management-insight-note",
    ".crew-work-hub-focus-hint",
    ".crew-work-hub-focus-item",
    ".crew-work-hub-focus-primary-timeline",
    ".crew-work-hub-focus-summary-line",
    ".crew-work-hub-focus-badges",
    ".crew-work-hub-focus-badge",
    ".crew-work-hub-focus-item:focus-visible",
    ".crew-work-hub-focus-item-arrow",
    '.crew-work-hub-focus-section[data-work-hub-destination-active="true"]',
    '.crew-vendor-list[data-work-hub-destination-active="true"]',
    '@media (max-width: 720px)',
):
    if snippet not in template_text:
        raise SystemExit(f"work hub runtime consumption should keep focus item affordance styling: {snippet}")

required_focus_section_snippets = (
    'const crewManagementInsightSummary = document.getElementById("crewManagementInsightSummary");',
    "function buildCrewManagementInsightStatusMeta(data = {}) {",
    "function buildCrewManagementInsightMetricMeta(summary = {}, drilldownRefs = {}) {",
    "const resolveTargetAction = (key, fallbackAction) => {",
    'const target = String(drilldownRefs?.[key]?.target || "").trim();',
    "return target || fallbackAction;",
    "function buildCrewManagementInsightNotes(summary = {}) {",
    "function renderCrewManagementInsightSummary(data) {",
    "Management Insight Summary",
    "優先使用 management read model API，整理排程、核准與需求確認的只讀管理摘要。",
    "management read model 暫時不可用，改用既有 dashboard / scheduling 只讀摘要。",
    "部分只讀資料暫時不可用，顯示降級管理摘要。",
    "目前沒有可顯示的管理摘要，保留只讀空狀態。",
    'data-testid="crew-management-insight-mode"',
    'data-testid="crew-management-insight-status-note"',
    'data-testid="crew-management-insight-metric-${metric.summaryKey}"',
    'data-testid="crew-management-insight-value-${metric.summaryKey}"',
    'data-testid="crew-management-insight-note-${index + 1}"',
    'data-management-insight-action="${escapeHtml(metric.targetAction)}"',
    'crewManagementInsightSummary.setAttribute("data-management-insight-state", statusMeta.stateLabel);',
    'crewWorkHubCards.setAttribute("data-work-hub-render-state", renderState);',
    'crewWorkHubFocusSections.setAttribute("data-work-hub-render-state", renderState);',
    'tabindex="0"',
    'role="button"',
    '按 Enter 可查看對應 Work Hub 明細',
    'targetAction: resolveTargetAction("today_entries", "today-entries")',
    'targetAction: resolveTargetAction("scheduled", "scheduled")',
    'targetAction: resolveTargetAction("today_schedule", "today-schedule")',
    'targetAction: resolveTargetAction("schedulable", "schedulable")',
    'targetAction: resolveTargetAction("blocked", "blocked")',
    'targetAction: resolveTargetAction("pending_approval", "pending-approval")',
    'targetAction: resolveTargetAction("pending_requirement", "pending-requirement")',
    "function setCrewManagementInsightMetricActiveState(metric) {",
    "function activateCrewManagementInsightMetric(metric) {",
    'metric.setAttribute("data-management-insight-active", "true");',
    "function activateCrewReadonlyDrilldown(control) {",
    'if (control.matches("[data-management-insight-action]")) {',
    "activateCrewManagementInsightMetric(control);",
    "scrollCrewWorkHubToTarget(metric.dataset.managementInsightAction);",
    'if (action === "today-schedule") {',
    'const focusSectionTarget = findCrewWorkHubFocusSectionTarget(action);',
    "focusSectionTarget ||",
    'crewVendorList.querySelector("[data-work-hub-scheduled=\\\'true\\\']") ||',
    "summary.today_schedule_count ?? 0,",
    "summary.schedulable_count ?? 0,",
    "summary.blocked_count ?? 0,",
    "summary.pending_approval_count ?? 0,",
    "summary.pending_requirement_count ?? 0,",
    "renderCrewManagementInsightSummary({",
    'renderCrewManagementInsightSummary({ state: renderState, summary, drilldown_refs: {} });',
    'renderCrewManagementInsightSummary({ state: "empty", summary: emptySummary, drilldown_refs: {} });',
    'const crewWorkHubFocusSections = document.getElementById("crewWorkHubFocusSections");',
    "function renderCrewWorkHubFocusSections(data) {",
    'data-testid="crew-work-hub-focus-section-${section.key}"',
    'data-testid="crew-work-hub-focus-count-${section.key}"',
    'data-testid="crew-work-hub-focus-empty-${section.key}"',
    'class="crew-work-hub-focus-item"',
    'class="crew-work-hub-focus-item-main"',
    'class="crew-work-hub-focus-item-arrow"',
    '<p class="crew-work-hub-focus-hint">點擊項目可定位到下方明細</p>',
    "function buildCrewWorkHubPrimaryTimeline(entry) {",
    "function buildCrewWorkHubSummaryBadges(entry, sectionKey) {",
    "function buildCrewWorkHubFocusSummary(entry, sectionKey) {",
    "function buildCrewWorkHubFocusAriaLabel(entry) {",
    "function activateCrewWorkHubFocusItem(item) {",
    "function findCrewWorkHubFocusSectionTarget(action) {",
    'class="crew-work-hub-focus-badges"',
    'class="crew-work-hub-focus-badge"',
    'class="crew-work-hub-focus-primary-timeline"',
    'class="crew-work-hub-focus-summary-line"',
    'data-work-hub-entry-id="${escapeHtml(entry?.id ?? "")}"',
    'data-work-hub-section-key="${escapeHtml(section.key)}"',
    'tabindex="0"',
    'role="button"',
    'aria-label="${escapeHtml(buildCrewWorkHubFocusAriaLabel(entry))}"',
    "function findCrewWorkHubEntryRow(entryId) {",
    "function setCrewWorkHubFocusItemActiveState(item) {",
    'function focusCrewWorkHubEntryRow(entryId, fallbackAction = "") {',
    'item.setAttribute("data-work-hub-item-active", "true");',
    'row.setAttribute("data-work-hub-focus-active", "true");',
    "window.setTimeout(() => {",
    "if (!row) {",
    "scrollCrewWorkHubToTarget(fallbackAction);",
    'if (control.matches("[data-work-hub-entry-id]")) {',
    "activateCrewWorkHubFocusItem(control);",
    'document.addEventListener("keydown", (event) => {',
    'if (event.key !== "Enter" && event.key !== " ") return;',
    "event.preventDefault();",
    "blocked_entries: Array.isArray(workHubRuntimeData?.work_hub?.blocked_entries)",
    "schedulable_entries: Array.isArray(workHubRuntimeData?.work_hub?.schedulable_entries)",
    "today_entries: Array.isArray(workHubRuntimeData?.work_hub?.today_entries)",
    "today_schedule: Array.isArray(workHubRuntimeData?.work_hub?.today_schedule)",
    "function resetCrewWorkHubDerivedState() {",
    "clearCrewWorkHubFocusedRow();",
    "setCrewWorkHubFocusItemActiveState(null);",
    "setCrewManagementInsightMetricActiveState(null);",
    "renderCrewWorkHubFocusSections(focusSections);",
    "syncCrewScheduledRowMarkers();",
    'data-work-hub-action="${card.action}"',
)
for snippet in required_focus_section_snippets:
    if snippet not in js_text:
        raise SystemExit(f"work hub runtime consumption missing focus sections guardrail: {snippet}")

for snippet in (
    "let crewWorkHubDestinationActiveTimeoutId = 0;",
    "function clearCrewWorkHubDestinationActiveState() {",
    "window.clearTimeout(crewWorkHubDestinationActiveTimeoutId);",
    'container.removeAttribute("data-work-hub-destination-active");',
    "function setCrewWorkHubDestinationActiveState(target) {",
    'const isFocusSection = target?.classList?.contains("crew-work-hub-focus-section");',
    "const isVendorList = target === crewVendorList;",
    'target.setAttribute("data-work-hub-destination-active", "true");',
    'target.removeAttribute("data-work-hub-destination-active");',
    "crewWorkHubDestinationActiveTimeoutId = window.setTimeout(() => {",
    "clearCrewWorkHubDestinationActiveState();",
    'if (target.classList?.contains("crew-entry-row")) {',
    "focusCrewWorkHubEntryRow(target.dataset.entryId);",
    "setCrewWorkHubDestinationActiveState(target);",
):
    if snippet not in drilldown_interaction_section and snippet not in js_text:
        raise SystemExit(f"readonly drilldown destination feedback missing guardrail: {snippet}")

for snippet in (
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-blocked=\\\'true\\\']") || crewVendorList;',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-schedulable=\\\'true\\\']") || crewVendorList;',
    'return focusSectionTarget || crewVendorList.querySelector("[data-work-hub-scheduled=\\\'true\\\']") || crewVendorList;',
    'return crewVendorList.querySelector("[data-work-hub-pending-approval=\\\'true\\\']") || crewVendorList;',
    'return crewVendorList.querySelector("[data-work-hub-pending-requirement=\\\'true\\\']") || crewVendorList;',
):
    if snippet not in target_boundary_section:
        raise SystemExit(f"readonly drilldown should preserve section to row to list fallback: {snippet}")

if 'if (sectionKey === "today-schedule") {' not in section_action_mapping or 'return "today-schedule";' not in section_action_mapping:
    raise SystemExit("today-schedule missing-row fallback should preserve today-schedule section semantics")
if 'sectionKey === "today-entries" || sectionKey === "today-schedule"' in section_action_mapping:
    raise SystemExit("today-schedule missing-row fallback must not collapse into today-entries")

if event_delegation_section.count("activateCrewReadonlyDrilldown(crewReadonlyDrilldown)") != 2:
    raise SystemExit("click and keyboard drilldown activation should share the same readonly handler")
for snippet in (
    '"[data-management-insight-action], [data-work-hub-entry-id], [data-work-hub-action]"',
    'if (event.key !== "Enter" && event.key !== " ") return;',
    "event.preventDefault();",
):
    if snippet not in event_delegation_section:
        raise SystemExit(f"readonly drilldown click/keyboard parity missing guardrail: {snippet}")

for snippet in (
    'data-work-hub-action="${card.action}"',
    'tabindex="0"',
    'role="button"',
    'aria-label="${escapeHtml(`${card.title} ${card.value}，按 Enter 可查看對應 Work Hub 明細`)}"',
):
    if snippet not in cards_render_section:
        raise SystemExit(f"work hub cards should preserve readonly click/keyboard parity: {snippet}")

for forbidden_snippet in (
    "fetch(",
    'method: "POST"',
    "method: 'POST'",
    "localStorage",
    "sessionStorage",
    "document.cookie",
    "history.pushState",
    "location.href",
):
    if forbidden_snippet in drilldown_interaction_section:
        raise SystemExit(f"readonly drilldown helpers must remain fetch-free and non-persistent: {forbidden_snippet}")

for snippet in (
    'const plannedAt = String(entry?.planned_at || "").trim();',
    'const scheduledDate = String(entry?.scheduled_date || "").trim();',
    'const scheduledTime = String(entry?.scheduled_time || "").trim();',
    'const requirementStatus = String(entry?.requirement_status || "").trim();',
    'const formalApprovalState = String(entry?.formal_approval_state || "").trim();',
    'const schedulingGateState = String(entry?.scheduling_gate_state || "").trim();',
    'const schedulingGateReason = String(entry?.scheduling_gate_reason || "").trim();',
    'const readinessState = String(entry?.readiness_state || "").trim();',
    'const readinessReason = String(entry?.readiness_reason || "").trim();',
    'const hasRequirement = Boolean(String(entry?.pre_entry_requirement || "").trim());',
):
    if snippet not in focus_summary_section:
        raise SystemExit(f"work hub focus summary density should consume existing entry fields: {snippet}")

for forbidden_snippet in (
    "fetch(",
    'method: "POST"',
    "method: 'POST'",
):
    if forbidden_snippet in focus_interaction_section:
        raise SystemExit(f"work hub focus item interaction should remain read-only and fetch-free: {forbidden_snippet}")

for required_snippet in (
    "crewScheduledEntryIds = new Set();",
    "syncCrewScheduledRowMarkers();",
    "clearCrewWorkHubDestinationActiveState();",
    "clearCrewWorkHubFocusedRow();",
    "setCrewWorkHubFocusItemActiveState(null);",
    "setCrewManagementInsightMetricActiveState(null);",
):
    if required_snippet not in reset_derived_state_section:
        raise SystemExit(f"work hub derived state reset missing guardrail: {required_snippet}")

for forbidden_snippet in (
    "fetch(",
    "localStorage",
    "sessionStorage",
    "document.cookie",
    'method: "POST"',
    "method: 'POST'",
):
    if forbidden_snippet in reset_derived_state_section:
        raise SystemExit(f"work hub derived state reset must not persist or mutate business data: {forbidden_snippet}")

for snippet in (
    "setCrewWorkHubFocusItemActiveState(item);",
    "focusCrewWorkHubEntryRow(",
    "mapCrewWorkHubSectionKeyToAction(item.dataset.workHubSectionKey)",
):
    if snippet not in focus_interaction_section and snippet not in js_text:
        raise SystemExit(f"work hub accessibility activation should keep existing navigation helper path: {snippet}")

for forbidden_snippet in (
    "fetch(",
    'method: "POST"',
    "method: 'POST'",
):
    if forbidden_snippet in focus_summary_section:
        raise SystemExit(f"work hub focus summary density should remain read-only and fetch-free: {forbidden_snippet}")

for required_snippet in (
    "const todayEntryCount = Number(summary.today_entry_count ?? 0);",
    "const scheduledCount = Number(summary.scheduled_count ?? 0);",
    "const todayScheduleCount = Number(summary.today_schedule_count ?? 0);",
    "const schedulableCount = Number(summary.schedulable_count ?? 0);",
    "const blockedCount = Number(summary.blocked_count ?? 0);",
    "const pendingApprovalCount = Number(summary.pending_approval_count ?? 0);",
    "const pendingRequirementCount = Number(summary.pending_requirement_count ?? 0);",
    "const drilldownRefs = data?.drilldown_refs || {};",
    "排程進度：今日進場",
    "核准狀態：待正式核准",
    "需求確認狀態：待確認需求",
):
    if required_snippet not in js_text:
        raise SystemExit(f"management insight summary should reuse existing dashboard/work hub counts: {required_snippet}")

for forbidden_snippet in (
    "最大瓶頸",
    "最優先處理",
    "風險最高",
    "priority",
    "bottleneck",
    "KPI",
    "sorting",
    "build_dashboard_payload(",
    "build_work_hub_runtime_payload(",
    "build_management_read_model_payload(",
    "Array.isArray(workHubRuntimeData?.work_hub?.today_entries) ? workHubRuntimeData.work_hub.today_entries.filter(",
    "Array.isArray(workHubRuntimeData?.work_hub?.scheduled_entries) ? workHubRuntimeData.work_hub.scheduled_entries.filter(",
    "managementReadModelData.management_summary.blocked_entries",
    "managementReadModelData.management_summary.schedulable_entries",
    "managementReadModelData.management_summary.scheduled_entries",
    "managementReadModelData.management_summary.today_entries",
):
    if forbidden_snippet in js_text:
        raise SystemExit(f"management insight drilldown should not derive new rules or reach into backend helpers: {forbidden_snippet}")

for forbidden_snippet in (
    "fetch(`/api/analytics",
    "blocked_items.length",
    "schedulable_entries.filter(",
    "today_entries.filter(",
    "scheduled_entries.filter(",
    "drilldown_refs.filter(",
    "Promise.race([",
):
    if forbidden_snippet in js_text:
        raise SystemExit(f"management insight summary should not introduce new analytics APIs or frontend rule re-derivation: {forbidden_snippet}")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect for work hub runtime consumption smoke")

    sheet_response = client.get("/sheet")
    if sheet_response.status_code != 200:
        raise SystemExit("/sheet GET should render successfully for work hub runtime consumption smoke")
    html = sheet_response.get_data(as_text=True)
    for snippet in (
        'data-testid="crew-work-hub-shell"',
        'data-testid="crew-management-insight-summary"',
        'data-testid="crew-work-hub-cards"',
        'data-testid="crew-work-hub-focus-sections"',
        'data-testid="crew-work-hub-target-today-entries"',
    ):
        if snippet not in html:
            raise SystemExit(f"rendered /sheet missing work hub runtime consumption shell: {snippet}")

print("work hub runtime consumption smoke PASS")
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
    if "work hub runtime consumption smoke PASS" not in result.stdout:
        raise AssertionError("work hub runtime consumption smoke subprocess did not report PASS.")


def run_sheet_endpoint_smoke(app_db_path: Path) -> None:
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

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
if "sheet.sheet" in template_text:
    raise SystemExit("sheet.html should not reference sheet.sheet")

for source_path in (
    Path(root_dir) / "routes" / "auth.py",
    Path(root_dir) / "routes" / "sheet.py",
):
    source_text = source_path.read_text(encoding="utf-8")
    if "sheet.sheet" in source_text:
        raise SystemExit(f"{source_path.name} should not reference sheet.sheet")

sheet_rules = [rule.rule for rule in module.app.url_map.iter_rules() if rule.endpoint == "sheet"]
if "/sheet" not in sheet_rules or "/sheet/<int:sheet_id>" not in sheet_rules:
    raise SystemExit("app.url_map missing expected sheet routes")
if any(rule.endpoint == "sheet.sheet" for rule in module.app.url_map.iter_rules()):
    raise SystemExit("app.url_map should not require sheet.sheet endpoint")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect")
    location = login_response.headers.get("Location", "")
    if not location.endswith("/sheet"):
        raise SystemExit(f"login redirect target mismatch: {location}")

    sheet_response = client.get("/sheet")
    if sheet_response.status_code != 200:
        raise SystemExit("/sheet GET should render successfully")

    specific_sheet_response = client.get("/sheet/1")
    if specific_sheet_response.status_code != 200:
        raise SystemExit("/sheet/1 GET should render successfully")

    html = sheet_response.get_data(as_text=True)
    if "/sheet/1" not in html:
        raise SystemExit("sheet tab link should render /sheet/<id> href")
    if "sheet.sheet" in html:
        raise SystemExit("rendered sheet page should not contain sheet.sheet")

print("sheet endpoint smoke PASS")
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
    if "sheet endpoint smoke PASS" not in result.stdout:
        raise AssertionError("sheet endpoint smoke subprocess did not report PASS.")


def run_table_admin_endpoint_and_formula_smoke(app_db_path: Path) -> None:
    script = """
import importlib.util
import os
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "table_admin.html").read_text(encoding="utf-8")
if "admin.table_admin" in template_text:
    raise SystemExit("table_admin.html should not reference admin.table_admin")
admin_route_text = (Path(root_dir) / "routes" / "admin.py").read_text(encoding="utf-8")
if "admin.table_admin" in admin_route_text:
    raise SystemExit("routes/admin.py should not reference admin.table_admin")

table_rules = [rule.rule for rule in module.app.url_map.iter_rules() if rule.endpoint == "table_admin"]
if "/admin/table" not in table_rules:
    raise SystemExit("app.url_map missing table_admin endpoint")

field_initial = {"field_key": "initial_check", "field_type": "date"}
field_recheck_1 = {"field_key": "recheck_1", "field_type": "date"}
field_recheck_2 = {"field_key": "recheck_2", "field_type": "date"}
field_handover = {"field_key": "handover", "field_type": "status"}

if module.extra_done(field_initial, {"recheck_1": "", "recheck_2": "2026-06-29", "handover": "X"}):
    raise SystemExit("initial_check should not complete from recheck_2 alone")
if not module.extra_done(field_initial, {"recheck_1": "2026-06-29", "recheck_2": "", "handover": "X"}):
    raise SystemExit("initial_check should complete from recheck_1")
if not module.extra_done(field_initial, {"recheck_1": "", "recheck_2": "", "handover": "O"}):
    raise SystemExit("initial_check should complete from handover=O")

if not module.extra_done(field_recheck_1, {"recheck_2": "2026-06-29", "handover": "X"}):
    raise SystemExit("recheck_1 should complete from recheck_2")
if not module.extra_done(field_recheck_1, {"recheck_2": "", "handover": "O"}):
    raise SystemExit("recheck_1 should complete from handover=O")

if not module.extra_done(field_recheck_2, {"recheck_2": "2026-06-29", "handover": "X"}):
    raise SystemExit("recheck_2 should complete from its own date")
if not module.extra_done(field_recheck_2, {"recheck_2": "", "handover": "O"}):
    raise SystemExit("recheck_2 should complete from handover=O")
if not module.extra_done(field_handover, {"handover": "O"}):
    raise SystemExit("handover should complete from O")

with module.app.test_client() as client:
    login_response = client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if login_response.status_code != 302:
        raise SystemExit("login route did not redirect for table admin smoke")

    table_response = client.get("/admin/table")
    if table_response.status_code != 200:
        raise SystemExit("/admin/table should render successfully")
    html = table_response.get_data(as_text=True)
    if "/admin/table?sheet_id=1" not in html and "/admin/table?sheet_id=" not in html:
        raise SystemExit("table admin sheet switcher link missing expected /admin/table?sheet_id=... href")
    if "admin.table_admin" in html:
        raise SystemExit("rendered /admin/table should not contain admin.table_admin")

print("table admin endpoint and formula smoke PASS")
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
    if "table admin endpoint and formula smoke PASS" not in result.stdout:
        raise AssertionError("table admin endpoint and formula smoke subprocess did not report PASS.")


def run_admin_current_site_sheet_write_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing")
    site_b_row = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__admin_write_site_b__", "site-b"),
    ).fetchone()
    site_b = int(site_b_row["id"])
    sheet_a = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()["id"]
    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Sheet B", 999, site_b),
    ).fetchone()["id"]
    conn.commit()

client = module.app.test_client()

def set_admin_session(*, current_site_id=None, current_site_name=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "管理員"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = current_site_name or f"site-{current_site_id}"
            session["site_selection_required"] = False

with module.db() as conn:
    before_count = conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0]
set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
create_response = client.post(
    "/admin/table",
    data={"action": "create_sheet", "new_sheet_name": "Current Site Sheet"},
    follow_redirects=False,
)
if create_response.status_code != 302:
    raise SystemExit("create_sheet should redirect")
with module.db() as conn:
    after_count = conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0]
    created_row = conn.execute(
        "SELECT site_id FROM sheets WHERE name = ? ORDER BY id DESC LIMIT 1",
        ("Current Site Sheet",),
    ).fetchone()
if after_count != before_count + 1:
    raise SystemExit("create_sheet should add one sheet")
if created_row is None or int(created_row["site_id"]) != int(site_a):
    raise SystemExit("create_sheet should use current_site_id")

set_admin_session()
missing_create = client.post(
    "/admin/table",
    data={"action": "create_sheet", "new_sheet_name": "Should Not Exist"},
    follow_redirects=False,
)
if missing_create.status_code != 302 or not missing_create.headers.get("Location", "").endswith("/site-selector"):
    raise SystemExit("missing current site create_sheet should redirect to /site-selector")
with module.db() as conn:
    missing_row = conn.execute("SELECT 1 FROM sheets WHERE name = ?", ("Should Not Exist",)).fetchone()
if missing_row is not None:
    raise SystemExit("missing current site create_sheet should not add a sheet")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
delete_current = client.post(f"/admin/table?sheet_id={sheet_a}", data={"action": "delete_sheet"}, follow_redirects=False)
if delete_current.status_code != 302:
    raise SystemExit("delete current-site sheet should redirect")
with module.db() as conn:
    deleted_row = conn.execute("SELECT 1 FROM sheets WHERE id = ?", (sheet_a,)).fetchone()
    other_row = conn.execute("SELECT 1 FROM sheets WHERE id = ?", (sheet_b,)).fetchone()
if deleted_row is not None:
    raise SystemExit("delete current-site sheet should remove target sheet")
if other_row is None:
    raise SystemExit("delete current-site sheet should not remove other site sheet")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
cross_site_before = sqlite3.connect(app_db_path)
cross_site_before.row_factory = sqlite3.Row
before_snapshot = cross_site_before.execute("SELECT COUNT(*) FROM sheets WHERE id = ?", (sheet_b,)).fetchone()[0]
cross_site_before.close()
cross_site_delete = client.post(f"/admin/table?sheet_id={sheet_b}", data={"action": "delete_sheet"}, follow_redirects=False)
if cross_site_delete.status_code != 302 or "/admin/table?sheet_id=" not in cross_site_delete.headers.get("Location", ""):
    raise SystemExit("cross-site delete should redirect back to /admin/table")
with module.db() as conn:
    after_snapshot = conn.execute("SELECT COUNT(*) FROM sheets WHERE id = ?", (sheet_b,)).fetchone()[0]
if before_snapshot != after_snapshot:
    raise SystemExit("cross-site delete should not remove target sheet")

set_admin_session()
missing_delete = client.post(f"/admin/table?sheet_id={sheet_b}", data={"action": "delete_sheet"}, follow_redirects=False)
if missing_delete.status_code != 302 or not missing_delete.headers.get("Location", "").endswith("/site-selector"):
    raise SystemExit("missing current site delete_sheet should redirect to /site-selector")
with module.db() as conn:
    final_snapshot = conn.execute("SELECT COUNT(*) FROM sheets WHERE id = ?", (sheet_b,)).fetchone()[0]
if final_snapshot != after_snapshot:
    raise SystemExit("missing current site delete should not remove target sheet")

print("admin current-site sheet write smoke PASS")
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
    if "admin current-site sheet write smoke PASS" not in result.stdout:
        raise AssertionError("admin current-site sheet write smoke subprocess did not report PASS.")


def run_admin_current_site_task_write_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing")
    site_b = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__admin_task_site_b__", "task-site-b"),
    ).fetchone()["id"]
    sheet_a = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()["id"]
    floor_a = conn.execute("SELECT id FROM floors WHERE sheet_id = ? ORDER BY id LIMIT 1", (sheet_a,)).fetchone()["id"]
    unit_a = conn.execute("SELECT id FROM units WHERE floor_id = ? ORDER BY id LIMIT 1", (floor_a,)).fetchone()["id"]
    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Task Sheet B", 900, site_b),
    ).fetchone()["id"]
    floor_b = conn.execute(
        "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 1) RETURNING id",
        (sheet_b, 901, "B1", "B"),
    ).fetchone()["id"]
    unit_b = conn.execute(
        "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?) RETURNING id",
        (floor_b, 1, "B101"),
    ).fetchone()["id"]
    task_b = conn.execute(
        "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (sheet_b, 901, "Vendor B", "Location B", "Task B"),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)",
        (unit_b, task_b, module.WORKING_VALUE),
    )
    conn.commit()

client = module.app.test_client()

def set_admin_session(*, current_site_id=None, current_site_name=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = current_site_name or f"site-{current_site_id}"
            session["site_selection_required"] = False

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
    before_progress = conn.execute(
        "SELECT COUNT(*) FROM progress WHERE unit_id = ?",
        (unit_a,),
    ).fetchone()[0]
add_task_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={
        "action": "add_task",
        "new_task_vendor": "Vendor A",
        "new_task_location": "Location A",
        "new_task_name": "Task A2",
    },
    follow_redirects=False,
)
if add_task_ok.status_code != 302:
    raise SystemExit("add_task current site should redirect")
with module.db() as conn:
    after_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
    created_task = conn.execute(
        "SELECT id FROM tasks WHERE sheet_id = ? AND name = ? ORDER BY id DESC LIMIT 1",
        (sheet_a, "Task A2"),
    ).fetchone()
    after_progress = conn.execute(
        "SELECT COUNT(*) FROM progress WHERE unit_id = ?",
        (unit_a,),
    ).fetchone()[0]
if after_tasks != before_tasks + 1:
    raise SystemExit("add_task current site should add one task")
if created_task is None:
    raise SystemExit("add_task current site should create task row")
if after_progress != before_progress + 1:
    raise SystemExit("add_task current site should add progress rows")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_cross_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE sheet_id = ?", (sheet_b,)).fetchone()[0]
    before_cross_progress = conn.execute("SELECT COUNT(*) FROM progress WHERE task_id = ?", (task_b,)).fetchone()[0]
add_task_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={
        "action": "add_task",
        "new_task_vendor": "Vendor Cross",
        "new_task_location": "Location Cross",
        "new_task_name": "Should Not Add",
    },
    follow_redirects=False,
)
if add_task_cross.status_code != 302 or "/admin/table?sheet_id=" not in add_task_cross.headers.get("Location", ""):
    raise SystemExit("add_task cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_cross_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE sheet_id = ?", (sheet_b,)).fetchone()[0]
    after_cross_progress = conn.execute("SELECT COUNT(*) FROM progress WHERE task_id = ?", (task_b,)).fetchone()[0]
    unexpected_cross = conn.execute(
        "SELECT 1 FROM tasks WHERE sheet_id = ? AND name = ?",
        (sheet_b, "Should Not Add"),
    ).fetchone()
if before_cross_tasks != after_cross_tasks:
    raise SystemExit("add_task cross-site should not add task row")
if before_cross_progress != after_cross_progress:
    raise SystemExit("add_task cross-site should not change progress rows")
if unexpected_cross is not None:
    raise SystemExit("add_task cross-site should not create a task")

set_admin_session()
missing_site_page = client.get(f"/admin/table?sheet_id={sheet_a}")
missing_site_html = missing_site_page.get_data(as_text=True)
if missing_site_page.status_code != 200:
    raise SystemExit("task admin page should still render without current site")
if 'data-task-write-enabled="false"' not in missing_site_html:
    raise SystemExit("task admin page should disable writes when current site is missing")
if 'data-task-write-block-reason="missing_current_site"' not in missing_site_html:
    raise SystemExit("task admin page should mark missing current-site block reason")
if 'data-task-write-blocked="true"' not in missing_site_html:
    raise SystemExit("task admin page should show blocked-state helper message")

delete_task_id = int(created_task["id"])
set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_delete_task = conn.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (delete_task_id,)).fetchone()[0]
    before_delete_progress = conn.execute("SELECT COUNT(*) FROM progress WHERE task_id = ?", (delete_task_id,)).fetchone()[0]
delete_task_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"delete_task:{delete_task_id}"},
    follow_redirects=False,
)
if delete_task_ok.status_code != 302:
    raise SystemExit("delete_task current site should redirect")
with module.db() as conn:
    after_delete_task = conn.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (delete_task_id,)).fetchone()[0]
    after_delete_progress = conn.execute("SELECT COUNT(*) FROM progress WHERE task_id = ?", (delete_task_id,)).fetchone()[0]
if before_delete_task != 1 or before_delete_progress <= 0:
    raise SystemExit("delete_task current site preconditions failed")
if after_delete_task != 0 or after_delete_progress != 0:
    raise SystemExit("delete_task current site should remove task and progress")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_cross_delete_task = conn.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (task_b,)).fetchone()[0]
    before_cross_delete_progress = conn.execute("SELECT COUNT(*) FROM progress WHERE task_id = ?", (task_b,)).fetchone()[0]
delete_task_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": f"delete_task:{task_b}"},
    follow_redirects=False,
)
if delete_task_cross.status_code != 302 or "/admin/table?sheet_id=" not in delete_task_cross.headers.get("Location", ""):
    raise SystemExit("delete_task cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_cross_delete_task = conn.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (task_b,)).fetchone()[0]
    after_cross_delete_progress = conn.execute("SELECT COUNT(*) FROM progress WHERE task_id = ?", (task_b,)).fetchone()[0]
if before_cross_delete_task != after_cross_delete_task:
    raise SystemExit("delete_task cross-site should not remove task")
if before_cross_delete_progress != after_cross_delete_progress:
    raise SystemExit("delete_task cross-site should not remove progress")

print("admin current-site task write smoke PASS")
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
    if "admin current-site task write smoke PASS" not in result.stdout:
        raise AssertionError("admin current-site task write smoke subprocess did not report PASS.")


def run_admin_current_site_floor_write_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing")
    site_b = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__admin_floor_site_b__", "floor-site-b"),
    ).fetchone()["id"]
    sheet_a = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()["id"]
    floor_a = conn.execute("SELECT id FROM floors WHERE sheet_id = ? ORDER BY id LIMIT 1", (sheet_a,)).fetchone()["id"]
    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Floor Sheet B", 910, site_b),
    ).fetchone()["id"]
    floor_b = conn.execute(
        "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 1) RETURNING id",
        (sheet_b, 911, "B1", "B"),
    ).fetchone()["id"]
    unit_b = conn.execute(
        "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?) RETURNING id",
        (floor_b, 1, "B101"),
    ).fetchone()["id"]
    task_b = conn.execute(
        "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (sheet_b, 912, "Vendor B", "Location B", "Task B"),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)",
        (unit_b, task_b, module.WORKING_VALUE),
    )
    conn.execute(
        "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
        (unit_b, module.WORKING_VALUE),
    )
    conn.execute(
        "INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (unit_b, "custom_field", "demo", 1),
    )
    conn.commit()

client = module.app.test_client()

def set_admin_session(*, current_site_id=None, current_site_name=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = current_site_name or f"site-{current_site_id}"
            session["site_selection_required"] = False

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_floors = conn.execute("SELECT COUNT(*) FROM floors WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
add_floor_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": "add_floor", "new_floor_name": "2F", "new_floor_block": "A"},
    follow_redirects=False,
)
if add_floor_ok.status_code != 302:
    raise SystemExit("add_floor current site should redirect")
with module.db() as conn:
    after_floors = conn.execute("SELECT COUNT(*) FROM floors WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
    added_floor = conn.execute(
        "SELECT 1 FROM floors WHERE sheet_id = ? AND name = ? AND block_name = ?",
        (sheet_a, "2F", "A"),
    ).fetchone()
if after_floors != before_floors + 1:
    raise SystemExit("add_floor current site should add one floor")
if added_floor is None:
    raise SystemExit("add_floor current site should create floor row")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_cross_floors = conn.execute("SELECT COUNT(*) FROM floors WHERE sheet_id = ?", (sheet_b,)).fetchone()[0]
add_floor_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": "add_floor", "new_floor_name": "Should Not Add", "new_floor_block": "B"},
    follow_redirects=False,
)
if add_floor_cross.status_code != 302 or "/admin/table?sheet_id=" not in add_floor_cross.headers.get("Location", ""):
    raise SystemExit("add_floor cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_cross_floors = conn.execute("SELECT COUNT(*) FROM floors WHERE sheet_id = ?", (sheet_b,)).fetchone()[0]
    unexpected_floor = conn.execute(
        "SELECT 1 FROM floors WHERE sheet_id = ? AND name = ?",
        (sheet_b, "Should Not Add"),
    ).fetchone()
if before_cross_floors != after_cross_floors:
    raise SystemExit("add_floor cross-site should not change floor count")
if unexpected_floor is not None:
    raise SystemExit("add_floor cross-site should not create floor row")

set_admin_session()
missing_site_page = client.get(f"/admin/table?sheet_id={sheet_a}")
missing_site_html = missing_site_page.get_data(as_text=True)
if missing_site_page.status_code != 200:
    raise SystemExit("floor admin page should still render without current site")
if 'data-floor-write-enabled="false"' not in missing_site_html:
    raise SystemExit("floor admin page should disable writes when current site is missing")
if 'data-floor-write-block-reason="missing_current_site"' not in missing_site_html:
    raise SystemExit("floor admin page should mark missing current-site block reason")
if 'data-floor-write-blocked="true"' not in missing_site_html:
    raise SystemExit("floor admin page should show blocked-state helper message")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_delete_floor = conn.execute("SELECT COUNT(*) FROM floors WHERE id = ?", (floor_a,)).fetchone()[0]
delete_floor_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"delete_floor:{floor_a}"},
    follow_redirects=False,
)
if delete_floor_ok.status_code != 302:
    raise SystemExit("delete_floor current site should redirect")
with module.db() as conn:
    after_delete_floor = conn.execute("SELECT COUNT(*) FROM floors WHERE id = ?", (floor_a,)).fetchone()[0]
if before_delete_floor != 1 or after_delete_floor != 0:
    raise SystemExit("delete_floor current site should remove floor")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_snapshot = {
        "floors": conn.execute("SELECT COUNT(*) FROM floors WHERE id = ?", (floor_b,)).fetchone()[0],
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE floor_id = ?", (floor_b,)).fetchone()[0],
        "progress": conn.execute("SELECT COUNT(*) FROM progress WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra": conn.execute("SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra_values": conn.execute("SELECT COUNT(*) FROM unit_extra_values WHERE unit_id = ?", (unit_b,)).fetchone()[0],
    }
delete_floor_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": f"delete_floor:{floor_b}"},
    follow_redirects=False,
)
if delete_floor_cross.status_code != 302 or "/admin/table?sheet_id=" not in delete_floor_cross.headers.get("Location", ""):
    raise SystemExit("delete_floor cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_snapshot = {
        "floors": conn.execute("SELECT COUNT(*) FROM floors WHERE id = ?", (floor_b,)).fetchone()[0],
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE floor_id = ?", (floor_b,)).fetchone()[0],
        "progress": conn.execute("SELECT COUNT(*) FROM progress WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra": conn.execute("SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra_values": conn.execute("SELECT COUNT(*) FROM unit_extra_values WHERE unit_id = ?", (unit_b,)).fetchone()[0],
    }
if before_snapshot != after_snapshot:
    raise SystemExit("delete_floor cross-site should not change related rows")

print("admin current-site floor write smoke PASS")
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
    if "admin current-site floor write smoke PASS" not in result.stdout:
        raise AssertionError("admin current-site floor write smoke subprocess did not report PASS.")


def run_admin_current_site_unit_write_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing")
    site_b = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__admin_unit_site_b__", "unit-site-b"),
    ).fetchone()["id"]
    sheet_a = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()["id"]
    floor_a = conn.execute("SELECT id FROM floors WHERE sheet_id = ? ORDER BY id LIMIT 1", (sheet_a,)).fetchone()["id"]
    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Unit Sheet B", 920, site_b),
    ).fetchone()["id"]
    floor_b = conn.execute(
        "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 1) RETURNING id",
        (sheet_b, 921, "B1", "B"),
    ).fetchone()["id"]
    unit_b = conn.execute(
        "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?) RETURNING id",
        (floor_b, 1, "B101"),
    ).fetchone()["id"]
    task_b = conn.execute(
        "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (sheet_b, 922, "Vendor B", "Location B", "Task B"),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)",
        (unit_b, task_b, module.WORKING_VALUE),
    )
    conn.execute(
        "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
        (unit_b, module.WORKING_VALUE),
    )
    conn.execute(
        "INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (unit_b, "custom_field", "demo", 1),
    )
    conn.commit()

client = module.app.test_client()

def set_admin_session(*, current_site_id=None, current_site_name=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = current_site_name or f"site-{current_site_id}"
            session["site_selection_required"] = False

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_snapshot = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE floor_id = ?", (floor_a,)).fetchone()[0],
        "progress": conn.execute(
            "SELECT COUNT(*) FROM progress WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_a,),
        ).fetchone()[0],
        "unit_extra": conn.execute(
            "SELECT COUNT(*) FROM unit_extra WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_a,),
        ).fetchone()[0],
        "unit_extra_values": conn.execute(
            "SELECT COUNT(*) FROM unit_extra_values WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_a,),
        ).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_a,)).fetchone()[0],
        "task_count": conn.execute("SELECT COUNT(*) FROM tasks WHERE sheet_id = ?", (sheet_a,)).fetchone()[0],
    }
add_unit_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"add_unit:{floor_a}", f"new_unit_name_{floor_a}": "102"},
    follow_redirects=False,
)
if add_unit_ok.status_code != 302:
    raise SystemExit("add_unit current site should redirect")
with module.db() as conn:
    after_units = conn.execute("SELECT COUNT(*) FROM units WHERE floor_id = ?", (floor_a,)).fetchone()[0]
    added_unit = conn.execute(
        "SELECT id FROM units WHERE floor_id = ? AND name = ? ORDER BY id DESC LIMIT 1",
        (floor_a, "102"),
    ).fetchone()
    after_progress = conn.execute(
        "SELECT COUNT(*) FROM progress WHERE unit_id = ?",
        (added_unit["id"],),
    ).fetchone()[0] if added_unit is not None else 0
    after_unit_extra = conn.execute(
        "SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?",
        (added_unit["id"],),
    ).fetchone()[0] if added_unit is not None else 0
    after_unit_count = conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_a,)).fetchone()[0]
if after_units != before_snapshot["units"] + 1:
    raise SystemExit("add_unit current site should add one unit")
if added_unit is None:
    raise SystemExit("add_unit current site should create unit row")
if after_progress != before_snapshot["task_count"]:
    raise SystemExit("add_unit current site should add progress rows for each task")
if after_unit_extra != 1:
    raise SystemExit("add_unit current site should initialize unit_extra")
if after_unit_count != before_snapshot["unit_count"] + 1:
    raise SystemExit("add_unit current site should update unit_count")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_cross = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE floor_id = ?", (floor_b,)).fetchone()[0],
        "progress": conn.execute(
            "SELECT COUNT(*) FROM progress WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_b,),
        ).fetchone()[0],
        "unit_extra": conn.execute(
            "SELECT COUNT(*) FROM unit_extra WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_b,),
        ).fetchone()[0],
        "unit_extra_values": conn.execute(
            "SELECT COUNT(*) FROM unit_extra_values WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_b,),
        ).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_b,)).fetchone()[0],
    }
add_unit_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": f"add_unit:{floor_b}", f"new_unit_name_{floor_b}": "Should Not Add"},
    follow_redirects=False,
)
if add_unit_cross.status_code != 302 or "/admin/table?sheet_id=" not in add_unit_cross.headers.get("Location", ""):
    raise SystemExit("add_unit cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_cross = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE floor_id = ?", (floor_b,)).fetchone()[0],
        "progress": conn.execute(
            "SELECT COUNT(*) FROM progress WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_b,),
        ).fetchone()[0],
        "unit_extra": conn.execute(
            "SELECT COUNT(*) FROM unit_extra WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_b,),
        ).fetchone()[0],
        "unit_extra_values": conn.execute(
            "SELECT COUNT(*) FROM unit_extra_values WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)",
            (floor_b,),
        ).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_b,)).fetchone()[0],
    }
    unexpected_unit = conn.execute(
        "SELECT 1 FROM units WHERE floor_id = ? AND name = ?",
        (floor_b, "Should Not Add"),
    ).fetchone()
if before_cross != after_cross:
    raise SystemExit("add_unit cross-site should not change related rows")
if unexpected_unit is not None:
    raise SystemExit("add_unit cross-site should not create unit row")

set_admin_session()
missing_site_page = client.get(f"/admin/table?sheet_id={sheet_a}")
missing_site_html = missing_site_page.get_data(as_text=True)
if missing_site_page.status_code != 200:
    raise SystemExit("unit admin page should still render without current site")
if 'data-unit-write-enabled="false"' not in missing_site_html:
    raise SystemExit("unit admin page should disable writes when current site is missing")
if 'data-unit-write-block-reason="missing_current_site"' not in missing_site_html:
    raise SystemExit("unit admin page should mark missing current-site block reason")
if 'data-unit-write-blocked="true"' not in missing_site_html:
    raise SystemExit("unit admin page should show blocked-state helper message")

delete_unit_id = int(added_unit["id"])
set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_delete = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE id = ?", (delete_unit_id,)).fetchone()[0],
        "progress": conn.execute("SELECT COUNT(*) FROM progress WHERE unit_id = ?", (delete_unit_id,)).fetchone()[0],
        "unit_extra": conn.execute("SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?", (delete_unit_id,)).fetchone()[0],
        "unit_extra_values": conn.execute("SELECT COUNT(*) FROM unit_extra_values WHERE unit_id = ?", (delete_unit_id,)).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_a,)).fetchone()[0],
    }
delete_unit_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"delete_unit:{delete_unit_id}"},
    follow_redirects=False,
)
if delete_unit_ok.status_code != 302:
    raise SystemExit("delete_unit current site should redirect")
with module.db() as conn:
    after_delete = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE id = ?", (delete_unit_id,)).fetchone()[0],
        "progress": conn.execute("SELECT COUNT(*) FROM progress WHERE unit_id = ?", (delete_unit_id,)).fetchone()[0],
        "unit_extra": conn.execute("SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?", (delete_unit_id,)).fetchone()[0],
        "unit_extra_values": conn.execute("SELECT COUNT(*) FROM unit_extra_values WHERE unit_id = ?", (delete_unit_id,)).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_a,)).fetchone()[0],
    }
if before_delete["units"] != 1:
    raise SystemExit("delete_unit current site precondition failed")
if after_delete["units"] != 0 or after_delete["progress"] != 0 or after_delete["unit_extra"] != 0 or after_delete["unit_extra_values"] != 0:
    raise SystemExit("delete_unit current site should remove unit and related rows")
if after_delete["unit_count"] != before_delete["unit_count"] - 1:
    raise SystemExit("delete_unit current site should decrement unit_count")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_cross_delete = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE id = ?", (unit_b,)).fetchone()[0],
        "progress": conn.execute("SELECT COUNT(*) FROM progress WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra": conn.execute("SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra_values": conn.execute("SELECT COUNT(*) FROM unit_extra_values WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_b,)).fetchone()[0],
    }
delete_unit_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": f"delete_unit:{unit_b}"},
    follow_redirects=False,
)
if delete_unit_cross.status_code != 302 or "/admin/table?sheet_id=" not in delete_unit_cross.headers.get("Location", ""):
    raise SystemExit("delete_unit cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_cross_delete = {
        "units": conn.execute("SELECT COUNT(*) FROM units WHERE id = ?", (unit_b,)).fetchone()[0],
        "progress": conn.execute("SELECT COUNT(*) FROM progress WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra": conn.execute("SELECT COUNT(*) FROM unit_extra WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_extra_values": conn.execute("SELECT COUNT(*) FROM unit_extra_values WHERE unit_id = ?", (unit_b,)).fetchone()[0],
        "unit_count": conn.execute("SELECT unit_count FROM floors WHERE id = ?", (floor_b,)).fetchone()[0],
    }
if before_cross_delete != after_cross_delete:
    raise SystemExit("delete_unit cross-site should not change related rows")

print("admin current-site unit write smoke PASS")
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
    if "admin current-site unit write smoke PASS" not in result.stdout:
        raise AssertionError("admin current-site unit write smoke subprocess did not report PASS.")


def run_admin_current_site_extra_field_write_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing")
    site_b = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__admin_extra_field_site_b__", "extra-field-site-b"),
    ).fetchone()["id"]
    sheet_a = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()["id"]
    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Extra Field Sheet B", 930, site_b),
    ).fetchone()["id"]
    field_a = conn.execute(
        '''
        INSERT INTO extra_fields
        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
        RETURNING id
        ''',
        (sheet_a, "custom_field_a", "Field A", "text", 931),
    ).fetchone()["id"]
    field_b = conn.execute(
        '''
        INSERT INTO extra_fields
        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
        RETURNING id
        ''',
        (sheet_b, "custom_field_b", "Field B", "text", 932),
    ).fetchone()["id"]
    conn.commit()

client = module.app.test_client()

def set_admin_session(*, current_site_id=None, current_site_name=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = current_site_name or f"site-{current_site_id}"
            session["site_selection_required"] = False

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_count = conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
add_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": "add_extra_field", "new_extra_name": "Extra A", "new_extra_type": "text"},
    follow_redirects=False,
)
if add_ok.status_code != 302:
    raise SystemExit("add_extra_field current site should redirect")
with module.db() as conn:
    after_count = conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
    added_row = conn.execute(
        "SELECT sheet_id, active FROM extra_fields WHERE sheet_id = ? AND name = ? ORDER BY id DESC LIMIT 1",
        (sheet_a, "Extra A"),
    ).fetchone()
if after_count != before_count + 1:
    raise SystemExit("add_extra_field current site should add one row")
if added_row is None or int(added_row["sheet_id"]) != int(sheet_a) or int(added_row["active"]) != 1:
    raise SystemExit("add_extra_field current site should create an active row on current site sheet")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_cross = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_b,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_b,)).fetchone()[0],
    }
add_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": "add_extra_field", "new_extra_name": "Should Not Add", "new_extra_type": "text"},
    follow_redirects=False,
)
if add_cross.status_code != 302 or "/admin/table?sheet_id=" not in add_cross.headers.get("Location", ""):
    raise SystemExit("add_extra_field cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_cross = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_b,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_b,)).fetchone()[0],
    }
    unexpected_row = conn.execute(
        "SELECT 1 FROM extra_fields WHERE sheet_id = ? AND name = ?",
        (sheet_b, "Should Not Add"),
    ).fetchone()
if before_cross != after_cross:
    raise SystemExit("add_extra_field cross-site should not change rows")
if unexpected_row is not None:
    raise SystemExit("add_extra_field cross-site should not create a row")

set_admin_session()
missing_site_page = client.get(f"/admin/table?sheet_id={sheet_a}")
missing_site_html = missing_site_page.get_data(as_text=True)
if missing_site_page.status_code != 200:
    raise SystemExit("extra field admin page should still render without current site")
if 'data-extra-field-write-enabled="false"' not in missing_site_html:
    raise SystemExit("extra field admin page should disable writes when current site is missing")
if 'data-extra-field-write-block-reason="missing_current_site"' not in missing_site_html:
    raise SystemExit("extra field admin page should mark missing current-site block reason")
if 'data-extra-field-write-blocked="true"' not in missing_site_html:
    raise SystemExit("extra field admin page should show blocked-state helper message")
with module.db() as conn:
    before_missing = conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
add_missing = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": "add_extra_field", "new_extra_name": "Should Not Exist Missing Site", "new_extra_type": "text"},
    follow_redirects=False,
)
if add_missing.status_code != 302 or not add_missing.headers.get("Location", "").endswith("/site-selector"):
    raise SystemExit("add_extra_field missing current site should redirect to /site-selector")
with module.db() as conn:
    after_missing = conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_a,)).fetchone()[0]
    missing_row = conn.execute(
        "SELECT 1 FROM extra_fields WHERE sheet_id = ? AND name = ?",
        (sheet_a, "Should Not Exist Missing Site"),
    ).fetchone()
if before_missing != after_missing:
    raise SystemExit("add_extra_field missing current site should not change rows")
if missing_row is not None:
    raise SystemExit("add_extra_field missing current site should not create a row")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_delete_active = conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_a,)).fetchone()[0]
delete_ok = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"delete_extra_field:{field_a}"},
    follow_redirects=False,
)
if delete_ok.status_code != 302:
    raise SystemExit("delete_extra_field current site should redirect")
with module.db() as conn:
    after_delete_active = conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_a,)).fetchone()[0]
if int(before_delete_active) != 1 or int(after_delete_active) != 0:
    raise SystemExit("delete_extra_field current site should soft delete the row")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_delete_cross = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_b,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_b,)).fetchone()[0],
    }
delete_cross = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={"action": f"delete_extra_field:{field_b}"},
    follow_redirects=False,
)
if delete_cross.status_code != 302 or "/admin/table?sheet_id=" not in delete_cross.headers.get("Location", ""):
    raise SystemExit("delete_extra_field cross-site should redirect back to /admin/table")
with module.db() as conn:
    after_delete_cross = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_b,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_b,)).fetchone()[0],
    }
if before_delete_cross != after_delete_cross:
    raise SystemExit("delete_extra_field cross-site should not change rows")

set_admin_session()
with module.db() as conn:
    before_delete_missing = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_a,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_a,)).fetchone()[0],
    }
delete_missing = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"delete_extra_field:{field_a}"},
    follow_redirects=False,
)
if delete_missing.status_code != 302 or not delete_missing.headers.get("Location", "").endswith("/site-selector"):
    raise SystemExit("delete_extra_field missing current site should redirect to /site-selector")
with module.db() as conn:
    after_delete_missing = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_a,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_a,)).fetchone()[0],
    }
if before_delete_missing != after_delete_missing:
    raise SystemExit("delete_extra_field missing current site should not change rows")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
with module.db() as conn:
    before_mismatch = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_b,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_b,)).fetchone()[0],
    }
delete_mismatch = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={"action": f"delete_extra_field:{field_b}"},
    follow_redirects=False,
)
if delete_mismatch.status_code != 302 or "/admin/table?sheet_id=" not in delete_mismatch.headers.get("Location", ""):
    raise SystemExit("delete_extra_field mismatch should redirect back to /admin/table")
with module.db() as conn:
    after_mismatch = {
        "count": conn.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id = ?", (sheet_b,)).fetchone()[0],
        "active": conn.execute("SELECT active FROM extra_fields WHERE id = ?", (field_b,)).fetchone()[0],
    }
if before_mismatch != after_mismatch:
    raise SystemExit("delete_extra_field mismatch should not change rows")

print("admin current-site extra-field write smoke PASS")
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
    if "admin current-site extra-field write smoke PASS" not in result.stdout:
        raise AssertionError("admin current-site extra-field write smoke subprocess did not report PASS.")


def run_admin_save_internal_split_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing")
    site_b = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__admin_save_site_b__", "save-site-b"),
    ).fetchone()["id"]
    sheet_a = conn.execute("SELECT id FROM sheets ORDER BY id LIMIT 1").fetchone()["id"]
    task_a = conn.execute(
        "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (sheet_a, 940, "Vendor A", "Location A", "Task A"),
    ).fetchone()["id"]
    floor_a = conn.execute(
        "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 1) RETURNING id",
        (sheet_a, 941, "1F", "A"),
    ).fetchone()["id"]
    unit_a = conn.execute(
        "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?) RETURNING id",
        (floor_a, 1, "A101"),
    ).fetchone()["id"]
    field_a = conn.execute(
        '''
        INSERT INTO extra_fields
        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
        RETURNING id
        ''',
        (sheet_a, "custom_save_a", "Field Save A", "text", 942),
    ).fetchone()["id"]

    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Save Sheet B", 943, site_b),
    ).fetchone()["id"]
    task_b = conn.execute(
        "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (sheet_b, 944, "Vendor B", "Location B", "Task B"),
    ).fetchone()["id"]
    floor_b = conn.execute(
        "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 1) RETURNING id",
        (sheet_b, 945, "2F", "B"),
    ).fetchone()["id"]
    unit_b = conn.execute(
        "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?) RETURNING id",
        (floor_b, 1, "B201"),
    ).fetchone()["id"]
    field_b = conn.execute(
        '''
        INSERT INTO extra_fields
        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
        RETURNING id
        ''',
        (sheet_b, "custom_save_b", "Field Save B", "text", 946),
    ).fetchone()["id"]
    conn.commit()

client = module.app.test_client()

def set_admin_session(*, current_site_id=None, current_site_name=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = current_site_name or f"site-{current_site_id}"
            session["site_selection_required"] = False

def snapshot(sheet_id, task_id, field_id, floor_id, unit_id):
    with module.db() as conn:
        return {
            "meta_site_title": conn.execute("SELECT value FROM meta WHERE key = 'site_title'").fetchone()["value"],
            "sheet_name": conn.execute("SELECT name FROM sheets WHERE id = ?", (sheet_id,)).fetchone()["name"],
            "task": dict(conn.execute("SELECT vendor, location, name FROM tasks WHERE id = ?", (task_id,)).fetchone()),
            "field": dict(conn.execute("SELECT name, field_type, active FROM extra_fields WHERE id = ?", (field_id,)).fetchone()),
            "floor": dict(conn.execute("SELECT name, block_name FROM floors WHERE id = ?", (floor_id,)).fetchone()),
            "unit": dict(conn.execute("SELECT name FROM units WHERE id = ?", (unit_id,)).fetchone()),
        }

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
global_only = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={
        "action": "save",
        "site_title": "Global Only Title",
        "sheet_name": "Sheet A Original",
        f"task_vendor_{task_a}": "Vendor A",
        f"task_location_{task_a}": "Location A",
        f"task_name_{task_a}": "Task A",
        f"extra_name_{field_a}": "Field Save A",
        f"extra_type_{field_a}": "text",
        f"floor_name_{floor_a}": "1F",
        f"floor_block_{floor_a}": "A",
        f"unit_name_{unit_a}": "A101",
    },
    follow_redirects=False,
)
if global_only.status_code != 302:
    raise SystemExit("save global-only with valid current site should redirect")
snap_after_global = snapshot(sheet_a, task_a, field_a, floor_a, unit_a)
if snap_after_global["meta_site_title"] != "Global Only Title":
    raise SystemExit("save global-only should update meta")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
site_only = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={
        "action": "save",
        "site_title": "Global Only Title",
        "sheet_name": "Sheet A Site Save",
        f"task_vendor_{task_a}": "Vendor A Updated",
        f"task_location_{task_a}": "Location A Updated",
        f"task_name_{task_a}": "Task A Updated",
        f"extra_name_{field_a}": "Field Save A Updated",
        f"extra_type_{field_a}": "date",
        f"floor_name_{floor_a}": "1F Updated",
        f"floor_block_{floor_a}": "A2",
        f"unit_name_{unit_a}": "A102",
    },
    follow_redirects=False,
)
if site_only.status_code != 302:
    raise SystemExit("save current-site site content should redirect")
snap_after_site = snapshot(sheet_a, task_a, field_a, floor_a, unit_a)
if snap_after_site["sheet_name"] != "Sheet A Site Save":
    raise SystemExit("save current-site site content should update sheet")
if snap_after_site["task"]["vendor"] != "Vendor A Updated" or snap_after_site["task"]["name"] != "Task A Updated":
    raise SystemExit("save current-site site content should update task")
if snap_after_site["field"]["name"] != "Field Save A Updated" or snap_after_site["field"]["field_type"] != "date":
    raise SystemExit("save current-site site content should update extra field")
if snap_after_site["floor"]["name"] != "1F Updated" or snap_after_site["floor"]["block_name"] != "A2":
    raise SystemExit("save current-site site content should update floor")
if snap_after_site["unit"]["name"] != "A102":
    raise SystemExit("save current-site site content should update unit")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
mixed = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={
        "action": "save",
        "site_title": "Mixed Title",
        "sheet_name": "Sheet A Mixed Save",
        f"task_vendor_{task_a}": "Vendor A Mixed",
        f"task_location_{task_a}": "Location A Mixed",
        f"task_name_{task_a}": "Task A Mixed",
        f"extra_name_{field_a}": "Field Save Mixed",
        f"extra_type_{field_a}": "status",
        f"floor_name_{floor_a}": "1F Mixed",
        f"floor_block_{floor_a}": "A3",
        f"unit_name_{unit_a}": "A103",
    },
    follow_redirects=False,
)
if mixed.status_code != 302:
    raise SystemExit("save mixed payload with valid current site should redirect")
snap_after_mixed = snapshot(sheet_a, task_a, field_a, floor_a, unit_a)
if snap_after_mixed["meta_site_title"] != "Mixed Title":
    raise SystemExit("save mixed payload should update meta")
if snap_after_mixed["sheet_name"] != "Sheet A Mixed Save":
    raise SystemExit("save mixed payload should update site content")

set_admin_session(current_site_id=site_a, current_site_name=module.DEFAULT_SITE_NAME)
before_cross = snapshot(sheet_b, task_b, field_b, floor_b, unit_b)
cross_site = client.post(
    f"/admin/table?sheet_id={sheet_b}",
    data={
        "action": "save",
        "site_title": "Should Not Change Cross Site",
        "sheet_name": "Blocked Cross Sheet",
        f"task_vendor_{task_b}": "Blocked Vendor",
        f"task_location_{task_b}": "Blocked Location",
        f"task_name_{task_b}": "Blocked Task",
        f"extra_name_{field_b}": "Blocked Field",
        f"extra_type_{field_b}": "status",
        f"floor_name_{floor_b}": "Blocked Floor",
        f"floor_block_{floor_b}": "Blocked Block",
        f"unit_name_{unit_b}": "Blocked Unit",
    },
    follow_redirects=False,
)
if cross_site.status_code != 302 or "/admin/table?sheet_id=" not in cross_site.headers.get("Location", ""):
    raise SystemExit("save cross-site should redirect back to /admin/table")
after_cross = snapshot(sheet_b, task_b, field_b, floor_b, unit_b)
if before_cross != after_cross:
    raise SystemExit("save cross-site reject should not change meta or site content for target sheet")
with module.db() as conn:
    current_meta = conn.execute("SELECT value FROM meta WHERE key = 'site_title'").fetchone()["value"]
if current_meta != "Mixed Title":
    raise SystemExit("save cross-site reject must not update meta")

set_admin_session()
before_missing = snapshot(sheet_a, task_a, field_a, floor_a, unit_a)
missing_site = client.post(
    f"/admin/table?sheet_id={sheet_a}",
    data={
        "action": "save",
        "site_title": "Should Not Change Missing Site",
        "sheet_name": "Blocked Missing Site",
        f"task_vendor_{task_a}": "Blocked Missing Vendor",
        f"task_location_{task_a}": "Blocked Missing Location",
        f"task_name_{task_a}": "Blocked Missing Task",
        f"extra_name_{field_a}": "Blocked Missing Field",
        f"extra_type_{field_a}": "status",
        f"floor_name_{floor_a}": "Blocked Missing Floor",
        f"floor_block_{floor_a}": "Blocked Missing Block",
        f"unit_name_{unit_a}": "Blocked Missing Unit",
    },
    follow_redirects=False,
)
if missing_site.status_code != 302:
    raise SystemExit("save missing current site should redirect")
after_missing = snapshot(sheet_a, task_a, field_a, floor_a, unit_a)
if before_missing != after_missing:
    raise SystemExit("save missing current site reject should not change site content")
with module.db() as conn:
    current_meta_after_missing = conn.execute("SELECT value FROM meta WHERE key = 'site_title'").fetchone()["value"]
if current_meta_after_missing != "Mixed Title":
    raise SystemExit("save missing current site reject must not update meta")

print("admin save internal split smoke PASS")
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
    if "admin save internal split smoke PASS" not in result.stdout:
        raise AssertionError("admin save internal split smoke subprocess did not report PASS.")


def run_handover_reset_separation_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

progress_spec = importlib.util.spec_from_file_location(
    "progress_service_under_test",
    str(Path(root_dir) / "services" / "progress_service.py"),
)
progress_module = importlib.util.module_from_spec(progress_spec)
progress_spec.loader.exec_module(progress_module)
client = module.app.test_client()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    site_a = module.get_default_site_id(conn)
    if site_a is None:
        raise SystemExit("default site missing for reset-sheet smoke")
    site_b = conn.execute(
        "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
        ("__reset_sheet_site_b__", "reset-sheet-site-b"),
    ).fetchone()["id"]
    target_unit = conn.execute(
        "SELECT u.id AS unit_id, f.sheet_id "
        "FROM units u "
        "JOIN floors f ON f.id = u.floor_id "
        "ORDER BY u.id "
        "LIMIT 1"
    ).fetchone()
    if target_unit is None:
        raise SystemExit("expected at least one unit for handover/reset smoke")
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = 1",
        (generate_password_hash("admin"),),
    )
    conn.execute(
        "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
        (target_unit["unit_id"], "X"),
    )
    conn.execute(
        '''
        UPDATE unit_extra
        SET initial_check = ?, recheck_1 = ?, recheck_2 = ?, handover = ?, updated_by = 1, updated_at = CURRENT_TIMESTAMP
        WHERE unit_id = ?
        ''',
        ("2026-06-20", "2026-06-21", "2026-06-22", "X", target_unit["unit_id"]),
    )
    field_key_a = "reset_field_a"
    conn.execute(
        '''
        INSERT INTO extra_fields
        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
        ''',
        (target_unit["sheet_id"], field_key_a, "Reset Field A", "text", 950),
    )
    conn.execute(
        '''
        INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''',
        (target_unit["unit_id"], field_key_a, "value-a"),
    )

    sheet_b = conn.execute(
        "INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?) RETURNING id",
        ("Reset Sheet B", 951, site_b),
    ).fetchone()["id"]
    task_b = conn.execute(
        "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (sheet_b, 952, "Vendor B", "Location B", "Task B"),
    ).fetchone()["id"]
    floor_b = conn.execute(
        "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 1) RETURNING id",
        (sheet_b, 953, "B1", "B"),
    ).fetchone()["id"]
    unit_b = conn.execute(
        "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?) RETURNING id",
        (floor_b, 1, "B101"),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at) VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
        (unit_b, task_b, "O"),
    )
    conn.execute(
        '''
        INSERT INTO unit_extra (unit_id, initial_check, recheck_1, recheck_2, handover, updated_by, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''',
        (unit_b, "2026-06-23", "2026-06-24", "2026-06-25", "O"),
    )
    field_key_b = "reset_field_b"
    conn.execute(
        '''
        INSERT INTO extra_fields
        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
        VALUES (?, ?, ?, ?, ?, 0, 1)
        ''',
        (sheet_b, field_key_b, "Reset Field B", "text", 954),
    )
    conn.execute(
        '''
        INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''',
        (unit_b, field_key_b, "value-b"),
    )
    conn.commit()

def set_admin_session(*, current_site_id=None, sheet_id=None):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"
        if current_site_id is not None:
            session["current_site_id"] = int(current_site_id)
            session["current_site_name"] = f"site-{current_site_id}"
            session["site_selection_required"] = False
        if sheet_id is not None:
            session["sheet_id"] = int(sheet_id)

def snapshot_reset_state(sheet_id, unit_id, field_key):
    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        progress_rows = [
            dict(row)
            for row in conn.execute(
                "SELECT unit_id, task_id, value FROM progress WHERE task_id IN (SELECT id FROM tasks WHERE sheet_id = ?) ORDER BY unit_id, task_id",
                (sheet_id,),
            ).fetchall()
        ]
        unit_extra_rows = [
            dict(row)
            for row in conn.execute(
                "SELECT unit_id, initial_check, recheck_1, recheck_2, handover FROM unit_extra WHERE unit_id IN (SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?) ORDER BY unit_id",
                (sheet_id,),
            ).fetchall()
        ]
        unit_extra_value_rows = [
            dict(row)
            for row in conn.execute(
                '''
                SELECT unit_id, field_key, value
                FROM unit_extra_values
                WHERE unit_id IN (
                    SELECT u.id
                    FROM units u
                    JOIN floors f ON f.id = u.floor_id
                    WHERE f.sheet_id = ?
                )
                ORDER BY unit_id, field_key
                ''',
                (sheet_id,),
            ).fetchall()
        ]
        reset_row = conn.execute(
            "SELECT initial_check, recheck_1, recheck_2, handover FROM unit_extra WHERE unit_id = ?",
            (unit_id,),
        ).fetchone()
        field_rows = conn.execute(
            "SELECT field_key FROM extra_fields WHERE sheet_id = ? ORDER BY field_key",
            (sheet_id,),
        ).fetchall()
        return {
            "progress_rows": progress_rows,
            "unit_extra_rows": unit_extra_rows,
            "unit_extra_value_rows": unit_extra_value_rows,
            "reset_row": dict(reset_row) if reset_row else None,
            "field_keys": [row["field_key"] for row in field_rows],
            "field_key_present": any(row["field_key"] == field_key for row in field_rows),
        }

result = progress_module.update_unit_extra(
    unit_id=target_unit["unit_id"],
    field="handover",
    value="O",
    user_id=1,
    fallback_sheet_id=target_unit["sheet_id"],
)
if not result["ok"]:
    raise SystemExit("handover single-cell update should succeed")
with module.db() as conn:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT initial_check, recheck_1, recheck_2, handover FROM unit_extra WHERE unit_id = ?",
        (target_unit["unit_id"],),
    ).fetchone()
if row["initial_check"] != "2026-06-20" or row["recheck_1"] != "2026-06-21" or row["recheck_2"] != "2026-06-22":
    raise SystemExit("handover single-cell update should not clear date fields")
if row["handover"] != "O":
    raise SystemExit("handover single-cell update should store O")

reset_result = progress_module.reset_sheet(sheet_id=target_unit["sheet_id"], user_id=1, password="admin")
if not reset_result["ok"]:
    raise SystemExit("reset_sheet should succeed with valid password")
with module.db() as conn:
    conn.row_factory = sqlite3.Row
    reset_row = conn.execute(
        "SELECT initial_check, recheck_1, recheck_2, handover FROM unit_extra WHERE unit_id = ?",
        (target_unit["unit_id"],),
    ).fetchone()
if reset_row["initial_check"] != "" or reset_row["recheck_1"] != "" or reset_row["recheck_2"] != "":
    raise SystemExit("reset_sheet should clear date fields")
if reset_row["handover"] != "X":
    raise SystemExit("reset_sheet should reset handover to X")

with module.db() as conn:
    conn.execute("UPDATE progress SET value = ?, updated_by = 1, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?", ("O", task_b))
    conn.execute(
        '''
        UPDATE unit_extra
        SET initial_check = ?, recheck_1 = ?, recheck_2 = ?, handover = ?, updated_by = 1, updated_at = CURRENT_TIMESTAMP
        WHERE unit_id = ?
        ''',
        ("2026-06-23", "2026-06-24", "2026-06-25", "O", unit_b),
    )
    conn.execute(
        "UPDATE unit_extra_values SET value = ?, updated_by = 1, updated_at = CURRENT_TIMESTAMP WHERE unit_id = ? AND field_key = ?",
        ("value-b", unit_b, field_key_b),
    )
    conn.commit()

set_admin_session(current_site_id=site_a, sheet_id=target_unit["sheet_id"])
same_site_reset = client.post("/api/reset-sheet", json={"sheet_id": target_unit["sheet_id"], "password": "admin"})
if same_site_reset.status_code != 200:
    raise SystemExit("reset current-site sheet should succeed")
after_same_site = snapshot_reset_state(target_unit["sheet_id"], target_unit["unit_id"], field_key_a)
if any(row["value"] != "X" for row in after_same_site["progress_rows"]):
    raise SystemExit("reset current-site sheet should reset progress")
if after_same_site["reset_row"]["initial_check"] != "" or after_same_site["reset_row"]["recheck_1"] != "" or after_same_site["reset_row"]["recheck_2"] != "":
    raise SystemExit("reset current-site sheet should clear unit_extra dates")
if after_same_site["reset_row"]["handover"] != "X":
    raise SystemExit("reset current-site sheet should reset handover to X")
if after_same_site["unit_extra_value_rows"]:
    raise SystemExit("reset current-site sheet should clear unit_extra_values for target sheet")

before_cross_site = snapshot_reset_state(sheet_b, unit_b, field_key_b)
set_admin_session(current_site_id=site_a, sheet_id=target_unit["sheet_id"])
cross_site_reset = client.post("/api/reset-sheet", json={"sheet_id": sheet_b, "password": "admin"})
if cross_site_reset.status_code != 403:
    raise SystemExit("reset cross-site sheet should be rejected")
if cross_site_reset.get_json()["ok"] is not False:
    raise SystemExit("reset cross-site sheet should return ok=false")
after_cross_site = snapshot_reset_state(sheet_b, unit_b, field_key_b)
if before_cross_site != after_cross_site:
    raise SystemExit("reset cross-site sheet reject should not change DB state")

before_missing_site = snapshot_reset_state(target_unit["sheet_id"], target_unit["unit_id"], field_key_a)
set_admin_session(sheet_id=target_unit["sheet_id"])
missing_site_reset = client.post("/api/reset-sheet", json={"sheet_id": target_unit["sheet_id"], "password": "admin"})
if missing_site_reset.status_code != 403:
    raise SystemExit("reset missing current site should be rejected")
after_missing_site = snapshot_reset_state(target_unit["sheet_id"], target_unit["unit_id"], field_key_a)
if before_missing_site != after_missing_site:
    raise SystemExit("reset missing current site reject should not change DB state")

before_invalid_sheet = snapshot_reset_state(target_unit["sheet_id"], target_unit["unit_id"], field_key_a)
set_admin_session(current_site_id=site_a, sheet_id=target_unit["sheet_id"])
invalid_sheet_reset = client.post("/api/reset-sheet", json={"sheet_id": 999999, "password": "admin"})
if invalid_sheet_reset.status_code != 404:
    raise SystemExit("reset invalid sheet should return 404")
after_invalid_sheet = snapshot_reset_state(target_unit["sheet_id"], target_unit["unit_id"], field_key_a)
if before_invalid_sheet != after_invalid_sheet:
    raise SystemExit("reset invalid sheet reject should not change DB state")

before_stale_session = snapshot_reset_state(sheet_b, unit_b, field_key_b)
set_admin_session(current_site_id=site_a, sheet_id=sheet_b)
stale_session_reset = client.post("/api/reset-sheet", json={"password": "admin"})
if stale_session_reset.status_code != 403:
    raise SystemExit("stale session cross-site reset should be rejected")
after_stale_session = snapshot_reset_state(sheet_b, unit_b, field_key_b)
if before_stale_session != after_stale_session:
    raise SystemExit("stale session cross-site reset reject should not change DB state")

print("handover reset separation smoke PASS")
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
    if "handover reset separation smoke PASS" not in result.stdout:
        raise AssertionError("handover reset separation smoke subprocess did not report PASS.")


def run_handover_route_regression_smoke(app_db_path: Path) -> None:
    if app_db_path.exists():
        app_db_path.unlink()
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

app_db_path, root_dir = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = app_db_path
spec.loader.exec_module(module)
module.app.testing = True

template_text = (Path(root_dir) / "templates" / "sheet.html").read_text(encoding="utf-8")
if 'type="datetime-local"' in template_text:
    raise SystemExit("sheet.html should not use datetime-local for extra date fields")
if 'type="date"' not in template_text:
    raise SystemExit("sheet.html should render extra date fields with type=date")

with module.app.test_client() as client:
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        target_unit = conn.execute(
            "SELECT u.id AS unit_id, f.sheet_id "
            "FROM units u "
            "JOIN floors f ON f.id = u.floor_id "
            "ORDER BY u.id "
            "LIMIT 1"
        ).fetchone()
        if target_unit is None:
            raise SystemExit("expected at least one unit for handover route smoke")
        conn.execute(
            "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
            (target_unit["unit_id"], "X"),
        )
        conn.execute(
            '''
            UPDATE unit_extra
            SET initial_check = ?, recheck_1 = ?, recheck_2 = ?, handover = ?, updated_by = 1, updated_at = CURRENT_TIMESTAMP
            WHERE unit_id = ?
            ''',
            ("2026-06-20", "2026-06-21", "2026-06-22", "X", target_unit["unit_id"]),
        )

    response = client.post(
        "/api/unit-extra",
        json={"unit_id": int(target_unit["unit_id"]), "field": "handover", "value": "O"},
    )
    if response.status_code != 200:
        raise SystemExit("/api/unit-extra handover update should succeed")
    data = response.get_json()
    if not data.get("ok"):
        raise SystemExit("/api/unit-extra should report ok=true")

    extra = data["grid"]["extras"][str(target_unit["unit_id"])]
    if extra.get("initial_check") != "2026-06-20":
        raise SystemExit("api/unit-extra should preserve initial_check")
    if extra.get("recheck_1") != "2026-06-21":
        raise SystemExit("api/unit-extra should preserve recheck_1")
    if extra.get("recheck_2") != "2026-06-22":
        raise SystemExit("api/unit-extra should preserve recheck_2")
    if extra.get("handover") != "O":
        raise SystemExit("api/unit-extra should update handover to O")

    extra_summary = data["grid"]["extra_summary"]
    if extra_summary["initial_check"]["done"] < 1:
        raise SystemExit("initial_check summary should count done when recheck_1 exists or handover=O")
    if extra_summary["recheck_1"]["done"] < 1:
        raise SystemExit("recheck_1 summary should count done when recheck_2 exists or handover=O")
    if extra_summary["recheck_2"]["done"] < 1:
        raise SystemExit("recheck_2 summary should count done when recheck_2 exists or handover=O")
    if extra_summary["handover"]["done"] < 1:
        raise SystemExit("handover summary should count done when handover=O")

    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT initial_check, recheck_1, recheck_2, handover FROM unit_extra WHERE unit_id = ?",
            (target_unit["unit_id"],),
        ).fetchone()
    if row["initial_check"] != "2026-06-20" or row["recheck_1"] != "2026-06-21" or row["recheck_2"] != "2026-06-22":
        raise SystemExit("api/unit-extra should not clear persisted date fields")
    if row["handover"] != "O":
        raise SystemExit("api/unit-extra should persist handover=O")

print("handover route regression smoke PASS")
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
    if "handover route regression smoke PASS" not in result.stdout:
        raise AssertionError("handover route regression smoke subprocess did not report PASS.")


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
default_site_id = module.ensure_site_foundation_schema(conn)
conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (2, default_site_id, "member"),
)
deleted_user_row = module.delete_user_sqlite(conn, 2)
conn.commit()
row = conn.execute("SELECT COUNT(*) AS count FROM users WHERE id = 2").fetchone()
permission_row = conn.execute("SELECT COUNT(*) AS count FROM user_site_permissions WHERE user_id = 2").fetchone()
conn.close()
if row["count"] != 0:
    raise SystemExit("user delete helper did not delete the target row")
if permission_row["count"] != 0:
    raise SystemExit("user delete helper did not delete related site permissions")
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
        "- USERS_READ_COMPARE enabled=",
        "- run_users_read_compare_by_username: ",
        "- run_users_read_compare_by_id: ",
        "- run_users_list_compare: ",
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
os.environ["USERS_READ_COMPARE"] = "false"
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
actual_ids = [int(row["id"]) for row in listed_users]
expected_ids = sorted(actual_ids)
if actual_ids != expected_ids:
    raise SystemExit("list_users should return users in id ASC order")
first_payload = dict(listed_users[0])
if "password_hash" in first_payload:
    raise SystemExit("list_users should not expose password_hash")
if not any(row["username"] == "admin" for row in listed_users):
    raise SystemExit("list_users smoke missing admin user")

compare_logs = []
module.dual_write_log = lambda message: compare_logs.append(message)
original_shadow_get_user_by_username = module._shadow_get_user_by_username
original_shadow_get_user_by_id = module._shadow_get_user_by_id
original_shadow_list_users = module._shadow_list_users

module.get_user_by_username("admin")
module.get_user_by_id(1)
module.list_users()
if any("USERS_READ_COMPARE" in message for message in compare_logs):
    raise SystemExit("compare logs should be silent when USERS_READ_COMPARE=false")

module.users_read_compare_enabled = lambda: True
compare_logs.clear()
module.get_user_by_username("admin")
module.get_user_by_id(1)
module.list_users()
expected_compare_snippets = [
    "USERS_READ_COMPARE helper=get_user_by_username key=username:admin status=match",
    "USERS_READ_COMPARE helper=get_user_by_id key=id:1 status=match",
    "USERS_READ_COMPARE helper=list_users status=match",
]
for snippet in expected_compare_snippets:
    if not any(snippet in message for message in compare_logs):
        raise SystemExit(f"missing compare log: {snippet}")
if any("hash$" in message or "hash-created-once" in message for message in compare_logs):
    raise SystemExit("compare logs should not leak password hash values")

class FakeShadowUser:
    id = 1
    username = "admin"
    display_name = "Admin Shadow Drift"
    role = "admin"
    created_at = admin_user["created_at"]
    password_hash = admin_user["password_hash"]

module._shadow_get_user_by_username = lambda username: FakeShadowUser()
compare_logs.clear()
result_user = module.get_user_by_username("admin")
if result_user["display_name"] != admin_user["display_name"]:
    raise SystemExit("compare mismatch should not change primary helper result")
if not any(
    "USERS_READ_COMPARE helper=get_user_by_username key=username:admin status=mismatch fields=display_name"
    in message
    for message in compare_logs
):
    raise SystemExit("compare mismatch log missing for get_user_by_username")

class FakeShadowListUser:
    def __init__(self, user_id, username, display_name, role, created_at):
        self.id = user_id
        self.username = username
        self.display_name = display_name
        self.role = role
        self.created_at = created_at

module._shadow_list_users = lambda: [
    FakeShadowListUser(
        row["id"],
        row["username"],
        "Admin Shadow Drift" if row["id"] == 1 else row["display_name"],
        row["role"],
        row["created_at"],
    )
    for row in listed_users
]
compare_logs.clear()
listed_again = module.list_users()
if listed_again[0]["display_name"] != listed_users[0]["display_name"]:
    raise SystemExit("list_users compare mismatch should not change primary rows")
if not any(
    "USERS_READ_COMPARE helper=list_users status=mismatch row_count_match=true ordered_ids_match=true"
    in message
    for message in compare_logs
):
    raise SystemExit("list_users mismatch summary log missing")
if not any(
    "USERS_READ_COMPARE_DETAIL helper=list_users id=1 status=mismatch fields=display_name"
    in message
    for message in compare_logs
):
    raise SystemExit("list_users mismatch detail log missing")

def _raise_compare_error():
    raise RuntimeError("synthetic compare failure")

module._shadow_get_user_by_id = lambda user_id: _raise_compare_error()
compare_logs.clear()
result_by_id_error = module.get_user_by_id(1)
if result_by_id_error["id"] != admin_by_id["id"]:
    raise SystemExit("compare error should not change primary get_user_by_id result")
expected_id_error_log = (
    "USERS_READ_COMPARE helper=get_user_by_id key=id:1 status=mismatch "
    "fields=compare_error compare_error_class=RuntimeError compare_error_stage=compare"
)
if not any(expected_id_error_log in message for message in compare_logs):
    raise SystemExit("get_user_by_id compare error diagnostic log missing")

module._shadow_list_users = lambda: _raise_compare_error()
compare_logs.clear()
result_list_error = module.list_users()
if len(result_list_error) != len(listed_users):
    raise SystemExit("compare error should not change primary list_users result")
expected_list_error_log = (
    "USERS_READ_COMPARE helper=list_users status=mismatch "
    "row_count_match=unknown ordered_ids_match=unknown "
    "compare_error_class=RuntimeError compare_error_stage=compare"
)
if not any(expected_list_error_log in message for message in compare_logs):
    raise SystemExit("list_users compare error diagnostic log missing")

module._shadow_get_user_by_username = original_shadow_get_user_by_username
module._shadow_get_user_by_id = original_shadow_get_user_by_id
module._shadow_list_users = original_shadow_list_users

with module.app.test_client() as client:
    compare_logs.clear()
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

request_compare_snippets = [
    "USERS_READ_COMPARE helper=get_user_by_username key=username:admin status=match",
    "USERS_READ_COMPARE helper=list_users status=match",
    "USERS_READ_COMPARE helper=get_user_by_id key=id:1 status=match",
]
for snippet in request_compare_snippets:
    if not any(snippet in message for message in compare_logs):
        raise SystemExit(f"request-path compare log missing: {snippet}")
if any("compare_error" in message for message in compare_logs):
    raise SystemExit("request-path compare should not emit compare_error after ORM init fix")
if any("hash$" in message or "hash-created-once" in message for message in compare_logs):
    raise SystemExit("request-path compare logs should not leak password hash values")

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


def run_users_read_compare_readiness_smoke(app_db_path: Path) -> None:
    result = run_script(
        "check_users_read_compare_readiness.py",
        env={"APP_DB_PATH": str(app_db_path), "USERS_READ_COMPARE": "true"},
    )
    output = result.stdout
    if result.returncode != 0:
        raise AssertionError(f"check_users_read_compare_readiness.py failed:\n{output}")
    required_snippets = [
        "USERS_READ_COMPARE: true",
        "sqlite_admin_exists: true",
        "shadow_admin_exists: true",
        "compare get_user_by_username('admin'): status=match fields=none password_hash_match=true",
        "compare get_user_by_id(1): status=match fields=none password_hash_match=true",
        "compare list_users: status=match row_count_match=true ordered_ids_match=true",
        "PASS users read compare readiness check passed.",
    ]
    for snippet in required_snippets:
        if snippet not in output:
            raise AssertionError(
                f"check_users_read_compare_readiness.py missing expected snippet: {snippet}"
            )
    if "password_hash=" in output or "password_hash:" in output:
        raise AssertionError("check_users_read_compare_readiness.py output should not include password_hash values.")


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


def run_user_site_permissions_smoke_guardrail(db_path: Path, app_db_path: Path) -> None:
    script = """
import importlib.util
from pathlib import Path
import sqlite3
import sys

app_db_path, sample_db_path, root_dir = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
import os
os.environ["APP_DB_PATH"] = sample_db_path
spec.loader.exec_module(module)
module.app.testing = True

conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
default_site_id = module.ensure_site_foundation_schema(conn)
secondary_site = conn.execute(
    "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
    ("__perm_secondary__", "perm-secondary"),
).fetchone()["id"]
inactive_site = conn.execute(
    "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 0) RETURNING id",
    ("__perm_inactive__", "perm-inactive"),
).fetchone()["id"]
password_hash = module.generate_password_hash("x")
conn.execute(
    "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
    ("perm_member", "perm_member", password_hash, "member"),
)
conn.execute(
    "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
    ("perm_other", "perm_other", password_hash, "member"),
)
member_id = conn.execute("SELECT id FROM users WHERE username = 'perm_member'").fetchone()["id"]
other_member_id = conn.execute("SELECT id FROM users WHERE username = 'perm_other'").fetchone()["id"]
conn.commit()
conn.close()

with module.app.test_client() as client:
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["display_name"] = "Admin"
        session["role"] = "admin"

    users_page = client.get("/admin/users")
    page = users_page.get_data(as_text=True)
    if users_page.status_code != 200:
        raise SystemExit("/admin/users permission GET smoke failed")
    if "Global Admin（全站可存取）" not in page:
        raise SystemExit("admin compatibility text missing from /admin/users")
    if "新增工地授權" not in page:
        raise SystemExit("site permission add form missing from /admin/users")

    add_response = client.post(
        "/admin/users",
        data={
            "action": f"add_site_permission:{member_id}",
            "site_id": str(secondary_site),
            "site_role": "supervisor",
        },
        follow_redirects=False,
    )
    if add_response.status_code != 302:
        raise SystemExit("add_site_permission request failed")

    conn = sqlite3.connect(sample_db_path)
    conn.row_factory = sqlite3.Row
    permission_row = conn.execute(
        "SELECT id, role FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
        (member_id, secondary_site),
    ).fetchone()
    if permission_row is None or permission_row["role"] != "supervisor":
        raise SystemExit("add_site_permission did not persist expected role")

    client.post(
        "/admin/users",
        data={
            "action": f"add_site_permission:{member_id}",
            "site_id": str(secondary_site),
            "site_role": "member",
        },
        follow_redirects=False,
    )
    duplicate_count = conn.execute(
        "SELECT COUNT(*) AS count FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
        (member_id, secondary_site),
    ).fetchone()["count"]
    if duplicate_count != 1:
        raise SystemExit("duplicate site permission should be prevented")

    client.post(
        "/admin/users",
        data={
            "action": f"update_site_permission:{permission_row['id']}",
            "site_role": "member",
        },
        follow_redirects=False,
    )
    updated_role = conn.execute(
        "SELECT role FROM user_site_permissions WHERE id = ?",
        (permission_row["id"],),
    ).fetchone()["role"]
    if updated_role != "member":
        raise SystemExit("update_site_permission should update role only")

    client.post(
        "/admin/users",
        data={
            "action": f"add_site_permission:{other_member_id}",
            "site_id": str(inactive_site),
            "site_role": "member",
        },
        follow_redirects=False,
    )
    if conn.execute(
        "SELECT 1 FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
        (other_member_id, inactive_site),
    ).fetchone():
        raise SystemExit("inactive site permission should be rejected")

    client.post(
        "/admin/users",
        data={
            "action": f"add_site_permission:{other_member_id}",
            "site_id": str(secondary_site),
            "site_role": "invalid",
        },
        follow_redirects=False,
    )
    if conn.execute(
        "SELECT 1 FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
        (other_member_id, secondary_site),
    ).fetchone():
        raise SystemExit("invalid site role should be rejected")

    client.post(
        "/admin/users",
        data={"action": f"delete_site_permission:{permission_row['id']}"},
        follow_redirects=False,
    )
    if conn.execute("SELECT 1 FROM user_site_permissions WHERE id = ?", (permission_row["id"],)).fetchone():
        raise SystemExit("delete_site_permission should remove row")

    conn.close()

with module.app.test_client() as non_admin_client:
    with non_admin_client.session_transaction() as session:
        session["user_id"] = member_id
        session["username"] = "perm_member"
        session["display_name"] = "perm_member"
        session["role"] = "member"
    forbidden_response = non_admin_client.post(
        "/admin/users",
        data={
            "action": f"add_site_permission:{member_id}",
            "site_id": str(default_site_id),
            "site_role": "member",
        },
        follow_redirects=False,
    )
    if forbidden_response.status_code not in (302, 403):
        raise SystemExit("non-admin should not be able to modify site permissions")

print("user site permissions smoke guardrail PASS")
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
    if "user site permissions smoke guardrail PASS" not in result.stdout:
        raise AssertionError("user site permissions smoke guardrail subprocess did not report PASS.")


def run_site_read_isolation_smoke(db_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "check_site_read_isolation.py"),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "APP_DB_PATH": str(db_path)},
    )
    if "PASS site read isolation check passed." not in result.stdout:
        raise AssertionError("check_site_read_isolation.py smoke subprocess did not report PASS.")


def run_progress_write_isolation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys

sample_db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = sample_db_path
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.ensure_vendor_contacts_schema(conn)
default_site_id = module.ensure_site_foundation_schema(conn)
default_site_name = conn.execute("SELECT site_name FROM sites WHERE id = ?", (default_site_id,)).fetchone()["site_name"]
secondary_site_id = conn.execute(
    "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
    ("__write_iso_secondary__", "write-iso-secondary"),
).fetchone()["id"]
secondary_sheet_id = conn.execute(
    "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
    ("__write_iso_sheet__", 99, secondary_site_id),
).fetchone()["id"]
secondary_floor_id = conn.execute(
    "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, ?)",
    (secondary_sheet_id, 99, "9F", "B", 1),
).lastrowid
secondary_unit_id = conn.execute(
    "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
    (secondary_floor_id, 1, "901"),
).lastrowid
secondary_task_id = conn.execute(
    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
    (secondary_sheet_id, 5, "Vendor B", "Room B", "Task B"),
).lastrowid
conn.execute(
    "INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
    (secondary_unit_id, secondary_task_id, module.WORKING_VALUE, 1),
)
password_hash = module.generate_password_hash("x")
conn.execute(
    "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
    ("write_member", "write_member", password_hash, "member"),
)
member_id = conn.execute("SELECT id FROM users WHERE username = 'write_member'").fetchone()["id"]
conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.commit()

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "write_member"
        session["display_name"] = "write_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

set_member_session()
same_site_response = client.post(
    "/api/progress",
    json={"unit_id": 1, "task_id": 1, "value": module.DONE_VALUE},
)
if same_site_response.status_code != 200:
    raise SystemExit("same-site progress write should succeed")
same_site_value = conn.execute(
    "SELECT value FROM progress WHERE unit_id = 1 AND task_id = 1"
).fetchone()["value"]
if same_site_value != module.DONE_VALUE:
    raise SystemExit("same-site progress write should update progress row")

set_member_session()
cross_site_response = client.post(
    "/api/progress",
    json={"unit_id": int(secondary_unit_id), "task_id": int(secondary_task_id), "value": module.DONE_VALUE},
)
if cross_site_response.status_code != 403:
    raise SystemExit("cross-site progress write should be rejected with 403")
cross_site_value = conn.execute(
    "SELECT value FROM progress WHERE unit_id = ? AND task_id = ?",
    (secondary_unit_id, secondary_task_id),
).fetchone()["value"]
if cross_site_value != module.WORKING_VALUE:
    raise SystemExit("cross-site progress write must not change progress row")

set_member_session(with_current_site=False)
missing_site_response = client.post(
    "/api/progress",
    json={"unit_id": 1, "task_id": 1, "value": module.WORKING_VALUE},
)
if missing_site_response.status_code != 403:
    raise SystemExit("missing current site should be rejected with 403")
missing_site_payload = missing_site_response.get_json()
if missing_site_payload.get("ok") is not False:
    raise SystemExit("missing current site should return ok=false")
if missing_site_payload.get("message") != "current_site_id is missing or invalid.":
    raise SystemExit("missing current site should return deterministic progress error message")

set_member_session()
conn.execute("DELETE FROM user_site_permissions WHERE user_id = ?", (member_id,))
conn.commit()
permission_removed_response = client.post(
    "/api/progress",
    json={"unit_id": 1, "task_id": 1, "value": module.WORKING_VALUE},
)
if permission_removed_response.status_code != 403:
    raise SystemExit("permission removed should be rejected with 403")
post_permission_removed_value = conn.execute(
    "SELECT value FROM progress WHERE unit_id = 1 AND task_id = 1"
).fetchone()["value"]
if post_permission_removed_value != module.DONE_VALUE:
    raise SystemExit("permission-removed progress write must not change stored value")

conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.commit()
set_member_session()
unit_task_mismatch_response = client.post(
    "/api/progress",
    json={"unit_id": 1, "task_id": int(secondary_task_id), "value": module.WORKING_VALUE},
)
if unit_task_mismatch_response.status_code != 409:
    raise SystemExit("unit/task mismatch should be rejected with 409")

conn.close()
print("progress write isolation smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "progress write isolation smoke PASS" not in result.stdout:
        raise AssertionError("progress write isolation smoke subprocess did not report PASS.")


def run_unit_extra_write_isolation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys

sample_db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = sample_db_path
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.ensure_vendor_contacts_schema(conn)
default_site_id = module.ensure_site_foundation_schema(conn)
default_site_name = conn.execute("SELECT site_name FROM sites WHERE id = ?", (default_site_id,)).fetchone()["site_name"]
secondary_site_id = conn.execute(
    "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
    ("__unit_extra_secondary__", "unit-extra-secondary"),
).fetchone()["id"]
secondary_sheet_id = conn.execute(
    "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
    ("__unit_extra_sheet__", 98, secondary_site_id),
).fetchone()["id"]
secondary_floor_id = conn.execute(
    "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, ?)",
    (secondary_sheet_id, 98, "8F", "C", 1),
).lastrowid
secondary_unit_id = conn.execute(
    "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
    (secondary_floor_id, 1, "801"),
).lastrowid
conn.execute(
    '''
    INSERT INTO extra_fields (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''',
    (secondary_sheet_id, "secondary_only_status", "Secondary Only", "status", 10, 0, 1),
)
conn.execute(
    "INSERT INTO unit_extra (unit_id, handover, updated_by, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
    (secondary_unit_id, module.WORKING_VALUE, 1),
)
password_hash = module.generate_password_hash("x")
conn.execute(
    "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
    ("unit_extra_member", "unit_extra_member", password_hash, "member"),
)
member_id = conn.execute("SELECT id FROM users WHERE username = 'unit_extra_member'").fetchone()["id"]
conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.commit()

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "unit_extra_member"
        session["display_name"] = "unit_extra_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

def get_handover(unit_id):
    return conn.execute(
        "SELECT handover FROM unit_extra WHERE unit_id = ?",
        (unit_id,),
    ).fetchone()["handover"]

set_member_session()
same_site_response = client.post(
    "/api/unit-extra",
    json={"unit_id": 1, "field": "handover", "value": module.DONE_VALUE},
)
if same_site_response.status_code != 200:
    raise SystemExit("same-site unit-extra write should succeed")
if get_handover(1) != module.DONE_VALUE:
    raise SystemExit("same-site unit-extra write should update handover")

set_member_session()
cross_site_response = client.post(
    "/api/unit-extra",
    json={"unit_id": int(secondary_unit_id), "field": "secondary_only_status", "value": module.DONE_VALUE},
)
if cross_site_response.status_code != 403:
    raise SystemExit("cross-site unit-extra write should be rejected with 403")
secondary_extra_value = conn.execute(
    "SELECT value FROM unit_extra_values WHERE unit_id = ? AND field_key = ?",
    (secondary_unit_id, "secondary_only_status"),
).fetchone()
if secondary_extra_value is not None:
    raise SystemExit("cross-site unit-extra write must not create unit_extra_values rows")
if get_handover(secondary_unit_id) != module.WORKING_VALUE:
    raise SystemExit("cross-site unit-extra write must not change built-in rows")

set_member_session(with_current_site=False)
missing_site_response = client.post(
    "/api/unit-extra",
    json={"unit_id": 1, "field": "handover", "value": module.WORKING_VALUE},
)
if missing_site_response.status_code != 403:
    raise SystemExit("missing current site should reject unit-extra write with 403")
if get_handover(1) != module.DONE_VALUE:
    raise SystemExit("missing current site must not change existing unit-extra row")

set_member_session()
conn.execute("DELETE FROM user_site_permissions WHERE user_id = ?", (member_id,))
conn.commit()
permission_removed_response = client.post(
    "/api/unit-extra",
    json={"unit_id": 1, "field": "handover", "value": module.WORKING_VALUE},
)
if permission_removed_response.status_code != 403:
    raise SystemExit("permission removed should reject unit-extra write with 403")
if get_handover(1) != module.DONE_VALUE:
    raise SystemExit("permission-removed unit-extra write must not change stored row")

conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.commit()
set_member_session()
unit_field_mismatch_response = client.post(
    "/api/unit-extra",
    json={"unit_id": 1, "field": "secondary_only_status", "value": module.DONE_VALUE},
)
if unit_field_mismatch_response.status_code != 409:
    raise SystemExit("unit/field sheet mismatch should be rejected with 409")
if get_handover(1) != module.DONE_VALUE:
    raise SystemExit("unit/field mismatch must not modify existing unit-extra row")

set_member_session()
invalid_status_value_response = client.post(
    "/api/unit-extra",
    json={"unit_id": 1, "field": "handover", "value": "INVALID"},
)
if invalid_status_value_response.status_code != 400:
    raise SystemExit("invalid status value should be rejected with 400")
if get_handover(1) != module.DONE_VALUE:
    raise SystemExit("invalid status value must not modify existing unit-extra row")

conn.close()
print("unit-extra write isolation smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "unit-extra write isolation smoke PASS" not in result.stdout:
        raise AssertionError("unit-extra write isolation smoke subprocess did not report PASS.")


def run_vendor_contact_write_isolation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys

sample_db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = sample_db_path
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.ensure_vendor_contacts_schema(conn)
default_site_id = module.ensure_site_foundation_schema(conn)
default_site_name = conn.execute("SELECT site_name FROM sites WHERE id = ?", (default_site_id,)).fetchone()["site_name"]
secondary_site_id = conn.execute(
    "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
    ("__vendor_contact_secondary__", "vendor-contact-secondary"),
).fetchone()["id"]
secondary_sheet_id = conn.execute(
    "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
    ("__vendor_contact_sheet__", 97, secondary_site_id),
).fetchone()["id"]
max_col_index = conn.execute("SELECT COALESCE(MAX(col_index), 0) FROM tasks").fetchone()[0]
conn.execute(
    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
    (1, max_col_index + 1, "VendorAllowedDefault", "Room A", "Vendor Default Task"),
)
conn.execute(
    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
    (secondary_sheet_id, max_col_index + 2, "VendorAllowedSecondary", "Room B", "Vendor Secondary Task"),
)
password_hash = module.generate_password_hash("x")
conn.execute(
    "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
    ("vendor_contact_member", "vendor_contact_member", password_hash, "member"),
)
member_id = conn.execute("SELECT id FROM users WHERE username = 'vendor_contact_member'").fetchone()["id"]
conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.execute(
    '''
    INSERT INTO vendor_contacts (
        sheet_id, vendor_name, contact_name, contact_title, contact_phone,
        is_primary, contact_order, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''',
    (1, "VendorAllowedDefault", "Default Contact", "Lead", "0900000001", 1, 0),
)
default_contact_id = conn.execute(
    "SELECT id FROM vendor_contacts WHERE sheet_id = 1 AND vendor_name = ?",
    ("VendorAllowedDefault",),
).fetchone()["id"]
conn.execute(
    '''
    INSERT INTO vendor_contacts (
        sheet_id, vendor_name, contact_name, contact_title, contact_phone,
        is_primary, contact_order, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''',
    (secondary_sheet_id, "VendorAllowedSecondary", "Secondary Contact", "Lead", "0900000002", 1, 0),
)
secondary_contact_id = conn.execute(
    "SELECT id FROM vendor_contacts WHERE sheet_id = ? AND vendor_name = ?",
    (secondary_sheet_id, "VendorAllowedSecondary"),
).fetchone()["id"]
conn.commit()

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "vendor_contact_member"
        session["display_name"] = "vendor_contact_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

def count_contacts(sheet_id, vendor_name):
    return conn.execute(
        "SELECT COUNT(*) FROM vendor_contacts WHERE sheet_id = ? AND vendor_name = ?",
        (sheet_id, vendor_name),
    ).fetchone()[0]

def fetch_contact(contact_id):
    return conn.execute(
        "SELECT vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order FROM vendor_contacts WHERE id = ?",
        (contact_id,),
    ).fetchone()

set_member_session()
same_site_create = client.post(
    "/api/vendor-contact",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefault",
        "contact_name": "Create Contact",
        "contact_title": "Supervisor",
        "contact_phone": "0900000010",
        "is_primary": 0,
    },
)
if same_site_create.status_code != 200 or not same_site_create.get_json().get("ok"):
    raise SystemExit("same-site vendor-contact create should succeed")
if count_contacts(1, "VendorAllowedDefault") != 2:
    raise SystemExit("same-site vendor-contact create should insert a new row")

set_member_session()
same_site_update = client.post(
    "/api/vendor-contact",
    json={
        "id": int(default_contact_id),
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefault",
        "contact_name": "Updated Contact",
        "contact_title": "Coordinator",
        "contact_phone": "0900000011",
        "is_primary": 1,
        "contact_order": 0,
    },
)
if same_site_update.status_code != 200 or not same_site_update.get_json().get("ok"):
    raise SystemExit("same-site vendor-contact update should succeed")
updated_default = fetch_contact(default_contact_id)
if updated_default["contact_name"] != "Updated Contact" or updated_default["contact_title"] != "Coordinator":
    raise SystemExit("same-site vendor-contact update should persist updated values")

set_member_session()
before_cross_site_create = count_contacts(secondary_sheet_id, "VendorAllowedSecondary")
cross_site_create = client.post(
    "/api/vendor-contact",
    json={
        "sheet_id": int(secondary_sheet_id),
        "vendor_name": "VendorAllowedSecondary",
        "contact_name": "Cross Site Create",
        "contact_title": "",
        "contact_phone": "0900000099",
        "is_primary": 0,
    },
)
if cross_site_create.status_code != 403:
    raise SystemExit("cross-site vendor-contact create should be rejected with 403")
if count_contacts(secondary_sheet_id, "VendorAllowedSecondary") != before_cross_site_create:
    raise SystemExit("cross-site vendor-contact create must not change row count")

set_member_session()
before_cross_site_update = dict(fetch_contact(secondary_contact_id))
cross_site_update = client.post(
    "/api/vendor-contact",
    json={
        "id": int(secondary_contact_id),
        "sheet_id": int(secondary_sheet_id),
        "vendor_name": "VendorAllowedSecondary",
        "contact_name": "Cross Site Update",
        "contact_title": "Blocked",
        "contact_phone": "0900000022",
        "is_primary": 1,
        "contact_order": 0,
    },
)
if cross_site_update.status_code != 403:
    raise SystemExit("cross-site vendor-contact update should be rejected with 403")
after_cross_site_update = dict(fetch_contact(secondary_contact_id))
if after_cross_site_update != before_cross_site_update:
    raise SystemExit("cross-site vendor-contact update must not modify stored row")

set_member_session(with_current_site=False)
before_missing_site = count_contacts(1, "VendorAllowedDefault")
missing_site = client.post(
    "/api/vendor-contact",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefault",
        "contact_name": "Missing Site",
        "contact_title": "",
        "contact_phone": "0900000012",
        "is_primary": 0,
    },
)
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject vendor-contact write with 403")
if count_contacts(1, "VendorAllowedDefault") != before_missing_site:
    raise SystemExit("missing current site must not change contact rows")

set_member_session()
conn.execute("DELETE FROM user_site_permissions WHERE user_id = ?", (member_id,))
conn.commit()
before_permission_removed = count_contacts(1, "VendorAllowedDefault")
permission_removed = client.post(
    "/api/vendor-contact",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefault",
        "contact_name": "Permission Removed",
        "contact_title": "",
        "contact_phone": "0900000013",
        "is_primary": 0,
    },
)
if permission_removed.status_code != 403:
    raise SystemExit("permission removed should reject vendor-contact write with 403")
if count_contacts(1, "VendorAllowedDefault") != before_permission_removed:
    raise SystemExit("permission removed must not change contact rows")

conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.commit()
set_member_session()
before_vendor_not_in_sheet = count_contacts(1, "VendorAllowedDefault")
vendor_not_in_sheet = client.post(
    "/api/vendor-contact",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorMissing",
        "contact_name": "Unknown Vendor",
        "contact_title": "",
        "contact_phone": "0900000014",
        "is_primary": 0,
    },
)
if vendor_not_in_sheet.status_code != 404:
    raise SystemExit("vendor not in sheet should be rejected with 404")
if count_contacts(1, "VendorAllowedDefault") != before_vendor_not_in_sheet:
    raise SystemExit("vendor-not-in-sheet rejection must not affect existing rows")

set_member_session()
before_contact_mismatch = dict(fetch_contact(default_contact_id))
contact_mismatch = client.post(
    "/api/vendor-contact",
    json={
        "id": int(default_contact_id),
        "sheet_id": int(secondary_sheet_id),
        "vendor_name": "VendorAllowedSecondary",
        "contact_name": "Wrong Sheet",
        "contact_title": "",
        "contact_phone": "0900000015",
        "is_primary": 0,
        "contact_order": 0,
    },
)
if contact_mismatch.status_code != 400:
    raise SystemExit("contact mismatch should be rejected with 400")
if contact_mismatch.get_json()["error"]["code"] != "cross_sheet_update_not_allowed":
    raise SystemExit("contact mismatch should preserve cross_sheet_update_not_allowed error code")
after_contact_mismatch = dict(fetch_contact(default_contact_id))
if after_contact_mismatch != before_contact_mismatch:
    raise SystemExit("contact mismatch must not modify stored row")

conn.close()
print("vendor-contact write isolation smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "vendor-contact write isolation smoke PASS" not in result.stdout:
        raise AssertionError("vendor-contact write isolation smoke subprocess did not report PASS.")


def run_vendor_work_entry_write_isolation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys

sample_db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = sample_db_path
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

conn = sqlite3.connect(sample_db_path)
conn.row_factory = sqlite3.Row
module.ensure_vendor_contacts_schema(conn)
default_site_id = module.ensure_site_foundation_schema(conn)
default_site_name = conn.execute("SELECT site_name FROM sites WHERE id = ?", (default_site_id,)).fetchone()["site_name"]
secondary_site_id = conn.execute(
    "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
    ("__vendor_work_secondary__", "vendor-work-secondary"),
).fetchone()["id"]
secondary_sheet_id = conn.execute(
    "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
    ("__vendor_work_sheet__", 96, secondary_site_id),
).fetchone()["id"]
max_col_index = conn.execute("SELECT COALESCE(MAX(col_index), 0) FROM tasks").fetchone()[0]
conn.execute(
    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
    (1, max_col_index + 1, "VendorAllowedDefaultEntry", "Room A", "Vendor Default Entry Task"),
)
conn.execute(
    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
    (secondary_sheet_id, max_col_index + 2, "VendorAllowedSecondaryEntry", "Room B", "Vendor Secondary Entry Task"),
)
password_hash = module.generate_password_hash("x")
conn.execute(
    "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
    ("vendor_work_member", "vendor_work_member", password_hash, "member"),
)
member_id = conn.execute("SELECT id FROM users WHERE username = 'vendor_work_member'").fetchone()["id"]
conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
business_date = module.resolve_crew_business_date()
conn.execute(
    '''
    INSERT INTO vendor_work_entries (
        sheet_id, vendor_name, business_date, planned_at, planned_headcount,
        actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''',
    (1, "VendorAllowedDefaultEntry", business_date, "2000-01-01 09:00", 3, 0, "Default Entry", 0, 0),
)
default_entry_id = conn.execute(
    "SELECT id FROM vendor_work_entries WHERE sheet_id = 1 AND vendor_name = ?",
    ("VendorAllowedDefaultEntry",),
).fetchone()["id"]
conn.execute(
    '''
    INSERT INTO vendor_work_entries (
        sheet_id, vendor_name, business_date, planned_at, planned_headcount,
        actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''',
    (secondary_sheet_id, "VendorAllowedSecondaryEntry", business_date, "2000-01-01 10:00", 2, 1, "Secondary Entry", 1, 0),
)
secondary_entry_id = conn.execute(
    "SELECT id FROM vendor_work_entries WHERE sheet_id = ? AND vendor_name = ?",
    (secondary_sheet_id, "VendorAllowedSecondaryEntry"),
).fetchone()["id"]
conn.commit()

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "vendor_work_member"
        session["display_name"] = "vendor_work_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

def count_entries(sheet_id, vendor_name):
    return conn.execute(
        "SELECT COUNT(*) FROM vendor_work_entries WHERE sheet_id = ? AND vendor_name = ?",
        (sheet_id, vendor_name),
    ).fetchone()[0]

def fetch_entry(entry_id):
    return conn.execute(
        '''
        SELECT vendor_name, business_date, planned_at, planned_headcount,
               actual_headcount, work_content, work_headcount, entry_order
        FROM vendor_work_entries
        WHERE id = ?
        ''',
        (entry_id,),
    ).fetchone()

set_member_session()
same_site_create = client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefaultEntry",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 4,
        "actual_headcount": 0,
        "work_content": "Create Entry",
        "work_headcount": 0,
        "entry_order": 1,
    },
)
if same_site_create.status_code != 200 or not same_site_create.get_json().get("ok"):
    raise SystemExit("same-site vendor-work-entry create should succeed")
same_site_create_payload = same_site_create.get_json()
if set(same_site_create_payload.keys()) != {"ok", "entry"}:
    raise SystemExit("same-site vendor-work-entry create should preserve top-level response shape")
if not isinstance(same_site_create_payload.get("entry"), dict):
    raise SystemExit("same-site vendor-work-entry create should return entry payload")
if count_entries(1, "VendorAllowedDefaultEntry") != 2:
    raise SystemExit("same-site vendor-work-entry create should insert a new row")

set_member_session()
same_site_update = client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(default_entry_id),
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefaultEntry",
        "business_date": business_date,
        "planned_at": "2000-01-01 11:00",
        "planned_headcount": 5,
        "actual_headcount": 2,
        "work_content": "Updated Entry",
        "work_headcount": 2,
        "entry_order": 0,
    },
)
if same_site_update.status_code != 200 or not same_site_update.get_json().get("ok"):
    raise SystemExit("same-site vendor-work-entry update should succeed")
updated_default = fetch_entry(default_entry_id)
if updated_default["work_content"] != "Updated Entry" or updated_default["actual_headcount"] != 2:
    raise SystemExit("same-site vendor-work-entry update should persist updated values")

set_member_session()
before_cross_site_create = count_entries(secondary_sheet_id, "VendorAllowedSecondaryEntry")
cross_site_create = client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": int(secondary_sheet_id),
        "vendor_name": "VendorAllowedSecondaryEntry",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 1,
        "actual_headcount": 0,
        "work_content": "Cross Site Create",
        "work_headcount": 0,
        "entry_order": 1,
    },
)
if cross_site_create.status_code != 403:
    raise SystemExit("cross-site vendor-work-entry create should be rejected with 403")
if count_entries(secondary_sheet_id, "VendorAllowedSecondaryEntry") != before_cross_site_create:
    raise SystemExit("cross-site vendor-work-entry create must not change row count")

set_member_session()
before_cross_site_update = dict(fetch_entry(secondary_entry_id))
cross_site_update = client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(secondary_entry_id),
        "sheet_id": int(secondary_sheet_id),
        "vendor_name": "VendorAllowedSecondaryEntry",
        "business_date": business_date,
        "planned_at": "2000-01-01 12:00",
        "planned_headcount": 3,
        "actual_headcount": 1,
        "work_content": "Blocked Update",
        "work_headcount": 1,
        "entry_order": 0,
    },
)
if cross_site_update.status_code != 403:
    raise SystemExit("cross-site vendor-work-entry update should be rejected with 403")
after_cross_site_update = dict(fetch_entry(secondary_entry_id))
if after_cross_site_update != before_cross_site_update:
    raise SystemExit("cross-site vendor-work-entry update must not modify stored row")

set_member_session(with_current_site=False)
before_missing_site = dict(fetch_entry(default_entry_id))
missing_site = client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(default_entry_id),
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefaultEntry",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 6,
        "actual_headcount": 2,
        "work_content": "Missing Site",
        "work_headcount": 2,
        "entry_order": 0,
    },
)
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject vendor-work-entry write with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False:
    raise SystemExit("missing current site should return ok=false")
if missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site should preserve site_context_invalid")
if missing_site_payload["error"]["message"] != "current_site_id is missing or invalid.":
    raise SystemExit("missing current site should preserve deterministic error message")
after_missing_site = dict(fetch_entry(default_entry_id))
if after_missing_site != before_missing_site:
    raise SystemExit("missing current site must not change existing vendor-work-entry row")

set_member_session()
conn.execute("DELETE FROM user_site_permissions WHERE user_id = ?", (member_id,))
conn.commit()
before_permission_removed = dict(fetch_entry(default_entry_id))
permission_removed = client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(default_entry_id),
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefaultEntry",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 7,
        "actual_headcount": 2,
        "work_content": "Permission Removed",
        "work_headcount": 2,
        "entry_order": 0,
    },
)
if permission_removed.status_code != 403:
    raise SystemExit("permission removed should reject vendor-work-entry write with 403")
permission_removed_payload = permission_removed.get_json()
if permission_removed_payload.get("ok") is not False:
    raise SystemExit("permission removed should return ok=false")
if permission_removed_payload["error"]["code"] != "site_permission_missing":
    raise SystemExit("permission removed should preserve site_permission_missing")
if permission_removed_payload["error"]["message"] != "current user no longer has permission for the current site.":
    raise SystemExit("permission removed should preserve deterministic error message")
after_permission_removed = dict(fetch_entry(default_entry_id))
if after_permission_removed != before_permission_removed:
    raise SystemExit("permission removed must not change existing vendor-work-entry row")

conn.execute(
    "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
    (member_id, default_site_id, "member"),
)
conn.commit()
set_member_session()
before_vendor_not_in_sheet = count_entries(1, "VendorAllowedDefaultEntry")
vendor_not_in_sheet = client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorMissing",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 1,
        "actual_headcount": 0,
        "work_content": "Unknown Vendor",
        "work_headcount": 0,
        "entry_order": 0,
    },
)
if vendor_not_in_sheet.status_code != 404:
    raise SystemExit("vendor not in sheet should be rejected with 404")
vendor_not_in_sheet_payload = vendor_not_in_sheet.get_json()
if vendor_not_in_sheet_payload.get("ok") is not False:
    raise SystemExit("vendor not in sheet should return ok=false")
if vendor_not_in_sheet_payload["error"]["code"] != "vendor_not_in_sheet":
    raise SystemExit("vendor not in sheet should preserve vendor_not_in_sheet error code")
if vendor_not_in_sheet_payload["error"]["message"] != "vendor_name does not belong to the requested sheet.":
    raise SystemExit("vendor not in sheet should preserve deterministic error message")
if count_entries(1, "VendorAllowedDefaultEntry") != before_vendor_not_in_sheet:
    raise SystemExit("vendor-not-in-sheet rejection must not affect existing rows")

set_member_session()
before_entry_mismatch = dict(fetch_entry(default_entry_id))
entry_mismatch = client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(default_entry_id),
        "sheet_id": int(secondary_sheet_id),
        "vendor_name": "VendorAllowedSecondaryEntry",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 1,
        "actual_headcount": 0,
        "work_content": "Wrong Sheet",
        "work_headcount": 0,
        "entry_order": 0,
    },
)
if entry_mismatch.status_code != 409:
    raise SystemExit("entry mismatch should be rejected with 409")
entry_mismatch_payload = entry_mismatch.get_json()
if entry_mismatch_payload.get("ok") is not False:
    raise SystemExit("entry mismatch should return ok=false")
if entry_mismatch_payload["error"]["code"] != "sheet_mismatch":
    raise SystemExit("entry mismatch should preserve sheet_mismatch error code")
if entry_mismatch_payload["error"]["message"] != "vendor work entry belongs to a different sheet_id.":
    raise SystemExit("entry mismatch should preserve deterministic error message")
after_entry_mismatch = dict(fetch_entry(default_entry_id))
if after_entry_mismatch != before_entry_mismatch:
    raise SystemExit("entry mismatch must not modify stored row")

set_member_session()
before_invalid_business_date = dict(fetch_entry(default_entry_id))
invalid_business_date = client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefaultEntry",
        "business_date": "not-a-date",
        "planned_at": "",
        "planned_headcount": 1,
        "actual_headcount": 0,
        "work_content": "Invalid Date",
        "work_headcount": 0,
        "entry_order": 0,
    },
)
if invalid_business_date.status_code != 400:
    raise SystemExit("invalid business_date should be rejected with 400")
after_invalid_business_date = dict(fetch_entry(default_entry_id))
if after_invalid_business_date != before_invalid_business_date:
    raise SystemExit("invalid business_date must not modify existing vendor-work-entry row")

set_member_session()
before_invalid_headcount = dict(fetch_entry(default_entry_id))
invalid_headcount = client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": 1,
        "vendor_name": "VendorAllowedDefaultEntry",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": -1,
        "actual_headcount": 0,
        "work_content": "Invalid Headcount",
        "work_headcount": 0,
        "entry_order": 0,
    },
)
if invalid_headcount.status_code != 400:
    raise SystemExit("invalid headcount should be rejected with 400")
invalid_payload = invalid_headcount.get_json()
if invalid_payload.get("ok") is not False or "error" not in invalid_payload:
    raise SystemExit("invalid headcount should use standard error payload")
after_invalid_headcount = dict(fetch_entry(default_entry_id))
if after_invalid_headcount != before_invalid_headcount:
    raise SystemExit("invalid headcount must not modify existing vendor-work-entry row")

conn.close()
print("vendor-work-entry write isolation smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "vendor-work-entry write isolation smoke PASS" not in result.stdout:
        raise AssertionError("vendor-work-entry write isolation smoke subprocess did not report PASS.")


def run_vendor_work_entry_requirement_confirmation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = db_path
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for requirement confirmation smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for requirement confirmation smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__requirement_confirm_site_b__", "requirement-confirm-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Requirement Confirm Sheet B", 999, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("confirm_member", "confirm_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("confirm_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    admin_password_hash = module.generate_password_hash("admin-pass")
    conn.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (admin_password_hash,))
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_confirm_only", module.generate_password_hash("vendor-pass"), "Vendor Confirm", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("vendor_confirm_only",)).fetchone()["id"]
    )
    target_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Confirm", business_date, "2000-01-01 09:00", 3, 0, "Confirm Work", "Need power off", 0, 0),
        ).fetchone()["id"]
    )
    secondary_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (secondary_sheet_id, "Vendor Confirm", business_date, "2000-01-01 10:00", 2, 0, "Cross Site Confirm Work", "Need fence open", 0, 0),
        ).fetchone()["id"]
    )
    conn.commit()

def fetch_confirmation_snapshot(entry_id):
    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            '''
            SELECT pre_entry_requirement, requirement_status, requirement_confirmed_by, requirement_confirmed_at
            FROM vendor_work_entries
            WHERE id = ?
            ''',
            (entry_id,),
        ).fetchone()
        return dict(row)

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "confirm_member"
        session["display_name"] = "confirm_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

set_member_session()
before_confirm = fetch_confirmation_snapshot(target_entry_id)
confirm_response = client.post(
    "/api/crew-work-entry-requirement-confirm",
    json={"entry_id": target_entry_id, "sheet_id": sheet_id},
)
if confirm_response.status_code != 200 or not confirm_response.get_json().get("ok"):
    raise SystemExit("requirement confirmation success path should return ok=true")
confirm_entry = confirm_response.get_json()["entry"]
if set(confirm_entry.keys()) != {"id", "requirement_status", "requirement_confirmed_by", "requirement_confirmed_at"}:
    raise SystemExit("requirement confirmation response contract should remain minimal")
if int(confirm_entry["id"]) != int(target_entry_id):
    raise SystemExit("requirement confirmation should return the confirmed entry id")
if confirm_entry["requirement_status"] != "confirmed":
    raise SystemExit("requirement confirmation should set requirement_status=confirmed")
if confirm_entry["requirement_confirmed_by"] != "confirm_member":
    raise SystemExit("requirement confirmation should stamp current internal username")
if not str(confirm_entry["requirement_confirmed_at"] or ""):
    raise SystemExit("requirement confirmation should stamp requirement_confirmed_at")
after_confirm = fetch_confirmation_snapshot(target_entry_id)
if after_confirm["pre_entry_requirement"] != before_confirm["pre_entry_requirement"]:
    raise SystemExit("requirement confirmation must not modify pre_entry_requirement text")
if after_confirm["requirement_status"] != "confirmed":
    raise SystemExit("requirement confirmation should persist confirmed status")
if after_confirm["requirement_confirmed_by"] != "confirm_member":
    raise SystemExit("requirement confirmation should persist requirement_confirmed_by")
if not str(after_confirm["requirement_confirmed_at"] or ""):
    raise SystemExit("requirement confirmation should persist requirement_confirmed_at")

set_member_session()
repeat_response = client.post(
    "/api/crew-work-entry-requirement-confirm",
    json={"entry_id": target_entry_id, "sheet_id": sheet_id},
)
if repeat_response.status_code != 200 or not repeat_response.get_json().get("ok"):
    raise SystemExit("repeated requirement confirmation should remain idempotently successful")
repeat_entry = repeat_response.get_json()["entry"]
if repeat_entry["requirement_status"] != "confirmed":
    raise SystemExit("repeated requirement confirmation should preserve confirmed status")
repeat_snapshot = fetch_confirmation_snapshot(target_entry_id)
if repeat_snapshot != after_confirm:
    raise SystemExit("repeated requirement confirmation should not change persisted confirmation state")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "vendor_confirm_only"
    session["vendor_name"] = "Vendor Confirm"
vendor_forbidden = client.post(
    "/api/crew-work-entry-requirement-confirm",
    json={"entry_id": target_entry_id, "sheet_id": sheet_id},
)
if vendor_forbidden.status_code != 403:
    raise SystemExit("vendor session should not confirm requirement")
vendor_forbidden_payload = vendor_forbidden.get_json()
if vendor_forbidden_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor session rejection should preserve vendor_auth_forbidden error code")
if fetch_confirmation_snapshot(target_entry_id) != repeat_snapshot:
    raise SystemExit("vendor session rejection must not modify confirmation state")

set_member_session(with_current_site=False)
missing_site = client.post(
    "/api/crew-work-entry-requirement-confirm",
    json={"entry_id": target_entry_id, "sheet_id": sheet_id},
)
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject requirement confirmation with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site should preserve site_context_invalid error code")
if fetch_confirmation_snapshot(target_entry_id) != repeat_snapshot:
    raise SystemExit("missing current site rejection must not modify confirmation state")

set_member_session()
before_cross_site = fetch_confirmation_snapshot(secondary_entry_id)
cross_site = client.post(
    "/api/crew-work-entry-requirement-confirm",
    json={"entry_id": secondary_entry_id, "sheet_id": secondary_sheet_id},
)
if cross_site.status_code != 403:
    raise SystemExit("cross-site requirement confirmation should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload["error"]["code"] != "write_target_not_in_current_site":
    raise SystemExit("cross-site requirement confirmation should preserve write_target_not_in_current_site")
after_cross_site = fetch_confirmation_snapshot(secondary_entry_id)
if after_cross_site != before_cross_site:
    raise SystemExit("cross-site requirement confirmation must not modify stored row")

set_member_session()
before_sheet_mismatch = fetch_confirmation_snapshot(target_entry_id)
sheet_mismatch = client.post(
    "/api/crew-work-entry-requirement-confirm",
    json={"entry_id": target_entry_id, "sheet_id": secondary_sheet_id},
)
if sheet_mismatch.status_code != 409:
    raise SystemExit("sheet mismatch requirement confirmation should be rejected with 409")
sheet_mismatch_payload = sheet_mismatch.get_json()
if sheet_mismatch_payload["error"]["code"] != "sheet_mismatch":
    raise SystemExit("sheet mismatch requirement confirmation should preserve sheet_mismatch error code")
after_sheet_mismatch = fetch_confirmation_snapshot(target_entry_id)
if after_sheet_mismatch != before_sheet_mismatch:
    raise SystemExit("sheet mismatch requirement confirmation must not modify stored row")

print("vendor-work-entry requirement confirmation smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "vendor-work-entry requirement confirmation smoke PASS" not in result.stdout:
        raise AssertionError("vendor-work-entry requirement confirmation smoke subprocess did not report PASS.")


def run_vendor_work_entry_formal_approve_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = db_path
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for formal approve smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for formal approve smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__formal_approve_site_b__", "formal-approve-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Formal Approve Sheet B", 999, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("formal_member", "formal_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("formal_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    admin_password_hash = module.generate_password_hash("admin-pass")
    conn.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (admin_password_hash,))
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_formal_only", module.generate_password_hash("vendor-pass"), "Vendor Formal", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("vendor_formal_only",)).fetchone()["id"]
    )
    ready_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Formal", business_date, "2000-01-01 09:00", 3, 0, "Ready Work", "", 0, 0),
        ).fetchone()["id"]
    )
    pending_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Formal", business_date, "2000-01-01 10:00", 2, 0, "Pending Work", "Need power off", 0, 1),
        ).fetchone()["id"]
    )
    secondary_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (secondary_sheet_id, "Vendor Formal", business_date, "2000-01-01 11:00", 2, 0, "Cross Site Work", "", 0, 0),
        ).fetchone()["id"]
    )
    conn.commit()

def fetch_entry_snapshot(entry_id):
    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            '''
            SELECT id, sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                   actual_headcount, work_content, pre_entry_requirement, requirement_status,
                   requirement_confirmed_by, requirement_confirmed_at, work_headcount, entry_order,
                   created_at, updated_at
            FROM vendor_work_entries
            WHERE id = ?
            ''',
            (entry_id,),
        ).fetchone()
        return dict(row)

def fetch_formal_approval_count():
    with module.db() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0])

def fetch_formal_approval_row(entry_id):
    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            '''
            SELECT entry_id, sheet_id, action, approval_status, approved_by, approved_at
            FROM formal_approvals
            WHERE entry_id = ?
            ''',
            (entry_id,),
        ).fetchone()
        return dict(row) if row is not None else None

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "formal_member"
        session["display_name"] = "formal_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

with module.db() as conn:
    ready_context = module.resolve_vendor_work_entry_formal_approve_context(
        conn,
        sheet_id=sheet_id,
        entry_id=ready_entry_id,
    )
    pending_context = module.resolve_vendor_work_entry_formal_approve_context(
        conn,
        sheet_id=sheet_id,
        entry_id=pending_entry_id,
    )
if ready_context["readiness_state"] != "ready" or ready_context["readiness_reason"] != "no_requirement":
    raise SystemExit("allowed formal approve smoke entry should remain readiness=ready/no_requirement")
if ready_context["scheduling_gate_state"] != "allowed" or ready_context["scheduling_gate_reason"] != "no_requirement":
    raise SystemExit("allowed formal approve smoke entry should remain scheduling gate allowed/no_requirement")
if pending_context["readiness_state"] != "not_ready" or pending_context["readiness_reason"] != "requirement_pending":
    raise SystemExit("blocked formal approve smoke entry should remain readiness=not_ready/requirement_pending")
if pending_context["scheduling_gate_state"] != "warning" or pending_context["scheduling_gate_reason"] != "requirement_pending":
    raise SystemExit("blocked formal approve smoke entry should remain scheduling gate warning/requirement_pending")

ready_before = fetch_entry_snapshot(ready_entry_id)
formal_approvals_before_ready = fetch_formal_approval_count()
set_member_session()
ready_response = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": ready_entry_id, "sheet_id": sheet_id, "action": "crew_formal_approve_entry"},
)
if ready_response.status_code != 200 or not ready_response.get_json().get("ok"):
    raise SystemExit("ready entry formal approve should return ok=true")
ready_payload = ready_response.get_json()
if set(ready_payload.keys()) != {"ok", "action", "entry"}:
    raise SystemExit("formal approve success response should keep exact contract keys")
if ready_payload["ok"] is not True:
    raise SystemExit("formal approve success response should keep ok=true")
if ready_payload["action"] != "crew_formal_approve_entry":
    raise SystemExit("formal approve success should return crew_formal_approve_entry action")
if set(ready_payload["entry"].keys()) != {"id", "sheet_id"}:
    raise SystemExit("formal approve success response should remain minimal")
if int(ready_payload["entry"]["id"]) != int(ready_entry_id) or int(ready_payload["entry"]["sheet_id"]) != int(sheet_id):
    raise SystemExit("formal approve success should return the acted-on entry identity")
ready_after = fetch_entry_snapshot(ready_entry_id)
if ready_after != ready_before:
    raise SystemExit("allowed formal approve must not modify stored row")
if fetch_formal_approval_count() != formal_approvals_before_ready + 1:
    raise SystemExit("allowed formal approve should create exactly one formal_approvals row")
ready_approval = fetch_formal_approval_row(ready_entry_id)
if ready_approval is None:
    raise SystemExit("allowed formal approve should persist a formal approval row")
if int(ready_approval["entry_id"]) != int(ready_entry_id) or int(ready_approval["sheet_id"]) != int(sheet_id):
    raise SystemExit("formal approval row should persist acted-on entry identity")
if ready_approval["action"] != "crew_formal_approve_entry":
    raise SystemExit("formal approval row should persist crew_formal_approve_entry action")
if ready_approval["approval_status"] != "approved":
    raise SystemExit("formal approval row should persist approval_status=approved")
if ready_approval["approved_by"] != "formal_member":
    raise SystemExit("formal approval row should persist approving username")
if not str(ready_approval["approved_at"] or "").strip():
    raise SystemExit("formal approval row should persist approved_at timestamp")

duplicate_before = fetch_entry_snapshot(ready_entry_id)
duplicate_count_before = fetch_formal_approval_count()
set_member_session()
duplicate_response = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": ready_entry_id, "sheet_id": sheet_id, "action": "crew_formal_approve_entry"},
)
if duplicate_response.status_code != 409:
    raise SystemExit("duplicate formal approve should be rejected with 409")
duplicate_payload = duplicate_response.get_json()
if duplicate_payload.get("ok") is not False:
    raise SystemExit("duplicate formal approve rejection should keep ok=false")
if duplicate_payload["error"]["code"] != "duplicate_approval":
    raise SystemExit("duplicate formal approve should preserve duplicate_approval error code")
if fetch_entry_snapshot(ready_entry_id) != duplicate_before:
    raise SystemExit("duplicate formal approve rejection must not modify stored entry")
if fetch_formal_approval_count() != duplicate_count_before:
    raise SystemExit("duplicate formal approve should not create extra formal_approvals rows")

pending_before = fetch_entry_snapshot(pending_entry_id)
formal_approvals_before_blocked = fetch_formal_approval_count()
set_member_session()
blocked_response = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": pending_entry_id, "sheet_id": sheet_id, "action": "crew_formal_approve_entry"},
)
if blocked_response.status_code != 409:
    raise SystemExit("not-ready formal approve should be rejected with 409")
blocked_payload = blocked_response.get_json()
if set(blocked_payload.keys()) != {"ok", "error"}:
    raise SystemExit("blocked formal approve response should keep exact contract keys")
if blocked_payload["ok"] is not False:
    raise SystemExit("blocked formal approve response should keep ok=false")
if set(blocked_payload["error"].keys()) != {"code", "message"}:
    raise SystemExit("blocked formal approve error contract should remain minimal")
if blocked_payload["error"]["code"] != "entry_not_ready":
    raise SystemExit("not-ready formal approve should preserve entry_not_ready error code")
if blocked_payload["error"]["message"] != "Entry is not ready for this action.":
    raise SystemExit("not-ready formal approve should preserve deterministic error message")
pending_after = fetch_entry_snapshot(pending_entry_id)
if pending_after != pending_before:
    raise SystemExit("blocked formal approve must not modify stored row")
if fetch_formal_approval_count() != formal_approvals_before_blocked:
    raise SystemExit("blocked formal approve must not create formal_approvals rows")
if fetch_formal_approval_row(pending_entry_id) is not None:
    raise SystemExit("blocked formal approve must not persist a formal approval row")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "vendor_formal_only"
    session["vendor_name"] = "Vendor Formal"
vendor_forbidden_before = fetch_entry_snapshot(ready_entry_id)
vendor_forbidden = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": ready_entry_id, "sheet_id": sheet_id, "action": "crew_formal_approve_entry"},
)
if vendor_forbidden.status_code != 403:
    raise SystemExit("vendor session should not formal-approve entry")
vendor_forbidden_payload = vendor_forbidden.get_json()
if vendor_forbidden_payload.get("ok") is not False:
    raise SystemExit("vendor formal approve rejection should keep ok=false")
if vendor_forbidden_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor formal approve rejection should preserve vendor_auth_forbidden error code")
if fetch_entry_snapshot(ready_entry_id) != vendor_forbidden_before:
    raise SystemExit("vendor formal approve rejection must not modify stored row")
if fetch_formal_approval_count() != duplicate_count_before:
    raise SystemExit("vendor formal approve rejection must not create formal_approvals rows")

set_member_session(with_current_site=False)
missing_site_before = fetch_entry_snapshot(ready_entry_id)
missing_site_formal_count_before = fetch_formal_approval_count()
missing_site = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": ready_entry_id, "sheet_id": sheet_id, "action": "crew_formal_approve_entry"},
)
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject formal approve with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False:
    raise SystemExit("missing current site formal approve rejection should keep ok=false")
if missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site formal approve should preserve site_context_invalid error code")
if fetch_entry_snapshot(ready_entry_id) != missing_site_before:
    raise SystemExit("missing current site formal approve rejection must not modify stored row")
if fetch_formal_approval_count() != missing_site_formal_count_before:
    raise SystemExit("missing current site formal approve must not create formal_approvals rows")

set_member_session()
cross_site_before = fetch_entry_snapshot(secondary_entry_id)
cross_site_formal_count_before = fetch_formal_approval_count()
cross_site = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": secondary_entry_id, "sheet_id": secondary_sheet_id, "action": "crew_formal_approve_entry"},
)
if cross_site.status_code != 403:
    raise SystemExit("cross-site formal approve should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload.get("ok") is not False:
    raise SystemExit("cross-site formal approve rejection should keep ok=false")
if cross_site_payload["error"]["code"] != "write_target_not_in_current_site":
    raise SystemExit("cross-site formal approve should preserve write_target_not_in_current_site error code")
if fetch_entry_snapshot(secondary_entry_id) != cross_site_before:
    raise SystemExit("cross-site formal approve must not modify stored row")
if fetch_formal_approval_count() != cross_site_formal_count_before:
    raise SystemExit("cross-site formal approve must not create formal_approvals rows")

set_member_session()
sheet_mismatch_before = fetch_entry_snapshot(ready_entry_id)
sheet_mismatch_formal_count_before = fetch_formal_approval_count()
sheet_mismatch = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": ready_entry_id, "sheet_id": secondary_sheet_id, "action": "crew_formal_approve_entry"},
)
if sheet_mismatch.status_code != 409:
    raise SystemExit("sheet mismatch formal approve should be rejected with 409")
sheet_mismatch_payload = sheet_mismatch.get_json()
if sheet_mismatch_payload.get("ok") is not False:
    raise SystemExit("sheet mismatch formal approve rejection should keep ok=false")
if sheet_mismatch_payload["error"]["code"] != "sheet_mismatch":
    raise SystemExit("sheet mismatch formal approve should preserve sheet_mismatch error code")
if fetch_entry_snapshot(ready_entry_id) != sheet_mismatch_before:
    raise SystemExit("sheet mismatch formal approve must not modify stored row")
if fetch_formal_approval_count() != sheet_mismatch_formal_count_before:
    raise SystemExit("sheet mismatch formal approve must not create formal_approvals rows")

set_member_session()
entry_not_found_formal_count_before = fetch_formal_approval_count()
entry_not_found = client.post(
    "/api/crew-work-entry/formal-approve",
    json={"entry_id": 999999, "sheet_id": sheet_id, "action": "crew_formal_approve_entry"},
)
if entry_not_found.status_code != 404:
    raise SystemExit("missing entry formal approve should be rejected with 404")
entry_not_found_payload = entry_not_found.get_json()
if entry_not_found_payload.get("ok") is not False:
    raise SystemExit("missing entry formal approve rejection should keep ok=false")
if entry_not_found_payload["error"]["code"] != "entry_not_found":
    raise SystemExit("missing entry formal approve should preserve entry_not_found error code")
if fetch_formal_approval_count() != entry_not_found_formal_count_before:
    raise SystemExit("missing entry formal approve must not create formal_approvals rows")

print("vendor-work-entry formal approve smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "vendor-work-entry formal approve smoke PASS" not in result.stdout:
        raise AssertionError("vendor-work-entry formal approve smoke subprocess did not report PASS.")


def run_scheduler_persistence_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = db_path
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for scheduler persistence smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for scheduler persistence smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__schedule_entry_site_b__", "schedule-entry-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Schedule Entry Sheet B", 999, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("schedule_member", "schedule_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("schedule_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_schedule_only", module.generate_password_hash("vendor-pass"), "Vendor Schedule", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("vendor_schedule_only",)).fetchone()["id"]
    )
    ready_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Schedule", business_date, "2000-01-01 09:00", 3, 0, "Ready Schedule Work", "", 0, 0),
        ).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Schedule", business_date, "2000-01-01 10:00", 2, 0, "Blocked Schedule Work", "Need shutdown", 0, 1),
        ).fetchone()["id"]
    )
    secondary_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (secondary_sheet_id, "Vendor Schedule", business_date, "2000-01-01 11:00", 1, 0, "Cross Site Schedule Work", "", 0, 0),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (ready_entry_id, sheet_id, "schedule_member"),
    )
    conn.commit()

def fetch_schedule_count():
    with module.db() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0])

def fetch_schedule_row(entry_id):
    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            '''
            SELECT id, entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time, scheduled_by, scheduled_at
            FROM scheduling_entries
            WHERE entry_id = ?
            ''',
            (entry_id,),
        ).fetchone()
        return dict(row) if row is not None else None

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "scheduling_entries": int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "schedule_member"
        session["display_name"] = "schedule_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

with module.db() as conn:
    ready_context = module.resolve_schedule_entry_context(conn, sheet_id=sheet_id, entry_id=ready_entry_id)
    blocked_context = module.resolve_schedule_entry_context(conn, sheet_id=sheet_id, entry_id=blocked_entry_id)
if ready_context["formal_approval_state"] != "approved" or ready_context["scheduling_gate_state"] != "allowed":
    raise SystemExit("scheduler persistence ready entry should remain schedulable")
if blocked_context["scheduling_gate_state"] != "warning":
    raise SystemExit("scheduler persistence blocked entry should remain blocked by scheduling gate")

success_before = fetch_db_snapshot()
set_member_session()
success_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "09:30",
    },
)
if success_response.status_code != 200 or not success_response.get_json().get("ok"):
    raise SystemExit("schedulable entry should create schedule successfully")
success_payload = success_response.get_json()
if set(success_payload.keys()) != {"ok", "action", "schedule"}:
    raise SystemExit("schedule entry success response should keep exact contract keys")
if success_payload["action"] != "schedule_entry":
    raise SystemExit("schedule entry success should preserve action=schedule_entry")
if set(success_payload["schedule"].keys()) != {"id", "entry_id", "sheet_id", "scheduled_date", "scheduled_time"}:
    raise SystemExit("schedule entry success should keep minimal schedule contract")
if int(success_payload["schedule"]["entry_id"]) != int(ready_entry_id) or int(success_payload["schedule"]["sheet_id"]) != int(sheet_id):
    raise SystemExit("schedule entry success should return acted-on schedule identity")
if success_payload["schedule"]["scheduled_date"] != "2026-07-08" or success_payload["schedule"]["scheduled_time"] != "09:30":
    raise SystemExit("schedule entry success should preserve scheduled date/time")
if fetch_schedule_count() != success_before["scheduling_entries"] + 1:
    raise SystemExit("schedule entry success should create exactly one scheduling_entries row")
success_row = fetch_schedule_row(ready_entry_id)
if success_row is None:
    raise SystemExit("schedule entry success should persist scheduling row")
if success_row["action"] != "schedule_entry" or success_row["schedule_status"] != "scheduled":
    raise SystemExit("schedule entry row should persist action/status")
if success_row["scheduled_by"] != "schedule_member":
    raise SystemExit("schedule entry row should persist scheduling username")
if not str(success_row["scheduled_at"] or "").strip():
    raise SystemExit("schedule entry row should persist scheduled_at timestamp")

duplicate_before = fetch_db_snapshot()
set_member_session()
duplicate_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "10:00",
    },
)
if duplicate_response.status_code != 409:
    raise SystemExit("duplicate schedule should be rejected with 409")
duplicate_payload = duplicate_response.get_json()
if duplicate_payload.get("ok") is not False or duplicate_payload["error"]["code"] != "duplicate_schedule":
    raise SystemExit("duplicate schedule should preserve duplicate_schedule error code")
if fetch_db_snapshot() != duplicate_before:
    raise SystemExit("duplicate schedule rejection must keep DB unchanged")

blocked_before = fetch_db_snapshot()
set_member_session()
blocked_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": blocked_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "11:00",
    },
)
if blocked_response.status_code != 409:
    raise SystemExit("blocked schedule should be rejected with 409")
blocked_payload = blocked_response.get_json()
if blocked_payload.get("ok") is not False or blocked_payload["error"]["code"] != "entry_not_schedulable":
    raise SystemExit("blocked schedule should preserve entry_not_schedulable")
if fetch_db_snapshot() != blocked_before:
    raise SystemExit("blocked schedule rejection must keep DB unchanged")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "vendor_schedule_only"
    session["vendor_name"] = "Vendor Schedule"
vendor_before = fetch_db_snapshot()
vendor_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "12:00",
    },
)
if vendor_response.status_code != 403:
    raise SystemExit("vendor session should be forbidden from schedule entry API")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor schedule rejection should preserve vendor_auth_forbidden")
if fetch_db_snapshot() != vendor_before:
    raise SystemExit("vendor schedule rejection must keep DB unchanged")

missing_site_before = fetch_db_snapshot()
set_member_session(with_current_site=False)
missing_site_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "13:00",
    },
)
if missing_site_response.status_code != 403:
    raise SystemExit("missing current site should reject schedule entry API")
missing_site_payload = missing_site_response.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site schedule rejection should preserve site_context_invalid")
if fetch_db_snapshot() != missing_site_before:
    raise SystemExit("missing current site schedule rejection must keep DB unchanged")

cross_site_before = fetch_db_snapshot()
set_member_session()
cross_site_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": secondary_entry_id,
        "sheet_id": secondary_sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "14:00",
    },
)
if cross_site_response.status_code != 403:
    raise SystemExit("cross-site schedule should be rejected with 403")
cross_site_payload = cross_site_response.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "write_target_not_in_current_site":
    raise SystemExit("cross-site schedule rejection should preserve write_target_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("cross-site schedule rejection must keep DB unchanged")

sheet_mismatch_before = fetch_db_snapshot()
set_member_session()
sheet_mismatch_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": secondary_sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "15:00",
    },
)
if sheet_mismatch_response.status_code != 409:
    raise SystemExit("sheet mismatch schedule should be rejected with 409")
sheet_mismatch_payload = sheet_mismatch_response.get_json()
if sheet_mismatch_payload.get("ok") is not False or sheet_mismatch_payload["error"]["code"] != "sheet_mismatch":
    raise SystemExit("sheet mismatch schedule rejection should preserve sheet_mismatch")
if fetch_db_snapshot() != sheet_mismatch_before:
    raise SystemExit("sheet mismatch schedule rejection must keep DB unchanged")

missing_entry_before = fetch_db_snapshot()
set_member_session()
missing_entry_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": 999999,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "16:00",
    },
)
if missing_entry_response.status_code != 404:
    raise SystemExit("missing entry schedule should be rejected with 404")
missing_entry_payload = missing_entry_response.get_json()
if missing_entry_payload.get("ok") is not False or missing_entry_payload["error"]["code"] != "entry_not_found":
    raise SystemExit("missing entry schedule rejection should preserve entry_not_found")
if fetch_db_snapshot() != missing_entry_before:
    raise SystemExit("missing entry schedule rejection must keep DB unchanged")

print("scheduler persistence smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "scheduler persistence smoke PASS" not in result.stdout:
        raise AssertionError("scheduler persistence smoke subprocess did not report PASS.")


def run_scheduler_persistence_guardrail_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
os.environ["APP_DB_PATH"] = db_path
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for scheduler persistence guardrail smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for scheduler persistence guardrail smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__schedule_guardrail_site_b__", "schedule-guardrail-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Schedule Guardrail Sheet B", 1000, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("schedule_guardrail_member", "schedule_guardrail_member", member_password_hash, "member"),
    )
    member_id = int(
        conn.execute("SELECT id FROM users WHERE username = ?", ("schedule_guardrail_member",)).fetchone()["id"]
    )
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_schedule_guardrail", module.generate_password_hash("vendor-pass"), "Vendor Schedule Guardrail", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("vendor_schedule_guardrail",)).fetchone()["id"]
    )
    ready_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Schedule Guardrail", business_date, "2000-01-01 09:00", 3, 0, "Ready Guardrail Work", "", 0, 0),
        ).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Schedule Guardrail", business_date, "2000-01-01 10:00", 2, 0, "Blocked Guardrail Work", "Need shutdown", 0, 1),
        ).fetchone()["id"]
    )
    secondary_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (secondary_sheet_id, "Vendor Schedule Guardrail", business_date, "2000-01-01 11:00", 1, 0, "Cross Site Guardrail Work", "", 0, 0),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (ready_entry_id, sheet_id, "schedule_guardrail_member"),
    )
    conn.commit()

def fetch_schedule_count():
    with module.db() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0])

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "scheduling_entries": int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "schedule_guardrail_member"
        session["display_name"] = "schedule_guardrail_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

success_before = fetch_db_snapshot()
set_member_session()
success_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "09:30",
    },
)
if success_response.status_code != 200:
    raise SystemExit("scheduler persistence guardrail success should return 200")
success_payload = success_response.get_json()
if set(success_payload.keys()) != {"ok", "action", "schedule"}:
    raise SystemExit("scheduler persistence guardrail should freeze exact success response keys")
if success_payload["ok"] is not True:
    raise SystemExit("scheduler persistence guardrail should freeze ok=true on success")
if success_payload["action"] != "schedule_entry":
    raise SystemExit("scheduler persistence guardrail should freeze action=schedule_entry")
if set(success_payload["schedule"].keys()) != {"id", "entry_id", "sheet_id", "scheduled_date", "scheduled_time"}:
    raise SystemExit("scheduler persistence guardrail should freeze exact schedule response keys")
if fetch_schedule_count() != success_before["scheduling_entries"] + 1:
    raise SystemExit("scheduler persistence guardrail should freeze success row count +1")

duplicate_before = fetch_db_snapshot()
set_member_session()
duplicate_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "10:00",
    },
)
if duplicate_response.status_code != 409:
    raise SystemExit("scheduler persistence guardrail duplicate should return 409")
duplicate_payload = duplicate_response.get_json()
if set(duplicate_payload.keys()) != {"ok", "error"}:
    raise SystemExit("scheduler persistence guardrail should freeze duplicate error contract keys")
if duplicate_payload.get("ok") is not False or duplicate_payload["error"]["code"] != "duplicate_schedule":
    raise SystemExit("scheduler persistence guardrail should freeze duplicate_schedule")
if fetch_db_snapshot() != duplicate_before:
    raise SystemExit("scheduler persistence guardrail duplicate must keep DB unchanged")

blocked_before = fetch_db_snapshot()
set_member_session()
blocked_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": blocked_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "11:00",
    },
)
if blocked_response.status_code != 409:
    raise SystemExit("scheduler persistence guardrail blocked should return 409")
blocked_payload = blocked_response.get_json()
if blocked_payload.get("ok") is not False or blocked_payload["error"]["code"] != "entry_not_schedulable":
    raise SystemExit("scheduler persistence guardrail should freeze entry_not_schedulable")
if fetch_db_snapshot() != blocked_before:
    raise SystemExit("scheduler persistence guardrail blocked must keep DB unchanged")

sheet_mismatch_before = fetch_db_snapshot()
set_member_session()
sheet_mismatch_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": secondary_sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "12:00",
    },
)
if sheet_mismatch_response.status_code != 409:
    raise SystemExit("scheduler persistence guardrail sheet mismatch should return 409")
sheet_mismatch_payload = sheet_mismatch_response.get_json()
if sheet_mismatch_payload.get("ok") is not False or sheet_mismatch_payload["error"]["code"] != "sheet_mismatch":
    raise SystemExit("scheduler persistence guardrail should freeze sheet_mismatch")
if fetch_db_snapshot() != sheet_mismatch_before:
    raise SystemExit("scheduler persistence guardrail sheet mismatch must keep DB unchanged")

missing_entry_before = fetch_db_snapshot()
set_member_session()
missing_entry_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": 999999,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "13:00",
    },
)
if missing_entry_response.status_code != 404:
    raise SystemExit("scheduler persistence guardrail missing entry should return 404")
missing_entry_payload = missing_entry_response.get_json()
if missing_entry_payload.get("ok") is not False or missing_entry_payload["error"]["code"] != "entry_not_found":
    raise SystemExit("scheduler persistence guardrail should freeze entry_not_found")
if fetch_db_snapshot() != missing_entry_before:
    raise SystemExit("scheduler persistence guardrail missing entry must keep DB unchanged")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "vendor_schedule_guardrail"
    session["vendor_name"] = "Vendor Schedule Guardrail"
vendor_before = fetch_db_snapshot()
vendor_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "14:00",
    },
)
if vendor_response.status_code != 403:
    raise SystemExit("scheduler persistence guardrail vendor should return 403")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("scheduler persistence guardrail should freeze vendor_auth_forbidden")
if fetch_db_snapshot() != vendor_before:
    raise SystemExit("scheduler persistence guardrail vendor must keep DB unchanged")

missing_site_before = fetch_db_snapshot()
set_member_session(with_current_site=False)
missing_site_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": ready_entry_id,
        "sheet_id": sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "15:00",
    },
)
if missing_site_response.status_code != 403:
    raise SystemExit("scheduler persistence guardrail missing current site should return 403")
missing_site_payload = missing_site_response.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("scheduler persistence guardrail should freeze site_context_invalid")
if fetch_db_snapshot() != missing_site_before:
    raise SystemExit("scheduler persistence guardrail missing site must keep DB unchanged")

cross_site_before = fetch_db_snapshot()
set_member_session()
cross_site_response = client.post(
    "/api/schedule-entry",
    json={
        "entry_id": secondary_entry_id,
        "sheet_id": secondary_sheet_id,
        "action": "schedule_entry",
        "scheduled_date": "2026-07-08",
        "scheduled_time": "16:00",
    },
)
if cross_site_response.status_code != 403:
    raise SystemExit("scheduler persistence guardrail cross-site should return 403")
cross_site_payload = cross_site_response.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "write_target_not_in_current_site":
    raise SystemExit("scheduler persistence guardrail should freeze write_target_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("scheduler persistence guardrail cross-site must keep DB unchanged")

print("scheduler persistence guardrail smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "scheduler persistence guardrail smoke PASS" not in result.stdout:
        raise AssertionError("scheduler persistence guardrail smoke subprocess did not report PASS.")


def run_dashboard_api_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for dashboard smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for dashboard smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__dashboard_site_b__", "dashboard-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Dashboard Sheet B", 999, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("dashboard_member", "dashboard_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("dashboard_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("dashboard_vendor", module.generate_password_hash("vendor-pass"), "Vendor Dashboard", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("dashboard_vendor",)).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Dashboard", business_date, "2000-01-01 09:00", 2, 0, "Blocked Work", "Need permit", 0, 0),
        ).fetchone()["id"]
    )
    pending_approval_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Dashboard", business_date, "2000-01-01 10:00", 3, 0, "Pending Approval Work", "", 0, 1),
        ).fetchone()["id"]
    )
    approved_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Dashboard", business_date, "2000-01-01 11:00", 1, 0, "Approved Work", "", 0, 2),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, "dashboard_member"),
    )
    conn.execute(
        '''
        INSERT INTO scheduling_entries (
            entry_id, sheet_id, action, schedule_status, scheduled_date, scheduled_time,
            scheduled_by, scheduled_at, created_at, updated_at
        ) VALUES (?, ?, 'schedule_entry', 'scheduled', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (approved_entry_id, sheet_id, business_date, "09:30", "dashboard_member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (secondary_sheet_id, "Vendor Dashboard", business_date, "2000-01-01 12:00", 1, 0, "Cross Site Work", "", 0, 0),
    )
    conn.commit()

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
            "scheduling_entries": int(conn.execute("SELECT COUNT(*) FROM scheduling_entries").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "dashboard_member"
        session["display_name"] = "dashboard_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

success_before = fetch_db_snapshot()
set_member_session()
success = client.get(f"/api/dashboard?sheet_id={sheet_id}")
if success.status_code != 200:
    raise SystemExit("dashboard success path should return 200")
payload = success.get_json()
expected_top_level_keys = {
    "summary",
    "blocked_items",
    "pending_approvals",
    "pending_requirements",
    "today_entries",
    "scheduled_entries",
    "today_schedule",
    "quick_actions",
}
if set(payload.keys()) != expected_top_level_keys:
    raise SystemExit("dashboard success response should preserve existing fields and append scheduled fact fields")
summary = payload["summary"]
expected_summary_keys = {
    "blocked_count",
    "pending_approval_count",
    "pending_requirement_count",
    "today_entry_count",
    "approved_today_count",
    "scheduled_count",
    "today_schedule_count",
}
if set(summary.keys()) != expected_summary_keys:
    raise SystemExit("dashboard summary should preserve existing counts and append scheduled fact counts")
if summary["blocked_count"] != 1:
    raise SystemExit("dashboard summary should count one blocked item")
if summary["pending_approval_count"] != 1:
    raise SystemExit("dashboard summary should count one pending approval")
if summary["pending_requirement_count"] != 1:
    raise SystemExit("dashboard summary should count one pending requirement")
if summary["today_entry_count"] != 3:
    raise SystemExit("dashboard summary should count three today entries")
if summary["approved_today_count"] != 1:
    raise SystemExit("dashboard summary should count one approved today entry")
if summary["scheduled_count"] != 1:
    raise SystemExit("dashboard summary should count one scheduled fact entry")
if summary["today_schedule_count"] != 1:
    raise SystemExit("dashboard summary should count one scheduled fact for today")
if len(payload["blocked_items"]) != 1 or int(payload["blocked_items"][0]["id"]) != int(blocked_entry_id):
    raise SystemExit("dashboard blocked_items should surface the blocked entry")
if payload["blocked_items"][0]["scheduling_gate_state"] != "warning" or payload["blocked_items"][0]["scheduling_gate_reason"] != "requirement_pending":
    raise SystemExit("dashboard blocked_items should preserve scheduling gate warning contract")
if len(payload["pending_approvals"]) != 1 or int(payload["pending_approvals"][0]["id"]) != int(pending_approval_entry_id):
    raise SystemExit("dashboard pending_approvals should surface the ready unapproved entry")
if payload["pending_approvals"][0]["formal_approval_state"] != "pending":
    raise SystemExit("dashboard pending_approvals should preserve pending formal approval state")
if len(payload["pending_requirements"]) != 1 or int(payload["pending_requirements"][0]["id"]) != int(blocked_entry_id):
    raise SystemExit("dashboard pending_requirements should surface the blocked requirement-pending entry")
if len(payload["today_entries"]) != 3:
    raise SystemExit("dashboard today_entries should include all in-scope entries")
if len(payload["scheduled_entries"]) != 1 or int(payload["scheduled_entries"][0]["id"]) != int(approved_entry_id):
    raise SystemExit("dashboard scheduled_entries should surface the scheduled fact entry")
if payload["scheduled_entries"][0]["scheduled_date"] != business_date or payload["scheduled_entries"][0]["scheduled_time"] != "09:30":
    raise SystemExit("dashboard scheduled_entries should preserve scheduled fact metadata")
if len(payload["today_schedule"]) != 1 or int(payload["today_schedule"][0]["id"]) != int(approved_entry_id):
    raise SystemExit("dashboard today_schedule should surface today's scheduled fact entry")
if len(payload["quick_actions"]) != 3:
    raise SystemExit("dashboard quick_actions should expose the first-baseline action list")
if fetch_db_snapshot() != success_before:
    raise SystemExit("dashboard aggregation API must not modify DB state")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "dashboard_vendor"
    session["vendor_name"] = "Vendor Dashboard"
vendor_response = client.get(f"/api/dashboard?sheet_id={sheet_id}")
if vendor_response.status_code != 403:
    raise SystemExit("vendor session should be forbidden from dashboard API")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor dashboard rejection should preserve vendor_auth_forbidden")

set_member_session(with_current_site=False)
missing_site = client.get(f"/api/dashboard?sheet_id={sheet_id}")
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject dashboard API with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site dashboard rejection should preserve site_context_invalid")

set_member_session()
cross_site_before = fetch_db_snapshot()
cross_site = client.get(f"/api/dashboard?sheet_id={secondary_sheet_id}")
if cross_site.status_code != 403:
    raise SystemExit("cross-site dashboard read should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "sheet_not_in_current_site":
    raise SystemExit("cross-site dashboard rejection should preserve sheet_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("cross-site dashboard rejection must not modify DB state")

print("dashboard api smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "dashboard api smoke PASS" not in result.stdout:
        raise AssertionError("dashboard api smoke subprocess did not report PASS.")


def run_scheduling_api_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for scheduling smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for scheduling smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__scheduling_site_b__", "scheduling-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Scheduling Sheet B", 999, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("scheduling_member", "scheduling_member", member_password_hash, "member"),
    )
    member_id = int(conn.execute("SELECT id FROM users WHERE username = ?", ("scheduling_member",)).fetchone()["id"])
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("scheduling_vendor", module.generate_password_hash("vendor-pass"), "Vendor Scheduling", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("scheduling_vendor",)).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Scheduling", business_date, "2000-01-01 09:00", 2, 0, "Blocked Work", "Need permit", 0, 0),
        ).fetchone()["id"]
    )
    schedulable_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Scheduling", business_date, "2000-01-01 10:00", 3, 0, "Schedulable Work", "", 0, 1),
        ).fetchone()["id"]
    )
    unapproved_ready_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (sheet_id, "Vendor Scheduling", business_date, "2000-01-01 11:00", 1, 0, "Unapproved Ready Work", "", 0, 2),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (schedulable_entry_id, sheet_id, "scheduling_member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (secondary_sheet_id, "Vendor Scheduling", business_date, "2000-01-01 12:00", 1, 0, "Cross Site Work", "", 0, 0),
    )
    conn.commit()

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "scheduling_member"
        session["display_name"] = "scheduling_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

success_before = fetch_db_snapshot()
set_member_session()
success = client.get(f"/api/scheduling?sheet_id={sheet_id}")
if success.status_code != 200:
    raise SystemExit("scheduling success path should return 200")
payload = success.get_json()
if set(payload.keys()) != {"summary", "schedulable_entries", "blocked_entries", "scheduled_entries", "unscheduled_entries"}:
    raise SystemExit("scheduling success response should keep exact top-level contract")
summary = payload["summary"]
if set(summary.keys()) != {"schedulable_count", "blocked_count", "unscheduled_count"}:
    raise SystemExit("scheduling summary should keep exact first-baseline contract")
if summary["schedulable_count"] != 1:
    raise SystemExit("scheduling summary should count one schedulable entry")
if summary["blocked_count"] != 2:
    raise SystemExit("scheduling summary should count two blocked entries")
if summary["unscheduled_count"] != 3:
    raise SystemExit("scheduling summary should count three unscheduled entries")
if len(payload["schedulable_entries"]) != 1 or int(payload["schedulable_entries"][0]["id"]) != int(schedulable_entry_id):
    raise SystemExit("scheduling schedulable_entries should surface the approved allowed entry")
if payload["schedulable_entries"][0]["formal_approval_state"] != "approved":
    raise SystemExit("scheduling schedulable entry should preserve approved formal approval state")
if payload["schedulable_entries"][0]["scheduling_gate_state"] != "allowed":
    raise SystemExit("scheduling schedulable entry should preserve allowed scheduling gate state")
blocked_ids = {int(entry["id"]) for entry in payload["blocked_entries"]}
if blocked_ids != {int(blocked_entry_id), int(unapproved_ready_entry_id)}:
    raise SystemExit("scheduling blocked_entries should surface blocked and unapproved-ready entries")
if payload["scheduled_entries"] != []:
    raise SystemExit("scheduling scheduled_entries should remain an empty list in the first baseline")
unscheduled_ids = {int(entry["id"]) for entry in payload["unscheduled_entries"]}
if unscheduled_ids != {int(blocked_entry_id), int(schedulable_entry_id), int(unapproved_ready_entry_id)}:
    raise SystemExit("scheduling unscheduled_entries should include all in-scope entries while scheduled is empty")
if fetch_db_snapshot() != success_before:
    raise SystemExit("scheduling aggregation API must not modify DB state")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "scheduling_vendor"
    session["vendor_name"] = "Vendor Scheduling"
vendor_response = client.get(f"/api/scheduling?sheet_id={sheet_id}")
if vendor_response.status_code != 403:
    raise SystemExit("vendor session should be forbidden from scheduling API")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("vendor scheduling rejection should preserve vendor_auth_forbidden")

set_member_session(with_current_site=False)
missing_site = client.get(f"/api/scheduling?sheet_id={sheet_id}")
if missing_site.status_code != 403:
    raise SystemExit("missing current site should reject scheduling API with 403")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("missing current site scheduling rejection should preserve site_context_invalid")

set_member_session()
cross_site_before = fetch_db_snapshot()
cross_site = client.get(f"/api/scheduling?sheet_id={secondary_sheet_id}")
if cross_site.status_code != 403:
    raise SystemExit("cross-site scheduling read should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "sheet_not_in_current_site":
    raise SystemExit("cross-site scheduling rejection should preserve sheet_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("cross-site scheduling rejection must not modify DB state")

print("scheduling api smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "scheduling api smoke PASS" not in result.stdout:
        raise AssertionError("scheduling api smoke subprocess did not report PASS.")


def run_scheduling_guardrail_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.app.testing = True

business_date = module.resolve_crew_business_date()

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    default_site_row = conn.execute("SELECT id, site_name FROM sites ORDER BY id LIMIT 1").fetchone()
    if default_site_row is None:
        raise SystemExit("expected a default site for scheduling guardrail smoke")
    default_site_id = int(default_site_row["id"])
    default_site_name = str(default_site_row["site_name"])
    sheet_row = conn.execute("SELECT id FROM sheets WHERE site_id = ? ORDER BY id LIMIT 1", (default_site_id,)).fetchone()
    if sheet_row is None:
        raise SystemExit("expected a default sheet for scheduling guardrail smoke")
    sheet_id = int(sheet_row["id"])
    secondary_site_id = int(
        conn.execute(
            "INSERT INTO sites (site_name, site_code, is_active) VALUES (?, ?, 1) RETURNING id",
            ("__scheduling_guardrail_site_b__", "scheduling-guardrail-site-b"),
        ).fetchone()["id"]
    )
    secondary_sheet_id = int(
        conn.execute(
            "INSERT INTO sheets (name, sort_order, site_id, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) RETURNING id",
            ("Scheduling Guardrail Sheet B", 1000, secondary_site_id),
        ).fetchone()["id"]
    )
    member_password_hash = module.generate_password_hash("member-pass")
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("scheduling_guardrail_member", "scheduling_guardrail_member", member_password_hash, "member"),
    )
    member_id = int(
        conn.execute("SELECT id FROM users WHERE username = ?", ("scheduling_guardrail_member",)).fetchone()["id"]
    )
    conn.execute(
        "INSERT INTO user_site_permissions (user_id, site_id, role) VALUES (?, ?, ?)",
        (member_id, default_site_id, "member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("scheduling_guardrail_vendor", module.generate_password_hash("vendor-pass"), "Vendor Scheduling Guardrail", 1),
    )
    vendor_account_id = int(
        conn.execute("SELECT id FROM vendor_accounts WHERE username = ?", ("scheduling_guardrail_vendor",)).fetchone()["id"]
    )
    blocked_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (
                sheet_id,
                "Vendor Scheduling Guardrail",
                business_date,
                "2000-01-01 09:00",
                2,
                0,
                "Blocked Guardrail Work",
                "Need permit",
                0,
                0,
            ),
        ).fetchone()["id"]
    )
    schedulable_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (
                sheet_id,
                "Vendor Scheduling Guardrail",
                business_date,
                "2000-01-01 10:00",
                3,
                0,
                "Schedulable Guardrail Work",
                "",
                0,
                1,
            ),
        ).fetchone()["id"]
    )
    unapproved_ready_entry_id = int(
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            ''',
            (
                sheet_id,
                "Vendor Scheduling Guardrail",
                business_date,
                "2000-01-01 11:00",
                1,
                0,
                "Unapproved Ready Guardrail Work",
                "",
                0,
                2,
            ),
        ).fetchone()["id"]
    )
    conn.execute(
        '''
        INSERT INTO formal_approvals (
            entry_id, sheet_id, action, approval_status, approved_by, approved_at, created_at, updated_at
        ) VALUES (?, ?, 'crew_formal_approve_entry', 'approved', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (schedulable_entry_id, sheet_id, "scheduling_guardrail_member"),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (
            secondary_sheet_id,
            "Vendor Scheduling Guardrail",
            business_date,
            "2000-01-01 12:00",
            1,
            0,
            "Cross Site Guardrail Work",
            "",
            0,
            0,
        ),
    )
    conn.commit()

def fetch_db_snapshot():
    with module.db() as conn:
        return {
            "vendor_work_entries": int(conn.execute("SELECT COUNT(*) FROM vendor_work_entries").fetchone()[0]),
            "formal_approvals": int(conn.execute("SELECT COUNT(*) FROM formal_approvals").fetchone()[0]),
        }

client = module.app.test_client()

def set_member_session(*, with_current_site=True):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = int(member_id)
        session["username"] = "scheduling_guardrail_member"
        session["display_name"] = "scheduling_guardrail_member"
        session["role"] = "member"
        if with_current_site:
            session["current_site_id"] = int(default_site_id)
            session["current_site_name"] = str(default_site_name)
            session["site_selection_required"] = False

success_before = fetch_db_snapshot()
set_member_session()
success = client.get(f"/api/scheduling?sheet_id={sheet_id}")
if success.status_code != 200:
    raise SystemExit("scheduling guardrail success path should return 200")
payload = success.get_json()
expected_top_level_keys = {"summary", "schedulable_entries", "blocked_entries", "scheduled_entries", "unscheduled_entries"}
if set(payload.keys()) != expected_top_level_keys:
    raise SystemExit("scheduling guardrail should freeze exact top-level response contract")
summary = payload["summary"]
expected_summary_keys = {"schedulable_count", "blocked_count", "unscheduled_count"}
if set(summary.keys()) != expected_summary_keys:
    raise SystemExit("scheduling guardrail should freeze exact summary contract")
if summary["schedulable_count"] != 1:
    raise SystemExit("scheduling guardrail should freeze one schedulable entry")
if summary["blocked_count"] != 2:
    raise SystemExit("scheduling guardrail should freeze two blocked entries")
if summary["unscheduled_count"] != 3:
    raise SystemExit("scheduling guardrail should freeze three unscheduled entries")

schedulable_entries = payload["schedulable_entries"]
if len(schedulable_entries) != 1 or int(schedulable_entries[0]["id"]) != int(schedulable_entry_id):
    raise SystemExit("scheduling guardrail should freeze schedulable entry membership")
for entry in schedulable_entries:
    if entry["formal_approval_state"] != "approved" or entry["scheduling_gate_state"] != "allowed":
        raise SystemExit("scheduling guardrail should freeze schedulable AND decision contract")

blocked_entries = payload["blocked_entries"]
blocked_ids = {int(entry["id"]) for entry in blocked_entries}
if blocked_ids != {int(blocked_entry_id), int(unapproved_ready_entry_id)}:
    raise SystemExit("scheduling guardrail should freeze blocked entry membership")
for entry in blocked_entries:
    if not (
        entry["formal_approval_state"] != "approved"
        or entry["scheduling_gate_state"] == "warning"
    ):
        raise SystemExit("scheduling guardrail should freeze blocked OR decision contract")

if payload["scheduled_entries"] != []:
    raise SystemExit("scheduling guardrail should freeze scheduled_entries as an empty list in v1")

unscheduled_entries = payload["unscheduled_entries"]
unscheduled_ids = {int(entry["id"]) for entry in unscheduled_entries}
if unscheduled_ids != {int(blocked_entry_id), int(schedulable_entry_id), int(unapproved_ready_entry_id)}:
    raise SystemExit("scheduling guardrail should freeze unscheduled_entries membership in v1")

if fetch_db_snapshot() != success_before:
    raise SystemExit("scheduling guardrail API must not modify DB state")

with client.session_transaction() as session:
    session.clear()
    session["identity_type"] = "vendor"
    session["vendor_account_id"] = int(vendor_account_id)
    session["vendor_username"] = "scheduling_guardrail_vendor"
    session["vendor_name"] = "Vendor Scheduling Guardrail"
vendor_response = client.get(f"/api/scheduling?sheet_id={sheet_id}")
if vendor_response.status_code != 403:
    raise SystemExit("vendor session should remain forbidden from scheduling guardrail API")
vendor_payload = vendor_response.get_json()
if vendor_payload.get("ok") is not False or vendor_payload["error"]["code"] != "vendor_auth_forbidden":
    raise SystemExit("scheduling guardrail should preserve vendor_auth_forbidden")

set_member_session(with_current_site=False)
missing_site = client.get(f"/api/scheduling?sheet_id={sheet_id}")
if missing_site.status_code != 403:
    raise SystemExit("missing current site should remain rejected by scheduling guardrail API")
missing_site_payload = missing_site.get_json()
if missing_site_payload.get("ok") is not False or missing_site_payload["error"]["code"] != "site_context_invalid":
    raise SystemExit("scheduling guardrail should preserve site_context_invalid")

set_member_session()
cross_site_before = fetch_db_snapshot()
cross_site = client.get(f"/api/scheduling?sheet_id={secondary_sheet_id}")
if cross_site.status_code != 403:
    raise SystemExit("cross-site scheduling guardrail read should be rejected with 403")
cross_site_payload = cross_site.get_json()
if cross_site_payload.get("ok") is not False or cross_site_payload["error"]["code"] != "sheet_not_in_current_site":
    raise SystemExit("scheduling guardrail should preserve sheet_not_in_current_site")
if fetch_db_snapshot() != cross_site_before:
    raise SystemExit("cross-site scheduling guardrail rejection must not modify DB state")

print("scheduling guardrail smoke PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            str(ROOT_DIR),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if "scheduling guardrail smoke PASS" not in result.stdout:
        raise AssertionError("scheduling guardrail smoke subprocess did not report PASS.")


def run_site_write_isolation_readiness_smoke() -> None:
    script_path = TOOLS_DIR / "check_site_write_isolation_readiness.py"
    if not script_path.exists():
        raise AssertionError("check_site_write_isolation_readiness.py does not exist.")

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    required_fragments = (
        "PASS site write isolation readiness check passed.",
        "status: ENFORCED",
        "/api/progress",
        "/api/unit-extra",
        "/api/vendor-contact",
        "/api/vendor-work-entry",
    )
    for fragment in required_fragments:
        if fragment not in result.stdout:
            raise AssertionError(f"check_site_write_isolation_readiness.py output missing: {fragment}")


def run_admin_write_model_readiness_smoke() -> None:
    script_path = TOOLS_DIR / "check_admin_write_model_readiness.py"
    if not script_path.exists():
        raise AssertionError("check_admin_write_model_readiness.py does not exist.")

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    required_fragments = (
        "PASS admin write model readiness check passed.",
        "create_sheet",
        "delete_sheet",
        "add_task",
        "delete_task",
        "add_floor",
        "delete_floor",
        "add_unit",
        "delete_unit",
        "add_extra_field",
        "delete_extra_field",
        "save",
        "INTERNAL_SPLIT",
        "MIXED",
        "status: ENFORCED",
        "current_site_enforced: yes",
        "writes new sheet to current_site_id",
        "task delete validates task_id belongs to route sheet",
        "floor delete validates floor_id belongs to route sheet",
        "unit delete validates unit_id belongs to route sheet",
        "extra-field delete validates field_id belongs to route sheet",
        "global_settings_path: yes",
        "site_content_path: yes",
        "site_content_current_site_enforced: yes",
        "template_split: no",
        "ui_action_split: no",
        "/api/reset-sheet",
        "action: reset_sheet",
        "reset_sheet_status: ENFORCED",
        "reset_sheet_destructive_candidate: resolved",
        "destructive_candidate resolved",
    )
    for fragment in required_fragments:
        if fragment not in result.stdout:
            raise AssertionError(f"check_admin_write_model_readiness.py output missing: {fragment}")


def run_vendor_auth_foundation_smoke(db_path: Path) -> None:
    script = """
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

db_path, root_dir = sys.argv[1:3]
os.environ["APP_DB_PATH"] = db_path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
spec = importlib.util.spec_from_file_location("app_under_test", str(Path(root_dir) / "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with module.db() as conn:
    conn.row_factory = sqlite3.Row
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = 'admin'",
        (module.generate_password_hash("admin"),),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_active", module.generate_password_hash("vendor-pass"), "Vendor A", 1),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_inactive", module.generate_password_hash("vendor-pass"), "Vendor B", 0),
    )
    conn.execute(
        '''
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
        VALUES (?, ?, ?, ?)
        ''',
        ("vendor_empty", module.generate_password_hash("vendor-pass"), "Vendor Empty", 1),
    )
    conn.execute(
        '''
        INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (1, 5, "Vendor A", "Vendor Zone", "Vendor A Task"),
    )
    business_date = module.resolve_crew_business_date()
    earlier_business_date = "2000-01-01"
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (1, "Vendor A", business_date, "2000-01-01 09:00", 3, 1, "Vendor A Work 1", "Vendor A Requirement 1", 1, 0),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, pre_entry_requirement, work_headcount, entry_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (1, "Vendor A", business_date, "2000-01-01 10:00", 2, 0, "Vendor A Work 2", "Vendor A Requirement 2", 0, 1),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (1, "Vendor A", earlier_business_date, "", 5, 4, "Vendor A Work 0", 4, 2),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''',
        (1, "Vendor Other", business_date, "2000-01-01 11:00", 9, 9, "Vendor Other Work", 9, 0),
    )
    vendor_a_entry_id = conn.execute(
        "SELECT id FROM vendor_work_entries WHERE sheet_id = 1 AND vendor_name = ? AND entry_order = 0",
        ("Vendor A",),
    ).fetchone()["id"]
    vendor_a_second_entry_id = conn.execute(
        "SELECT id FROM vendor_work_entries WHERE sheet_id = 1 AND vendor_name = ? AND business_date = ? AND entry_order = 1",
        ("Vendor A", business_date),
    ).fetchone()["id"]
    vendor_other_entry_id = conn.execute(
        "SELECT id FROM vendor_work_entries WHERE sheet_id = 1 AND vendor_name = ?",
        ("Vendor Other",),
    ).fetchone()["id"]
    conn.commit()

client = module.app.test_client()

internal_login = client.post(
    "/login",
    data={"username": "admin", "display_name": "Admin", "password": "admin"},
    follow_redirects=False,
)
if internal_login.status_code != 302:
    raise SystemExit("internal login regression should still pass")
with client.session_transaction() as session:
    if session.get("user_id") is None or session.get("role") != "admin":
        raise SystemExit("internal login should still populate internal session")

internal_vendor_work_entry_regression = client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(vendor_a_entry_id),
        "sheet_id": 1,
        "vendor_name": "Vendor A",
        "business_date": business_date,
        "planned_at": "2000-01-01 09:15",
        "planned_headcount": 3,
        "actual_headcount": 1,
        "work_content": "Vendor A Work 1 Internal Regression",
        "work_headcount": 1,
        "entry_order": 0,
    },
)
if internal_vendor_work_entry_regression.status_code != 200 or not internal_vendor_work_entry_regression.get_json().get("ok"):
    raise SystemExit("internal /api/vendor-work-entry contract should remain unchanged")

with client.session_transaction() as session:
    session.clear()

vendor_login_page = client.get("/vendor/login")
if vendor_login_page.status_code != 200:
    raise SystemExit("vendor login page GET should return 200")
vendor_login_html = vendor_login_page.get_data(as_text=True)
for fragment in (
    "Vendor Login",
    'data-testid="vendor-login-page"',
    'data-testid="vendor-login-form"',
    'name="username"',
    'name="password"',
    'method="post"',
):
    if fragment not in vendor_login_html:
        raise SystemExit(f"vendor login page missing fragment: {fragment}")

vendor_home_unauthenticated = client.get("/vendor/home", follow_redirects=False)
if vendor_home_unauthenticated.status_code != 302 or not vendor_home_unauthenticated.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("unauthenticated vendor home should redirect to /vendor/login")

vendor_work_entry_page_unauthenticated = client.get("/vendor/work-entry", follow_redirects=False)
if vendor_work_entry_page_unauthenticated.status_code != 302 or not vendor_work_entry_page_unauthenticated.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("unauthenticated vendor work entry page should redirect to /vendor/login")

vendor_profile_unauthenticated = client.get("/vendor/profile", follow_redirects=False)
if vendor_profile_unauthenticated.status_code != 302 or not vendor_profile_unauthenticated.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("unauthenticated vendor profile should redirect to /vendor/login")

vendor_scope_unauthenticated = client.get("/vendor/scope", follow_redirects=False)
if vendor_scope_unauthenticated.status_code != 302 or not vendor_scope_unauthenticated.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("unauthenticated vendor scope should redirect to /vendor/login")

vendor_business_preview_unauthenticated = client.get("/vendor/business-read-preview", follow_redirects=False)
if vendor_business_preview_unauthenticated.status_code != 302 or not vendor_business_preview_unauthenticated.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("unauthenticated vendor business read preview should redirect to /vendor/login")
with client.session_transaction() as session:
    for key in ("identity_type", "vendor_account_id", "vendor_username", "vendor_name"):
        if session.get(key) is not None:
            raise SystemExit("unauthenticated vendor business read preview should not create vendor session")
    if session.get("user_id") is not None or session.get("role") is not None:
        raise SystemExit("unauthenticated vendor business read preview should not create internal session")

vendor_work_preflight_unauthenticated = client.post(
    "/api/vendor/work-entry/preflight",
    json={"sheet_id": 1, "business_date": business_date},
)
if vendor_work_preflight_unauthenticated.status_code != 403:
    raise SystemExit("unauthenticated vendor work-entry preflight should return 403")
vendor_work_preflight_unauthenticated_payload = vendor_work_preflight_unauthenticated.get_json()
if vendor_work_preflight_unauthenticated_payload["error"]["code"] != "vendor_auth_required":
    raise SystemExit("unauthenticated vendor work-entry preflight should preserve vendor_auth_required")

with client.session_transaction() as session:
    session["user_id"] = 999
    session["role"] = "admin"
    session["current_site_id"] = 123
    session["current_site_name"] = "Leaked Site"

internal_vendor_profile = client.get("/vendor/profile", follow_redirects=False)
if internal_vendor_profile.status_code != 302 or not internal_vendor_profile.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("internal session must not access vendor-only endpoint")

internal_vendor_scope = client.get("/vendor/scope", follow_redirects=False)
if internal_vendor_scope.status_code != 302 or not internal_vendor_scope.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("internal session must not access vendor-only scope endpoint")

internal_vendor_business_preview = client.get("/vendor/business-read-preview", follow_redirects=False)
if internal_vendor_business_preview.status_code != 302 or not internal_vendor_business_preview.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("internal session must not access vendor business read preview")

internal_vendor_work_preflight = client.post(
    "/api/vendor/work-entry/preflight",
    json={"sheet_id": 1, "business_date": business_date},
)
if internal_vendor_work_preflight.status_code != 403:
    raise SystemExit("internal session must not access vendor write preflight")
internal_vendor_work_preflight_payload = internal_vendor_work_preflight.get_json()
if internal_vendor_work_preflight_payload["error"]["code"] != "vendor_auth_required":
    raise SystemExit("internal vendor write preflight should preserve vendor_auth_required")

wrong_password = client.post(
    "/vendor/login",
    data={"username": "vendor_active", "password": "wrong-pass"},
    follow_redirects=False,
)
if wrong_password.status_code != 200:
    raise SystemExit("vendor wrong password should render login page")
wrong_password_html = wrong_password.get_data(as_text=True)
if 'data-testid="vendor-login-error"' not in wrong_password_html:
    raise SystemExit("vendor wrong password should render template error state")
with client.session_transaction() as session:
    if session.get("identity_type") is not None:
        raise SystemExit("vendor wrong password should not create vendor session")
    if session.get("user_id") is not None or session.get("role") is not None:
        raise SystemExit("vendor wrong password should not create internal session")
    if session.get("current_site_id") is not None or session.get("current_site_name") is not None:
        raise SystemExit("vendor wrong password should clear stale current-site session")

inactive_vendor = client.post(
    "/vendor/login",
    data={"username": "vendor_inactive", "password": "vendor-pass"},
    follow_redirects=False,
)
if inactive_vendor.status_code != 200:
    raise SystemExit("inactive vendor should render login page")
with client.session_transaction() as session:
    if session.get("identity_type") is not None or session.get("vendor_account_id") is not None:
        raise SystemExit("inactive vendor should not create vendor session")

valid_vendor = client.post(
    "/vendor/login",
    data={"username": "vendor_active", "password": "vendor-pass"},
    follow_redirects=False,
)
if valid_vendor.status_code != 302 or not valid_vendor.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("vendor valid login should redirect to /vendor/login")
with client.session_transaction() as session:
    if session.get("identity_type") != "vendor":
        raise SystemExit("vendor valid login should set identity_type=vendor")
    if session.get("vendor_username") != "vendor_active":
        raise SystemExit("vendor valid login should set vendor_username")
    if session.get("vendor_name") != "Vendor A":
        raise SystemExit("vendor valid login should set vendor_name")
    if session.get("vendor_account_id") is None:
        raise SystemExit("vendor valid login should set vendor_account_id")
    if session.get("user_id") is not None or session.get("role") is not None:
        raise SystemExit("vendor session must not contain internal user_id/role")
    if session.get("current_site_id") is not None or session.get("current_site_name") is not None:
        raise SystemExit("vendor session must not contain internal current-site session")

vendor_work_preflight = client.post(
    "/api/vendor/work-entry/preflight",
    json={
        "sheet_id": 1,
        "business_date": business_date,
        "vendor_name": "Vendor A",
    },
)
if vendor_work_preflight.status_code != 200:
    raise SystemExit("vendor write preflight should return 200 for authenticated vendor")
vendor_work_preflight_payload = vendor_work_preflight.get_json()
if not isinstance(vendor_work_preflight_payload, dict) or vendor_work_preflight_payload.get("ok") is not True:
    raise SystemExit("vendor write preflight should return ok=true payload")
preflight = vendor_work_preflight_payload.get("preflight")
if not isinstance(preflight, dict):
    raise SystemExit("vendor write preflight should return preflight context")
expected_preflight_keys = {
    "vendor_account_id",
    "vendor_username",
    "vendor_name",
    "sheet_id",
    "business_date",
    "entry_id",
    "write_mode",
}
if set(preflight.keys()) != expected_preflight_keys:
    raise SystemExit("vendor write preflight should return stable preflight context shape")
if preflight.get("vendor_username") != "vendor_active" or preflight.get("vendor_name") != "Vendor A":
    raise SystemExit("vendor write preflight must use authenticated vendor identity")
if preflight.get("sheet_id") != 1 or preflight.get("business_date") != business_date:
    raise SystemExit("vendor write preflight should return trusted write context")
if preflight.get("entry_id") is not None or preflight.get("write_mode") != "create":
    raise SystemExit("vendor write preflight create should return entry_id=None and write_mode=create")
with client.session_transaction() as session:
    if session.get("current_site_id") is not None or session.get("current_site_name") is not None:
        raise SystemExit("vendor write preflight must not create current-site session")

vendor_work_preflight_mismatch = client.post(
    "/api/vendor/work-entry/preflight",
    json={
        "sheet_id": 1,
        "business_date": business_date,
        "vendor_name": "Vendor Other",
    },
)
if vendor_work_preflight_mismatch.status_code != 403:
    raise SystemExit("vendor_name mismatch should be rejected with 403")
vendor_work_preflight_mismatch_payload = vendor_work_preflight_mismatch.get_json()
if vendor_work_preflight_mismatch_payload["error"]["code"] != "vendor_name_mismatch":
    raise SystemExit("vendor_name mismatch should preserve vendor_name_mismatch error code")

vendor_work_preflight_cross_vendor = client.post(
    "/api/vendor/work-entry/preflight",
    json={
        "id": int(vendor_other_entry_id),
        "sheet_id": 1,
        "business_date": business_date,
        "vendor_name": "Vendor A",
    },
)
if vendor_work_preflight_cross_vendor.status_code != 403:
    raise SystemExit("vendor cross-vendor preflight should be rejected with 403")
vendor_work_preflight_cross_vendor_payload = vendor_work_preflight_cross_vendor.get_json()
if vendor_work_preflight_cross_vendor_payload["error"]["code"] != "vendor_cross_vendor_write_forbidden":
    raise SystemExit("vendor cross-vendor preflight should preserve vendor_cross_vendor_write_forbidden")

vendor_work_preflight_update = client.post(
    "/api/vendor/work-entry/preflight",
    json={
        "id": int(vendor_a_entry_id),
        "sheet_id": 1,
        "business_date": business_date,
        "vendor_name": "Vendor A",
    },
)
if vendor_work_preflight_update.status_code != 200:
    raise SystemExit("vendor update preflight should return 200 when business_date matches existing entry")
vendor_work_preflight_update_payload = vendor_work_preflight_update.get_json()
vendor_work_preflight_update_context = vendor_work_preflight_update_payload.get("preflight")
if vendor_work_preflight_update_context.get("entry_id") != int(vendor_a_entry_id) or vendor_work_preflight_update_context.get("write_mode") != "update":
    raise SystemExit("vendor update preflight should preserve trusted update context")

vendor_work_preflight_business_date_mismatch = client.post(
    "/api/vendor/work-entry/preflight",
    json={
        "id": int(vendor_a_entry_id),
        "sheet_id": 1,
        "business_date": earlier_business_date,
        "vendor_name": "Vendor A",
    },
)
if vendor_work_preflight_business_date_mismatch.status_code != 409:
    raise SystemExit("vendor update preflight business_date mismatch should be rejected with 409")
vendor_work_preflight_business_date_mismatch_payload = vendor_work_preflight_business_date_mismatch.get_json()
if vendor_work_preflight_business_date_mismatch_payload["error"]["code"] != "vendor_business_date_mismatch":
    raise SystemExit("vendor update preflight business_date mismatch should preserve vendor_business_date_mismatch")

vendor_work_internal_route_with_vendor_session = client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": 1,
        "vendor_name": "Vendor A",
        "business_date": business_date,
        "planned_at": "",
        "planned_headcount": 1,
        "actual_headcount": 0,
        "work_content": "Vendor Route Should Not Hit Internal Route",
        "work_headcount": 0,
        "entry_order": 0,
    },
    follow_redirects=False,
)
if vendor_work_internal_route_with_vendor_session.status_code != 302 or not vendor_work_internal_route_with_vendor_session.headers.get("Location", "").endswith("/login"):
    raise SystemExit("vendor session must not pass internal /api/vendor-work-entry route")

vendor_logged_in_page = client.get("/vendor/login")
if vendor_logged_in_page.status_code != 200:
    raise SystemExit("vendor logged-in page GET should return 200")
vendor_logged_in_html = vendor_logged_in_page.get_data(as_text=True)
for fragment in (
    'data-testid="vendor-login-success"',
    'data-testid="vendor-logout-link"',
    "Vendor A",
    "vendor_active",
):
    if fragment not in vendor_logged_in_html:
        raise SystemExit(f"vendor logged-in page missing fragment: {fragment}")

vendor_home = client.get("/vendor/home", follow_redirects=False)
if vendor_home.status_code != 200:
    raise SystemExit("vendor authenticated home should return 200")
vendor_home_body = vendor_home.get_data(as_text=True)
for fragment in ('data-testid="vendor-work-entry-page"', "Vendor Home:", "Vendor A", "vendor_active"):
    if fragment not in vendor_home_body:
        raise SystemExit(f"vendor home missing fragment: {fragment}")

vendor_work_entry_page = client.get("/vendor/work-entry", follow_redirects=False)
if vendor_work_entry_page.status_code != 200:
    raise SystemExit("vendor authenticated work entry page should return 200")
vendor_work_entry_page_html = vendor_work_entry_page.get_data(as_text=True)
for fragment in (
    'data-testid="vendor-work-entry-today-entries"',
    'data-testid="vendor-work-entry-today-entry-status-line"',
    'data-testid="vendor-work-entry-today-entry-count"',
    'data-testid="vendor-work-entry-today-entry-list"',
    'data-testid="vendor-work-entry-today-entry-item"',
    'data-testid="vendor-work-entry-today-entry-switch"',
    'data-testid="vendor-work-entry-new-entry-link"',
    'data-testid="vendor-work-entry-today-entry-id"',
    'data-testid="vendor-work-entry-today-entry-active"',
    'data-testid="vendor-work-entry-today-entry-active-id"',
    'data-testid="vendor-work-entry-readiness-summary"',
    'data-testid="vendor-work-entry-pending-items"',
    'data-testid="vendor-work-entry-draft-submit"',
    'data-testid="vendor-work-entry-history"',
    'data-testid="vendor-work-entry-profile"',
    'data-testid="vendor-work-entry-scope"',
    'data-testid="vendor-work-entry-preview"',
    'data-testid="vendor-work-entry-preflight"',
    'data-vendor-preflight-available="true"',
    "Vendor A",
    "vendor_active",
    business_date,
):
    if fragment not in vendor_work_entry_page_html:
        raise SystemExit(f"vendor work entry page missing fragment: {fragment}")
if "2000-01-01 09:15" not in vendor_work_entry_page_html or "2000-01-01 10:00" not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry page should render today's multiple planned entries")
if "You are viewing an existing planned entry for today. Switching entries aligns the draft form with that entry's update context." not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry page should explain selected-entry navigation status")
for fragment in (
    'data-testid="vendor-work-entry-summary-business-date"',
    'data-testid="vendor-work-entry-summary-vendor-name"',
    'data-testid="vendor-work-entry-summary-status-line"',
    'data-testid="vendor-work-entry-summary-active-entry-id"',
    'data-testid="vendor-work-entry-summary-write-mode"',
    'data-testid="vendor-work-entry-summary-entry-id"',
    'data-testid="vendor-work-entry-summary-pending-item-count"',
    'data-testid="vendor-work-entry-summary-pending-items"',
    "update",
    "Vendor A",
):
    if fragment not in vendor_work_entry_page_html:
        raise SystemExit(f"vendor work entry readiness summary missing fragment: {fragment}")
if "You are viewing an existing entry that is ready for update." not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry readiness summary should explain selected-entry update status")
for fragment in (
    'data-testid="vendor-work-entry-pending-items-helper"',
    'data-testid="vendor-work-entry-pending-items-count"',
):
    if fragment not in vendor_work_entry_page_html:
        raise SystemExit(f"vendor work entry pending items missing fragment: {fragment}")
if (
    'data-testid="vendor-work-entry-pending-items-list"' not in vendor_work_entry_page_html
    and 'data-testid="vendor-work-entry-pending-items-empty"' not in vendor_work_entry_page_html
):
    raise SystemExit("vendor work entry pending items should render either list or empty state")
for fragment in (
    'data-testid="vendor-work-entry-history-list"',
    'data-testid="vendor-work-entry-history-item"',
    'data-testid="vendor-work-entry-history-business-date"',
    'data-testid="vendor-work-entry-history-has-work-content"',
):
    if fragment not in vendor_work_entry_page_html:
        raise SystemExit(f"vendor work entry history missing fragment: {fragment}")
for fragment in (
    'data-testid="vendor-work-entry-draft-business-date"',
    'data-testid="vendor-work-entry-draft-entry-id"',
    'data-testid="vendor-work-entry-draft-write-mode"',
    'data-testid="vendor-work-entry-draft-hidden-entry-id"',
    'data-testid="vendor-work-entry-draft-planned-at"',
    'data-testid="vendor-work-entry-draft-submit-button"',
    'data-testid="vendor-work-entry-draft-context-group"',
    'data-testid="vendor-work-entry-draft-work-group"',
    'data-testid="vendor-work-entry-draft-pre-entry-requirement"',
    'data-testid="vendor-work-entry-draft-validation-summary"',
    'data-testid="vendor-work-entry-draft-validation-error-planned-at"',
    'data-testid="vendor-work-entry-draft-validation-error-planned-headcount"',
    'data-testid="vendor-work-entry-draft-validation-error-actual-headcount"',
    'data-testid="vendor-work-entry-draft-validation-error-work-headcount"',
    'data-testid="vendor-work-entry-draft-validation-error-entry-order"',
    'data-vendor-work-entry-submit-url="/api/vendor-work-entry"',
    'data-vendor-work-entry-context="trusted"',
    'data-submit-enabled="true"',
):
    if fragment not in vendor_work_entry_page_html:
        raise SystemExit(f"vendor work entry draft submit preparation missing fragment: {fragment}")
if 'data-testid="vendor-work-entry-draft-submit-button" disabled' in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry draft submit button should be enabled for first write wiring")
expected_default_entry_id_fragment = f'data-testid="vendor-work-entry-today-entry-active-id">{vendor_a_entry_id}<'
if expected_default_entry_id_fragment not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry page should align active today entry id with default selected entry")
if f'data-testid="vendor-work-entry-summary-active-entry-id">{vendor_a_entry_id}<' not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry readiness summary should expose active entry id")
if f'data-testid="vendor-work-entry-summary-entry-id">{vendor_a_entry_id}<' not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry readiness summary entry_id should align with active entry preflight")
if f'data-testid="vendor-work-entry-draft-entry-id">{vendor_a_entry_id}<' not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry draft visible entry id should align with active entry preflight")
if f'data-testid="vendor-work-entry-draft-write-mode">update<' not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry draft write mode should align with active entry preflight")
if f'data-testid="vendor-work-entry-draft-hidden-entry-id"' not in vendor_work_entry_page_html or f'value="{vendor_a_entry_id}"' not in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry draft hidden entry id should align with active entry preflight")
def extract_input_value_by_testid(html: str, testid: str) -> str:
    marker = f'data-testid="{testid}"'
    marker_index = html.find(marker)
    if marker_index == -1:
        raise SystemExit(f"vendor work entry page should expose input marker: {testid}")
    tag_start = html.rfind("<input", 0, marker_index)
    if tag_start == -1:
        raise SystemExit(f"vendor work entry page input marker should belong to an input tag: {testid}")
    tag_end = html.find(">", marker_index)
    if tag_end == -1:
        raise SystemExit(f"vendor work entry page input tag should terminate: {testid}")
    input_tag = html[tag_start:tag_end]
    value_marker = 'value="'
    value_index = input_tag.find(value_marker)
    if value_index == -1:
        raise SystemExit(f"vendor work entry page input marker should expose value: {testid}")
    value_start = value_index + len(value_marker)
    value_end = input_tag.find('"', value_start)
    if value_end == -1:
        raise SystemExit(f"vendor work entry page input value should terminate: {testid}")
    return input_tag[value_start:value_end]


def extract_textarea_value_by_testid(html: str, testid: str) -> str:
    marker = f'data-testid="{testid}"'
    marker_index = html.find(marker)
    if marker_index == -1:
        raise SystemExit(f"vendor work entry page should expose textarea marker: {testid}")
    tag_start = html.rfind("<textarea", 0, marker_index)
    if tag_start == -1:
        raise SystemExit(f"vendor work entry page textarea marker should belong to a textarea tag: {testid}")
    content_start = html.find(">", marker_index)
    if content_start == -1:
        raise SystemExit(f"vendor work entry page textarea tag should terminate: {testid}")
    content_start += 1
    content_end = html.find("</textarea>", content_start)
    if content_end == -1:
        raise SystemExit(f"vendor work entry page textarea content should terminate: {testid}")
    return html[content_start:content_end]


def extract_hidden_vendor_work_entry_id(html: str) -> str:
    return extract_input_value_by_testid(html, "vendor-work-entry-draft-hidden-entry-id")


if "Vendor A Requirement 1" in vendor_work_entry_page_html:
    raise SystemExit("vendor work entry selected-entry mode should not show stale pre-entry requirement after internal update")
if extract_textarea_value_by_testid(vendor_work_entry_page_html, "vendor-work-entry-draft-pre-entry-requirement") != "":
    raise SystemExit("vendor work entry selected-entry mode should align draft pre-entry requirement with updated entry state")


def fetch_vendor_work_entry_snapshot(entry_id: int) -> dict[str, object]:
    row = conn.execute(
        '''
        SELECT
            id,
            vendor_name,
            business_date,
            planned_at,
            planned_headcount,
            actual_headcount,
            work_content,
            pre_entry_requirement,
            work_headcount,
            entry_order
        FROM vendor_work_entries
        WHERE id = ?
        ''',
        (int(entry_id),),
    ).fetchone()
    if row is None:
        raise SystemExit(f"vendor work entry {entry_id} should exist")
    return dict(row)


def build_internal_vendor_work_entry_update_client():
    internal_client = module.app.test_client()
    internal_login = internal_client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if internal_login.status_code != 302:
        raise SystemExit("internal login should succeed for selected entry submit target verification")
    return internal_client

vendor_work_entry_page_first_today_entry = client.get(
    "/vendor/work-entry?today_entry_index=0",
    follow_redirects=False,
)
if vendor_work_entry_page_first_today_entry.status_code != 200:
    raise SystemExit("vendor work entry page should return 200 when today entry index is 0")

vendor_work_entry_page_second_today_entry = client.get(
    "/vendor/work-entry?today_entry_index=1",
    follow_redirects=False,
)
if vendor_work_entry_page_second_today_entry.status_code != 200:
    raise SystemExit("vendor work entry page should return 200 when switching today entry index")
vendor_work_entry_page_second_today_entry_html = vendor_work_entry_page_second_today_entry.get_data(as_text=True)
for fragment in (
    'data-testid="vendor-work-entry-today-entries"',
    'data-testid="vendor-work-entry-today-entry-status-line"',
    'data-testid="vendor-work-entry-today-entry-count"',
    'data-testid="vendor-work-entry-today-entry-id"',
    'data-testid="vendor-work-entry-today-entry-active"',
    'data-testid="vendor-work-entry-today-entry-active-id"',
    'data-testid="vendor-work-entry-readiness-summary"',
    'data-testid="vendor-work-entry-summary-status-line"',
    'data-testid="vendor-work-entry-summary-active-entry-id"',
    'data-testid="vendor-work-entry-summary-entry-id"',
    'data-testid="vendor-work-entry-draft-submit"',
    'data-testid="vendor-work-entry-draft-entry-id"',
    'data-testid="vendor-work-entry-draft-hidden-entry-id"',
    'data-testid="vendor-work-entry-draft-write-mode"',
    'data-testid="vendor-work-entry-draft-pre-entry-requirement"',
    'data-testid="vendor-work-entry-history"',
    'data-testid="vendor-work-entry-pending-items"',
    "2000-01-01 10:00",
    "update",
):
    if fragment not in vendor_work_entry_page_second_today_entry_html:
        raise SystemExit(f"vendor work entry page missing switched today entry fragment: {fragment}")
if f'data-testid="vendor-work-entry-today-entry-active-id">{vendor_a_second_entry_id}<' not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched page should expose selected active entry id")
if f'data-testid="vendor-work-entry-summary-active-entry-id">{vendor_a_second_entry_id}<' not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched readiness summary should expose selected active entry id")
if f'data-testid="vendor-work-entry-summary-entry-id">{vendor_a_second_entry_id}<' not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched readiness summary entry_id should align with selected active entry")
if f'data-testid="vendor-work-entry-draft-entry-id">{vendor_a_second_entry_id}<' not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched draft visible entry id should align with selected active entry")
if f'data-testid="vendor-work-entry-draft-hidden-entry-id"' not in vendor_work_entry_page_second_today_entry_html or f'value="{vendor_a_second_entry_id}"' not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched draft hidden entry id should align with selected active entry")
if f'data-testid="vendor-work-entry-draft-write-mode">update<' not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched draft write mode should align with selected active entry")
if "You are viewing an existing entry that is ready for update." not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched readiness summary should explain selected-entry update status")
if "You are viewing an existing planned entry for today. Switching entries aligns the draft form with that entry's update context." not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched page should explain selected-entry navigation status")
if "Vendor A Requirement 2" not in vendor_work_entry_page_second_today_entry_html:
    raise SystemExit("vendor work entry switched selected-entry mode should display the second entry pre-entry requirement")

vendor_work_entry_page_new_entry_mode = client.get(
    "/vendor/work-entry?new_entry=1",
    follow_redirects=False,
)
if vendor_work_entry_page_new_entry_mode.status_code != 200:
    raise SystemExit("vendor work entry page should return 200 when switching to new entry mode")
vendor_work_entry_page_new_entry_mode_html = vendor_work_entry_page_new_entry_mode.get_data(as_text=True)
for fragment in (
    'data-testid="vendor-work-entry-new-entry-link"',
    'data-testid="vendor-work-entry-today-entry-status-line"',
    'data-testid="vendor-work-entry-create-mode"',
    'data-testid="vendor-work-entry-readiness-summary"',
    'data-testid="vendor-work-entry-summary-status-line"',
    'data-testid="vendor-work-entry-draft-submit"',
    'data-testid="vendor-work-entry-history"',
    'data-testid="vendor-work-entry-pending-items"',
):
    if fragment not in vendor_work_entry_page_new_entry_mode_html:
        raise SystemExit(f"vendor work entry new entry mode missing fragment: {fragment}")
if f'data-testid="vendor-work-entry-draft-write-mode">create<' not in vendor_work_entry_page_new_entry_mode_html:
    raise SystemExit("vendor work entry new entry mode should expose create write mode")
if extract_hidden_vendor_work_entry_id(vendor_work_entry_page_new_entry_mode_html) != "":
    raise SystemExit("vendor work entry new entry mode should keep hidden entry id empty")
if extract_input_value_by_testid(vendor_work_entry_page_new_entry_mode_html, "vendor-work-entry-draft-entry-order") != "2":
    raise SystemExit("vendor work entry new entry mode should default entry_order to today's entry count")
if "You are preparing a new entry for today." not in vendor_work_entry_page_new_entry_mode_html:
    raise SystemExit("vendor work entry create mode readiness summary should explain create status")
if "You are preparing a new planned entry for today, not editing an existing one." not in vendor_work_entry_page_new_entry_mode_html:
    raise SystemExit("vendor work entry create mode should explain create-mode navigation status")
if extract_textarea_value_by_testid(vendor_work_entry_page_new_entry_mode_html, "vendor-work-entry-draft-pre-entry-requirement") != "":
    raise SystemExit("vendor work entry create mode should keep pre-entry requirement empty by default")
vendor_work_entry_count_before_new_entry_submit = conn.execute(
    "SELECT COUNT(*) FROM vendor_work_entries"
).fetchone()[0]
if vendor_work_entry_count_before_new_entry_submit != 4:
    raise SystemExit("vendor work entry baseline should start with four total seeded rows before create-mode submit verification")
first_entry_before_new_entry_submit = fetch_vendor_work_entry_snapshot(vendor_a_entry_id)
second_entry_before_new_entry_submit = fetch_vendor_work_entry_snapshot(vendor_a_second_entry_id)
create_mode_sheet_id = extract_input_value_by_testid(
    vendor_work_entry_page_new_entry_mode_html,
    "vendor-work-entry-draft-hidden-sheet-id",
)
create_mode_business_date = extract_input_value_by_testid(
    vendor_work_entry_page_new_entry_mode_html,
    "vendor-work-entry-draft-hidden-business-date",
)
create_mode_vendor_name = extract_input_value_by_testid(
    vendor_work_entry_page_new_entry_mode_html,
    "vendor-work-entry-draft-hidden-vendor-name",
)
create_mode_entry_order = extract_input_value_by_testid(
    vendor_work_entry_page_new_entry_mode_html,
    "vendor-work-entry-draft-entry-order",
)
create_mode_submit_client = build_internal_vendor_work_entry_update_client()
create_mode_submit = create_mode_submit_client.post(
    "/api/vendor-work-entry",
    json={
        "sheet_id": int(create_mode_sheet_id),
        "vendor_name": create_mode_vendor_name,
        "business_date": create_mode_business_date,
        "planned_at": "2000-01-01 11:00",
        "planned_headcount": 4,
        "actual_headcount": 0,
        "work_content": "Create mode third entry verification",
        "pre_entry_requirement": "Create mode requirement verification",
        "work_headcount": 0,
        "entry_order": int(create_mode_entry_order),
    },
    follow_redirects=False,
)
if create_mode_submit.status_code != 200:
    raise SystemExit("vendor work entry create-mode submit should return 200")
create_mode_submit_payload = create_mode_submit.get_json()
if not isinstance(create_mode_submit_payload, dict) or create_mode_submit_payload.get("ok") is not True:
    raise SystemExit("vendor work entry create-mode submit should return ok=true payload")
created_entry_payload = create_mode_submit_payload.get("entry")
if not isinstance(created_entry_payload, dict):
    raise SystemExit("vendor work entry create-mode submit should return created entry payload")
if created_entry_payload.get("pre_entry_requirement") != "Create mode requirement verification":
    raise SystemExit("vendor work entry create-mode submit should return persisted pre_entry_requirement in response payload")
created_entry_id = int(created_entry_payload.get("id"))
if created_entry_id in {int(vendor_a_entry_id), int(vendor_a_second_entry_id)}:
    raise SystemExit("vendor work entry create-mode submit should create a new row instead of reusing existing today entry ids")
vendor_work_entry_count_after_new_entry_submit = conn.execute(
    "SELECT COUNT(*) FROM vendor_work_entries"
).fetchone()[0]
if vendor_work_entry_count_after_new_entry_submit != vendor_work_entry_count_before_new_entry_submit + 1:
    raise SystemExit("vendor work entry create-mode submit should add exactly one row")
first_entry_after_new_entry_submit = fetch_vendor_work_entry_snapshot(vendor_a_entry_id)
second_entry_after_new_entry_submit = fetch_vendor_work_entry_snapshot(vendor_a_second_entry_id)
if first_entry_after_new_entry_submit != first_entry_before_new_entry_submit:
    raise SystemExit("vendor work entry create-mode submit must not mutate the first existing today entry")
if second_entry_after_new_entry_submit != second_entry_before_new_entry_submit:
    raise SystemExit("vendor work entry create-mode submit must not mutate the second existing today entry")
created_entry_snapshot = fetch_vendor_work_entry_snapshot(created_entry_id)
if str(created_entry_snapshot["vendor_name"]) != "Vendor A":
    raise SystemExit("vendor work entry create-mode submit should preserve vendor name for the new row")
if str(created_entry_snapshot["business_date"]) != business_date:
    raise SystemExit("vendor work entry create-mode submit should preserve business_date for the new row")
if int(created_entry_snapshot["entry_order"]) != 2:
    raise SystemExit("vendor work entry create-mode submit should use the default today-entry-count entry_order for the new row")
if str(created_entry_snapshot["work_content"]) != "Create mode third entry verification":
    raise SystemExit("vendor work entry create-mode submit should persist the submitted work_content for the new row")
if str(created_entry_snapshot["pre_entry_requirement"]) != "Create mode requirement verification":
    raise SystemExit("vendor work entry create-mode submit should persist the submitted pre_entry_requirement for the new row")
vendor_work_entry_page_after_new_entry_submit = client.get(
    "/vendor/work-entry",
    follow_redirects=False,
)
if vendor_work_entry_page_after_new_entry_submit.status_code != 200:
    raise SystemExit("vendor work entry page should return 200 after create-mode submit")
vendor_work_entry_page_after_new_entry_submit_html = vendor_work_entry_page_after_new_entry_submit.get_data(as_text=True)
for fragment in (
    'data-testid="vendor-work-entry-readiness-summary"',
    'data-testid="vendor-work-entry-draft-submit"',
    'data-testid="vendor-work-entry-history"',
    'data-testid="vendor-work-entry-pending-items"',
    'data-testid="vendor-work-entry-today-entry-count">3<',
    "2000-01-01 11:00",
):
    if fragment not in vendor_work_entry_page_after_new_entry_submit_html:
        raise SystemExit(f"vendor work entry page should reflect the newly created third entry: {fragment}")

vendor_work_entry_page_first_today_entry_html = vendor_work_entry_page_first_today_entry.get_data(as_text=True)
selected_first_entry_id = extract_hidden_vendor_work_entry_id(vendor_work_entry_page_first_today_entry_html)
if selected_first_entry_id != str(vendor_a_entry_id):
    raise SystemExit("selected first today entry should submit with first entry id")
vendor_work_entry_count_before_first_selected_submit = conn.execute(
    "SELECT COUNT(*) FROM vendor_work_entries"
).fetchone()[0]
first_entry_before_first_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_entry_id)
second_entry_before_first_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_second_entry_id)
selected_first_entry_submit_client = build_internal_vendor_work_entry_update_client()
selected_first_entry_submit = selected_first_entry_submit_client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(selected_first_entry_id),
        "sheet_id": 1,
        "vendor_name": str(first_entry_before_first_selected_submit["vendor_name"]),
        "business_date": str(first_entry_before_first_selected_submit["business_date"]),
        "planned_at": str(first_entry_before_first_selected_submit["planned_at"]),
        "planned_headcount": int(first_entry_before_first_selected_submit["planned_headcount"]),
        "actual_headcount": int(first_entry_before_first_selected_submit["actual_headcount"]),
        "work_content": "Selected first entry target verification",
        "pre_entry_requirement": "Selected first requirement verification",
        "work_headcount": int(first_entry_before_first_selected_submit["work_headcount"]),
        "entry_order": int(first_entry_before_first_selected_submit["entry_order"]),
    },
    follow_redirects=False,
)
if selected_first_entry_submit.status_code != 200:
    raise SystemExit("selected first today entry submit should return 200")
selected_first_entry_submit_payload = selected_first_entry_submit.get_json()
if not isinstance(selected_first_entry_submit_payload, dict) or selected_first_entry_submit_payload.get("ok") is not True:
    raise SystemExit("selected first today entry submit should return ok=true payload")
selected_first_entry_response = selected_first_entry_submit_payload.get("entry")
if not isinstance(selected_first_entry_response, dict):
    raise SystemExit("selected first today entry submit should return entry payload")
if int(selected_first_entry_response.get("id") or 0) != int(vendor_a_entry_id):
    raise SystemExit("selected first today entry submit should preserve first entry id")
if selected_first_entry_response.get("pre_entry_requirement") != "Selected first requirement verification":
    raise SystemExit("selected first today entry submit should return updated pre_entry_requirement")
vendor_work_entry_count_after_first_selected_submit = conn.execute(
    "SELECT COUNT(*) FROM vendor_work_entries"
).fetchone()[0]
if vendor_work_entry_count_after_first_selected_submit != vendor_work_entry_count_before_first_selected_submit:
    raise SystemExit("selected first today entry submit must not create a new vendor work entry row")
first_entry_after_first_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_entry_id)
second_entry_after_first_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_second_entry_id)
if first_entry_after_first_selected_submit["work_content"] != "Selected first entry target verification":
    raise SystemExit("selected first today entry submit should update the first entry only")
if first_entry_after_first_selected_submit["pre_entry_requirement"] != "Selected first requirement verification":
    raise SystemExit("selected first today entry submit should update pre_entry_requirement for the first entry only")
if second_entry_after_first_selected_submit != second_entry_before_first_selected_submit:
    raise SystemExit("selected first today entry submit must not mutate the second entry")

selected_second_entry_id = extract_hidden_vendor_work_entry_id(vendor_work_entry_page_second_today_entry_html)
if selected_second_entry_id != str(vendor_a_second_entry_id):
    raise SystemExit("selected second today entry should submit with second entry id")
vendor_work_entry_count_before_second_selected_submit = conn.execute(
    "SELECT COUNT(*) FROM vendor_work_entries"
).fetchone()[0]
first_entry_before_second_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_entry_id)
second_entry_before_second_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_second_entry_id)
selected_second_entry_submit_client = build_internal_vendor_work_entry_update_client()
selected_second_entry_submit = selected_second_entry_submit_client.post(
    "/api/vendor-work-entry",
    json={
        "id": int(selected_second_entry_id),
        "sheet_id": 1,
        "vendor_name": str(second_entry_before_second_selected_submit["vendor_name"]),
        "business_date": str(second_entry_before_second_selected_submit["business_date"]),
        "planned_at": str(second_entry_before_second_selected_submit["planned_at"]),
        "planned_headcount": int(second_entry_before_second_selected_submit["planned_headcount"]),
        "actual_headcount": int(second_entry_before_second_selected_submit["actual_headcount"]),
        "work_content": "Selected second entry target verification",
        "pre_entry_requirement": "Selected second requirement verification",
        "work_headcount": int(second_entry_before_second_selected_submit["work_headcount"]),
        "entry_order": int(second_entry_before_second_selected_submit["entry_order"]),
    },
    follow_redirects=False,
)
if selected_second_entry_submit.status_code != 200:
    raise SystemExit("selected second today entry submit should return 200")
selected_second_entry_submit_payload = selected_second_entry_submit.get_json()
if not isinstance(selected_second_entry_submit_payload, dict) or selected_second_entry_submit_payload.get("ok") is not True:
    raise SystemExit("selected second today entry submit should return ok=true payload")
selected_second_entry_response = selected_second_entry_submit_payload.get("entry")
if not isinstance(selected_second_entry_response, dict):
    raise SystemExit("selected second today entry submit should return entry payload")
if int(selected_second_entry_response.get("id") or 0) != int(vendor_a_second_entry_id):
    raise SystemExit("selected second today entry submit should preserve second entry id")
if selected_second_entry_response.get("pre_entry_requirement") != "Selected second requirement verification":
    raise SystemExit("selected second today entry submit should return updated pre_entry_requirement")
vendor_work_entry_count_after_second_selected_submit = conn.execute(
    "SELECT COUNT(*) FROM vendor_work_entries"
).fetchone()[0]
if vendor_work_entry_count_after_second_selected_submit != vendor_work_entry_count_before_second_selected_submit:
    raise SystemExit("selected second today entry submit must not create a new vendor work entry row")
first_entry_after_second_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_entry_id)
second_entry_after_second_selected_submit = fetch_vendor_work_entry_snapshot(vendor_a_second_entry_id)
if first_entry_after_second_selected_submit != first_entry_before_second_selected_submit:
    raise SystemExit("selected second today entry submit must not mutate the first entry")
if second_entry_after_second_selected_submit["work_content"] != "Selected second entry target verification":
    raise SystemExit("selected second today entry submit should update the second entry only")
if second_entry_after_second_selected_submit["pre_entry_requirement"] != "Selected second requirement verification":
    raise SystemExit("selected second today entry submit should update pre_entry_requirement for the second entry only")

vendor_work_entry_submit_result_page = client.get(
    "/vendor/work-entry?submit_status=success&submit_mode=create",
    follow_redirects=False,
)
if vendor_work_entry_submit_result_page.status_code != 200:
    raise SystemExit("vendor work entry submit result page should return 200")
vendor_work_entry_submit_result_html = vendor_work_entry_submit_result_page.get_data(as_text=True)
for fragment in (
    'data-testid="vendor-work-entry-submit-result"',
    'data-testid="vendor-work-entry-submit-result-status"',
    'data-testid="vendor-work-entry-submit-result-mode"',
    'data-testid="vendor-work-entry-readiness-summary"',
    "Submit successful.",
    "create",
    business_date,
):
    if fragment not in vendor_work_entry_submit_result_html:
        raise SystemExit(f"vendor work entry submit result page missing fragment: {fragment}")

vendor_profile = client.get("/vendor/profile", follow_redirects=False)
if vendor_profile.status_code != 200:
    raise SystemExit("vendor authenticated profile should return 200")
vendor_profile_payload = vendor_profile.get_json()
if not isinstance(vendor_profile_payload, dict) or vendor_profile_payload.get("ok") is not True:
    raise SystemExit("vendor profile should return ok=true payload")
expected_vendor_profile_keys = {
    "ok",
    "vendor_account_id",
    "vendor_username",
    "vendor_name",
}
if set(vendor_profile_payload.keys()) != expected_vendor_profile_keys:
    raise SystemExit("vendor profile should keep stable top-level response shape")
if vendor_profile_payload.get("vendor_account_id") is None:
    raise SystemExit("vendor profile should return vendor_account_id")
if vendor_profile_payload.get("vendor_username") != "vendor_active":
    raise SystemExit("vendor profile should return vendor_username")
if vendor_profile_payload.get("vendor_name") != "Vendor A":
    raise SystemExit("vendor profile should return vendor_name")
if "password_hash" in vendor_profile_payload:
    raise SystemExit("vendor profile must not return password_hash")

vendor_scope = client.get("/vendor/scope", follow_redirects=False)
if vendor_scope.status_code != 200:
    raise SystemExit("vendor authenticated scope should return 200")
vendor_scope_payload = vendor_scope.get_json()
if not isinstance(vendor_scope_payload, dict) or vendor_scope_payload.get("ok") is not True:
    raise SystemExit("vendor scope should return ok=true payload")
expected_vendor_scope_keys = {"ok", "scope"}
if set(vendor_scope_payload.keys()) != expected_vendor_scope_keys:
    raise SystemExit("vendor scope should keep stable top-level response shape")
scope = vendor_scope_payload.get("scope")
if not isinstance(scope, dict):
    raise SystemExit("vendor scope should return scope object")
if scope.get("identity_type") != "vendor":
    raise SystemExit("vendor scope should return identity_type=vendor")
if scope.get("vendor_account_id") is None:
    raise SystemExit("vendor scope should return vendor_account_id")
if scope.get("vendor_username") != "vendor_active":
    raise SystemExit("vendor scope should return vendor_username")
if scope.get("vendor_name") != "Vendor A":
    raise SystemExit("vendor scope should return vendor_name")
if scope.get("scope_type") != "vendor_identity_only":
    raise SystemExit("vendor scope should return scope_type=vendor_identity_only")
if scope.get("scope_version") != 1:
    raise SystemExit("vendor scope should return scope_version=1")
if "password_hash" in scope:
    raise SystemExit("vendor scope must not return password_hash")
for forbidden_key in ("site_id", "sheet_id", "allowed_site_ids", "allowed_sheet_ids"):
    if forbidden_key in scope:
        raise SystemExit(f"vendor scope must not return {forbidden_key}")

vendor_business_preview = client.get("/vendor/business-read-preview", follow_redirects=False)
if vendor_business_preview.status_code != 200:
    raise SystemExit("vendor authenticated business read preview should return 200")
vendor_business_preview_payload = vendor_business_preview.get_json()
if not isinstance(vendor_business_preview_payload, dict) or vendor_business_preview_payload.get("ok") is not True:
    raise SystemExit("vendor business read preview should return ok=true payload")
expected_top_level_keys = {
    "ok",
    "vendor_account_id",
    "vendor_username",
    "vendor_name",
    "entry_count",
    "business_dates",
    "entries",
}
if set(vendor_business_preview_payload.keys()) != expected_top_level_keys:
    raise SystemExit("vendor business read preview should keep stable top-level response shape")
if vendor_business_preview_payload.get("vendor_account_id") is None:
    raise SystemExit("vendor business read preview should return vendor_account_id")
if vendor_business_preview_payload.get("vendor_username") != "vendor_active":
    raise SystemExit("vendor business read preview should return vendor_username")
if vendor_business_preview_payload.get("vendor_name") != "Vendor A":
    raise SystemExit("vendor business read preview should return vendor_name")
if "password_hash" in vendor_business_preview_payload:
    raise SystemExit("vendor business read preview must not return password_hash")
for forbidden_key in ("site_id", "sheet_id", "allowed_site_ids", "allowed_sheet_ids"):
    if forbidden_key in vendor_business_preview_payload:
        raise SystemExit(f"vendor business read preview must not return top-level {forbidden_key}")
entries = vendor_business_preview_payload.get("entries")
if not isinstance(entries, list):
    raise SystemExit("vendor business read preview should return entries list")
if vendor_business_preview_payload.get("entry_count") != len(entries):
    raise SystemExit("vendor business read preview entry_count should match entries length")
if len(entries) < 3:
    raise SystemExit("vendor business read preview should include the seeded current vendor entries")
if any(entry.get("vendor_name") != "Vendor A" for entry in entries):
    raise SystemExit("vendor business read preview should only return current vendor entries")
if any(int(entry.get("entry_id") or 0) == int(vendor_other_entry_id) for entry in entries):
    raise SystemExit("vendor business read preview must not include another vendor's entry")
actual_entry_order = [(entry["business_date"], entry["entry_order"]) for entry in entries]
expected_entry_order = sorted(actual_entry_order, key=lambda item: (item[0], -item[1]), reverse=True)
if actual_entry_order != expected_entry_order:
    raise SystemExit(
        "vendor business read preview entries should keep stable ordering by business_date DESC then entry_order ASC"
    )
for entry in entries:
    expected_entry_keys = {
        "entry_id",
        "vendor_name",
        "business_date",
        "planned_at",
        "planned_headcount",
        "actual_headcount",
        "work_content",
        "pre_entry_requirement",
        "work_headcount",
        "entry_order",
    }
    if set(entry.keys()) != expected_entry_keys:
        raise SystemExit("vendor business read preview entries should keep stable response shape")
    if not isinstance(entry.get("entry_id"), int):
        raise SystemExit("vendor business read preview entries must return int for entry_id")
    if entry.get("vendor_name") != "Vendor A":
        raise SystemExit("vendor business read preview must only return current vendor data")
    if "password_hash" in entry:
        raise SystemExit("vendor business read preview entries must not return password_hash")
    for forbidden_key in ("site_id", "sheet_id", "allowed_site_ids", "allowed_sheet_ids"):
        if forbidden_key in entry:
            raise SystemExit(f"vendor business read preview entries must not return {forbidden_key}")
    for numeric_key in ("planned_headcount", "actual_headcount", "work_headcount", "entry_order"):
        if not isinstance(entry.get(numeric_key), int):
            raise SystemExit(f"vendor business read preview entries must return int for {numeric_key}")
empty_planned_at_entries = [entry for entry in entries if entry.get("planned_at") == ""]
if not empty_planned_at_entries:
    raise SystemExit("vendor business read preview should serialize empty planned_at as empty string")
business_dates = vendor_business_preview_payload.get("business_dates")
if not isinstance(business_dates, list) or business_date not in business_dates:
    raise SystemExit("vendor business read preview should return current vendor business_dates")
if business_dates != [business_date, earlier_business_date]:
    raise SystemExit("vendor business read preview should return de-duplicated, stable-sorted business_dates")
if vendor_business_preview_payload.get("entry_count") != len(entries):
    raise SystemExit("vendor business read preview should return current vendor entry_count")

vendor_logout = client.get("/vendor/logout", follow_redirects=False)
if vendor_logout.status_code != 302 or not vendor_logout.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("vendor logout should redirect to /vendor/login before empty preview check")

empty_vendor_login = client.post(
    "/vendor/login",
    data={"username": "vendor_empty", "password": "vendor-pass"},
    follow_redirects=False,
)
if empty_vendor_login.status_code != 302 or not empty_vendor_login.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("empty vendor valid login should redirect to /vendor/login")
empty_vendor_preview = client.get("/vendor/business-read-preview", follow_redirects=False)
if empty_vendor_preview.status_code != 200:
    raise SystemExit("empty vendor business read preview should return 200")
empty_vendor_preview_payload = empty_vendor_preview.get_json()
if not isinstance(empty_vendor_preview_payload, dict) or empty_vendor_preview_payload.get("ok") is not True:
    raise SystemExit("empty vendor business read preview should return ok=true payload")
if set(empty_vendor_preview_payload.keys()) != expected_top_level_keys:
    raise SystemExit("empty vendor business read preview should keep stable top-level response shape")
if empty_vendor_preview_payload.get("vendor_username") != "vendor_empty":
    raise SystemExit("empty vendor business read preview should return vendor_username")
if empty_vendor_preview_payload.get("vendor_name") != "Vendor Empty":
    raise SystemExit("empty vendor business read preview should return vendor_name")
if empty_vendor_preview_payload.get("entry_count") != 0:
    raise SystemExit("empty vendor business read preview should return entry_count=0")
if empty_vendor_preview_payload.get("business_dates") != []:
    raise SystemExit("empty vendor business read preview should return empty business_dates")
if empty_vendor_preview_payload.get("entries") != []:
    raise SystemExit("empty vendor business read preview should return empty entries")
for forbidden_key in ("password_hash", "site_id", "sheet_id", "allowed_site_ids", "allowed_sheet_ids"):
    if forbidden_key in empty_vendor_preview_payload:
        raise SystemExit(f"empty vendor business read preview must not return {forbidden_key}")

internal_route_with_vendor_session = client.get("/sheet", follow_redirects=False)
if internal_route_with_vendor_session.status_code != 302 or not internal_route_with_vendor_session.headers.get("Location", "").endswith("/login"):
    raise SystemExit("vendor session must not pass internal protected route")

vendor_logout = client.get("/vendor/logout", follow_redirects=False)
if vendor_logout.status_code != 302 or not vendor_logout.headers.get("Location", "").endswith("/vendor/login"):
    raise SystemExit("vendor logout should redirect to /vendor/login")
with client.session_transaction() as session:
    for key in ("identity_type", "vendor_account_id", "vendor_username", "vendor_name"):
        if session.get(key) is not None:
            raise SystemExit("vendor logout should clear vendor session")
    if session.get("user_id") is not None or session.get("role") is not None:
        raise SystemExit("vendor logout should not create internal session")

print("vendor auth foundation smoke PASS")
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "vendor_auth_foundation_smoke.py"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(script_path), str(db_path), str(ROOT_DIR)],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
    if "vendor auth foundation smoke PASS" not in result.stdout:
        raise AssertionError("vendor auth foundation smoke subprocess did not report PASS.")


def run_vendor_work_entry_page_context_regression_smoke(db_path: Path) -> None:
    import importlib.util

    os.environ["APP_DB_PATH"] = str(db_path)
    module_name = "vendor_work_entry_page_context_under_test"
    spec = importlib.util.spec_from_file_location(module_name, str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (module.generate_password_hash("admin"),),
        )
        conn.execute(
            '''
            INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
            VALUES (?, ?, ?, ?)
            ''',
            ("vendor_active", module.generate_password_hash("vendor-pass"), "Vendor A", 1),
        )
        conn.execute(
            '''
            INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (1, 5, "Vendor A", "Vendor Zone", "Vendor A Task"),
        )
        business_date = module.resolve_crew_business_date()
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (1, "Vendor A", business_date, "2000-01-01 09:00", 3, 1, "Vendor A Work 1", 1, 0),
        )
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (1, "Vendor A", business_date, "2000-01-01 10:00", 2, 0, "Vendor A Work 2", 0, 1),
        )
        first_entry_id = conn.execute(
            "SELECT id FROM vendor_work_entries WHERE vendor_name = ? AND business_date = ? AND entry_order = 0",
            ("Vendor A", business_date),
        ).fetchone()["id"]
        conn.commit()

    client = module.app.test_client()
    login = client.post(
        "/vendor/login",
        data={"username": "vendor_active", "password": "vendor-pass"},
        follow_redirects=False,
    )
    if login.status_code != 302:
        raise AssertionError("vendor work entry page context regression smoke login should redirect successfully")

    selected_entry_page = client.get("/vendor/work-entry", follow_redirects=False)
    if selected_entry_page.status_code != 200:
        raise AssertionError("vendor work entry selected-entry page should return 200")
    selected_entry_html = selected_entry_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-readiness-summary"',
        'data-testid="vendor-work-entry-summary-status-line"',
        'data-testid="vendor-work-entry-draft-submit"',
        'data-testid="vendor-work-entry-history"',
        'data-testid="vendor-work-entry-pending-items"',
        'data-testid="vendor-work-entry-new-entry-link"',
        f'data-testid="vendor-work-entry-summary-active-entry-id">{first_entry_id}<',
        'data-testid="vendor-work-entry-draft-write-mode">update<',
        f'data-testid="vendor-work-entry-draft-hidden-entry-id"' ,
        f'value="{first_entry_id}"',
    ):
        if fragment not in selected_entry_html:
            raise AssertionError(f"vendor work entry selected-entry page missing fragment: {fragment}")

    new_entry_page = client.get("/vendor/work-entry?new_entry=1", follow_redirects=False)
    if new_entry_page.status_code != 200:
        raise AssertionError("vendor work entry create-mode page should return 200")
    new_entry_html = new_entry_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-readiness-summary"',
        'data-testid="vendor-work-entry-summary-status-line"',
        'data-testid="vendor-work-entry-draft-submit"',
        'data-testid="vendor-work-entry-history"',
        'data-testid="vendor-work-entry-pending-items"',
        'data-testid="vendor-work-entry-new-entry-link"',
        'data-testid="vendor-work-entry-create-mode"',
        'data-testid="vendor-work-entry-draft-write-mode">create<',
        'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        'value=""',
    ):
        if fragment not in new_entry_html:
            raise AssertionError(f"vendor work entry create-mode page missing fragment: {fragment}")


def run_vendor_work_entry_preflight_context_regression_smoke(db_path: Path) -> None:
    import importlib.util

    os.environ["APP_DB_PATH"] = str(db_path)
    module_name = "vendor_work_entry_preflight_context_under_test"
    spec = importlib.util.spec_from_file_location(module_name, str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (module.generate_password_hash("admin"),),
        )
        conn.execute(
            '''
            INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
            VALUES (?, ?, ?, ?)
            ''',
            ("vendor_active", module.generate_password_hash("vendor-pass"), "Vendor A", 1),
        )
        conn.execute(
            '''
            INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (1, 5, "Vendor A", "Vendor Zone", "Vendor A Task"),
        )
        business_date = module.resolve_crew_business_date()
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (1, "Vendor A", business_date, "2000-01-01 09:00", 3, 1, "Vendor A Work 1", 1, 0),
        )
        entry_id = conn.execute(
            "SELECT id FROM vendor_work_entries WHERE vendor_name = ? AND business_date = ? AND entry_order = 0",
            ("Vendor A", business_date),
        ).fetchone()["id"]
        conn.commit()

    client = module.app.test_client()
    login = client.post(
        "/vendor/login",
        data={"username": "vendor_active", "password": "vendor-pass"},
        follow_redirects=False,
    )
    if login.status_code != 302:
        raise AssertionError("vendor preflight context regression smoke login should redirect successfully")

    create_preflight = client.post(
        "/api/vendor/work-entry/preflight",
        json={"sheet_id": 1, "business_date": business_date, "vendor_name": "Vendor A"},
    )
    if create_preflight.status_code != 200:
        raise AssertionError("vendor preflight context regression smoke create path should return 200")
    create_payload = create_preflight.get_json()
    create_context = create_payload.get("preflight") if isinstance(create_payload, dict) else None
    if not isinstance(create_context, dict):
        raise AssertionError("vendor preflight context regression smoke create path should return preflight object")
    if create_context.get("entry_id") is not None or create_context.get("write_mode") != "create":
        raise AssertionError("vendor preflight context regression smoke create path should preserve create contract")

    update_preflight = client.post(
        "/api/vendor/work-entry/preflight",
        json={"id": int(entry_id), "sheet_id": 1, "business_date": business_date, "vendor_name": "Vendor A"},
    )
    if update_preflight.status_code != 200:
        raise AssertionError("vendor preflight context regression smoke update path should return 200")
    update_payload = update_preflight.get_json()
    update_context = update_payload.get("preflight") if isinstance(update_payload, dict) else None
    if not isinstance(update_context, dict):
        raise AssertionError("vendor preflight context regression smoke update path should return preflight object")
    if update_context.get("entry_id") != int(entry_id) or update_context.get("write_mode") != "update":
        raise AssertionError("vendor preflight context regression smoke update path should preserve update contract")

    selected_entry_page = client.get("/vendor/work-entry", follow_redirects=False)
    if selected_entry_page.status_code != 200:
        raise AssertionError("vendor preflight context regression smoke selected-entry page should return 200")
    selected_entry_html = selected_entry_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-readiness-summary"',
        'data-testid="vendor-work-entry-draft-submit"',
        'data-testid="vendor-work-entry-summary-status-line"',
        'data-testid="vendor-work-entry-draft-write-mode">update<',
        f'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        f'value="{entry_id}"',
    ):
        if fragment not in selected_entry_html:
            raise AssertionError(f"vendor preflight context regression smoke selected-entry page missing fragment: {fragment}")
    if "You are viewing an existing entry that is ready for update." not in selected_entry_html:
        raise AssertionError("vendor preflight context regression smoke selected-entry page should explain update status")

    new_entry_page = client.get("/vendor/work-entry?new_entry=1", follow_redirects=False)
    if new_entry_page.status_code != 200:
        raise AssertionError("vendor preflight context regression smoke create-mode page should return 200")
    new_entry_html = new_entry_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-create-mode"',
        'data-testid="vendor-work-entry-summary-status-line"',
        'data-testid="vendor-work-entry-draft-write-mode">create<',
        'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        'value=""',
    ):
        if fragment not in new_entry_html:
            raise AssertionError(f"vendor preflight context regression smoke create-mode page missing fragment: {fragment}")
    if "You are preparing a new entry for today." not in new_entry_html:
        raise AssertionError("vendor preflight context regression smoke create-mode page should explain create status")


def run_vendor_work_entry_submit_pipeline_regression_smoke(db_path: Path) -> None:
    import importlib.util

    os.environ["APP_DB_PATH"] = str(db_path)
    module_name = "vendor_work_entry_submit_pipeline_under_test"
    spec = importlib.util.spec_from_file_location(module_name, str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (module.generate_password_hash("admin"),),
        )
        conn.execute(
            '''
            INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
            VALUES (?, ?, ?, ?)
            ''',
            ("vendor_active", module.generate_password_hash("vendor-pass"), "Vendor A", 1),
        )
        next_task_col_index = conn.execute("SELECT COALESCE(MAX(col_index), 0) + 1 FROM tasks").fetchone()[0]
        conn.execute(
            '''
            INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (1, next_task_col_index, "Vendor A", "Vendor Zone", "Vendor A Task"),
        )
        business_date = module.resolve_crew_business_date()
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (1, "Vendor A", business_date, "2000-01-01 09:00", 3, 1, "Vendor A Work 1", 1, 0),
        )
        first_entry_id = conn.execute(
            "SELECT id FROM vendor_work_entries WHERE vendor_name = ? AND business_date = ? AND entry_order = 0",
            ("Vendor A", business_date),
        ).fetchone()["id"]
        conn.commit()

    vendor_client = module.app.test_client()
    vendor_login = vendor_client.post(
        "/vendor/login",
        data={"username": "vendor_active", "password": "vendor-pass"},
        follow_redirects=False,
    )
    if vendor_login.status_code != 302:
        raise AssertionError("vendor submit pipeline regression smoke vendor login should redirect successfully")

    selected_entry_page = vendor_client.get("/vendor/work-entry", follow_redirects=False)
    if selected_entry_page.status_code != 200:
        raise AssertionError("vendor submit pipeline regression smoke selected-entry page should return 200")
    selected_entry_html = selected_entry_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-draft-submit"',
        'data-testid="vendor-work-entry-summary-status-line"',
        f'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        f'value="{first_entry_id}"',
        'data-testid="vendor-work-entry-draft-write-mode">update<',
        'data-testid="vendor-work-entry-draft-planned-at"',
        'value="2000-01-01 09:00"',
        'data-testid="vendor-work-entry-draft-work-content"',
        'Vendor A Work 1',
    ):
        if fragment not in selected_entry_html:
            raise AssertionError(f"vendor submit pipeline regression smoke selected-entry page missing fragment: {fragment}")
    if "You are viewing an existing entry that is ready for update." not in selected_entry_html:
        raise AssertionError("vendor submit pipeline regression smoke selected-entry page should explain update status")

    new_entry_page = vendor_client.get("/vendor/work-entry?new_entry=1", follow_redirects=False)
    if new_entry_page.status_code != 200:
        raise AssertionError("vendor submit pipeline regression smoke create-mode page should return 200")
    new_entry_html = new_entry_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-create-mode"',
        'data-testid="vendor-work-entry-summary-status-line"',
        'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        'value=""',
        'data-testid="vendor-work-entry-draft-write-mode">create<',
        'data-testid="vendor-work-entry-draft-entry-order"',
        'value="1"',
    ):
        if fragment not in new_entry_html:
            raise AssertionError(f"vendor submit pipeline regression smoke create-mode page missing fragment: {fragment}")
    if "You are preparing a new entry for today." not in new_entry_html:
        raise AssertionError("vendor submit pipeline regression smoke create-mode page should explain create status")

    internal_client = module.app.test_client()
    internal_login = internal_client.post(
        "/login",
        data={"username": "admin", "display_name": "Admin", "password": "admin"},
        follow_redirects=False,
    )
    if internal_login.status_code != 302:
        raise AssertionError("vendor submit pipeline regression smoke internal login should redirect successfully")

    create_payload = {
        "sheet_id": 1,
        "vendor_name": "Vendor A",
        "business_date": business_date,
        "planned_at": "2000-01-01 10:00",
        "planned_headcount": 2,
        "actual_headcount": 0,
        "work_content": "Vendor A Work Create",
        "pre_entry_requirement": "Vendor A Requirement Create",
        "work_headcount": 0,
        "entry_order": 1,
    }
    create_response = internal_client.post("/api/vendor-work-entry", json=create_payload, follow_redirects=False)
    if create_response.status_code != 200:
        raise AssertionError("vendor submit pipeline regression smoke create path should return 200")
    create_response_payload = create_response.get_json()
    create_entry = create_response_payload.get("entry") if isinstance(create_response_payload, dict) else None
    if create_response_payload.get("ok") is not True or not isinstance(create_entry, dict):
        raise AssertionError("vendor submit pipeline regression smoke create path should preserve ok/entry response contract")
    if create_entry.get("pre_entry_requirement") != "Vendor A Requirement Create":
        raise AssertionError("vendor submit pipeline regression smoke create path should return persisted pre_entry_requirement")
    if create_entry.get("id") is None or create_entry.get("vendor_name") != "Vendor A" or create_entry.get("entry_order") != 1:
        raise AssertionError("vendor submit pipeline regression smoke create path should preserve trusted create payload fields")

    update_payload = {
        "id": int(first_entry_id),
        "sheet_id": 1,
        "vendor_name": "Vendor A",
        "business_date": business_date,
        "planned_at": "2000-01-01 09:15",
        "planned_headcount": 4,
        "actual_headcount": 2,
        "work_content": "Vendor A Work Updated",
        "pre_entry_requirement": "Vendor A Requirement Updated",
        "work_headcount": 2,
        "entry_order": 0,
    }
    update_response = internal_client.post("/api/vendor-work-entry", json=update_payload, follow_redirects=False)
    if update_response.status_code != 200:
        raise AssertionError("vendor submit pipeline regression smoke update path should return 200")
    update_response_payload = update_response.get_json()
    update_entry = update_response_payload.get("entry") if isinstance(update_response_payload, dict) else None
    if update_response_payload.get("ok") is not True or not isinstance(update_entry, dict):
        raise AssertionError("vendor submit pipeline regression smoke update path should preserve ok/entry response contract")
    if update_entry.get("pre_entry_requirement") != "Vendor A Requirement Updated":
        raise AssertionError("vendor submit pipeline regression smoke update path should return persisted pre_entry_requirement")
    if (
        int(update_entry.get("id") or 0) != int(first_entry_id)
        or update_entry.get("work_content") != "Vendor A Work Updated"
        or update_entry.get("entry_order") != 0
    ):
        raise AssertionError("vendor submit pipeline regression smoke update path should preserve target id and updated fields")


def run_vendor_work_entry_submit_result_flow_completion_smoke(db_path: Path) -> None:
    import importlib.util

    os.environ["APP_DB_PATH"] = str(db_path)
    module_name = "vendor_work_entry_submit_result_flow_completion_under_test"
    spec = importlib.util.spec_from_file_location(module_name, str(ROOT_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    template_text = (ROOT_DIR / "templates" / "vendor_work_entry.html").read_text(encoding="utf-8")
    for fragment in (
        'reloadUrl.searchParams.set("selected_entry_id", resultEntryId);',
        'reloadUrl.searchParams.delete("new_entry");',
    ):
        if fragment not in template_text:
            raise AssertionError(f"vendor submit result flow completion smoke template missing fragment: {fragment}")

    with module.db() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (module.generate_password_hash("admin"),),
        )
        conn.execute(
            '''
            INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active)
            VALUES (?, ?, ?, ?)
            ''',
            ("vendor_active", module.generate_password_hash("vendor-pass"), "Vendor A", 1),
        )
        next_task_col_index = conn.execute("SELECT COALESCE(MAX(col_index), 0) + 1 FROM tasks").fetchone()[0]
        conn.execute(
            '''
            INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (1, next_task_col_index, "Vendor A", "Vendor Zone", "Vendor A Task"),
        )
        business_date = module.resolve_crew_business_date()
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (1, "Vendor A", business_date, "2000-01-01 09:00", 3, 1, "Vendor A Work 1", 1, 0),
        )
        conn.execute(
            '''
            INSERT INTO vendor_work_entries (
                sheet_id, vendor_name, business_date, planned_at, planned_headcount,
                actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (1, "Vendor A", business_date, "2000-01-01 10:00", 2, 0, "Vendor A Work 2", 0, 1),
        )
        first_entry_id = conn.execute(
            "SELECT id FROM vendor_work_entries WHERE vendor_name = ? AND business_date = ? AND entry_order = 0",
            ("Vendor A", business_date),
        ).fetchone()["id"]
        second_entry_id = conn.execute(
            "SELECT id FROM vendor_work_entries WHERE vendor_name = ? AND business_date = ? AND entry_order = 1",
            ("Vendor A", business_date),
        ).fetchone()["id"]
        conn.commit()

    vendor_client = module.app.test_client()
    vendor_login = vendor_client.post(
        "/vendor/login",
        data={"username": "vendor_active", "password": "vendor-pass"},
        follow_redirects=False,
    )
    if vendor_login.status_code != 302:
        raise AssertionError("vendor submit result flow completion smoke vendor login should redirect successfully")

    invalid_selected_page = vendor_client.get(
        "/vendor/work-entry?selected_entry_id=999999&today_entry_index=1",
        follow_redirects=False,
    )
    if invalid_selected_page.status_code != 200:
        raise AssertionError("vendor submit result flow completion smoke invalid selected_entry_id page should return 200")
    invalid_selected_html = invalid_selected_page.get_data(as_text=True)
    for fragment in (
        f'data-testid="vendor-work-entry-today-entry-active-id">{second_entry_id}<',
        f'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        f'value="{second_entry_id}"',
        'data-testid="vendor-work-entry-draft-write-mode">update<',
    ):
        if fragment not in invalid_selected_html:
            raise AssertionError(f"vendor submit result flow completion smoke invalid selected_entry_id fallback missing fragment: {fragment}")

    create_landing_page = vendor_client.get(
        f"/vendor/work-entry?submit_status=success&submit_mode=create&selected_entry_id={second_entry_id}",
        follow_redirects=False,
    )
    if create_landing_page.status_code != 200:
        raise AssertionError("vendor submit result flow completion smoke create success landing page should return 200")
    create_landing_html = create_landing_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-submit-result"',
        'data-testid="vendor-work-entry-submit-result-mode">create<',
        'data-testid="vendor-work-entry-summary-status-line"',
        f'data-testid="vendor-work-entry-summary-active-entry-id">{second_entry_id}<',
        f'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        f'value="{second_entry_id}"',
        'data-testid="vendor-work-entry-draft-write-mode">update<',
    ):
        if fragment not in create_landing_html:
            raise AssertionError(f"vendor submit result flow completion smoke create landing missing fragment: {fragment}")
    if 'data-testid="vendor-work-entry-create-mode"' in create_landing_html:
        raise AssertionError("vendor submit result flow completion smoke create landing should not remain in create-mode state")
    if "You are viewing an existing entry that is ready for update." not in create_landing_html:
        raise AssertionError("vendor submit result flow completion smoke create landing should explain selected-entry update status")

    update_landing_page = vendor_client.get(
        f"/vendor/work-entry?submit_status=success&submit_mode=update&selected_entry_id={first_entry_id}",
        follow_redirects=False,
    )
    if update_landing_page.status_code != 200:
        raise AssertionError("vendor submit result flow completion smoke update success landing page should return 200")
    update_landing_html = update_landing_page.get_data(as_text=True)
    for fragment in (
        'data-testid="vendor-work-entry-submit-result"',
        'data-testid="vendor-work-entry-submit-result-mode">update<',
        'data-testid="vendor-work-entry-summary-status-line"',
        f'data-testid="vendor-work-entry-summary-active-entry-id">{first_entry_id}<',
        f'data-testid="vendor-work-entry-draft-hidden-entry-id"',
        f'value="{first_entry_id}"',
        'data-testid="vendor-work-entry-draft-write-mode">update<',
    ):
        if fragment not in update_landing_html:
            raise AssertionError(f"vendor submit result flow completion smoke update landing missing fragment: {fragment}")
    if "You are viewing an existing entry that is ready for update." not in update_landing_html:
        raise AssertionError("vendor submit result flow completion smoke update landing should explain selected-entry update status")


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
        expected_counts = {"meta": 3, "users": 2, "vendor_contacts": 0, "vendor_work_entries": 0}
        if any(count != expected_counts.get(table_name, 1) for table_name, count in counts.items()):
            raise AssertionError(f"Unexpected sample counts: {counts}")

        site_foundation_db = Path(tmpdir) / "site-foundation.db"
        create_sample_sqlite(site_foundation_db)
        run_site_foundation_smoke(site_foundation_db)
        site_selection_db = Path(tmpdir) / "site-selection.db"
        create_sample_sqlite(site_selection_db)
        run_site_selection_smoke(site_selection_db)
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
        run_users_read_compare_readiness_smoke(Path(tmpdir) / "app-smoke.db")
        run_crew_schema_smoke_v2(Path(tmpdir) / "crew-schema-smoke.db")
        run_crew_schema_migration_smoke(Path(tmpdir) / "crew-schema-migration-smoke.db")
        run_scheduler_schema_smoke(Path(tmpdir) / "scheduler-schema-smoke.db")
        run_crew_api_smoke(Path(tmpdir) / "crew-api-smoke.db")
        run_dashboard_api_smoke(Path(tmpdir) / "dashboard-api-smoke.db")
        run_scheduling_api_smoke(Path(tmpdir) / "scheduling-api-smoke.db")
        run_scheduler_persistence_smoke(Path(tmpdir) / "scheduler-persistence-smoke.db")
        run_scheduler_persistence_guardrail_smoke(Path(tmpdir) / "scheduler-persistence-guardrail-smoke.db")
        run_scheduling_guardrail_smoke(Path(tmpdir) / "scheduling-guardrail-smoke.db")
        run_crew_readonly_render_smoke(Path(tmpdir) / "crew-readonly-smoke.db")
        run_work_hub_scheduling_smoke(Path(tmpdir) / "work-hub-scheduling-smoke.db")
        run_work_hub_scheduled_smoke(Path(tmpdir) / "work-hub-scheduled-smoke.db")
        run_work_hub_scheduled_guardrail_smoke(Path(tmpdir) / "work-hub-scheduled-guardrail-smoke.db")
        run_work_hub_runtime_helper_smoke(Path(tmpdir) / "work-hub-runtime-helper-smoke.db")
        run_management_read_model_helper_smoke(Path(tmpdir) / "management-read-model-helper-smoke.db")
        run_management_read_model_api_smoke(Path(tmpdir) / "management-read-model-api-smoke.db")
        run_work_hub_runtime_api_smoke(Path(tmpdir) / "work-hub-runtime-api-smoke.db")
        run_work_hub_runtime_consumption_smoke(Path(tmpdir) / "work-hub-runtime-consumption-smoke.db")
        run_work_hub_quick_action_smoke(Path(tmpdir) / "work-hub-quick-action-smoke.db")
        run_users_id_allocation_smoke(db_path)
        run_users_sqlite_sequence_bump_plan_smoke()
        run_users_sqlite_sequence_apply_guard_smoke()
        run_sqlite_db_path_resolver_smoke()
        run_users_template_delete_ui_smoke()
        run_sheet_endpoint_smoke(Path(tmpdir) / "app-smoke.db")
        run_table_admin_endpoint_and_formula_smoke(Path(tmpdir) / "app-smoke.db")
        run_admin_current_site_sheet_write_smoke(Path(tmpdir) / "admin-current-site-sheet-write.db")
        run_admin_current_site_task_write_smoke(Path(tmpdir) / "admin-current-site-task-write.db")
        run_admin_current_site_floor_write_smoke(Path(tmpdir) / "admin-current-site-floor-write.db")
        run_admin_current_site_unit_write_smoke(Path(tmpdir) / "admin-current-site-unit-write.db")
        run_admin_current_site_extra_field_write_smoke(Path(tmpdir) / "admin-current-site-extra-field-write.db")
        run_admin_save_internal_split_smoke(Path(tmpdir) / "admin-save-internal-split.db")
        run_handover_reset_separation_smoke(Path(tmpdir) / "handover-smoke.db")
        run_handover_route_regression_smoke(Path(tmpdir) / "handover-route-smoke.db")
        run_user_create_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_admin_user_role_update_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_user_site_permissions_smoke_guardrail(db_path, Path(tmpdir) / "app-smoke.db")
        run_site_read_isolation_smoke(db_path)
        run_progress_write_isolation_smoke(db_path)
        run_unit_extra_write_isolation_smoke(db_path)
        run_vendor_contact_write_isolation_smoke(db_path)
        run_vendor_work_entry_write_isolation_smoke(db_path)
        run_vendor_work_entry_requirement_confirmation_smoke(db_path)
        run_vendor_work_entry_formal_approve_smoke(db_path)
        vendor_auth_db = Path(tmpdir) / "vendor-auth-foundation.db"
        create_sample_sqlite(vendor_auth_db)
        run_vendor_auth_foundation_smoke(vendor_auth_db)
        run_site_write_isolation_readiness_smoke()
        run_admin_write_model_readiness_smoke()

    if redact_database_url("postgresql://user:secret@localhost:5432/demo") != "postgresql://user:***@localhost:5432/demo":
        raise AssertionError("DATABASE_URL redaction failed.")

    run_help("check_controlled_dual_write.py")
    run_help("check_users_secondary_update.py")
    run_help("check_users_baseline_and_sequence.py")
    run_help("check_users_create_readiness.py")
    run_help("check_users_delete_readiness.py")
    run_help("check_users_delete_submit.py")
    run_help("check_users_read_inventory.py")
    run_help("check_users_read_compare_readiness.py")
    run_help("check_crew_schema.py")
    run_help("check_site_schema.py")
    run_help("check_site_seed.py")
    run_help("check_sheet_site_backfill.py")
    run_help("check_site_selection_readiness.py")
    run_help("check_site_permission_readiness.py")
    run_help("check_site_read_isolation.py")
    run_help("check_site_write_isolation_readiness.py")
    run_help("check_admin_write_model_readiness.py")
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
    site_permission_result = run_script("check_site_permission_readiness.py")
    if "PASS site permission readiness check passed." not in site_permission_result.stdout:
        raise AssertionError("check_site_permission_readiness.py did not report PASS.")
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
    crew_schema_result = run_script("check_crew_schema.py", env={"DATABASE_URL": ""})
    if "crew_schema_scope: sqlite_only" not in crew_schema_result.stdout or "PASS crew schema check passed." not in crew_schema_result.stdout:
        raise AssertionError("check_crew_schema.py did not report expected SQLite-only PASS output.")
    site_schema_result = run_script("check_site_schema.py", env={"DATABASE_URL": ""})
    if "site_schema_scope: sqlite_only" not in site_schema_result.stdout or "PASS site schema check passed." not in site_schema_result.stdout:
        raise AssertionError("check_site_schema.py did not report expected PASS output.")
    site_seed_result = run_script("check_site_seed.py", env={"DATABASE_URL": ""})
    if "site_seed_scope: sqlite_only" not in site_seed_result.stdout or "PASS site seed check passed." not in site_seed_result.stdout:
        raise AssertionError("check_site_seed.py did not report expected PASS output.")
    site_backfill_result = run_script("check_sheet_site_backfill.py", env={"DATABASE_URL": ""})
    if "sheet_site_backfill_scope: sqlite_only" not in site_backfill_result.stdout or "PASS sheet site backfill check passed." not in site_backfill_result.stdout:
        raise AssertionError("check_sheet_site_backfill.py did not report expected PASS output.")
    site_selection_result = run_script("check_site_selection_readiness.py", env={"DATABASE_URL": ""})
    if "site_selection_readiness_scope: sqlite_only" not in site_selection_result.stdout or "PASS site selection readiness check passed." not in site_selection_result.stdout:
        raise AssertionError("check_site_selection_readiness.py did not report expected PASS output.")
    site_read_isolation_result = run_script("check_site_read_isolation.py", env={"DATABASE_URL": ""})
    if "site_read_isolation_scope: sqlite_only" not in site_read_isolation_result.stdout or "PASS site read isolation check passed." not in site_read_isolation_result.stdout:
        raise AssertionError("check_site_read_isolation.py did not report expected PASS output.")
    site_write_isolation_result = run_script("check_site_write_isolation_readiness.py", env={"DATABASE_URL": ""})
    if "site_write_isolation_readiness_scope: high_risk_group_full_enforcement" not in site_write_isolation_result.stdout:
        raise AssertionError("check_site_write_isolation_readiness.py did not report expected high-risk group full enforcement scope.")
    if "PASS site write isolation readiness check passed." not in site_write_isolation_result.stdout:
        raise AssertionError("check_site_write_isolation_readiness.py did not report expected PASS output.")
    if site_write_isolation_result.stdout.count("status: ENFORCED") < 4:
        raise AssertionError("check_site_write_isolation_readiness.py did not report ENFORCED status for all enforced write paths.")
    for fragment in ("/api/progress", "/api/unit-extra", "/api/vendor-contact", "/api/vendor-work-entry"):
        if fragment not in site_write_isolation_result.stdout:
            raise AssertionError(f"check_site_write_isolation_readiness.py missing expected inventory fragment: {fragment}")
    admin_write_model_result = run_script("check_admin_write_model_readiness.py", env={"DATABASE_URL": ""})
    if "admin_write_model_readiness_scope: admin_site_content_enforced_save_internal_split_reset_sheet_enforced" not in admin_write_model_result.stdout:
        raise AssertionError("check_admin_write_model_readiness.py did not report expected reset-sheet-enforced scope.")
    if "PASS admin write model readiness check passed." not in admin_write_model_result.stdout:
        raise AssertionError("check_admin_write_model_readiness.py did not report expected PASS output.")
    for fragment in (
        "create_sheet",
        "delete_sheet",
        "add_task",
        "delete_task",
        "add_floor",
        "delete_floor",
        "add_unit",
        "delete_unit",
        "add_extra_field",
        "delete_extra_field",
        "save",
        "INTERNAL_SPLIT",
        "MIXED",
        "status: ENFORCED",
        "current_site_enforced: yes",
        "writes new sheet to current_site_id",
        "task delete validates task_id belongs to route sheet",
        "floor delete validates floor_id belongs to route sheet",
        "unit delete validates unit_id belongs to route sheet",
        "extra-field delete validates field_id belongs to route sheet",
        "global_settings_path: yes",
        "site_content_path: yes",
        "site_content_current_site_enforced: yes",
        "template_split: no",
        "ui_action_split: no",
        "/api/reset-sheet",
        "action: reset_sheet",
        "reset_sheet_status: ENFORCED",
        "reset_sheet_destructive_candidate: resolved",
        "destructive_candidate resolved",
    ):
        if fragment not in admin_write_model_result.stdout:
            raise AssertionError(f"check_admin_write_model_readiness.py missing expected inventory fragment: {fragment}")
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
