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

from db_compat import PostgresCompatConnection


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


def test_controlled_dual_write_sheet_update_stays_gated_to_sheets_only():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta,sheets"
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

    postgres_calls: list[tuple[str, tuple[object, ...] | None]] = []

    class FakeCursor:
        def execute(self, sql, params=None):
            postgres_calls.append((sql, params))

        def close(self):
            return None

    class FakeRawConnection:
        def cursor(self):
            return FakeCursor()

    compat_conn = object.__new__(PostgresCompatConnection)
    compat_conn._conn = FakeRawConnection()

    try:
        compat_conn.execute = lambda sql, params=(): None  # type: ignore[attr-defined]
        write_service.update_sheet_name_sqlite(compat_conn, sheet_id=9, name="Renamed sheet")
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    assert any("SAVEPOINT dual_write_sheets_secondary" in call[0] for call in postgres_calls if isinstance(call[0], str))
    assert any("UPDATE sheets" in call[0] for call in postgres_calls if isinstance(call[0], str))
    assert "DUAL_WRITE operation=update table=sheets" in log_output
    assert "postgres_result=success" in log_output
    assert "DUAL_WRITE_DRY_RUN operation=update table=sheets" in log_output
    assert "DUAL_WRITE_SHEETS_SECONDARY table=sheets strategy=reuse_primary_postgres_connection event=SAVEPOINT_START" in log_output
    assert "DUAL_WRITE_SHEETS_SECONDARY table=sheets strategy=reuse_primary_postgres_connection event=EXECUTE_SQL_OK" in log_output


def test_controlled_dual_write_sheet_update_strict_false_logs_postgres_error_without_blocking_primary():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta,sheets"
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
        def execute(self, sql, params=None):
            raise RuntimeError("forced sheets secondary failure")

        def close(self):
            return None

    class FailingPostgresConnection:
        def __init__(self):
            self.rolled_back = False

        def cursor(self):
            return FailingCursor()

        def commit(self):
            raise AssertionError("commit should not be called on failed secondary write")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    failing_connections: list[FailingPostgresConnection] = []

    class FailingPsycopg:
        def connect(self, url, **kwargs):
            conn = FailingPostgresConnection()
            failing_connections.append(conn)
            return conn

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sheets (id INTEGER PRIMARY KEY, name TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 1)")
    conn.execute("INSERT INTO sheets (id, name, sort_order) VALUES (1, 'Before', 1)")
    write_service.psycopg = FailingPsycopg()

    try:
        write_service.update_sheet_name_sqlite(conn, sheet_id=1, name="After")
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    stored_value = conn.execute("SELECT name FROM sheets WHERE id = 1").fetchone()[0]
    assert stored_value == "After"
    assert "DUAL_WRITE operation=update table=sheets" in log_output
    assert "postgres_result=failed" in log_output
    assert "DUAL_WRITE_DRY_RUN operation=update table=sheets" in log_output
    assert failing_connections and failing_connections[0].rolled_back is True


def test_controlled_dual_write_extra_fields_update_reuses_postgres_compat_primary_connection():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta,sheets,extra_fields"
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

    raw_calls: list[tuple[str, tuple[object, ...] | None]] = []

    class FakeCursor:
        def execute(self, sql, params=None):
            raw_calls.append((sql.strip(), params))

        def close(self):
            return None

    class FakeRawConnection:
        def cursor(self):
            return FakeCursor()

    compat_conn = object.__new__(PostgresCompatConnection)
    compat_conn._conn = FakeRawConnection()
    compat_conn.execute = lambda sql, params=(): None  # type: ignore[attr-defined]

    try:
        write_service.update_extra_field_sqlite(
            compat_conn,
            field_id=7,
            sheet_id=3,
            name="Updated field",
            field_type="status",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    assert any("SAVEPOINT dual_write_extra_fields_secondary" in call[0] for call in raw_calls if isinstance(call[0], str))
    assert any("UPDATE extra_fields" in call[0] for call in raw_calls if isinstance(call[0], str))
    assert "DUAL_WRITE operation=update table=extra_fields" in log_output
    assert "postgres_result=success" in log_output
    assert "DUAL_WRITE_DRY_RUN operation=update table=extra_fields" in log_output
    assert "DUAL_WRITE_EXTRA_FIELDS_SECONDARY table=extra_fields strategy=reuse_primary_postgres_connection event=SAVEPOINT_START" in log_output
    assert "DUAL_WRITE_EXTRA_FIELDS_SECONDARY table=extra_fields strategy=reuse_primary_postgres_connection event=EXECUTE_SQL_OK" in log_output


def test_controlled_dual_write_extra_fields_update_strict_false_logs_postgres_error_without_blocking_primary():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta,sheets,extra_fields"
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
        def execute(self, sql, params=None):
            raise RuntimeError("forced extra_fields secondary failure")

        def close(self):
            return None

    class FailingPostgresConnection:
        def __init__(self):
            self.rolled_back = False

        def cursor(self):
            return FailingCursor()

        def commit(self):
            raise AssertionError("commit should not be called on failed secondary write")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    failing_connections: list[FailingPostgresConnection] = []

    class FailingPsycopg:
        def connect(self, url, **kwargs):
            conn = FailingPostgresConnection()
            failing_connections.append(conn)
            return conn

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE extra_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            name TEXT NOT NULL,
            field_type TEXT NOT NULL DEFAULT 'date',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        "INSERT INTO extra_fields (id, sheet_id, field_key, name, field_type, sort_order, is_builtin, active) VALUES (1, 1, 'handover', 'Before', 'status', 1, 1, 1)"
    )
    write_service.psycopg = FailingPsycopg()

    try:
        write_service.update_extra_field_sqlite(
            conn,
            field_id=1,
            sheet_id=1,
            name="After",
            field_type="date",
        )
        write_service.deactivate_extra_field_sqlite(
            conn,
            field_id=1,
            sheet_id=1,
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    stored_row = conn.execute("SELECT name, field_type, active FROM extra_fields WHERE id = 1 AND sheet_id = 1").fetchone()
    assert stored_row["name"] == "After"
    assert stored_row["field_type"] == "date"
    assert stored_row["active"] == 0
    assert "DUAL_WRITE operation=update table=extra_fields" in log_output
    assert "postgres_result=failed" in log_output
    assert "DUAL_WRITE_DRY_RUN operation=update table=extra_fields" in log_output
    assert failing_connections and failing_connections[0].rolled_back is True


def test_controlled_dual_write_units_update_reuses_postgres_compat_primary_connection():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta,sheets,extra_fields,units"
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

    raw_calls: list[tuple[str, tuple[object, ...] | None]] = []

    class FakeCursor:
        def execute(self, sql, params=None):
            raw_calls.append((sql.strip(), params))

        def close(self):
            return None

    class FakeRawConnection:
        def cursor(self):
            return FakeCursor()

    compat_conn = object.__new__(PostgresCompatConnection)
    compat_conn._conn = FakeRawConnection()
    compat_conn.execute = lambda sql, params=(): None  # type: ignore[attr-defined]

    try:
        write_service.update_unit_name_sqlite(
            compat_conn,
            unit_id=11,
            name="Unit 11A",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    assert any("SAVEPOINT dual_write_units_secondary" in call[0] for call in raw_calls if isinstance(call[0], str))
    assert any("UPDATE units" in call[0] for call in raw_calls if isinstance(call[0], str))
    assert "DUAL_WRITE operation=update table=units" in log_output
    assert "postgres_result=success" in log_output
    assert "DUAL_WRITE_DRY_RUN operation=update table=units" in log_output
    assert "DUAL_WRITE_UNITS_SECONDARY table=units strategy=reuse_primary_postgres_connection event=SAVEPOINT_START" in log_output
    assert "DUAL_WRITE_UNITS_SECONDARY table=units strategy=reuse_primary_postgres_connection event=EXECUTE_SQL_OK" in log_output


def test_controlled_dual_write_units_update_strict_false_logs_postgres_error_without_blocking_primary():
    os.environ["DUAL_WRITE_ENABLED"] = "true"
    os.environ["DUAL_WRITE_TABLES"] = "meta,sheets,extra_fields,units"
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
        def execute(self, sql, params=None):
            raise RuntimeError("forced units secondary failure")

        def close(self):
            return None

    class FailingPostgresConnection:
        def __init__(self):
            self.rolled_back = False

        def cursor(self):
            return FailingCursor()

        def commit(self):
            raise AssertionError("commit should not be called on failed secondary write")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    failing_connections: list[FailingPostgresConnection] = []

    class FailingPsycopg:
        def connect(self, url, **kwargs):
            conn = FailingPostgresConnection()
            failing_connections.append(conn)
            return conn

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL
        )
        """
    )
    conn.execute("INSERT INTO units (id, floor_id, sort_order, name) VALUES (1, 1, 1, 'Before')")
    write_service.psycopg = FailingPsycopg()

    try:
        write_service.update_unit_name_sqlite(
            conn,
            unit_id=1,
            name="After",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    stored_row = conn.execute("SELECT name FROM units WHERE id = 1").fetchone()
    assert stored_row["name"] == "After"
    assert "DUAL_WRITE operation=update table=units" in log_output
    assert "postgres_result=failed" in log_output
    assert "DUAL_WRITE_DRY_RUN operation=update table=units" in log_output
    assert failing_connections and failing_connections[0].rolled_back is True


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


def test_controlled_dual_write_meta_reuses_postgres_compat_primary_connection():
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

    raw_calls: list[tuple[str, tuple[object, ...] | None]] = []

    class FakeCursor:
        def execute(self, sql, params=None):
            raw_calls.append((sql.strip(), params))

        def close(self):
            return None

    class FakeRawConnection:
        def cursor(self):
            return FakeCursor()

    compat_conn = object.__new__(PostgresCompatConnection)
    compat_conn._conn = FakeRawConnection()

    class FailingPsycopg:
        def connect(self, url, **kwargs):
            raise AssertionError("psycopg.connect should not be used when reusing compat primary connection")

    write_service.psycopg = FailingPsycopg()

    try:
        result, error, details = write_service._write_meta_to_postgres_secondary(  # type: ignore[attr-defined]
            compat_conn,
            key="site_title",
            value="Compat reuse",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    log_output = "\n".join(messages)
    assert result == "success"
    assert error is None
    assert details["strategy"] == "reuse_primary_postgres_connection"
    assert any("SAVEPOINT dual_write_meta_secondary" in call[0] for call in raw_calls)
    assert any("INSERT INTO meta" in call[0] for call in raw_calls)
    assert "strategy=reuse_primary_postgres_connection" in log_output
    assert "event=EXECUTE_SQL_OK" in log_output


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
    test_controlled_dual_write_sheet_update_stays_gated_to_sheets_only()
    test_controlled_dual_write_meta_non_sqlite_runtime_still_attempts_secondary_write()
    test_controlled_dual_write_meta_reuses_postgres_compat_primary_connection()
    test_controlled_dual_write_meta_strict_false_logs_postgres_error_without_blocking_primary()
    test_controlled_dual_write_meta_strict_true_raises_after_primary_write()
    test_controlled_dual_write_sheet_update_strict_false_logs_postgres_error_without_blocking_primary()
    test_controlled_dual_write_extra_fields_update_reuses_postgres_compat_primary_connection()
    test_controlled_dual_write_extra_fields_update_strict_false_logs_postgres_error_without_blocking_primary()
    test_controlled_dual_write_units_update_reuses_postgres_compat_primary_connection()
    test_controlled_dual_write_units_update_strict_false_logs_postgres_error_without_blocking_primary()
    test_create_user_runtime_path_uses_cursor_lastrowid_and_emits_dry_run_log()


if __name__ == "__main__":
    run()
