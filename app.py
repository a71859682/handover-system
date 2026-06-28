from __future__ import annotations

import os
import sqlite3
import uuid
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from flask import Flask, flash, g, has_app_context, jsonify, redirect, render_template, request, session, url_for
from openpyxl import load_workbook
from werkzeug.security import check_password_hash, generate_password_hash
from database import init_database
from sqlite_db_path import get_sqlite_db_path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = get_sqlite_db_path()
SOURCE_XLSX = BASE_DIR / "source.xlsx"
MAX_WORK_COL = 60  # D:BH
DONE_VALUE = "O"
WORKING_VALUE = "X"
BUILTIN_EXTRA_FIELDS = {
    "initial_check": {"name": "初驗時間", "type": "date", "sort_order": 1},
    "recheck_1": {"name": "複驗1", "type": "date", "sort_order": 2},
    "recheck_2": {"name": "複驗2", "type": "date", "sort_order": 3},
    "handover": {"name": "已交屋", "type": "status", "sort_order": 4},
}
EXTRA_FIELDS = tuple(BUILTIN_EXTRA_FIELDS)
EXTRA_FIELD_TYPES = ("date", "status")

DEFAULT_SETTINGS = {
    "site_title": "大英營造-新埔段",
    "sheet_title": "內裝管制表",
    "tab_title": "內裝管制表(室內)",
    "instruction_text": "子項目輸入 O 代表完成；X 代表施作中或未開始。",
    "floor_header": "樓層",
    "count_header": "戶數",
    "unit_header": "棟別/戶別",
    "vendor_header": "廠商",
    "task_header": "工項",
}
DUAL_WRITE_FLOORS_STRATEGY_LOG = (
    "DUAL_WRITE_FLOORS_SECONDARY table=floors strategy=reuse_primary_postgres_connection"
)
DUAL_WRITE_USERS_STRATEGY_LOG = (
    "DUAL_WRITE_USERS_SECONDARY table=users strategy=reuse_primary_postgres_connection"
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "dev-secret-change-me")
ASSET_VERSION = "20260627-010"
_USERS_READ_COMPARE_ORM_READY = False


@app.context_processor
def inject_asset_version():
    return {"asset_version": ASSET_VERSION}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def dual_write_tables() -> set[str]:
    raw = os.environ.get("DUAL_WRITE_TABLES", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def controlled_dual_write_enabled(*, table: str, operation: str) -> bool:
    if not env_flag("DUAL_WRITE_ENABLED"):
        return False
    if env_flag("USE_SQLALCHEMY_WRITES"):
        return False
    if operation == "update":
        return table in dual_write_tables()
    if operation in {"create", "delete"} and table == "users":
        return table in dual_write_tables()
    return False


def dual_write_dry_run_enabled() -> bool:
    return env_flag("DUAL_WRITE_DRY_RUN")


def dual_write_strict_enabled() -> bool:
    return env_flag("DUAL_WRITE_STRICT")


def dual_write_log(message: str) -> None:
    print(message, flush=True)


def users_read_compare_enabled() -> bool:
    return env_flag("USERS_READ_COMPARE")


def _ensure_users_read_compare_orm_ready() -> None:
    global _USERS_READ_COMPARE_ORM_READY
    if _USERS_READ_COMPARE_ORM_READY:
        return

    app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{DB_PATH.resolve().as_posix()}")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    init_database(app)
    _USERS_READ_COMPARE_ORM_READY = True


def _run_with_app_context(fn):
    if has_app_context():
        return fn()
    with app.app_context():
        return fn()


def _user_row_payload(
    row: sqlite3.Row | object | None,
    *,
    include_password_hash: bool,
) -> dict[str, object] | None:
    if row is None:
        return None

    is_mapping = isinstance(row, sqlite3.Row) or isinstance(row, dict)
    payload = {
        "id": row["id"] if is_mapping else row.id,
        "username": row["username"] if is_mapping else row.username,
        "display_name": row["display_name"] if is_mapping else row.display_name,
        "role": row["role"] if is_mapping else row.role,
        "created_at": row["created_at"] if is_mapping else row.created_at,
    }
    if include_password_hash:
        payload["password_hash"] = row["password_hash"] if is_mapping else row.password_hash
    return payload


def _list_user_row_payload(row: sqlite3.Row | object) -> dict[str, object]:
    is_mapping = isinstance(row, sqlite3.Row) or isinstance(row, dict)
    return {
        "id": row["id"] if is_mapping else row.id,
        "username": row["username"] if is_mapping else row.username,
        "display_name": row["display_name"] if is_mapping else row.display_name,
        "role": row["role"] if is_mapping else row.role,
        "created_at": row["created_at"] if is_mapping else row.created_at,
    }


def _sqlite_get_user_by_username(username: str) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute(
            """
            SELECT id, username, display_name, password_hash, role, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()


def _sqlite_get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute(
            """
            SELECT id, username, display_name, password_hash, role, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()


def _sqlite_list_users() -> list[sqlite3.Row]:
    with db() as conn:
        return conn.execute(
            """
            SELECT id, username, display_name, role, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()


def _shadow_get_user_by_username(username: str):
    from services.users_orm_service import get_user_by_username_orm

    _ensure_users_read_compare_orm_ready()
    return _run_with_app_context(lambda: get_user_by_username_orm(username))


def _shadow_get_user_by_id(user_id: int):
    from services.users_orm_service import get_user_by_id_orm

    _ensure_users_read_compare_orm_ready()
    return _run_with_app_context(lambda: get_user_by_id_orm(user_id))


def _shadow_list_users():
    from services.users_orm_service import list_users_orm

    _ensure_users_read_compare_orm_ready()
    return _run_with_app_context(list_users_orm)


def _log_users_read_compare_match(*, helper: str, key: str | None = None) -> None:
    message = f"USERS_READ_COMPARE helper={helper}"
    if key:
        message += f" key={key}"
    message += " status=match"
    dual_write_log(message)


def _log_users_read_compare_mismatch(*, helper: str, fields: list[str], key: str | None = None) -> None:
    message = f"USERS_READ_COMPARE helper={helper}"
    if key:
        message += f" key={key}"
    message += f" status=mismatch fields={','.join(fields)}"
    dual_write_log(message)


def _compare_user_lookup(
    *,
    helper: str,
    key: str,
    primary_row: sqlite3.Row | None,
    shadow_row,
    log_result: bool,
) -> dict[str, object]:
    primary_payload = _user_row_payload(primary_row, include_password_hash=True)
    shadow_payload = _user_row_payload(shadow_row, include_password_hash=True)
    mismatch_fields: list[str] = []

    if (primary_payload is None) != (shadow_payload is None):
        mismatch_fields.append("exists")
    elif primary_payload and shadow_payload:
        for field_name in ("id", "username", "display_name", "role", "created_at"):
            if primary_payload[field_name] != shadow_payload[field_name]:
                mismatch_fields.append(field_name)
        if primary_payload["password_hash"] != shadow_payload["password_hash"]:
            mismatch_fields.append("password_hash_match")

    result = {
        "helper": helper,
        "key": key,
        "status": "match" if not mismatch_fields else "mismatch",
        "fields": mismatch_fields,
        "exists_match": (primary_payload is None) == (shadow_payload is None),
        "password_hash_match": "password_hash_match" not in mismatch_fields,
    }
    if log_result:
        if mismatch_fields:
            _log_users_read_compare_mismatch(helper=helper, key=key, fields=mismatch_fields)
        else:
            _log_users_read_compare_match(helper=helper, key=key)
    return result


def _compare_list_users(*, primary_rows: list[sqlite3.Row], shadow_rows, log_result: bool) -> dict[str, object]:
    primary_payloads = [_list_user_row_payload(row) for row in primary_rows]
    shadow_payloads = [_list_user_row_payload(row) for row in shadow_rows]
    row_count_match = len(primary_payloads) == len(shadow_payloads)
    primary_ids = [row["id"] for row in primary_payloads]
    shadow_ids = [row["id"] for row in shadow_payloads]
    ordered_ids_match = primary_ids == shadow_ids
    detail_mismatches: list[dict[str, object]] = []

    shadow_by_id = {row["id"]: row for row in shadow_payloads}
    for primary_row in primary_payloads:
        row_id = primary_row["id"]
        shadow_row = shadow_by_id.get(row_id)
        mismatch_fields: list[str] = []
        if shadow_row is None:
            mismatch_fields.append("missing_in_shadow")
        else:
            for field_name in ("username", "display_name", "role", "created_at"):
                if primary_row[field_name] != shadow_row[field_name]:
                    mismatch_fields.append(field_name)
        if mismatch_fields:
            detail_mismatches.append({"id": row_id, "fields": mismatch_fields})

    primary_id_set = set(primary_ids)
    for shadow_row in shadow_payloads:
        if shadow_row["id"] not in primary_id_set:
            detail_mismatches.append({"id": shadow_row["id"], "fields": ["missing_in_primary"]})

    status = "match" if row_count_match and ordered_ids_match and not detail_mismatches else "mismatch"
    result = {
        "helper": "list_users",
        "status": status,
        "row_count_match": row_count_match,
        "ordered_ids_match": ordered_ids_match,
        "details": detail_mismatches,
    }

    if log_result:
        if status == "match":
            dual_write_log("USERS_READ_COMPARE helper=list_users status=match")
        else:
            dual_write_log(
                "USERS_READ_COMPARE helper=list_users "
                f"status=mismatch row_count_match={str(row_count_match).lower()} "
                f"ordered_ids_match={str(ordered_ids_match).lower()}"
            )
            for detail in detail_mismatches:
                dual_write_log(
                    "USERS_READ_COMPARE_DETAIL helper=list_users "
                    f"id={detail['id']} status=mismatch fields={','.join(detail['fields'])}"
                )
    return result


def run_users_read_compare_by_username(username: str, *, log_result: bool = False) -> dict[str, object]:
    primary_row = _sqlite_get_user_by_username(username)
    try:
        shadow_row = _shadow_get_user_by_username(username)
    except Exception:
        result = {
            "helper": "get_user_by_username",
            "key": f"username:{username}",
            "status": "mismatch",
            "fields": ["compare_error"],
            "exists_match": False,
            "password_hash_match": False,
        }
        if log_result:
            _log_users_read_compare_mismatch(
                helper="get_user_by_username",
                key=f"username:{username}",
                fields=["compare_error"],
            )
        return result
    return _compare_user_lookup(
        helper="get_user_by_username",
        key=f"username:{username}",
        primary_row=primary_row,
        shadow_row=shadow_row,
        log_result=log_result,
    )


def run_users_read_compare_by_id(user_id: int, *, log_result: bool = False) -> dict[str, object]:
    primary_row = _sqlite_get_user_by_id(user_id)
    try:
        shadow_row = _shadow_get_user_by_id(user_id)
    except Exception:
        result = {
            "helper": "get_user_by_id",
            "key": f"id:{user_id}",
            "status": "mismatch",
            "fields": ["compare_error"],
            "exists_match": False,
            "password_hash_match": False,
        }
        if log_result:
            _log_users_read_compare_mismatch(
                helper="get_user_by_id",
                key=f"id:{user_id}",
                fields=["compare_error"],
            )
        return result
    return _compare_user_lookup(
        helper="get_user_by_id",
        key=f"id:{user_id}",
        primary_row=primary_row,
        shadow_row=shadow_row,
        log_result=log_result,
    )


def run_users_list_compare(*, log_result: bool = False) -> dict[str, object]:
    primary_rows = _sqlite_list_users()
    try:
        shadow_rows = _shadow_list_users()
    except Exception:
        result = {
            "helper": "list_users",
            "status": "mismatch",
            "row_count_match": False,
            "ordered_ids_match": False,
            "details": [{"id": -1, "fields": ["compare_error"]}],
        }
        if log_result:
            dual_write_log(
                "USERS_READ_COMPARE helper=list_users status=mismatch "
                "row_count_match=false ordered_ids_match=false"
            )
            dual_write_log(
                "USERS_READ_COMPARE_DETAIL helper=list_users id=-1 status=mismatch fields=compare_error"
            )
        return result
    return _compare_list_users(primary_rows=primary_rows, shadow_rows=shadow_rows, log_result=log_result)


def get_primary_postgres_connection() -> psycopg.Connection:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for PostgreSQL secondary writes.")
    scheme = urlsplit(database_url).scheme.lower()
    if scheme not in {"postgresql", "postgres"}:
        raise RuntimeError(f"DATABASE_URL must point to PostgreSQL, got scheme '{scheme or 'missing'}'.")

    pg_conn = getattr(g, "_dual_write_pg_conn", None)
    if pg_conn is None or pg_conn.closed:
        pg_conn = psycopg.connect(database_url)
        g._dual_write_pg_conn = pg_conn
    return pg_conn


@app.teardown_appcontext
def close_primary_postgres_connection(exc: BaseException | None) -> None:
    pg_conn = g.pop("_dual_write_pg_conn", None)
    if pg_conn is None or pg_conn.closed:
        return
    try:
        if exc is None:
            pg_conn.commit()
        else:
            pg_conn.rollback()
    finally:
        pg_conn.close()


def update_floor_fields_sqlite(
    conn: sqlite3.Connection,
    floor_id: int,
    *,
    name: str,
    block_name: str,
) -> None:
    conn.execute(
        "UPDATE floors SET name = ?, block_name = ? WHERE id = ?",
        (name, block_name, floor_id),
    )


def update_user_display_name_sqlite(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    display_name: str,
) -> None:
    conn.execute(
        "UPDATE users SET display_name = ? WHERE id = ?",
        (display_name, user_id),
    )


def update_user_role_sqlite(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    role: str,
) -> None:
    conn.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (role, user_id),
    )


def create_user_sqlite(
    conn: sqlite3.Connection,
    *,
    username: str,
    display_name: str,
    password_hash: str,
    role: str,
) -> dict[str, object]:
    cur = conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        (username, display_name, password_hash, role),
    )
    row = conn.execute(
        """
        SELECT id, username, display_name, password_hash, role, created_at
        FROM users
        WHERE id = ?
        """,
        (cur.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"SQLite users primary create could not reload id={cur.lastrowid}.")
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def is_protected_user_row(user_row: sqlite3.Row | dict[str, object]) -> bool:
    return (
        int(user_row["id"]) == 1
        or str(user_row["username"]) == "admin"
        or str(user_row["role"]) == "admin"
    )


def delete_user_sqlite(
    conn: sqlite3.Connection,
    user_id: int,
) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT id, username, display_name, password_hash, role, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"SQLite users primary delete could not find id={user_id}.")
    if is_protected_user_row(row):
        raise ValueError(f"SQLite users primary delete refused protected id={user_id}.")
    cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if cur.rowcount != 1:
        raise RuntimeError(f"SQLite users primary delete affected {cur.rowcount} rows for user_id={user_id}.")
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def update_floor_fields_postgres(
    pg_conn: psycopg.Connection,
    floor_id: int,
    *,
    name: str,
    block_name: str,
) -> None:
    savepoint_name = f"dual_write_floors_update_{floor_id}"
    dual_write_log(f"{DUAL_WRITE_FLOORS_STRATEGY_LOG} floor_id={floor_id}")
    with pg_conn.cursor() as cur:
        dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=SAVEPOINT_START floor_id={floor_id}")
        cur.execute(f"SAVEPOINT {savepoint_name}")
        dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=SAVEPOINT_OK floor_id={floor_id}")
        try:
            dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=EXECUTE_SQL_START floor_id={floor_id}")
            cur.execute(
                "UPDATE floors SET name = %s, block_name = %s WHERE id = %s",
                (name, block_name, floor_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"PostgreSQL floors secondary update affected {cur.rowcount} rows for floor_id={floor_id}."
                )
            dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=EXECUTE_SQL_OK floor_id={floor_id}")
            cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            dual_write_log(
                f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=RELEASE_SAVEPOINT_OK floor_id={floor_id}"
            )
            pg_conn.commit()
        except Exception:
            try:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            finally:
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            pg_conn.commit()
            raise


def update_user_display_name_postgres(
    pg_conn: psycopg.Connection,
    user_id: int,
    *,
    display_name: str,
) -> None:
    savepoint_name = f"dual_write_users_update_{user_id}"
    dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} user_id={user_id}")
    with pg_conn.cursor() as cur:
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_START user_id={user_id}")
        cur.execute(f"SAVEPOINT {savepoint_name}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_OK user_id={user_id}")
        try:
            dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_START user_id={user_id}")
            cur.execute(
                "UPDATE users SET display_name = %s WHERE id = %s",
                (display_name, user_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"PostgreSQL users secondary update affected {cur.rowcount} rows for user_id={user_id}."
                )
            dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_OK user_id={user_id}")
            cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            dual_write_log(
                f"DUAL_WRITE_USERS_SECONDARY table=users event=RELEASE_SAVEPOINT_OK user_id={user_id}"
            )
            pg_conn.commit()
        except Exception:
            try:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            finally:
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            pg_conn.commit()
            raise


def update_user_role_postgres(
    pg_conn: psycopg.Connection,
    user_id: int,
    *,
    role: str,
) -> None:
    savepoint_name = f"dual_write_users_update_{user_id}"
    dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} user_id={user_id}")
    with pg_conn.cursor() as cur:
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_START user_id={user_id}")
        cur.execute(f"SAVEPOINT {savepoint_name}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_OK user_id={user_id}")
        try:
            dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_START user_id={user_id}")
            cur.execute(
                "UPDATE users SET role = %s WHERE id = %s",
                (role, user_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"PostgreSQL users secondary update affected {cur.rowcount} rows for user_id={user_id}."
                )
            dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_OK user_id={user_id}")
            cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            dual_write_log(
                f"DUAL_WRITE_USERS_SECONDARY table=users event=RELEASE_SAVEPOINT_OK user_id={user_id}"
            )
            pg_conn.commit()
        except Exception:
            try:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            finally:
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            pg_conn.commit()
            raise


def create_user_postgres(
    pg_conn: psycopg.Connection,
    *,
    id: int,
    username: str,
    display_name: str,
    password_hash: str,
    role: str,
    created_at: str,
) -> None:
    savepoint_name = f"dual_write_users_create_{id}"
    dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} operation=create user_id={id}")
    with pg_conn.cursor() as cur:
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=SAVEPOINT_START user_id={id}")
        cur.execute(f"SAVEPOINT {savepoint_name}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=SAVEPOINT_OK user_id={id}")
        try:
            dual_write_log(
                f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=EXECUTE_SQL_START user_id={id}"
            )
            cur.execute(
                """
                INSERT INTO users (id, username, display_name, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (id, username, display_name, password_hash, role, created_at),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"PostgreSQL users secondary create affected {cur.rowcount} rows for user_id={id}."
                )
            dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=EXECUTE_SQL_OK user_id={id}")
            cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            dual_write_log(
                f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=RELEASE_SAVEPOINT_OK user_id={id}"
            )
            pg_conn.commit()
        except Exception:
            try:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            finally:
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            pg_conn.commit()
            raise


def delete_user_postgres(
    pg_conn: psycopg.Connection,
    *,
    id: int,
    username: str,
) -> None:
    savepoint_name = f"dual_write_users_delete_{id}"
    dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} operation=delete user_id={id}")
    with pg_conn.cursor() as cur:
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=SAVEPOINT_START user_id={id}")
        cur.execute(f"SAVEPOINT {savepoint_name}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=SAVEPOINT_OK user_id={id}")
        try:
            dual_write_log(
                f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=EXECUTE_SQL_START user_id={id}"
            )
            cur.execute(
                "DELETE FROM users WHERE id = %s AND username = %s",
                (id, username),
            )
            if cur.rowcount == 0:
                dual_write_log(
                    "DUAL_WRITE_USERS_SECONDARY table=users operation=delete "
                    f"event=SECONDARY_NOT_FOUND user_id={id} username={username!r}"
                )
            elif cur.rowcount != 1:
                raise RuntimeError(
                    f"PostgreSQL users secondary delete affected {cur.rowcount} rows for user_id={id}."
                )
            dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=EXECUTE_SQL_OK user_id={id}")
            cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            dual_write_log(
                f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=RELEASE_SAVEPOINT_OK user_id={id}"
            )
            pg_conn.commit()
        except Exception:
            try:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            finally:
                cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            pg_conn.commit()
            raise


def maybe_dual_write_floor_update(
    floor_id: int,
    *,
    name: str,
    block_name: str,
) -> None:
    if not controlled_dual_write_enabled(table="floors", operation="update"):
        return

    dry_run = dual_write_dry_run_enabled()
    if dry_run:
        dual_write_log(f"DUAL_WRITE_DRY_RUN operation=update table=floors floor_id={floor_id}")
        dual_write_log(f"{DUAL_WRITE_FLOORS_STRATEGY_LOG} floor_id={floor_id}")
        dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=SAVEPOINT_START floor_id={floor_id}")
        dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=SAVEPOINT_OK floor_id={floor_id}")
        dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=EXECUTE_SQL_START floor_id={floor_id}")
        dual_write_log(f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=EXECUTE_SQL_OK floor_id={floor_id}")
        dual_write_log(
            f"DUAL_WRITE_FLOORS_SECONDARY table=floors event=RELEASE_SAVEPOINT_OK floor_id={floor_id}"
        )
        dual_write_log(
            "DUAL_WRITE operation=update table=floors "
            f"floor_id={floor_id} dry_run=true postgres_result=success"
        )
        return

    try:
        update_floor_fields_postgres(
            get_primary_postgres_connection(),
            floor_id,
            name=name,
            block_name=block_name,
        )
        dual_write_log(
            "DUAL_WRITE operation=update table=floors "
            f"floor_id={floor_id} dry_run=false postgres_result=success"
        )
    except Exception as exc:
        dual_write_log(
            "DUAL_WRITE operation=update table=floors "
            f"floor_id={floor_id} dry_run=false postgres_result=failed error={exc!r}"
        )
        if dual_write_strict_enabled():
            raise


def maybe_dual_write_user_display_name_update(
    user_id: int,
    *,
    display_name: str,
) -> None:
    if not controlled_dual_write_enabled(table="users", operation="update"):
        return

    dry_run = dual_write_dry_run_enabled()
    if dry_run:
        dual_write_log(f"DUAL_WRITE_DRY_RUN operation=update table=users user_id={user_id}")
        dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_START user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_OK user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_START user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_OK user_id={user_id}")
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users event=RELEASE_SAVEPOINT_OK user_id={user_id}"
        )
        dual_write_log(
            "DUAL_WRITE operation=update table=users "
            f"user_id={user_id} dry_run=true postgres_result=success"
        )
        return

    try:
        update_user_display_name_postgres(
            get_primary_postgres_connection(),
            user_id,
            display_name=display_name,
        )
        dual_write_log(
            "DUAL_WRITE operation=update table=users "
            f"user_id={user_id} dry_run=false postgres_result=success"
        )
    except Exception as exc:
        dual_write_log(
            "DUAL_WRITE operation=update table=users "
            f"user_id={user_id} dry_run=false postgres_result=failed error={exc!r}"
        )
        if dual_write_strict_enabled():
            raise


def maybe_dual_write_user_role_update(
    user_id: int,
    *,
    role: str,
) -> None:
    if not controlled_dual_write_enabled(table="users", operation="update"):
        return

    dry_run = dual_write_dry_run_enabled()
    if dry_run:
        dual_write_log(f"DUAL_WRITE_DRY_RUN operation=update table=users user_id={user_id}")
        dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_START user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=SAVEPOINT_OK user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_START user_id={user_id}")
        dual_write_log(f"DUAL_WRITE_USERS_SECONDARY table=users event=EXECUTE_SQL_OK user_id={user_id}")
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users event=RELEASE_SAVEPOINT_OK user_id={user_id}"
        )
        dual_write_log(
            "DUAL_WRITE operation=update table=users "
            f"user_id={user_id} dry_run=true postgres_result=success"
        )
        return

    try:
        update_user_role_postgres(
            get_primary_postgres_connection(),
            user_id,
            role=role,
        )
        dual_write_log(
            "DUAL_WRITE operation=update table=users "
            f"user_id={user_id} dry_run=false postgres_result=success"
        )
    except Exception as exc:
        dual_write_log(
            "DUAL_WRITE operation=update table=users "
            f"user_id={user_id} dry_run=false postgres_result=failed error={exc!r}"
        )
        if dual_write_strict_enabled():
            raise


def maybe_dual_write_user_create(user_row: dict[str, object]) -> None:
    if not controlled_dual_write_enabled(table="users", operation="create"):
        return

    user_id = int(user_row["id"])
    username = str(user_row["username"])
    dry_run = dual_write_dry_run_enabled()
    if dry_run:
        dual_write_log(
            f"DUAL_WRITE_DRY_RUN operation=create table=users user_id={user_id} username={username!r}"
        )
        dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} operation=create user_id={user_id}")
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=SAVEPOINT_START user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=SAVEPOINT_OK user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=EXECUTE_SQL_START user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=EXECUTE_SQL_OK user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=create event=RELEASE_SAVEPOINT_OK user_id={user_id}"
        )
        dual_write_log(
            "DUAL_WRITE operation=create table=users "
            f"user_id={user_id} username={username!r} dry_run=true postgres_result=success"
        )
        return

    try:
        create_user_postgres(
            get_primary_postgres_connection(),
            id=user_id,
            username=username,
            display_name=str(user_row["display_name"]),
            password_hash=str(user_row["password_hash"]),
            role=str(user_row["role"]),
            created_at=str(user_row["created_at"]),
        )
        dual_write_log(
            "DUAL_WRITE operation=create table=users "
            f"user_id={user_id} username={username!r} dry_run=false postgres_result=success"
        )
    except Exception as exc:
        dual_write_log(
            "DUAL_WRITE operation=create table=users "
            f"user_id={user_id} username={username!r} dry_run=false postgres_result=failed error={exc!r}"
        )
        if dual_write_strict_enabled():
            raise


def maybe_dual_write_user_delete(user_row: dict[str, object]) -> None:
    if not controlled_dual_write_enabled(table="users", operation="delete"):
        return

    user_id = int(user_row["id"])
    username = str(user_row["username"])
    dry_run = dual_write_dry_run_enabled()
    if dry_run:
        dual_write_log(
            f"DUAL_WRITE_DRY_RUN operation=delete table=users user_id={user_id} username={username!r}"
        )
        dual_write_log(f"{DUAL_WRITE_USERS_STRATEGY_LOG} operation=delete user_id={user_id}")
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=SAVEPOINT_START user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=SAVEPOINT_OK user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=EXECUTE_SQL_START user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=EXECUTE_SQL_OK user_id={user_id}"
        )
        dual_write_log(
            f"DUAL_WRITE_USERS_SECONDARY table=users operation=delete event=RELEASE_SAVEPOINT_OK user_id={user_id}"
        )
        dual_write_log(
            "DUAL_WRITE operation=delete table=users "
            f"user_id={user_id} username={username!r} dry_run=true postgres_result=success"
        )
        return

    try:
        delete_user_postgres(
            get_primary_postgres_connection(),
            id=user_id,
            username=username,
        )
        dual_write_log(
            "DUAL_WRITE operation=delete table=users "
            f"user_id={user_id} username={username!r} dry_run=false postgres_result=success"
        )
    except Exception as exc:
        dual_write_log(
            "DUAL_WRITE operation=delete table=users "
            f"user_id={user_id} username={username!r} dry_run=false postgres_result=failed error={exc!r}"
        )
        if dual_write_strict_enabled():
            raise


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute(sql, params).fetchone()


def get_user_by_username(username: str) -> sqlite3.Row | None:
    row = _sqlite_get_user_by_username(username)
    if users_read_compare_enabled():
        run_users_read_compare_by_username(username, log_result=True)
    return row


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    row = _sqlite_get_user_by_id(user_id)
    if users_read_compare_enabled():
        run_users_read_compare_by_id(user_id, log_result=True)
    return row


def list_users() -> list[sqlite3.Row]:
    rows = _sqlite_list_users()
    if users_read_compare_enabled():
        run_users_list_compare(log_result=True)
    return rows


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("需要管理員權限。", "error")
            return redirect(url_for("sheet"))
        return fn(*args, **kwargs)

    return wrapper


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            col_index INTEGER NOT NULL UNIQUE,
            vendor TEXT,
            location TEXT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            sort_order INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            block_name TEXT,
            unit_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (floor_id) REFERENCES floors(id)
        );

        CREATE TABLE IF NOT EXISTS progress (
            unit_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            value TEXT NOT NULL DEFAULT 'X',
            updated_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (unit_id, task_id),
            FOREIGN KEY (unit_id) REFERENCES units(id),
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (updated_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS unit_extra (
            unit_id INTEGER PRIMARY KEY,
            initial_check TEXT NOT NULL DEFAULT '',
            recheck_1 TEXT NOT NULL DEFAULT '',
            recheck_2 TEXT NOT NULL DEFAULT '',
            handover TEXT NOT NULL DEFAULT 'X',
            updated_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (unit_id) REFERENCES units(id),
            FOREIGN KEY (updated_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS extra_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            name TEXT NOT NULL,
            field_type TEXT NOT NULL DEFAULT 'date',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(sheet_id, field_key),
            FOREIGN KEY (sheet_id) REFERENCES sheets(id)
        );

        CREATE TABLE IF NOT EXISTS unit_extra_values (
            unit_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            updated_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (unit_id, field_key),
            FOREIGN KEY (unit_id) REFERENCES units(id),
            FOREIGN KEY (updated_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def seed_admin(conn: sqlite3.Connection) -> None:
    exists = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if exists:
        return
    conn.execute(
        "INSERT INTO users (username, display_name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("admin", "管理員", generate_password_hash("admin"), "admin"),
    )


def get_setting(conn: sqlite3.Connection, key: str) -> str:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else DEFAULT_SETTINGS[key]


def get_settings(conn: sqlite3.Connection) -> dict[str, str]:
    settings = DEFAULT_SETTINGS.copy()
    rows = conn.execute("SELECT key, value FROM meta").fetchall()
    for row in rows:
        if row["key"] in settings:
            settings[row["key"]] = row["value"]
    return settings


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO meta (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def seed_settings(conn: sqlite3.Connection) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        row = conn.execute("SELECT key FROM meta WHERE key = ?", (key,)).fetchone()
        if not row:
            set_setting(conn, key, value)


def seed_from_excel(conn: sqlite3.Connection) -> None:
    seeded = conn.execute("SELECT value FROM meta WHERE key = 'excel_seeded'").fetchone()
    if seeded:
        return
    if not SOURCE_XLSX.exists():
        raise FileNotFoundError(f"找不到 {SOURCE_XLSX}")

    wb = load_workbook(SOURCE_XLSX, data_only=False)
    ws = wb.active
    sheet_row = conn.execute("SELECT id FROM sheets ORDER BY sort_order, id LIMIT 1").fetchone()
    if not sheet_row:
        cur = conn.execute("INSERT INTO sheets (name, sort_order) VALUES (?, ?)", (get_setting(conn, "tab_title"), 1))
        sheet_id = cur.lastrowid
    else:
        sheet_id = sheet_row["id"]
    task_ids: dict[int, int] = {}
    for col in range(4, MAX_WORK_COL + 1):
        task_name = ws.cell(4, col).value
        if not task_name:
            continue
        cur = conn.execute(
            "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
            (sheet_id, col, ws.cell(2, col).value or "", ws.cell(3, col).value or "", str(task_name)),
        )
        task_ids[col] = cur.lastrowid

    for sort_order, floor_name in enumerate(
        ["20F", "19F", "18F", "17F", "16F", "15F", "14F", "13F", "12F", "11F", "10F", "9F", "8F", "7F", "6F", "5F", "4F", "3F", "2F", "1MF", "1F"],
        start=1,
    ):
        units = desired_units_for_floor(floor_name)
        cur = conn.execute(
            "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, ?)",
            (sheet_id, sort_order, floor_name, block_for_floor(floor_name), len(units)),
        )
        floor_id = cur.lastrowid
        for unit_order, unit_name in enumerate(units, start=1):
            unit_cur = conn.execute(
                "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
                (floor_id, unit_order, unit_name),
            )
            unit_id = unit_cur.lastrowid
            for task_id in task_ids.values():
                conn.execute(
                    "INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)",
                    (unit_id, task_id, WORKING_VALUE),
                )
            conn.execute("INSERT INTO unit_extra (unit_id) VALUES (?)", (unit_id,))

    conn.execute("INSERT INTO meta (key, value) VALUES ('excel_seeded', CURRENT_TIMESTAMP)")


def block_for_floor(floor_name: str) -> str:
    if floor_name in ("1MF", "1F"):
        return "S"
    return "A/B"


def desired_units_for_floor(floor_name: str) -> list[str]:
    if floor_name in ("1MF", "1F"):
        return ["S1", "S2", "S3", "S4", "S5", "S7", "S8"]
    if floor_name == "20F":
        return ["A1", "A2", "A6", "A7", "B1", "B2", "B5", "B7"]
    return ["A1", "A2", "A3", "A5", "A6", "A7", "B1", "B2", "B3", "B5", "B6", "B7"]


def migrate_schema(conn: sqlite3.Connection) -> None:
    existing_tables = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "unit_extra" not in existing_tables:
        conn.executescript(
            """
            CREATE TABLE unit_extra (
                unit_id INTEGER PRIMARY KEY,
                initial_check TEXT NOT NULL DEFAULT '',
                recheck_1 TEXT NOT NULL DEFAULT '',
                recheck_2 TEXT NOT NULL DEFAULT '',
                handover TEXT NOT NULL DEFAULT 'X',
                updated_by INTEGER,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id),
                FOREIGN KEY (updated_by) REFERENCES users(id)
            );
            """
        )
    task_cols = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
    floor_cols = {row["name"] for row in conn.execute("PRAGMA table_info(floors)")}
    user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "display_name" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        conn.execute("UPDATE users SET display_name = username WHERE display_name IS NULL OR display_name = ''")
    if "sheets" not in existing_tables:
        conn.execute(
            """
            CREATE TABLE sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    sheet = conn.execute("SELECT id FROM sheets ORDER BY sort_order, id LIMIT 1").fetchone()
    if not sheet:
        cur = conn.execute(
            "INSERT INTO sheets (name, sort_order) VALUES (?, ?)",
            (get_setting(conn, "tab_title"), 1),
        )
        default_sheet_id = cur.lastrowid
    else:
        default_sheet_id = sheet["id"]
    if "sheet_id" not in task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN sheet_id INTEGER")
        conn.execute("UPDATE tasks SET sheet_id = ?", (default_sheet_id,))
    if "sheet_id" not in floor_cols:
        conn.execute("ALTER TABLE floors ADD COLUMN sheet_id INTEGER")
        conn.execute("UPDATE floors SET sheet_id = ?", (default_sheet_id,))


def normalize_progress_values(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT unit_id, task_id, value FROM progress").fetchall()
    for row in rows:
        value = row["value"]
        if value in ("1", "O"):
            new_value = DONE_VALUE
        else:
            new_value = WORKING_VALUE
        if new_value != value:
            conn.execute(
                "UPDATE progress SET value = ? WHERE unit_id = ? AND task_id = ?",
                (new_value, row["unit_id"], row["task_id"]),
            )


def migrate_unit_layout(conn: sqlite3.Connection) -> None:
    version = conn.execute("SELECT value FROM meta WHERE key = 'unit_layout_version'").fetchone()
    if version and version["value"] == "2026-06-26-ab":
        return

    tasks = conn.execute("SELECT id FROM tasks ORDER BY col_index").fetchall()
    floors = conn.execute("SELECT * FROM floors ORDER BY sort_order").fetchall()

    for floor in floors:
        desired = desired_units_for_floor(floor["name"])
        old_units = conn.execute(
            "SELECT * FROM units WHERE floor_id = ? ORDER BY sort_order", (floor["id"],)
        ).fetchall()
        old_by_name = {unit["name"]: unit for unit in old_units}
        old_progress: dict[tuple[str, int], str] = {}
        old_extra: dict[str, sqlite3.Row] = {}
        for unit in old_units:
            for progress in conn.execute("SELECT task_id, value FROM progress WHERE unit_id = ?", (unit["id"],)):
                old_progress[(unit["name"], progress["task_id"])] = progress["value"]
            extra = conn.execute("SELECT * FROM unit_extra WHERE unit_id = ?", (unit["id"],)).fetchone()
            if extra:
                old_extra[unit["name"]] = extra

        conn.execute("DELETE FROM progress WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)", (floor["id"],))
        conn.execute("DELETE FROM unit_extra WHERE unit_id IN (SELECT id FROM units WHERE floor_id = ?)", (floor["id"],))
        conn.execute("DELETE FROM units WHERE floor_id = ?", (floor["id"],))

        for order, unit_name in enumerate(desired, start=1):
            cur = conn.execute(
                "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
                (floor["id"], order, unit_name),
            )
            unit_id = cur.lastrowid
            for task in tasks:
                old_value = old_progress.get((unit_name, task["id"]), WORKING_VALUE)
                value = DONE_VALUE if old_value in ("1", "O") else WORKING_VALUE
                conn.execute(
                    "INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)",
                    (unit_id, task["id"], value),
                )

            extra = old_extra.get(unit_name)
            if extra:
                conn.execute(
                    """
                    INSERT INTO unit_extra
                    (unit_id, initial_check, recheck_1, recheck_2, handover, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        unit_id,
                        extra["initial_check"],
                        extra["recheck_1"],
                        extra["recheck_2"],
                        DONE_VALUE if extra["handover"] in ("1", "O") else WORKING_VALUE,
                        extra["updated_by"],
                        extra["updated_at"],
                    ),
                )
            else:
                conn.execute("INSERT INTO unit_extra (unit_id, handover) VALUES (?, ?)", (unit_id, WORKING_VALUE))

        conn.execute(
            "UPDATE floors SET block_name = ?, unit_count = ? WHERE id = ?",
            (block_for_floor(floor["name"]), len(desired), floor["id"]),
        )

    set_setting(conn, "unit_layout_version", "2026-06-26-ab")


def ensure_unit_extra_rows(conn: sqlite3.Connection) -> None:
    for unit in conn.execute("SELECT id FROM units"):
        conn.execute(
            "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
            (unit["id"], WORKING_VALUE),
        )


def ensure_extra_fields(conn: sqlite3.Connection) -> None:
    for sheet in conn.execute("SELECT id FROM sheets"):
        for field_key, field in BUILTIN_EXTRA_FIELDS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO extra_fields
                (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
                VALUES (?, ?, ?, ?, ?, 1, 1)
                """,
                (sheet["id"], field_key, field["name"], field["type"], field["sort_order"]),
            )


def bootstrap() -> None:
    with db() as conn:
        init_schema(conn)
        seed_admin(conn)
        seed_settings(conn)
        seed_from_excel(conn)
        migrate_schema(conn)
        normalize_progress_values(conn)
        ensure_unit_extra_rows(conn)
        ensure_extra_fields(conn)
        migrate_unit_layout(conn)


def available_sheets(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sheets ORDER BY sort_order, id").fetchall()


def resolve_sheet_id(conn: sqlite3.Connection, sheet_id: int | None = None) -> int:
    if sheet_id:
        row = conn.execute("SELECT id FROM sheets WHERE id = ?", (sheet_id,)).fetchone()
        if row:
            return row["id"]
    row = conn.execute("SELECT id FROM sheets ORDER BY sort_order, id LIMIT 1").fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO sheets (name, sort_order) VALUES (?, ?)", (get_setting(conn, "tab_title"), 1))
    return cur.lastrowid


def extra_done(field: dict | sqlite3.Row, extra: dict) -> bool:
    field_key = field["field_key"]
    if field_key == "initial_check":
        return bool(extra.get("recheck_1")) or bool(extra.get("recheck_2")) or extra.get("handover") == DONE_VALUE
    if field_key == "recheck_1":
        return bool(extra.get("recheck_2")) or extra.get("handover") == DONE_VALUE
    if field_key == "recheck_2":
        return bool(extra.get("recheck_2")) or extra.get("handover") == DONE_VALUE
    if field_key == "handover":
        return extra.get("handover") == DONE_VALUE
    if field["field_type"] == "status":
        return extra.get(field_key) == DONE_VALUE
    return bool(extra.get(field_key))


def load_grid(sheet_id: int | None = None) -> dict:
    with db() as conn:
        current_sheet_id = resolve_sheet_id(conn, sheet_id)
        settings = get_settings(conn)
        sheets = available_sheets(conn)
        current_sheet = conn.execute("SELECT * FROM sheets WHERE id = ?", (current_sheet_id,)).fetchone()
        tasks = conn.execute("SELECT * FROM tasks WHERE sheet_id = ? ORDER BY col_index", (current_sheet_id,)).fetchall()
        floors = conn.execute("SELECT * FROM floors WHERE sheet_id = ? ORDER BY sort_order", (current_sheet_id,)).fetchall()
        units_by_floor = {
            floor["id"]: conn.execute(
                "SELECT * FROM units WHERE floor_id = ? ORDER BY sort_order", (floor["id"],)
            ).fetchall()
            for floor in floors
        }
        progress_rows = conn.execute("SELECT unit_id, task_id, value FROM progress").fetchall()
        extra_rows = conn.execute("SELECT * FROM unit_extra").fetchall()
        extra_fields = conn.execute(
            "SELECT * FROM extra_fields WHERE sheet_id = ? AND active = 1 ORDER BY sort_order, id",
            (current_sheet_id,),
        ).fetchall()
        extra_value_rows = conn.execute(
            """
            SELECT v.unit_id, v.field_key, v.value
            FROM unit_extra_values v
            JOIN units u ON u.id = v.unit_id
            JOIN floors f ON f.id = u.floor_id
            WHERE f.sheet_id = ?
            """,
            (current_sheet_id,),
        ).fetchall()

    progress = {(row["unit_id"], row["task_id"]): row["value"] for row in progress_rows}
    extras = {row["unit_id"]: dict(row) for row in extra_rows}
    for row in extra_value_rows:
        extras.setdefault(row["unit_id"], {})[row["field_key"]] = row["value"]
    floor_rows = []
    summary = {task["id"]: {"done": 0, "total": 0} for task in tasks}
    extra_summary = {field["field_key"]: {"done": 0, "total": 0} for field in extra_fields}

    for floor in floors:
        units = units_by_floor[floor["id"]]
        parent_status = {}
        for task in tasks:
            values = [progress.get((unit["id"], task["id"]), WORKING_VALUE) for unit in units]
            done_count = sum(1 for value in values if value == DONE_VALUE)
            parent_status[task["id"]] = DONE_VALUE if units and done_count == len(units) else WORKING_VALUE
            summary[task["id"]]["done"] += done_count
            summary[task["id"]]["total"] += len(units)
        for unit in units:
            extra = extras.get(unit["id"], {})
            for field in extra_fields:
                field_key = field["field_key"]
                extra_summary[field_key]["done"] += 1 if extra_done(field, extra) else 0
                extra_summary[field_key]["total"] += 1
        floor_rows.append({"floor": floor, "units": units, "parent_status": parent_status})

    return {
        "settings": settings,
        "sheets": sheets,
        "current_sheet": current_sheet,
        "tasks": tasks,
        "extra_fields": extra_fields,
        "floor_rows": floor_rows,
        "progress": progress,
        "extras": extras,
        "summary": summary,
        "extra_summary": extra_summary,
    }


def render_grid_payload(sheet_id: int | None = None) -> dict:
    grid = load_grid(sheet_id)
    floors = []
    for item in grid["floor_rows"]:
        floor = dict(item["floor"])
        units = [dict(unit) for unit in item["units"]]
        floors.append({"floor": floor, "units": units, "parent_status": item["parent_status"]})
    return {
        "settings": grid["settings"],
        "sheets": [dict(sheet) for sheet in grid["sheets"]],
        "current_sheet": dict(grid["current_sheet"]) if grid["current_sheet"] else None,
        "tasks": [dict(task) for task in grid["tasks"]],
        "extra_fields": [dict(field) for field in grid["extra_fields"]],
        "floors": floors,
        "progress": {f"{unit_id}:{task_id}": value for (unit_id, task_id), value in grid["progress"].items()},
        "extras": {str(unit_id): extra for unit_id, extra in grid["extras"].items()},
        "summary": grid["summary"],
        "extra_summary": grid["extra_summary"],
    }


@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return redirect(url_for("sheet"))


@app.route("/login", methods=["GET", "POST"])
def login():
    settings = query_settings()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip() or username
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user["display_name"] or user["username"]
            session["role"] = user["role"]
            return redirect(url_for("sheet"))
        flash("帳號或密碼錯誤。", "error")
    return render_template("login.html", settings=settings)


def query_settings() -> dict[str, str]:
    with db() as conn:
        return get_settings(conn)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/sheet")
@app.route("/sheet/<int:sheet_id>")
@login_required
def sheet(sheet_id: int | None = None):
    with db() as conn:
        resolved = resolve_sheet_id(conn, sheet_id)
    session["sheet_id"] = resolved
    grid = load_grid(resolved)
    return render_template(
        "sheet.html",
        grid=grid,
        settings=grid["settings"],
        done_value=DONE_VALUE,
        working_value=WORKING_VALUE,
    )


@app.route("/api/grid")
@login_required
def api_grid():
    sheet_id = request.args.get("sheet_id", type=int) or session.get("sheet_id")
    return jsonify(render_grid_payload(sheet_id))


@app.route("/api/progress", methods=["POST"])
@login_required
def api_progress():
    data = request.get_json(force=True)
    unit_id = int(data.get("unit_id"))
    task_id = int(data.get("task_id"))
    value = data.get("value", WORKING_VALUE)
    if value not in (DONE_VALUE, WORKING_VALUE):
        return jsonify({"ok": False, "message": "狀態只能是 O 或 X。"}), 400
    with db() as conn:
        conn.execute(
            """
            INSERT INTO progress (unit_id, task_id, value, updated_by, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(unit_id, task_id) DO UPDATE SET
                value = excluded.value,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (unit_id, task_id, value, session["user_id"]),
        )
    sheet_row = query_one(
        "SELECT f.sheet_id FROM units u JOIN floors f ON f.id = u.floor_id WHERE u.id = ?",
        (unit_id,),
    )
    return jsonify({"ok": True, "grid": render_grid_payload(sheet_row["sheet_id"] if sheet_row else session.get("sheet_id"))})


@app.route("/api/unit-extra", methods=["POST"])
@login_required
def api_unit_extra():
    data = request.get_json(force=True)
    unit_id = int(data.get("unit_id"))
    field = data.get("field", "")
    value = data.get("value", "")
    with db() as conn:
        field_row = conn.execute(
            """
            SELECT ef.*
            FROM extra_fields ef
            JOIN floors f ON f.sheet_id = ef.sheet_id
            JOIN units u ON u.floor_id = f.id
            WHERE u.id = ? AND ef.field_key = ? AND ef.active = 1
            """,
            (unit_id, field),
        ).fetchone()
        if not field_row:
            return jsonify({"ok": False, "message": "欄位錯誤。"}), 400
        if field_row["field_type"] == "status" and value not in (DONE_VALUE, WORKING_VALUE):
            return jsonify({"ok": False, "message": "O/X 欄位只能是 O 或 X。"}), 400
        conn.execute(
            "INSERT OR IGNORE INTO unit_extra (unit_id, handover) VALUES (?, ?)",
            (unit_id, WORKING_VALUE),
        )
        if field in EXTRA_FIELDS:
            conn.execute(
                f"""
                UPDATE unit_extra
                SET {field} = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE unit_id = ?
                """,
                (value, session["user_id"], unit_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(unit_id, field_key) DO UPDATE SET
                    value = excluded.value,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (unit_id, field, value, session["user_id"]),
            )
    sheet_row = query_one(
        "SELECT f.sheet_id FROM units u JOIN floors f ON f.id = u.floor_id WHERE u.id = ?",
        (unit_id,),
    )
    return jsonify({"ok": True, "grid": render_grid_payload(sheet_row["sheet_id"] if sheet_row else session.get("sheet_id"))})


@app.route("/api/reset-sheet", methods=["POST"])
@admin_required
def api_reset_sheet():
    data = request.get_json(force=True)
    password = data.get("password", "")
    user = get_user_by_id(session["user_id"])
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"ok": False, "message": "管理員密碼錯誤。"}), 403

    with db() as conn:
        sheet_id = resolve_sheet_id(conn, data.get("sheet_id") or session.get("sheet_id"))
        conn.execute(
            """
            UPDATE progress
            SET value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id IN (SELECT id FROM tasks WHERE sheet_id = ?)
            """,
            (WORKING_VALUE, session["user_id"], sheet_id),
        )
        conn.execute(
            """
            UPDATE unit_extra
            SET initial_check = '',
                recheck_1 = '',
                recheck_2 = '',
                handover = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE unit_id IN (
                SELECT u.id
                FROM units u
                JOIN floors f ON f.id = u.floor_id
                WHERE f.sheet_id = ?
            )
            """,
            (WORKING_VALUE, session["user_id"], sheet_id),
        )
        conn.execute(
            """
            DELETE FROM unit_extra_values
            WHERE unit_id IN (
                SELECT u.id
                FROM units u
                JOIN floors f ON f.id = u.floor_id
                WHERE f.sheet_id = ?
            )
            AND field_key IN (SELECT field_key FROM extra_fields WHERE sheet_id = ?)
            """,
            (sheet_id, sheet_id),
        )
    return jsonify({"ok": True, "grid": render_grid_payload(sheet_id)})


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        action = request.form.get("action", "create_user")
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip() or username
        password = request.form.get("password", "")
        role = request.form.get("role", "member")

        if role not in ("member", "admin"):
            flash("\u89d2\u8272\u8a2d\u5b9a\u932f\u8aa4\u3002", "error")
        elif action == "create_user":
            if not username or not password:
                flash("\u8acb\u8f38\u5165\u5e33\u865f\u8207\u5bc6\u78bc\u3002", "error")
            else:
                try:
                    password_hash = generate_password_hash(password)
                    with db() as conn:
                        user_row = create_user_sqlite(
                            conn,
                            username=username,
                            display_name=display_name,
                            password_hash=password_hash,
                            role=role,
                        )
                    maybe_dual_write_user_create(user_row)
                    flash("\u6210\u54e1\u5df2\u65b0\u589e\u3002", "success")
                except sqlite3.IntegrityError:
                    flash("\u5e33\u865f\u5df2\u5b58\u5728\u3002", "error")
        elif action.startswith("update_user:"):
            user_id = int(action.split(":", 1)[1])
            if user_id == session.get("user_id"):
                flash("\u672c\u968e\u6bb5\u4e0d\u5141\u8a31\u4fee\u6539\u81ea\u5df1\u7684\u89d2\u8272", "error")
            else:
                try:
                    with db() as conn:
                        update_user_role_sqlite(conn, user_id, role=role)
                    maybe_dual_write_user_role_update(user_id, role=role)
                    if user_id == session.get("user_id"):
                        session["username"] = username
                        session["display_name"] = display_name
                        session["role"] = role
                    flash("\u6210\u54e1\u8cc7\u6599\u5df2\u66f4\u65b0\u3002", "success")
                except sqlite3.IntegrityError:
                    flash("\u5e33\u865f\u5df2\u5b58\u5728\u3002", "error")
        elif action.startswith("delete_user:"):
            user_id = int(action.split(":", 1)[1])
            try:
                with db() as conn:
                    deleted_user_row = delete_user_sqlite(conn, user_id)
                maybe_dual_write_user_delete(deleted_user_row)
                flash("\u6210\u54e1\u5df2\u522a\u9664\u3002", "success")
            except ValueError:
                flash("\u7ba1\u7406\u54e1\u6216\u4fdd\u8b77\u5e33\u865f\u4e0d\u53ef\u522a\u9664\u3002", "error")
            except LookupError:
                flash("\u627e\u4e0d\u5230\u8981\u522a\u9664\u7684\u6210\u54e1\u3002", "error")
        else:
            flash("\u64cd\u4f5c\u7121\u6548\u3002", "error")

        return redirect(url_for("users"))

    all_users = list_users()
    with db() as conn:
        settings = get_settings(conn)
    return render_template("users.html", users=all_users, settings=settings)


@app.route("/admin/table", methods=["GET", "POST"])
@admin_required
def table_admin():
    with db() as conn:
        sheet_id = resolve_sheet_id(conn, request.values.get("sheet_id", type=int) or session.get("sheet_id"))
        session["sheet_id"] = sheet_id
        if request.method == "POST":
            actions = request.form.getlist("action")
            action = actions[-1] if actions else "save"
            if action == "create_sheet":
                name = request.form.get("new_sheet_name", "").strip() or "????"
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM sheets").fetchone()[0]
                cur = conn.execute("INSERT INTO sheets (name, sort_order) VALUES (?, ?)", (name, next_order))
                for field_key, field in BUILTIN_EXTRA_FIELDS.items():
                    conn.execute(
                        """
                        INSERT INTO extra_fields
                        (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
                        VALUES (?, ?, ?, ?, ?, 1, 1)
                        """,
                        (cur.lastrowid, field_key, field["name"], field["type"], field["sort_order"]),
                    )
                flash("???????", "success")
                return redirect(url_for("table_admin", sheet_id=cur.lastrowid))
            if action == "delete_sheet":
                count = conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0]
                if count <= 1:
                    flash("????????????", "error")
                    return redirect(url_for("table_admin", sheet_id=sheet_id))
                unit_ids = [row["id"] for row in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,))]
                if unit_ids:
                    placeholders = ",".join("?" for _ in unit_ids)
                    conn.execute(f"DELETE FROM progress WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra_values WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM units WHERE id IN ({placeholders})", unit_ids)
                conn.execute("DELETE FROM tasks WHERE sheet_id = ?", (sheet_id,))
                conn.execute("DELETE FROM floors WHERE sheet_id = ?", (sheet_id,))
                conn.execute("DELETE FROM unit_extra_values WHERE field_key IN (SELECT field_key FROM extra_fields WHERE sheet_id = ?)", (sheet_id,))
                conn.execute("DELETE FROM extra_fields WHERE sheet_id = ?", (sheet_id,))
                conn.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))
                next_sheet = resolve_sheet_id(conn)
                flash("???????", "success")
                return redirect(url_for("table_admin", sheet_id=next_sheet))
            if action == "add_task":
                next_col = conn.execute("SELECT COALESCE(MAX(col_index), 3) + 1 FROM tasks").fetchone()[0]
                cur = conn.execute(
                    "INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)",
                    (sheet_id, next_col, request.form.get("new_task_vendor", ""), request.form.get("new_task_location", ""), request.form.get("new_task_name", "???") or "???"),
                )
                for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):
                    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)", (unit["id"], cur.lastrowid, WORKING_VALUE))
                flash("??????", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action.startswith("delete_task:"):
                task_id = int(action.split(":", 1)[1])
                conn.execute("DELETE FROM progress WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM tasks WHERE id = ? AND sheet_id = ?", (task_id, sheet_id))
                flash("??????", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action == "add_extra_field":
                field_name = request.form.get("new_extra_name", "").strip() or "新增欄位"
                field_type = request.form.get("new_extra_type", "date")
                if field_type not in EXTRA_FIELD_TYPES:
                    field_type = "date"
                next_order = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM extra_fields WHERE sheet_id = ?",
                    (sheet_id,),
                ).fetchone()[0]
                conn.execute(
                    """
                    INSERT INTO extra_fields
                    (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
                    VALUES (?, ?, ?, ?, ?, 0, 1)
                    """,
                    (sheet_id, f"custom_{uuid.uuid4().hex[:12]}", field_name, field_type, next_order),
                )
                flash("欄位已新增。", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action.startswith("delete_extra_field:"):
                field_id = int(action.split(":", 1)[1])
                conn.execute("UPDATE extra_fields SET active = 0 WHERE id = ? AND sheet_id = ?", (field_id, sheet_id))
                flash("欄位已刪除。", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action == "add_floor":
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM floors").fetchone()[0]
                conn.execute(
                    "INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 0)",
                    (sheet_id, next_order, request.form.get("new_floor_name", "???") or "???", request.form.get("new_floor_block", "")),
                )
                flash("??????", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action.startswith("delete_floor:"):
                floor_id = int(action.split(":", 1)[1])
                unit_ids = [row["id"] for row in conn.execute("SELECT id FROM units WHERE floor_id = ?", (floor_id,))]
                if unit_ids:
                    placeholders = ",".join("?" for _ in unit_ids)
                    conn.execute(f"DELETE FROM progress WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM unit_extra_values WHERE unit_id IN ({placeholders})", unit_ids)
                    conn.execute(f"DELETE FROM units WHERE id IN ({placeholders})", unit_ids)
                conn.execute("DELETE FROM floors WHERE id = ? AND sheet_id = ?", (floor_id, sheet_id))
                flash("??????", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action.startswith("add_unit:"):
                floor_id = int(action.split(":", 1)[1])
                next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM units WHERE floor_id = ?", (floor_id,)).fetchone()[0]
                cur = conn.execute(
                    "INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)",
                    (floor_id, next_order, request.form.get(f"new_unit_name_{floor_id}", "???") or "???"),
                )
                for task in conn.execute("SELECT id FROM tasks WHERE sheet_id = ?", (sheet_id,)):
                    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (?, ?, ?)", (cur.lastrowid, task["id"], WORKING_VALUE))
                conn.execute("INSERT INTO unit_extra (unit_id, handover) VALUES (?, ?)", (cur.lastrowid, WORKING_VALUE))
                conn.execute("UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = ?) WHERE id = ?", (floor_id, floor_id))
                flash("??????", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))
            if action.startswith("delete_unit:"):
                unit_id = int(action.split(":", 1)[1])
                floor = conn.execute("SELECT floor_id FROM units WHERE id = ?", (unit_id,)).fetchone()
                conn.execute("DELETE FROM progress WHERE unit_id = ?", (unit_id,))
                conn.execute("DELETE FROM unit_extra WHERE unit_id = ?", (unit_id,))
                conn.execute("DELETE FROM unit_extra_values WHERE unit_id = ?", (unit_id,))
                conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))
                if floor:
                    conn.execute("UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = ?) WHERE id = ?", (floor["floor_id"], floor["floor_id"]))
                flash("??????", "success")
                return redirect(url_for("table_admin", sheet_id=sheet_id))

            conn.execute("UPDATE sheets SET name = ? WHERE id = ?", (request.form.get("sheet_name", "").strip() or "???", sheet_id))
            for key in DEFAULT_SETTINGS:
                if key in request.form:
                    set_setting(conn, key, request.form.get(key, "").strip())
            for task in conn.execute("SELECT id FROM tasks WHERE sheet_id = ?", (sheet_id,)):
                task_id = task["id"]
                conn.execute("UPDATE tasks SET vendor = ?, location = ?, name = ? WHERE id = ?", (request.form.get(f"task_vendor_{task_id}", "").strip(), request.form.get(f"task_location_{task_id}", "").strip(), request.form.get(f"task_name_{task_id}", "").strip(), task_id))
            for field in conn.execute("SELECT id FROM extra_fields WHERE sheet_id = ? AND active = 1", (sheet_id,)):
                field_id = field["id"]
                field_type = request.form.get(f"extra_type_{field_id}", "date")
                if field_type not in EXTRA_FIELD_TYPES:
                    field_type = "date"
                conn.execute(
                    "UPDATE extra_fields SET name = ?, field_type = ? WHERE id = ? AND sheet_id = ?",
                    (request.form.get(f"extra_name_{field_id}", "").strip() or "欄位", field_type, field_id, sheet_id),
                )
            for floor in conn.execute("SELECT id FROM floors WHERE sheet_id = ?", (sheet_id,)):
                floor_id = floor["id"]
                floor_name = request.form.get(f"floor_name_{floor_id}", "").strip()
                floor_block_name = request.form.get(f"floor_block_{floor_id}", "").strip()
                update_floor_fields_sqlite(conn, floor_id, name=floor_name, block_name=floor_block_name)
                maybe_dual_write_floor_update(floor_id, name=floor_name, block_name=floor_block_name)
            for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):
                unit_id = unit["id"]
                conn.execute("UPDATE units SET name = ? WHERE id = ?", (request.form.get(f"unit_name_{unit_id}", "").strip(), unit_id))
            flash("????????", "success")
            return redirect(url_for("table_admin", sheet_id=sheet_id))

        settings = get_settings(conn)
        sheets = available_sheets(conn)
        current_sheet = conn.execute("SELECT * FROM sheets WHERE id = ?", (sheet_id,)).fetchone()
        tasks = conn.execute("SELECT * FROM tasks WHERE sheet_id = ? ORDER BY col_index", (sheet_id,)).fetchall()
        extra_fields = conn.execute("SELECT * FROM extra_fields WHERE sheet_id = ? AND active = 1 ORDER BY sort_order, id", (sheet_id,)).fetchall()
        floors = conn.execute("SELECT * FROM floors WHERE sheet_id = ? ORDER BY sort_order", (sheet_id,)).fetchall()
        units = {floor["id"]: conn.execute("SELECT * FROM units WHERE floor_id = ? ORDER BY sort_order", (floor["id"],)).fetchall() for floor in floors}
    return render_template("table_admin.html", settings=settings, sheets=sheets, current_sheet=current_sheet, tasks=tasks, extra_fields=extra_fields, floors=floors, units=units)


bootstrap()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
