from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from check_users_secondary_update import (
    connect_postgres,
    connect_sqlite,
    redact_database_url,
    resolve_sqlite_source_path,
)


BASE_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill PostgreSQL users.display_name from SQLite for matching user ids/usernames."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned PostgreSQL users.display_name updates without applying them.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply PostgreSQL users.display_name updates. Defaults to dry-run when omitted.",
    )
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("--dry-run and --apply cannot be used together.")
    return args


def fetch_sqlite_users(sqlite_path: Path) -> dict[int, sqlite3.Row]:
    with connect_sqlite(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT id, username, display_name, role FROM users ORDER BY id"
        ).fetchall()
    return {row["id"]: row for row in rows}


def fetch_postgres_users(database_url: str) -> dict[int, dict[str, object]]:
    with connect_postgres(database_url) as pg_conn:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT id, username, display_name, role FROM users ORDER BY id")
            rows = cur.fetchall()
    return {
        row[0]: {
            "id": row[0],
            "username": row[1],
            "display_name": row[2],
            "role": row[3],
        }
        for row in rows
    }


def build_plan_lines(
    sqlite_rows: dict[int, sqlite3.Row],
    postgres_rows: dict[int, dict[str, object]],
) -> tuple[list[str], list[tuple[int, str, str | None, str | None]]]:
    lines: list[str] = ["PLAN users.display_name sync"]
    updates: list[tuple[int, str, str | None, str | None]] = []

    all_ids = sorted(set(sqlite_rows) | set(postgres_rows))
    for user_id in all_ids:
        sqlite_row = sqlite_rows.get(user_id)
        postgres_row = postgres_rows.get(user_id)

        if sqlite_row is None and postgres_row is not None:
            lines.append(
                f"id={user_id} username={postgres_row['username']} action=skip reason=missing_in_sqlite"
            )
            continue

        if sqlite_row is not None and postgres_row is None:
            lines.append(
                f"id={user_id} username={sqlite_row['username']} action=skip reason=missing_in_postgres"
            )
            continue

        assert sqlite_row is not None
        assert postgres_row is not None

        sqlite_username = sqlite_row["username"]
        postgres_username = postgres_row["username"]
        if sqlite_username != postgres_username:
            lines.append(
                f"id={user_id} username={sqlite_username} action=skip reason=username_mismatch postgres_username={postgres_username}"
            )
            continue

        sqlite_display_name = sqlite_row["display_name"]
        postgres_display_name = postgres_row["display_name"]
        if sqlite_display_name == postgres_display_name:
            lines.append(
                f"id={user_id} username={sqlite_username} action=noop reason=already_in_sync"
            )
            continue

        updates.append(
            (user_id, str(sqlite_username), sqlite_display_name, postgres_display_name)
        )
        lines.append(
            f"id={user_id} username={sqlite_username} sqlite={sqlite_display_name!r} "
            f"postgres={postgres_display_name!r} action=update_postgres_display_name"
        )

    return lines, updates


def apply_updates(
    database_url: str,
    updates: list[tuple[int, str, str | None, str | None]],
) -> int:
    applied = 0
    with connect_postgres(database_url) as pg_conn:
        with pg_conn.cursor() as cur:
            for user_id, username, sqlite_display_name, _postgres_display_name in updates:
                cur.execute(
                    "UPDATE users SET display_name = %s WHERE id = %s AND username = %s",
                    (sqlite_display_name, user_id, username),
                )
                if cur.rowcount != 1:
                    raise SystemExit(
                        f"FAIL expected exactly 1 PostgreSQL row to update for id={user_id} username={username!r}, got {cur.rowcount}"
                    )
                applied += 1
        pg_conn.commit()
    return applied


def run_secondary_check() -> int:
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "tools" / "check_users_secondary_update.py")],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is not configured.")
        print("PASS")
        return 0

    sqlite_path = resolve_sqlite_source_path()
    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    sqlite_rows = fetch_sqlite_users(sqlite_path)
    postgres_rows = fetch_postgres_users(database_url)
    plan_lines, updates = build_plan_lines(sqlite_rows, postgres_rows)
    for line in plan_lines:
        print(line)

    if not args.apply:
        print("DRY_RUN no changes applied.")
        print("PASS")
        return 0

    applied = apply_updates(database_url, updates)
    print(f"APPLY updated_rows={applied}")

    check_result = run_secondary_check()
    if check_result != 0:
        return check_result

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
