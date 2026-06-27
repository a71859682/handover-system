from __future__ import annotations

import os
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("FAIL: DATABASE_URL is not set")
        return 1

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        print(f"FAIL: DATABASE_URL is not PostgreSQL: {parsed.scheme}")
        return 1

    connect_url = database_url
    if parsed.scheme == "postgres":
        connect_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif parsed.scheme == "postgresql":
        connect_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

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
