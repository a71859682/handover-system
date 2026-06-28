from __future__ import annotations

import sqlite3
import uuid

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from routes.auth import admin_required
from services.write_service import (
    create_builtin_extra_fields_sqlite,
    create_sheet_sqlite,
    create_user_sqlite,
    deactivate_extra_field_sqlite,
    update_floor_fields_sqlite,
    update_extra_field_sqlite,
    update_sheet_name_sqlite,
    update_task_fields_sqlite,
    update_unit_name_sqlite,
    update_user_sqlite,
)


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
                        create_user_sqlite(
                            conn,
                            username=username,
                            display_name=display_name,
                            password_hash=generate_password_hash(password),
                            role=role,
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
                        update_user_sqlite(
                            conn,
                            user_id=user_id,
                            username=username,
                            display_name=display_name,
                            role=role,
                            password_hash=generate_password_hash(password) if password else None,
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
                name = request.form.get("new_sheet_name", "").strip() or "未命名工作表"
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM sheets").fetchone()[0]
                sheet_id = create_sheet_sqlite(conn, name=name, sort_order=next_order)
                create_builtin_extra_fields_sqlite(
                    conn,
                    sheet_id=sheet_id,
                    builtin_fields=app.BUILTIN_EXTRA_FIELDS,
                )
                flash("工作表已新增。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action == "delete_sheet":
                count = conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0]
                if count <= 1:
                    flash("至少要保留一個工作表。", "error")
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
                flash("工作表已刪除。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=next_sheet))
            if action == "add_task":
                next_col = conn.execute("SELECT COALESCE(MAX(col_index), 3) + 1 FROM tasks").fetchone()[0]
                cur = conn.execute(
                    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
                    (sheet_id, next_col, request.form.get("new_task_vendor", ""), request.form.get("new_task_location", ""), request.form.get("new_task_name", "新任務") or "新任務"),
                )
                for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):
                    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)", (unit["id"], cur.lastrowid, app.WORKING_VALUE))
                flash("任務已新增。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("delete_task:"):
                task_id = int(action.split(":", 1)[1])
                conn.execute("DELETE FROM progress WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM tasks WHERE id = ? AND sheet_id = ?", (task_id, sheet_id))
                flash("任務已刪除。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action == "add_extra_field":
                field_name = request.form.get("new_extra_name", "").strip() or "新欄位"
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
                deactivate_extra_field_sqlite(conn, field_id=field_id, sheet_id=sheet_id)
                flash("欄位已停用。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action == "add_floor":
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM floors").fetchone()[0]
                conn.execute(
                    "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 0)",
                    (sheet_id, next_order, request.form.get("new_floor_name", "新樓層") or "新樓層", request.form.get("new_floor_block", "")),
                )
                flash("樓層已新增。", "success")
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
                flash("樓層已刪除。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))
            if action.startswith("add_unit:"):
                floor_id = int(action.split(":", 1)[1])
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM units WHERE floor_id = ?", (floor_id,)).fetchone()[0]
                cur = conn.execute(
                    "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
                    (floor_id, next_order, request.form.get(f"new_unit_name_{floor_id}", "新戶別") or "新戶別"),
                )
                for task in conn.execute("SELECT id FROM tasks WHERE sheet_id = ?", (sheet_id,)):
                    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)", (cur.lastrowid, task["id"], app.WORKING_VALUE))
                conn.execute("INSERT INTO unit_extra (unit_id, handover) VALUES (?, ?)", (cur.lastrowid, app.WORKING_VALUE))
                conn.execute("UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = ?) WHERE id = ?", (floor_id, floor_id))
                flash("戶別已新增。", "success")
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
                flash("戶別已刪除。", "success")
                return redirect(url_for("admin.table_admin", sheet_id=sheet_id))

            update_sheet_name_sqlite(
                conn,
                sheet_id=sheet_id,
                name=request.form.get("sheet_name", "").strip() or "未命名工作表",
            )
            for key in app.DEFAULT_SETTINGS:
                if key in request.form:
                    app.set_setting(conn, key, request.form.get(key, "").strip())
            for task in conn.execute("SELECT id FROM tasks WHERE sheet_id = ?", (sheet_id,)):
                task_id = task["id"]
                update_task_fields_sqlite(
                    conn,
                    task_id,
                    vendor=request.form.get(f"task_vendor_{task_id}", "").strip(),
                    location=request.form.get(f"task_location_{task_id}", "").strip(),
                    name=request.form.get(f"task_name_{task_id}", "").strip(),
                )
            for field in conn.execute("SELECT id FROM extra_fields WHERE sheet_id = ? AND active = 1", (sheet_id,)):
                field_id = field["id"]
                field_type = request.form.get(f"extra_type_{field_id}", "date")
                if field_type not in app.EXTRA_FIELD_TYPES:
                    field_type = "date"
                update_extra_field_sqlite(
                    conn,
                    field_id=field_id,
                    sheet_id=sheet_id,
                    name=request.form.get(f"extra_name_{field_id}", "").strip() or "未命名欄位",
                    field_type=field_type,
                )
            for floor in conn.execute("SELECT id FROM floors WHERE sheet_id = ?", (sheet_id,)):
                floor_id = floor["id"]
                update_floor_fields_sqlite(
                    conn,
                    floor_id=floor_id,
                    name=request.form.get(f"floor_name_{floor_id}", "").strip(),
                    block_name=request.form.get(f"floor_block_{floor_id}", "").strip(),
                )
            for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):
                unit_id = unit["id"]
                update_unit_name_sqlite(
                    conn,
                    unit_id=unit_id,
                    name=request.form.get(f"unit_name_{unit_id}", "").strip(),
                )
            flash("設定已更新。", "success")
            return redirect(url_for("admin.table_admin", sheet_id=sheet_id))

        settings = app.get_settings(conn)
        sheets = app.available_sheets(conn)
        current_sheet = app.get_sheet(sheet_id)
        tasks = app.list_tasks_for_sheet(sheet_id)
        extra_fields = conn.execute("SELECT * FROM extra_fields WHERE sheet_id = ? AND active = 1 ORDER BY sort_order, id", (sheet_id,)).fetchall()
        floors = app.list_floors_for_sheet(sheet_id)
        units = {floor["id"]: app.list_units_for_floor(floor["id"]) for floor in floors}
    return render_template("table_admin.html", settings=settings, sheets=sheets, current_sheet=current_sheet, tasks=tasks, extra_fields=extra_fields, floors=floors, units=units)
