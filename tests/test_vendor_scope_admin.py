"""VR3: real Flask flow and transaction rejection, in an isolated subprocess.

Set VR3_TEST_ROOT to a new disposable directory before invoking unittest. The
child disables external backends and installs SQLite/network guards BEFORE app
import. It never uses a repo/site.db or imports app in the discovery process.
"""

import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

REPO = Path(__file__).resolve().parents[1]
FLAGS = ("USE_SQLALCHEMY_READS", "USE_SQLALCHEMY_WRITES", "USERS_READ_COMPARE",
         "DUAL_WRITE_ENABLED", "DUAL_WRITE_DRY_RUN", "DUAL_WRITE_STRICT")


class VendorScopeAdminIsolationTests(unittest.TestCase):
    def test_isolated_flask_behavior_suite(self):
        root = Path(os.environ["VR3_TEST_ROOT"]).resolve()
        with tempfile.TemporaryDirectory(prefix="vr3-flask-", dir=root) as child_root:
            env = os.environ.copy()
            env.update({flag: "false" for flag in FLAGS})
            env.update(APP_DB_PATH=str(Path(child_root) / "bootstrap.sqlite3"), DATABASE_URL="",
                       DUAL_WRITE_TABLES="", PYTHONDONTWRITEBYTECODE="1")
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--child", child_root],
                                    cwd=REPO, env=env, capture_output=True)
            # Preserve exact child outputs in the test root for the execution
            # wrapper; relay without changing their contents into its streams.
            (root / "vr3-child.stdout").write_bytes(result.stdout)
            (root / "vr3-child.stderr").write_bytes(result.stderr)
            sys.stdout.buffer.write(result.stdout)
            sys.stderr.buffer.write(result.stderr)
            self.assertEqual(result.returncode, 0, "isolated Flask child failed; see original streams")


class FormParser(HTMLParser):
    """Read actual successful HTML controls, without a browser/JS claim."""
    def __init__(self, html):
        super().__init__()
        from werkzeug.datastructures import MultiDict
        self.form = MultiDict()
        self.active = False
        self.select = None
        self.options = []
        self.textarea = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.active = a.get("id") == "pending-scope-form"
        if not self.active:
            return
        if tag == "input" and "name" in a and "disabled" not in a:
            if a.get("type") not in ("checkbox", "radio") or "checked" in a:
                self.form.add(a["name"], a.get("value", ""))
        if tag == "select":
            self.select, self.options = a.get("name"), []
        if tag == "option" and self.select:
            self.options.append((a.get("value", ""), "selected" in a))
        if tag == "textarea":
            self.textarea = a.get("name")
            self.form[self.textarea] = ""

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False
        if tag == "select" and self.select:
            self.form[self.select] = next((v for v, selected in self.options if selected), self.options[0][0])
            self.select = None
        if tag == "textarea":
            self.textarea = None

    def handle_data(self, value):
        if self.active and self.textarea:
            self.form[self.textarea] += value


def child_suite(root):
    if sys.flags.optimize:
        raise RuntimeError("Isolation requires assertions enabled")
    root = root.resolve()
    assert root.is_dir() and not (root / "bootstrap.sqlite3").exists()
    assert Path(os.environ["APP_DB_PATH"]).resolve() == root / "bootstrap.sqlite3"
    assert os.environ.get("DATABASE_URL") == "" and os.environ.get("DUAL_WRITE_TABLES") == ""
    assert all(os.environ.get(flag) == "false" for flag in FLAGS)
    counts = {"sqlite_outside_attempts": 0, "network_attempts": 0, "postgres_attempts": 0}

    def audit(event, arguments):
        if event == "sqlite3.connect":
            raw = str(arguments[0])
            path = Path(url2pathname(unquote(urlsplit(raw).path)) if raw.startswith("file:") else raw).resolve()
            if not path.is_relative_to(root):
                counts["sqlite_outside_attempts"] += 1
                raise RuntimeError("non-fixture SQLite access")
        if event in {"socket.connect", "socket.getaddrinfo", "socket.bind", "socket.sendto"}:
            counts["network_attempts"] += 1
            raise RuntimeError("network forbidden in isolated test")

    sys.addaudithook(audit)
    import psycopg

    def deny_postgres(*args, **kwargs):
        counts["postgres_attempts"] += 1
        raise RuntimeError("PostgreSQL forbidden")

    psycopg.connect = deny_postgres
    psycopg.Connection.connect = deny_postgres
    psycopg.AsyncConnection.connect = deny_postgres
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    with sqlite3.connect(root / "bootstrap.sqlite3") as conn:
        conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO meta VALUES('excel_seeded','synthetic-vr3')")
    import app as application
    import test_vendor_roster_service as fixture
    from services import vendor_access_service as access
    from services import vendor_roster_service as roster
    from services import vendor_scope_admin_service as service
    from unittest.mock import patch

    base = root / "bootstrap.sqlite3"
    with sqlite3.connect(base) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        fixture.seed_protected_rows(conn)
        roster.initialize_schema(conn)
        vendors = roster.apply_roster(conn, fixture.roster())["vendor_ids"]
        vendor, other = vendors["00252579"], vendors["96769654"]
        conn.execute("INSERT INTO users(id,username,password_hash,role) VALUES(601,'global-admin','synthetic','admin')")
        conn.executemany("INSERT INTO vendor_accounts(id,username,password_hash,vendor_name,is_active) VALUES(?,?,?,'same untrusted name',0)",
                         [(602, "pending-account", "SECRET-PASSWORD-HASH"), (603, "other-pending", "SECRET-PASSWORD-HASH")])
        for task, vid in ((301, vendor), (302, vendor), (303, vendor), (304, other), (305, vendor)):
            conn.execute("INSERT INTO task_vendor_assignments VALUES(?,?,'fixture','explicit_name_exact_trim','{}')", (task, vid))
        assert application._vendor_organization_schema_state(conn) == "all_exact"
    app = application.app
    app.config.update(TESTING=True, SECRET_KEY="synthetic-vr3-session-key")
    admin = access.InternalActor(601)
    core_state = application._vendor_organization_schema_state

    def stable_rows(conn):
        # The accepted helper sorts repr(row); sqlite3.Row repr contains object
        # addresses. Normalize to values BEFORE sorting, preserving all columns.
        return {name: sorted((tuple(row) for row in rows), key=repr)
                for name, rows in fixture.snapshot(conn).items()}

    class FlaskBehaviorTests(unittest.TestCase):
        def setUp(self):
            self.path = root / ("case-" + uuid.uuid4().hex + ".sqlite3")
            shutil.copyfile(base, self.path)
            application.DB_PATH = self.path
            self.client = app.test_client()
            self.login()
            self.initial = self.snapshot()

        def login(self, client=None, **values):
            with (client or self.client).session_transaction() as s:
                s.clear()
                s.update(user_id=601, username="global-admin", role="admin", current_site_id=102,
                         current_site_name="工地乙")
                s.update(values)

        def connect(self):
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        def sql(self, sql, params=()):
            with self.connect() as conn:
                conn.execute(sql, params)

        def snapshot(self):
            with self.connect() as conn:
                return {"schema": [tuple(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")],
                        "rows": stable_rows(conn)}

        def get(self, client=None, account=602, vid=None):
            return (client or self.client).get("/admin/vendor-scopes", query_string={"vendor_id": vid or vendor, "account_id": account})

        def form(self, scopes=None, client=None, account=602, vid=None):
            response = self.get(client, account, vid)
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            form = FormParser(response.get_data(as_text=True)).form
            self.assertIn("snapshot", form)
            for key in list(form):
                if key.startswith(("enabled.", "task.")):
                    del form[key]
            form["reason"] = "管理者確認待開通範圍"
            if "confirm_membership" in response.get_data(as_text=True):
                form["confirm_membership"] = "1"
            for sid, mode, tasks in ([] if scopes is None else scopes):
                form["enabled." + str(sid)] = "1"
                form["mode." + str(sid)] = mode
                form.setlist("task." + str(sid), [str(t) for t in tasks])
            return form

        def post(self, form, client=None):
            return (client or self.client).post("/admin/vendor-scopes", data=form)

        def saved(self, scopes=None):
            form = self.form([(101, "ALL", [])] if scopes is None else scopes)
            response = self.post(form)
            self.assertEqual(response.status_code, 303, response.get_data(as_text=True))
            return form

        def reject(self, form, code=400, client=None):
            before = self.snapshot()
            response = self.post(form, client)
            self.assertEqual(response.status_code, code, response.get_data(as_text=True))
            self.assertEqual(self.snapshot(), before)
            return response

        def preview(self):
            with self.connect() as conn:
                mid = conn.execute("SELECT vendor_membership_id FROM vendor_organization_memberships WHERE vendor_account_id=602").fetchone()[0]
                return access.preview_scopes(conn, actor=admin, membership_id=mid)

        def test_actual_route_navigation_get_is_read_only_and_first_unchecked(self):
            raw = self.path.read_bytes()
            response = self.client.get("/admin/vendor-scopes")
            self.assertEqual(response.status_code, 200)
            self.assertIn("00252579", response.get_data(as_text=True))
            self.assertNotIn("SECRET-PASSWORD-HASH", response.get_data(as_text=True))
            form = FormParser(self.get().get_data(as_text=True)).form
            self.assertFalse(any(k.startswith("enabled.") for k in form))
            self.assertTrue(all(value == "ALL" for key, value in form.items() if key.startswith("mode.")))
            self.assertEqual(raw, self.path.read_bytes())
            self.assertEqual(self.snapshot(), self.initial)
            navigation = self.client.get("/admin/users")
            self.assertEqual(navigation.status_code, 200)
            self.assertIn('href="/admin/vendor-scopes"', navigation.get_data(as_text=True))
            self.assertIn("vendor_scope_admin.index", app.view_functions)
            (root.parent / "vr3-initial.html").write_bytes(response.data)

        def test_first_save_prepares_relations_provenance_and_remains_pending(self):
            self.saved()
            with self.connect() as conn:
                self.assertEqual(core_state(conn), "all_exact")
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(conn.execute("SELECT is_active FROM vendor_accounts WHERE id=602").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT organization_status FROM vendor_organizations WHERE vendor_id=?", (vendor,)).fetchone()[0], "disabled")
                m = conn.execute("SELECT * FROM vendor_organization_memberships WHERE vendor_account_id=602").fetchone()
                self.assertEqual((m["membership_status"], m["membership_role"], m["predecessor_membership_id"]), ("pending", "member", None))
                for table in ("vendor_organization_memberships", "vendor_site_assignments", "sheet_vendor_bindings"):
                    rows = conn.execute("SELECT * FROM " + table + " WHERE vendor_id=?", (vendor,)).fetchall()
                    self.assertTrue(rows)
                    for row in rows:
                        for prefix in ("created", "updated"):
                            self.assertEqual(row[prefix + "_actor_kind"], "internal_user")
                            self.assertEqual(row[prefix + "_actor_id"], "601")
                            self.assertEqual(row[prefix + "_reason"], "管理者確認待開通範圍")
                            self.assertEqual(row[prefix + "_source"], "004F-VR3/vendor_scope_admin")
                            self.assertEqual(uuid.UUID(row[prefix + "_correlation_id"]).version, 4)
                self.assertEqual(access.resolve_scope(conn, vendor_account_id=602)["task_count"], 0)
            preview = self.preview()
            self.assertEqual(preview["revision"], 1)
            self.assertEqual(preview["configured_scope"]["task_count"], 3)
            self.assertEqual(preview["effective_scope"]["task_count"], 0)
            html = self.get().get_data(as_text=True)
            self.assertIn("待開通，尚未生效", html)
            self.assertIn('name="enabled.101" value="1" checked', html)
            self.assertNotIn("啟用帳號</button>", html)
            (root.parent / "vr3-saved.html").write_text(html, encoding="utf-8")
            after = self.snapshot()["rows"]
            changed = {"vendor_organization_memberships", "vendor_site_assignments", "sheet_vendor_bindings"}
            for table, rows in self.initial["rows"].items():
                if table not in changed:
                    self.assertEqual(after[table], rows, table)
            with self.client.session_transaction() as s:
                self.assertEqual(s["current_site_id"], 102)

        def test_same_request_retry_and_identical_fresh_save_do_not_write(self):
            form = self.saved()
            before = self.snapshot()
            self.assertEqual(self.post(form).status_code, 303)
            self.assertEqual(self.snapshot(), before)
            self.saved()
            self.assertEqual(self.snapshot(), before)
            form["reason"] = "changed request"
            self.reject(form, 409)

        def test_all_selected_empty_remove_and_clear_preserve_shared_links(self):
            self.saved([(101, "ALL", []), (102, "ALL", [])])
            self.assertEqual(self.preview()["configured_scope"]["task_count"], 4)
            with self.connect() as conn:
                links = {t: [tuple(r) for r in conn.execute("SELECT * FROM " + t)] for t in ("vendor_site_assignments", "sheet_vendor_bindings")}
            self.saved([(101, "SELECTED", [301, 305])])
            self.assertEqual(self.preview()["configured_scope"]["task_count"], 2)
            self.saved([(101, "SELECTED", [])])
            self.assertEqual(self.preview()["configured_scope"]["task_count"], 0)
            self.assertEqual(self.preview()["configured_scopes"][0]["mode"], "SELECTED")
            self.saved([])
            self.assertEqual(self.preview()["configured_scopes"], [])
            with self.connect() as conn:
                for table, rows in links.items():
                    self.assertEqual([tuple(r) for r in conn.execute("SELECT * FROM " + table)], rows)

        def test_all_dynamic_tasks_in_existing_qualified_sheets_only(self):
            self.saved()
            self.sql("INSERT INTO tasks(id,sheet_id,col_index,name,vendor) VALUES(401,201,401,'new','irrelevant')")
            self.sql("INSERT INTO task_vendor_assignments VALUES(401,?,'explicit','explicit_name_exact_trim','{}')", (vendor,))
            self.assertEqual(self.preview()["configured_scope"]["task_count"], 4)
            with self.connect() as conn:
                self.assertEqual(access.resolve_scope(conn, vendor_account_id=602)["task_count"], 0)

        def test_cross_vendor_site_and_unassigned_task_rejected(self):
            for task in (304, 303, 307, 99999):
                with self.subTest(task=task):
                    self.reject(self.form([(101, "SELECTED", [task])]))

        def test_malformed_duplicate_missing_and_unchecked_payloads(self):
            valid = self.form([(101, "SELECTED", [301])])
            variants = []
            for key in ("scope_set_complete", "site_row", "mode.101", "tasks_present.101", "reason", "confirm_membership"):
                f = valid.copy(); del f[key]; variants.append(f)
            for key, value in (("mode.101", "selected"), ("reason", "  "), ("reason", "x" * 501),
                               ("task.101", "true"), ("task.101", "0301"), ("task.101", "0"),
                               ("actor_id", "601"), ("account_id", "603"), ("vendor_id", other)):
                f = valid.copy(); f[key] = value; variants.append(f)
            for key in ("site_row", "task.101", "mode.101", "account_id"):
                f = valid.copy(); f.add(key, f[key]); variants.append(f)
            f = valid.copy(); del f["enabled.101"]; variants.append(f)
            f = valid.copy(); f["mode.101"] = "ALL"; variants.append(f)
            for index, form in enumerate(variants):
                with self.subTest(index=index):
                    self.reject(form)

        def test_form_error_keeps_reason_and_selections_escaped(self):
            form = self.form([(101, "SELECTED", [301])])
            form["reason"] = '<script>alert("x")</script>'
            form["actor_id"] = "bad"
            response = self.reject(form)
            html = response.get_data(as_text=True)
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn('<script>alert("x")</script>', html)
            self.assertIn('value="301" checked', html)

        def test_current_admin_role_not_session_role(self):
            self.login(role="member")
            self.assertEqual(self.get().status_code, 200)
            form = self.form([(101, "ALL", [])])
            self.sql("UPDATE users SET role='member' WHERE id=601")
            self.assertEqual(self.get().status_code, 403)
            self.reject(form, 403)

        def test_deleted_internal_user_is_denied(self):
            form = self.form([(101, "ALL", [])])
            self.sql("DELETE FROM users WHERE id=601")
            self.assertEqual(self.get().status_code, 403)
            self.reject(form, 403)

        def test_vendor_mixed_invalid_and_site_admin_sessions_no_details(self):
            identities = [{"user_id": 101, "role": "admin"}, {"user_id": True}, {"user_id": "601"},
                          {"vendor_account_id": None}, {"vendor_username": ""}, {"vendor_name": ""},
                          {"identity_type": "vendor"}, {"user_id": None, "vendor_account_id": 601}]
            for identity in identities:
                with self.subTest(identity=identity):
                    self.login(**identity)
                    before = self.snapshot()
                    response = self.get()
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn("pending-account", response.get_data(as_text=True))
                    self.assertNotIn("浤淋", response.get_data(as_text=True))
                    self.assertEqual(before, self.snapshot())

        def test_csrf_and_signed_actor_binding(self):
            form = self.form([(101, "ALL", [])])
            wrong = form.copy(); wrong["csrf_token"] = "forged"; self.reject(wrong, 403)
            wrong = form.copy(); wrong["csrf_token"] = "測試"; self.reject(wrong, 403)
            wrong = form.copy(); del wrong["csrf_token"]; self.reject(wrong, 403)
            wrong = form.copy(); wrong.add("csrf_token", form["csrf_token"]); self.reject(wrong, 403)
            wrong = form.copy(); wrong["snapshot"] += "tampered"; self.reject(wrong, 409)
            self.sql("INSERT INTO users(id,username,password_hash,role) VALUES(602,'second-admin','synthetic','admin')")
            with self.client.session_transaction() as s:
                s["user_id"] = 602
            self.reject(form, 403)

        def test_snapshot_expiry_is_conflict_without_writes(self):
            from itsdangerous import URLSafeTimedSerializer
            import time
            form = self.form([(101, "ALL", [])])
            signer = URLSafeTimedSerializer(app.secret_key, salt="004f-vr3-pending-editor-v1")
            bound = signer.loads(form["snapshot"])
            with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=int(time.time()) - 1801):
                form["snapshot"] = signer.dumps(bound)
            self.reject(form, 409)

        def test_activation_after_get_rejects_account_or_org(self):
            for sql, params in (("UPDATE vendor_accounts SET is_active=1 WHERE id=602", ()),
                                ("UPDATE vendor_organizations SET organization_status='active' WHERE vendor_id=?", (vendor,))):
                form = self.form([(101, "ALL", [])])
                self.sql(sql, params)
                self.reject(form, 409)
                html = self.get().get_data(as_text=True)
                self.assertNotIn('id="pending-scope-form"', html)
                self.sql("UPDATE vendor_accounts SET is_active=0 WHERE id=602")
                self.sql("UPDATE vendor_organizations SET organization_status='disabled' WHERE vendor_id=?", (vendor,))

        def test_membership_history_other_vendor_revoked_active_are_blocked(self):
            for vid, status in ((other, "pending"), (vendor, "revoked"), (vendor, "active")):
                mid = str(uuid.uuid4())
                with self.connect() as conn:
                    fixture.audited_insert(conn, "vendor_organization_memberships", {
                        "vendor_membership_id": mid, "vendor_id": vid, "vendor_account_id": 602,
                        "membership_role": "member", "membership_status": status})
                before = self.snapshot()
                response = self.get()
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('id="pending-scope-form"', response.get_data(as_text=True))
                self.assertEqual(self.snapshot(), before)
                self.sql("DELETE FROM vendor_organization_memberships WHERE vendor_membership_id=?", (mid,))

        def test_existing_pending_owner_and_links_reused_without_role_change(self):
            mid = str(uuid.uuid4())
            with self.connect() as conn:
                fixture.audited_insert(conn, "vendor_organization_memberships", {
                    "vendor_membership_id": mid, "vendor_id": vendor, "vendor_account_id": 602,
                    "membership_role": "owner", "membership_status": "pending"})
            self.saved()
            self.saved([(101, "SELECTED", [301])])
            with self.connect() as conn:
                self.assertEqual([tuple(r) for r in conn.execute("SELECT vendor_membership_id,membership_role,membership_status FROM vendor_organization_memberships WHERE vendor_account_id=602")], [(mid, "owner", "pending")])

        def test_inactive_assignment_history_rejects_without_revival(self):
            with self.connect() as conn:
                fixture.audited_insert(conn, "vendor_site_assignments", {
                    "vendor_site_assignment_id": str(uuid.uuid4()), "vendor_id": vendor,
                    "site_id": 101, "assignment_status": "inactive"})
            self.reject(self.form([(101, "ALL", [])]))

        def test_inactive_binding_history_rejects(self):
            self.saved()
            self.sql("UPDATE sheet_vendor_bindings SET binding_status='inactive' WHERE vendor_id=? AND sheet_id=201", (vendor,))
            before = self.snapshot()
            response = self.get()
            self.assertNotIn('id="pending-scope-form"', response.get_data(as_text=True))
            self.assertEqual(before, self.snapshot())

        def test_binding_cross_site_mismatch_rejects_old_snapshot(self):
            self.saved()
            form = self.form([(101, "ALL", [])])
            self.sql("UPDATE sheet_vendor_bindings SET site_id=102 WHERE vendor_id=? AND sheet_id=201", (vendor,))
            self.reject(form, 409)

        def test_stale_revision_cannot_overwrite_new_scopes(self):
            self.saved()
            old = self.form([(101, "SELECTED", [301])])
            self.saved([(101, "SELECTED", [302])])
            self.reject(old, 409)
            self.assertEqual(self.preview()["configured_scopes"][0]["task_ids"], [302])

        def test_concurrent_first_creation_two_clients_has_single_winner(self):
            other_client = app.test_client(); self.login(other_client)
            first = self.form([(101, "ALL", [])])
            second = self.form([(102, "ALL", [])], client=other_client)
            self.assertEqual(self.post(first).status_code, 303)
            self.reject(second, 409, other_client)
            with self.connect() as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM vendor_organization_memberships WHERE vendor_account_id=602").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT count(*) FROM vr2_scope_events").fetchone()[0], 1)

        def test_membership_change_and_assignment_replacement_stale(self):
            self.saved()
            form = self.form([(101, "ALL", [])])
            self.sql("UPDATE vendor_organization_memberships SET membership_status='revoked' WHERE vendor_account_id=602")
            self.reject(form, 409)

        def test_simultaneous_first_posts_serialize_with_one_winner(self):
            from concurrent.futures import ThreadPoolExecutor
            import threading
            second_client = app.test_client(); self.login(second_client)
            first = self.form([(101, "ALL", [])])
            second = self.form([(102, "ALL", [])], client=second_client)
            barrier = threading.Barrier(2)
            def submit(client, form):
                barrier.wait(timeout=10)
                return self.post(form, client).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(submit, self.client, first)
                b = pool.submit(submit, second_client, second)
                self.assertEqual(sorted([a.result(timeout=15), b.result(timeout=15)]), [303, 409])
            with self.connect() as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM vendor_organization_memberships WHERE vendor_account_id=602").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT count(*) FROM vr2_scope_events").fetchone()[0], 1)

        def test_cross_identity_successor_histories_are_bound_and_rejected(self):
            self.saved()
            for kind in ("membership", "assignment", "binding"):
                form = self.form([(101, "ALL", [])])
                rid = str(uuid.uuid4())
                with self.connect() as conn:
                    if kind == "membership":
                        table, key = "vendor_organization_memberships", "vendor_membership_id"
                        previous = conn.execute("SELECT vendor_membership_id FROM vendor_organization_memberships WHERE vendor_account_id=602").fetchone()[0]
                        fields = {key: rid, "vendor_id": other, "vendor_account_id": 603,
                                  "membership_status": "pending", "membership_role": "member", "predecessor_membership_id": previous}
                    elif kind == "assignment":
                        table, key = "vendor_site_assignments", "vendor_site_assignment_id"
                        previous = conn.execute("SELECT vendor_site_assignment_id FROM vendor_site_assignments WHERE vendor_id=?", (vendor,)).fetchone()[0]
                        fields = {key: rid, "vendor_id": other, "site_id": 102,
                                  "assignment_status": "active", "predecessor_assignment_id": previous}
                    else:
                        table, key = "sheet_vendor_bindings", "sheet_vendor_binding_id"
                        previous = conn.execute("SELECT sheet_vendor_binding_id FROM sheet_vendor_bindings WHERE vendor_id=? AND sheet_id=201", (vendor,)).fetchone()[0]
                        fields = {key: rid, "vendor_id": other, "site_id": 101, "sheet_id": 202,
                                  "vendor_site_assignment_id": fixture.OLD_SITE_LINK,
                                  "binding_status": "active", "predecessor_binding_id": previous}
                    fixture.audited_insert(conn, table, fields)
                with self.subTest(kind=kind):
                    self.reject(form, 409)
                    self.assertNotIn('id="pending-scope-form"', self.get().get_data(as_text=True))
                self.sql("DELETE FROM " + table + " WHERE " + key + "=?", (rid,))
            self.sql("UPDATE vendor_organization_memberships SET membership_status='pending' WHERE vendor_account_id=602")
            form = self.form([(101, "ALL", [])])
            self.sql("UPDATE vendor_site_assignments SET assignment_status='inactive' WHERE vendor_id=? AND site_id=101", (vendor,))
            with self.connect() as conn:
                fixture.audited_insert(conn, "vendor_site_assignments", {
                    "vendor_site_assignment_id": str(uuid.uuid4()), "vendor_id": vendor,
                    "site_id": 101, "assignment_status": "active"})
            self.reject(form, 409)

        def test_old_selected_task_moved_or_reassigned_not_silently_removed(self):
            self.saved([(101, "SELECTED", [301])])
            form = self.form([(101, "SELECTED", [301])])
            self.sql("UPDATE tasks SET sheet_id=203 WHERE id=301")
            response = self.reject(form, 409)
            self.assertIn("本次輸入未保存", response.get_data(as_text=True))
            self.assertNotIn('id="pending-scope-form"', self.get().get_data(as_text=True))
            self.sql("UPDATE tasks SET sheet_id=201 WHERE id=301")
            form = self.form([(101, "SELECTED", [301])])
            self.sql("UPDATE task_vendor_assignments SET vendor_id=? WHERE task_id=301", (other,))
            self.reject(form, 409)

        def test_partial_and_incompatible_vr2_schema_are_prerequisite_failures(self):
            form = self.form([(101, "ALL", [])])
            self.sql("CREATE TABLE vr2_scope_versions(dummy TEXT)")
            self.assertEqual(self.get().status_code, 503)
            self.reject(form, 503)
            self.sql("DROP TABLE vr2_scope_versions")
            self.saved()
            form = self.form([(101, "ALL", [])])
            self.sql("ALTER TABLE vr2_scope_events ADD COLUMN unexpected TEXT")
            self.assertEqual(self.get().status_code, 503)
            self.reject(form, 503)

        def test_missing_vr1_or_core_schema_does_not_initialize(self):
            for table in ("task_vendor_assignments", "vendor_profiles"):
                # A new independent fixture for each destructive test setup.
                shutil.copyfile(base, self.path)
                form = self.form([(101, "ALL", [])])
                with sqlite3.connect(self.path) as conn:
                    conn.execute("PRAGMA foreign_keys=OFF")
                    conn.execute("DROP TABLE " + table)
                self.assertEqual(self.get().status_code, 503)
                self.reject(form, 503)
            shutil.copyfile(base, self.path)
            form = self.form([(101, "ALL", [])])
            self.sql("ALTER TABLE vendor_site_assignments ADD COLUMN unexpected TEXT")
            self.assertEqual(self.get().status_code, 503)
            self.reject(form, 503)

        def test_injected_failure_after_relationships_rolls_back_ddl_and_all_rows(self):
            form = self.form([(101, "ALL", [])])
            def fail(*args, **kwargs):
                conn = args[0]
                self.assertTrue(conn.execute("SELECT 1 FROM vendor_organization_memberships WHERE vendor_account_id=602").fetchone())
                self.assertTrue(conn.execute("SELECT 1 FROM sheet_vendor_bindings WHERE vendor_id=?", (vendor,)).fetchone())
                raise sqlite3.OperationalError("synthetic failure after relationships")
            with patch.object(access, "save_scopes", side_effect=fail):
                self.reject(form, 503)
            with self.connect() as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM sqlite_schema WHERE name LIKE 'vr2_%'").fetchone()[0], 0)

        def test_failure_after_scope_event_rolls_back_everything(self):
            form = self.form([(101, "ALL", [])])
            original = access.save_scopes
            def fail(*args, **kwargs):
                original(*args, **kwargs)
                raise sqlite3.OperationalError("synthetic failure after event")
            with patch.object(access, "save_scopes", side_effect=fail):
                self.reject(form, 503)

        def test_service_savepoint_preserves_callers_prior_work(self):
            with self.connect() as conn:
                conn.execute("BEGIN")
                conn.execute("INSERT INTO meta VALUES('caller-marker','keep')")
                edit = service.editor(conn, actor=admin, vendor_id=vendor, account_id=602, core_state=core_state)
                before = stable_rows(conn)
                with patch.object(access, "save_scopes", side_effect=sqlite3.OperationalError("injected")):
                    with self.assertRaises(sqlite3.OperationalError):
                        service.save_pending(conn, actor=admin, vendor_id=vendor, account_id=602,
                            expected_fingerprint=edit["fingerprint"], scopes=[{"site_id": 101, "mode": "ALL", "task_ids": []}],
                            reason="test", confirm_membership=True, core_state=core_state)
                self.assertEqual(stable_rows(conn), before)
                self.assertTrue(conn.in_transaction)
                conn.rollback()

        def test_public_management_queries_use_current_admin_and_exact_intersection(self):
            self.saved()
            with self.connect() as conn:
                before = stable_rows(conn)
                self.assertEqual(access.admin_schema_state(conn, actor=admin), "ready")
                tasks = access.list_admin_eligible_tasks(conn, actor=admin, vendor_id=vendor, site_id=101)
                self.assertEqual({t["task_id"] for t in tasks}, {301, 302, 305})
                self.assertEqual(stable_rows(conn), before)
                with self.assertRaises(access.ScopeError):
                    access.list_admin_eligible_tasks(conn, actor=access.InternalActor(101), vendor_id=vendor, site_id=101)

        def test_malicious_labels_are_escaped_and_eight_digits_preserved(self):
            self.sql("UPDATE vendor_accounts SET username='<img src=x onerror=alert(1)>' WHERE id=602")
            self.sql("UPDATE tasks SET name='<script>task</script>' WHERE id=301")
            self.sql("UPDATE sheets SET name='<b>sheet</b>' WHERE id=201")
            self.sql("UPDATE vendor_profiles SET legal_name='<svg onload=alert(1)>' WHERE vendor_id=?", (vendor,))
            html = self.get().get_data(as_text=True)
            for unsafe, safe in (("<img src=x", "&lt;img src=x"), ("<script>task", "&lt;script&gt;task"),
                                 ("<b>sheet", "&lt;b&gt;sheet"), ("<svg onload", "&lt;svg onload")):
                self.assertNotIn(unsafe, html); self.assertIn(safe, html)
            self.assertIn("00252579", html)

        def test_no_pending_accounts_empty_state_is_truthful(self):
            self.sql("UPDATE vendor_accounts SET is_active=1")
            before = self.snapshot()
            response = self.client.get("/admin/vendor-scopes")
            self.assertEqual(response.status_code, 200)
            self.assertIn("尚無待開通帳號", response.get_data(as_text=True))
            self.assertEqual(before, self.snapshot())

        def test_missing_database_is_not_created(self):
            missing = root / "must-not-create.sqlite3"
            application.DB_PATH = missing
            response = self.client.get("/admin/vendor-scopes")
            self.assertEqual(response.status_code, 503)
            self.assertFalse(missing.exists())

        def test_service_rejects_non_admin_or_no_transaction_or_fk(self):
            with self.connect() as conn:
                with self.assertRaises(service.AdminError):
                    service.catalog(conn, actor=admin, core_state=core_state)
                conn.execute("BEGIN")
                for actor in (601, access.InternalActor(True), access.InternalActor(101)):
                    with self.assertRaises(service.AdminError):
                        service.catalog(conn, actor=actor, core_state=core_state)
                conn.rollback()
                conn.execute("PRAGMA foreign_keys=OFF"); conn.execute("BEGIN")
                with self.assertRaises(service.AdminError):
                    service.catalog(conn, actor=admin, core_state=core_state)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FlaskBehaviorTests))
    print(json.dumps({"vr3_child_tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                      "isolated_before_app_import": True, "network": "DENIED", "external_backends": "DISABLED",
                      "visual_browser": "NOT_RUN", **counts}, sort_keys=True))
    return result.wasSuccessful()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        sys.exit(0 if child_suite(Path(sys.argv[2])) else 1)
    unittest.main()
