
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = Path(os.environ.get("APP_DB_PATH", BASE_DIR / "site.db"))

POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
else:
    psycopg = None

ID_TABLES = {"users", "tasks", "sheets", "floors", "units", "extra_fields"}

class Result:
    def __init__(self, rows=None, lastrowid=None, cursor=None):
        self._rows = rows
        self.lastrowid = lastrowid
        self._cursor = cursor

    def fetchone(self):
        if self._rows is not None:
            return self._rows[0] if self._rows else None
        return self._cursor.fetchone()

    def fetchall(self):
        if self._rows is not None:
            return self._rows
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self.fetchall())

    def __getitem__(self, index):
        return self.fetchall()[index]


def _split_sql_script(script: str) -> list[str]:
    parts = []
    buf = []
    in_single = False
    in_double = False
    for ch in script:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            s = "".join(buf).strip()
            if s:
                parts.append(s)
            buf = []
        else:
            buf.append(ch)
    s = "".join(buf).strip()
    if s:
        parts.append(s)
    return parts


def _qmark_to_percent(sql: str) -> str:
    # safe for this project: no SQL text literals contain question-mark placeholders
    return sql.replace("?", "%s")


def _insert_table(sql: str) -> str | None:
    m = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, re.I)
    return m.group(1).lower() if m else None


def _pg_schema(script: str) -> str:
    s = script
    s = s.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    s = s.replace("INTEGER PRIMARY KEY,", "INTEGER PRIMARY KEY,")
    return s


def _pg_translate(sql: str) -> str:
    s = sql.strip()
    # SQLite system catalog emulation is handled before execution.
    s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, flags=re.I)
    s = _qmark_to_percent(s)
    if re.search(r"INSERT\s+INTO", s, re.I) and " OR IGNORE " not in sql.upper():
        table = _insert_table(s)
        if table in ID_TABLES and "RETURNING" not in s.upper() and "ON CONFLICT" not in s.upper():
            s = s.rstrip().rstrip(";") + " RETURNING id"
    # For INSERT OR IGNORE conversions where unique constraints exist.
    if re.search(r"INSERT\s+INTO\s+unit_extra\b", s, re.I) and "ON CONFLICT" not in s.upper():
        s += " ON CONFLICT (unit_id) DO NOTHING"
    if re.search(r"INSERT\s+INTO\s+extra_fields\b", s, re.I) and "ON CONFLICT" not in s.upper():
        s += " ON CONFLICT (sheet_id, field_key) DO NOTHING"
    return s


class SQLiteConnection:
    def __enter__(self):
        self.conn = sqlite3.connect(SQLITE_DB_PATH)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()


class PostgresConnection:
    def __enter__(self):
        self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> Result:
        raw = sql.strip()
        # emulate SQLite table checks used by migration code
        if re.search(r"FROM\s+sqlite_master", raw, re.I):
            cur = self.conn.execute("SELECT tablename AS name FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
            return Result(cur.fetchall())
        m = re.match(r"PRAGMA\s+table_info\(([^)]+)\)", raw, re.I)
        if m:
            table = m.group(1).strip().strip('"')
            cur = self.conn.execute(
                """
                SELECT column_name AS name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table,),
            )
            return Result(cur.fetchall())
        sql2 = _pg_translate(raw)
        try:
            cur = self.conn.execute(sql2, tuple(params))
            lastrowid = None
            if sql2.upper().rstrip().endswith("RETURNING ID"):
                row = cur.fetchone()
                if row:
                    lastrowid = row["id"]
                return Result([], lastrowid=lastrowid)
            return Result(cursor=cur)
        except Exception as e:
            if psycopg and isinstance(e, psycopg.IntegrityError):
                raise sqlite3.IntegrityError(str(e)) from e
            raise

    def executescript(self, script: str) -> None:
        script = _pg_schema(script)
        for stmt in _split_sql_script(script):
            self.execute(stmt)


def connect():
    return PostgresConnection() if POSTGRES else SQLiteConnection()
