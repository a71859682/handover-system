"""Public inactive registration. No session identity or authorization is issued."""

import hmac
import secrets
import sqlite3

from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from services import vendor_registration_service as service


def register_vendor_registration(app, *, db_path, core_state, registry_schema, settings):
    blueprint = Blueprint("vendor_registration", __name__)

    def render(*, error=None, status=200, values=None, success=None):
        response = app.make_response((render_template("vendor_register.html", settings=settings,
            error=error, values=values or {}, success=success, csrf_token=session.get("vr4_csrf", "")), status))
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @blueprint.before_request
    def boundary():
        # Even incomplete/stale identity markers must not be converted or cleared.
        markers = {"user_id", "username", "role", "identity_type", "vendor_account_id", "vendor_username", "vendor_name"}
        if markers.intersection(session):
            abort(403)
        request.max_content_length = 16 * 1024
        request.max_form_memory_size = 16 * 1024
        request.max_form_parts = 6

    @blueprint.errorhandler(RequestEntityTooLarge)
    def too_large(error):
        return render(error="表單內容過大，請縮短後重新填寫", status=413)

    @blueprint.route("/vendor/register", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            if request.args:
                return render(error="此頁不接受查詢參數", status=400)
            if "vr4_csrf" not in session:
                session["vr4_csrf"] = secrets.token_urlsafe(32)
            return render()
        values = {key: request.form.get(key, "") for key in ("company_name", "tax_id", "username")}
        posted = request.form.getlist("csrf_token")
        token = session.get("vr4_csrf")
        if (not isinstance(token, str) or not token.isascii() or len(posted) != 1 or
                not posted[0].isascii() or not hmac.compare_digest(token, posted[0])):
            return render(error="申請驗證已失效，請重新載入表單", status=403, values=values)
        conn = None
        try:
            fields = service.FIELDS | {"csrf_token"}
            if request.args or request.files or set(request.form) != fields or any(len(request.form.getlist(k)) != 1 for k in fields):
                raise service.RegistrationError("表單欄位缺少、重複或不支援，未建立帳號")
            submitted = {key: request.form[key] for key in service.FIELDS}
            service.validate(submitted)
            # mode=rw requires an existing DB; a public request cannot bootstrap it.
            conn = sqlite3.connect(db_path().resolve().as_uri() + "?mode=rw", uri=True, timeout=5)
            conn.execute("PRAGMA foreign_keys=ON")
            if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise service.PrerequisiteError("無法啟用外鍵")
            conn.execute("BEGIN IMMEDIATE")
            receipt = service.register(conn, submitted, core_state=core_state, registry_schema=registry_schema)
            conn.commit()
            session["vr4_receipt"] = receipt
            session["vr4_csrf"] = secrets.token_urlsafe(32)
            return redirect(url_for("vendor_registration.success"), 303)
        except service.PrerequisiteError:
            return render(error="註冊資料前提不足或不相容，請聯絡管理者；本次未建立帳號", status=503, values=values)
        except service.RegistrationError as exc:
            return render(error=str(exc), status=400, values=values)
        except sqlite3.Error:
            # Do not log request values, credentials, hashes or SQLite payloads.
            return render(error="資料庫忙碌或保存失敗；本次未建立帳號，請稍後重新填寫", status=503, values=values)
        finally:
            if conn is not None:
                if conn.in_transaction:
                    conn.rollback()
                conn.close()

    @blueprint.get("/vendor/register/success")
    def success():
        if request.args:
            abort(400)
        receipt = session.get("vr4_receipt")
        if not isinstance(receipt, dict) or set(receipt) != {"username", "company_name", "tax_id"}:
            return redirect(url_for("vendor_registration.index"), 303)
        return render(success=receipt)

    app.register_blueprint(blueprint)
