from __future__ import annotations

import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask
from openpyxl import load_workbook
from werkzeug.security import generate_password_hash

from config import APP_DB_PATH, DATABASE_URL
from database import init_database
from db_compat import IntegrityError, connect_db
from routes.admin import admin_bp
from routes.api import api_bp
from routes.auth import admin_required as auth_admin_required, auth_bp, login_required as auth_login_required
from routes.sheet import sheet_bp
from services.progress_service import reset_sheet, update_progress, update_unit_extra
from services.sheet_service import available_sheets, load_grid, render_grid_payload, resolve_sheet_id
from tools.import_seed import import_seed_into_conn


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DB_PATH
SEED_PATH = BASE_DIR / "seeds" / "default_seed.json"
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

ASSET_VERSION = "20260627-010"
def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "dev-secret-change-me")
    if DATABASE_URL:
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH.resolve().as_posix()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    init_database(app)

    @app.context_processor
    def inject_asset_version():
        return {"asset_version": ASSET_VERSION}

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sheet_bp)
    return app


app = create_app()


def db():
    return connect_db(DB_PATH)


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute(sql, params).fetchone()


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


login_required = auth_login_required
admin_required = auth_admin_required


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


def primary_tables_are_empty(conn: sqlite3.Connection) -> bool:
    for table in ("users", "sheets", "tasks", "floors", "units"):
        if conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
            return False
    return True


def bootstrap() -> None:
    with db() as conn:
        init_schema(conn)
        if primary_tables_are_empty(conn):
            if SEED_PATH.exists():
                import_seed_into_conn(conn, SEED_PATH)
            else:
                seed_admin(conn)
                seed_settings(conn)
                seed_from_excel(conn)
        migrate_schema(conn)
        seed_admin(conn)
        seed_settings(conn)
        normalize_progress_values(conn)
        ensure_unit_extra_rows(conn)
        ensure_extra_fields(conn)
        migrate_unit_layout(conn)

def query_settings() -> dict[str, str]:
    with db() as conn:
        return get_settings(conn)
bootstrap()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
