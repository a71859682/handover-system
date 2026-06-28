from __future__ import annotations

import argparse
import os

from psycopg import sql

from check_users_baseline_and_sequence import fetch_sequence_report
from check_users_secondary_update import connect_postgres, redact_database_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and optionally repair the PostgreSQL users.id sequence."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly run in dry-run mode. This is also the default when --apply is omitted.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the planned PostgreSQL sequence fix. Defaults to dry-run.",
    )
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run cannot be used together.")
    return args


def build_fix_plan(report: dict[str, object]) -> dict[str, object]:
    sequence_name = report["sequence_name"]
    max_user_id = report["max_user_id"]

    if sequence_name is None:
        return {
            "mode": "no-op",
            "reason": "sequence_not_found",
            "target_setval_value": None,
            "target_setval_is_called": None,
            "expected_next_insert_id": None,
            "needs_fix": False,
        }

    if max_user_id in (None, 0):
        return {
            "mode": "no-op",
            "reason": "users_table_empty",
            "target_setval_value": None,
            "target_setval_is_called": None,
            "expected_next_insert_id": report["next_insert_id"],
            "needs_fix": False,
        }

    target_setval_value = max_user_id
    target_setval_is_called = True
    expected_next_insert_id = max_user_id + report["increment_by"]
    needs_fix = report["next_insert_id"] <= max_user_id
    mode = "fix" if needs_fix else "no-op"
    reason = "next_insert_id_not_ahead_of_max_id" if needs_fix else "sequence_already_healthy"

    return {
        "mode": mode,
        "reason": reason,
        "target_setval_value": target_setval_value,
        "target_setval_is_called": target_setval_is_called,
        "expected_next_insert_id": expected_next_insert_id,
        "needs_fix": needs_fix,
    }


def print_current_state(report: dict[str, object]) -> None:
    print("Current sequence state:")
    print(f"- max_user_id: {report['max_user_id']}")
    print(f"- sequence_name: {report['sequence_name']!r}")
    print(f"- last_value: {report.get('last_value')}")
    print(f"- is_called: {report.get('is_called')}")
    print(f"- increment_by: {report.get('increment_by')}")
    print(f"- next_insert_id: {report.get('next_insert_id')}")


def print_planned_fix(plan: dict[str, object]) -> None:
    print("Planned fix:")
    print(f"- mode: {plan['mode']}")
    print(f"- reason: {plan['reason']}")
    print(f"- target_setval_value: {plan['target_setval_value']}")
    print(f"- target_setval_is_called: {plan['target_setval_is_called']}")
    print(f"- expected_next_insert_id: {plan['expected_next_insert_id']}")


def apply_fix(pg_conn, sequence_name: str, target_setval_value: int, target_setval_is_called: bool) -> None:
    query = sql.SQL("SELECT setval({}, %s, %s)").format(sql.Literal(sequence_name))
    with pg_conn.cursor() as cur:
        cur.execute(query, (target_setval_value, target_setval_is_called))
    pg_conn.commit()


def print_post_apply_report(report: dict[str, object]) -> bool:
    print("Post-apply sequence state:")
    print(f"- max_user_id: {report['max_user_id']}")
    print(f"- sequence_name: {report['sequence_name']!r}")
    print(f"- last_value: {report.get('last_value')}")
    print(f"- is_called: {report.get('is_called')}")
    print(f"- increment_by: {report.get('increment_by')}")
    print(f"- next_insert_id: {report.get('next_insert_id')}")
    print(f"- status: {report.get('status')}")
    print(f"- reason: {report.get('reason')}")
    return bool(report["next_insert_id"] > report["max_user_id"] and report["status"] == "ok")


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is not configured.")
        print("PASS")
        return 0

    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    with connect_postgres(database_url) as pg_conn:
        current_report = fetch_sequence_report(pg_conn)
        plan = build_fix_plan(current_report)

        print_current_state(current_report)
        print_planned_fix(plan)

        if not args.apply:
            if plan["needs_fix"]:
                print("DRY_RUN users.id sequence repair is required.")
                return 1
            print("DRY_RUN no-op: users.id sequence is already healthy.")
            print("PASS")
            return 0

        if not plan["needs_fix"]:
            print("APPLY no-op: users.id sequence is already healthy.")
            print("PASS")
            return 0

        if plan["target_setval_value"] is None or plan["target_setval_is_called"] is None:
            print("FAIL cannot apply sequence fix because no safe target_setval was planned.")
            return 1

        apply_fix(
            pg_conn,
            current_report["sequence_name"],
            int(plan["target_setval_value"]),
            bool(plan["target_setval_is_called"]),
        )
        post_apply_report = fetch_sequence_report(pg_conn)
        verified = print_post_apply_report(post_apply_report)
        if not verified:
            print("FAIL users.id sequence post-apply verification failed.")
            return 1

    print("PASS users.id sequence fix applied and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
