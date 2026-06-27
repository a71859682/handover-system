from __future__ import annotations

import sqlite3


def _app_state():
    import app

    return app


def available_sheets(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sheets ORDER BY sort_order, id").fetchall()


def resolve_sheet_id(conn: sqlite3.Connection, sheet_id: int | None = None) -> int:
    app = _app_state()

    if sheet_id:
        row = conn.execute("SELECT id FROM sheets WHERE id = ?", (sheet_id,)).fetchone()
        if row:
            return row["id"]
    row = conn.execute("SELECT id FROM sheets ORDER BY sort_order, id LIMIT 1").fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO sheets (name, sort_order) VALUES (?, ?)", (app.get_setting(conn, "tab_title"), 1))
    return cur.lastrowid


def extra_done(field: dict | sqlite3.Row, extra: dict) -> bool:
    app = _app_state()
    done_value = app.DONE_VALUE

    field_key = field["field_key"]
    if field_key == "initial_check":
        return bool(extra.get("recheck_1")) or bool(extra.get("recheck_2")) or extra.get("handover") == done_value
    if field_key == "recheck_1":
        return bool(extra.get("recheck_2")) or extra.get("handover") == done_value
    if field_key == "recheck_2":
        return bool(extra.get("recheck_2")) or extra.get("handover") == done_value
    if field_key == "handover":
        return extra.get("handover") == done_value
    if field["field_type"] == "status":
        return extra.get(field_key) == done_value
    return bool(extra.get(field_key))


def load_grid(sheet_id: int | None = None) -> dict:
    app = _app_state()
    working_value = app.WORKING_VALUE
    done_value = app.DONE_VALUE

    with app.db() as conn:
        current_sheet_id = resolve_sheet_id(conn, sheet_id)
        settings = app.get_settings(conn)
        sheets = available_sheets(conn)
        current_sheet = conn.execute("SELECT * FROM sheets WHERE id = ?", (current_sheet_id,)).fetchone()
        tasks = conn.execute("SELECT * FROM tasks WHERE sheet_id = ? ORDER BY col_index", (current_sheet_id,)).fetchall()
        floors = conn.execute("SELECT * FROM floors WHERE sheet_id = ? ORDER BY sort_order", (current_sheet_id,)).fetchall()
        units_by_floor = {
            floor["id"]: conn.execute(
                "SELECT * FROM units WHERE floor_id = ? ORDER BY sort_order", (floor["id"],)
            ).fetchall()
            for floor in floors
        }
        progress_rows = conn.execute("SELECT unit_id, task_id, value FROM progress").fetchall()
        extra_rows = conn.execute("SELECT * FROM unit_extra").fetchall()
        extra_fields = conn.execute(
            "SELECT * FROM extra_fields WHERE sheet_id = ? AND active = 1 ORDER BY sort_order, id",
            (current_sheet_id,),
        ).fetchall()
        extra_value_rows = conn.execute(
            """
            SELECT v.unit_id, v.field_key, v.value
            FROM unit_extra_values v
            JOIN units u ON u.id = v.unit_id
            JOIN floors f ON f.id = u.floor_id
            WHERE f.sheet_id = ?
            """,
            (current_sheet_id,),
        ).fetchall()

    progress = {(row["unit_id"], row["task_id"]): row["value"] for row in progress_rows}
    extras = {row["unit_id"]: dict(row) for row in extra_rows}
    for row in extra_value_rows:
        extras.setdefault(row["unit_id"], {})[row["field_key"]] = row["value"]
    floor_rows = []
    summary = {task["id"]: {"done": 0, "total": 0} for task in tasks}
    extra_summary = {field["field_key"]: {"done": 0, "total": 0} for field in extra_fields}

    for floor in floors:
        units = units_by_floor[floor["id"]]
        parent_status = {}
        for task in tasks:
            values = [progress.get((unit["id"], task["id"]), working_value) for unit in units]
            done_count = sum(1 for value in values if value == done_value)
            parent_status[task["id"]] = done_value if units and done_count == len(units) else working_value
            summary[task["id"]]["done"] += done_count
            summary[task["id"]]["total"] += len(units)
        for unit in units:
            extra = extras.get(unit["id"], {})
            for field in extra_fields:
                field_key = field["field_key"]
                extra_summary[field_key]["done"] += 1 if extra_done(field, extra) else 0
                extra_summary[field_key]["total"] += 1
        floor_rows.append({"floor": floor, "units": units, "parent_status": parent_status})

    return {
        "settings": settings,
        "sheets": sheets,
        "current_sheet": current_sheet,
        "tasks": tasks,
        "extra_fields": extra_fields,
        "floor_rows": floor_rows,
        "progress": progress,
        "extras": extras,
        "summary": summary,
        "extra_summary": extra_summary,
    }


def render_grid_payload(sheet_id: int | None = None) -> dict:
    grid = load_grid(sheet_id)
    floors = []
    for item in grid["floor_rows"]:
        floor = dict(item["floor"])
        units = [dict(unit) for unit in item["units"]]
        floors.append({"floor": floor, "units": units, "parent_status": item["parent_status"]})
    return {
        "settings": grid["settings"],
        "sheets": [dict(sheet) for sheet in grid["sheets"]],
        "current_sheet": dict(grid["current_sheet"]) if grid["current_sheet"] else None,
        "tasks": [dict(task) for task in grid["tasks"]],
        "extra_fields": [dict(field) for field in grid["extra_fields"]],
        "floors": floors,
        "progress": {f"{unit_id}:{task_id}": value for (unit_id, task_id), value in grid["progress"].items()},
        "extras": {str(unit_id): extra for unit_id, extra in grid["extras"].items()},
        "summary": grid["summary"],
        "extra_summary": grid["extra_summary"],
    }
