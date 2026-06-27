from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from routes.auth import admin_required, login_required


api_bp = Blueprint("api", __name__)


def _app_state():
    import app

    return app


@api_bp.route("/api/grid")
@login_required
def api_grid():
    app = _app_state()

    sheet_id = request.args.get("sheet_id", type=int) or session.get("sheet_id")
    return jsonify(app.render_grid_payload(sheet_id))


@api_bp.route("/api/progress", methods=["POST"])
@login_required
def api_progress():
    app = _app_state()

    data = request.get_json(force=True)
    result = app.update_progress(
        unit_id=int(data.get("unit_id")),
        task_id=int(data.get("task_id")),
        value=data.get("value", app.WORKING_VALUE),
        user_id=session["user_id"],
        fallback_sheet_id=session.get("sheet_id"),
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify({"ok": True, "grid": app.render_grid_payload(result["sheet_id"])})


@api_bp.route("/api/unit-extra", methods=["POST"])
@login_required
def api_unit_extra():
    app = _app_state()

    data = request.get_json(force=True)
    result = app.update_unit_extra(
        unit_id=int(data.get("unit_id")),
        field=data.get("field", ""),
        value=data.get("value", ""),
        user_id=session["user_id"],
        fallback_sheet_id=session.get("sheet_id"),
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify({"ok": True, "grid": app.render_grid_payload(result["sheet_id"])})


@api_bp.route("/api/reset-sheet", methods=["POST"])
@admin_required
def api_reset_sheet():
    app = _app_state()

    data = request.get_json(force=True)
    result = app.reset_sheet(
        sheet_id=data.get("sheet_id") or session.get("sheet_id"),
        user_id=session["user_id"],
        password=data.get("password", ""),
    )
    if not result["ok"]:
        return jsonify(result), 403
    return jsonify({"ok": True, "grid": app.render_grid_payload(result["sheet_id"])})
