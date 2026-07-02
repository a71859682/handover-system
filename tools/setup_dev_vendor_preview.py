from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import db, generate_password_hash, resolve_crew_business_date  # noqa: E402
from tools._dev_vendor_preview import (  # noqa: E402
    EMPTY_USERNAME,
    EMPTY_VENDOR_NAME,
    EXPECTED_PREVIEW_ENTRY_COUNT,
    PREVIEW_USERNAME,
    PREVIEW_VENDOR_NAME,
    build_status_summary,
    collect_dev_vendor_preview_inventory,
    format_status_lines,
)


PASSWORD_ENV_NAME = "DEV_VENDOR_PREVIEW_PASSWORD"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reuse-first setup for Dev vendor preview test data.")
    parser.add_argument("--dry-run", action="store_true", help="Preview setup actions without mutating the target DB.")
    return parser.parse_args()


def _build_actions(summary: dict[str, object]) -> tuple[list[str], list[str], list[str], list[str]]:
    reuse: list[str] = []
    missing: list[str] = []
    would_create: list[str] = []
    blockers: list[str] = []

    target = summary["target"]  # type: ignore[index]
    preview_vendor = summary["preview_vendor"]  # type: ignore[index]
    empty_vendor = summary["empty_vendor"]  # type: ignore[index]
    preview_entries = summary["preview_entries"]  # type: ignore[index]
    empty_entries = summary["empty_entries"]  # type: ignore[index]
    safe_sheet = summary["safe_sheet"]  # type: ignore[index]

    if not bool(target["safe_target"]):  # type: ignore[index]
        blockers.append("unsafe_target")

    if bool(preview_vendor["ready"]):  # type: ignore[index]
        reuse.append("preview_vendor")
    elif bool(preview_vendor["missing"]):  # type: ignore[index]
        missing.append("preview_vendor")
        would_create.append("preview_vendor")
    else:
        blockers.append("preview_vendor_conflict")

    if bool(empty_vendor["ready"]):  # type: ignore[index]
        reuse.append("empty_vendor")
    elif bool(empty_vendor["missing"]):  # type: ignore[index]
        missing.append("empty_vendor")
        would_create.append("empty_vendor")
    else:
        blockers.append("empty_vendor_conflict")

    if bool(preview_entries["ready"]):  # type: ignore[index]
        reuse.append("preview_entries")
    elif bool(preview_entries["missing"]):  # type: ignore[index]
        missing.append("preview_entries")
        would_create.append("preview_entries")
    else:
        blockers.append("preview_entries_conflict")

    if bool(empty_entries["ready"]):  # type: ignore[index]
        reuse.append("empty_entries")
    else:
        blockers.append("empty_entries_conflict")

    if bool(safe_sheet["ready"]):  # type: ignore[index]
        reuse.append("safe_sheet")
    else:
        blockers.append("safe_sheet_missing")

    return reuse, missing, would_create, blockers


def _create_vendor_account(conn: sqlite3.Connection, *, username: str, vendor_name: str, password: str) -> None:
    conn.execute(
        """
        INSERT INTO vendor_accounts (username, password_hash, vendor_name, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (username, generate_password_hash(password), vendor_name),
    )


def _create_preview_entries(conn: sqlite3.Connection, *, sheet_id: int, vendor_name: str) -> None:
    business_date = resolve_crew_business_date()
    earlier_business_date = (datetime.fromisoformat(business_date)).date().replace(day=1).isoformat()
    rows = (
        (sheet_id, vendor_name, business_date, f"{business_date} 09:00", 3, 1, "Preview Work 1", 1, 0),
        (sheet_id, vendor_name, business_date, f"{business_date} 10:00", 2, 0, "Preview Work 2", 0, 1),
        (sheet_id, vendor_name, earlier_business_date, "", 5, 4, "Preview Work 0", 4, 2),
    )
    conn.executemany(
        """
        INSERT INTO vendor_work_entries (
            sheet_id, vendor_name, business_date, planned_at, planned_headcount,
            actual_headcount, work_content, work_headcount, entry_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        rows,
    )


def main() -> int:
    args = parse_args()

    print("dev_vendor_preview_setup_scope: dev_only_reuse_first")
    print(f"dry_run: {str(bool(args.dry_run)).lower()}")
    with db() as conn:
        conn.row_factory = sqlite3.Row
        inventory = collect_dev_vendor_preview_inventory(conn)

    summary = build_status_summary(inventory)
    for line in format_status_lines(summary):
        print(line)

    reuse, missing, would_create, blockers = _build_actions(summary)
    print(f"reuse: {', '.join(reuse) if reuse else 'none'}")
    print(f"missing: {', '.join(missing) if missing else 'none'}")
    print(f"would_create: {', '.join(would_create) if would_create else 'none'}")
    print(f"blockers: {', '.join(blockers) if blockers else 'none'}")

    if blockers:
        raise SystemExit("FAIL dev vendor preview setup blocked.")

    if args.dry_run:
        print("PASS dev vendor preview setup dry-run passed.")
        return 0

    if not would_create:
        print("PASS dev vendor preview setup reused existing data.")
        return 0

    dev_password = os.environ.get(PASSWORD_ENV_NAME, "")
    if not dev_password:
        raise SystemExit(f"FAIL missing required env var: {PASSWORD_ENV_NAME}")

    with db() as conn:
        conn.row_factory = sqlite3.Row
        if "preview_vendor" in would_create:
            _create_vendor_account(
                conn,
                username=PREVIEW_USERNAME,
                vendor_name=PREVIEW_VENDOR_NAME,
                password=dev_password,
            )
        if "empty_vendor" in would_create:
            _create_vendor_account(
                conn,
                username=EMPTY_USERNAME,
                vendor_name=EMPTY_VENDOR_NAME,
                password=dev_password,
            )
        if "preview_entries" in would_create:
            refreshed_inventory = collect_dev_vendor_preview_inventory(conn)
            refreshed_summary = build_status_summary(refreshed_inventory)
            safe_sheet = refreshed_summary["safe_sheet"]["sheet"]  # type: ignore[index]
            if safe_sheet is None:
                raise SystemExit("FAIL safe_sheet_missing during preview entry creation.")
            _create_preview_entries(
                conn,
                sheet_id=int(safe_sheet["id"]),
                vendor_name=PREVIEW_VENDOR_NAME,
            )
        conn.commit()

        final_inventory = collect_dev_vendor_preview_inventory(conn)

    final_summary = build_status_summary(final_inventory)
    print("---")
    print("post_setup_status:")
    for line in format_status_lines(final_summary):
        print(line)

    if (
        bool(final_summary["preview_vendor"]["ready"])
        and bool(final_summary["empty_vendor"]["ready"])
        and bool(final_summary["preview_entries"]["ready"])
        and bool(final_summary["empty_entries"]["ready"])
        and bool(final_summary["safe_sheet"]["ready"])
    ):
        print("PASS dev vendor preview setup applied successfully.")
        return 0

    raise SystemExit("FAIL dev vendor preview setup applied but readiness is incomplete.")


if __name__ == "__main__":
    raise SystemExit(main())
