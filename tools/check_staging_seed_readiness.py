from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SEED_SCRIPT_PATH = ROOT_DIR / "tools" / "seed_staging_release_verification.py"


@dataclass(frozen=True)
class Expectation:
    label: str
    markers: tuple[str, ...]


EXPECTATIONS: tuple[Expectation, ...] = (
    Expectation(
        label="staging_guard",
        markers=(
            'APP_ENV',
            'STAGING_SEED_ALLOWED',
            'Refusing to run seed script outside staging guard.',
        ),
    ),
    Expectation(
        label="database_redaction",
        markers=(
            'redact_database_url',
            'target_database_url:',
            'require_postgres_database_url',
        ),
    ),
    Expectation(
        label="dry_run_support",
        markers=(
            '--dry-run',
            "PASS staging release seed dry-run passed.",
            'dry_run_execution: offline_preview_only',
        ),
    ),
    Expectation(
        label="clear_and_reseed_support",
        markers=(
            '--clear-and-reseed',
            'delete_managed_rows(conn)',
        ),
    ),
    Expectation(
        label="managed_sites_and_sheets",
        markers=(
            'SITE_A_NAME = "staging_release_site_a"',
            'SITE_B_NAME = "staging_release_site_b"',
            'SHEET_A_NAME = "staging_release_sheet_a"',
            'SHEET_B_NAME = "staging_release_sheet_b"',
        ),
    ),
    Expectation(
        label="managed_users",
        markers=(
            'ADMIN_USERNAME = "admin_staging"',
            'SINGLE_SITE_USERNAME = "single_site_user_staging"',
            'MULTI_SITE_USERNAME = "multi_site_user_staging"',
            'ZERO_SITE_USERNAME = "zero_site_user_staging"',
            'PERMISSION_REMOVED_USERNAME = "permission_removed_user_staging"',
        ),
    ),
    Expectation(
        label="managed_data",
        markers=(
            'vendor_contacts',
            'vendor_work_entries',
            'ensure_progress(',
            'ensure_unit_extra_value(',
            'ensure_permission(',
        ),
    ),
    Expectation(
        label="summary_counts",
        markers=(
            'PLANNED_SUMMARY_COUNTS = {',
            'print_summary("planned_summary", PLANNED_SUMMARY_COUNTS)',
            'print_summary("summary", summary)',
        ),
    ),
)


def expect(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check staging release seed tooling readiness.")
    parser.parse_args()

    print("staging_seed_readiness_scope: tooling_only")
    print(f"seed_script_path: {SEED_SCRIPT_PATH}")

    issues: list[str] = []
    expect(SEED_SCRIPT_PATH.exists(), "seed_script_missing", issues)

    source = SEED_SCRIPT_PATH.read_text(encoding="utf-8") if SEED_SCRIPT_PATH.exists() else ""

    for expectation in EXPECTATIONS:
        missing = [marker for marker in expectation.markers if marker not in source]
        print("---")
        print(f"check: {expectation.label}")
        print(f"missing_markers: {len(missing)}")
        if missing:
            for marker in missing:
                print(f"missing: {marker}")
            issues.append(f"missing_markers:{expectation.label}")

    print("---")
    print("expected_execution:")
    print("- dry-run requires APP_ENV=staging or STAGING_SEED_ALLOWED=true")
    print("- DATABASE_URL must be PostgreSQL and look like a staging target")
    print("- script prints a redacted target_database_url")
    print("- dry-run is offline preview only and does not mutate the target DB")
    print("- script supports idempotent apply and --clear-and-reseed")
    print("- script seeds site A / site B, sheet A / sheet B, staging users, permissions, tasks, floors, units, extra fields, progress, unit_extra, vendor_contacts, vendor_work_entries")

    print(f"issues_count: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"ISSUE {issue}")
        raise SystemExit("FAIL staging seed readiness check failed.")

    print("PASS staging seed readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
