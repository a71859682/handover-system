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
        "created_at",
        "updated_at",
    ):
        if required not in vendor_work_entries_columns:
            raise SystemExit(f"vendor_work_entries missing required column: {required}")

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
    conn.execute(
        "INSERT OR IGNORE INTO sheets (id, name, sort_order, created_at) VALUES (2, 'Sheet B', 2, CURRENT_TIMESTAMP)"
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

    conn.execute(
        "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_phone) VALUES (?, ?, ?, ?)",
        (sheet_id, "VendorA", "Alice", "0900000001"),
    )
    conn.execute(
        "INSERT INTO vendor_contacts (sheet_id, vendor_name, contact_name, contact_phone) VALUES (?, ?, ?, ?)",
        (sheet_id, "VendorB", "Bob", "0900000002"),
    )

    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, work_headcount, entry_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (sheet_id, "VendorA", business_date, "2000-01-01 09:00", 3, 0, "Missing Crew", 0, 0),
    )
    conn.execute(
        '''
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, work_headcount, entry_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (sheet_id, "VendorA", business_date, "2000-01-01 10:00", 2, 2, "Summary Crew", 2, 1),
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
    vendor_c = active_vendors["VendorC"]
    if vendor_c["contact"]["id"] is not None:
        raise SystemExit("active vendor without contacts should use empty compatibility contact")
    if vendor_c["contact"]["display_name"] != "":
        raise SystemExit("empty compatibility contact should use empty display_name")
    if vendor_c["contacts"] != []:
        raise SystemExit("active vendor without contacts should return empty contacts array")
    if vendor_c["contact"]["contact_name"] != "" or vendor_c["contact"]["contact_phone"] != "":
        raise SystemExit("empty compatibility contact should preserve readonly-safe blank fields")

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
            "work_headcount": 0,
            "entry_order": 2,
        },
    )
    if entry_insert.status_code != 200 or not entry_insert.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry insert should succeed")
    inserted_entry = entry_insert.get_json()["entry"]
    if inserted_entry["business_date"] != business_date:
        raise SystemExit("/api/vendor-work-entry insert should default business_date from helper")

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
            "work_headcount": 1,
            "entry_order": 2,
        },
    )
    if entry_update.status_code != 200 or not entry_update.get_json().get("ok"):
        raise SystemExit("/api/vendor-work-entry update should succeed")
    updated_entry = entry_update.get_json()["entry"]
    if updated_entry["actual_headcount"] != 1 or updated_entry["work_content"] != "Insert Crew Updated":
        raise SystemExit("/api/vendor-work-entry update returned unexpected payload")

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

    summary_response = client.get(f"/api/crew-daily-summary?sheet_id={sheet_id}&business_date={business_date}")
    if summary_response.status_code != 200:
        raise SystemExit("/api/crew-daily-summary should return 200")
    summary = summary_response.get_json()
    if not summary.get("ok"):
        raise SystemExit("/api/crew-daily-summary should report ok=true")
    summary_contents = {item["work_content"] for item in summary["items"]}
    if "Summary Crew" not in summary_contents or "Insert Crew Updated" not in summary_contents:
        raise SystemExit("/api/crew-daily-summary should include actual_headcount > 0 entries")
    if summary["totals"]["actual_headcount_sum"] != 3:
        raise SystemExit("/api/crew-daily-summary returned unexpected actual_headcount_sum")
    if summary["totals"]["work_headcount_sum"] != 3:
        raise SystemExit("/api/crew-daily-summary returned unexpected work_headcount_sum")

    missing_response = client.get(f"/api/crew-missing?sheet_id={sheet_id}&business_date={business_date}")
    if missing_response.status_code != 200:
        raise SystemExit("/api/crew-missing should return 200")
    missing = missing_response.get_json()
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
        "entry_order", "created_at", "updated_at",
    ):
        if required not in vendor_work_entries_columns:
            raise SystemExit(f"vendor_work_entries missing required column: {required}")

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
    for required in ("sheet_id", "vendor_name", "business_date", "entry_order"):
        if required not in work_columns:
            raise SystemExit("vendor_work_entries should remain intact after vendor_contacts migration")

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
    "function renderCrewForms",
    "function renderCrewFormError",
    "function formatCrewDate",
    "function formatCrewDateTime",
    "/api/crew-forms?sheet_id=",
):
    if required not in js_text:
        raise SystemExit(f"app.js missing readonly crew helper: {required}")

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
    for snippet in ('class="crew-form-shell"', 'data-mode="readonly"', 'id="crewVendorList"'):
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


def run_site_permission_management_smoke(db_path: Path, app_db_path: Path) -> None:
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

    client.post(
        "/admin/users",
        data={
            "action": f"add_site_permission:{other_member_id}",
            "site_id": str(default_site_id),
            "site_role": "member",
        },
        follow_redirects=False,
    )
    second_permission = conn.execute(
        "SELECT id FROM user_site_permissions WHERE user_id = ? AND site_id = ?",
        (other_member_id, default_site_id),
    ).fetchone()
    if second_permission is None:
        raise SystemExit("site permission setup for delete-user integration failed")

    client.post(
        "/admin/users",
        data={"action": f"delete_user:{other_member_id}"},
        follow_redirects=False,
    )
    if conn.execute("SELECT 1 FROM users WHERE id = ?", (other_member_id,)).fetchone():
        raise SystemExit("delete_user should still remove member")
    if conn.execute("SELECT 1 FROM user_site_permissions WHERE user_id = ?", (other_member_id,)).fetchone():
        raise SystemExit("delete_user should remove related site permissions")
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

print("site permission management smoke PASS")
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
    if "site permission management smoke PASS" not in result.stdout:
        raise AssertionError("site permission management smoke subprocess did not report PASS.")


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
        "/api/progress",
        "/api/unit-extra",
        "/api/vendor-contact",
        "/api/vendor-work-entry",
    )
    for fragment in required_fragments:
        if fragment not in result.stdout:
            raise AssertionError(f"check_site_write_isolation_readiness.py output missing: {fragment}")


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
        run_crew_api_smoke(Path(tmpdir) / "crew-api-smoke.db")
        run_crew_readonly_render_smoke(Path(tmpdir) / "crew-readonly-smoke.db")
        run_users_id_allocation_smoke(db_path)
        run_users_sqlite_sequence_bump_plan_smoke()
        run_users_sqlite_sequence_apply_guard_smoke()
        run_sqlite_db_path_resolver_smoke()
        run_users_template_delete_ui_smoke()
        run_sheet_endpoint_smoke(Path(tmpdir) / "app-smoke.db")
        run_table_admin_endpoint_and_formula_smoke(Path(tmpdir) / "app-smoke.db")
        run_handover_reset_separation_smoke(Path(tmpdir) / "handover-smoke.db")
        run_handover_route_regression_smoke(Path(tmpdir) / "handover-route-smoke.db")
        run_user_create_helper_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_admin_user_role_update_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_site_permission_management_smoke(db_path, Path(tmpdir) / "app-smoke.db")
        run_site_read_isolation_smoke(db_path)
        run_site_write_isolation_readiness_smoke()

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
    if "site_write_isolation_readiness_scope: inventory_only" not in site_write_isolation_result.stdout:
        raise AssertionError("check_site_write_isolation_readiness.py did not report expected inventory-only scope.")
    if "PASS site write isolation readiness check passed." not in site_write_isolation_result.stdout:
        raise AssertionError("check_site_write_isolation_readiness.py did not report expected PASS output.")
    for fragment in ("/api/progress", "/api/unit-extra", "/api/vendor-contact", "/api/vendor-work-entry"):
        if fragment not in site_write_isolation_result.stdout:
            raise AssertionError(f"check_site_write_isolation_readiness.py missing expected inventory fragment: {fragment}")
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
