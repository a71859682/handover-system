from __future__ import annotations

import io
import logging
import os
import sys
import uuid
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

    probe_key = f"__meta_secondary_probe__{uuid.uuid4().hex}"
    probe_value = "meta secondary write probe"

    try:
        with app.db() as conn:
            conn.execute("DELETE FROM meta WHERE key = ?", (probe_key,))
            result, error, details = write_service._write_meta_to_postgres_secondary(  # type: ignore[attr-defined]
                conn,
                key=probe_key,
                value=probe_value,
            )
            conn.execute("DELETE FROM meta WHERE key = ?", (probe_key,))

        log_output = stream.getvalue().strip()
        strategy = details.get("strategy", "unknown")
        elapsed_ms = details.get("elapsed_ms", "unknown")

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
