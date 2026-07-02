from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools._dev_vendor_authenticated import (
    STATUS_BLOCKED,
    STATUS_FAIL,
    STATUS_PASS,
    build_summary_payload,
    build_runtime_context,
    build_summary_phase_result,
    check_password_preflight,
    collect_preview_readiness_preflight,
    collect_runtime_preflight,
    format_output_lines,
    run_authentication_and_session_phases,
    run_authorization_phase,
    run_cleanup_phase,
    run_preview_contract_phase,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Dev-only authenticated vendor verification framework preflight."
    )
    parser.add_argument("--label", default="development", help="Runtime label for inventory collection.")
    parser.add_argument("--json", action="store_true", help="Print the fixed output structure as JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    runtime_details, runtime_result = collect_runtime_preflight(label=args.label)
    readiness_details, readiness_result = collect_preview_readiness_preflight()
    password_result = check_password_preflight()

    preflight_results = [runtime_result, readiness_result, password_result]
    runtime_context, bootstrap_results = build_runtime_context(preflight_results)
    authentication_session_results = run_authentication_and_session_phases(
        runtime_context,
        prerequisite_results=bootstrap_results,
    )
    authorization_results = run_authorization_phase(
        runtime_context,
        authentication_session_results=authentication_session_results,
    )
    preview_contract_results = run_preview_contract_phase(
        runtime_context,
        authorization_results=authorization_results,
    )
    cleanup_results = run_cleanup_phase(
        runtime_context,
        preview_contract_results=preview_contract_results,
    )
    non_summary_verification_results = [
        *authentication_session_results,
        *authorization_results,
        *preview_contract_results,
        *cleanup_results,
    ]
    summary_result = build_summary_phase_result([*preflight_results, *non_summary_verification_results])
    verification_results = [
        *non_summary_verification_results,
        summary_result,
    ]
    payload = build_summary_payload(
        runtime_details,
        readiness_details,
        [*preflight_results, *verification_results],
    )

    for line in format_output_lines(payload):
        print(line)

    if args.json:
        print()
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))

    if payload["overall_status"] == STATUS_FAIL:
        return 1
    if payload["overall_status"] == STATUS_BLOCKED:
        return 2
    if payload["overall_status"] == STATUS_PASS:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
