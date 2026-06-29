from __future__ import annotations

from flask import Blueprint, redirect, render_template, session, url_for

from routes.auth import login_required


sheet_bp = Blueprint("sheet", __name__)


def _app_state():
    import app

    return app


@sheet_bp.route("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    return redirect(url_for("sheet"))


@sheet_bp.route("/sheet")
@sheet_bp.route("/sheet/<int:sheet_id>")
@login_required
def sheet(sheet_id: int | None = None):
    app = _app_state()

    with app.db() as conn:
        resolved = app.resolve_sheet_id(conn, sheet_id)
    session["sheet_id"] = resolved
    grid = app.load_grid(resolved)
    return render_template(
        "sheet.html",
        grid=grid,
        settings=grid["settings"],
        done_value=app.DONE_VALUE,
        working_value=app.WORKING_VALUE,
    )
