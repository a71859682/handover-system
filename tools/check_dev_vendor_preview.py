from __future__ import annotations

import argparse
import json
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
    evaluate_preview_check,
    EXIT_BLOCKED,
    EXIT_FAIL,
    EXIT_PASS,
    format_status_lines,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Dev vendor preview test data readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    args = parser.parse_args()

    with db() as conn:
        conn.row_factory = sqlite3.Row
        inventory = collect_dev_vendor_preview_inventory(conn)

    summary = build_status_summary(inventory)
    status_info = evaluate_preview_check(summary)

    print("Status:")
    print(status_info["overall_status"])
    print("Reason:")
    print(status_info["overall_reason"])
    print("Target:")
    print(status_info["target"])
    print("dev_vendor_preview_check_scope: read_only")
    for explain_line in status_info["status_explainability"]:
        print(f"status_note: {explain_line}")
    for line in format_status_lines(summary):
        print(line)

    payload = {
        "overall_status": status_info["overall_status"],
        "overall_reason": status_info["overall_reason"],
        "target": status_info["target"],
        "status_explainability": status_info["status_explainability"],
        "summary": summary,
    }

    if args.json:
        print()
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))

    print(f"{status_info['overall_status']} dev vendor preview check {status_info['overall_reason']}.")
    if status_info["exit_code"] == EXIT_PASS:
        return EXIT_PASS
    if status_info["exit_code"] == EXIT_FAIL:
        return EXIT_FAIL
    if status_info["exit_code"] == EXIT_BLOCKED:
        return EXIT_BLOCKED
    return EXIT_BLOCKED


if __name__ == "__main__":
    raise SystemExit(main())
