from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

try:
    import psycopg
except Exception:  # psycopg is only required on PostgreSQL runtime
    psycopg = None


class Row(dict):
    """Row object compatible with sqlite3.Row style access: row['id'] and row[0]."""

    def __init__(self, keys: list[str], values: Iterable[Any]):
        values = list(values)
        super().__init__(zip(keys, values))
        self._keys = keys
        self._values = values

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class IntegrityError(sqlite3.IntegrityError):
    pass


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip()


def is_postgres() -> bool:
    url = _database_url()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def connect_db(sqlite_path: str | Path):
    if is_postgres():
        if psycopg is None:
            raise RuntimeError("psycopg is not installed. Add psycopg[binary] to requirements.txt")
        return PostgresCompatConnection(_database_url())
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def _convert_placeholders(sql: str) -> str:
    # Convert DB-API qmark placeholders to psycopg placeholders.
    return sql.replace("?", "%s")


def _split_sql_script(script: str) -> list[str]:
    statements: list[str] = []
    buff: list[str] = []
    in_single = False
    in_double = False
    prev = ""
    for ch in script:
        if ch == "'" and not in_double and prev != "\\":
            in_single = not in_single
        elif ch == '"' and not in_single and prev != "\\":
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buff).strip()
            if stmt:
                statements.append(stmt)
            buff = []
        else:
            buff.append(ch)
        prev = ch
    tail = "".join(buff).strip()
    if tail:
        statements.append(tail)
    return statements


def _translate_sql(sql: str) -> str:
    stripped = sql.strip()
    low = re.sub(r"\s+", " ", stripped.lower())

    if low == "select name from sqlite_master where type = 'table'":
        return "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'public'"

    pragma = re.match(r"pragma\s+table_info\(([^)]+)\)", low)
    if pragma:
        table = pragma.group(1).strip('"')
        return (
            "SELECT column_name AS name "
            "FROM information_schema.columns "
            f"WHERE table_schema = 'public' AND table_name = '{table}' "
            "ORDER BY ordinal_position"
        )

    s = stripped
    s = re.sub(r"id\s+INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "id SERIAL PRIMARY KEY", s, flags=re.I)
    s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, flags=re.I)
    if re.search(r"INSERT\s+INTO", s, re.I) and "ON CONFLICT" not in s.upper() and "DO NOTHING" not in s.upper():
        # For translated INSERT OR IGNORE, add a generic do-nothing conflict handler when obvious.
        original_was_ignore = re.search(r"INSERT\s+OR\s+IGNORE\s+INTO", stripped, re.I) is not None
        if original_was_ignore:
            s += " ON CONFLICT DO NOTHING"

    s = _convert_placeholders(s)
    return s


def _insert_needs_returning_id(sql: str) -> bool:
    low = re.sub(r"\s+", " ", sql.strip().lower())
    if not low.startswith("insert into "):
        return False
    if " returning " in low or " on conflict " in low:
        return False
    return bool(re.match(r"insert into (users|tasks|sheets|floors|units|extra_fields)\b", low))


class CompatCursor:
    def __init__(self, cursor, keys: list[str] | None = None, lastrowid: int | None = None):
        self._cursor = cursor
        self._keys = keys
        self.lastrowid = lastrowid

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return Row(self._keys or [d.name for d in self._cursor.description], row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        keys = self._keys or [d.name for d in self._cursor.description]
        return [Row(keys, row) for row in rows]

    def __iter__(self):
        keys = self._keys or [d.name for d in self._cursor.description]
        for row in self._cursor:
            yield Row(keys, row)


class PostgresCompatConnection:
    def __init__(self, url: str):
        self._conn = psycopg.connect(url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
            self._conn.close()
        return False

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def executescript(self, script: str):
        for stmt in _split_sql_script(script):
            self.execute(stmt)

    def execute(self, sql: str, params: tuple | list = ()):  # sqlite-like execute
        translated = _translate_sql(sql)
        if _insert_needs_returning_id(translated):
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
        cur = self._conn.cursor()
        try:
            cur.execute(translated, params)
            lastrowid = None
            keys = None
            if cur.description:
                keys = [d.name for d in cur.description]
                if keys == ["id"] and translated.lower().strip().startswith("insert into"):
                    row = cur.fetchone()
                    lastrowid = row[0] if row else None
                    # Replace with an empty cursor-like object for callers that only inspect lastrowid.
                    cur = self._conn.cursor()
            return CompatCursor(cur, keys, lastrowid)
        except Exception as exc:
            if psycopg and isinstance(exc, psycopg.errors.UniqueViolation):
                raise IntegrityError(str(exc)) from exc
            raise
