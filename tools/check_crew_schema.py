from __future__ import annotations

import argparse
import importlib
import os
import sqlite3
import sys
import tempfile
from shutil import copy2, rmtree
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlite_db_path import get_sqlite_db_path


VENDOR_CONTACTS_COLUMNS = (
    "id",
    "sheet_id",
    "vendor_name",
    "contact_name",
    "contact_title",
    "contact_phone",
    "is_primary",
    "contact_order",
    "created_at",
    "updated_at",
)
VENDOR_WORK_ENTRIES_COLUMNS = (
    "id",
    "sheet_id",
    "vendor_name",
    "business_date",
    "planned_at",
    "planned_headcount",
    "actual_headcount",
    "work_content",
    "work_headcount",
    "entry_order",
    "created_at",
    "updated_at",
)
EXPECTED_INDEXES = {
    "vendor_contacts": {
        "idx_vendor_contacts_sheet_id",
        "idx_vendor_contacts_sheet_vendor",
        "idx_vendor_contacts_sheet_vendor_order",
    },
    "vendor_work_entries": {
        "idx_vendor_work_entries_sheet_business_date",
        "idx_vendor_work_entries_sheet_vendor_date",
        "idx_vendor_work_entries_business_date",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect lower crew form SQLite schema readiness without touching PostgreSQL."
    )
    return parser.parse_args()


def fetch_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def fetch_indexes(conn: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(f"PRAGMA index_list({table_name})").fetchall()


def index_columns(conn: sqlite3.Connection, index_name: str) -> tuple[str, ...]:
    return tuple(row[2] for row in conn.execute(f"PRAGMA index_info({index_name})").fetchall())


def main() -> int:
    parse_args()
    source_db_path = get_sqlite_db_path()
    tmpdir = tempfile.mkdtemp(prefix="crew-schema-")
    try:
        analysis_db_path = Path(tmpdir) / source_db_path.name
        copy2(source_db_path, analysis_db_path)
        os.environ["APP_DB_PATH"] = str(analysis_db_path)
        app = importlib.import_module("app")

        issues: list[str] = []

        print("crew_schema_scope: sqlite_only")
        print(f"sqlite_source: {source_db_path}")
        print(f"analysis_db_copy: {analysis_db_path}")

        with app.db() as conn:
            conn.row_factory = sqlite3.Row
            existing_tables = {
                row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }

            print(f"vendor_contacts_table_exists: {str('vendor_contacts' in existing_tables).lower()}")
            print(f"vendor_work_entries_table_exists: {str('vendor_work_entries' in existing_tables).lower()}")

            if "vendor_contacts" not in existing_tables:
                issues.append("vendor_contacts_missing")
            if "vendor_work_entries" not in existing_tables:
                issues.append("vendor_work_entries_missing")

            if "vendor_contacts" in existing_tables:
                vendor_contacts_columns = fetch_table_columns(conn, "vendor_contacts")
                print(f"vendor_contacts_columns: {','.join(vendor_contacts_columns)}")
                missing = [col for col in VENDOR_CONTACTS_COLUMNS if col not in vendor_contacts_columns]
                if missing:
                    issues.append(f"vendor_contacts_missing_columns:{','.join(missing)}")

                contact_indexes = fetch_indexes(conn, "vendor_contacts")
                contact_index_names = {row["name"] for row in contact_indexes}
                print(f"vendor_contacts_indexes: {','.join(sorted(contact_index_names))}")
                missing_indexes = sorted(EXPECTED_INDEXES["vendor_contacts"] - contact_index_names)
                if missing_indexes:
                    issues.append(f"vendor_contacts_missing_indexes:{','.join(missing_indexes)}")

                legacy_unique_present = False
                for row in contact_indexes:
                    if row["unique"]:
                        if index_columns(conn, row["name"]) == ("sheet_id", "vendor_name"):
                            legacy_unique_present = True
                            break
                print(f"vendor_contacts_unique_sheet_vendor: {str(legacy_unique_present).lower()}")
                if legacy_unique_present:
                    issues.append("vendor_contacts_legacy_unique_sheet_vendor_present")

            if "vendor_work_entries" in existing_tables:
                vendor_work_entries_columns = fetch_table_columns(conn, "vendor_work_entries")
                print(f"vendor_work_entries_columns: {','.join(vendor_work_entries_columns)}")
                missing = [col for col in VENDOR_WORK_ENTRIES_COLUMNS if col not in vendor_work_entries_columns]
                if missing:
                    issues.append(f"vendor_work_entries_missing_columns:{','.join(missing)}")

                work_indexes = fetch_indexes(conn, "vendor_work_entries")
                work_index_names = {row["name"] for row in work_indexes}
                print(f"vendor_work_entries_indexes: {','.join(sorted(work_index_names))}")
                missing_indexes = sorted(EXPECTED_INDEXES["vendor_work_entries"] - work_index_names)
                if missing_indexes:
                    issues.append(f"vendor_work_entries_missing_indexes:{','.join(missing_indexes)}")

        helper_cases = [
            ("before_0830", datetime(2026, 6, 29, 8, 29, 0), "2026-06-28"),
            ("at_0830", datetime(2026, 6, 29, 8, 30, 0), "2026-06-29"),
            ("late_day", datetime(2026, 6, 29, 23, 59, 0), "2026-06-29"),
        ]
        helper_pass = True
        for label, now, expected in helper_cases:
            resolved = app.resolve_crew_business_date(now)
            print(f"resolve_crew_business_date[{label}]: {resolved}")
            if resolved != expected:
                helper_pass = False
                issues.append(f"resolve_crew_business_date_failed:{label}:{resolved}")
        print(f"resolve_crew_business_date_pass: {str(helper_pass).lower()}")

        with app.app.app_context():
            from database import db as orm_db

            orm_db.session.remove()
            orm_db.engine.dispose()

        if issues:
            print(f"FAIL crew schema check: {', '.join(issues)}")
            return 1

        print("PASS crew schema check passed.")
        return 0
    finally:
        rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
