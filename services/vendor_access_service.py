"""VR2 member task scopes; no app import, connection creation or runtime wiring.

Only a trusted controller may construct InternalActor from an authenticated
internal identity. Integer IDs from different identity domains are not actors.
Mutations require a caller-owned transaction and enabled foreign keys. Effective
reads require a connection outside any transaction, and own one read snapshot.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import sqlite3
import uuid


class ScopeError(ValueError):
    """Invalid input, identity, connection or schema; no retained service writes."""


class ScopeConflict(ScopeError):
    """The editor's revision or identity generation is no longer current."""


@dataclass(frozen=True)
class InternalActor:
    """Server-authenticated INTERNAL user ID, never a request-supplied actor."""

    user_id: int


_SCHEMA = {
    "vr2_scope_versions": """CREATE TABLE vr2_scope_versions (
        membership_id TEXT NOT NULL PRIMARY KEY
            REFERENCES vendor_organization_memberships(vendor_membership_id) ON DELETE RESTRICT,
        vendor_id TEXT NOT NULL REFERENCES vendor_profiles(vendor_id) ON DELETE RESTRICT,
        account_id INTEGER NOT NULL REFERENCES vendor_accounts(id) ON DELETE RESTRICT,
        revision INTEGER NOT NULL CHECK(revision > 0),
        updated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 500)
    ) STRICT""",
    "vr2_site_scopes": """CREATE TABLE vr2_site_scopes (
        membership_id TEXT NOT NULL REFERENCES vr2_scope_versions(membership_id) ON DELETE RESTRICT,
        site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE RESTRICT,
        assignment_id TEXT NOT NULL REFERENCES vendor_site_assignments(vendor_site_assignment_id) ON DELETE RESTRICT,
        mode TEXT NOT NULL CHECK(mode IN ('ALL', 'SELECTED')),
        PRIMARY KEY(membership_id, site_id)
    ) STRICT""",
    "vr2_selected_tasks": """CREATE TABLE vr2_selected_tasks (
        membership_id TEXT NOT NULL,
        site_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
        PRIMARY KEY(membership_id, site_id, task_id),
        FOREIGN KEY(membership_id, site_id)
            REFERENCES vr2_site_scopes(membership_id, site_id) ON DELETE CASCADE
    ) STRICT""",
    "vr2_scope_events": """CREATE TABLE vr2_scope_events (
        membership_id TEXT NOT NULL REFERENCES vr2_scope_versions(membership_id) ON DELETE RESTRICT,
        revision INTEGER NOT NULL CHECK(revision > 0),
        actor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 500),
        scopes_json TEXT NOT NULL CHECK(json_valid(scopes_json) AND json_type(scopes_json) = 'array'),
        PRIMARY KEY(membership_id, revision)
    ) STRICT""",
}

_CORE = {
    "users": {"id", "role"},
    "vendor_accounts": {"id", "is_active"},
    "vendor_organizations": {"vendor_id", "organization_status"},
    "vendor_profiles": {"vendor_id"},
    "vendor_organization_memberships": {
        "vendor_membership_id", "vendor_id", "vendor_account_id", "membership_status"},
    "vendor_site_assignments": {
        "vendor_site_assignment_id", "vendor_id", "site_id", "assignment_status"},
    "sheet_vendor_bindings": {
        "vendor_id", "site_id", "sheet_id", "vendor_site_assignment_id", "binding_status"},
    "sites": {"id", "site_name", "is_active"},
    "sheets": {"id", "site_id", "name"},
    "tasks": {"id", "sheet_id", "name"},
    "task_vendor_assignments": {"task_id", "vendor_id"},
}


def _integer(value, field, minimum=1):
    if type(value) is not int or value < minimum:
        raise ScopeError(f"invalid_{field}")
    return value


def _membership_id(value):
    if not isinstance(value, str):
        raise ScopeError("invalid_membership_id")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ScopeError("invalid_membership_id") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ScopeError("invalid_membership_id")
    return value


@contextmanager
def _snapshot(conn, *, writing=False, fresh=False):
    if not isinstance(conn, sqlite3.Connection):
        raise ScopeError("sqlite_connection_required")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise ScopeError("foreign_keys_required")
    if writing and not conn.in_transaction:
        raise ScopeError("caller_transaction_required")
    if fresh and conn.in_transaction:
        raise ScopeError("fresh_request_connection_required")
    name = "vr2_" + uuid.uuid4().hex
    conn.execute(f"SAVEPOINT {name}")
    try:
        yield
        conn.execute(f"RELEASE SAVEPOINT {name}")
    except BaseException:
        conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
        conn.execute(f"RELEASE SAVEPOINT {name}")
        raise


def _sql_key(sql):
    return " ".join(sql.split()).rstrip(";")


def _schema(conn, *, allow_absent=False):
    # All queries and DML target main explicitly. Reject shadows as well, so a
    # controller cannot accidentally mix identities from another schema.
    names = set(_CORE) | set(_SCHEMA)
    for kind, name, table in conn.execute("SELECT type,name,tbl_name FROM temp.sqlite_schema"):
        if name in names or (kind == "trigger" and table in _SCHEMA):
            raise ScopeError("temp_schema_collision")
    for name, columns in _CORE.items():
        row = conn.execute("SELECT type FROM main.sqlite_schema WHERE name=?", (name,)).fetchone()
        if row is None or row[0] != "table":
            raise ScopeError(f"core_table_unavailable:{name}")
        actual = {row[1] for row in conn.execute(f"PRAGMA main.table_info({name})")}
        if not columns <= actual:
            raise ScopeError(f"core_columns_unavailable:{name}")
    for name, sql in _SCHEMA.items():
        if conn.execute("SELECT 1 FROM main.sqlite_schema WHERE type='trigger' AND tbl_name=?", (name,)).fetchone():
            raise ScopeError("unexpected_scope_trigger")
        row = conn.execute("SELECT type,sql FROM main.sqlite_schema WHERE name=?", (name,)).fetchone()
        if row is None and allow_absent:
            continue
        if row is None or row[0] != "table" or _sql_key(row[1]) != _sql_key(sql):
            raise ScopeError(f"scope_schema_unavailable:{name}")
        if conn.execute(f"PRAGMA main.foreign_key_check({name})").fetchone():
            raise ScopeError("scope_relationship_invalid")


def initialize_schema(conn):
    """Explicitly add only VR2 tables; caller must first validate core guards."""
    with _snapshot(conn, writing=True):
        _schema(conn, allow_absent=True)
        for name, sql in _SCHEMA.items():
            if conn.execute("SELECT 1 FROM main.sqlite_schema WHERE name=?", (name,)).fetchone() is None:
                conn.execute(sql.replace("CREATE TABLE ", "CREATE TABLE main.", 1))
        _schema(conn)


def _admin(conn, actor):
    if type(actor) is not InternalActor:
        raise ScopeError("authenticated_internal_actor_required")
    user_id = _integer(actor.user_id, "actor_id")
    rows = conn.execute("SELECT role FROM main.users WHERE id=?", (user_id,)).fetchall()
    if len(rows) != 1 or str(rows[0][0] or "").strip() != "admin":
        raise ScopeError("global_admin_required")
    return user_id


def _member(conn, membership_id):
    rows = conn.execute("""SELECT m.vendor_id,m.vendor_account_id,m.membership_status,
        a.is_active,o.organization_status FROM main.vendor_organization_memberships m
        JOIN main.vendor_accounts a ON a.id=m.vendor_account_id
        JOIN main.vendor_organizations o ON o.vendor_id=m.vendor_id
        JOIN main.vendor_profiles p ON p.vendor_id=m.vendor_id
        WHERE m.vendor_membership_id=?""", (membership_id,)).fetchall()
    if len(rows) != 1:
        raise ScopeError("membership_identity_unavailable")
    vendor, account, status, active, organization = rows[0]
    anchor = conn.execute("SELECT vendor_id,account_id FROM main.vr2_scope_versions WHERE membership_id=?",
                          (membership_id,)).fetchone()
    if anchor is not None and tuple(anchor) != (vendor, account):
        raise ScopeConflict("membership_identity_changed_use_successor")
    return vendor, account, status, active, organization


def _assignment(conn, vendor, site):
    rows = conn.execute("""SELECT a.vendor_site_assignment_id FROM main.vendor_site_assignments a
        JOIN main.sites s ON s.id=a.site_id AND s.is_active=1
        WHERE a.vendor_id=? AND a.site_id=? AND a.assignment_status='active'""", (vendor, site)).fetchall()
    if len(rows) != 1:
        raise ScopeError("尚未建立廠商工地關係：需要唯一有效關係及啟用工地")
    return rows[0][0]


def _eligible(conn, vendor, site, assignment):
    # Shared by validation, configured preview and effective resolution. Every
    # equality matters: individually valid FKs do not prove the intersection.
    return [dict(zip(("site_id", "site_name", "sheet_id", "sheet_name", "task_id", "task_name"), row))
            for row in conn.execute("""SELECT s.id,s.site_name,h.id,h.name,t.id,t.name
        FROM main.vendor_site_assignments a
        JOIN main.sites s ON s.id=a.site_id AND s.is_active=1
        JOIN main.sheet_vendor_bindings b ON b.vendor_site_assignment_id=a.vendor_site_assignment_id
            AND b.vendor_id=a.vendor_id AND b.site_id=a.site_id AND b.binding_status='active'
        JOIN main.sheets h ON h.id=b.sheet_id AND h.site_id=s.id
        JOIN main.tasks t ON t.sheet_id=h.id
        JOIN main.task_vendor_assignments v ON v.task_id=t.id AND v.vendor_id=a.vendor_id
        WHERE a.vendor_id=? AND a.site_id=? AND a.vendor_site_assignment_id=?
            AND a.assignment_status='active'
            AND (SELECT count(*) FROM main.vendor_site_assignments x
                WHERE x.vendor_id=a.vendor_id AND x.site_id=a.site_id AND x.assignment_status='active')=1
            AND (SELECT count(*) FROM main.sheet_vendor_bindings x
                WHERE x.vendor_id=b.vendor_id AND x.sheet_id=b.sheet_id AND x.binding_status='active')=1
            AND (SELECT count(*) FROM main.task_vendor_assignments x WHERE x.task_id=t.id)=1
        ORDER BY s.id,h.id,t.id""", (vendor, site, assignment))]


def _stored(conn, membership_id):
    selected = {}
    for site, task in conn.execute("""SELECT site_id,task_id FROM main.vr2_selected_tasks
            WHERE membership_id=? ORDER BY site_id,task_id""", (membership_id,)):
        selected.setdefault(site, []).append(task)
    return [{"site_id": site, "assignment_id": assignment, "mode": mode,
             "task_ids": selected.get(site, [])}
            for site, assignment, mode in conn.execute("""SELECT site_id,assignment_id,mode
                FROM main.vr2_site_scopes WHERE membership_id=? ORDER BY site_id""", (membership_id,))]


def _revision(conn, membership_id):
    row = conn.execute("SELECT revision FROM main.vr2_scope_versions WHERE membership_id=?", (membership_id,)).fetchone()
    return row[0] if row else 0


def save_scopes(conn, *, actor, membership_id, scopes, expected_revision, reason):
    """Replace the COMPLETE site set; [] revokes all and retains a version tombstone.

    scopes=[{'site_id': 1, 'assignment_id': current_assignment_uuid,
             'mode': 'ALL'|'SELECTED', 'task_ids': [...]}].
    No implicit mode, vendor/account pairing, role flag, or link creation.
    Returns the current/new revision. Identical saves are idempotent only after
    checking the supplied revision and every current relationship.
    """
    _membership_id(membership_id)
    _integer(expected_revision, "expected_revision", 0)
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500 or "\x00" in reason:
        raise ScopeError("invalid_reason")
    if not isinstance(scopes, list):
        raise ScopeError("scopes_require_list")
    with _snapshot(conn, writing=True):
        _schema(conn)
        actor_id = _admin(conn, actor)
        vendor, account, status, _, organization = _member(conn, membership_id)
        current = conn.execute("""SELECT vendor_membership_id FROM main.vendor_organization_memberships
            WHERE vendor_id=? AND vendor_account_id=? AND membership_status IN ('pending','active')""",
                               (vendor, account)).fetchall()
        if status not in {"pending", "active"} or organization not in {"disabled", "active"} or len(current) != 1:
            raise ScopeError("membership_not_current_or_organization_retired")
        previous = _revision(conn, membership_id)
        if previous != expected_revision:
            raise ScopeConflict("stale_revision")
        normalized, seen = [], set()
        for scope in scopes:
            if not isinstance(scope, dict) or set(scope) != {"site_id", "assignment_id", "mode", "task_ids"}:
                raise ScopeError("invalid_scope_fields")
            site = _integer(scope["site_id"], "site_id")
            mode, tasks = scope["mode"], scope["task_ids"]
            if site in seen or mode not in ("ALL", "SELECTED") or not isinstance(tasks, list):
                raise ScopeError("invalid_scope")
            seen.add(site)
            for task in tasks:
                _integer(task, "task_id")
            if len(tasks) != len(set(tasks)) or (mode == "ALL" and tasks):
                raise ScopeError("duplicate_or_unexpected_task_ids")
            assignment = _assignment(conn, vendor, site)
            if scope["assignment_id"] != assignment:
                raise ScopeConflict("stale_assignment_generation")
            eligible = {task["task_id"] for task in _eligible(conn, vendor, site, assignment)}
            if not set(tasks) <= eligible:
                raise ScopeError("selected_task_outside_current_vendor_site_binding")
            normalized.append({"site_id": site, "assignment_id": assignment, "mode": mode, "task_ids": sorted(tasks)})
        normalized.sort(key=lambda scope: scope["site_id"])
        if previous and normalized == _stored(conn, membership_id):
            return previous
        revision = previous + 1
        if previous:
            result = conn.execute("""UPDATE main.vr2_scope_versions SET revision=?,updated_by=?,
                updated_at=CURRENT_TIMESTAMP,reason=? WHERE membership_id=? AND revision=?""",
                (revision, actor_id, reason.strip(), membership_id, expected_revision))
            if result.rowcount != 1:
                raise ScopeConflict("stale_revision")
        else:
            conn.execute("""INSERT INTO main.vr2_scope_versions
                (membership_id,vendor_id,account_id,revision,updated_by,reason) VALUES(?,?,?,?,?,?)""",
                (membership_id, vendor, account, revision, actor_id, reason.strip()))
        conn.execute("DELETE FROM main.vr2_site_scopes WHERE membership_id=?", (membership_id,))
        for scope in normalized:
            conn.execute("INSERT INTO main.vr2_site_scopes VALUES(?,?,?,?)",
                         (membership_id, scope["site_id"], scope["assignment_id"], scope["mode"]))
            for task in scope["task_ids"]:
                conn.execute("INSERT INTO main.vr2_selected_tasks VALUES(?,?,?)", (membership_id, scope["site_id"], task))
        conn.execute("""INSERT INTO main.vr2_scope_events
            (membership_id,revision,actor_id,reason,scopes_json) VALUES(?,?,?,?,?)""",
            (membership_id, revision, actor_id, reason.strip(), json.dumps(normalized, sort_keys=True, separators=(",", ":"))))
        return revision


def _group(tasks):
    sites = {}
    for task in tasks:
        site = sites.setdefault(task["site_id"], {"site_id": task["site_id"], "site_name": task["site_name"], "sheets": {}})
        sheet = site["sheets"].setdefault(task["sheet_id"], {"sheet_id": task["sheet_id"], "sheet_name": task["sheet_name"], "tasks": []})
        sheet["tasks"].append({"task_id": task["task_id"], "task_name": task["task_name"]})
    for site in sites.values():
        site["sheets"] = list(site["sheets"].values())
        for sheet in site["sheets"]:
            sheet["task_count"] = len(sheet["tasks"])
        site["task_count"] = sum(sheet["task_count"] for sheet in site["sheets"])
    return {"sites": list(sites.values()), "task_count": len(tasks)}


def _configured(conn, vendor, scopes):
    tasks, issues = [], []
    for scope in scopes:
        if scope["mode"] not in ("ALL", "SELECTED"):
            raise ScopeError("invalid_stored_mode")
        rows = _eligible(conn, vendor, scope["site_id"], scope["assignment_id"])
        if scope["mode"] == "SELECTED":
            rows = [row for row in rows if row["task_id"] in scope["task_ids"]]
        elif scope["task_ids"]:
            raise ScopeError("all_scope_has_selected_residue")
        tasks.extend(rows)
        if not rows:
            issues.append({"site_id": scope["site_id"], "reason": "no_current_eligible_tasks"})
    return _group(tasks), issues


def _inactive_reason(conn, membership_id, member):
    _, account, status, active, organization = member
    if active != 1:
        return "account_inactive"
    if status != "active":
        return "membership_not_active"
    rows = conn.execute("""SELECT vendor_membership_id FROM main.vendor_organization_memberships
        WHERE vendor_account_id=? AND membership_status='active'""", (account,)).fetchall()
    if len(rows) != 1 or rows[0][0] != membership_id:
        return "membership_ambiguous"
    if organization != "active":
        return "organization_not_active"
    return None


def preview_scopes(conn, *, actor, membership_id):
    """Trusted global-admin preview; configuration is distinct from live access.

    May share the caller's management transaction. It is not a member resolver.
    No fields from this preview authorize a later member request.
    """
    _membership_id(membership_id)
    with _snapshot(conn):
        _schema(conn)
        _admin(conn, actor)
        member = _member(conn, membership_id)
        scopes = _stored(conn, membership_id)
        configured, issues = _configured(conn, member[0], scopes)
        reason = _inactive_reason(conn, membership_id, member)
        return {"membership_id": membership_id, "revision": _revision(conn, membership_id),
                "configured_scopes": scopes, "configured_scope": configured,
                "effective_scope": _group([]) if reason else configured,
                "inactive_reason": reason, "site_issues": issues}


def resolve_scope(conn, *, vendor_account_id):
    """Fail closed, read-only member view from a new request snapshot.

    Caller supplies a trusted authenticated vendor account ID, never a vendor
    name, target vendor ID or session scope. Existing transactions are rejected
    without ending them. There is no admin bypass. Empty results grant nothing.
    """
    try:
        _integer(vendor_account_id, "vendor_account_id")
        with _snapshot(conn, fresh=True):
            _schema(conn)
            rows = conn.execute("""SELECT vendor_membership_id FROM main.vendor_organization_memberships
                WHERE vendor_account_id=? AND membership_status='active'""", (vendor_account_id,)).fetchall()
            if len(rows) != 1:
                return {**_group([]), "reason": "no_unique_active_membership"}
            membership_id = rows[0][0]
            member = _member(conn, membership_id)
            reason = _inactive_reason(conn, membership_id, member)
            if reason:
                return {**_group([]), "reason": reason}
            scope, _ = _configured(conn, member[0], _stored(conn, membership_id))
            return {**scope, "reason": None if scope["task_count"] else "no_eligible_tasks"}
    except (ScopeError, sqlite3.Error):
        return {**_group([]), "reason": "scope_unavailable"}


def admin_schema_state(conn, *, actor):
    """Read-only management gate: absent as a whole, or exact VR2 schema.

    The controller still supplies the existing core schema guard. Unlike explicit
    initialize_schema, management must never repair a partially present schema.
    """
    with _snapshot(conn):
        _admin(conn, actor)
        present = sum(conn.execute(
            "SELECT 1 FROM main.sqlite_schema WHERE name=?", (name,)).fetchone() is not None
            for name in _SCHEMA)
        if present not in (0, len(_SCHEMA)):
            raise ScopeError("partial_scope_schema")
        _schema(conn, allow_absent=present == 0)
        return "absent" if present == 0 else "ready"


def list_admin_eligible_tasks(conn, *, actor, vendor_id, site_id):
    """Expose the SAME complete intersection used by saving and resolution.

    This reports existing valid links only; it does not prepare links or grant
    effective access. VR3 uses it after preparation in its caller transaction.
    """
    _integer(site_id, "site_id")
    with _snapshot(conn):
        _admin(conn, actor)
        _schema(conn)
        assignment = _assignment(conn, vendor_id, site_id)
        return _eligible(conn, vendor_id, site_id, assignment)
