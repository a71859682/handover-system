"""Gunicorn entry: validate and identify the isolated DB before importing app."""

import hashlib
import json
import uuid

from .fixture import (BASELINE, IDENTITY, finish_fixture, install_storage_guard,
                      prepare, readonly, validate_environment, verify_identity)

contract = validate_environment()
install_storage_guard(contract)
with prepare(contract) as (fresh, fixture_instance):
    import app as product
    finish_fixture(product, contract, fresh)

from flask import abort, jsonify, request, session
from services import vendor_access_service as access
from services import vendor_scope_admin_service as scope_admin

app = product.app
BOOT_ID = str(uuid.uuid4())
VERSION = dict(preview=IDENTITY, baseline_commit=BASELINE, render_git_commit=contract.commit,
               boot_id=BOOT_ID, fixture_instance=fixture_instance, synthetic=True)
# This entry exposes only the preview flow. Original handlers/auth/CSRF are intact.
# In particular no original admin/users, admin/table or reset endpoint is exposed.
ALLOWED = {"/", "/login", "/logout", "/vendor/login", "/vendor/logout",
           "/vendor/register", "/vendor/register/success", "/admin/vendor-scopes",
           "/site-selector", "/sheet", "/api/grid", "/preview/version", "/preview/fixture-state"}


@app.context_processor
def preview_template_context():
    # Registered only after preimport isolation and fixture validation succeeded.
    return {"vr4_preview": True}


@app.before_request
def preview_surface():
    sheet_read = (request.method in {"GET", "HEAD"} and
                  request.url_rule is not None and
                  request.url_rule.rule == "/sheet/<int:sheet_id>" and
                  request.endpoint == "sheet")
    if (request.path not in ALLOWED and not sheet_read and
            not request.path.startswith("/static/")):
        abort(404)


@app.get("/preview/version")
def preview_version():
    if request.args:
        abort(400)
    response = jsonify(VERSION)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/preview/fixture-state")
def fixture_state():
    """Fixed, read-only, credential-free projection; no caller SQL/path/filter."""
    if request.args:
        abort(400)
    try:
        if product.resolve_vendor_work_entry_actor_session_type() != "internal":
            abort(403)
    except LookupError:
        abort(403)
    user_id = session.get("user_id")
    if type(user_id) is not int or user_id <= 0:
        abort(403)
    with readonly(contract) as conn:
        conn.execute("BEGIN")
        verify_identity(conn, contract)
        user = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if user is None or user[0] != "admin":
            abort(403)
        actor = access.InternalActor(user_id)
        catalog = scope_admin.catalog(conn, actor=actor, core_state=product._vendor_organization_schema_state)
        state = dict(vendors=[{k: p[k] for k in ("vendor_id", "tax_id", "legal_name", "organization_status")}
                              for p in catalog["profiles"]],
                     accounts=[{k: a[k] for k in ("id", "username", "is_active")}
                               for a in catalog["accounts"]],
                     registrations=list(catalog["registration_info"]["by_account"].values()),
                     memberships=[], sites=[dict(r) for r in conn.execute(
                         "SELECT id,site_name,is_active FROM sites ORDER BY id")])
        for row in conn.execute("SELECT vendor_membership_id,vendor_account_id,vendor_id,membership_status "
                                "FROM vendor_organization_memberships ORDER BY vendor_membership_id"):
            preview = access.preview_scopes(conn, actor=actor, membership_id=row[0])
            state["memberships"].append(dict(row) | {
                "revision": preview["revision"], "configured_scopes": preview["configured_scopes"],
                "configured_task_count": preview["configured_scope"]["task_count"],
                "effective_task_count": preview["effective_scope"]["task_count"]})
        tables = ("vendor_accounts", "vendor_organizations", "vendor_organization_memberships",
                  "vendor_site_assignments", "sheet_vendor_bindings", "vendor_registration_requests",
                  "vr2_site_scopes", "vr2_selected_tasks", "vr2_scope_versions", "vr2_scope_events")
        present = {r[0] for r in conn.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
        state["row_counts"] = {name: conn.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0]
                               if name in present else 0 for name in tables}
        digest = hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    response = jsonify(VERSION | {"state": state, "state_sha256": digest, "readonly": True})
    response.headers["Cache-Control"] = "no-store"
    return response
