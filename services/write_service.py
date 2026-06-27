from __future__ import annotations

import sqlite3
from typing import Mapping


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
    _future_dual_write_placeholder(
        "create_user",
        {
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
    _future_dual_write_placeholder(
        "create_builtin_extra_fields",
        {"sheet_id": sheet_id, "field_keys": tuple(builtin_fields)},
    )


def update_sheet_name_sqlite(conn: sqlite3.Connection, *, sheet_id: int, name: str) -> None:
    conn.execute("UPDATE sheets SET name = ? WHERE id = ?", (name, sheet_id))
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
    _future_dual_write_placeholder(
        "upsert_progress",
        {
            "unit_id": unit_id,
            "task_id": task_id,
            "value": value,
            "updated_by": updated_by,
        },
    )
