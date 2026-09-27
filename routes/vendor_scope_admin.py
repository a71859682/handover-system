"""Actual Flask pending-scope controller; current DB admin, CSRF and edit CAS."""

import hmac
import re
import secrets
import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer

from services import vendor_access_service as access
from services import vendor_roster_service as roster
from services import vendor_scope_admin_service as service


def _one(form, key):
    values = form.getlist(key)
    if len(values) != 1:
        raise service.AdminError("表單欄位缺少或重複，未保存：" + key)
    return values[0]


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,17}", value):
        raise service.AdminError("ID 必須是正整數")
    return int(value)


def _parse_scopes(form, edit):
    ids = [str(site["id"]) for site in edit["sites"]]
    rows = form.getlist("site_row")
    if _one(form, "scope_set_complete") != "1" or sorted(rows) != sorted(ids):
        raise service.AdminError("完整工地集合缺少或重複，未執行清空")
    allowed = {"csrf_token", "snapshot", "vendor_id", "account_id", "reason", "confirm_membership",
               "scope_set_complete", "site_row"}
    scopes = []
    for sid in ids:
        allowed.update({"enabled." + sid, "mode." + sid, "tasks_present." + sid, "task." + sid})
        enabled = form.getlist("enabled." + sid)
        if enabled not in ([], ["1"]):
            raise service.AdminError("工地勾選格式錯誤")
        mode = _one(form, "mode." + sid)
        if _one(form, "tasks_present." + sid) != "1" or mode not in ("ALL", "SELECTED"):
            raise service.AdminError("工項欄位缺少或模式錯誤")
        tasks = [_id(value) for value in form.getlist("task." + sid)]
        if len(tasks) != len(set(tasks)) or (tasks and (not enabled or mode == "ALL")):
            raise service.AdminError("未勾工地或 ALL 夾帶工項／重複 ID，未保存")
        if enabled:
            scopes.append({"site_id": int(sid), "mode": mode, "task_ids": tasks})
    if set(form) - allowed:
        raise service.AdminError("表單含有不支援的欄位，未保存")
    confirm = form.getlist("confirm_membership")
    if confirm not in ([], ["1"]):
        raise service.AdminError("歸屬確認格式錯誤")
    return scopes, bool(confirm)


def register_vendor_scope_admin(app, *, db_path, core_state, session_type, settings):
    blueprint = Blueprint("vendor_scope_admin", __name__)

    def signer():
        return URLSafeTimedSerializer(app.secret_key, salt="004f-vr3-pending-editor-v1")

    def render(data=None, edit=None, token=None, error=None, status=200, stale=False):
        response = app.make_response((render_template("vendor_scope_admin.html", settings=settings,
            catalog=data, edit=edit, snapshot_token=token, error=error, stale=stale,
            submitted=request.form if request.method == "POST" else None,
            csrf_token=session.get("vr3_csrf", "")), status))
        response.headers["Cache-Control"] = "no-store"
        return response

    @blueprint.route("/admin/vendor-scopes", methods=["GET", "POST"])
    def index():
        try:
            if session_type() != "internal" or type(session.get("user_id")) is not int or session["user_id"] <= 0:
                abort(403)
        except LookupError:
            abort(403)
        if request.method == "POST":
            csrf = session.get("vr3_csrf")
            posted = request.form.getlist("csrf_token")
            if (not isinstance(csrf, str) or not csrf.isascii() or len(posted) != 1 or
                    not posted[0].isascii() or not hmac.compare_digest(csrf, posted[0])):
                abort(403)
        conn = None
        data = edit = token = None
        try:
            # URI mode prevents accidental creation of an empty production DB.
            mode = "ro" if request.method == "GET" else "rw"
            conn = sqlite3.connect(db_path().resolve().as_uri() + "?mode=" + mode, uri=True, timeout=5)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise service.PrerequisiteError("無法啟用外鍵")
            if request.method == "GET":
                conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN" if request.method == "GET" else "BEGIN IMMEDIATE")
            row = conn.execute("SELECT role FROM main.users WHERE id=?", (session["user_id"],)).fetchone()
            if row is None or row[0] != "admin":
                abort(403)
            actor = access.InternalActor(session["user_id"])
            if request.method == "GET":
                data = service.catalog(conn, actor=actor, core_state=core_state)
                if "vr3_csrf" not in session:
                    session["vr3_csrf"] = secrets.token_urlsafe(32)
                if request.args:
                    if set(request.args) != {"vendor_id", "account_id"}:
                        raise service.AdminError("請完整選擇廠商與帳號")
                    vendor_id = _one(request.args, "vendor_id")
                    account_id = _id(_one(request.args, "account_id"))
                    edit = service.editor(conn, actor=actor, vendor_id=vendor_id, account_id=account_id,
                                          core_state=core_state)
                    token = signer().dumps({"actor": actor.user_id, "csrf": session["vr3_csrf"],
                        "vendor": vendor_id, "account": account_id, "fingerprint": edit["fingerprint"]})
                return render(data, edit, token)

            token = _one(request.form, "snapshot")
            try:
                bound = signer().loads(token, max_age=1800)
            except BadSignature as exc:
                raise access.ScopeConflict("編輯快照無效或超過 30 分鐘，請重新載入") from exc
            if not isinstance(bound, dict) or bound.get("actor") != actor.user_id or bound.get("csrf") != session["vr3_csrf"]:
                abort(403)
            if _one(request.form, "vendor_id") != bound["vendor"] or _id(_one(request.form, "account_id")) != bound["account"]:
                raise service.AdminError("目標帳號／廠商與編輯快照不一致")
            edit = service.editor(conn, actor=actor, vendor_id=bound["vendor"], account_id=bound["account"],
                                  core_state=core_state)
            request_id = service.fingerprint(sorted((key, request.form.getlist(key)) for key in request.form))
            receipt = session.get("vr3_receipt", {})
            if (receipt.get("request") == request_id and receipt.get("actor") == actor.user_id and
                    receipt.get("after") == edit["fingerprint"] and not edit["blocked"]):
                conn.rollback()
                flash("相同請求已保存；待開通，尚未生效。", "success")
                return redirect(url_for("vendor_scope_admin.index", vendor_id=bound["vendor"], account_id=bound["account"]), 303)
            # Compare before parsing against today's options: old options must
            # never silently disappear and become a different replacement set.
            if bound["fingerprint"] != edit["fingerprint"]:
                raise access.ScopeConflict("編輯快照已過期，請重新載入並確認全部選項")
            scopes, confirm = _parse_scopes(request.form, edit)
            service.save_pending(conn, actor=actor, vendor_id=bound["vendor"], account_id=bound["account"],
                expected_fingerprint=bound["fingerprint"], scopes=scopes, reason=_one(request.form, "reason"),
                confirm_membership=confirm, core_state=core_state)
            after = service.editor(conn, actor=actor, vendor_id=bound["vendor"], account_id=bound["account"], core_state=core_state)
            conn.commit()
            session["vr3_receipt"] = {"request": request_id, "actor": actor.user_id, "after": after["fingerprint"]}
            flash("設定已保存；待開通，尚未生效。", "success")
            return redirect(url_for("vendor_scope_admin.index", vendor_id=bound["vendor"], account_id=bound["account"]), 303)
        except access.ScopeConflict as exc:
            if conn is not None:
                conn.rollback()
            return render(data, edit, token, str(exc), 409, stale=True)
        except service.PrerequisiteError as exc:
            if conn is not None:
                conn.rollback()
            return render(error=str(exc), status=503)
        except (access.ScopeError, roster.RosterError) as exc:
            if conn is not None:
                conn.rollback()
            return render(data, edit, token, str(exc), 400)
        except sqlite3.Error:
            if conn is not None:
                conn.rollback()
            app.logger.exception("VR3 pending configuration rolled back")
            return render(data, edit, token, "資料庫前提缺少、忙碌或保存失敗；本次未保存，請重新載入。", 503, stale=True)
        finally:
            if conn is not None:
                if conn.in_transaction:
                    conn.rollback()
                conn.close()

    app.register_blueprint(blueprint)
