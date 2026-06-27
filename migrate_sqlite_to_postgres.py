
from __future__ import annotations
import os, sqlite3
import psycopg
from psycopg.rows import dict_row

TABLES = [
    "users", "sheets", "tasks", "floors", "units", "progress",
    "unit_extra", "extra_fields", "unit_extra_values", "meta",
]

def main():
    sqlite_path = os.environ.get("SQLITE_PATH", "site.db")
    database_url = os.environ["DATABASE_URL"]
    sconn = sqlite3.connect(sqlite_path)
    sconn.row_factory = sqlite3.Row
    pconn = psycopg.connect(database_url, row_factory=dict_row)
    with pconn:
        with pconn.cursor() as cur:
            for table in reversed(TABLES):
                cur.execute(f"DELETE FROM {table}")
            for table in TABLES:
                rows = sconn.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    continue
                cols = rows[0].keys()
                placeholders = ", ".join(["%s"] * len(cols))
                col_sql = ", ".join(cols)
                for row in rows:
                    values = [row[c] for c in cols]
                    cur.execute(f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})", values)
            for table in ["users", "sheets", "tasks", "floors", "units", "extra_fields"]:
                cur.execute("SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE((SELECT MAX(id) FROM " + table + "), 1), true)", (table,))
    sconn.close()
    pconn.close()
    print("Migration completed.")

if __name__ == "__main__":
    main()
