"""C09 offline route checks in a new retained synthetic fixture.

No listener, real login, old suite, or existing fixture is used. The child
imports the real preview entry through its unchanged preimport/storage guards.
Synthetic sessions test authorization behavior; they are not live UI evidence.
Run with --evidence pointing at a NEW directory outside the product repository.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from preview.vr4_20260928_r01.fixture import FLAGS, IDENTITY, WINDOWS_ROOT, plain_path


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def audited_insert(conn, table, values):
    for prefix in ("created", "updated"):
        values.update({f"{prefix}_actor_kind": "migration",
                       f"{prefix}_actor_id": "c09-synthetic",
                       f"{prefix}_reason": "offline projection check",
                       f"{prefix}_source": "C09 fixture",
                       f"{prefix}_correlation_id": "c09-synthetic"})
    conn.execute(f"INSERT INTO {table} ({','.join(values)}) VALUES "
                 f"({','.join('?' for _ in values)})", tuple(values.values()))


def child(root):
    check(os.name == "nt" and not sys.flags.optimize, "windows_assertions_required")
    root = root.resolve()
    plain_path(root)
    check(root.is_relative_to(WINDOWS_ROOT) and root.is_dir()
          and not any(root.iterdir()), "new_empty_scratch_required")
    database = root / "fixture.sqlite3"
    os.environ.update({flag: "false" for flag in FLAGS})
    os.environ.update(VR4_PREVIEW_MODE=IDENTITY, VR4_PREVIEW_RUNTIME="LOCAL_SMOKE",
                      VR4_PREVIEW_ROOT=str(root), APP_DB_PATH=str(database),
                      VR4_PREVIEW_ADMIN_USERNAME="c09.synthetic.admin",
                      VR4_PREVIEW_ADMIN_PASSWORD=secrets.token_urlsafe(32),
                      APP_SECRET_KEY=secrets.token_urlsafe(48), DATABASE_URL="",
                      DUAL_WRITE_TABLES="", FLASK_DEBUG="0", FLASK_TESTING="false")
    network_attempts = []

    def no_network(event, arguments):
        if event in {"socket.__new__", "socket.connect", "socket.bind", "socket.getaddrinfo", "socket.sendto"}:
            network_attempts.append(event)
            raise RuntimeError("NETWORK_FORBIDDEN")

    sys.addaudithook(no_network)
    from preview.vr4_20260928_r01 import entry
    from services import vendor_access_service as access
    app = entry.app
    # Expose exceptions only to this in-process check; no server is started.
    app.config["PROPAGATE_EXCEPTIONS"] = True
    check(not app.testing and not app.debug, "production_guard_retained")
    memberships = [str(uuid.uuid4()), str(uuid.uuid4())]
    selected_by_membership = dict(zip(memberships, ([302, 303], [302, 306])))
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        access.initialize_schema(conn)
        admin = conn.execute("SELECT id FROM users WHERE username='c09.synthetic.admin'").fetchone()[0]
        vendors = dict(conn.execute("SELECT tax_id,vendor_id FROM vendor_profiles"))
        beta, alpha = vendors["00000002"], vendors["00000001"]
        assignments = {site: str(uuid.uuid4()) for site in (101, 102)}
        for site, assignment in assignments.items():
            audited_insert(conn, "vendor_site_assignments", {
                "vendor_site_assignment_id": assignment, "vendor_id": beta,
                "site_id": site, "assignment_status": "active"})
        for sheet, site in ((201, 101), (202, 101), (203, 102)):
            audited_insert(conn, "sheet_vendor_bindings", {
                "sheet_vendor_binding_id": str(uuid.uuid4()), "vendor_id": beta,
                "sheet_id": sheet, "site_id": site,
                "vendor_site_assignment_id": assignments[site], "binding_status": "active"})
        conn.execute("INSERT INTO users(id,username,password_hash,role) "
                     "VALUES(990,'c09.dummy.member','not-a-login-credential','member')")
        for account, membership, role in zip((901, 902), memberships, ("member", "owner")):
            conn.execute("INSERT INTO vendor_accounts(id,username,password_hash,vendor_name,is_active) "
                         "VALUES(?,?,?,?,0)", (account, f"c09.dummy.{account}",
                         "not-a-login-credential", "synthetic"))
            audited_insert(conn, "vendor_organization_memberships", {
                "vendor_membership_id": membership, "vendor_id": beta,
                "vendor_account_id": account, "membership_role": role,
                "membership_status": "pending"})
            access.save_scopes(conn, actor=access.InternalActor(admin), membership_id=membership,
                expected_revision=0, reason="new offline synthetic setup", scopes=[
                    dict(site_id=101, assignment_id=assignments[101], mode="SELECTED",
                         task_ids=selected_by_membership[membership]),
                    dict(site_id=102, assignment_id=assignments[102], mode="ALL", task_ids=[])])

    completed = []

    def request(label, *, session_values=None, path="/preview/fixture-state", method="GET", status=200):
        before = database.read_bytes()
        client = app.test_client()
        if session_values:
            with client.session_transaction() as state:
                state.update(session_values)
        response = client.open(path, method=method)
        check(response.status_code == status, label + "_status")
        check(database.read_bytes() == before, label + "_database_bytes_changed")
        completed.append(label)
        return response

    def projection(label, site=None):
        values = {"user_id": admin}
        if site is not None:
            values["current_site_id"] = site
        response = request(label, session_values=values)
        check(response.headers.get("Cache-Control") == "no-store", label + "_cache")
        payload = response.get_json()
        check(all(payload[k] == v for k, v in entry.VERSION.items()), label + "_identity")
        check(payload["readonly"] is True, label + "_readonly")
        digest = hashlib.sha256(json.dumps(payload["state"], sort_keys=True,
                                          ensure_ascii=True).encode()).hexdigest()
        check(digest == payload["state_sha256"], label + "_digest")
        forbidden = {"password", "password_hash", "secret", "cookie", "csrf_token", "snapshot_token"}

        def safe_keys(value):
            if isinstance(value, dict):
                check(not forbidden.intersection(value), label + "_secret_field")
                for item in value.values():
                    safe_keys(item)
            elif isinstance(value, list):
                for item in value:
                    safe_keys(item)
        safe_keys(payload)
        return payload

    def rows(payload):
        return {r["vendor_membership_id"]: r for r in payload["state"]["memberships"]}

    def task_map(row):
        return {site["site_id"]: [task["task_id"] for sheet in site["sheets"]
                for task in sheet["tasks"]] for site in row["configured_scope"]["sites"]}

    def task_coordinates(row):
        return sorted((site["site_id"], sheet["sheet_id"], task["task_id"])
                      for site in row["configured_scope"]["sites"]
                      for sheet in site["sheets"] for task in sheet["tasks"])

    selected_coordinates = dict(zip(memberships, (
        [(101, 201, 302), (101, 202, 303)],
        [(101, 201, 302), (101, 201, 306)])))

    first = projection("admin_without_current_site")
    initial = rows(first)
    check(set(initial) == set(memberships), "no_invented_membership")
    for account, membership, role in zip((901, 902), memberships, ("member", "owner")):
        row = initial[membership]
        check(row["membership_role"] == role and row["vendor_id"] == beta and row["vendor_account_id"] == account
              and row["membership_status"] == "pending" and row["revision"] == 1, "stored_identity_role")
        check(task_map(row) == {101: selected_by_membership[membership], 102: [304]}, "initial_configured_ids")
        check(task_coordinates(row) == sorted(selected_coordinates[membership] + [(102, 203, 304)]),
              "initial_membership_site_sheet_task_binding")
        check(row["configured_task_count"] == 3 and row["effective_task_count"] == 0, "configured_not_effective")
    for site in (101, 102, 999999):
        check(projection("current_site_" + str(site), site)["state"] == first["state"], "site_independence")

    for label, values in [("anonymous", {}), ("vendor", {"vendor_account_id": 901}),
                          ("mixed", {"user_id": admin, "vendor_account_id": 901}),
                          ("member", {"user_id": 990}), ("missing_user", {"user_id": 999999})]:
        request(label, session_values=values, status=403)
    for index, value in enumerate((0, -1, True, str(admin))):
        request("invalid_user_" + str(index), session_values={"user_id": value}, status=403)
    for query in ("site_id=101", "sql=select", "filter=all"):
        request("query_" + query.split("=")[0], session_values={"user_id": admin},
                path="/preview/fixture-state?" + query, status=400)
    request("anonymous_query_precedence", path="/preview/fixture-state?site_id=101", status=400)
    request("post_rejected", session_values={"user_id": admin}, method="POST", status=405)

    # Controlled mutations below affect this new synthetic fixture only.
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        for task, sheet, vendor in ((904, 203, beta), (905, 203, alpha), (906, 201, beta)):
            conn.execute("INSERT INTO tasks(id,sheet_id,col_index,vendor,location,name) VALUES(?,?,?,?,?,?)",
                         (task, sheet, task, "synthetic", "synthetic", "dynamic " + str(task)))
            conn.execute("INSERT INTO task_vendor_assignments VALUES(?,?,'fixture','explicit_name_exact_trim','{}')",
                         (task, vendor))
    dynamic = rows(projection("dynamic_all_selected_vendor_boundaries"))
    for membership, row in dynamic.items():
        check(task_map(row) == {101: selected_by_membership[membership], 102: [304, 904]}, "canonical_dynamic_ids")
        check(task_coordinates(row) == sorted(selected_coordinates[membership] + [(102, 203, 304), (102, 203, 904)]),
              "dynamic_membership_site_sheet_task_binding")
        check(row["configured_task_count"] == 4 and row["effective_task_count"] == 0
              and row["revision"] == 1, "dynamic_counts_revision")
        check(row["configured_scopes"] == initial[row["vendor_membership_id"]]["configured_scopes"],
              "stored_scope_unchanged")
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("UPDATE tasks SET sheet_id=201,col_index=9304 WHERE id=304")
    for membership, row in rows(projection("moved_task_site_boundary")).items():
        check(task_map(row) == {101: selected_by_membership[membership], 102: [904]}, "no_hardcoded_304")
        check(task_coordinates(row) == sorted(selected_coordinates[membership] + [(102, 203, 904)]),
              "moved_task_excluded_from_original_site_sheet")
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("UPDATE tasks SET sheet_id=202,col_index=9906 WHERE id=306")
    selected_coordinates[memberships[1]] = [(101, 201, 302), (101, 202, 306)]
    for membership, row in rows(projection("same_site_sheet_reassignment")).items():
        check(task_coordinates(row) == sorted(selected_coordinates[membership] + [(102, 203, 904)]),
              "same_site_sheet_change_without_membership_cross_pairing")
        check(row["revision"] == 1 and row["configured_scopes"] == initial[membership]["configured_scopes"],
              "same_site_sheet_change_preserves_saved_scope_revision")
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE sheet_vendor_bindings SET binding_status='inactive' "
                     "WHERE vendor_id=? AND site_id=102", (beta,))
    for membership, row in rows(projection("inactive_binding_zero_eligible")).items():
        check(task_map(row) == {101: selected_by_membership[membership]} and row["revision"] == 1, "binding_excluded")
        check(task_coordinates(row) == sorted(selected_coordinates[membership]), "inactive_binding_tuple_exclusion")
        check(len(row["configured_scopes"]) == 2, "stored_all_scope_retained")
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE vendor_site_assignments SET assignment_status='inactive' "
                     "WHERE vendor_id=? AND site_id=101", (beta,))
    for row in rows(projection("inactive_assignment_empty_expansion")).values():
        check(task_map(row) == {} and row["configured_task_count"] == 0, "assignment_excluded")
        check(task_coordinates(row) == [], "inactive_assignment_no_tuples")
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE users SET role='member' WHERE id=?", (admin,))
    request("current_db_role_downgrade", session_values={"user_id": admin}, status=403)
    check(not network_attempts, "unexpected_network_attempt")
    print(json.dumps({"result": "PASS", "source": "offline Flask test_client; synthetic sessions",
                      "checks": completed, "check_count": len(completed),
                      "network_attempts": 0, "live_login": False,
                      "fixture_retained": True, "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--child", type=Path)
    args = parser.parse_args()
    if args.child:
        child(args.child)
        return
    check(args.evidence is not None, "evidence_directory_required")
    evidence = args.evidence.resolve()
    plain_path(evidence)
    check(not evidence.exists() and not evidence.is_relative_to(REPO), "new_external_evidence_required")
    evidence.mkdir(parents=True, exist_ok=False)
    root = WINDOWS_ROOT / "scratch" / ("c09-" + uuid.uuid4().hex)
    plain_path(root)
    root.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(root)]
    (evidence / "run.json").write_text(json.dumps({"argv": command, "cwd": str(REPO),
        "scratch": str(root), "mode": "new synthetic offline test; no live product"}, indent=2), encoding="utf-8")
    try:
        result = subprocess.run(command, cwd=REPO, env=env, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as error:
        (evidence / "child.stdout").write_bytes(error.stdout or b"")
        (evidence / "child.stderr").write_bytes(error.stderr or b"")
        (evidence / "result.json").write_text('{"result":"TIMEOUT","retry":false}', encoding="utf-8")
        raise SystemExit("isolated child timed out; retained evidence; do not blind retry")
    (evidence / "child.stdout").write_bytes(result.stdout)
    (evidence / "child.stderr").write_bytes(result.stderr)
    (evidence / "result.json").write_text(json.dumps({"exit_code": result.returncode,
        "scratch_retained": True}), encoding="utf-8")
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
