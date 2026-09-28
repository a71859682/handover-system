"""VR4 real Flask tests, isolated BEFORE app import; no existing DB/network.

Set VR4_TEST_ROOT to a newly created directory below the operation root. The
discover process never imports app. Child stdout/stderr are preserved verbatim.
"""

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
import os
import secrets
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import traceback
import unittest
import uuid
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

REPO = Path(__file__).resolve().parents[1]
FLAGS = ("USE_SQLALCHEMY_READS", "USE_SQLALCHEMY_WRITES", "USERS_READ_COMPARE",
         "DUAL_WRITE_ENABLED", "DUAL_WRITE_DRY_RUN", "DUAL_WRITE_STRICT")


class VendorRegistrationIsolationTests(unittest.TestCase):
    def test_isolated_registration_suite(self):
        root = Path(os.environ["VR4_TEST_ROOT"]).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="vr4-flask-", dir=root) as child_root:
            env = os.environ.copy()
            env.update({flag: "false" for flag in FLAGS})
            env.update(APP_DB_PATH=str(Path(child_root) / "bootstrap.sqlite3"), DATABASE_URL="",
                       DUAL_WRITE_TABLES="", PYTHONDONTWRITEBYTECODE="1")
            argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", child_root]
            result = subprocess.run(argv, cwd=REPO, env=env, capture_output=True)
            (root / "vr4-child.stdout").write_bytes(result.stdout)
            (root / "vr4-child.stderr").write_bytes(result.stderr)
            (root / "vr4-child.json").write_text(json.dumps({"argv": argv, "cwd": str(REPO),
                "exit": result.returncode, "VR4_TEST_FILTER": env.get("VR4_TEST_FILTER")}), encoding="utf-8")
            if (Path(child_root) / "responses").exists():
                shutil.copytree(Path(child_root) / "responses", root / "responses")
            sys.stdout.buffer.write(result.stdout)
            sys.stderr.buffer.write(result.stderr)
            self.assertEqual(result.returncode, 0, "isolated child failed; see original streams")


class RegistrationForm(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.inputs = {}
        self.selects = {}
        self.buttons = []
        self.labels = []
        self.option = None
        self.select = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and "name" in attrs:
            self.inputs[attrs["name"]] = attrs
        if tag == "select":
            self.select = attrs["name"]
            self.selects[self.select] = dict(attrs=attrs, options=[])
        if tag == "option" and self.select:
            self.option = dict(attrs=attrs, text="")
            self.selects[self.select]["options"].append(self.option)
        if tag == "button":
            self.buttons.append(attrs)
        if tag == "label":
            self.labels.append(attrs)

    def handle_data(self, data):
        if self.option is not None:
            self.option["text"] += data

    def handle_endtag(self, tag):
        if tag == "option":
            self.option = None
        if tag == "select":
            self.select = None


def child_suite(root):
    if sys.flags.optimize:
        raise RuntimeError("Isolation assertions must be enabled")
    root = root.resolve(strict=True)
    assert not (root / "bootstrap.sqlite3").exists()
    assert Path(os.environ["APP_DB_PATH"]).resolve() == root / "bootstrap.sqlite3"
    assert os.environ.get("DATABASE_URL") == os.environ.get("DUAL_WRITE_TABLES") == ""
    assert all(os.environ.get(flag) == "false" for flag in FLAGS)
    counts = {"sqlite_outside_attempts": 0, "network_attempts": 0, "postgres_attempts": 0, "source_xlsx_attempts": 0}

    def audit(event, arguments):
        if event == "open" and isinstance(arguments[0], (str, bytes, os.PathLike)):
            if Path(os.fsdecode(arguments[0])).resolve() == REPO / "source.xlsx":
                counts["source_xlsx_attempts"] += 1
                raise RuntimeError("source.xlsx import forbidden")
        if event == "sqlite3.connect":
            raw = str(arguments[0])
            path = Path(url2pathname(unquote(urlsplit(raw).path)) if raw.startswith("file:") else raw).resolve()
            if not path.is_relative_to(root):
                counts["sqlite_outside_attempts"] += 1
                raise RuntimeError("non-fixture SQLite access")
        if event in {"socket.connect", "socket.getaddrinfo", "socket.bind", "socket.sendto"}:
            counts["network_attempts"] += 1
            raise RuntimeError("network forbidden")

    sys.addaudithook(audit)
    import psycopg

    def deny_postgres(*args, **kwargs):
        counts["postgres_attempts"] += 1
        raise RuntimeError("PostgreSQL forbidden")

    psycopg.connect = psycopg.Connection.connect = psycopg.AsyncConnection.connect = deny_postgres
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    base = root / "bootstrap.sqlite3"
    with sqlite3.connect(base) as conn:
        conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        conn.execute("INSERT INTO meta VALUES('excel_seeded','synthetic-vr4')")
    import app as application
    import test_vendor_roster_service as fixture
    from test_vendor_scope_admin import FormParser
    from services import vendor_roster_service as roster
    from services import vendor_registration_service as service
    from services import vendor_scope_admin_service as admin_service
    from services import vendor_access_service as access
    from unittest.mock import patch
    from werkzeug.datastructures import MultiDict
    from werkzeug.security import check_password_hash, generate_password_hash

    admin_password = secrets.token_urlsafe(36)
    with sqlite3.connect(base) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        fixture.seed_protected_rows(conn)
        roster.initialize_schema(conn)
        entries = [dict(tax_id=tax, legal_name=legal, display_name=display,
                        aliases=["PRIVATE_ALIAS_SENTINEL"], source=dict(document="PRIVATE_SOURCE_SENTINEL",
                        version="ux-r01", sheet="synthetic", source_original_name=legal, row=i))
                   for i, (tax, legal, display) in enumerate((
                       ("00000001", "合成甲有限公司", "合成甲"),
                       ("00000002", "合成乙有限公司", "合成乙")), 1)]
        vendors = roster.apply_roster(conn, entries)["vendor_ids"]
        vendor, other = vendors["00000001"], vendors["00000002"]
        conn.execute("UPDATE users SET password_hash=?,role='member' WHERE username='admin'",
                     (generate_password_hash(secrets.token_urlsafe(36)),))
        conn.execute("INSERT INTO users(id,username,password_hash,role) VALUES(701,'vr4-admin',?,'admin')",
                     (generate_password_hash(admin_password),))
        conn.execute("INSERT INTO vendor_accounts(id,username,password_hash,vendor_name,is_active) VALUES(702,'legacy-pending','synthetic','untrusted',0)")
        for task in (301, 302, 303):
            conn.execute("INSERT INTO task_vendor_assignments VALUES(?,?,'fixture','explicit_name_exact_trim','{}')", (task, other if task == 302 else vendor))
        assert application._vendor_organization_schema_state(conn) == "all_exact"
    app = application.app
    app.config.update(TESTING=True, SECRET_KEY=secrets.token_urlsafe(48))
    core_state = application._vendor_organization_schema_state
    actor = access.InternalActor(701)
    password = "  " + secrets.token_urlsafe(24) + "  "

    class RegistrationTests(unittest.TestCase):
        def setUp(self):
            self.reset()

        def reset(self):
            self.path = root / ("case-" + uuid.uuid4().hex + ".sqlite3")
            shutil.copyfile(base, self.path)
            application.DB_PATH = self.path
            self.client = app.test_client()

        def connect(self):
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        def sql(self, sql, parameters=()):
            with self.connect() as conn:
                conn.execute(sql, parameters)

        def snapshot(self):
            with self.connect() as conn:
                return {"schema": [tuple(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")],
                        "rows": {name: sorted((tuple(r) for r in rows), key=repr) for name, rows in fixture.snapshot(conn).items()}}

        def form(self, client=None, **changes):
            response = (client or self.client).get("/vendor/register")
            self.assertEqual(response.status_code, 200)
            fields = RegistrationForm(response.get_data(as_text=True)).inputs
            form = MultiDict({"vendor_id": vendor, "username": "new.vendor",
                              "password": password, "confirm_password": password, "csrf_token": fields["csrf_token"]["value"]})
            form.update(changes)
            for key, value in changes.items():
                form.setlist(key, [value])
            return form

        def post(self, form=None, client=None):
            return (client or self.client).post("/vendor/register", data=self.form() if form is None else form)

        def reject(self, form, code=400, client=None):
            before, raw = self.snapshot(), self.path.read_bytes()
            response = self.post(form, client)
            self.assertEqual(response.status_code, code, response.get_data(as_text=True))
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.path.read_bytes(), raw)
            html = response.get_data(as_text=True)
            self.assertNotIn(password, html)
            for key in ("password", "confirm_password"):
                self.assertNotIn("value", RegistrationForm(html).inputs.get(key, {}))
            return response

        def register(self, **changes):
            response = self.post(self.form(**changes))
            self.assertEqual(response.status_code, 303, response.get_data(as_text=True))
            with self.connect() as conn:
                return conn.execute("SELECT id FROM vendor_accounts WHERE username=?", (changes.get("username", "new.vendor").strip(),)).fetchone()[0]

        def admin(self, **markers):
            client = app.test_client()
            with client.session_transaction() as session:
                session.update(user_id=701, username="vr4-admin", role="admin", **markers)
            return client

        def editor(self, client, account, vid=vendor):
            response = client.get("/admin/vendor-scopes", query_string={"vendor_id": vid, "account_id": account})
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            return response, FormParser(response.get_data(as_text=True)).form

        def capture_response(self, label, response):
            if os.environ.get("VR4_CAPTURE_RESPONSES") == "1":
                target = root / "responses"
                target.mkdir(exist_ok=True)
                stem = self._testMethodName + "-" + label
                (target / (stem + ".json")).write_text(json.dumps({"status": response.status_code,
                    "content_type": response.content_type, "cache_control": response.headers.get("Cache-Control"),
                    "synthetic_only": True, "body_and_security_values_omitted": True}), encoding="utf-8")

        def invalid_admin_reason(self, client, form, label):
            form["reason"] = " \t "
            form["confirm_membership"] = "1"
            before, raw = self.snapshot(), self.path.read_bytes()
            response = client.post("/admin/vendor-scopes", data=form)
            self.capture_response(label, response)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.path.read_bytes(), raw)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            html = response.get_data(as_text=True)
            self.assertIn("請填寫 1–500 字的保存理由", html)
            returned = FormParser(html).form
            self.assertEqual(dict(returned.lists()), dict(form.lists()))
            return html, returned

        def test_admin_post400_preserves_target_request_and_mismatch(self):
            for selected_vendor in (other, vendor):
                with self.subTest(mismatch=selected_vendor == other):
                    self.reset()
                    account = self.register()
                    client = self.admin()
                    response, form = self.editor(client, account, selected_vendor)
                    label = "different" if selected_vendor == other else "same"
                    self.capture_response(label + "-get", response)
                    with self.connect() as conn:
                        request_before = tuple(conn.execute("SELECT * FROM vendor_registration_requests WHERE account_id=?", (account,)).fetchone())
                    form["enabled.101"] = "1"
                    form["mode.101"] = "SELECTED"
                    if selected_vendor == vendor:
                        form.setlist("task.101", ["301"])
                    html, returned = self.invalid_admin_reason(client, form, label + "-400")
                    for page in (response.get_data(as_text=True), html):
                        self.assertIn('data-testid="registration-info"', page)
                        self.assertIn("申請人提供的公司歸屬，尚未核驗：合成甲有限公司／00000001", page)
                        self.assertIn("申請廠商 ID：" + vendor, page)
                        self.assertEqual("目前選定廠商與申請廠商不同" in page, selected_vendor == other)
                        self.assertNotIn("此帳號無本片申請資料", page)
                    self.assertEqual(returned["vendor_id"], selected_vendor)
                    self.assertEqual(returned["account_id"], str(account))
                    returned["reason"] = "人工核對實際歸屬"
                    saved = client.post("/admin/vendor-scopes", data=returned)
                    self.capture_response(label + "-saved", saved)
                    self.assertEqual(saved.status_code, 303)
                    self.capture_response(label + "-after", client.get(saved.location))
                    with self.connect() as conn:
                        member = conn.execute("SELECT * FROM vendor_organization_memberships WHERE vendor_account_id=?", (account,)).fetchone()
                        self.assertEqual((member["vendor_id"], member["membership_role"], member["membership_status"]),
                                         (selected_vendor, "member", "pending"))
                        self.assertEqual(conn.execute("SELECT is_active FROM vendor_accounts WHERE id=?", (account,)).fetchone()[0], 0)
                        self.assertEqual(conn.execute("SELECT organization_status FROM vendor_organizations WHERE vendor_id=?", (selected_vendor,)).fetchone()[0], "disabled")
                        self.assertEqual(access.preview_scopes(conn, actor=actor, membership_id=member["vendor_membership_id"])["effective_scope"]["task_count"], 0)
                        self.assertEqual(tuple(conn.execute("SELECT * FROM vendor_registration_requests WHERE account_id=?", (account,)).fetchone()), request_before)

        def test_real_admin_login_selector_registration_and_post400_recovery(self):
            account = self.register()
            client = app.test_client()
            signed_in = client.post("/login", data={"username": "vr4-admin", "password": admin_password})
            self.assertEqual(signed_in.status_code, 302)
            with client.session_transaction() as logged_in:
                self.assertEqual(logged_in.get("user_id"), 701)
                self.assertEqual(logged_in.get("role"), "admin")
            response, form = self.editor(client, account, other)
            self.assertNotIn("confirm_membership", form)
            form["enabled.101"] = "1"
            form["mode.101"] = "SELECTED"
            form.setlist("task.101", ["302"])
            html, returned = self.invalid_admin_reason(client, form, "real-login-400")
            for page in (response.get_data(as_text=True), html):
                self.assertIn("目前選定廠商與申請廠商不同", page)
                self.assertIn("申請人提供的公司歸屬，尚未核驗：合成甲有限公司／00000001", page)
                self.assertIn("申請廠商 ID：" + vendor, page)
            self.assertEqual(returned["vendor_id"], other)
            self.assertEqual(returned["confirm_membership"], "1")
            self.assertEqual(returned.getlist("task.101"), ["302"])
            returned["reason"] = "管理員人工核對不同公司歸屬"
            self.assertEqual(client.post("/admin/vendor-scopes", data=returned).status_code, 303)
            with self.connect() as conn:
                member = conn.execute("SELECT * FROM vendor_organization_memberships WHERE vendor_account_id=?", (account,)).fetchone()
                self.assertEqual((member["vendor_id"], member["membership_role"], member["membership_status"]), (other, "member", "pending"))
                self.assertEqual(conn.execute("SELECT is_active FROM vendor_accounts WHERE id=?", (account,)).fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT organization_status FROM vendor_organizations WHERE vendor_id=?", (other,)).fetchone()[0], "disabled")
                scopes = access.preview_scopes(conn, actor=actor, membership_id=member["vendor_membership_id"])
                self.assertEqual(scopes["configured_scope"]["task_count"], 1)
                self.assertEqual(scopes["effective_scope"]["task_count"], 0)
                self.assertEqual(conn.execute("SELECT requested_vendor_id FROM vendor_registration_requests WHERE account_id=?", (account,)).fetchone()[0], vendor)

        def test_vendor_login_traditional_chinese_and_uniform_failures(self):
            self.register()
            with self.connect() as conn:
                conn.execute("INSERT INTO vendor_accounts(username,password_hash,vendor_name,is_active) VALUES(?,?,?,1)",
                             ("active.synthetic", generate_password_hash(password), "合成登入公司"))
            page = self.client.get("/vendor/login").get_data(as_text=True)
            for text in ("<title>廠商登入</title>", "<h1>廠商登入</h1>", "帳號", "密碼", ">登入<", "廠商申請帳號"):
                self.assertIn(text, page)
            failures = []
            before, raw = self.snapshot(), self.path.read_bytes()
            for username, supplied in (("active.synthetic", secrets.token_urlsafe(32)),
                                       ("unknown.synthetic", password), ("new.vendor", password)):
                client = app.test_client()
                response = client.post("/vendor/login", data={"username": username, "password": supplied})
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn("廠商帳號或密碼錯誤，或帳號尚未開通", html)
                failures.append(html)
                with client.session_transaction() as state:
                    self.assertFalse({"identity_type", "vendor_account_id", "user_id"}.intersection(state))
            self.assertTrue(failures[0] == failures[1] == failures[2])
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.path.read_bytes(), raw)
            client = app.test_client()
            self.assertEqual(client.post("/vendor/login", data={"username": "active.synthetic", "password": password}).status_code, 302)
            html = client.get("/vendor/login").get_data(as_text=True)
            self.assertIn("已登入廠商：", html)
            self.assertIn(">登出<", html)
            for english in ("Vendor Login", "Username", "Password", "Signed in as", ">Logout<", ">Login<", "Invalid vendor"):
                self.assertNotIn(english, page + html + failures[0])
            self.assertEqual(client.get("/vendor/logout").status_code, 302)

        def test_admin_post400_uses_only_target_request(self):
            account = self.register()
            second = self.register(username="second.vendor")
            self.sql("UPDATE vendor_registration_requests SET submitted_company_name='other-account-only',submitted_tax_id='12345678',requested_vendor_id=? WHERE account_id=?", (other, second))
            client = self.admin()
            _, form = self.editor(client, account)
            html, _ = self.invalid_admin_reason(client, form, "target-400")
            self.assertIn("申請人提供的公司歸屬，尚未核驗：合成甲有限公司／00000001", html)
            for unrelated in ("other-account-only", "12345678", "second.vendor", other):
                self.assertNotIn(unrelated, html)
            with self.connect() as conn:
                conn.execute("BEGIN")
                info = admin_service.editor(conn, actor=actor, vendor_id=vendor, account_id=account,
                                            core_state=core_state)["registration_info"]
                self.assertEqual(set(info), {"state", "request"})
                self.assertEqual(info["request"]["account_id"], account)

        def test_get_readonly_transaction_and_minimal_projection(self):
            from flask import template_rendered
            before, raw = self.snapshot(), self.path.read_bytes()
            opened, statements, projections = [], [], []
            real_connect = sqlite3.connect

            def connect(database, *args, **kwargs):
                opened.append((database, kwargs.get("uri")))
                conn = real_connect(database, *args, **kwargs)
                conn.set_trace_callback(statements.append)
                return conn

            def rendered(sender, template, context, **extra):
                projections.append(context["choices"])

            with patch("routes.vendor_registration.sqlite3.connect", connect):
                with template_rendered.connected_to(rendered, app):
                    response = self.client.get("/vendor/register")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(opened, [(self.path.resolve().as_uri() + "?mode=ro", True)])
            self.assertEqual(statements[:3], ["PRAGMA foreign_keys=ON", "PRAGMA query_only=ON", "BEGIN"])
            self.assertEqual(statements[-1], "ROLLBACK")
            self.assertFalse(any(sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER")) for sql in statements))
            self.assertTrue(all(set(p) == {"vendor_id", "display_name", "legal_name"} for p in projections[0]))
            self.assertEqual({p["vendor_id"] for p in projections[0]}, {vendor, other})
            html = response.get_data(as_text=True)
            for private in ("00000001", "00000002", "PRIVATE_ALIAS_SENTINEL", "PRIVATE_SOURCE_SENTINEL", "legacy-pending", "工地甲"):
                self.assertNotIn(private, html)
            parsed = RegistrationForm(html)
            select = parsed.selects["vendor_id"]
            self.assertIn({"for": "registration-company"}, parsed.labels)
            self.assertEqual(select["attrs"]["id"], "registration-company")
            self.assertIn("required", select["attrs"])
            self.assertEqual([o["attrs"]["value"] for o in select["options"] if "selected" in o["attrs"]], [""])
            self.assertEqual(select["options"][0]["text"], "請選擇公司")
            self.assertIn("合成甲（合成甲有限公司）", html)
            self.assertNotIn("company_name", parsed.inputs)
            self.assertNotIn("tax_id", parsed.inputs)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.path.read_bytes(), raw)

        def test_get_empty_missing_and_incompatible_roster(self):
            self.sql("UPDATE vendor_organizations SET organization_status='active'")
            before, raw = self.snapshot(), self.path.read_bytes()
            response = self.client.get("/vendor/register")
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("目前沒有可申請的公司", html)
            parsed = RegistrationForm(html)
            self.assertEqual(len(parsed.selects["vendor_id"]["options"]), 1)
            self.assertIn("disabled", parsed.selects["vendor_id"]["attrs"])
            self.assertIn("disabled", parsed.buttons[0])
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.path.read_bytes(), raw)
            self.reset()
            form = self.form()
            missing = root / ("missing-" + uuid.uuid4().hex + ".sqlite3")
            application.DB_PATH = missing
            self.assertEqual(self.client.get("/vendor/register").status_code, 503)
            self.assertEqual(self.post(form).status_code, 503)
            self.assertFalse(missing.exists())
            for statement in ("ALTER TABLE vendor_profiles RENAME COLUMN legal_name TO wrong_name",
                              "UPDATE vendor_organizations SET display_name='mismatch' WHERE vendor_id='" + vendor + "'",
                              "DROP TABLE task_vendor_assignments"):
                self.reset()
                self.sql(statement)
                before, raw = self.snapshot(), self.path.read_bytes()
                response = self.client.get("/vendor/register")
                self.assertEqual(response.status_code, 503)
                html = response.get_data(as_text=True)
                self.assertIn("公司名冊暫時無法讀取或資料不相容", html)
                self.assertNotIn("目前沒有可申請的公司", html)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.path.read_bytes(), raw)

        def test_get_escaped_duplicate_labels_and_disabled_only(self):
            label = '<script>合成同名</script>'
            self.sql("UPDATE vendor_profiles SET legal_name=?,display_name=?", (label, label))
            self.sql("UPDATE vendor_organizations SET display_name=? WHERE vendor_id IN (?,?)", (label, vendor, other))
            html = self.client.get("/vendor/register").get_data(as_text=True)
            self.assertNotIn(label, html)
            self.assertIn("&lt;script&gt;合成同名&lt;/script&gt;", html)
            options = RegistrationForm(html).selects["vendor_id"]["options"][1:]
            self.assertEqual(len(options), 2)
            for option in options:
                self.assertEqual(option["text"].count(label), 1)
                self.assertIn("識別：" + option["attrs"]["value"], option["text"])
            for status in ("active", "retired"):
                self.sql("UPDATE vendor_organizations SET organization_status=? WHERE vendor_id=?", (status, other))
                html = self.client.get("/vendor/register").get_data(as_text=True)
                self.assertNotIn(other, html)
                self.assertIn(vendor, html)

        def test_login_link_and_success_prg_private_receipt(self):
            self.assertIn('/vendor/register', self.client.get('/vendor/login').get_data(as_text=True))
            response = self.post()
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.location, "/vendor/register/success")
            page = self.client.get(response.location).get_data(as_text=True)
            self.assertIn("帳號已建立，待管理者確認，尚未開通", page)
            self.assertIn("00000001", page)
            self.assertNotIn(password, page)
            self.assertNotIn("scrypt:", page)
            self.assertEqual(app.test_client().get(response.location).status_code, 303)
            self.assertEqual(self.client.get(response.location + "?account_id=601").status_code, 400)
            with self.client.session_transaction() as session:
                self.assertEqual(set(session), {"vr4_csrf", "vr4_receipt"})
                self.assertEqual(set(session["vr4_receipt"]), {"username", "company_name", "tax_id"})

        def test_only_inactive_account_and_unverified_request_created(self):
            before = self.snapshot()["rows"]
            account = self.register(username=" new.vendor ")
            after = self.snapshot()["rows"]
            for table in before.keys() - {"vendor_accounts", "sqlite_sequence"}:
                self.assertEqual(before[table], after[table], table)
            with self.connect() as conn:
                row = conn.execute("SELECT * FROM vendor_accounts WHERE id=?", (account,)).fetchone()
                self.assertEqual(row["is_active"], 0)
                self.assertEqual(row["vendor_name"], "合成甲有限公司")
                self.assertTrue(check_password_hash(row["password_hash"], password))
                self.assertFalse(check_password_hash(row["password_hash"], password.strip()))
                req = conn.execute("SELECT * FROM vendor_registration_requests").fetchall()
                self.assertEqual(len(req), 1)
                self.assertEqual(tuple(req[0])[:4], (account, vendor, "合成甲有限公司", "00000001"))
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertIsNone(application.verify_vendor_account("new.vendor", password))
            self.client.post("/vendor/login", data={"username": "new.vendor", "password": password})
            with self.client.session_transaction() as session:
                self.assertFalse({"identity_type", "vendor_account_id", "user_id"}.intersection(session))

        def test_end_to_end_manual_confirmation_still_pending_zero_effective(self):
            account = self.register()
            client = self.admin()
            page, form = self.editor(client, account)
            html = page.get_data(as_text=True)
            self.assertIn("申請人提供的公司歸屬，尚未核驗", html)
            self.assertIn("00000001", html)
            self.assertNotIn("confirm_membership", form)
            self.assertFalse(any(k.startswith("enabled.") for k in form))
            form["reason"] = "人工核對本次申請"
            form["enabled.101"] = "1"
            form["mode.101"] = "SELECTED"
            form.setlist("task.101", ["301"])
            before = self.snapshot()
            self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 400)
            self.assertEqual(self.snapshot(), before)
            form["confirm_membership"] = "1"
            response = client.post("/admin/vendor-scopes", data=form)
            self.assertEqual(response.status_code, 303, response.get_data(as_text=True))
            with self.connect() as conn:
                member = conn.execute("SELECT * FROM vendor_organization_memberships WHERE vendor_account_id=?", (account,)).fetchone()
                self.assertEqual((member["membership_role"], member["membership_status"]), ("member", "pending"))
                self.assertEqual(conn.execute("SELECT is_active FROM vendor_accounts WHERE id=?", (account,)).fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT organization_status FROM vendor_organizations WHERE vendor_id=?", (vendor,)).fetchone()[0], "disabled")
                preview = access.preview_scopes(conn, actor=actor, membership_id=member["vendor_membership_id"])
                self.assertEqual(preview["configured_scope"]["task_count"], 1)
                self.assertEqual(preview["effective_scope"]["task_count"], 0)
            before = self.snapshot()
            self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 303)
            self.assertEqual(self.snapshot(), before)

        def test_company_tax_exact_pair_ascii_and_leading_zero(self):
            # The public selector changed; retain the internal canonical safety cases.
            canonical = dict(company_name="合成甲有限公司", tax_id="00000001", username="new.vendor",
                             password=password, confirm_password=password)
            for changes in ({"tax_id": "00000009"}, {"tax_id": "252579"}, {"tax_id": "０００００００１"},
                            {"tax_id": " 00000001"}, {"company_name": "合成甲"}, {"company_name": "合 成甲有限公司"},
                            {"company_name": "合成甲有限公司", "tax_id": "00000002"}, {"company_name": "甲" * 201}):
                before, raw = self.snapshot(), self.path.read_bytes()
                with self.connect() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    with self.assertRaises(service.RegistrationError):
                        service.register(conn, canonical | changes, core_state=core_state,
                                         registry_schema=application.IDENTITY_REGISTRY_SCHEMA_STATEMENTS)
                    conn.rollback()
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.path.read_bytes(), raw)
            self.assertEqual(service.validate(canonical | {"company_name": " \t合成甲有限公司\u3000"})[:2],
                             ("合成甲有限公司", "00000001"))

        def test_old_handwritten_shape_rejected_and_canonical_contract_retained(self):
            self.assertEqual(service.FIELDS, {"company_name", "tax_id", "username", "password", "confirm_password"})
            canonical = dict(company_name="合成甲有限公司", tax_id="00000001", username="new.vendor",
                             password=password, confirm_password=password)
            self.assertEqual(service.validate(canonical)[:3], ("合成甲有限公司", "00000001", "new.vendor"))
            for tax in ("252579", "０００００００１", " 00000001"):
                with self.assertRaises(service.RegistrationError):
                    service.validate(canonical | {"tax_id": tax})
            form = self.form()
            del form["vendor_id"]
            form.update({"company_name": "合成甲有限公司", "tax_id": "00000001"})
            self.reject(form)

        def test_blank_unknown_deleted_selection_and_error_retention(self):
            for value in ("", " ", str(uuid.uuid4()), '<script>invalid</script>'):
                response = self.reject(self.form(vendor_id=value))
                html = response.get_data(as_text=True)
                self.assertIn("請選擇公司" if not value.strip() else "請重新選擇公司", html)
                options = RegistrationForm(html).selects["vendor_id"]["options"]
                self.assertEqual([o["attrs"]["value"] for o in options if "selected" in o["attrs"]], [""])
            response = self.reject(self.form(username="invalid username"))
            parsed = RegistrationForm(response.get_data(as_text=True))
            self.assertEqual(parsed.inputs["username"]["value"], "invalid username")
            self.assertEqual([o["attrs"]["value"] for o in parsed.selects["vendor_id"]["options"] if "selected" in o["attrs"]], [vendor])
            form = self.form()
            self.sql("DELETE FROM task_vendor_assignments WHERE vendor_id=?", (vendor,))
            self.sql("DELETE FROM vendor_profiles WHERE vendor_id=?", (vendor,))
            response = self.reject(form)
            self.assertIn("請重新選擇公司", response.get_data(as_text=True))

        def test_post_uses_current_server_canonical_values(self):
            form = self.form()
            self.sql("UPDATE vendor_profiles SET legal_name='合成甲更名有限公司',tax_id='00000003' WHERE vendor_id=?", (vendor,))
            self.assertEqual(self.post(form).status_code, 303)
            with self.connect() as conn:
                row = conn.execute("SELECT requested_vendor_id,submitted_company_name,submitted_tax_id FROM vendor_registration_requests").fetchone()
                self.assertEqual(tuple(row), (vendor, "合成甲更名有限公司", "00000003"))
            page = self.client.get("/vendor/register/success").get_data(as_text=True)
            self.assertIn("合成甲更名有限公司", page)
            self.assertIn("00000003", page)
            self.assertIn("申請人提供的公司歸屬，尚未核驗", page)

        def test_company_status_rechecked_after_get(self):
            for state in ("active", "retired"):
                self.reset()
                form = self.form()
                self.sql("UPDATE vendor_organizations SET organization_status=? WHERE vendor_id=?", (state, vendor))
                response = self.reject(form)
                parsed = RegistrationForm(response.get_data(as_text=True))
                self.assertIn("請重新選擇公司", response.get_data(as_text=True))
                self.assertEqual([o["attrs"]["value"] for o in parsed.selects["vendor_id"]["options"] if "selected" in o["attrs"]], [""])

        def test_ambiguous_roster_rejected(self):
            original = roster.list_profiles
            def duplicate(conn):
                profiles = original(conn)
                return profiles + [p for p in profiles if p["tax_id"] == "00000001"]
            form = self.form()
            with patch.object(roster, "list_profiles", duplicate):
                self.reject(form, 503)

        def test_username_rules_and_boundaries(self):
            for name in ("abc", "1abc", "New.vendor", "a bcd", "ｎｅｗ.vendor", "a" * 65, "a/bcd", "abcd\x00"):
                with self.subTest(name=name):
                    self.reject(self.form(username=name))
            self.register(username="a" * 64)
            self.register(username="a._-")

        def test_password_limits_confirmation_and_not_trimmed(self):
            short = secrets.token_urlsafe(16)[:11]
            long = secrets.token_urlsafe(128)[:129]
            nul = short + "\x00"
            for value, confirmation in ((short, short), (long, long),
                                        (password, password.strip()), (nul, nul)):
                self.reject(self.form(password=value, confirm_password=confirmation))
            for length, name in ((12, "pass.minimum"), (128, "pass.maximum")):
                value = secrets.token_urlsafe(128)[:length]
                self.register(username=name, password=value, confirm_password=value)

        def test_missing_duplicate_extra_and_caller_identity_fields(self):
            for key in service.SELECTION_FIELDS:
                with self.subTest(missing=key):
                    form = self.form()
                    del form[key]
                    self.reject(form)
                with self.subTest(duplicate=key):
                    form = self.form()
                    form.add(key, form[key])
                    self.reject(form)
            for key in ("company_name", "tax_id", "account_id", "global_identity_id", "role", "is_active", "owner", "site_id"):
                form = self.form()
                form[key] = "1"
                self.reject(form)

        def test_csrf_missing_duplicate_wrong_and_cross_client(self):
            form = self.form()
            del form["csrf_token"]
            self.reject(form, 403)
            form = self.form()
            form.add("csrf_token", form["csrf_token"])
            self.reject(form, 403)
            self.reject(self.form(csrf_token="bad"), 403)
            self.reject(self.form(csrf_token="非ASCII"), 403)
            self.reject(self.form(), 403, app.test_client())

        def test_body_limit_and_query_or_file_fields(self):
            self.reject(self.form(username="x" * 20000), 413)
            form = self.form()
            before = self.snapshot()
            self.assertEqual(self.client.post("/vendor/register?role=admin", data=form).status_code, 400)
            import io
            form["upload"] = (io.BytesIO(b"synthetic"), "test.txt")
            self.assertIn(self.client.post("/vendor/register", data=form).status_code, (400, 413))
            self.assertEqual(self.snapshot(), before)

        def test_error_escaping_safe_fields_password_absent(self):
            payload = '<script>alert("x")</script>'
            response = self.reject(self.form(username=payload))
            html = response.get_data(as_text=True)
            self.assertNotIn(payload, html)
            self.assertIn("&lt;script&gt;", html)
            self.assertEqual(RegistrationForm(html).inputs["username"]["value"], payload)

        def test_invalid_safe_fields_are_not_silently_shortened(self):
            for key, value in (("username", "a" * 65),):
                response = self.reject(self.form(**{key: value}))
                self.assertEqual(RegistrationForm(response.get_data(as_text=True)).inputs[key]["value"], value)

        def test_internal_vendor_mixed_and_partial_sessions_unchanged(self):
            for markers in ({"user_id": 701}, {"user_id": None}, {"vendor_account_id": None},
                            {"vendor_username": ""}, {"vendor_name": None}, {"identity_type": "vendor"},
                            {"user_id": 701, "vendor_account_id": 601}, {"role": "admin"}):
                client = app.test_client()
                with client.session_transaction() as session:
                    session.update(markers)
                before = self.snapshot()
                for path, method in (("/vendor/register", "get"), ("/vendor/register", "post"),
                                     ("/vendor/register/success", "get")):
                    self.assertEqual(getattr(client, method)(path).status_code, 403)
                    with client.session_transaction() as session:
                        self.assertEqual(dict(session), markers)
                self.assertEqual(self.snapshot(), before)

        def test_backend_names_casefold_nfkc_trim_all_statuses(self):
            for table in ("users", "vendor_accounts"):
                for name in ("new.vendor", " NEW.VENDOR ", "ｎｅｗ．ｖｅｎｄｏｒ", "\u3000New.Vendor\t"):
                    with self.subTest(table=table, name=name):
                        self.reset()
                        if table == "users":
                            self.sql("INSERT INTO users(username,password_hash,role) VALUES(?,'unchanged','member')", (name,))
                        else:
                            self.sql("INSERT INTO vendor_accounts(username,password_hash,vendor_name,is_active) VALUES(?,'unchanged','legacy',0)", (name,))
                        self.reject(self.form())

        def test_alias_every_status_raw_equivalence_and_stored_key(self):
            for status in ("active", "disabled", "superseded"):
                for raw, key in ((" NEW.VENDOR ", "different-key"), ("unrelated", "new.vendor"),
                                 ("ｎｅｗ．ｖｅｎｄｏｒ", "different-key")):
                    self.reset()
                    self.sql("UPDATE login_identifier_aliases SET raw_alias=?,normalized_lookup_key=?,alias_status=?", (raw, key, status))
                    self.reject(self.form())

        def test_registry_all_absent_allowed_no_registry_created(self):
            for table in ("login_identifier_aliases", "backend_principal_mappings", "global_identities"):
                self.sql("DROP TABLE " + table)
            self.register()
            self.assertTrue(set(service.REGISTRY_TABLES).isdisjoint(self.snapshot()["rows"]))

        def test_registry_partial_or_incompatible_rejected(self):
            self.sql("DROP TABLE login_identifier_aliases")
            self.reject(self.form(), 503)
            self.reset()
            self.sql("ALTER TABLE login_identifier_aliases RENAME COLUMN normalized_lookup_key TO wrong_key")
            self.reject(self.form(), 503)

        def test_malformed_backend_name_fails_closed(self):
            self.sql("UPDATE users SET username=? WHERE id=101", (sqlite3.Binary(b"new.vendor"),))
            self.reject(self.form(), 503)

        def test_missing_core_roster_or_account_columns_rejected(self):
            for statement in ("DROP TABLE task_vendor_assignments", "DROP TABLE vendor_profiles",
                              "ALTER TABLE vendor_accounts RENAME COLUMN is_active TO wrong_active",
                              "ALTER TABLE users RENAME COLUMN username TO wrong_username",
                              "ALTER TABLE vendor_organizations RENAME COLUMN organization_status TO wrong_status"):
                with self.subTest(statement=statement):
                    self.reset()
                    form = self.form()
                    # Fixture schema mutation happens before rejection snapshots.
                    with self.connect() as conn:
                        conn.execute("PRAGMA foreign_keys=OFF")
                        conn.execute(statement)
                    self.reject(form, 503)

        def test_incompatible_supplement_and_write_triggers_rejected(self):
            self.sql("CREATE TABLE vendor_registration_requests(account_id INTEGER)")
            self.reject(self.form(), 503)
            self.reset()
            self.sql("CREATE TRIGGER unexpected AFTER INSERT ON vendor_accounts BEGIN UPDATE users SET role='admin'; END")
            self.reject(self.form(), 503)

        def test_resubmit_never_overwrites_existing_password(self):
            form = self.form()
            self.assertEqual(self.post(form).status_code, 303)
            self.reject(form, 403)
            different = secrets.token_urlsafe(32)
            self.reject(self.form(password=different, confirm_password=different))

        def test_second_insert_failure_rolls_back_account_and_new_table(self):
            real_connect = sqlite3.connect
            class FailingConnection(sqlite3.Connection):
                def execute(self, sql, parameters=()):
                    if "INSERT INTO main.vendor_registration_requests" in sql:
                        raise sqlite3.IntegrityError("synthetic second insert failure")
                    return super().execute(sql, parameters)
            def connect(*args, **kwargs):
                kwargs["factory"] = FailingConnection
                return real_connect(*args, **kwargs)
            form = self.form()
            with patch("routes.vendor_registration.sqlite3.connect", connect):
                self.reject(form, 503)
            self.assertNotIn("vendor_registration_requests", self.snapshot()["rows"])

        def test_same_name_concurrent_first_requests_have_one_winner(self):
            barrier = threading.Barrier(2)
            def worker():
                client = app.test_client()
                form = self.form(client=client)
                barrier.wait(timeout=10)
                return self.post(form, client).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                codes = sorted(pool.map(lambda _: worker(), range(2)))
            self.assertEqual(codes, [303, 400])
            with self.connect() as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM vendor_accounts WHERE username='new.vendor'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT count(*) FROM vendor_registration_requests").fetchone()[0], 1)

        def test_admin_absent_supplement_and_legacy_account_unchanged(self):
            for has_table in (False, True):
                with self.subTest(has_table=has_table):
                    self.reset()
                    if has_table:
                        self.register()
                    client = self.admin()
                    before = self.snapshot()
                    response, form = self.editor(client, 702)
                    self.assertIn("此帳號無本片申請資料", response.get_data(as_text=True))
                    self.assertEqual(self.snapshot(), before)
                    html, form = self.invalid_admin_reason(client, form, "ready-400" if has_table else "absent-400")
                    self.assertIn("此帳號無本片申請資料", html)
                    self.assertNotIn("申請資訊不可用", html)
                    self.assertNotIn('data-testid="registration-info"', html)
                    form["reason"] = "人工確認舊帳號"
                    self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 303)
                    if has_table:
                        self.assertEqual(self.snapshot()["rows"]["vendor_registration_requests"], before["rows"]["vendor_registration_requests"])
                    else:
                        self.assertNotIn("vendor_registration_requests", self.snapshot()["rows"])

        def test_admin_incompatible_supplement_explicit_unavailable_can_save(self):
            self.sql("CREATE TABLE vendor_registration_requests(account_id INTEGER)")
            client = self.admin()
            response, form = self.editor(client, 702)
            html = response.get_data(as_text=True)
            self.assertIn("申請資訊不可用", html)
            self.assertNotIn("此帳號無本片申請資料", html)
            html, form = self.invalid_admin_reason(client, form, "unavailable-400")
            self.assertIn("申請資訊不可用", html)
            self.assertNotIn("無本片申請資料", html)
            form["reason"] = "人工確認"
            form["confirm_membership"] = "1"
            self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 303)

        def test_admin_current_global_role_gate_no_request_leak(self):
            self.register()
            for markers in ({}, {"user_id": 101, "role": "admin"}, {"vendor_account_id": 601},
                            {"user_id": 701, "vendor_name": "legacy"}):
                client = app.test_client()
                with client.session_transaction() as session:
                    session.update(markers)
                response = client.get("/admin/vendor-scopes")
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("00000001", response.get_data(as_text=True))

        def test_admin_mismatch_warns_manual_choice_can_be_saved(self):
            account = self.register()
            client = self.admin()
            response, form = self.editor(client, account, other)
            self.assertIn("目前選定廠商與申請廠商不同", response.get_data(as_text=True))
            self.assertEqual(form["vendor_id"], other)
            self.assertNotIn("confirm_membership", form)
            form["reason"] = "人工核對實際歸屬為另一公司"
            form["confirm_membership"] = "1"
            self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 303)
            with self.connect() as conn:
                self.assertEqual(conn.execute("SELECT vendor_id FROM vendor_organization_memberships WHERE vendor_account_id=?", (account,)).fetchone()[0], other)
                self.assertEqual(conn.execute("SELECT requested_vendor_id FROM vendor_registration_requests WHERE account_id=?", (account,)).fetchone()[0], vendor)

        def test_display_data_does_not_change_fingerprint_cas_or_replay(self):
            account = self.register()
            client = self.admin()
            _, form = self.editor(client, account)
            def fingerprint():
                with self.connect() as conn:
                    conn.execute("BEGIN")
                    return admin_service.editor(conn, actor=actor, vendor_id=vendor, account_id=account, core_state=core_state)["fingerprint"]
            before = fingerprint()
            self.sql("UPDATE vendor_registration_requests SET submitted_company_name=? WHERE account_id=?", ('<script>unverified</script>', account))
            self.assertEqual(fingerprint(), before)
            page, _ = self.editor(client, account)
            self.assertNotIn("<script>unverified</script>", page.get_data(as_text=True))
            self.assertIn("&lt;script&gt;unverified&lt;/script&gt;", page.get_data(as_text=True))
            html, form = self.invalid_admin_reason(client, form, "escaped-400")
            self.assertNotIn("<script>unverified</script>", html)
            self.assertIn("&lt;script&gt;unverified&lt;/script&gt;", html)
            self.assertEqual(fingerprint(), before)
            form["reason"] = "人工確認"
            form["confirm_membership"] = "1"
            self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 303)
            self.sql("UPDATE vendor_registration_requests SET created_at='display-only' WHERE account_id=?", (account,))
            before = self.snapshot()
            self.assertEqual(client.post("/admin/vendor-scopes", data=form).status_code, 303)
            self.assertEqual(self.snapshot(), before)

    selected = os.environ.get("VR4_TEST_FILTER")
    suite = (unittest.TestSuite([RegistrationTests(selected)]) if selected else
             unittest.defaultTestLoader.loadTestsFromTestCase(RegistrationTests))
    class SafeResult(unittest.TextTestResult):
        def _exc_info_to_string(self, err, test):
            # Preserve failure location/type without dumping live credentials,
            # hashes, signed form fields or complete DB rows in assertion reprs.
            return "".join(traceback.format_list(traceback.extract_tb(err[2]))) + err[0].__name__ + ": values withheld\n"

    result = unittest.TextTestRunner(verbosity=2, resultclass=SafeResult).run(suite)
    print(json.dumps({"isolation": counts, "unicode_version": service.UNICODE_VERSION,
                      "child_tests": result.testsRun, "successful": result.wasSuccessful()}))
    assert not any(counts.values()), counts
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--child":
    raise SystemExit(child_suite(Path(sys.argv[2])))
