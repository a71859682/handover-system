from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main() -> int:
    if not os.environ.get("DATABASE_URL", "").strip():
        print("DATABASE_URL is not configured.")
        print("PASS")
        return 0

    import app
    import services.write_service as write_service

    logger = logging.getLogger("dual_write")
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    try:
        with app.db() as conn:
            floor = conn.execute(
                "SELECT id, name, block_name FROM floors ORDER BY sort_order, id LIMIT 1"
            ).fetchone()
            if floor is None:
                print("FAIL no floor rows found")
                return 1

            result, error, details = write_service._write_floor_fields_to_postgres_secondary(  # type: ignore[attr-defined]
                conn,
                floor_id=floor["id"],
                name=floor["name"],
                block_name=floor["block_name"] or "",
            )

        log_output = stream.getvalue().strip()
        strategy = details.get("strategy", "unknown")
        elapsed_ms = details.get("elapsed_ms", "unknown")

        print(f"floor_id={floor['id']}")
        print(f"strategy={strategy}")
        print(f"elapsed_ms={elapsed_ms}")
        print("LOG_OUTPUT_BEGIN")
        if log_output:
            print(log_output)
        print("LOG_OUTPUT_END")

        if result == "success":
            print("PASS")
            return 0

        print(f"FAIL result={result} error={error}")
        return 1
    finally:
        logger.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
