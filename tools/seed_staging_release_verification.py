from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import psycopg
from werkzeug.security import generate_password_hash

ROOT_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


STATUS_DONE = "O"
STATUS_WORKING = "X"

SITE_A_NAME = "staging_release_site_a"
SITE_B_NAME = "staging_release_site_b"
SITE_A_CODE = "staging-a"
SITE_B_CODE = "staging-b"
SHEET_A_NAME = "staging_release_sheet_a"
SHEET_B_NAME = "staging_release_sheet_b"

ADMIN_USERNAME = "admin_staging"
SINGLE_SITE_USERNAME = "single_site_user_staging"
MULTI_SITE_USERNAME = "multi_site_user_staging"
ZERO_SITE_USERNAME = "zero_site_user_staging"
PERMISSION_REMOVED_USERNAME = "permission_removed_user_staging"

STAGING_PASSWORDS = {
    ADMIN_USERNAME: "staging-admin-pass",
    SINGLE_SITE_USERNAME: "staging-single-pass",
    MULTI_SITE_USERNAME: "staging-multi-pass",
    ZERO_SITE_USERNAME: "staging-zero-pass",
    PERMISSION_REMOVED_USERNAME: "staging-permission-pass",
}

DEFAULT_META_SETTINGS = {
    "site_title": "Staging Release Verification",
    "sheet_title": "Staging Release Verification",
    "tab_title": "Staging Release Verification",
    "instruction_text": "Staging release verification seed data.",
    "floor_header": "Floor",
    "count_header": "Count",
    "unit_header": "Unit",
    "vendor_header": "Vendor",
    "task_header": "Task",
}


@dataclass(frozen=True)
class SiteSpec:
    name: str
    code: str
    sheet_name: str
    task_base: int
    floor_base: int
    vendors: tuple[str, str]


SITE_SPECS: tuple[SiteSpec, ...] = (
    SiteSpec(
        name=SITE_A_NAME,
        code=SITE_A_CODE,
        sheet_name=SHEET_A_NAME,
        task_base=1100,
        floor_base=110,
        vendors=("Vendor A Prime", "Vendor A Finish"),
    ),
    SiteSpec(
        name=SITE_B_NAME,
        code=SITE_B_CODE,
        sheet_name=SHEET_B_NAME,
        task_base=2100,
        floor_base=210,
        vendors=("Vendor B Prime", "Vendor B Finish"),
    ),
)

MANAGED_SITE_NAMES = tuple(spec.name for spec in SITE_SPECS)
MANAGED_SITE_CODES = tuple(spec.code for spec in SITE_SPECS)
MANAGED_SHEET_NAMES = tuple(spec.sheet_name for spec in SITE_SPECS)
MANAGED_USERNAMES = (
    ADMIN_USERNAME,
    SINGLE_SITE_USERNAME,
    MULTI_SITE_USERNAME,
    ZERO_SITE_USERNAME,
    PERMISSION_REMOVED_USERNAME,
)
MANAGED_VENDORS = tuple(vendor for spec in SITE_SPECS for vendor in spec.vendors)
MANAGED_EXTRA_FIELDS = ("release_note", "release_status")

TABLES_TO_VERIFY = (
    "sites",
    "sheets",
    "users",
    "user_site_permissions",
    "tasks",
    "floors",
    "units",
    "progress",
    "unit_extra",
    "extra_fields",
    "unit_extra_values",
    "vendor_contacts",
    "vendor_work_entries",
)

PLANNED_SUMMARY_COUNTS = {
    "sites": 2,
    "sheets": 2,
    "users": 5,
    "user_site_permissions": 4,
    "tasks": 4,
    "floors": 4,
    "units": 6,
    "progress": 12,
    "unit_extra": 6,
    "extra_fields": 4,
    "unit_extra_values": 12,
    "vendor_contacts": 4,
    "vendor_work_entries": 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed staging release verification data into the staging PostgreSQL database.")
    parser.add_argument("--dry-run", action="store_true", help="Run the full seed flow inside a transaction and roll it back.")
    parser.add_argument(
        "--clear-and-reseed",
        action="store_true",
        help="Delete only managed staging release verification rows before reseeding.",
    )
    return parser.parse_args()


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def require_postgres_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")
    scheme = urlsplit(database_url).scheme.lower()
    if scheme not in {"postgresql", "postgres"}:
        raise SystemExit(f"DATABASE_URL must point to PostgreSQL, got scheme '{scheme or 'missing'}'.")
    return database_url


def redact_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    hostname = parts.hostname or ""
    if parts.port:
        hostname = f"{hostname}:{parts.port}"
    if parts.username:
        netloc = f"{parts.username}:***@{hostname}"
    else:
        netloc = hostname
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def require_staging_guard() -> None:
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if app_env == "staging" or env_flag("STAGING_SEED_ALLOWED"):
        return
    raise SystemExit("Refusing to run seed script outside staging guard. Set APP_ENV=staging or STAGING_SEED_ALLOWED=true.")


def require_staging_target(database_url: str) -> None:
    parts = urlsplit(database_url)
    target_blob = " ".join(
        part
        for part in (
            parts.hostname or "",
            parts.path or "",
            parts.username or "",
            parts.netloc or "",
        )
        if part
    ).lower()
    if "staging" not in target_blob:
        raise SystemExit("Refusing to run because DATABASE_URL does not look like a staging target.")


def fetch_existing_tables(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        return {row[0] for row in cur.fetchall()}


def ensure_required_tables(conn: psycopg.Connection) -> None:
    existing = fetch_existing_tables(conn)
    missing = [table for table in TABLES_TO_VERIFY if table not in existing]
    if missing:
        raise SystemExit(f"Missing required PostgreSQL tables: {', '.join(missing)}")


def fetchone_dict(cur: psycopg.Cursor[Any]) -> dict[str, Any] | None:
    row = cur.fetchone()
    if row is None:
        return None
    columns = [col.name for col in cur.description]
    return dict(zip(columns, row))


def get_site_by_name(conn: psycopg.Connection, *, site_name: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, site_name, site_code, is_active FROM sites WHERE site_name = %s",
            (site_name,),
        )
        return fetchone_dict(cur)


def get_sheet_by_name(conn: psycopg.Connection, *, sheet_name: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, site_id, name, sort_order FROM sheets WHERE name = %s",
            (sheet_name,),
        )
        return fetchone_dict(cur)


def get_user_by_username(conn: psycopg.Connection, *, username: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, role FROM users WHERE username = %s",
            (username,),
        )
        return fetchone_dict(cur)


def ensure_meta_defaults(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        for key, value in DEFAULT_META_SETTINGS.items():
            cur.execute(
                """
                INSERT INTO meta (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                (key, value),
            )


def ensure_site(conn: psycopg.Connection, *, site_name: str, site_code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sites (site_name, site_code, is_active)
            VALUES (%s, %s, 1)
            ON CONFLICT (site_name) DO UPDATE
            SET site_code = EXCLUDED.site_code,
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (site_name, site_code),
        )
        return int(cur.fetchone()[0])


def next_sheet_sort_order(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM sheets")
        return int(cur.fetchone()[0])


def ensure_sheet(conn: psycopg.Connection, *, site_id: int, sheet_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM sheets WHERE name = %s", (sheet_name,))
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE sheets
                SET site_id = %s
                WHERE id = %s
                RETURNING id
                """,
                (site_id, row[0]),
            )
            return int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO sheets (name, sort_order, site_id)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (sheet_name, next_sheet_sort_order(conn), site_id),
        )
        return int(cur.fetchone()[0])


def ensure_user(conn: psycopg.Connection, *, username: str, display_name: str, role: str) -> int:
    password_hash = generate_password_hash(STAGING_PASSWORDS[username])
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (username, display_name, password_hash, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE
            SET display_name = EXCLUDED.display_name,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role
            RETURNING id
            """,
            (username, display_name, password_hash, role),
        )
        return int(cur.fetchone()[0])


def ensure_permission(conn: psycopg.Connection, *, user_id: int, site_id: int, role: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_site_permissions (user_id, site_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, site_id) DO UPDATE
            SET role = EXCLUDED.role,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, site_id, role),
        )


def ensure_task(
    conn: psycopg.Connection,
    *,
    sheet_id: int,
    col_index: int,
    vendor: str,
    location: str,
    name: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks (sheet_id, col_index, vendor, location, name)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (col_index) DO UPDATE
            SET sheet_id = EXCLUDED.sheet_id,
                vendor = EXCLUDED.vendor,
                location = EXCLUDED.location,
                name = EXCLUDED.name
            RETURNING id
            """,
            (sheet_id, col_index, vendor, location, name),
        )
        return int(cur.fetchone()[0])


def ensure_floor(
    conn: psycopg.Connection,
    *,
    sheet_id: int,
    sort_order: int,
    name: str,
    block_name: str,
    unit_count: int,
) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM floors WHERE sort_order = %s", (sort_order,))
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE floors
                SET sheet_id = %s,
                    name = %s,
                    block_name = %s,
                    unit_count = %s
                WHERE id = %s
                RETURNING id
                """,
                (sheet_id, name, block_name, unit_count, row[0]),
            )
            return int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (sheet_id, sort_order, name, block_name, unit_count),
        )
        return int(cur.fetchone()[0])


def ensure_unit(conn: psycopg.Connection, *, floor_id: int, sort_order: int, name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM units WHERE floor_id = %s AND sort_order = %s",
            (floor_id, sort_order),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE units SET name = %s WHERE id = %s RETURNING id",
                (name, row[0]),
            )
            return int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO units (floor_id, sort_order, name)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (floor_id, sort_order, name),
        )
        return int(cur.fetchone()[0])


def ensure_progress(
    conn: psycopg.Connection,
    *,
    unit_id: int,
    task_id: int,
    value: str,
    updated_by: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO progress (unit_id, task_id, value, updated_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (unit_id, task_id) DO UPDATE
            SET value = EXCLUDED.value,
                updated_by = EXCLUDED.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (unit_id, task_id, value, updated_by),
        )


def ensure_unit_extra(
    conn: psycopg.Connection,
    *,
    unit_id: int,
    updated_by: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO unit_extra (unit_id, initial_check, recheck_1, recheck_2, handover, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (unit_id) DO UPDATE
            SET initial_check = EXCLUDED.initial_check,
                recheck_1 = EXCLUDED.recheck_1,
                recheck_2 = EXCLUDED.recheck_2,
                handover = EXCLUDED.handover,
                updated_by = EXCLUDED.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (unit_id, "", "", "", STATUS_WORKING, updated_by),
        )


def ensure_extra_field(
    conn: psycopg.Connection,
    *,
    sheet_id: int,
    field_key: str,
    name: str,
    field_type: str,
    sort_order: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extra_fields (sheet_id, field_key, name, field_type, sort_order, is_builtin, active)
            VALUES (%s, %s, %s, %s, %s, 0, 1)
            ON CONFLICT (sheet_id, field_key) DO UPDATE
            SET name = EXCLUDED.name,
                field_type = EXCLUDED.field_type,
                sort_order = EXCLUDED.sort_order,
                active = 1
            """,
            (sheet_id, field_key, name, field_type, sort_order),
        )


def ensure_unit_extra_value(
    conn: psycopg.Connection,
    *,
    unit_id: int,
    field_key: str,
    value: str,
    updated_by: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO unit_extra_values (unit_id, field_key, value, updated_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (unit_id, field_key) DO UPDATE
            SET value = EXCLUDED.value,
                updated_by = EXCLUDED.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (unit_id, field_key, value, updated_by),
        )


def ensure_vendor_contact(
    conn: psycopg.Connection,
    *,
    sheet_id: int,
    vendor_name: str,
    contact_name: str,
    contact_title: str,
    contact_phone: str,
    is_primary: int,
    contact_order: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM vendor_contacts
            WHERE sheet_id = %s AND vendor_name = %s AND contact_order = %s
            """,
            (sheet_id, vendor_name, contact_order),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE vendor_contacts
                SET contact_name = %s,
                    contact_title = %s,
                    contact_phone = %s,
                    is_primary = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (contact_name, contact_title, contact_phone, is_primary, row[0]),
            )
            return

        cur.execute(
            """
            INSERT INTO vendor_contacts
                (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (sheet_id, vendor_name, contact_name, contact_title, contact_phone, is_primary, contact_order),
        )


def ensure_vendor_work_entry(
    conn: psycopg.Connection,
    *,
    sheet_id: int,
    vendor_name: str,
    business_date: str,
    planned_at: str,
    planned_headcount: int,
    actual_headcount: int,
    work_content: str,
    work_headcount: int,
    entry_order: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM vendor_work_entries
            WHERE sheet_id = %s AND vendor_name = %s AND business_date = %s AND entry_order = %s
            """,
            (sheet_id, vendor_name, business_date, entry_order),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE vendor_work_entries
                SET planned_at = %s,
                    planned_headcount = %s,
                    actual_headcount = %s,
                    work_content = %s,
                    work_headcount = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    planned_at,
                    planned_headcount,
                    actual_headcount,
                    work_content,
                    work_headcount,
                    row[0],
                ),
            )
            return

        cur.execute(
            """
            INSERT INTO vendor_work_entries
                (sheet_id, vendor_name, business_date, planned_at, planned_headcount, actual_headcount, work_content, work_headcount, entry_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                sheet_id,
                vendor_name,
                business_date,
                planned_at,
                planned_headcount,
                actual_headcount,
                work_content,
                work_headcount,
                entry_order,
            ),
        )


def delete_managed_rows(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM sheets WHERE name = ANY(%s)", (list(MANAGED_SHEET_NAMES),))
        sheet_ids = [int(row[0]) for row in cur.fetchall()]

        if sheet_ids:
            cur.execute(
                "SELECT id FROM floors WHERE sheet_id = ANY(%s)",
                (sheet_ids,),
            )
            floor_ids = [int(row[0]) for row in cur.fetchall()]
        else:
            floor_ids = []

        if floor_ids:
            cur.execute(
                "SELECT id FROM units WHERE floor_id = ANY(%s)",
                (floor_ids,),
            )
            unit_ids = [int(row[0]) for row in cur.fetchall()]
        else:
            unit_ids = []

        if unit_ids:
            cur.execute("DELETE FROM unit_extra_values WHERE unit_id = ANY(%s)", (unit_ids,))
            cur.execute("DELETE FROM progress WHERE unit_id = ANY(%s)", (unit_ids,))
            cur.execute("DELETE FROM unit_extra WHERE unit_id = ANY(%s)", (unit_ids,))
            cur.execute("DELETE FROM units WHERE id = ANY(%s)", (unit_ids,))

        if floor_ids:
            cur.execute("DELETE FROM floors WHERE id = ANY(%s)", (floor_ids,))

        if sheet_ids:
            cur.execute("DELETE FROM vendor_contacts WHERE sheet_id = ANY(%s)", (sheet_ids,))
            cur.execute("DELETE FROM vendor_work_entries WHERE sheet_id = ANY(%s)", (sheet_ids,))
            cur.execute("DELETE FROM extra_fields WHERE sheet_id = ANY(%s)", (sheet_ids,))
            cur.execute("DELETE FROM tasks WHERE sheet_id = ANY(%s)", (sheet_ids,))
            cur.execute("DELETE FROM sheets WHERE id = ANY(%s)", (sheet_ids,))

        cur.execute("SELECT id FROM sites WHERE site_name = ANY(%s)", (list(MANAGED_SITE_NAMES),))
        site_ids = [int(row[0]) for row in cur.fetchall()]
        if site_ids:
            cur.execute("DELETE FROM user_site_permissions WHERE site_id = ANY(%s)", (site_ids,))
            cur.execute("DELETE FROM sites WHERE id = ANY(%s)", (site_ids,))

        cur.execute("DELETE FROM user_site_permissions WHERE user_id IN (SELECT id FROM users WHERE username = ANY(%s))", (list(MANAGED_USERNAMES),))
        cur.execute("DELETE FROM users WHERE username = ANY(%s)", (list(MANAGED_USERNAMES),))


def seed_site_bundle(
    conn: psycopg.Connection,
    *,
    admin_user_id: int,
    site_spec: SiteSpec,
) -> dict[str, Any]:
    site_id = ensure_site(conn, site_name=site_spec.name, site_code=site_spec.code)
    sheet_id = ensure_sheet(conn, site_id=site_id, sheet_name=site_spec.sheet_name)

    tasks = [
        (site_spec.task_base + 1, site_spec.vendors[0], "Tower", f"{site_spec.sheet_name}_task_prime"),
        (site_spec.task_base + 2, site_spec.vendors[1], "Lobby", f"{site_spec.sheet_name}_task_finish"),
    ]
    task_ids: list[int] = []
    for col_index, vendor_name, location, task_name in tasks:
        task_ids.append(
            ensure_task(
                conn,
                sheet_id=sheet_id,
                col_index=col_index,
                vendor=vendor_name,
                location=location,
                name=task_name,
            )
        )

    floor_a_id = ensure_floor(
        conn,
        sheet_id=sheet_id,
        sort_order=site_spec.floor_base,
        name=f"{site_spec.sheet_name}_1f",
        block_name="A",
        unit_count=2,
    )
    floor_b_id = ensure_floor(
        conn,
        sheet_id=sheet_id,
        sort_order=site_spec.floor_base + 1,
        name=f"{site_spec.sheet_name}_2f",
        block_name="B",
        unit_count=1,
    )

    units = [
        ensure_unit(conn, floor_id=floor_a_id, sort_order=1, name=f"{site_spec.sheet_name}_101"),
        ensure_unit(conn, floor_id=floor_a_id, sort_order=2, name=f"{site_spec.sheet_name}_102"),
        ensure_unit(conn, floor_id=floor_b_id, sort_order=1, name=f"{site_spec.sheet_name}_201"),
    ]

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = %s) WHERE id = %s",
            (floor_a_id, floor_a_id),
        )
        cur.execute(
            "UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = %s) WHERE id = %s",
            (floor_b_id, floor_b_id),
        )

    ensure_extra_field(
        conn,
        sheet_id=sheet_id,
        field_key="release_note",
        name="release_note",
        field_type="date",
        sort_order=10,
    )
    ensure_extra_field(
        conn,
        sheet_id=sheet_id,
        field_key="release_status",
        name="release_status",
        field_type="status",
        sort_order=11,
    )

    for unit_id in units:
        ensure_unit_extra(conn, unit_id=unit_id, updated_by=admin_user_id)
        ensure_unit_extra_value(
            conn,
            unit_id=unit_id,
            field_key="release_note",
            value="2026-07-01",
            updated_by=admin_user_id,
        )
        ensure_unit_extra_value(
            conn,
            unit_id=unit_id,
            field_key="release_status",
            value=STATUS_WORKING,
            updated_by=admin_user_id,
        )
        for idx, task_id in enumerate(task_ids):
            ensure_progress(
                conn,
                unit_id=unit_id,
                task_id=task_id,
                value=STATUS_DONE if idx == 0 else STATUS_WORKING,
                updated_by=admin_user_id,
            )

    ensure_vendor_contact(
        conn,
        sheet_id=sheet_id,
        vendor_name=site_spec.vendors[0],
        contact_name=f"{site_spec.sheet_name}_contact_primary",
        contact_title="PM",
        contact_phone="0900-000-001",
        is_primary=1,
        contact_order=1,
    )
    ensure_vendor_contact(
        conn,
        sheet_id=sheet_id,
        vendor_name=site_spec.vendors[1],
        contact_name=f"{site_spec.sheet_name}_contact_secondary",
        contact_title="Supervisor",
        contact_phone="0900-000-002",
        is_primary=1,
        contact_order=1,
    )
    ensure_vendor_work_entry(
        conn,
        sheet_id=sheet_id,
        vendor_name=site_spec.vendors[0],
        business_date="2026-07-01",
        planned_at="08:00",
        planned_headcount=4,
        actual_headcount=4,
        work_content=f"{site_spec.sheet_name}_work_prime",
        work_headcount=4,
        entry_order=1,
    )
    ensure_vendor_work_entry(
        conn,
        sheet_id=sheet_id,
        vendor_name=site_spec.vendors[1],
        business_date="2026-07-01",
        planned_at="13:30",
        planned_headcount=3,
        actual_headcount=2,
        work_content=f"{site_spec.sheet_name}_work_finish",
        work_headcount=2,
        entry_order=1,
    )

    return {
        "site_id": site_id,
        "sheet_id": sheet_id,
        "task_ids": task_ids,
        "floor_ids": [floor_a_id, floor_b_id],
        "unit_ids": units,
    }


def collect_summary_counts(conn: psycopg.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sites WHERE site_name = ANY(%s)", (list(MANAGED_SITE_NAMES),))
        counts["sites"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM sheets WHERE name = ANY(%s)", (list(MANAGED_SHEET_NAMES),))
        counts["sheets"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM users WHERE username = ANY(%s)", (list(MANAGED_USERNAMES),))
        counts["users"] = int(cur.fetchone()[0])
        cur.execute(
            "SELECT COUNT(*) FROM user_site_permissions WHERE user_id IN (SELECT id FROM users WHERE username = ANY(%s))",
            (list(MANAGED_USERNAMES),),
        )
        counts["user_site_permissions"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM tasks WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))", (list(MANAGED_SHEET_NAMES),))
        counts["tasks"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM floors WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))", (list(MANAGED_SHEET_NAMES),))
        counts["floors"] = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*)
            FROM units
            WHERE floor_id IN (
                SELECT id FROM floors WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))
            )
            """,
            (list(MANAGED_SHEET_NAMES),),
        )
        counts["units"] = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*)
            FROM progress
            WHERE unit_id IN (
                SELECT id FROM units WHERE floor_id IN (
                    SELECT id FROM floors WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))
                )
            )
            """,
            (list(MANAGED_SHEET_NAMES),),
        )
        counts["progress"] = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*)
            FROM unit_extra
            WHERE unit_id IN (
                SELECT id FROM units WHERE floor_id IN (
                    SELECT id FROM floors WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))
                )
            )
            """,
            (list(MANAGED_SHEET_NAMES),),
        )
        counts["unit_extra"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM extra_fields WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))", (list(MANAGED_SHEET_NAMES),))
        counts["extra_fields"] = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*)
            FROM unit_extra_values
            WHERE unit_id IN (
                SELECT id FROM units WHERE floor_id IN (
                    SELECT id FROM floors WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))
                )
            )
            """,
            (list(MANAGED_SHEET_NAMES),),
        )
        counts["unit_extra_values"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM vendor_contacts WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))", (list(MANAGED_SHEET_NAMES),))
        counts["vendor_contacts"] = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM vendor_work_entries WHERE sheet_id IN (SELECT id FROM sheets WHERE name = ANY(%s))", (list(MANAGED_SHEET_NAMES),))
        counts["vendor_work_entries"] = int(cur.fetchone()[0])
    return counts


def print_summary(prefix: str, counts: dict[str, int]) -> None:
    for key, value in counts.items():
        print(f"{prefix}_{key}: {value}")


def main() -> int:
    args = parse_args()
    require_staging_guard()

    database_url = require_postgres_database_url()
    require_staging_target(database_url)
    redacted_target = redact_database_url(database_url)

    print("staging_release_seed_scope: postgres_only")
    print(f"target_database_url: {redacted_target}")
    print(f"mode: {'dry-run' if args.dry_run else 'apply'}")
    print(f"clear_and_reseed: {str(args.clear_and_reseed).lower()}")
    print(f"app_env: {os.environ.get('APP_ENV', '').strip() or '<unset>'}")
    print(f"staging_seed_allowed: {str(env_flag('STAGING_SEED_ALLOWED')).lower()}")
    print(f"managed_sites: {', '.join(MANAGED_SITE_NAMES)}")
    print(f"managed_sheets: {', '.join(MANAGED_SHEET_NAMES)}")
    print(f"managed_users: {', '.join(MANAGED_USERNAMES)}")
    print(f"managed_vendors: {', '.join(MANAGED_VENDORS)}")

    if args.dry_run:
        print("dry_run_execution: offline_preview_only")
        print("dry_run_database_mutation: no")
        print_summary("planned_summary", PLANNED_SUMMARY_COUNTS)
        print("PASS staging release seed dry-run passed.")
        return 0

    with psycopg.connect(database_url) as conn:
        ensure_required_tables(conn)
        ensure_meta_defaults(conn)

        if args.clear_and_reseed:
            delete_managed_rows(conn)

        admin_user_id = ensure_user(
            conn,
            username=ADMIN_USERNAME,
            display_name="Staging Admin",
            role="admin",
        )
        single_site_user_id = ensure_user(
            conn,
            username=SINGLE_SITE_USERNAME,
            display_name="Single Site User",
            role="member",
        )
        multi_site_user_id = ensure_user(
            conn,
            username=MULTI_SITE_USERNAME,
            display_name="Multi Site User",
            role="member",
        )
        ensure_user(
            conn,
            username=ZERO_SITE_USERNAME,
            display_name="Zero Site User",
            role="member",
        )
        permission_removed_user_id = ensure_user(
            conn,
            username=PERMISSION_REMOVED_USERNAME,
            display_name="Permission Removed User",
            role="member",
        )

        seeded_sites = [seed_site_bundle(conn, admin_user_id=admin_user_id, site_spec=spec) for spec in SITE_SPECS]
        site_a_id = int(seeded_sites[0]["site_id"])
        site_b_id = int(seeded_sites[1]["site_id"])

        ensure_permission(conn, user_id=single_site_user_id, site_id=site_a_id, role="member")
        ensure_permission(conn, user_id=multi_site_user_id, site_id=site_a_id, role="member")
        ensure_permission(conn, user_id=multi_site_user_id, site_id=site_b_id, role="supervisor")
        ensure_permission(conn, user_id=permission_removed_user_id, site_id=site_a_id, role="member")

        summary = collect_summary_counts(conn)
        print_summary("summary", summary)

        conn.commit()
        print("PASS staging release seed applied.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
