from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
APP_DB_PATH = Path(os.environ.get("APP_DB_PATH", BASE_DIR / "site.db"))
USE_SQLALCHEMY_READS = _env_flag("USE_SQLALCHEMY_READS", default=False)
USE_SQLALCHEMY_WRITES = _env_flag("USE_SQLALCHEMY_WRITES", default=False)
