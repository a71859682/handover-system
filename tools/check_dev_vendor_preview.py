from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import db  # noqa: E402
from tools._dev_vendor_preview import (  # noqa: E402
    build_status_summary,
    collect_dev_vendor_preview_inventory,
    format_status_lines,
    is_ready_for_authenticated_verification,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Dev vendor preview test data readiness.")
    parser.parse_args()

    print("dev_vendor_preview_check_scope: read_only")
    with db() as conn:
        conn.row_factory = sqlite3.Row
        inventory = collect_dev_vendor_preview_inventory(conn)

    summary = build_status_summary(inventory)
    for line in format_status_lines(summary):
        print(line)

    if is_ready_for_authenticated_verification(summary):
        print("PASS dev vendor preview check passed.")
        return 0

    print("FAIL dev vendor preview check failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
