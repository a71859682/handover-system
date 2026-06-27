from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "site.db"
SEED_PATH = ROOT / "seeds" / "default_seed.json"
TABLES = [
    "users",
    "meta",
    "sheets",
    "tasks",
    "floors",
    "units",
    "progress",
    "unit_extra",
    "extra_fields",
    "unit_extra_values",
]


def load_seed(seed_path: Path = SEED_PATH) -> dict[str, object]:
    return json.loads(seed_path.read_text(encoding="utf-8"))


def database_is_empty(conn: sqlite3.Connection) -> bool:
    for table in TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count:
            return False
    return True


def import_seed_into_conn(conn: sqlite3.Connection, seed_path: Path = SEED_PATH) -> None:
    if not database_is_empty(conn):
        raise RuntimeError("Target database is not empty.")

    payload = load_seed(seed_path)
    tables = payload.get("tables", {})

    for table in TABLES:
        rows = tables.get(table, [])
        if not rows:
            continue
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        column_sql = ", ".join(columns)
        sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
        for row in rows:
            conn.execute(sql, tuple(row[column] for column in columns))


def import_seed(db_path: Path = DB_PATH, seed_path: Path = SEED_PATH) -> Path:
    conn = sqlite3.connect(db_path)
    try:
        import_seed_into_conn(conn, seed_path)
        conn.commit()
    finally:
        conn.close()
    return db_path


def main() -> None:
    db_path = import_seed()
    print(f"Imported seed into {db_path}")


if __name__ == "__main__":
    main()
