from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import APP_DB_PATH  # noqa: E402
from check_users_id_allocation import fetch_sqlite_users_schema  # noqa: E402
from check_users_secondary_update import (  # noqa: E402
    discover_app_db_path,
    resolve_sqlite_candidates,
    resolve_sqlite_source_path,
)
from sqlite_db_path import resolve_sqlite_db_path  # noqa: E402


PERSISTENT_PREFIXES = (
    "/var/data",
    "/mnt",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect the runtime SQLite path, file metadata, and persistence risk without modifying data."
    )
    return parser.parse_args()


def classify_persistence(sqlite_path: Path) -> tuple[bool, str]:
    sqlite_path_text = sqlite_path.as_posix()
    if any(sqlite_path_text.startswith(prefix) for prefix in PERSISTENT_PREFIXES):
        return True, "path_matches_common_persistent_mount"
    if sqlite_path_text.startswith("/opt/render/project/src"):
        return False, "path_is_under_render_source_tree"
    return False, "path_not_under_known_persistent_mount"


def format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def print_candidate_paths(selected_path: Path) -> None:
    print("SQLite candidate paths:")
    seen_existing: set[Path] = set()
    for label, candidate in resolve_sqlite_candidates():
        if not candidate.exists():
            continue
        if candidate in seen_existing:
            continue
        seen_existing.add(candidate)
        selected_marker = "selected" if candidate == selected_path else "other"
        print(f"- {label}: {candidate} [{selected_marker}]")
    if not seen_existing:
        print("- none")


def main() -> int:
    parse_args()

    raw_env_app_db_path = os.environ.get("APP_DB_PATH", "")
    config_app_db_path = APP_DB_PATH
    app_db_path = discover_app_db_path()
    shared_resolution = resolve_sqlite_db_path()
    sqlite_path = resolve_sqlite_source_path()
    sqlite_report = fetch_sqlite_users_schema(sqlite_path)

    print("SQLite runtime path configuration:")
    print(f"- APP_DB_PATH_env: {raw_env_app_db_path!r}")
    print(f"- APP_DB_PATH_config: {config_app_db_path}")
    print(f"- shared_resolver_source: {shared_resolution.source}")
    print(f"- shared_resolver_path: {shared_resolution.path}")
    print(f"- app.DB_PATH: {app_db_path}")
    print(f"- resolved_sqlite_source_path: {sqlite_path}")
    print(f"- app_and_tool_paths_match: {str(app_db_path == sqlite_path).lower()}")
    print(f"- config_and_tool_paths_match: {str(Path(config_app_db_path) == sqlite_path).lower()}")

    print("SQLite file status:")
    print(f"- exists: {str(sqlite_path.exists()).lower()}")
    if sqlite_path.exists():
        stat_result = sqlite_path.stat()
        print(f"- size_bytes: {stat_result.st_size}")
        print(f"- mtime: {format_timestamp(stat_result.st_mtime)}")
        print(f"- inode: {stat_result.st_ino}")
        print(f"- device_id: {stat_result.st_dev}")
    else:
        print("- size_bytes: none")
        print("- mtime: none")
        print("- inode: none")
        print("- device_id: none")

    is_persistent_path, persistence_reason = classify_persistence(sqlite_path)
    print("Persistence assessment:")
    print(f"- path_under_common_persistent_mount: {str(is_persistent_path).lower()}")
    print(f"- reason: {persistence_reason}")
    if sqlite_path.as_posix().startswith("/opt/render/project/src"):
        print(
            "- warning: SQLite is under /opt/render/project/src; this is likely deploy image or instance-local data, "
            "not a persistent runtime data path."
        )
        print("- warning: Do not rely on one-off Render Shell SQLite mutations here for durable production cleanup.")

    print_candidate_paths(sqlite_path)

    print("Current users allocation:")
    print(f"- sqlite_sequence_value: {sqlite_report['sqlite_sequence_value']}")
    print(f"- next_sqlite_user_id: {sqlite_report['next_sqlite_user_id']}")
    print(f"- user_count: {sqlite_report['user_count']}")
    print(f"- max_user_id: {sqlite_report['max_user_id']}")

    print("PASS sqlite runtime persistence inspection completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
