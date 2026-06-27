from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import app

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("FAIL: DATABASE_URL is not set")
        return 1

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgres", "postgresql+psycopg"}:
        print(f"FAIL: DATABASE_URL is not PostgreSQL: {parsed.scheme}")
        return 1

    connect_url = app.normalize_sqlalchemy_database_url(database_url)

    try:
        engine = create_engine(connect_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar_one()
        if result != 1:
            print(f"FAIL: unexpected SELECT 1 result: {result!r}")
            return 1
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
