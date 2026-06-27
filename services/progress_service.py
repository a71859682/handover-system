from __future__ import annotations

from werkzeug.security import check_password_hash


def _app_state():
    import app

    return app


def _sheet_id_for_unit(unit_id: int, fallback_sheet_id: int | None = None) -> int | None:
    app = _app_state()
    sheet_row = app.query_one(
        "SELECT f.sheet_id FROM units u JOIN floors f ON f.id = u.floor_id WHERE u.id = ?",
        (unit_id,),
    )
    return sheet_row["sheet_id"] if sheet_row else fallback_sheet_id


def update_progress(unit_id, task_id, value, user_id, fallback_sheet_id=None):
    app = _app_state()

    if value not in (app.DONE_VALUE, app.WORKING_VALUE):
        return {"ok": False, "message": "Value must be O or X."}

    with app.db() as conn:
        conn.execute(
            """
            INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(unit_id, task_id) DO UPDATE SET
                value = excluded.value,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (unit_id, task_id, value, user_id),
        )

    return {"ok": True, "sheet_id": _sheet_id_for_unit(unit_id, fallback_sheet_id)}


def update_unit_extra(unit_id, field, value, user_id, fallback_sheet_id=None):
    app = _app_state()

    with app.db() as conn:
        field_row = conn.execute(
            """
            SELECT ef.*
            FROM extra_fields ef
            JOIN floors f ON f.sheet_id = ef.sheet_id
            JOIN units u ON u.floor_id = f.id
            WHERE u.id = ? AND ef.field_key = ? AND ef.active = 1
            """,
            (unit_id, field),
        ).fetchone()
        if not field_row:
            return {"ok": False, "message": "Field not found."}
        if field_row["field_type"] == "status" and value not in (app.DONE_VALUE, app.WORKING_VALUE):
            return {"ok": False, "message": "Status value must be O or X."}

        conn.execute(
            "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
            (unit_id, app.WORKING_VALUE),
        )
        if field in app.EXTRA_FIELDS:
            conn.execute(
                f"""
                UPDATE unit_extra
                SET {field} = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE unit_id = ?
                """,
                (value, user_id, unit_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(unit_id, field_key) DO UPDATE SET
                    value = excluded.value,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (unit_id, field, value, user_id),
            )

    return {"ok": True, "sheet_id": _sheet_id_for_unit(unit_id, fallback_sheet_id)}


def reset_sheet(sheet_id, user_id, password):
    app = _app_state()

    user = app.get_user_by_id(user_id)
    if not user or not check_password_hash(user["password_hash"], password):
        return {"ok": False, "message": "Password verification failed."}

    with app.db() as conn:
        resolved_sheet_id = app.resolve_sheet_id(conn, sheet_id)
        conn.execute(
            """
            UPDATE progress
            SET value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id IN (SELECT id FROM tasks WHERE sheet_id = ?)
            """,
            (app.WORKING_VALUE, user_id, resolved_sheet_id),
        )
        conn.execute(
            """
            UPDATE unit_extra
            SET initial_check = '',
                recheck_1 = '',
                recheck_2 = '',
                handover = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE unit_id IN (
                SELECT u.id
                FROM units u
                JOIN floors f ON f.id = u.floor_id
                WHERE f.sheet_id = ?
            )
            """,
            (app.WORKING_VALUE, user_id, resolved_sheet_id),
        )
        conn.execute(
            """
            DELETE FROM unit_extra_values
            WHERE unit_id IN (
                SELECT u.id
                FROM units u
                JOIN floors f ON f.id = u.floor_id
                WHERE f.sheet_id = ?
            )
            AND field_key IN (SELECT field_key FROM extra_fields WHERE sheet_id = ?)
            """,
            (resolved_sheet_id, resolved_sheet_id),
        )

    return {"ok": True, "sheet_id": resolved_sheet_id}
