from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


auth_bp = Blueprint("auth", __name__)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("sheet.sheet"))
        return fn(*args, **kwargs)

    return wrapper


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from app import get_user_by_username, query_settings

    settings = query_settings()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user["display_name"] or user["username"]
            session["role"] = user["role"]
            return redirect(url_for("sheet.sheet"))
        flash("Invalid username or password.", "error")
    return render_template("login.html", settings=settings)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
