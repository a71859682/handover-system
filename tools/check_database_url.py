from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


def safe_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or ""
    username = parsed.username or ""
    auth = f"{username}:***@" if username else ""
    return f"{parsed.scheme}://{auth}{host}{port}{path}"


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("using sqlite fallback")
        return 0

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        print(f"FAIL: unsupported DATABASE_URL scheme: {parsed.scheme}")
        print(f"url: {safe_url(database_url)}")
        return 1

    connect_url = database_url
    if parsed.scheme == "postgres":
        connect_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif parsed.scheme == "postgresql":
        connect_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    print(f"url: {safe_url(database_url)}")
    print("engine: attempting connection")

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
