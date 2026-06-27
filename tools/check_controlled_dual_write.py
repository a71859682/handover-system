from __future__ import annotations

import importlib
import io
import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _load_modules(*, dual_write_enabled: bool, dual_write_tables: str, dual_write_strict: bool, dual_write_dry_run: bool):
    os.environ["DUAL_WRITE_ENABLED"] = "true" if dual_write_enabled else "false"
    os.environ["DUAL_WRITE_TABLES"] = dual_write_tables
    os.environ["DUAL_WRITE_STRICT"] = "true" if dual_write_strict else "false"
    os.environ["DUAL_WRITE_DRY_RUN"] = "true" if dual_write_dry_run else "false"
    os.environ["USE_SQLALCHEMY_WRITES"] = "false"

    import config
    import services.write_service as write_service

    config = importlib.reload(config)
    write_service = importlib.reload(write_service)
    return config, write_service


def _make_sqlite_meta_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn


def _make_sqlite_users_conn() -> sqlite3.Connection:
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
    return conn


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="controlled-dual-write-"))
    os.environ["APP_DB_PATH"] = str(temp_dir / "site.db")

    config, write_service = _load_modules(
        dual_write_enabled=True,
        dual_write_tables="meta",
        dual_write_strict=False,
        dual_write_dry_run=True,
    )

    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    postgres_calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def __init__(self, should_fail: bool = False):
            self.should_fail = should_fail

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql: str, params: tuple[object, ...]):
            if self.should_fail:
                raise RuntimeError("forced secondary failure")
            postgres_calls.append((sql, params))

        def close(self):
            return None

    class FakePostgresConnection:
        def __init__(self, should_fail: bool = False):
            self.should_fail = should_fail
            self.committed = False
            self.rolled_back = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor(should_fail=self.should_fail)

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    class FakePsycopg:
        def __init__(self, should_fail: bool = False):
            self.should_fail = should_fail

        def connect(self, database_url: str, **kwargs):
            postgres_calls.append(("CONNECT", (database_url, kwargs)))
            return FakePostgresConnection(should_fail=self.should_fail)

    class NonSqlitePrimaryConnection:
        pass

    try:
        write_service.psycopg = FakePsycopg()
        write_service.DATABASE_URL = "postgresql://example.test/app"

        conn = _make_sqlite_meta_conn()
        write_service.upsert_setting_sqlite(conn, "site_title", "Controlled Dual Write")
        sqlite_value = conn.execute("SELECT value FROM meta WHERE key = ?", ("site_title",)).fetchone()[0]

        before_non_meta_calls = len(postgres_calls)
        write_service.create_user_sqlite(
            _make_sqlite_users_conn(),
            username="only_sqlite",
            display_name="Only SQLite",
            password_hash="hash",
            role="member",
        )
        non_meta_calls_unchanged = len(postgres_calls) == before_non_meta_calls

        before_non_sqlite_calls = len(postgres_calls)
        write_service._maybe_controlled_dual_write_meta(  # type: ignore[attr-defined]
            NonSqlitePrimaryConnection(),
            operation="upsert",
            key="ignored",
            value="ignored",
        )
        non_sqlite_primary_attempted = len(postgres_calls) > before_non_sqlite_calls

        write_service.psycopg = FakePsycopg(should_fail=True)
        conn_before_failure = _make_sqlite_meta_conn()
        write_service.upsert_setting_sqlite(conn_before_failure, "site_title", "Primary survives secondary failure")
        sqlite_value_after_failure = conn_before_failure.execute(
            "SELECT value FROM meta WHERE key = ?",
            ("site_title",),
        ).fetchone()[0]

        log_output = stream.getvalue()

        allowed_tables = write_service._controlled_dual_write_tables()  # type: ignore[attr-defined]
        checks = [
            ("USE_SQLALCHEMY_WRITES disabled", config.USE_SQLALCHEMY_WRITES is False),
            ("DUAL_WRITE_ENABLED enabled", config.DUAL_WRITE_ENABLED is True),
            ("DUAL_WRITE_TABLES limited to meta/settings", allowed_tables == {"meta"}),
            ("Meta dual write is gated on", write_service._is_controlled_dual_write_enabled_for("meta") is True),  # type: ignore[attr-defined]
            ("Users do not dual write to PostgreSQL", non_meta_calls_unchanged),
            ("Non-SQLite runtime still attempts PostgreSQL secondary", non_sqlite_primary_attempted),
            ("Meta primary SQLite write still works", sqlite_value == "Controlled Dual Write"),
            ("Meta primary write survives failed secondary in non-strict mode", sqlite_value_after_failure == "Primary survives secondary failure"),
            ("Meta PostgreSQL secondary write can be attempted", any(call[0] == "CONNECT" for call in postgres_calls)),
            ("Controlled dual write log emitted", "DUAL_WRITE operation=upsert table=meta" in log_output),
            ("Controlled dual write log reports success", "postgres_result=success" in log_output),
            ("Controlled dual write reports failed on non-strict secondary error", "postgres_result=failed" in log_output),
            ("Controlled dual write no longer reports skipped_non_sqlite_primary", "skipped_non_sqlite_primary" not in log_output),
            ("Secondary debug log includes connect step", "DUAL_WRITE_META_SECONDARY strategy=raw_psycopg event=CONNECT_START" in log_output),
            ("Secondary debug log includes execute step", "DUAL_WRITE_META_SECONDARY strategy=raw_psycopg event=EXECUTE_SQL_START" in log_output),
            ("Secondary debug log includes rollback step on failure", "DUAL_WRITE_META_SECONDARY strategy=raw_psycopg event=ROLLBACK" in log_output),
            ("Dry-run log still emitted", "DUAL_WRITE_DRY_RUN operation=upsert table=meta" in log_output),
        ]

        failed = [label for label, ok in checks if not ok]

        print(f"USE_SQLALCHEMY_WRITES={str(config.USE_SQLALCHEMY_WRITES).lower()}")
        print(f"DUAL_WRITE_ENABLED={str(config.DUAL_WRITE_ENABLED).lower()}")
        print(f"DUAL_WRITE_TABLES={','.join(config.DUAL_WRITE_TABLES)}")
        print(f"DUAL_WRITE_STRICT={str(config.DUAL_WRITE_STRICT).lower()}")
        print("LOG_OUTPUT_BEGIN")
        print(log_output.strip())
        print("LOG_OUTPUT_END")
        for label, ok in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {label}")

        if failed:
            print("FAIL")
            return 1

        print("PASS")
        return 0
    finally:
        logger.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
