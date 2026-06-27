from __future__ import annotations

import sqlite3
import uuid

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from routes.auth import admin_required


admin_bp = Blueprint("admin", __name__)


def _app_state():
    import app

    return app


@admin_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def users():
    app = _app_state()

    if request.method == "POST":
        action = request.form.get("action", "create_user")
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip() or username
        password = request.form.get("password", "")
        role = request.form.get("role", "member")

        if role not in ("member", "admin"):
            flash("\u89d2\u8272\u8a2d\u5b9a\u932f\u8aa4\u3002", "error")
        elif action == "create_user":
            if not username or not password:
                flash("\u8acb\u8f38\u5165\u5e33\u865f\u8207\u5bc6\u78bc\u3002", "error")
            else:
                try:
                    with app.db() as conn:
                        conn.execute(
                            "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
                            (username, display_name, generate_password_hash(password), role),
                        )
                    flash("\u6210\u54e1\u5df2\u65b0\u589e\u3002", "success")
                except (sqlite3.IntegrityError, app.IntegrityError):
                    flash("\u5e33\u865f\u5df2\u5b58\u5728\u3002", "error")
        elif action.startswith("update_user:"):
            user_id = int(action.split(":", 1)[1])
            if not username:
                flash("\u5e33\u865f\u4e0d\u53ef\u7a7a\u767d\u3002", "error")
            else:
                try:
                    with app.db() as conn:
                        if password:
                            conn.execute(
                                """
                                UPDATE users
                                SET username = ?, display_name = ?, password_hash = ?, role = ?
                                WHERE id = ?
                                """,
                                (username, display_name, generate_password_hash(password), role, user_id),
                            )
                        else:
                            conn.execute(
                                "UPDATE users SET username = ?, display_name = ?, role = ? WHERE id = ?",
                                (username, display_name, role, user_id),
                            )
                    if user_id == session.get("user_id"):
                        session["username"] = username
                        session["display_name"] = display_name
                        session["role"] = role
                    flash("\u6210\u54e1\u8cc7\u6599\u5df2\u66f4\u65b0\u3002", "success")
                except (sqlite3.IntegrityError, app.IntegrityError):
                    flash("\u5e33\u865f\u5df2\u5b58\u5728\u3002", "error")
        else:
            flash("\u64cd\u4f5c\u7121\u6548\u3002", "error")

        return redirect(url_for("admin.users"))

    with app.db() as conn:
        settings = app.get_settings(conn)
    all_users = app.list_users()
    return render_template("users.html", users=all_users, settings=settings)


@admin_bp.route("/admin/table", methods=["GET", "POST"])
@admin_required
def table_admin():
    app = _app_state()

    with app.db() as conn:
        sheet_id = app.resolve_sheet_id(conn, request.values.get("sheet_id", type=int) or session.get("sheet_id"))
        session["sheet_id"] = sheet_id
        if request.method == "POST":
            actions = request.form.getlist("action")
            action = actions[-1] if actions else "save"
            if action == "create_sheet":
                name = request.form.get("new_sheet_name", "").strip() or "????"
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM sheets").fetchone()[0]
                cur = conn.execute("INSERT INTO sheets (name, sort_order) VALUES (?, ?)", (name, next_order))
                for field_key, field in app.BUILTIN_EXTRA_FIELDS.items():
                    conn.execute(
                        """
                        INSERT INTO extra_fields
                        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
                        VALUES (?, ?, ?, ?, ?, 1, 1)
                        """,
                        (cur.lastrowid, field_key, field["name"], field["type"], field["sort_order"]),
                    )
                flash("???????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=cur.lastrowid))
            if action == "delete_sheet":
                count = conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0]
                if count <= 1:
                    flash("????????????", "error")
                    return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
                unit_ids = [row["id"] for row in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,))]
                if unit_ids:
                    placeholders = ",".join("?" for _ in unit_ids)
                    conn.execute(f"DELETE FROM progress WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra_values WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM units WHERE id IN ({placeholders})", unit_ids)
                conn.execute("DELETE FROM tasks WHERE sheet_id = ?", (sheet_id,))
                conn.execute("DELETE FROM floors WHERE sheet_id = ?", (sheet_id,))
                conn.execute("DELETE FROM unit_extra_values WHERE field_key IN (SELECT field_key FROM extra_fields WHERE sheet_id = ?)", (sheet_id,))
                conn.execute("DELETE FROM extra_fields WHERE sheet_id = ?", (sheet_id,))
                conn.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))
                next_sheet = app.resolve_sheet_id(conn)
                flash("???????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=next_sheet))
            if action == "add_task":
                next_col = conn.execute("SELECT COALESCE(MAX(col_index), 3) + 1 FROM tasks").fetchone()[0]
                cur = conn.execute(
                    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
                    (sheet_id, next_col, request.form.get("new_task_vendor", ""), request.form.get("new_task_location", ""), request.form.get("new_task_name", "???") or "???"),
                )
                for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):
                    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)", (unit["id"], cur.lastrowid, app.WORKING_VALUE))
                flash("??????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("delete_task:"):
                task_id = int(action.split(":", 1)[1])
                conn.execute("DELETE FROM progress WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM tasks WHERE id = ? AND sheet_id = ?", (task_id, sheet_id))
                flash("??????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action == "add_extra_field":
                field_name = request.form.get("new_extra_name", "").strip() or "?啣?甈?"
                field_type = request.form.get("new_extra_type", "date")
                if field_type not in app.EXTRA_FIELD_TYPES:
                    field_type = "date"
                next_order = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM extra_fields WHERE sheet_id = ?",
                    (sheet_id,),
                ).fetchone()[0]
                conn.execute(
                    """
                    INSERT INTO extra_fields
                    (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
                    VALUES (?, ?, ?, ?, ?, 0, 1)
                    """,
                    (sheet_id, f"custom_{uuid.uuid4().hex[:12]}", field_name, field_type, next_order),
                )
                flash("欄位已新增。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("delete_extra_field:"):
                field_id = int(action.split(":", 1)[1])
                conn.execute("UPDATE extra_fields SET active = 0 WHERE id = ? AND sheet_id = ?", (field_id, sheet_id))
                flash("欄位已刪除。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action == "add_floor":
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM floors").fetchone()[0]
                conn.execute(
                    "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 0)",
                    (sheet_id, next_order, request.form.get("new_floor_name", "???") or "???", request.form.get("new_floor_block", "")),
                )
                flash("??????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("delete_floor:"):
                floor_id = int(action.split(":", 1)[1])
                unit_ids = [row["id"] for row in conn.execute("SELECT id FROM units WHERE floor_id = ?", (floor_id,))]
                if unit_ids:
                    placeholders = ",".join("?" for _ in unit_ids)
                    conn.execute(f"DELETE FROM progress WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra_values WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM units WHERE id IN ({placeholders})", unit_ids)
                conn.execute("DELETE FROM floors WHERE id = ? AND sheet_id = ?", (floor_id, sheet_id))
                flash("??????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("add_unit:"):
                floor_id = int(action.split(":", 1)[1])
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM units WHERE floor_id = ?", (floor_id,)).fetchone()[0]
                cur = conn.execute(
                    "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
                    (floor_id, next_order, request.form.get(f"new_unit_name_{floor_id}", "???") or "???"),
                )
                for task in conn.execute("SELECT id FROM tasks WHERE sheet_id = ?", (sheet_id,)):
                    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)", (cur.lastrowid, task["id"], app.WORKING_VALUE))
                conn.execute("INSERT INTO unit_extra (unit_id, handover) VALUES (?, ?)", (cur.lastrowid, app.WORKING_VALUE))
                conn.execute("UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = ?) WHERE id = ?", (floor_id, floor_id))
                flash("??????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("delete_unit:"):
                unit_id = int(action.split(":", 1)[1])
                floor = conn.execute("SELECT floor_id FROM units WHERE id = ?", (unit_id,)).fetchone()
                conn.execute("DELETE FROM progress WHERE unit_id = ?", (unit_id,))
                conn.execute("DELETE FROM unit_extra WHERE unit_id = ?", (unit_id,))
                conn.execute("DELETE FROM unit_extra_values WHERE unit_id = ?", (unit_id,))
                conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))
                if floor:
                    conn.execute("UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = ?) WHERE id = ?", (floor["floor_id"], floor["floor_id"]))
                flash("??????", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))

            conn.execute("UPDATE sheets SET name = ? WHERE id = ?", (request.form.get("sheet_name", "").strip() or "???", sheet_id))
            for key in app.DEFAULT_SETTINGS:
                if key in request.form:
                    app.set_setting(conn, key, request.form.get(key, "").strip())
            for task in conn.execute("SELECT id FROM tasks WHERE sheet_id = ?", (sheet_id,)):
                task_id = task["id"]
                conn.execute("UPDATE tasks SET vendor = ?, location = ?, name = ? WHERE id = ?", (request.form.get(f"task_vendor_{task_id}", "").strip(), request.form.get(f"task_location_{task_id}", "").strip(), request.form.get(f"task_name_{task_id}", "").strip(), task_id))
            for field in conn.execute("SELECT id FROM extra_fields WHERE sheet_id = ? AND active = 1", (sheet_id,)):
                field_id = field["id"]
                field_type = request.form.get(f"extra_type_{field_id}", "date")
                if field_type not in app.EXTRA_FIELD_TYPES:
                    field_type = "date"
                conn.execute(
                    "UPDATE extra_fields SET name = ?, field_type = ? WHERE id = ? AND sheet_id = ?",
                    (request.form.get(f"extra_name_{field_id}", "").strip() or "甈?", field_type, field_id, sheet_id),
                )
            for floor in conn.execute("SELECT id FROM floors WHERE sheet_id = ?", (sheet_id,)):
                floor_id = floor["id"]
                conn.execute("UPDATE floors SET name = ?, block_name = ? WHERE id = ?", (request.form.get(f"floor_name_{floor_id}", "").strip(), request.form.get(f"floor_block_{floor_id}", "").strip(), floor_id))
            for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):
                unit_id = unit["id"]
                conn.execute("UPDATE units SET name = ? WHERE id = ?", (request.form.get(f"unit_name_{unit_id}", "").strip(), unit_id))
            flash("????????", "success")
            return redirect(url_for("admin.table_admin", sheet_id=sheet_id))

        settings = app.get_settings(conn)
        sheets = app.available_sheets(conn)
        current_sheet = conn.execute("SELECT * FROM sheets WHERE id = ?", (sheet_id,)).fetchone()
        tasks = conn.execute("SELECT * FROM tasks WHERE sheet_id = ? ORDER BY col_index", (sheet_id,)).fetchall()
        extra_fields = conn.execute("SELECT * FROM extra_fields WHERE sheet_id = ? AND active = 1 ORDER BY sort_order, id", (sheet_id,)).fetchall()
        floors = conn.execute("SELECT * FROM floors WHERE sheet_id = ? ORDER BY sort_order", (sheet_id,)).fetchall()
        units = {floor["id"]: conn.execute("SELECT * FROM units WHERE floor_id = ? ORDER BY sort_order", (floor["id"],)).fetchall() for floor in floors}
    return render_template("table_admin.html", settings=settings, sheets=sheets, current_sheet=current_sheet, tasks=tasks, extra_fields=extra_fields, floors=floors, units=units)
