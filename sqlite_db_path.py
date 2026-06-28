from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class SqliteDbPathResolution:
    path: Path
    source: str
    raw_env_value: str


def _is_windows_absolute_path(raw_path: str) -> bool:
    if len(raw_path) < 3:
        return False
    return raw_path[1] == ":" and raw_path[2] in ("\\", "/")


def resolve_sqlite_db_path(raw_env_value: str | None = None) -> SqliteDbPathResolution:
    env_value = (raw_env_value if raw_env_value is not None else os.environ.get("APP_DB_PATH", "")).strip()
    default_path = BASE_DIR / "site.db"

    if env_value:
        if os.name != "nt" and _is_windows_absolute_path(env_value):
            return SqliteDbPathResolution(
                path=default_path,
                source="fallback_default_invalid_windows_env_on_non_windows",
                raw_env_value=env_value,
            )
        return SqliteDbPathResolution(
            path=Path(env_value).expanduser().resolve(strict=False),
            source="env_APP_DB_PATH",
            raw_env_value=env_value,
        )

    return SqliteDbPathResolution(
        path=default_path.resolve(strict=False),
        source="default_project_site_db",
        raw_env_value="",
    )


def get_sqlite_db_path(raw_env_value: str | None = None) -> Path:
    return resolve_sqlite_db_path(raw_env_value).path
