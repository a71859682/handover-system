from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Mapping

from config import DUAL_WRITE_DRY_RUN


LOGGER = logging.getLogger(__name__)


def _normalize_log_fields(payload: Mapping[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, tuple):
            normalized[key] = list(value)
        else:
            normalized[key] = value
    return normalized


def _log_dual_write_dry_run(
    *,
    operation: str,
    table: str,
    key: Mapping[str, object],
    fields: Mapping[str, object],
) -> None:
    if not DUAL_WRITE_DRY_RUN:
        return

    payload = {
        "operation": operation,
        "table": table,
        "key": _normalize_log_fields(key),
        "fields": _normalize_log_fields(fields),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
    }
    LOGGER.info("DUAL_WRITE_DRY_RUN %s", json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _future_dual_write_placeholder(operation: str, payload: Mapping[str, object]) -> None:
    # Reserved for the future dual-write rollout. This version intentionally
    # keeps SQLite as the only write target.
    _ = (operation, payload)


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
) -> None:
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        (username, display_name, password_hash, role),
    )
    created_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
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
    sheet_id = cur.lastrowid
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
