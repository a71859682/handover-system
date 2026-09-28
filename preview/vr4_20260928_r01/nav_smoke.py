"""NAV/r02 only: real loopback HTTP, normal login, safe event projections.

No historical smoke import, business submission matrix, remote access, mock
session, or response dumps. Fixtures remain in this operation's fresh scratch.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from html.parser import HTMLParser
import http.cookiejar
import importlib.abc
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import traceback
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import (build_opener, HTTPCookieProcessor,
                            HTTPRedirectHandler, ProxyHandler, Request)
import uuid

from .fixture import BASELINE, FLAGS, IDENTITY, WINDOWS_ROOT

MODULE = "preview.vr4_20260928_r01.nav_smoke"
REPO = Path(__file__).resolve().parents[2]
RECORD = Path(r"I:\公司web\record\product-mainline\vendor-id\004f\vr4-preview-nav-20260928-r02")


def emit(event, **fields):
    print(json.dumps(dict(event=event, **fields), ensure_ascii=True, sort_keys=True), flush=True)


def check(condition, code):
    if not condition:
        raise AssertionError(code)


def safe_failure(exc):
    # Only our fixed check codes and frame locations; never exception messages.
    code = exc.args[0] if type(exc) is AssertionError and exc.args else "UNEXPECTED_EXCEPTION"
    if not isinstance(code, str) or not code.replace("_", "").isalnum() or not code.isupper():
        code = "UNEXPECTED_EXCEPTION"
    emit("FAIL", code=code, exception_type=type(exc).__name__,
         frames=[dict(file=Path(f.filename).name, line=f.lineno)
                 for f in traceback.extract_tb(exc.__traceback__)[-3:]])


def server():
    with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
        from .entry import VERSION, app, contract, fresh
        from werkzeug.serving import WSGIRequestHandler, make_server

        class QuietHandler(WSGIRequestHandler):
            def log(self, *arguments, **keywords):
                pass

        app.logger.disabled = True
        listener = make_server("127.0.0.1", 0, app, request_handler=QuietHandler)
    thread = threading.Thread(target=listener.serve_forever, daemon=True)
    thread.start()
    emit("LISTENER_READY", pid=os.getpid(), port=listener.server_port,
         version=VERSION, root=str(contract.root), runtime=contract.runtime,
         fresh=fresh, testing=app.testing, debug=app.debug)
    try:
        check(sys.stdin.readline().strip() == "STOP", "STOP_SIGNAL_REQUIRED")
    finally:
        listener.shutdown()
        thread.join(timeout=10)
        listener.server_close()
        emit("LISTENER_STOPPED", pid=os.getpid(), thread_alive=thread.is_alive())
        check(not thread.is_alive(), "LISTENER_THREAD_REMAINS")


def probe():
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
        code = str(exc)
        check(code in {"PREVIEW_MODE_REQUIRED", "ROOT_NOT_AUTHORIZED"}, "UNEXPECTED_GUARD_CODE")
        emit("PREIMPORT_REJECTED", code=code, app_import_attempted=sentinel.attempted,
             app_in_modules="app" in sys.modules)
        return
    raise AssertionError("GUARD_NOT_REJECTED")


class Page(HTMLParser):
    """In-memory HTML structure; no raw page or control values enter evidence."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements, self.stack = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        element = dict(tag=tag, attrs=dict(attrs), text="")
        self.elements.append(element)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(element)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        for element in self.stack:
            element["text"] += text

    def select(self, tag=None, **attrs):
        return [e for e in self.elements if (tag is None or e["tag"] == tag)
                and all(e["attrs"].get(k) == v for k, v in attrs.items())]

    def tabs(self):
        return [e for e in self.select("a") if "tab" in e["attrs"].get("class", "").split()]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *arguments, **keywords):
        return None


class Client:
    def __init__(self, port):
        self.base = "http://127.0.0.1:" + str(port)
        self.opener = build_opener(ProxyHandler({}),
                                  HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect())

    def request(self, path, fields=None, method=None):
        check(path.startswith("/") and not path.startswith("//"), "LOOPBACK_ROUTE_REQUIRED")
        data = None if fields is None else urlencode(fields).encode()
        try:
            response = self.opener.open(Request(self.base + path, data=data, method=method), timeout=15)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, response.read().decode("utf-8"), response.headers.get("Location")


def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)


class Listener:
    def __init__(self, env, evidence):
        self.evidence, self.prefix = evidence, b""
        self.argv = [sys.executable, "-B", "-m", MODULE, "--server"]
        self.process = subprocess.Popen(self.argv, cwd=REPO, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = []
        reader = threading.Thread(target=lambda: result.append(self.process.stdout.readline()), daemon=True)
        reader.start()
        reader.join(timeout=40)
        if reader.is_alive() or not result or not result[0]:
            self.stop(force=True)
            raise AssertionError("LISTENER_START_FAILED")
        self.prefix = result[0]
        self.ready = json.loads(self.prefix)
        if self.ready.get("event") != "LISTENER_READY":
            self.stop(force=True)
            raise AssertionError("LISTENER_READY_REQUIRED")
        self.port = self.ready["port"]
        check(self.ready["pid"] == self.process.pid, "PID_MISMATCH")
        emit("BOOT", **{k: v for k, v in self.ready.items() if k != "event"})

    def stop(self, force=False):
        if force and self.process.poll() is None:
            self.process.terminate()
        try:
            out, err = self.process.communicate(None if force else b"STOP\n", timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            out, err = self.process.communicate(timeout=10)
            force = True
        write_new(self.evidence / "listener.stdout", self.prefix + out)
        write_new(self.evidence / "listener.stderr", err)
        closed = None
        if hasattr(self, "port"):
            with socket.socket() as sock:
                sock.settimeout(1)
                closed = sock.connect_ex(("127.0.0.1", self.port)) != 0
        terminal = dict(argv=self.argv, cwd=str(REPO), pid=self.process.pid,
                        exit=self.process.returncode, forced=force, port=getattr(self, "port", None),
                        port_released=closed, stderr_bytes=len(err))
        write_new(self.evidence / "listener.json", json.dumps(terminal, indent=2).encode())
        emit("LISTENER_TERMINAL", **terminal)
        if not force:
            check(closed and self.process.returncode == 0 and not err, "LISTENER_TERMINAL_FAILURE")


def audit_page(page, route, client):
    allowed = {"/sheet", "/site-selector", "/login", "/logout", "/vendor/register",
               "/vendor/login", "/vendor/logout", "/admin/vendor-scopes"}
    ids = {e["attrs"]["id"] for e in page.elements if "id" in e["attrs"]}
    links, forms, resources = 0, 0, 0
    for element in page.elements:
        tag, attrs = element["tag"], element["attrs"]
        if tag == "a" and "href" in attrs:
            target = attrs["href"]
            if target.startswith("#"):
                check(target[1:] in ids, "ANCHOR_TARGET_MISSING")
            else:
                url = urlsplit(target)
                check(not url.scheme and not url.netloc, "EXTERNAL_NAVIGATION")
                check(url.path in allowed or any(target == tab["attrs"]["href"] for tab in page.tabs()), "ENABLED_FORBIDDEN_LINK")
                status, _, _ = client.request(target)
                emit("LINK_REACHABILITY", source=route, target=url.path, status=status)
                check(status in {200, 302}, "ENABLED_LINK_NOT_REACHABLE")
            links += 1
        if tag == "form" and attrs.get("method", "get") != "dialog":
            target = urlsplit(attrs.get("action") or route).path
            check(target in allowed, "ENABLED_FORBIDDEN_FORM")
            forms += 1
        if tag in {"script", "link"}:
            target = attrs.get("src") if tag == "script" else attrs.get("href")
            if target:
                check(target.startswith("/static/"), "UNEXPECTED_RESOURCE")
                check(client.request(target)[0] == 200, "RESOURCE_NOT_REACHABLE")
                resources += 1
    emit("PAGE_AUDIT", route=route, links=links, forms=forms, resources=resources,
         forbidden_enabled_actions=0, anchors_valid=True)


def run(evidence, navigation_only=False):
    check(os.name == "nt" and REPO == WINDOWS_ROOT / "repo", "WORKSPACE_GUARD")
    check(evidence.is_relative_to(RECORD / "evidence") and not evidence.exists(), "EVIDENCE_SCOPE")
    evidence.mkdir(parents=True, exist_ok=False)
    root = WINDOWS_ROOT / "scratch" / ("nav-" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update({key: "false" for key in FLAGS})
    env.update(VR4_PREVIEW_MODE=IDENTITY, VR4_PREVIEW_RUNTIME="LOCAL_SMOKE",
               VR4_PREVIEW_ROOT=str(root / "fixture"), APP_DB_PATH=str(root / "fixture/fixture.sqlite3"),
               VR4_PREVIEW_ADMIN_USERNAME="vr4.preview.admin", VR4_PREVIEW_ADMIN_PASSWORD=secrets.token_urlsafe(32),
               APP_SECRET_KEY=secrets.token_urlsafe(48), DATABASE_URL="", DUAL_WRITE_TABLES="",
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", FLASK_DEBUG="0", FLASK_TESTING="false")
    execution_pins = {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in (
        "templates/base.html", "templates/sheet.html", "templates/vendor_scope_admin.html", "static/app.js",
        "preview/vr4_20260928_r01/entry.py", "preview/vr4_20260928_r01/fixture.py",
        "preview/vr4_20260928_r01/README.md", "preview/vr4_20260928_r01/nav_smoke.py")}
    write_new(evidence / "execution-pins.json", json.dumps(execution_pins, indent=2).encode())
    emit("RUN", root=str(root), baseline=BASELINE, identity=IDENTITY, runtime="LOCAL_SMOKE", synthetic=True)
    old_root = r"C:\Users\Public\Documents\004f-VR4-UX-PREVIEW-20260928-r01"
    guard_cases = [
        ("old_identity", {"VR4_PREVIEW_MODE": "004F-VR4-UX-PREVIEW/r01"}, "PREVIEW_MODE_REQUIRED"),
        ("old_root", {"VR4_PREVIEW_ROOT": old_root, "APP_DB_PATH": old_root + r"\fixture.sqlite3"}, "ROOT_NOT_AUTHORIZED"),
    ]
    if navigation_only:
        emit("GUARDS_SKIPPED", reason="navigation-only correction; retain prior guard evidence")
    for label, delta, expected in ([] if navigation_only else guard_cases):
        argv = [sys.executable, "-B", "-m", MODULE, "--probe"]
        result = subprocess.run(argv, cwd=REPO, env=env | delta, capture_output=True, timeout=25)
        write_new(evidence / (label + ".stdout"), result.stdout)
        write_new(evidence / (label + ".stderr"), result.stderr)
        write_new(evidence / (label + ".json"), json.dumps(dict(argv=argv, cwd=str(REPO), exit=result.returncode), indent=2).encode())
        check(result.returncode == 0 and not result.stderr, "PROBE_FAILED")
        event = json.loads(result.stdout)
        check(event["code"] == expected and not event["app_import_attempted"] and not event["app_in_modules"], "PREIMPORT_BOUNDARY")
        emit("GUARD", case=label, result="PASS", code=expected, app_imported=False, db_opened=False)
    check(not Path(env["APP_DB_PATH"]).exists(), "PROBE_CREATED_DB")
    listener = Listener(env, evidence)
    try:
        client = Client(listener.port)
        version = json.loads(client.request("/preview/version")[1])
        check(version == listener.ready["version"] and version["preview"] == IDENTITY and
              version["baseline_commit"] == BASELINE and version["render_git_commit"] == "LOCAL_SMOKE" and
              version["synthetic"] is True and listener.ready["fresh"] and
              listener.ready["root"] == env["VR4_PREVIEW_ROOT"] and
              not listener.ready["testing"] and not listener.ready["debug"], "VERSION_CONTRACT")
        check(client.request("/preview/fixture-state")[0] == 403, "ANONYMOUS_SUMMARY_ROLE")
        anonymous_admin_status = client.request("/admin/vendor-scopes")[0]
        emit("ANONYMOUS_ADMIN", status=anonymous_admin_status)
        check(anonymous_admin_status == 403, "ANONYMOUS_ADMIN_AUTH")
        public = Page(client.request("/login")[1])
        check(not any(e["attrs"].get("href") == "/admin/vendor-scopes" for e in public.select("a")), "PUBLIC_ADMIN_LINK")
        status, _, location = client.request("/login", dict(username=env["VR4_PREVIEW_ADMIN_USERNAME"], password=env["VR4_PREVIEW_ADMIN_PASSWORD"]))
        check(status == 302 and location in {"/site-selector", "/sheet"}, "NORMAL_LOGIN")
        status, html, _ = client.request("/site-selector")
        check(status == 200, "SITE_SELECTOR")
        sites = [e["attrs"]["value"] for e in Page(html).select("input", name="site_id")]
        check(len(sites) == 2, "SYNTHETIC_SITES")
        check(client.request("/site-selector", dict(site_id=sites[0]))[0] == 302, "SITE_SELECT_FIRST")
        status, html, _ = client.request("/sheet")
        check(status == 200, "SHEET_GET")
        first = Page(html)
        tabs = first.tabs()
        check(len(tabs) >= 2, "SAME_SITE_TWO_TABS")
        # The parameter path comes from the authenticated real page, not guessed IDs.
        anonymous = Client(listener.port)
        status, _, location = anonymous.request(tabs[0]["attrs"]["href"])
        check(status == 302 and location == "/login", "ANONYMOUS_PARAMETER_LOGIN")
        status, state_html, _ = client.request("/preview/fixture-state")
        check(status == 200, "ADMIN_SUMMARY")
        state_before = json.loads(state_html)
        check(state_before["readonly"] is True and all(state_before[k] == version[k] for k in version), "SUMMARY_CONTRACT")
        database = Path(env["APP_DB_PATH"])
        before_bytes = database.read_bytes()
        check(client.request("/preview/fixture-state", method="POST")[0] == 405, "SUMMARY_READONLY_METHOD")
        check(client.request("/preview/fixture-state?filter=x")[0] == 400, "SUMMARY_FIXED_QUERY")
        check("VR4 隔離預覽・僅供測試" in html and "重新整理更新" in html, "PREVIEW_NOTICE")
        check(first.select("button", id="resetSheetBtn") and "disabled" in first.select("button", id="resetSheetBtn")[0]["attrs"], "RESET_DISABLED")
        check(not first.select("form", **{"data-testid": "crew-formal-cancellation-form"}), "CANCEL_FORM_REMOVED")
        check("本次預覽未開放" in html and "正在載入工班資料" not in html and "功能規劃中" in html, "CREW_AND_AI_FALLBACK")
        for tab in tabs:
            href = tab["attrs"]["href"]
            status, body, _ = client.request(href)
            page = Page(body)
            active = [t for t in page.tabs() if "active" in t["attrs"].get("class", "").split()]
            check(status == 200 and len(active) == 1 and active[0]["attrs"]["href"] == href and
                  page.select("h1")[0]["text"].strip() == tab["text"].strip() and
                  page.select("title")[0]["text"].startswith(tab["text"].strip()) and
                  page.select("table", id="controlTable")[0]["attrs"]["data-sheet-id"] == href.rsplit("/", 1)[1], "TAB_TITLE_SELECTION")
            grid = json.loads(client.request("/api/grid")[1])
            check(str(grid["current_sheet"]["id"]) == href.rsplit("/", 1)[1] and
                  all(task["name"] in body for task in grid["tasks"]), "TAB_CONTENT_MATCH")
            check(client.request(href, method="HEAD")[0] == 200, "PARAMETER_HEAD")
            audit_page(page, href, client)
            emit("TAB", route=href, status=200, head=200, title_matches=True, content_matches=True)
        check(client.request("/site-selector", dict(site_id=sites[1]))[0] == 302, "SITE_SELECT_SECOND")
        status, body, _ = client.request("/sheet")
        second = Page(body)
        check(status == 200 and second.tabs() and
              {t["attrs"]["href"] for t in second.tabs()}.isdisjoint({t["attrs"]["href"] for t in tabs}), "SECOND_SITE_TABS")
        other_href = second.tabs()[0]["attrs"]["href"]
        check(client.request(other_href)[0] == 200, "SECOND_SITE_PARAMETER")
        check(client.request("/site-selector", dict(site_id=sites[0]))[0] == 302, "RESTORE_SITE")
        for label, route in [("cross_site", other_href), ("missing", "/sheet/2147483647")]:
            status, _, location = client.request(route)
            check(status == 302 and location == "/sheet", "ORIGINAL_SHEET_REJECTION")
            emit("SHEET_BOUNDARY", case=label, status=status, redirect="/sheet")
        for method, route in [("GET", "/sheetish/201"), ("GET", tabs[0]["attrs"]["href"] + "/extra"),
                              ("POST", tabs[0]["attrs"]["href"]), ("OPTIONS", tabs[0]["attrs"]["href"]),
                              ("GET", "/admin/users"), ("GET", "/admin/table"),
                              ("POST", "/api/reset-sheet"), ("POST", "/api/progress"), ("POST", "/api/unit-extra"),
                              ("GET", "/api/crew-forms"), ("GET", "/api/management-read-model"),
                              ("GET", "/api/work-hub-runtime"), ("GET", "/api/dashboard"), ("GET", "/api/scheduling"),
                              ("POST", "/api/crew-work-entry-requirement-confirm"),
                              ("POST", "/api/crew-work-entry/formal-approve"),
                              ("POST", "/api/crew-work-entry/formal-approval-cancel")]:
            status, _, _ = client.request(route, method=method)
            check(status == 404, "BACKEND_NEGATIVE_BOUNDARY")
            emit("DENIED", method=method, route=route, status=status)
        status, html, _ = client.request("/admin/vendor-scopes")
        scope = Page(html)
        check(status == 200 and scope.select("form", method="get") and scope.select("select", name="vendor_id") and
              scope.select("select", name="account_id") and len(scope.select("option")) >= 4 and
              any(e["attrs"].get("href") == "/sheet" and e["text"] == "返回管制表" for e in scope.select("a")), "SCOPE_NAVIGATION")
        audit_page(scope, "/admin/vendor-scopes", client)
        for route in ("/vendor/register", "/vendor/login", "/site-selector", "/login"):
            page_client = anonymous if route in {"/vendor/register", "/vendor/login", "/login"} else client
            status, html, _ = page_client.request(route)
            page = Page(html)
            check(status == 200, "NAV_DESTINATION")
            if route == "/vendor/register":
                check(page.select("select", name="vendor_id") and len(page.select("option")) >= 3, "COMPANY_CHOICES")
            if route == "/vendor/login":
                check("廠商登入" in html and "帳號" in html and "密碼" in html, "VENDOR_TRADITIONAL_CHINESE")
            audit_page(page, route, page_client)
        # Return to identical selected site/sheet before comparing fixed state.
        check(client.request("/site-selector", dict(site_id=sites[0]))[0] == 302, "FINAL_SITE_CONTEXT")
        check(client.request(tabs[0]["attrs"]["href"])[0] == 200, "FINAL_SHEET_CONTEXT")
        state_after = json.loads(client.request("/preview/fixture-state")[1])
        check(state_after == state_before and database.read_bytes() == before_bytes, "READONLY_STATE_OR_DB_CHANGED")
        check(json.loads(client.request("/preview/version")[1]) == version, "BOOT_CHANGED")
        emit("STATE_UNCHANGED", summary_equal=True, database_raw_equal=True,
             database_bytes=len(before_bytes), database_sha256=hashlib.sha256(before_bytes).hexdigest(),
             state_sha256=state_after["state_sha256"], boot_id=version["boot_id"],
             fixture_instance=version["fixture_instance"], same_site_context=True)
        check(client.request("/logout", {})[0] == 302 and client.request("/preview/fixture-state")[0] == 403, "LOGOUT_AND_ROLE_BOUNDARY")
        landing = Page(client.request("/login")[1])
        public_links = {e["attrs"].get("href") for e in landing.select("a")}
        check({"/vendor/register", "/vendor/login"}.issubset(public_links), "PUBLIC_ENTRIES_AFTER_LOGOUT")
        check(all(client.request(path)[0] == 200 for path in ("/vendor/register", "/vendor/login")), "LOGOUT_PUBLIC_NAVIGATION")
        check(database.read_bytes() == before_bytes, "LOGOUT_DB_CHANGED")
        emit("NAV_HTTP_COMPLETE", result="PASS", business_submissions=0,
             reset_handler_executions=0, historical_suite_executions=0,
             browser_review="PENDING", fixture_retained=str(root / "fixture"))
    finally:
        listener.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--navigation-only", action="store_true",
                        help="Run navigation after a correction; retain prior constant-guard evidence.")
    args = parser.parse_args()
    try:
        if args.server:
            server()
        elif args.probe:
            probe()
        else:
            check(args.evidence is not None, "EVIDENCE_REQUIRED")
            run(args.evidence.resolve(), args.navigation_only)
    except Exception as exc:
        safe_failure(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
