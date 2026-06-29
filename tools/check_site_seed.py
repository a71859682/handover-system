from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "site.db"
DEFAULT_SITE_NAME = "大英營造-新埔段"


def resolve_db_path() -> Path:
    raw = os.environ.get("APP_DB_PATH")
    return Path(raw).expanduser().resolve() if raw else DEFAULT_DB_PATH.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check default site seed state.")
    parser.parse_args()

    db_path = resolve_db_path()
    os.environ["APP_DB_PATH"] = str(db_path)
    sys.path.insert(0, str(ROOT_DIR))
    import app  # noqa: F401

    print("site_seed_scope: sqlite_only")
    print(f"default_site_name: {DEFAULT_SITE_NAME}")
    print(f"sqlite_path: {db_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, site_name, is_active FROM sites WHERE site_name = ? ORDER BY id",
        (DEFAULT_SITE_NAME,),
    ).fetchall()
    conn.close()

    print(f"default_site_exists: {bool(rows)}")
    print(f"default_site_count: {len(rows)}")
    print(f"default_site_id: {rows[0]['id'] if rows else ''}")
    print(f"default_site_is_active: {rows[0]['is_active'] if rows else ''}")

    if len(rows) != 1:
        print("FAIL site seed check:")
        print("- default_site_count_must_equal_1")
        return 1

    print("PASS site seed check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
