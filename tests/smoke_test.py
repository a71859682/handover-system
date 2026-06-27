import importlib
import logging
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def load_write_service(dual_write_dry_run: bool):
    os.environ["DUAL_WRITE_DRY_RUN"] = "true" if dual_write_dry_run else "false"
    import config
    import services.write_service as write_service

    importlib.reload(config)
    return importlib.reload(write_service)


def test_create_user_sqlite_with_sqlite_connection():
    write_service = load_write_service(dual_write_dry_run=False)
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    created_id = write_service.create_user_sqlite(
        conn,
        username="sqlite_user",
        display_name="SQLite User",
        password_hash="hash",
        role="member",
    )

    row = conn.execute("SELECT id, username FROM users WHERE username = ?", ("sqlite_user",)).fetchone()
    assert created_id == row[0]
    assert row[1] == "sqlite_user"


def test_controlled_dual_write_meta_stays_gated_to_meta():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta"
    os.environ["DUAL_WRITE_STRICT"] = "false"
    os.environ["DUAL_WRITE_DRY_RUN"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://example.test/app"

    import config
    import services.write_service as write_service

    config = importlib.reload(config)
    write_service = importlib.reload(write_service)

    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    messages: list[str] = []

    class CollectHandler(logging.Handler):
        def emit(self, record):
            messages.append(self.format(record))

    handler = CollectHandler(level=logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    postgres_calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            postgres_calls.append((sql, params))

    class FakePostgresConnection:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    class FakePsycopg:
        def connect(self, url, **kwargs):
            postgres_calls.append(("CONNECT", (url, kwargs)))
            return FakePostgresConnection()

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    write_service.psycopg = FakePsycopg()

    try:
        write_service.upsert_setting_sqlite(conn, "site_title", "Controlled")
        meta_calls = len(postgres_calls)
        write_service.create_user_sqlite(
            conn,
            username="meta_only_user",
            display_name="Meta Only User",
            password_hash="hash",
            role="member",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    assert meta_calls > 0
    assert len(postgres_calls) == meta_calls
    assert "DUAL_WRITE operation=upsert table=meta" in log_output
    assert "postgres_result=success" in log_output
    assert "skipped_non_sqlite_primary" not in log_output
    assert "DUAL_WRITE_DRY_RUN operation=upsert table=meta" in log_output
    assert "DUAL_WRITE operation=insert table=users" not in log_output


def test_controlled_dual_write_meta_non_sqlite_runtime_still_attempts_secondary_write():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta"
    os.environ["DUAL_WRITE_STRICT"] = "false"
    os.environ["DUAL_WRITE_DRY_RUN"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://example.test/app"

    import config
    import services.write_service as write_service

    config = importlib.reload(config)
    write_service = importlib.reload(write_service)

    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    messages: list[str] = []

    class CollectHandler(logging.Handler):
        def emit(self, record):
            messages.append(self.format(record))

    handler = CollectHandler(level=logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    postgres_calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            postgres_calls.append((sql, params))

    class FakePostgresConnection:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    class FakePsycopg:
        def connect(self, url, **kwargs):
            postgres_calls.append(("CONNECT", (url, kwargs)))
            return FakePostgresConnection()

    class NonSqlitePrimaryConnection:
        pass

    write_service.psycopg = FakePsycopg()

    try:
        write_service._maybe_controlled_dual_write_meta(  # type: ignore[attr-defined]
            NonSqlitePrimaryConnection(),
            operation="upsert",
            key="site_title",
            value="Controlled from compat runtime",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    assert any(call[0] == "CONNECT" for call in postgres_calls)
    assert "DUAL_WRITE operation=upsert table=meta" in log_output
    assert "postgres_result=success" in log_output
    assert "skipped_non_sqlite_primary" not in log_output


def test_controlled_dual_write_meta_strict_false_logs_postgres_error_without_blocking_primary():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta"
    os.environ["DUAL_WRITE_STRICT"] = "false"
    os.environ["DUAL_WRITE_DRY_RUN"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://example.test/app"

    import config
    import services.write_service as write_service

    config = importlib.reload(config)
    write_service = importlib.reload(write_service)

    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    messages: list[str] = []

    class CollectHandler(logging.Handler):
        def emit(self, record):
            messages.append(self.format(record))

    handler = CollectHandler(level=logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    class FailingCursor:
        def execute(self, sql, params):
            raise RuntimeError("forced secondary failure")

        def close(self):
            return None

    class FailingPostgresConnection:
        def __init__(self):
            self.rolled_back = False
            self.closed = False

        def cursor(self):
            return FailingCursor()

        def commit(self):
            raise AssertionError("commit should not be called on failed secondary write")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    failing_connections: list[FailingPostgresConnection] = []

    class FailingPsycopg:
        def connect(self, url, **kwargs):
            conn = FailingPostgresConnection()
            failing_connections.append(conn)
            return conn

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    write_service.psycopg = FailingPsycopg()

    try:
        write_service.upsert_setting_sqlite(conn, "site_title", "Primary still succeeds")
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    stored_value = conn.execute("SELECT value FROM meta WHERE key = ?", ("site_title",)).fetchone()[0]
    assert stored_value == "Primary still succeeds"
    assert "DUAL_WRITE operation=upsert table=meta" in log_output
    assert "postgres_result=failed" in log_output
    assert "dry_run=true" in log_output
    assert failing_connections and failing_connections[0].rolled_back is True


def test_controlled_dual_write_meta_strict_true_raises_after_primary_write():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta"
    os.environ["DUAL_WRITE_STRICT"] = "true"
    os.environ["DUAL_WRITE_DRY_RUN"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://example.test/app"

    import config
    import services.write_service as write_service

    config = importlib.reload(config)
    write_service = importlib.reload(write_service)

    class FailingCursor:
        def execute(self, sql, params):
            raise RuntimeError("strict secondary failure")

        def close(self):
            return None

    class FailingPostgresConnection:
        def cursor(self):
            return FailingCursor()

        def commit(self):
            raise AssertionError("commit should not be called on failed secondary write")

        def rollback(self):
            return None

        def close(self):
            return None

    class FailingPsycopg:
        def connect(self, url, **kwargs):
            return FailingPostgresConnection()

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    write_service.psycopg = FailingPsycopg()

    try:
        try:
            write_service.upsert_setting_sqlite(conn, "site_title", "Strict write")
            raise AssertionError("strict mode should raise when secondary write fails")
        except RuntimeError as exc:
            assert "Controlled dual write failed" in str(exc)
    finally:
        conn.close()


def test_create_user_runtime_path_uses_cursor_lastrowid_and_emits_dry_run_log():
    write_service = load_write_service(dual_write_dry_run=True)
    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    messages: list[str] = []

    class CollectHandler(logging.Handler):
        def emit(self, record):
            messages.append(self.format(record))

    handler = CollectHandler(level=logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    class FakeCursor:
        def __init__(self, lastrowid):
            self.lastrowid = lastrowid

    class FakePostgresRuntimeConnection:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=()):
            self.calls.append((sql, params))
            assert "last_insert_rowid()" not in sql
            assert "INSERT INTO users" in sql
            return FakeCursor(lastrowid=321)

    try:
        conn = FakePostgresRuntimeConnection()
        created_id = write_service.create_user_sqlite(
            conn,
            username="pg_user",
            display_name="PG User",
            password_hash="hash",
            role="member",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)

    assert created_id == 321
    assert len(conn.calls) == 1
    assert "last_insert_rowid()" not in log_output
    assert "DUAL_WRITE_DRY_RUN operation=insert table=users" in log_output
    assert "dry_run=true" in log_output


def run():
    test_app_imports()
    test_login_route_smoke()
    test_index_route_redirects_when_logged_out()
    test_admin_login_redirects_to_sheet()
    test_sheet_route_after_login()
    test_logout_redirects()
    test_create_user_sqlite_with_sqlite_connection()
    test_controlled_dual_write_meta_stays_gated_to_meta()
    test_controlled_dual_write_meta_non_sqlite_runtime_still_attempts_secondary_write()
    test_controlled_dual_write_meta_strict_false_logs_postgres_error_without_blocking_primary()
    test_controlled_dual_write_meta_strict_true_raises_after_primary_write()
    test_create_user_runtime_path_uses_cursor_lastrowid_and_emits_dry_run_log()


if __name__ == "__main__":
    run()
