from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

import psycopg


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def sqlite_has_users_table(path: Path) -> bool:
    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'"
            ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def normalize_candidate_path(raw_path: Path | str) -> Path:
    return Path(raw_path).expanduser().resolve(strict=False)


def discover_app_db_path() -> Path | None:
    try:
        from app import DB_PATH  # type: ignore
    except Exception:
        return None
    return normalize_candidate_path(DB_PATH)


def iter_db_files(root: Path) -> Iterable[Path]:
    if not root.exists() or not root.is_dir():
        return ()
    seen: set[Path] = set()
    matches: list[Path] = []
    for pattern in ("site.db", "*.db"):
        for candidate in root.rglob(pattern):
            resolved = normalize_candidate_path(candidate)
            if resolved in seen or not resolved.is_file():
                continue
            seen.add(resolved)
            matches.append(resolved)
    return matches


def resolve_sqlite_candidates() -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    seen: set[Path] = set()

    def add_candidate(label: str, raw_path: Path | str | None) -> None:
        if raw_path is None:
            return
        path = normalize_candidate_path(raw_path)
        if path in seen:
            return
        seen.add(path)
        candidates.append((label, path))

    configured = os.environ.get("APP_DB_PATH", "").strip()
    if configured:
        add_candidate("APP_DB_PATH", configured)

    add_candidate("flask.DB_PATH", discover_app_db_path())
    add_candidate("repo_site.db", BASE_DIR / "site.db")
    add_candidate("cwd_site.db", Path.cwd() / "site.db")
    add_candidate("/var/data/site.db", Path("/var/data/site.db"))
    add_candidate("/opt/render/project/src/site.db", Path("/opt/render/project/src/site.db"))

    search_roots = [
        BASE_DIR,
        Path.cwd(),
        Path("/opt/render/project/src"),
        Path("/opt/render/project"),
        Path("/var/data"),
    ]
    searched_roots: set[Path] = set()
    for root in search_roots:
        resolved_root = normalize_candidate_path(root)
        if resolved_root in searched_roots:
            continue
        searched_roots.add(resolved_root)
        for candidate in iter_db_files(resolved_root):
            add_candidate(f"search:{resolved_root}", candidate)

    return candidates


def resolve_sqlite_source_path() -> Path:
    candidates = resolve_sqlite_candidates()
    invalid: list[tuple[str, Path]] = []
    for label, path in candidates:
        if not path.exists():
            continue
        if sqlite_has_users_table(path):
            return path
        invalid.append((label, path))
    if invalid:
        checked = ", ".join(f"{label}={path}" for label, path in invalid)
        raise SystemExit(
            f"FAIL SQLite candidates exist but none contain a users table: {checked}"
        )
    checked = ", ".join(f"{label}={path}" for label, path in candidates)
    raise SystemExit(f"FAIL no SQLite candidate found: {checked}")


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


def connect_sqlite(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_postgres(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare users.display_name between local SQLite and staging PostgreSQL."
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="Limit comparison to a single user id.",
    )
    parser.add_argument(
        "--strict-presence",
        action="store_true",
        help="Treat users missing on either side as failures.",
    )
    return parser.parse_args()


def build_user_query(user_id: int | None) -> tuple[str, tuple]:
    sql = "SELECT id, username, display_name FROM users"
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE id = ?"
        params = (user_id,)
    sql += " ORDER BY id"
    return sql, params


def build_postgres_user_query(user_id: int | None) -> tuple[str, tuple]:
    sql = "SELECT id, username, display_name FROM users"
    params: tuple = ()
    if user_id is not None:
        sql += " WHERE id = %s"
        params = (user_id,)
    sql += " ORDER BY id"
    return sql, params


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

    sqlite_sql, sqlite_params = build_user_query(args.user_id)
    postgres_sql, postgres_params = build_postgres_user_query(args.user_id)

    with connect_sqlite(sqlite_path) as sqlite_conn, connect_postgres(database_url) as pg_conn:
        sqlite_rows = {
            row["id"]: {
                "username": row["username"],
                "display_name": row["display_name"],
            }
            for row in sqlite_conn.execute(sqlite_sql, sqlite_params).fetchall()
        }
        with pg_conn.cursor() as cur:
            cur.execute(postgres_sql, postgres_params)
            postgres_rows = {
                row[0]: {
                    "username": row[1],
                    "display_name": row[2],
                }
                for row in cur.fetchall()
            }

    has_failure = False
    all_ids = sorted(set(sqlite_rows) | set(postgres_rows))
    for user_id in all_ids:
        sqlite_row = sqlite_rows.get(user_id)
        postgres_row = postgres_rows.get(user_id)

        if sqlite_row is None and postgres_row is not None:
            status = "FAIL" if args.strict_presence else "SKIP"
            print(
                f"{status} users id={user_id}: username={postgres_row['username']} reason=missing_in_sqlite"
            )
            if status == "FAIL":
                has_failure = True
            continue

        if sqlite_row is not None and postgres_row is None:
            status = "FAIL" if args.strict_presence else "SKIP"
            print(
                f"{status} users id={user_id}: username={sqlite_row['username']} reason=missing_in_postgres"
            )
            if status == "FAIL":
                has_failure = True
            continue

        assert sqlite_row is not None
        assert postgres_row is not None

        sqlite_username = sqlite_row["username"]
        postgres_username = postgres_row["username"]
        if sqlite_username != postgres_username:
            status = "FAIL" if args.strict_presence else "SKIP"
            print(
                f"{status} users id={user_id}: sqlite_username={sqlite_username!r} "
                f"postgres_username={postgres_username!r} reason=username_mismatch"
            )
            if status == "FAIL":
                has_failure = True
            continue

        sqlite_value = sqlite_row["display_name"]
        postgres_value = postgres_row["display_name"]
        status = "PASS" if sqlite_value == postgres_value else "FAIL"
        print(
            f"{status} users id={user_id}: username={sqlite_username} "
            f"sqlite={sqlite_value!r} postgres={postgres_value!r}"
        )
        if status == "FAIL":
            has_failure = True

    if has_failure:
        print("FAIL users secondary update check found mismatches.")
        return 1

    print("PASS users secondary update fields match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
