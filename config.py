from __future__ import annotations

import os

from sqlite_db_path import get_sqlite_db_path


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str = "") -> tuple[str, ...]:
    value = os.environ.get(name, default)
    return tuple(part.strip() for part in value.split(",") if part.strip())


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
APP_DB_PATH = get_sqlite_db_path()
USE_SQLALCHEMY_READS = _env_flag("USE_SQLALCHEMY_READS", default=False)
USE_SQLALCHEMY_WRITES = _env_flag("USE_SQLALCHEMY_WRITES", default=False)
DUAL_WRITE_DRY_RUN = _env_flag("DUAL_WRITE_DRY_RUN", default=False)
DUAL_WRITE_ENABLED = _env_flag("DUAL_WRITE_ENABLED", default=False)
DUAL_WRITE_TABLES = _env_csv("DUAL_WRITE_TABLES", default="meta")
DUAL_WRITE_STRICT = _env_flag("DUAL_WRITE_STRICT", default=False)
