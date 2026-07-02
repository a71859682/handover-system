from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools._runtime_inventory import (  # noqa: E402
    build_diff_summary,
    collect_runtime_inventory,
    format_diff_summary,
    format_runtime_summary,
    json_ready_summary,
)


def _load_compare_file(path: str) -> dict[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only runtime inventory metadata.")
    parser.add_argument("--label", default="runtime", help="Human-readable label for this runtime summary.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary instead of text output.")
    parser.add_argument(
        "--compare",
        metavar="PATH",
        help="Compare the current runtime summary against a saved JSON summary file.",
    )
    args = parser.parse_args()

    summary = collect_runtime_inventory(label=args.label)
    json_summary = json_ready_summary(summary)

    if args.compare:
        other_summary = _load_compare_file(args.compare)
        diff_summary = build_diff_summary(json_summary, other_summary)
        if args.json:
            print(
                json.dumps(
                    {
                        "summary": json_summary,
                        "compare": diff_summary,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        print("runtime_inventory_scope: read_only")
        for line in format_runtime_summary(summary):
            print(line)
        for line in format_diff_summary(diff_summary):
            print(line)
        return 0

    if args.json:
        print(json.dumps(json_summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print("runtime_inventory_scope: read_only")
    for line in format_runtime_summary(summary):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
