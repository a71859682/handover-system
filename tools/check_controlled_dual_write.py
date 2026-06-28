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


def _make_sqlite_sheets_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    return conn


def _make_sqlite_extra_fields_conn() -> sqlite3.Connection:
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
    return conn


def _make_sqlite_units_conn() -> sqlite3.Connection:
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
    return conn


def _make_sqlite_floors_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            block_name TEXT,
            unit_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    return conn


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="controlled-dual-write-"))
    os.environ["APP_DB_PATH"] = str(temp_dir / "site.db")

    config, write_service = _load_modules(
        dual_write_enabled=True,
        dual_write_tables="meta,sheets,extra_fields,units,floors",
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

        sheets_conn = _make_sqlite_sheets_conn()
        sheets_conn.execute("INSERT INTO sheets (id, name, sort_order) VALUES (1, 'Old name', 1)")
        before_sheet_calls = len(postgres_calls)
        write_service.update_sheet_name_sqlite(sheets_conn, sheet_id=1, name="New name")
        sheet_value = sheets_conn.execute("SELECT name FROM sheets WHERE id = 1").fetchone()[0]
        sheet_calls_added = len(postgres_calls) > before_sheet_calls

        extra_fields_conn = _make_sqlite_extra_fields_conn()
        extra_fields_conn.execute(
            "INSERT INTO extra_fields (id, sheet_id, field_key, name, field_type, sort_order, is_builtin, active) VALUES (1, 1, 'initial_check', 'Old field', 'date', 1, 1, 1)"
        )
        before_extra_field_calls = len(postgres_calls)
        write_service.update_extra_field_sqlite(
            extra_fields_conn,
            field_id=1,
            sheet_id=1,
            name="New field",
            field_type="status",
        )
        updated_extra_field = extra_fields_conn.execute(
            "SELECT name, field_type, active FROM extra_fields WHERE id = 1 AND sheet_id = 1"
        ).fetchone()
        extra_field_calls_added = len(postgres_calls) > before_extra_field_calls

        units_conn = _make_sqlite_units_conn()
        units_conn.execute("INSERT INTO units (id, floor_id, sort_order, name) VALUES (1, 1, 1, 'Unit 101')")
        before_unit_calls = len(postgres_calls)
        write_service.update_unit_name_sqlite(units_conn, unit_id=1, name="Unit 101A")
        updated_unit = units_conn.execute("SELECT name FROM units WHERE id = 1").fetchone()
        unit_calls_added = len(postgres_calls) > before_unit_calls

        floors_conn = _make_sqlite_floors_conn()
        floors_conn.execute(
            "INSERT INTO floors (id, sheet_id, sort_order, name, block_name, unit_count) VALUES (1, 1, 1, '1F', 'A', 3)"
        )
        before_floor_calls = len(postgres_calls)
        write_service.update_floor_fields_sqlite(floors_conn, floor_id=1, name="1F-new", block_name="B")
        updated_floor = floors_conn.execute("SELECT name, block_name, unit_count FROM floors WHERE id = 1").fetchone()
        floor_calls_added = len(postgres_calls) > before_floor_calls

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

        sheets_conn_before_failure = _make_sqlite_sheets_conn()
        sheets_conn_before_failure.execute("INSERT INTO sheets (id, name, sort_order) VALUES (2, 'Before failure', 2)")
        write_service.update_sheet_name_sqlite(sheets_conn_before_failure, sheet_id=2, name="After failure")
        sheet_value_after_failure = sheets_conn_before_failure.execute(
            "SELECT name FROM sheets WHERE id = 2"
        ).fetchone()[0]

        extra_fields_conn_before_failure = _make_sqlite_extra_fields_conn()
        extra_fields_conn_before_failure.execute(
            "INSERT INTO extra_fields (id, sheet_id, field_key, name, field_type, sort_order, is_builtin, active) VALUES (2, 1, 'handover', 'Before failure', 'status', 2, 1, 1)"
        )
        write_service.update_extra_field_sqlite(
            extra_fields_conn_before_failure,
            field_id=2,
            sheet_id=1,
            name="After failure",
            field_type="date",
        )
        extra_field_after_failure = extra_fields_conn_before_failure.execute(
            "SELECT name, field_type, active FROM extra_fields WHERE id = 2 AND sheet_id = 1"
        ).fetchone()
        write_service.deactivate_extra_field_sqlite(
            extra_fields_conn_before_failure,
            field_id=2,
            sheet_id=1,
        )
        extra_field_after_deactivate = extra_fields_conn_before_failure.execute(
            "SELECT name, field_type, active FROM extra_fields WHERE id = 2 AND sheet_id = 1"
        ).fetchone()

        units_conn_before_failure = _make_sqlite_units_conn()
        units_conn_before_failure.execute("INSERT INTO units (id, floor_id, sort_order, name) VALUES (2, 1, 2, 'Before unit failure')")
        write_service.update_unit_name_sqlite(units_conn_before_failure, unit_id=2, name="After unit failure")
        unit_after_failure = units_conn_before_failure.execute("SELECT name FROM units WHERE id = 2").fetchone()

        floors_conn_before_failure = _make_sqlite_floors_conn()
        floors_conn_before_failure.execute(
            "INSERT INTO floors (id, sheet_id, sort_order, name, block_name, unit_count) VALUES (2, 1, 2, 'Before floor failure', 'A', 5)"
        )
        write_service.update_floor_fields_sqlite(
            floors_conn_before_failure,
            floor_id=2,
            name="After floor failure",
            block_name="C",
        )
        floor_after_failure = floors_conn_before_failure.execute(
            "SELECT name, block_name, unit_count FROM floors WHERE id = 2"
        ).fetchone()

        log_output = stream.getvalue()

        allowed_tables = write_service._controlled_dual_write_tables()  # type: ignore[attr-defined]
        checks = [
            ("USE_SQLALCHEMY_WRITES disabled", config.USE_SQLALCHEMY_WRITES is False),
            ("DUAL_WRITE_ENABLED enabled", config.DUAL_WRITE_ENABLED is True),
            ("DUAL_WRITE_TABLES limited to meta, sheets, extra_fields, units, and floors", allowed_tables == {"meta", "sheets", "extra_fields", "units", "floors"}),
            ("Meta dual write is gated on", write_service._is_controlled_dual_write_enabled_for("meta") is True),  # type: ignore[attr-defined]
            ("Sheets dual write is gated on", write_service._is_controlled_dual_write_enabled_for("sheets") is True),  # type: ignore[attr-defined]
            ("Extra fields dual write is gated on", write_service._is_controlled_dual_write_enabled_for("extra_fields") is True),  # type: ignore[attr-defined]
            ("Units dual write is gated on", write_service._is_controlled_dual_write_enabled_for("units") is True),  # type: ignore[attr-defined]
            ("Floors dual write is gated on", write_service._is_controlled_dual_write_enabled_for("floors") is True),  # type: ignore[attr-defined]
            ("Users do not dual write to PostgreSQL", non_meta_calls_unchanged),
            ("Non-SQLite runtime still attempts PostgreSQL secondary", non_sqlite_primary_attempted),
            ("Meta primary SQLite write still works", sqlite_value == "Controlled Dual Write"),
            ("Sheets primary SQLite write still works", sheet_value == "New name"),
            ("Extra fields primary SQLite update still works", updated_extra_field["name"] == "New field" and updated_extra_field["field_type"] == "status" and updated_extra_field["active"] == 1),
            ("Units primary SQLite update still works", updated_unit["name"] == "Unit 101A"),
            ("Floors primary SQLite update still works", updated_floor["name"] == "1F-new" and updated_floor["block_name"] == "B" and updated_floor["unit_count"] == 3),
            ("Meta primary write survives failed secondary in non-strict mode", sqlite_value_after_failure == "Primary survives secondary failure"),
            ("Sheets primary write survives failed secondary in non-strict mode", sheet_value_after_failure == "After failure"),
            ("Extra fields primary write survives failed secondary in non-strict mode", extra_field_after_failure["name"] == "After failure" and extra_field_after_failure["field_type"] == "date"),
            ("Units primary write survives failed secondary in non-strict mode", unit_after_failure["name"] == "After unit failure"),
            ("Floors primary write survives failed secondary in non-strict mode", floor_after_failure["name"] == "After floor failure" and floor_after_failure["block_name"] == "C" and floor_after_failure["unit_count"] == 5),
            ("Extra fields deactivate still updates SQLite primary", extra_field_after_deactivate["active"] == 0),
            ("Meta PostgreSQL secondary write can be attempted", any(call[0] == "CONNECT" for call in postgres_calls)),
            ("Sheets PostgreSQL secondary write can be attempted", sheet_calls_added),
            ("Extra fields PostgreSQL secondary write can be attempted", extra_field_calls_added),
            ("Units PostgreSQL secondary write can be attempted", unit_calls_added),
            ("Floors PostgreSQL secondary write can be attempted", floor_calls_added),
            ("Controlled dual write log emitted", "DUAL_WRITE operation=upsert table=meta" in log_output),
            ("Controlled dual write log reports success", "postgres_result=success" in log_output),
            ("Controlled dual write reports failed on non-strict secondary error", "postgres_result=failed" in log_output),
            ("Sheets controlled dual write log emitted", "DUAL_WRITE operation=update table=sheets" in log_output),
            ("Extra fields controlled dual write log emitted", "DUAL_WRITE operation=update table=extra_fields" in log_output),
            ("Units controlled dual write log emitted", "DUAL_WRITE operation=update table=units" in log_output),
            ("Floors controlled dual write log emitted", "DUAL_WRITE operation=update table=floors" in log_output),
            ("Controlled dual write no longer reports skipped_non_sqlite_primary", "skipped_non_sqlite_primary" not in log_output),
            ("Secondary debug log includes connect step", "DUAL_WRITE_META_SECONDARY strategy=raw_psycopg event=CONNECT_START" in log_output),
            ("Secondary debug log includes execute step", "DUAL_WRITE_META_SECONDARY strategy=raw_psycopg event=EXECUTE_SQL_START" in log_output),
            ("Secondary debug log includes rollback step on failure", "DUAL_WRITE_META_SECONDARY strategy=raw_psycopg event=ROLLBACK" in log_output),
            ("Sheets secondary debug log includes savepoint step", "DUAL_WRITE_SHEETS_SECONDARY table=sheets strategy=raw_psycopg event=EXECUTE_SQL_START" in log_output),
            ("Sheets secondary debug log includes release savepoint step", "DUAL_WRITE_SHEETS_SECONDARY table=sheets strategy=raw_psycopg event=ROLLBACK" in log_output or "DUAL_WRITE_SHEETS_SECONDARY table=sheets strategy=raw_psycopg event=COMMIT_OK" in log_output),
            ("Extra fields secondary debug log includes execute step", "DUAL_WRITE_EXTRA_FIELDS_SECONDARY table=extra_fields strategy=raw_psycopg event=EXECUTE_SQL_START" in log_output),
            ("Extra fields secondary debug log includes rollback step", "DUAL_WRITE_EXTRA_FIELDS_SECONDARY table=extra_fields strategy=raw_psycopg event=ROLLBACK" in log_output),
            ("Units secondary debug log includes execute step", "DUAL_WRITE_UNITS_SECONDARY table=units strategy=raw_psycopg event=EXECUTE_SQL_START" in log_output),
            ("Units secondary debug log includes rollback step", "DUAL_WRITE_UNITS_SECONDARY table=units strategy=raw_psycopg event=ROLLBACK" in log_output),
            ("Floors secondary debug log includes execute step", "DUAL_WRITE_FLOORS_SECONDARY table=floors strategy=raw_psycopg event=EXECUTE_SQL_START" in log_output),
            ("Floors secondary debug log includes rollback step", "DUAL_WRITE_FLOORS_SECONDARY table=floors strategy=raw_psycopg event=ROLLBACK" in log_output),
            ("Dry-run log still emitted", "DUAL_WRITE_DRY_RUN operation=upsert table=meta" in log_output),
            ("Sheets dry-run log still emitted", "DUAL_WRITE_DRY_RUN operation=update table=sheets" in log_output),
            ("Extra fields dry-run log still emitted", "DUAL_WRITE_DRY_RUN operation=update table=extra_fields" in log_output),
            ("Units dry-run log still emitted", "DUAL_WRITE_DRY_RUN operation=update table=units" in log_output),
            ("Floors dry-run log still emitted", "DUAL_WRITE_DRY_RUN operation=update table=floors" in log_output),
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
