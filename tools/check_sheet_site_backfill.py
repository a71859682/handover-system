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
    parser = argparse.ArgumentParser(description="Check sheets.site_id backfill state.")
    parser.parse_args()

    db_path = resolve_db_path()
    os.environ["APP_DB_PATH"] = str(db_path)
    sys.path.insert(0, str(ROOT_DIR))
    import app  # noqa: F401

    print("sheet_site_backfill_scope: sqlite_only")
    print(f"sqlite_path: {db_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    default_site = conn.execute(
        "SELECT id FROM sites WHERE site_name = ? ORDER BY id LIMIT 1",
        (DEFAULT_SITE_NAME,),
    ).fetchone()
    if not default_site:
        conn.close()
        print("FAIL sheet site backfill check:")
        print("- default_site_missing")
        return 1

    sheets = conn.execute("SELECT id, site_id FROM sheets ORDER BY id").fetchall()
    conn.close()

    non_null_count = sum(1 for row in sheets if row["site_id"] is not None)
    all_non_null = non_null_count == len(sheets)
    all_default = all(row["site_id"] == default_site["id"] for row in sheets)

    print(f"sheets_count: {len(sheets)}")
    print(f"sheets_site_id_non_null_count: {non_null_count}")
    print(f"sheets_site_id_all_non_null: {all_non_null}")
    print(f"sheets_site_id_all_default_site: {all_default}")
    print(f"default_site_id: {default_site['id']}")

    issues: list[str] = []
    if not all_non_null:
        issues.append("sheet_site_id_null_found")
    if not all_default:
        issues.append("sheet_site_id_not_default_site")

    if issues:
        print("FAIL sheet site backfill check:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("PASS sheet site backfill check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
