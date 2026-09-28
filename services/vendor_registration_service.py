"""Inactive backend registration, without connections, app imports or grants.

The controller owns a fresh BEGIN IMMEDIATE transaction with foreign keys ON.
Name rejection uses the running Python Unicode data, not an AUTH global claim.
"""

import re
import sqlite3
import unicodedata

from werkzeug.security import generate_password_hash

from services import vendor_roster_service as roster


class RegistrationError(ValueError):
    pass


class PrerequisiteError(RegistrationError):
    pass


UNICODE_VERSION = unicodedata.unidata_version
FIELDS = frozenset({"company_name", "tax_id", "username", "password", "confirm_password"})
PUBLIC_FIELDS = frozenset({"vendor_id", "username", "password", "confirm_password", "csrf_token"})
SELECTION_FIELDS = PUBLIC_FIELDS - {"csrf_token"}
REQUEST_SCHEMA = """CREATE TABLE vendor_registration_requests (
    account_id INTEGER NOT NULL PRIMARY KEY REFERENCES vendor_accounts(id) ON DELETE RESTRICT,
    requested_vendor_id TEXT NOT NULL REFERENCES vendor_profiles(vendor_id) ON DELETE RESTRICT,
    submitted_company_name TEXT NOT NULL CHECK(length(trim(submitted_company_name)) > 0),
    submitted_tax_id TEXT NOT NULL CHECK(length(submitted_tax_id) = 8 AND submitted_tax_id NOT GLOB '*[^0-9]*'),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT"""
REGISTRY_TABLES = ("global_identities", "login_identifier_aliases", "backend_principal_mappings")


def _sql_key(sql):
    return " ".join(sql.replace("IF NOT EXISTS ", "").split()).rstrip(";")


def request_schema_state(conn):
    row = conn.execute("SELECT type,sql FROM main.sqlite_schema WHERE name='vendor_registration_requests'").fetchone()
    if row is None:
        return "absent"
    if row[0] != "table" or _sql_key(row[1]) != _sql_key(REQUEST_SCHEMA):
        raise PrerequisiteError("申請資訊結構不相容")
    for schema in ("main", "temp"):
        if conn.execute(f"SELECT 1 FROM {schema}.sqlite_schema WHERE type='trigger' AND tbl_name='vendor_registration_requests'").fetchone():
            raise PrerequisiteError("申請資訊結構不相容")
    return "ready"


def validate(values):
    if not isinstance(values, dict) or set(values) != FIELDS or any(not isinstance(v, str) for v in values.values()):
        raise RegistrationError("申請欄位缺少或不支援")
    company = values["company_name"].strip()
    tax_id = values["tax_id"]
    username = values["username"].strip()
    password = values["password"]
    if not company or len(company) > 200 or "\x00" in company:
        raise RegistrationError("請填寫完整公司名稱（最多 200 字）")
    if re.fullmatch(r"[0-9]{8}", tax_id) is None:
        raise RegistrationError("統編須為完整八碼半形數字，請保留前導零")
    if re.fullmatch(r"[a-z][a-z0-9._-]{3,63}", username) is None:
        raise RegistrationError("帳號須為 4–64 字元，以小寫英文字母開頭，只含小寫英文、數字、點、底線或連字號")
    if not 12 <= len(password) <= 128 or "\x00" in password:
        raise RegistrationError("密碼須為 12–128 字元")
    if password != values["confirm_password"]:
        raise RegistrationError("兩次密碼不一致")
    return company, tax_id, username, password


def _backend_schema(conn):
    for table, required in {
        "users": {"id": "INTEGER", "username": "TEXT", "password_hash": "TEXT", "role": "TEXT"},
        "vendor_accounts": {"id": "INTEGER", "username": "TEXT", "password_hash": "TEXT",
                            "vendor_name": "TEXT", "is_active": "INTEGER",
                            "created_at": "TEXT", "updated_at": "TEXT"},
    }.items():
        kind = conn.execute("SELECT type FROM main.sqlite_schema WHERE name=?", (table,)).fetchone()
        columns = {r[1]: r for r in conn.execute(f"PRAGMA main.table_info({table})")}
        if (kind is None or kind[0] != "table" or not required.keys() <= columns.keys() or
                any(columns[k][2].upper() != t for k, t in required.items()) or columns["id"][5] != 1 or
                any(not columns[k][3] for k in required if k != "id")):
            raise PrerequisiteError("既有帳號資料前提不足或不相容")
        unique_username = False
        for index in conn.execute(f"PRAGMA main.index_list({table})"):
            if index[2] and not index[4]:
                index_name = index[1].replace('"', '""')
                if [r[2] for r in conn.execute(f'PRAGMA main.index_info("{index_name}")')] == ["username"]:
                    unique_username = True
        if not unique_username:
            raise PrerequisiteError("既有帳號名稱約束不相容")
    for schema in ("main", "temp"):
        if conn.execute(f"SELECT 1 FROM {schema}.sqlite_schema WHERE type='trigger' AND tbl_name='vendor_accounts'").fetchone():
            raise PrerequisiteError("既有帳號寫入結構不相容")


def _name_keys(value):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise PrerequisiteError("既有登入名稱資料不完整")
    trimmed = value.strip()
    normalized = unicodedata.normalize("NFKC", trimmed)
    return {value, trimmed.casefold(), normalized.casefold(),
            unicodedata.normalize("NFKC", trimmed.casefold()).strip(),
            unicodedata.normalize("NFKC", normalized.casefold()).strip()}


def _reject_collisions(conn, username, registry_schema):
    names = []
    for table in ("users", "vendor_accounts"):
        names.extend(row[0] for row in conn.execute(f"SELECT username FROM main.{table}"))
    present = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT name,type,sql FROM main.sqlite_schema WHERE name IN (?,?,?)", REGISTRY_TABLES)}
    if present:
        if set(present) != set(REGISTRY_TABLES):
            raise PrerequisiteError("登入名稱來源不完整，請由管理者處理")
        expected = {name: next((statement for statement in registry_schema
                    if re.search(r"CREATE TABLE IF NOT EXISTS " + name + r"\s*\(", statement)), None)
                    for name in REGISTRY_TABLES}
        for name, (kind, sql) in present.items():
            if kind != "table" or expected[name] is None or _sql_key(sql) != _sql_key(expected[name]):
                raise PrerequisiteError("登入名稱來源不相容，請由管理者處理")
            if conn.execute(f"PRAGMA main.foreign_key_check({name})").fetchone():
                raise PrerequisiteError("登入名稱來源關係不完整")
        for row in conn.execute("SELECT raw_alias,normalized_lookup_key FROM main.login_identifier_aliases"):
            names.extend(row)
    # Inspect every source, including disabled/superseded aliases. No winner selection.
    collisions = [username in _name_keys(name) for name in names]
    if any(collisions):
        raise RegistrationError("此帳號名稱無法使用，請改用其他名稱")


def register(conn, values, *, core_state, registry_schema):
    """No commit here. The caller must hold its SQLite writer reservation."""
    company, tax_id, username, password = validate(values)
    if not isinstance(conn, sqlite3.Connection) or not conn.in_transaction:
        raise PrerequisiteError("註冊需要獨立寫入交易")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise PrerequisiteError("註冊需要外鍵保護")
    conn.execute("SAVEPOINT vr4_registration")
    try:
        if core_state(conn) != "all_exact":
            raise PrerequisiteError("核心廠商資料前提不足或不相容")
        _backend_schema(conn)
        try:
            profiles = roster.list_profiles(conn)
        except roster.RosterError as exc:
            raise PrerequisiteError("公司名冊前提不足或不相容") from exc
        matches = [p for p in profiles if p["legal_name"] == company and p["tax_id"] == tax_id]
        if len(matches) != 1:
            raise RegistrationError("公司名稱與統編無法受理，請核對後再送出或聯絡管理者")
        vendor_id = matches[0]["vendor_id"]
        status = conn.execute("SELECT organization_status FROM main.vendor_organizations WHERE vendor_id=?", (vendor_id,)).fetchone()
        if status is None or status[0] != "disabled":
            raise RegistrationError("公司名稱與統編無法受理，請核對後再送出或聯絡管理者")
        _reject_collisions(conn, username, registry_schema)
        state = request_schema_state(conn)
        if state == "absent":
            conn.execute(REQUEST_SCHEMA)
        account_id = conn.execute("""INSERT INTO main.vendor_accounts
            (username,password_hash,vendor_name,is_active) VALUES(?,?,?,0)""",
            (username, generate_password_hash(password), company)).lastrowid
        conn.execute("""INSERT INTO main.vendor_registration_requests
            (account_id,requested_vendor_id,submitted_company_name,submitted_tax_id) VALUES(?,?,?,?)""",
            (account_id, vendor_id, company, tax_id))
        conn.execute("RELEASE SAVEPOINT vr4_registration")
        return {"username": username, "company_name": company, "tax_id": tax_id}
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT vr4_registration")
        conn.execute("RELEASE SAVEPOINT vr4_registration")
        raise


def _eligible_profiles(conn, *, core_state):
    """Read in the caller's explicit transaction; never initialize the roster."""
    if not isinstance(conn, sqlite3.Connection) or not conn.in_transaction:
        raise PrerequisiteError("讀取公司名冊需要明確交易")
    if core_state(conn) != "all_exact":
        raise PrerequisiteError("核心廠商資料前提不足或不相容")
    try:
        profiles = roster.list_profiles(conn)
    except roster.RosterError as exc:
        raise PrerequisiteError("公司名冊前提不足或不相容") from exc
    if len({p["vendor_id"] for p in profiles}) != len(profiles):
        raise PrerequisiteError("公司名冊有重複識別，無法受理")
    disabled = {row[0] for row in conn.execute(
        "SELECT vendor_id FROM main.vendor_organizations WHERE organization_status='disabled'")}
    return [p for p in profiles if p["vendor_id"] in disabled and len(p["legal_name"]) <= 200]


def registration_choices(conn, *, core_state):
    """The public projection contains no tax IDs, aliases or provenance."""
    return sorted(({key: p[key] for key in ("vendor_id", "display_name", "legal_name")}
                   for p in _eligible_profiles(conn, core_state=core_state)),
                  key=lambda p: (p["display_name"], p["legal_name"], p["vendor_id"]))


def register_selected(conn, values, *, core_state, registry_schema):
    """Resolve the claimed company under BEGIN IMMEDIATE, then use the core."""
    if (not isinstance(values, dict) or set(values) != SELECTION_FIELDS or
            any(not isinstance(v, str) for v in values.values())):
        raise RegistrationError("申請欄位缺少或不支援")
    if not values["vendor_id"].strip():
        raise RegistrationError("請選擇公司")
    matches = [p for p in _eligible_profiles(conn, core_state=core_state)
               if p["vendor_id"] == values["vendor_id"]]
    if len(matches) != 1:
        raise RegistrationError("所選公司已失效或目前無法申請，請重新選擇公司")
    profile = matches[0]
    canonical = {key: values[key] for key in ("username", "password", "confirm_password")}
    canonical.update(company_name=profile["legal_name"], tax_id=profile["tax_id"])
    return register(conn, canonical, core_state=core_state, registry_schema=registry_schema)
