import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _db_migration_common import TABLE_ORDER, fetch_sqlite_counts, redact_database_url


TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="handover-smoke-test-"))
TEST_DB_PATH = TEST_DB_DIR / "site.db"


def configure_test_db():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    os.environ["APP_DB_PATH"] = str(TEST_DB_PATH)


configure_test_db()


def load_app_module():
    from app import app, bootstrap, create_app

    bootstrap()
    return app, bootstrap, create_app


def test_app_imports():
    app, _, create_app = load_app_module()

    assert app is not None
    assert create_app() is not None


def make_client():
    _, _, create_app = load_app_module()

    return create_app().test_client()


def test_login_route_smoke():
    client = make_client()
    response = client.get("/login")

    assert response.status_code == 200


def test_index_route_redirects_when_logged_out():
    client = make_client()
    response = client.get("/")

    assert response.status_code == 302


def test_admin_login_redirects_to_sheet():
    client = make_client()
    response = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/sheet")


def test_sheet_route_after_login():
    client = make_client()
    client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    response = client.get("/sheet")

    assert response.status_code == 200


def test_logout_redirects():
    client = make_client()
    client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 302


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
            created_at TEXT NOT NULL
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
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "usage:" in result.stdout.lower()


def test_sqlite_postgres_tooling_smoke():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sample.db"
        create_sample_sqlite(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        counts = fetch_sqlite_counts(conn)
        conn.close()

        assert list(counts) == TABLE_ORDER
        assert all(count == 1 for count in counts.values())

    assert (
        redact_database_url("postgresql://user:secret@localhost:5432/demo")
        == "postgresql://user:***@localhost:5432/demo"
    )
    run_help("migrate_sqlite_to_postgres.py")
    run_help("check_sqlite_postgres_counts.py")


def run():
    test_app_imports()
    test_login_route_smoke()
    test_index_route_redirects_when_logged_out()
    test_admin_login_redirects_to_sheet()
    test_sheet_route_after_login()
    test_logout_redirects()
    test_sqlite_postgres_tooling_smoke()


if __name__ == "__main__":
    run()
