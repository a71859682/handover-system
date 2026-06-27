from __future__ import annotations

import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    APP_DB_PATH,
    DATABASE_URL,
    DUAL_WRITE_ENABLED,
    DUAL_WRITE_DRY_RUN,
    DUAL_WRITE_STRICT,
    DUAL_WRITE_TABLES,
    USE_SQLALCHEMY_READS,
    USE_SQLALCHEMY_WRITES,
)


def main() -> int:
    print(f"USE_SQLALCHEMY_READS={str(USE_SQLALCHEMY_READS).lower()}")
    print(f"USE_SQLALCHEMY_WRITES={str(USE_SQLALCHEMY_WRITES).lower()}")
    print(f"DUAL_WRITE_DRY_RUN={str(DUAL_WRITE_DRY_RUN).lower()}")
    print(f"DUAL_WRITE_ENABLED={str(DUAL_WRITE_ENABLED).lower()}")
    print(f"DUAL_WRITE_TABLES={','.join(DUAL_WRITE_TABLES)}")
    print(f"DUAL_WRITE_STRICT={str(DUAL_WRITE_STRICT).lower()}")
    print(f"DATABASE_URL_SET={'true' if bool(DATABASE_URL) else 'false'}")
    print(f"APP_DB_PATH={APP_DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
