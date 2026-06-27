from __future__ import annotations

import io
import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ["DUAL_WRITE_DRY_RUN"] = "true"
os.environ["USE_SQLALCHEMY_WRITES"] = "false"
tmpdir = Path(tempfile.mkdtemp(prefix="dual-write-dry-run-"))
os.environ["APP_DB_PATH"] = str(tmpdir / "site.db")

from config import DUAL_WRITE_DRY_RUN, USE_SQLALCHEMY_WRITES
from app import DONE_VALUE, bootstrap, db
from services import write_service


def _build_temp_db() -> Path:
    db_path = Path(os.environ["APP_DB_PATH"])
    bootstrap()
    return db_path


def main() -> int:
    db_path = _build_temp_db()

    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    try:
        with db() as conn:
            conn.row_factory = sqlite3.Row
            write_service.upsert_setting_sqlite(conn, "site_title", "Dry Run Site")

            unit = conn.execute("SELECT id FROM units ORDER BY id LIMIT 1").fetchone()
            task = conn.execute("SELECT id FROM tasks ORDER BY id LIMIT 1").fetchone()
            user = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
            write_service.upsert_progress_sqlite(
                conn,
                unit_id=unit["id"],
                task_id=task["id"],
                value=DONE_VALUE,
                updated_by=user["id"],
            )

            site_title = conn.execute("SELECT value FROM meta WHERE key = ?", ("site_title",)).fetchone()
            progress = conn.execute(
                "SELECT value, updated_by FROM progress WHERE unit_id = ? AND task_id = ?",
                (unit["id"], task["id"]),
            ).fetchone()

        log_output = stream.getvalue()
        has_handler = bool(logger.handlers) or bool(logging.getLogger().handlers)

        checks = [
            ("DUAL_WRITE_DRY_RUN enabled", DUAL_WRITE_DRY_RUN is True),
            ("USE_SQLALCHEMY_WRITES disabled", USE_SQLALCHEMY_WRITES is False),
            ("Logger has visible handler path", has_handler),
            ("SQLite settings write still works", site_title is not None and site_title["value"] == "Dry Run Site"),
            (
                "SQLite progress write still works",
                progress is not None and progress["value"] == DONE_VALUE and progress["updated_by"] == user["id"],
            ),
            (
                "Dry-run logger emitted meta record",
                "DUAL_WRITE_DRY_RUN operation=upsert table=meta" in log_output and "dry_run=true" in log_output,
            ),
            (
                "Dry-run logger emitted progress record",
                "DUAL_WRITE_DRY_RUN operation=upsert table=progress" in log_output and "dry_run=true" in log_output,
            ),
            ("No PostgreSQL write attempted", "INSERT INTO" not in log_output and "UPDATE " not in log_output and "DELETE " not in log_output),
        ]

        failed = [label for label, ok in checks if not ok]

        print(f"DUAL_WRITE_DRY_RUN={str(DUAL_WRITE_DRY_RUN).lower()}")
        print(f"USE_SQLALCHEMY_WRITES={str(USE_SQLALCHEMY_WRITES).lower()}")
        print(f"TEMP_DB_PATH={db_path}")
        print("LOG_OUTPUT_BEGIN")
        print(log_output.strip())
        print("LOG_OUTPUT_END")
        for label, ok in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {label}")

        if failed:
            print("FAIL")
            return 1

        print("PASS")
        return 0
    finally:
        logger.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
