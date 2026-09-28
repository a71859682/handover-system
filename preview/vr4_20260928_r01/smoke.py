"""Only this preview entry: real loopback HTTP, generated secrets, safe events.

Run from the repository: python -B -m preview.vr4_20260928_r01.smoke
Each invocation creates a new work/run directory and retains failures. No old
suite imports, credential arguments, response dumps, or session manipulation.
"""

from contextlib import redirect_stderr, redirect_stdout
from html.parser import HTMLParser
import http.cookiejar
import importlib.abc
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler, ProxyHandler, Request
import uuid

from .fixture import BASELINE, FLAGS, IDENTITY, VENDORS, WINDOWS_ROOT

MODULE = "preview.vr4_20260928_r01"
REPO = Path(__file__).resolve().parents[2]


def emit(event, **fields):
    print(json.dumps(dict(event=event, **fields), ensure_ascii=True, sort_keys=True), flush=True)


def check(condition, code):
    if not condition:
        raise AssertionError(code)


def safe_failure(exc):
    # Never serialize exception messages, requests, local variables or headers.
    frames = traceback.extract_tb(exc.__traceback__)
    emit("FAIL", exception_type=type(exc).__name__,
         check_code=exc.args[0] if type(exc) is AssertionError else "UNEXPECTED_EXCEPTION",
         location=[dict(file=Path(f.filename).name, line=f.lineno) for f in frames[-3:]])


def child_server():
    # Suppress framework logs at the capture source; only explicit events escape.
    with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
        from .entry import VERSION, app, fresh
        from werkzeug.serving import WSGIRequestHandler, make_server

        class QuietHandler(WSGIRequestHandler):
            def log(self, *arguments, **keywords):
                pass

        server = make_server("127.0.0.1", 0, app, request_handler=QuietHandler)
    # App logging is not HTTP behavior; no request/exception data enters evidence.
    app.logger.disabled = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    emit("LISTENER_READY", pid=os.getpid(), port=server.server_port,
         testing=app.testing, debug=app.debug, fresh=fresh, version=VERSION)
    try:
        check(sys.stdin.readline().strip() == "STOP", "STOP_SIGNAL_REQUIRED")
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        emit("LISTENER_STOPPED", pid=os.getpid(), thread_alive=thread.is_alive())


def child_probe():
    class AppSentinel(importlib.abc.MetaPathFinder):
        attempted = False

        def find_spec(self, fullname, path=None, target=None):
            if fullname == "app":
                self.attempted = True
                raise RuntimeError("APP_IMPORT_REACHED")
            return None

    sentinel = AppSentinel()
    sys.meta_path.insert(0, sentinel)
    from .fixture import PreviewRejected
    try:
        from . import entry  # noqa: F401
    except PreviewRejected as exc:
        emit("PREIMPORT_REJECTED", code=str(exc), app_import_attempted=sentinel.attempted,
             app_in_modules="app" in sys.modules)
        return
    raise AssertionError("UNSAFE_CONFIGURATION_NOT_REJECTED_BEFORE_APP")


class Form(HTMLParser):
    """Successful controls from original HTML; tokens live only in memory."""
    def __init__(self, html, form_id):
        super().__init__()
        self.form_id, self.active = form_id, False
        self.values, self.controls = {}, {}
        self.select, self.options, self.textarea = None, [], None
        self.choices, self.option = {}, None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.active = a.get("id") == self.form_id
        if not self.active:
            return
        if tag == "input" and "name" in a:
            self.controls.setdefault(a["name"], []).append(a)
            if "disabled" not in a and (a.get("type") not in ("checkbox", "radio") or "checked" in a):
                self.values.setdefault(a["name"], []).append(a.get("value", ""))
        if tag == "select":
            self.select, self.options = a.get("name"), []
            self.controls.setdefault(self.select, []).append(a)
        if tag == "option" and self.select:
            self.option = dict(value=a.get("value", ""), selected="selected" in a, label="")
            self.options.append(self.option)
        if tag == "textarea":
            self.textarea = a.get("name")
            self.values[self.textarea] = [""]

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False
        if tag == "select" and self.select:
            self.values[self.select] = [next((o["value"] for o in self.options if o["selected"]), self.options[0]["value"])]
            self.choices[self.select] = self.options
            self.select = None
        if tag == "option":
            self.option = None
        if tag == "textarea":
            self.textarea = None

    def handle_data(self, value):
        if self.active and self.option is not None:
            self.option["label"] += value
        if self.active and self.textarea:
            self.values[self.textarea][0] += value


class PageText(HTMLParser):
    """Read rendered title/labels/buttons/links without retaining HTTP evidence."""
    def __init__(self, html):
        super().__init__()
        self.elements, self.open_elements = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in ("title", "label", "button", "a"):
            element = dict(tag=tag, attrs=dict(attrs), text="")
            self.elements.append(element)
            self.open_elements.append(element)

    def handle_endtag(self, tag):
        self.open_elements = [e for e in self.open_elements if e["tag"] != tag]

    def handle_data(self, text):
        for element in self.open_elements:
            element["text"] += text


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *arguments, **keywords):
        return None


class BrowserlessClient:
    def __init__(self, port):
        self.base = "http://127.0.0.1:" + str(port)
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect())

    def request(self, path, fields=None):
        check(path.startswith("/") and not path.startswith("//"), "LOCAL_ROUTE_REQUIRED")
        data = None if fields is None else urlencode(fields, doseq=True).encode()
        try:
            response = self.opener.open(Request(self.base + path, data=data), timeout=15)
        except HTTPError as exc:
            response = exc
        with response:
            # Nothing in this body or in Set-Cookie is automatically logged.
            return response.status, response.read().decode("utf-8"), response.headers.get("Location")


class Listener:
    def __init__(self, env, evidence, label):
        self.label, self.evidence = label, evidence
        self.process = subprocess.Popen([sys.executable, "-B", "-m", MODULE + ".smoke", "--server"],
            cwd=REPO, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.prefix = b""
        # Bound startup without assuming a listener PID or killing any other process.
        result = []
        reader = threading.Thread(target=lambda: result.append(self.process.stdout.readline()), daemon=True)
        reader.start()
        reader.join(timeout=30)
        if reader.is_alive():
            self.stop(force=True)
            raise AssertionError("LISTENER_START_TIMEOUT")
        self.prefix = result[0]
        if not self.prefix:
            self.stop(force=True)
            raise AssertionError("LISTENER_START_NO_EVENT")
        self.ready = json.loads(self.prefix)
        if self.ready.get("event") != "LISTENER_READY":
            self.stop(force=True)
            raise AssertionError("LISTENER_START_FAILED")
        check(self.ready["pid"] == self.process.pid, "PID_MISMATCH")
        self.port = self.ready["port"]
        emit("BOOT", label=label, **{k: self.ready[k] for k in ("pid", "port", "fresh", "testing", "debug", "version")})

    def stop(self, force=False):
        if self.process.poll() is None and force:
            self.process.terminate()
        try:
            out, err = self.process.communicate(None if force else b"STOP\n", timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            out, err = self.process.communicate(timeout=10)
            force = True
        (self.evidence / (self.label + ".stdout")).write_bytes(self.prefix + out)
        (self.evidence / (self.label + ".stderr")).write_bytes(err)
        closed = True
        if hasattr(self, "port"):
            with socket.socket() as sock:
                sock.settimeout(1)
                closed = sock.connect_ex(("127.0.0.1", self.port)) != 0
        emit("LISTENER_TERMINAL", label=self.label, pid=self.process.pid,
             exit_code=self.process.returncode, forced=force, loopback_port_closed=closed,
             stderr_bytes=len(err))
        check(closed, "LISTENER_STILL_OPEN")
        if not force:
            check(self.process.returncode == 0 and not err, "LISTENER_TERMINAL_FAILURE")


def run():
    check(os.name == "nt", "WINDOWS_SMOKE_ONLY")
    root = WINDOWS_ROOT / ("run-" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    evidence = root / "evidence"
    evidence.mkdir()
    env = os.environ.copy()
    env.update({key: "false" for key in FLAGS})
    env.update(VR4_PREVIEW_MODE=IDENTITY, VR4_PREVIEW_RUNTIME="LOCAL_SMOKE",
        VR4_PREVIEW_ROOT=str(root / "fixture"), APP_DB_PATH=str(root / "fixture" / "fixture.sqlite3"),
        VR4_PREVIEW_ADMIN_USERNAME="vr4.preview.admin", VR4_PREVIEW_ADMIN_PASSWORD=secrets.token_urlsafe(32),
        APP_SECRET_KEY=secrets.token_urlsafe(48), DATABASE_URL="", DUAL_WRITE_TABLES="",
        PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", FLASK_DEBUG="0", FLASK_TESTING="false")
    emit("RUN", root=str(root), python=sys.version.split()[0], baseline=BASELINE, preview=IDENTITY)
    old_root = Path(r"C:\Users\Public\Documents\004f-vr4-preview-20260928-r01")
    cases = [("wrong_mode", {"VR4_PREVIEW_MODE": "004F-VR4-PREVIEW/r01"}, "PREVIEW_MODE_REQUIRED"),
             ("old_root", {"VR4_PREVIEW_ROOT": str(old_root), "APP_DB_PATH": str(old_root / "fixture.sqlite3")}, "ROOT_NOT_AUTHORIZED"),
             ("repo_database", {"APP_DB_PATH": str(REPO / "site.db")}, "DATABASE_NOT_AUTHORIZED"),
             ("var_data", {"APP_DB_PATH": "/var/data/site.db"}, "ABSOLUTE_PATH_REQUIRED"),
             ("arbitrary_database", {"APP_DB_PATH": str(root / "arbitrary.sqlite3")}, "DATABASE_NOT_AUTHORIZED"),
             ("database_url", {"DATABASE_URL": "forbidden"}, "BACKEND_NOT_EMPTY_DATABASE_URL"),
             ("dual_tables", {"DUAL_WRITE_TABLES": "meta"}, "BACKEND_NOT_EMPTY_DUAL_WRITE_TABLES"),
             ("missing_secret", {"APP_SECRET_KEY": None}, "STRONG_APP_SECRET_REQUIRED"),
             ("weak_secret", {"APP_SECRET_KEY": "x" * 48}, "STRONG_APP_SECRET_REQUIRED")]
    cases += [(key.lower(), {key: "true"}, "FLAG_NOT_FALSE_" + key) for key in
              ("USE_SQLALCHEMY_WRITES", "DUAL_WRITE_ENABLED", "DUAL_WRITE_DRY_RUN", "DUAL_WRITE_STRICT")]
    unknown = root / "unknown"
    unknown.mkdir()
    unknown_db = unknown / "fixture.sqlite3"
    with sqlite3.connect(unknown_db) as conn:
        conn.execute("CREATE TABLE unknown_identity(value TEXT)")
    before_unknown = unknown_db.read_bytes()
    cases.append(("unknown_database", {"VR4_PREVIEW_ROOT": str(unknown), "APP_DB_PATH": str(unknown_db)}, "UNKNOWN_OR_INCOMPLETE_DATABASE"))
    for label, changes, expected_code in cases:
        invalid = env.copy()
        for key, value in changes.items():
            if value is None:
                invalid.pop(key, None)
            else:
                invalid[key] = value
        argv = [sys.executable, "-B", "-m", MODULE + ".smoke", "--probe"]
        with subprocess.Popen(argv, cwd=REPO, env=invalid, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as probe:
            try:
                out, err = probe.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                probe.kill()
                out, err = probe.communicate(timeout=10)
            (evidence / (label + ".stdout")).write_bytes(out)
            (evidence / (label + ".stderr")).write_bytes(err)
        emit("PROBE_TERMINAL", case=label, argv=argv, cwd=str(REPO), pid=probe.pid,
             exit_code=probe.returncode, stdout_bytes=len(out), stderr_bytes=len(err))
        check(probe.returncode == 0 and not err, "PREIMPORT_PROBE_FAILURE_" + label)
        event = json.loads(out)
        check(event["event"] == "PREIMPORT_REJECTED" and event["code"] == expected_code and not event["app_import_attempted"]
              and not event["app_in_modules"], "PREIMPORT_BOUNDARY_FAILURE_" + label)
        emit("PREFLIGHT", case=label, result="PASS", code=event["code"], app_import_attempted=False)
    check(unknown_db.read_bytes() == before_unknown, "UNKNOWN_DATABASE_CHANGED")
    check(not Path(env["APP_DB_PATH"]).exists(), "INVALID_SETTINGS_CREATED_FIXTURE")
    emit("PREFLIGHT_COMPLETE", passed=len(cases), unknown_database_unchanged=True)

    listener = Listener(env, evidence, "boot1")
    try:
        check(listener.ready["fresh"] and not listener.ready["testing"] and not listener.ready["debug"], "FIRST_BOOT_MODE")
        public, admin = BrowserlessClient(listener.port), BrowserlessClient(listener.port)
        status, text, _ = public.request("/preview/version")
        version = json.loads(text)
        check(status == 200 and version["baseline_commit"] == BASELINE and
              version["preview"] == IDENTITY and version["render_git_commit"] == "LOCAL_SMOKE" and
              version["synthetic"] and version == listener.ready["version"] and
              all(str(uuid.UUID(version[key])) == version[key] for key in ("boot_id", "fixture_instance")), "VERSION_RESPONSE")
        emit("VERSION", result="PASS", **version)
        check(public.request("/preview/fixture-state")[0] == 403, "SUMMARY_ANONYMOUS_DENIED")
        check(admin.request("/login", {"username": "admin", "password": "admin"})[0] == 200 and
              admin.request("/preview/fixture-state")[0] == 403, "DEFAULT_LOGIN_DISABLED")
        check(admin.request("/login", {"username": env["VR4_PREVIEW_ADMIN_USERNAME"],
              "password": env["VR4_PREVIEW_ADMIN_PASSWORD"]})[0] == 302, "NORMAL_ADMIN_LOGIN")
        def summary():
            status, body, _ = admin.request("/preview/fixture-state")
            check(status == 200, "ADMIN_SUMMARY_STATUS")
            return json.loads(body)
        initial = summary()
        check(not initial["state"]["accounts"] and all(v["organization_status"] == "disabled"
              for v in initial["state"]["vendors"]), "FRESH_DISABLED_FIXTURE")
        for route in ("/admin/users", "/admin/table", "/api/reset-sheet"):
            check(admin.request(route, {} if route.startswith("/api") else None)[0] == 404, "TOOLS_NOT_EXPOSED")
        check(admin.request("/preview/fixture-state?sql=SELECT")[0] == 400, "SUMMARY_NO_QUERY")
        check(admin.request("/preview/fixture-state", {})[0] == 405, "SUMMARY_NO_POST")
        emit("ADMIN_LOGIN", result="PASS", default_login_disabled=True, anonymous_summary_status=403,
             admin_summary_status=200, tools_not_exposed=True)
        vendor_password = secrets.token_urlsafe(32)
        status, body, _ = public.request("/vendor/register")
        check(status == 200, "REGISTRATION_GET")
        registration = Form(body, "vendor-registration-form")
        fields = {"vendor_id", "username", "password", "confirm_password", "csrf_token"}
        choices = registration.choices["vendor_id"]
        check(set(registration.values) == fields and set(registration.controls) == fields and
              registration.values["vendor_id"] == [""] and choices[0]["selected"] and
              len(choices) == 3 and {o["label"] for o in choices if o["value"]} == {v[1] for v in VENDORS},
              "NATIVE_COMPANY_SELECT_AND_FIVE_FIELDS")
        selected_vendor = next(o["value"] for o in choices if o["label"] == VENDORS[0][1])
        other_vendor = next(o["value"] for o in choices if o["label"] == VENDORS[1][1])
        check(selected_vendor and other_vendor and selected_vendor != other_vendor, "DISTINCT_PAGE_OPTIONS")
        form = registration.values
        form.update(vendor_id=[selected_vendor], username=["preview.vendor"],
                    password=[vendor_password], confirm_password=[secrets.token_urlsafe(32)])
        database = Path(env["APP_DB_PATH"])
        before_registration, registration_bytes = summary(), database.read_bytes()
        status, body, _ = public.request("/vendor/register", form)
        refilled = Form(body, "vendor-registration-form")
        check(status == 400 and "兩次密碼不一致" in body and refilled.values["vendor_id"] == [selected_vendor]
              and refilled.values["username"] == ["preview.vendor"] and refilled.values["password"] == [""]
              and refilled.values["confirm_password"] == [""] and set(refilled.values) == fields
              and any(o["value"] == selected_vendor and o["selected"] for o in refilled.choices["vendor_id"]),
              "REGISTRATION_MISMATCH_REFILL")
        check(database.read_bytes() == registration_bytes and summary() == before_registration, "REGISTRATION400_NO_WRITE")
        check(vendor_password not in body and form["confirm_password"][0] not in body, "REGISTRATION_NO_PASSWORD_REFLECTION")
        emit("REGISTRATION_MISMATCH", result="PASS", status=400, exact_five_fields=True,
             native_select=True, synthetic_company_options=2, default_empty=True, page_option_used=True,
             company_and_username_retained=True, passwords_empty=True, database_bytes_unchanged=True,
             safe_summary_unchanged=True)
        form = refilled.values
        form.update(password=[vendor_password], confirm_password=[vendor_password])
        status, _, location = public.request("/vendor/register", form)
        check(status == 303 and location == "/vendor/register/success", "REGISTRATION_POST")
        status, body, _ = public.request(location)
        check(status == 200 and "帳號已建立，待管理者確認，尚未開通。" in body and
              VENDORS[0][1] in body and VENDORS[0][0] in body, "PENDING_CANONICAL_RECEIPT")
        registered = summary()
        account = registered["state"]["accounts"][0]
        check(account["is_active"] == 0 and not registered["state"]["memberships"], "REGISTERED_INACTIVE")
        request_info = registered["state"]["registrations"][0]
        check(request_info["requested_vendor_id"] == selected_vendor and
              request_info["submitted_company_name"] == VENDORS[0][1] and
              request_info["submitted_tax_id"] == VENDORS[0][0], "SERVER_CANONICAL_REQUEST")
        vendor_client = BrowserlessClient(listener.port)
        status, body, _ = vendor_client.request("/vendor/login")
        elements = PageText(body).elements
        check(status == 200 and any(e["tag"] == "title" and e["text"].strip() == "廠商登入" for e in elements)
              and {e["text"].strip() for e in elements if e["tag"] == "label"} == {"帳號", "密碼"}
              and any(e["tag"] == "button" and e["text"].strip() == "登入" for e in elements)
              and any(e["tag"] == "a" and e["attrs"].get("href") == "/vendor/register" and
                      e["text"].strip() == "廠商申請帳號（待開通）" for e in elements), "TRADITIONAL_CHINESE_LOGIN")
        status, body, _ = vendor_client.request("/vendor/login", {"username": "preview.vendor", "password": vendor_password})
        check(status == 200 and "廠商帳號或密碼錯誤，或帳號尚未開通" in body and
              'data-testid="vendor-login-success"' not in body and
              vendor_client.request("/preview/fixture-state")[0] == 403 and
              vendor_client.request("/vendor/register")[0] == 200, "INACTIVE_VENDOR_DENIED")
        emit("REGISTRATION", result="PASS", post_status=303, is_active=0, membership_count=0,
             waiting_message=True, normal_csrf_flow=True, server_canonical_company=True,
             leading_zero_tax_id=True, requested_vendor_matches_selected=True,
             effective_authorization=False, vendor_summary_status=403)
        emit("VENDOR_LOGIN", result="PASS", traditional_chinese_title_labels_button_link=True,
             inactive_real_password_status=200, generic_chinese_error=True, vendor_identity_granted=False)
        other = next(v for v in registered["state"]["vendors"] if v["vendor_id"] == other_vendor)
        editor_route = "/admin/vendor-scopes?" + urlencode(dict(vendor_id=other["vendor_id"], account_id=account["id"]))
        status, body, _ = admin.request(editor_route)
        hint = "注意：目前選定廠商與申請廠商不同。"
        check(status == 200 and hint in body, "CROSS_VENDOR_HINT_GET")
        editor = Form(body, "pending-scope-form")
        posted = editor.values
        posted.update(confirm_membership=["1"], reason=["   "], **{"enabled.101": ["1"], "mode.101": ["SELECTED"],
            "task.101": ["302", "303"], "enabled.102": ["1"], "mode.102": ["ALL"]})
        # Check exact DB bytes only in memory. Do not serialize DB or credential hashes.
        database = Path(env["APP_DB_PATH"])
        before_summary, before_bytes = summary(), database.read_bytes()
        status, body, _ = admin.request("/admin/vendor-scopes", posted)
        after_summary, after_bytes = summary(), database.read_bytes()
        check(status == 400 and before_summary == after_summary and before_bytes == after_bytes, "POST400_NO_WRITE")
        retained = Form(body, "pending-scope-form").values
        check(hint in body and VENDORS[0][1] in body and VENDORS[0][0] in body and
              VENDORS[1][1] in body and "preview.vendor" in body and
              retained == posted, "POST400_HINT_AND_ALL_CONTROLS_RETAINED")
        check(vendor_password not in body and env["VR4_PREVIEW_ADMIN_PASSWORD"] not in body and
              env["APP_SECRET_KEY"] not in body, "NO_SECRET_REFLECTION")
        emit("BLANK_REASON", result="PASS", status=400, database_bytes_unchanged=True,
             safe_summary_unchanged=True, cross_vendor_hint=True, safe_company_fields=True,
             csrf_and_snapshot_retained=True, all_controls_and_checks_retained=True)
        retained["reason"] = ["預覽人工核對跨廠商歸屬，僅保存待開通設定"]
        status, _, location = admin.request("/admin/vendor-scopes", retained)
        check(status == 303, "CORRECTED_REASON_POST")
        check(admin.request(location)[0] == 200, "CORRECTED_REASON_REDIRECT")
        final = summary()
        membership = final["state"]["memberships"][0]
        check(final["state"]["accounts"][0]["is_active"] == 0 and
              all(v["organization_status"] == "disabled" for v in final["state"]["vendors"]) and
              membership["membership_status"] == "pending" and membership["vendor_id"] == other["vendor_id"] and
              membership["effective_task_count"] == 0 and membership["configured_task_count"] == 3,
              "SAVED_PENDING_EFFECTIVE_ZERO")
        check(final["state"]["registrations"] == registered["state"]["registrations"] and
              final["state"]["registrations"][0]["requested_vendor_id"] == selected_vendor and
              selected_vendor != membership["vendor_id"], "REQUEST_NOT_REWRITTEN")
        (evidence / "safe-state-after.json").write_text(json.dumps(final, ensure_ascii=True, indent=2), encoding="utf-8")
        emit("CORRECTED_REASON", result="PASS", status=303, membership_status="pending",
             is_active=0, organizations_disabled=True, configured_tasks=3, effective_tasks=0,
             registration_request_preserved=True)
    finally:
        listener.stop()
    listener2 = Listener(env, evidence, "boot2")
    try:
        check(not listener2.ready["fresh"] and listener2.ready["version"]["fixture_instance"] == version["fixture_instance"]
              and listener2.ready["version"]["boot_id"] != version["boot_id"], "RESTART_IDENTITIES")
        admin2 = BrowserlessClient(listener2.port)
        check(admin2.request("/login", {"username": env["VR4_PREVIEW_ADMIN_USERNAME"],
              "password": env["VR4_PREVIEW_ADMIN_PASSWORD"]})[0] == 302, "RESTART_ADMIN_LOGIN")
        status, body, _ = admin2.request("/preview/fixture-state")
        restarted = json.loads(body)
        check(status == 200 and restarted["state"] == final["state"] and
              restarted["state_sha256"] == final["state_sha256"], "RESTART_PRESERVES_USER_ACTIONS")
        emit("RESTART", result="PASS", new_boot_same_fixture=True, user_actions_preserved=True,
             inactive_disabled_pending_effective_zero=True)
    finally:
        listener2.stop()
    emit("COMPLETE", result="PREVIEW_ENTRY_SMOKE_PASS", evidence=str(evidence),
         remote_calls=0, old_suites_run=0, browser_pass_claim=False, render_pass_claim=False)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--server"]:
            child_server()
        elif sys.argv[1:] == ["--probe"]:
            child_probe()
        else:
            check(not sys.argv[1:], "UNKNOWN_ARGUMENT")
            run()
    except BaseException as exc:
        safe_failure(exc)
        sys.exit(1)
