"""Preview-only isolation and synthetic fixture; no app import at module load."""

from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import sys
import uuid
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

IDENTITY = "004F-VR4-PREVIEW-NAV/r02"
BASELINE = "048f27807f89428301ad975aef420aa7721ac242"
WINDOWS_ROOT = Path(r"C:\Users\Public\Documents\004f-VR4-PREVIEW-NAV-20260928-r02")
RENDER_ROOT = Path("/tmp/004f-vr4-preview-nav-20260928-r02")
FLAGS = ("USE_SQLALCHEMY_READS", "USE_SQLALCHEMY_WRITES", "USERS_READ_COMPARE",
         "DUAL_WRITE_ENABLED", "DUAL_WRITE_DRY_RUN", "DUAL_WRITE_STRICT")
MARKER = "vr4_preview_identity"
VENDORS = (("00000001", "預覽合成甲有限公司"), ("00000002", "預覽合成乙有限公司"))


class PreviewRejected(RuntimeError):
    """Only fixed, non-secret rejection codes may be used as messages."""


@dataclass(frozen=True)
class Contract:
    root: Path
    database: Path
    runtime: str
    commit: str
    username: str
    password: str = field(repr=False)
    secret: str = field(repr=False)


def require(condition, code):
    if not condition:
        raise PreviewRejected(code)


def plain_path(path):
    """Reject symlink/junction aliases, including existing ancestors."""
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not
                    (getattr(info, "st_file_attributes", 0) & 0x400), "PATH_ALIAS")
    if path.exists() and path.is_file():
        require(path.stat().st_nlink == 1, "HARDLINK_DATABASE")


def validate_environment():
    """No mkdir, DB write, app or product-module import before this returns."""
    require("app" not in sys.modules, "APP_ALREADY_IMPORTED")
    env = os.environ
    require(env.get("VR4_PREVIEW_MODE") == IDENTITY, "PREVIEW_MODE_REQUIRED")
    runtime = env.get("VR4_PREVIEW_RUNTIME")
    require(runtime in ("LOCAL_SMOKE", "RENDER"), "RUNTIME_REQUIRED")
    require((os.name == "nt") == (runtime == "LOCAL_SMOKE"), "RUNTIME_PLATFORM")
    for key in ("DATABASE_URL", "DUAL_WRITE_TABLES"):
        require(env.get(key) == "", "BACKEND_NOT_EMPTY_" + key)
    for key in FLAGS:
        require(env.get(key) == "false", "FLAG_NOT_FALSE_" + key)
    require(env.get("FLASK_DEBUG", "0") == "0", "DEBUG_FORBIDDEN")
    require(env.get("FLASK_TESTING", "false") == "false", "TESTING_FORBIDDEN")
    root = Path(env.get("VR4_PREVIEW_ROOT", ""))
    database = Path(env.get("APP_DB_PATH", ""))
    require(root.is_absolute() and database.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
    plain_path(root)
    plain_path(database)
    require(".." not in root.parts and ".." not in database.parts, "PATH_TRAVERSAL")
    root, database = root.resolve(), database.resolve()
    if runtime == "RENDER":
        require(root == RENDER_ROOT, "ROOT_NOT_AUTHORIZED")
        commit = env.get("RENDER_GIT_COMMIT", "")
        require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "RENDER_COMMIT_REQUIRED")
    else:
        require(root.is_relative_to(WINDOWS_ROOT), "ROOT_NOT_AUTHORIZED")
        commit = "LOCAL_SMOKE"
    require(database == root / "fixture.sqlite3", "DATABASE_NOT_AUTHORIZED")
    username = env.get("VR4_PREVIEW_ADMIN_USERNAME", "")
    password = env.get("VR4_PREVIEW_ADMIN_PASSWORD", "")
    secret = env.get("APP_SECRET_KEY", "")
    require(re.fullmatch(r"[a-z][a-z0-9._-]{3,63}", username) is not None and
            username != "admin", "ADMIN_USERNAME_REQUIRED")
    require(24 <= len(password) <= 128 and len(set(password)) >= 12 and
            "\x00" not in password, "STRONG_ADMIN_PASSWORD_REQUIRED")
    require(43 <= len(secret) <= 256 and len(set(secret)) >= 16 and
            "\x00" not in secret and secret != password, "STRONG_APP_SECRET_REQUIRED")
    return Contract(root, database, runtime, commit, username, password, secret)


@contextmanager
def readonly(contract):
    conn = sqlite3.connect(contract.database.as_uri() + "?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    finally:
        conn.close()


def verify_identity(conn, contract):
    try:
        rows = dict(conn.execute("SELECT key,value FROM main.meta WHERE key IN "
                                "('vr4_preview_identity','vr4_preview_state',"
                                "'vr4_preview_instance','vr4_preview_admin','excel_seeded')"))
        require(rows.get(MARKER) == IDENTITY and rows.get("vr4_preview_state") == "ready"
                and rows.get("excel_seeded") == IDENTITY and
                rows.get("vr4_preview_admin") == contract.username, "FIXTURE_IDENTITY_MISMATCH")
        instance = rows.get("vr4_preview_instance", "")
        require(str(uuid.UUID(instance)) == instance, "FIXTURE_INSTANCE_INVALID")
        return instance
    except (sqlite3.Error, ValueError, TypeError):
        raise PreviewRejected("UNKNOWN_OR_INCOMPLETE_DATABASE") from None


def install_storage_guard(contract):
    """Fail closed on accidental product fallback or Excel file access."""
    excel = Path(__file__).resolve().parents[2] / "source.xlsx"

    def audit(event, arguments):
        if event == "sqlite3.connect":
            raw = str(arguments[0])
            path = Path(url2pathname(unquote(urlsplit(raw).path))
                        if raw.startswith("file:") else raw)
            require(path.is_absolute() and path.resolve() == contract.database,
                    "SQLITE_OUTSIDE_FIXTURE")
            plain_path(path)
        elif event == "open" and isinstance(arguments[0], (str, bytes, os.PathLike)):
            require(Path(os.fsdecode(arguments[0])).resolve() != excel, "EXCEL_READ_FORBIDDEN")

    sys.addaudithook(audit)


@contextmanager
def prepare(contract):
    """Own one startup lock; refuse unknown/partial DBs, never rebuild them."""
    contract.root.mkdir(parents=True, exist_ok=True)
    plain_path(contract.root)
    lock = contract.root / "startup.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise PreviewRejected("STARTUP_LOCK_EXISTS") from None
    try:
        fresh = not contract.database.exists()
        if not fresh:
            with readonly(contract) as conn:
                instance = verify_identity(conn, contract)
                from werkzeug.security import check_password_hash
                user = conn.execute("SELECT role,password_hash FROM users WHERE username=?",
                                    (contract.username,)).fetchone()
                require(user is not None and user[0] == "admin" and
                        check_password_hash(user[1], contract.password), "FIXTURE_ADMIN_MISMATCH")
        else:
            # An orphan journal is also an unknown predecessor, not a fresh fixture.
            require(not any(Path(str(contract.database) + suffix).exists()
                            for suffix in ("-wal", "-shm", "-journal")), "ORPHAN_SQLITE_SIDECAR")
            instance = str(uuid.uuid4())
            fd_db = os.open(contract.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd_db)
            with sqlite3.connect(contract.database) as conn:
                conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
                conn.executemany("INSERT INTO meta VALUES(?,?)", [
                    (MARKER, IDENTITY), ("excel_seeded", IDENTITY),
                    ("vr4_preview_state", "initializing"), ("vr4_preview_instance", instance),
                    ("vr4_preview_admin", contract.username)])
        yield fresh, instance
    finally:
        os.close(fd)
        lock.unlink()


def finish_fixture(application, contract, fresh):
    """Use original schema/bootstrap and roster service; no old test imports."""
    from services import vendor_roster_service as roster
    from werkzeug.security import generate_password_hash

    require(application.DB_PATH == contract.database, "APP_DATABASE_MISMATCH")
    require(not application.app.testing and not application.app.debug, "APP_DEBUG_OR_TESTING")
    if fresh:
        with sqlite3.connect(contract.database) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            # Keep the reserved name so bootstrap cannot recreate its known password.
            conn.execute("UPDATE users SET password_hash=?,role='member' WHERE username='admin'",
                         (generate_password_hash(secrets.token_urlsafe(48)),))
            conn.execute("INSERT INTO users(username,display_name,password_hash,role) VALUES(?,?,?,'admin')",
                         (contract.username, "預覽管理員", generate_password_hash(contract.password)))
            conn.execute("UPDATE sites SET is_active=0")
            conn.executemany("INSERT INTO sites(id,site_name,site_code) VALUES(?,?,?)",
                             [(101, "預覽工地甲", "PREVIEW-A"), (102, "預覽工地乙", "PREVIEW-B")])
            conn.executemany("INSERT INTO sheets(id,name,site_id,sort_order) VALUES(?,?,?,?)",
                             [(201, "甲區施工表", 101, 1), (202, "甲區補充表", 101, 2), (203, "乙區施工表", 102, 1)])
            tasks = [(301, 201, 101, VENDORS[0][1], "室內", "甲廠商油漆"),
                     (302, 201, 102, VENDORS[1][1], "室內", "乙廠商配線"),
                     (303, 202, 103, VENDORS[1][1], "公區", "乙廠商照明"),
                     (304, 203, 104, VENDORS[1][1], "室內", "乙廠商測試"),
                     (305, 203, 105, VENDORS[0][1], "室內", "甲廠商修補"),
                     (306, 201, 106, VENDORS[1][1], "室內", "乙廠商插座")]
            conn.executemany("INSERT INTO tasks(id,sheet_id,col_index,vendor,location,name) VALUES(?,?,?,?,?,?)", tasks)
            roster.initialize_schema(conn)
            roster.apply_roster(conn, [dict(tax_id=tax, legal_name=name, display_name=name,
                aliases=[], source=dict(document=IDENTITY, version="r01", sheet="synthetic",
                    source_original_name=name, row=i)) for i, (tax, name) in enumerate(VENDORS, 1)],
                task_ids=[row[0] for row in tasks])
            application.ensure_extra_fields(conn)
            conn.execute("UPDATE meta SET value='ready' WHERE key='vr4_preview_state'")
    with readonly(contract) as conn:
        verify_identity(conn, contract)
        require(application._vendor_organization_schema_state(conn) == "all_exact", "CORE_SCHEMA_MISMATCH")
        default = conn.execute("SELECT role,password_hash FROM users WHERE username='admin'").fetchone()
        from werkzeug.security import check_password_hash
        require(default is not None and default[0] == "member" and
                not check_password_hash(default[1], "admin"), "DEFAULT_ACCOUNT_NOT_DISABLED")
        require(not conn.execute("PRAGMA foreign_key_check").fetchall(), "FIXTURE_FOREIGN_KEY_FAILURE")
