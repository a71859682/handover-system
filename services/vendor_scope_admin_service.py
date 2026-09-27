"""Pending-only VR3 management. No app import, connection creation or activation.

The controller supplies a fresh FK-enabled connection, the existing read-only
core classifier, and an authenticated InternalActor. One caller-owned write
transaction and a nested savepoint cover preparation, DDL and VR2 persistence.
"""

from contextlib import contextmanager
import hashlib
import json
import sqlite3
import uuid

from services import vendor_access_service as access
from services import vendor_roster_service as roster
from services import vendor_registration_service as registration


class AdminError(access.ScopeError):
    pass


class PrerequisiteError(AdminError):
    pass


def _rows(conn, sql, params=()):
    cursor = conn.execute(sql, params)
    names = [col[0] for col in cursor.description]
    return [dict(zip(names, row)) for row in cursor]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _gate(conn, actor, core_state):
    if not isinstance(conn, sqlite3.Connection) or not conn.in_transaction:
        raise AdminError("需要獨立請求交易")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise AdminError("需要啟用外鍵")
    if type(actor) is not access.InternalActor or type(actor.user_id) is not int:
        raise AdminError("需要當期內部全站管理者")
    role = conn.execute("SELECT role FROM main.users WHERE id=?", (actor.user_id,)).fetchone()
    if role is None or role[0] != "admin":
        raise AdminError("需要當期內部全站管理者")
    if core_state(conn) != "all_exact":
        raise PrerequisiteError("核心廠商關係結構缺少或不相容，需先處理資料前提")
    try:
        state = access.admin_schema_state(conn, actor=actor)
        profiles = roster.list_profiles(conn)
    except (access.ScopeError, roster.RosterError) as exc:
        raise PrerequisiteError("VR1／VR2 資料前提缺少或不相容：" + str(exc)) from exc
    return state, profiles


def _registration_info(conn):
    """Display-only supplement; never used in the editor fingerprint or grants."""
    try:
        if registration.request_schema_state(conn) == "absent":
            return {"state": "absent", "by_account": {}}
        rows = _rows(conn, """SELECT account_id,requested_vendor_id,submitted_company_name,
            submitted_tax_id,created_at FROM main.vendor_registration_requests ORDER BY account_id""")
        return {"state": "ready", "by_account": {r["account_id"]: r for r in rows}}
    except (registration.PrerequisiteError, sqlite3.Error):
        return {"state": "unavailable", "by_account": {}}


def catalog(conn, *, actor, core_state):
    state, profiles = _gate(conn, actor, core_state)
    statuses = dict(conn.execute("SELECT vendor_id,organization_status FROM main.vendor_organizations"))
    accounts = _rows(conn, "SELECT id,username,is_active FROM main.vendor_accounts ORDER BY id")
    memberships = _rows(conn, """SELECT vendor_account_id,vendor_id,membership_status
        FROM main.vendor_organization_memberships ORDER BY vendor_account_id,vendor_membership_id""")
    for account in accounts:
        history = [m for m in memberships if m["vendor_account_id"] == account["id"]]
        account["status"] = ("帳號已啟用，本片不能修改" if account["is_active"] != 0 else
                             "尚無歸屬，需明確確認" if not history else
                             "待開通成員，請選擇原廠商" if len(history) == 1 and
                             history[0]["membership_status"] == "pending" else
                             "成員歷史不適用，本片不能修改")
        account["configurable"] = account["is_active"] == 0 and (not history or
            (len(history) == 1 and history[0]["membership_status"] == "pending" and
             statuses.get(history[0]["vendor_id"]) == "disabled"))
    return {"schema_state": state, "profiles": [dict(p, organization_status=statuses[p["vendor_id"]])
            for p in profiles], "accounts": accounts,
            "has_pending": any(a["configurable"] for a in accounts),
            "registration_info": _registration_info(conn)}


def _link_plan(site, tasks, assignments, bindings):
    history = [row for row in assignments if row["site_id"] == site["id"]]
    if history and (len(history) != 1 or history[0]["assignment_status"] != "active" or
                    history[0]["predecessor_assignment_id"] is not None or history[0]["successor_count"]):
        return None, "工地關係有 inactive／多世代歷史，需另行處理"
    assignment = history[0]["vendor_site_assignment_id"] if history else None
    sheets = sorted({task["sheet_id"] for task in tasks})
    plans = []
    for sheet in sheets:
        candidates = [b for b in bindings if b["sheet_id"] == sheet]
        if candidates and (len(candidates) != 1 or assignment is None or
            candidates[0]["vendor_id"] != site["vendor_id"] or
            candidates[0]["site_id"] != site["id"] or
            candidates[0]["vendor_site_assignment_id"] != assignment or
            candidates[0]["binding_status"] != "active" or
            candidates[0]["predecessor_binding_id"] is not None or candidates[0]["successor_count"]):
            return None, "表格關係有 inactive／衝突／多世代歷史，需另行處理"
        plans.append({"sheet_id": sheet, "binding_id": candidates[0]["sheet_vendor_binding_id"]
                      if candidates else None})
    for binding in bindings:
        touches_site = (binding["vendor_id"] == site["vendor_id"] and binding["site_id"] == site["id"])
        touches_assignment = assignment and binding["vendor_site_assignment_id"] == assignment
        if (touches_site or touches_assignment) and (
            binding["vendor_id"] != site["vendor_id"] or binding["site_id"] != site["id"] or
            binding["vendor_site_assignment_id"] != assignment or binding["current_sheet_site"] != site["id"] or
            binding["binding_status"] != "active" or binding["predecessor_binding_id"] is not None or
            binding["successor_count"] or sum(b["sheet_id"] == binding["sheet_id"] for b in bindings) != 1):
            return None, "既有表格與工地／廠商關係不一致，需另行處理"
    return {"assignment_id": assignment, "bindings": plans}, None


def editor(conn, *, actor, vendor_id, account_id, core_state):
    data = catalog(conn, actor=actor, core_state=core_state)
    if type(account_id) is not int or account_id <= 0 or not isinstance(vendor_id, str):
        raise AdminError("帳號／廠商 ID 格式錯誤")
    profile = next((p for p in data["profiles"] if p["vendor_id"] == vendor_id), None)
    account = next((a for a in data["accounts"] if a["id"] == account_id), None)
    if profile is None or account is None:
        raise AdminError("帳號或已保存廠商不存在，請重新選擇")
    memberships = _rows(conn, """SELECT m.vendor_membership_id,m.vendor_id,m.vendor_account_id,
        m.membership_role,m.membership_status,m.predecessor_membership_id,
        (SELECT count(*) FROM main.vendor_organization_memberships x
         WHERE x.predecessor_membership_id=m.vendor_membership_id) AS successor_count
        FROM main.vendor_organization_memberships m WHERE m.vendor_account_id=?
        ORDER BY m.vendor_membership_id""", (account_id,))
    blocked = None
    if account["is_active"] != 0:
        blocked = "帳號已啟用，本片不能修改"
    elif profile["organization_status"] != "disabled":
        blocked = "廠商組織不是 disabled，本片不能修改"
    elif memberships and (len(memberships) != 1 or memberships[0]["vendor_id"] != vendor_id or
                          memberships[0]["membership_status"] != "pending" or
                          memberships[0]["predecessor_membership_id"] is not None or memberships[0]["successor_count"]):
        blocked = "成員有其他廠商／非 pending／多世代歷史，不能搬移或復活"
    membership_id = memberships[0]["vendor_membership_id"] if len(memberships) == 1 and not blocked else None
    assignments = _rows(conn, """SELECT a.vendor_site_assignment_id,a.vendor_id,a.site_id,
        a.assignment_status,a.predecessor_assignment_id,
        (SELECT count(*) FROM main.vendor_site_assignments x
         WHERE x.predecessor_assignment_id=a.vendor_site_assignment_id) AS successor_count
        FROM main.vendor_site_assignments a WHERE a.vendor_id=? ORDER BY a.vendor_site_assignment_id""", (vendor_id,))
    bindings = _rows(conn, """SELECT b.sheet_vendor_binding_id,b.vendor_id,b.site_id,b.sheet_id,
        b.vendor_site_assignment_id,b.binding_status,b.predecessor_binding_id,h.site_id AS current_sheet_site,
        (SELECT count(*) FROM main.sheet_vendor_bindings x
         WHERE x.predecessor_binding_id=b.sheet_vendor_binding_id) AS successor_count
        FROM main.sheet_vendor_bindings b LEFT JOIN main.sheets h ON h.id=b.sheet_id
        WHERE b.vendor_id=? OR b.vendor_site_assignment_id IN
        (SELECT vendor_site_assignment_id FROM main.vendor_site_assignments WHERE vendor_id=?)
        ORDER BY b.sheet_vendor_binding_id""", (vendor_id, vendor_id))
    task_rows = roster.list_task_assignments(conn)
    sheet_names = dict(conn.execute("SELECT id,name FROM main.sheets"))
    sites = []
    for site in _rows(conn, "SELECT id,site_name,is_active FROM main.sites ORDER BY id"):
        tasks = [{"task_id": t["task_id"], "task_name": t["task_name"], "sheet_id": t["sheet_id"],
                  "sheet_name": sheet_names[t["sheet_id"]]} for t in task_rows
                 if t["vendor_id"] == vendor_id and t["site_id"] == site["id"] and t["sheet_id"] in sheet_names]
        plan, issue = _link_plan(dict(site, vendor_id=vendor_id), tasks, assignments, bindings)
        if site["is_active"] != 1:
            issue = "工地未啟用，不能配置"
        sites.append(dict(site, tasks=tasks, plan=plan, issue=issue))
    preview = {"revision": 0, "configured_scopes": [], "configured_scope": {"task_count": 0},
               "effective_scope": {"task_count": 0}}
    if membership_id and data["schema_state"] == "ready":
        preview = access.preview_scopes(conn, actor=actor, membership_id=membership_id)
    by_site = {s["id"]: s for s in sites}
    for scope in preview["configured_scopes"]:
        site = by_site.get(scope["site_id"])
        if site is None or site["issue"] or scope["assignment_id"] != site["plan"]["assignment_id"] or not set(
                scope["task_ids"]) <= {t["task_id"] for t in site["tasks"]}:
            blocked = "已保存選項失效或世代改變；不能靜默撤除，需先處理並重新確認"
    result = {"profile": profile, "account": account, "memberships": memberships,
              "membership_id": membership_id, "blocked": blocked, "sites": sites,
              "assignments": assignments, "bindings": bindings, "preview": preview,
              "schema_state": data["schema_state"],
              "pending_task_count": sum(t["pending"] for t in task_rows)}
    result["fingerprint"] = fingerprint(result)
    # Display-only data follows the fingerprint and stays scoped to this account.
    # POST error rendering has an editor but no catalog.
    info = data["registration_info"]
    result["registration_info"] = {"state": info["state"], "request": info["by_account"].get(account_id)}
    return result


@contextmanager
def _atomic(conn):
    name = "vr3_" + uuid.uuid4().hex
    conn.execute("SAVEPOINT " + name)
    try:
        yield
        conn.execute("RELEASE SAVEPOINT " + name)
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT " + name)
        conn.execute("RELEASE SAVEPOINT " + name)
        raise


def _insert(conn, table, fields, actor, reason, correlation):
    for prefix in ("created", "updated"):
        fields.update({prefix + "_actor_kind": "internal_user", prefix + "_actor_id": str(actor.user_id),
                       prefix + "_reason": reason, prefix + "_source": "004F-VR3/vendor_scope_admin",
                       prefix + "_correlation_id": correlation})
    conn.execute(f"INSERT INTO main.{table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                 tuple(fields.values()))


def save_pending(conn, *, actor, vendor_id, account_id, expected_fingerprint,
                 scopes, reason, confirm_membership, core_state):
    """Complete-set replacement. Invalid or stale input retains zero writes."""
    current = editor(conn, actor=actor, vendor_id=vendor_id, account_id=account_id, core_state=core_state)
    if current["fingerprint"] != expected_fingerprint:
        raise access.ScopeConflict("編輯快照已過期，請重新載入並確認全部選項")
    if current["blocked"]:
        raise AdminError(current["blocked"])
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500 or "\x00" in reason:
        raise AdminError("請填寫 1–500 字的保存理由")
    if type(confirm_membership) is not bool or (not current["membership_id"] and not confirm_membership):
        raise AdminError("首次建立成員必須明確確認此帳號的廠商歸屬")
    if not isinstance(scopes, list):
        raise AdminError("工地設定必須是完整集合")
    seen = set()
    sites = {s["id"]: s for s in current["sites"]}
    for scope in scopes:
        if not isinstance(scope, dict) or set(scope) != {"site_id", "mode", "task_ids"}:
            raise AdminError("工地設定欄位不完整")
        sid, mode, tasks = scope["site_id"], scope["mode"], scope["task_ids"]
        if type(sid) is not int or sid in seen or sid not in sites or sites[sid]["issue"]:
            raise AdminError("工地無效、重複或關係歷史有衝突")
        seen.add(sid)
        if mode not in ("ALL", "SELECTED") or not isinstance(tasks, list) or any(type(t) is not int for t in tasks):
            raise AdminError("工項模式或 ID 格式錯誤")
        if len(tasks) != len(set(tasks)) or (mode == "ALL" and tasks) or not set(tasks) <= {
                t["task_id"] for t in sites[sid]["tasks"]}:
            raise AdminError("工項重複或不屬於本廠商／工地，ALL 必須送空工項集合")
    with _atomic(conn):
        if current["schema_state"] == "absent":
            access.initialize_schema(conn)
        correlation = str(uuid.uuid4())
        membership_id = current["membership_id"]
        if membership_id is None:
            membership_id = str(uuid.uuid4())
            _insert(conn, "vendor_organization_memberships", {
                "vendor_membership_id": membership_id, "vendor_id": vendor_id,
                "vendor_account_id": account_id, "membership_role": "member", "membership_status": "pending"
            }, actor, reason.strip(), correlation)
        prepared = []
        for scope in scopes:
            site = sites[scope["site_id"]]
            plan = site["plan"]
            assignment = plan["assignment_id"]
            if assignment is None:
                assignment = str(uuid.uuid4())
                _insert(conn, "vendor_site_assignments", {"vendor_site_assignment_id": assignment,
                    "vendor_id": vendor_id, "site_id": site["id"], "assignment_status": "active"
                }, actor, reason.strip(), correlation)
            for binding in plan["bindings"]:
                if binding["binding_id"] is None:
                    _insert(conn, "sheet_vendor_bindings", {"sheet_vendor_binding_id": str(uuid.uuid4()),
                        "vendor_id": vendor_id, "site_id": site["id"], "sheet_id": binding["sheet_id"],
                        "vendor_site_assignment_id": assignment, "binding_status": "active"
                    }, actor, reason.strip(), correlation)
            eligible = access.list_admin_eligible_tasks(conn, actor=actor, vendor_id=vendor_id, site_id=site["id"])
            if {t["task_id"] for t in eligible} != {t["task_id"] for t in site["tasks"]}:
                raise access.ScopeConflict("準備後完整交集不一致，已回滾，請重新載入")
            prepared.append(dict(scope, assignment_id=assignment))
        access.save_scopes(conn, actor=actor, membership_id=membership_id, scopes=prepared,
                           expected_revision=current["preview"]["revision"], reason=reason)
        if core_state(conn) != "all_exact":
            raise PrerequisiteError("保存後核心 guard 不相容，已回滾")
        result = access.preview_scopes(conn, actor=actor, membership_id=membership_id)
        if result["effective_scope"]["task_count"] != 0:
            raise AdminError("待開通配置不得成為有效權限")
        return result
