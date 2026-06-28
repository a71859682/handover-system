from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Mapping

from flask import has_app_context

from config import (
    DATABASE_URL,
    DUAL_WRITE_DRY_RUN,
    DUAL_WRITE_ENABLED,
    DUAL_WRITE_STRICT,
    DUAL_WRITE_TABLES,
)
from database import db
from db_compat import PostgresCompatConnection

try:
    import psycopg
except Exception:
    psycopg = None


LOGGER = logging.getLogger("dual_write")
ALLOWED_CONTROLLED_DUAL_WRITE_TABLES = frozenset({"meta"})
POSTGRES_CONNECT_TIMEOUT_SECONDS = 3
POSTGRES_STATEMENT_TIMEOUT_MS = 3000


def _ensure_dual_write_logger() -> logging.Logger:
    logger = LOGGER
    logger.setLevel(logging.INFO)
    logger.propagate = True

    if not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger


def _normalize_log_fields(payload: Mapping[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, tuple):
            normalized[key] = list(value)
        else:
            normalized[key] = value
    return normalized


def _normalize_table_name(table: str) -> str:
    normalized = table.strip().lower()
    if normalized == "settings":
        return "meta"
    return normalized


def _controlled_dual_write_tables() -> set[str]:
    return {_normalize_table_name(table) for table in DUAL_WRITE_TABLES}

def _is_controlled_dual_write_enabled_for(table: str) -> bool:
    normalized = _normalize_table_name(table)
    return (
        DUAL_WRITE_ENABLED
        and normalized in ALLOWED_CONTROLLED_DUAL_WRITE_TABLES
        and normalized in _controlled_dual_write_tables()
    )


def _log_dual_write_dry_run(
    *,
    operation: str,
    table: str,
    key: Mapping[str, object],
    fields: Mapping[str, object],
) -> None:
    if not DUAL_WRITE_DRY_RUN:
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    logger = _ensure_dual_write_logger()
    logger.info(
        "DUAL_WRITE_DRY_RUN operation=%s table=%s key=%r fields=%r timestamp=%s dry_run=true",
        operation,
        table,
        _normalize_log_fields(key),
        _normalize_log_fields(fields),
        timestamp,
    )


def _future_dual_write_placeholder(operation: str, payload: Mapping[str, object]) -> None:
    # Reserved for the future dual-write rollout. This version intentionally
    # keeps SQLite as the only write target.
    _ = (operation, payload)


def _log_controlled_dual_write(
    *,
    operation: str,
    table: str,
    key: Mapping[str, object],
    sqlite_result: str,
    postgres_result: str,
    error: str | None,
) -> None:
    logger = _ensure_dual_write_logger()
    logger.info(
        "DUAL_WRITE operation=%s table=%s key=%r sqlite_result=%s postgres_result=%s error=%r timestamp=%s",
        operation,
        _normalize_table_name(table),
        _normalize_log_fields(key),
        sqlite_result,
        postgres_result,
        error,
        datetime.now(timezone.utc).isoformat(),
    )


def _log_meta_secondary_event(
    *,
    strategy: str,
    event: str,
    elapsed_ms: int,
    key: str,
    step_elapsed_ms: int | None = None,
    error: str | None = None,
) -> None:
    logger = _ensure_dual_write_logger()
    logger.info(
        "DUAL_WRITE_META_SECONDARY strategy=%s event=%s key=%r elapsed_ms=%s step_elapsed_ms=%s error=%r",
        strategy,
        event,
        key,
        elapsed_ms,
        step_elapsed_ms,
        error,
    )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _step_elapsed_ms(step_started: float) -> int:
    return int((time.perf_counter() - step_started) * 1000)


def _is_postgres_compat_primary_connection(conn) -> bool:
    return isinstance(conn, PostgresCompatConnection)


def _write_meta_with_existing_psycopg_connection(raw_conn, *, key: str, value: str) -> tuple[str, str | None, dict[str, object]]:
    strategy = "reuse_primary_postgres_connection"
    started = time.perf_counter()
    cur = None
    details: dict[str, object] = {"strategy": strategy}
    savepoint_name = "dual_write_meta_secondary"
    try:
        _log_meta_secondary_event(strategy=strategy, event="BEGIN_TX", key=key, elapsed_ms=0)
        cursor_started = time.perf_counter()
        cur = raw_conn.cursor()
        _log_meta_secondary_event(
            strategy=strategy,
            event="CURSOR_OK",
            key=key,
            elapsed_ms=_elapsed_ms(started),
            step_elapsed_ms=_step_elapsed_ms(cursor_started),
        )
        savepoint_started = time.perf_counter()
        _log_meta_secondary_event(strategy=strategy, event="SAVEPOINT_START", key=key, elapsed_ms=_elapsed_ms(started))
        cur.execute(f"SAVEPOINT {savepoint_name}")
        _log_meta_secondary_event(
            strategy=strategy,
            event="SAVEPOINT_OK",
            key=key,
            elapsed_ms=_elapsed_ms(started),
            step_elapsed_ms=_step_elapsed_ms(savepoint_started),
        )
        execute_started = time.perf_counter()
        _log_meta_secondary_event(strategy=strategy, event="EXECUTE_SQL_START", key=key, elapsed_ms=_elapsed_ms(started))
        cur.execute(
            """
            INSERT INTO meta(key, value)
            VALUES (%s, %s)
            ON CONFLICT(key)
            DO UPDATE
            SET value = EXCLUDED.value
            """,
            (key, value),
        )
        release_started = time.perf_counter()
        cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        elapsed_ms = _elapsed_ms(started)
        details["elapsed_ms"] = elapsed_ms
        details["execute_step_elapsed_ms"] = _step_elapsed_ms(execute_started)
        details["release_savepoint_step_elapsed_ms"] = _step_elapsed_ms(release_started)
        _log_meta_secondary_event(strategy=strategy, event="EXECUTE_SQL_OK", key=key, elapsed_ms=elapsed_ms)
        _log_meta_secondary_event(
            strategy=strategy,
            event="RELEASE_SAVEPOINT_OK",
            key=key,
            elapsed_ms=elapsed_ms,
            step_elapsed_ms=details["release_savepoint_step_elapsed_ms"],
        )
        return "success", None, details
    except BaseException as exc:
        if isinstance(exc, (SystemExit, KeyboardInterrupt)):
            raise
        if cur is not None:
            try:
                rollback_started = time.perf_counter()
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="ROLLBACK",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    step_elapsed_ms=_step_elapsed_ms(rollback_started),
                    error=str(exc),
                )
            except Exception as rollback_exc:
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="ROLLBACK_FAILED",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    error=str(rollback_exc),
                )
        elapsed_ms = _elapsed_ms(started)
        details["elapsed_ms"] = elapsed_ms
        details["exception_type"] = type(exc).__name__
        _log_meta_secondary_event(
            strategy=strategy,
            event="EXECUTE_SQL_FAILED",
            key=key,
            elapsed_ms=elapsed_ms,
            error=str(exc),
        )
        return "failed", str(exc), details
    finally:
        if cur is not None:
            try:
                close_started = time.perf_counter()
                cur.close()
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="CLOSE",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    step_elapsed_ms=_step_elapsed_ms(close_started),
                )
            except Exception as exc:
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="CLOSE_FAILED",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    error=str(exc),
                )


def _write_meta_with_sqlalchemy_engine(*, key: str, value: str) -> tuple[str, str | None, dict[str, object]]:
    strategy = "sqlalchemy_engine"
    started = time.perf_counter()
    details: dict[str, object] = {"strategy": strategy}
    _log_meta_secondary_event(strategy=strategy, event="CONNECT_START", key=key, elapsed_ms=0)
    try:
        connect_started = time.perf_counter()
        engine = db.engine
        _log_meta_secondary_event(
            strategy=strategy,
            event="CONNECT_OK",
            key=key,
            elapsed_ms=_elapsed_ms(started),
            step_elapsed_ms=_step_elapsed_ms(connect_started),
        )
        with engine.begin() as sql_conn:
            _log_meta_secondary_event(
                strategy=strategy,
                event="BEGIN_TX",
                key=key,
                elapsed_ms=_elapsed_ms(started),
            )
            timeout_started = time.perf_counter()
            sql_conn.exec_driver_sql(
                "SET LOCAL statement_timeout = %s",
                (str(POSTGRES_STATEMENT_TIMEOUT_MS),),
            )
            _log_meta_secondary_event(
                strategy=strategy,
                event="SET_TIMEOUT_OK",
                key=key,
                elapsed_ms=_elapsed_ms(started),
                step_elapsed_ms=_step_elapsed_ms(timeout_started),
            )
            execute_started = time.perf_counter()
            _log_meta_secondary_event(strategy=strategy, event="EXECUTE_SQL_START", key=key, elapsed_ms=_elapsed_ms(started))
            sql_conn.exec_driver_sql(
                """
                INSERT INTO meta(key, value)
                VALUES (%s, %s)
                ON CONFLICT(key)
                DO UPDATE
                SET value = EXCLUDED.value
                """,
                (key, value),
            )
            _log_meta_secondary_event(
                strategy=strategy,
                event="EXECUTE_SQL_OK",
                key=key,
                elapsed_ms=_elapsed_ms(started),
                step_elapsed_ms=_step_elapsed_ms(execute_started),
            )
            commit_started = time.perf_counter()
            _log_meta_secondary_event(
                strategy=strategy,
                event="COMMIT_START",
                key=key,
                elapsed_ms=_elapsed_ms(started),
            )
        elapsed_ms = _elapsed_ms(started)
        details["elapsed_ms"] = elapsed_ms
        details["commit_step_elapsed_ms"] = _step_elapsed_ms(commit_started)
        _log_meta_secondary_event(
            strategy=strategy,
            event="COMMIT_OK",
            key=key,
            elapsed_ms=elapsed_ms,
            step_elapsed_ms=details["commit_step_elapsed_ms"],
        )
        return "success", None, details
    except BaseException as exc:
        if isinstance(exc, (SystemExit, KeyboardInterrupt)):
            raise
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        details["elapsed_ms"] = elapsed_ms
        details["exception_type"] = type(exc).__name__
        _log_meta_secondary_event(
            strategy=strategy,
            event="ROLLBACK",
            key=key,
            elapsed_ms=elapsed_ms,
            error=str(exc),
        )
        return "failed", str(exc), details
    finally:
        _log_meta_secondary_event(
            strategy=strategy,
            event="CLOSE",
            key=key,
            elapsed_ms=_elapsed_ms(started),
        )


def _write_meta_with_raw_psycopg(*, key: str, value: str) -> tuple[str, str | None, dict[str, object]]:
    strategy = "raw_psycopg"
    started = time.perf_counter()
    conn = None
    cur = None
    details: dict[str, object] = {"strategy": strategy}
    try:
        _log_meta_secondary_event(strategy=strategy, event="CONNECT_START", key=key, elapsed_ms=0)
        connect_started = time.perf_counter()
        conn = psycopg.connect(
            DATABASE_URL,
            connect_timeout=POSTGRES_CONNECT_TIMEOUT_SECONDS,
            options=f"-c statement_timeout={POSTGRES_STATEMENT_TIMEOUT_MS}",
        )
        _log_meta_secondary_event(
            strategy=strategy,
            event="CONNECT_OK",
            key=key,
            elapsed_ms=_elapsed_ms(started),
            step_elapsed_ms=_step_elapsed_ms(connect_started),
        )
        _log_meta_secondary_event(
            strategy=strategy,
            event="BEGIN_TX",
            key=key,
            elapsed_ms=_elapsed_ms(started),
        )
        cursor_started = time.perf_counter()
        cur = conn.cursor()
        _log_meta_secondary_event(
            strategy=strategy,
            event="CURSOR_OK",
            key=key,
            elapsed_ms=_elapsed_ms(started),
            step_elapsed_ms=_step_elapsed_ms(cursor_started),
        )
        execute_started = time.perf_counter()
        _log_meta_secondary_event(
            strategy=strategy,
            event="EXECUTE_SQL_START",
            key=key,
            elapsed_ms=_elapsed_ms(started),
        )
        cur.execute(
            """
            INSERT INTO meta(key, value)
            VALUES (%s, %s)
            ON CONFLICT(key)
            DO UPDATE
            SET value = EXCLUDED.value
            """,
            (key, value),
        )
        _log_meta_secondary_event(
            strategy=strategy,
            event="EXECUTE_SQL_OK",
            key=key,
            elapsed_ms=_elapsed_ms(started),
            step_elapsed_ms=_step_elapsed_ms(execute_started),
        )
        commit_started = time.perf_counter()
        _log_meta_secondary_event(
            strategy=strategy,
            event="COMMIT_START",
            key=key,
            elapsed_ms=_elapsed_ms(started),
        )
        conn.commit()
        elapsed_ms = _elapsed_ms(started)
        details["elapsed_ms"] = elapsed_ms
        details["connect_step_elapsed_ms"] = _step_elapsed_ms(connect_started)
        details["execute_step_elapsed_ms"] = _step_elapsed_ms(execute_started)
        details["commit_step_elapsed_ms"] = _step_elapsed_ms(commit_started)
        _log_meta_secondary_event(
            strategy=strategy,
            event="COMMIT_OK",
            key=key,
            elapsed_ms=elapsed_ms,
            step_elapsed_ms=details["commit_step_elapsed_ms"],
        )
        return "success", None, details
    except BaseException as exc:
        if isinstance(exc, (SystemExit, KeyboardInterrupt)):
            raise
        if conn is not None:
            try:
                rollback_started = time.perf_counter()
                conn.rollback()
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="ROLLBACK",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    step_elapsed_ms=_step_elapsed_ms(rollback_started),
                    error=str(exc),
                )
            except Exception as rollback_exc:
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="ROLLBACK_FAILED",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    error=str(rollback_exc),
                )
        elapsed_ms = _elapsed_ms(started)
        details["elapsed_ms"] = elapsed_ms
        details["exception_type"] = type(exc).__name__
        return "failed", str(exc), details
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception as exc:
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="CLOSE_CURSOR_FAILED",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    error=str(exc),
                )
        if conn is not None:
            try:
                close_started = time.perf_counter()
                conn.close()
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="CLOSE",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    step_elapsed_ms=_step_elapsed_ms(close_started),
                )
            except Exception as exc:
                _log_meta_secondary_event(
                    strategy=strategy,
                    event="CLOSE_FAILED",
                    key=key,
                    elapsed_ms=_elapsed_ms(started),
                    error=str(exc),
                )


def _write_meta_to_postgres_secondary(conn=None, *, key: str, value: str) -> tuple[str, str | None, dict[str, object]]:
    if not DATABASE_URL:
        return "skipped_no_database_url", "DATABASE_URL is not configured", {"strategy": "none"}
    if psycopg is None:
        return "skipped_no_psycopg", "psycopg is not installed", {"strategy": "none"}
    if _is_postgres_compat_primary_connection(conn):
        return _write_meta_with_existing_psycopg_connection(conn._conn, key=key, value=value)
    if has_app_context():
        return _write_meta_with_sqlalchemy_engine(key=key, value=value)
    return _write_meta_with_raw_psycopg(key=key, value=value)


def _maybe_controlled_dual_write_meta(
    conn,
    *,
    operation: str,
    key: str,
    value: str,
) -> None:
    if not _is_controlled_dual_write_enabled_for("meta"):
        return

    postgres_result, error, _details = _write_meta_to_postgres_secondary(conn, key=key, value=value)
    _log_controlled_dual_write(
        operation=operation,
        table="meta",
        key={"key": key},
        sqlite_result="success",
        postgres_result=postgres_result,
        error=error,
    )
    if postgres_result == "failed" and DUAL_WRITE_STRICT:
        raise RuntimeError(f"Controlled dual write failed for meta key '{key}': {error}")


def _require_lastrowid(cursor, *, table: str) -> int:
    created_id = getattr(cursor, "lastrowid", None)
    if created_id is None:
        raise RuntimeError(f"Insert into {table} did not return lastrowid on the current runtime path")
    return int(created_id)


def upsert_setting_sqlite(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO meta (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    _log_dual_write_dry_run(
        operation="upsert",
        table="meta",
        key={"key": key},
        fields={"value": value},
    )
    _maybe_controlled_dual_write_meta(
        conn,
        operation="upsert",
        key=key,
        value=value,
    )
    _future_dual_write_placeholder("upsert_setting", {"key": key, "value": value})


def seed_settings_sqlite(conn: sqlite3.Connection, default_settings: Mapping[str, str]) -> None:
    for key, value in default_settings.items():
        row = conn.execute("SELECT key FROM meta WHERE key = ?", (key,)).fetchone()
        if not row:
            upsert_setting_sqlite(conn, key, value)


def create_user_sqlite(
    conn: sqlite3.Connection,
    *,
    username: str,
    display_name: str,
    password_hash: str,
    role: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        (username, display_name, password_hash, role),
    )
    created_id = _require_lastrowid(cur, table="users")
    _log_dual_write_dry_run(
        operation="insert",
        table="users",
        key={"id": created_id},
        fields={
            "username": username,
            "display_name": display_name,
            "password_hash": password_hash,
            "role": role,
        },
    )
    _future_dual_write_placeholder(
        "create_user",
        {
            "user_id": created_id,
            "username": username,
            "display_name": display_name,
            "password_hash": password_hash,
            "role": role,
        },
    )
    return created_id


def update_user_sqlite(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    display_name: str,
    role: str,
    password_hash: str | None = None,
) -> None:
    if password_hash:
        conn.execute(
            """
            UPDATE users
            SET username = ?, display_name = ?, password_hash = ?, role = ?
            WHERE id = ?
            """,
            (username, display_name, password_hash, role, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET username = ?, display_name = ?, role = ? WHERE id = ?",
            (username, display_name, role, user_id),
        )
    changed_fields: dict[str, object] = {
        "username": username,
        "display_name": display_name,
        "role": role,
    }
    if password_hash:
        changed_fields["password_hash"] = password_hash
    _log_dual_write_dry_run(
        operation="update",
        table="users",
        key={"id": user_id},
        fields=changed_fields,
    )
    _future_dual_write_placeholder(
        "update_user",
        {
            "user_id": user_id,
            "username": username,
            "display_name": display_name,
            "password_hash": password_hash,
            "role": role,
        },
    )


def create_sheet_sqlite(conn: sqlite3.Connection, *, name: str, sort_order: int) -> int:
    cur = conn.execute("INSERT INTO sheets (name, sort_order) VALUES (?, ?)", (name, sort_order))
    sheet_id = _require_lastrowid(cur, table="sheets")
    _log_dual_write_dry_run(
        operation="insert",
        table="sheets",
        key={"id": sheet_id},
        fields={"name": name, "sort_order": sort_order},
    )
    _future_dual_write_placeholder(
        "create_sheet",
        {"sheet_id": sheet_id, "name": name, "sort_order": sort_order},
    )
    return sheet_id


def create_builtin_extra_fields_sqlite(
    conn: sqlite3.Connection,
    *,
    sheet_id: int,
    builtin_fields: Mapping[str, Mapping[str, object]],
) -> None:
    for field_key, field in builtin_fields.items():
        conn.execute(
            """
            INSERT INTO extra_fields
            (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
            VALUES (?, ?, ?, ?, ?, 1, 1)
            """,
            (sheet_id, field_key, field["name"], field["type"], field["sort_order"]),
        )
        _log_dual_write_dry_run(
            operation="insert",
            table="extra_fields",
            key={"sheet_id": sheet_id, "field_key": field_key},
            fields={
                "name": field["name"],
                "field_type": field["type"],
                "sort_order": field["sort_order"],
                "is_builtin": 1,
                "active": 1,
            },
        )
    _future_dual_write_placeholder(
        "create_builtin_extra_fields",
        {"sheet_id": sheet_id, "field_keys": tuple(builtin_fields)},
    )


def update_sheet_name_sqlite(conn: sqlite3.Connection, *, sheet_id: int, name: str) -> None:
    conn.execute("UPDATE sheets SET name = ? WHERE id = ?", (name, sheet_id))
    _log_dual_write_dry_run(
        operation="update",
        table="sheets",
        key={"id": sheet_id},
        fields={"name": name},
    )
    _future_dual_write_placeholder("update_sheet_name", {"sheet_id": sheet_id, "name": name})


def upsert_progress_sqlite(
    conn: sqlite3.Connection,
    *,
    unit_id: int,
    task_id: int,
    value: str,
    updated_by: int,
) -> None:
    conn.execute(
        """
        INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(unit_id, task_id) DO UPDATE SET
            value = excluded.value,
            updated_by = excluded.updated_by,
            updated_at = CURRENT_TIMESTAMP
        """,
        (unit_id, task_id, value, updated_by),
    )
    _log_dual_write_dry_run(
        operation="upsert",
        table="progress",
        key={"unit_id": unit_id, "task_id": task_id},
        fields={"value": value, "updated_by": updated_by},
    )
    _future_dual_write_placeholder(
        "upsert_progress",
        {
            "unit_id": unit_id,
            "task_id": task_id,
            "value": value,
            "updated_by": updated_by,
        },
    )
