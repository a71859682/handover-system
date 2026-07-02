from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import DB_PATH  # noqa: E402
from sqlite_db_path import resolve_sqlite_db_path  # noqa: E402


PREVIEW_USERNAME = "vendor_preview_dev"
PREVIEW_VENDOR_NAME = "Vendor Preview Dev"
EMPTY_USERNAME = "vendor_empty_dev"
EMPTY_VENDOR_NAME = "Vendor Empty Dev"
EXPECTED_PREVIEW_ENTRY_COUNT = 3

SAFE_ENV_NAMES = {"dev", "development", "local", "test", "testing"}
UNSAFE_ENV_NAMES = {"prod", "production", "staging"}
SAFE_TARGET_MARKERS = ("dev", "development", "local", "test", "testing")
UNSAFE_TARGET_MARKERS = ("prod", "production", "staging")
ALLOW_OVERRIDE_ENV = "DEV_VENDOR_PREVIEW_ALLOWED"


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").lower()


def _target_markers_from_env() -> dict[str, str]:
    app_env = os.environ.get("APP_ENV", "").strip()
    app_db_path = os.environ.get("APP_DB_PATH", "").strip()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    render_service_name = os.environ.get("RENDER_SERVICE_NAME", "").strip()
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    resolution = resolve_sqlite_db_path(app_db_path or None)
    return {
        "app_env": app_env,
        "app_db_path": app_db_path,
        "database_url_set": str(bool(database_url)).lower(),
        "render_service_name": render_service_name,
        "render_external_url": render_external_url,
        "sqlite_db_path": str(DB_PATH),
        "sqlite_db_source": resolution.source,
    }


def _signal_from_text(value: str, *, markers: tuple[str, ...]) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in markers)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _database_fingerprint(database_url: str) -> str:
    if not database_url.strip():
        return ""
    parts = urlsplit(database_url)
    return " ".join(
        part
        for part in (
            parts.scheme or "",
            parts.hostname or "",
            parts.path or "",
            parts.username or "",
        )
        if part
    ).lower()


def is_safe_target() -> tuple[bool, list[str], list[str], str | None, str | None]:
    markers = _target_markers_from_env()
    safe_signals: list[str] = []
    unsafe_signals: list[str] = []
    hard_deny_reason: str | None = None
    ambiguous_reason: str | None = None

    app_env = markers["app_env"].strip().lower()
    if app_env in SAFE_ENV_NAMES:
        safe_signals.append(f"app_env={app_env}")
    elif app_env in UNSAFE_ENV_NAMES:
        unsafe_signals.append(f"app_env={app_env}")
        hard_deny_reason = f"app_env={app_env}"

    sqlite_db_path = markers["sqlite_db_path"]
    normalized_db_path = _normalize_path(sqlite_db_path)
    if _signal_from_text(normalized_db_path, markers=SAFE_TARGET_MARKERS):
        safe_signals.append(f"sqlite_db_path={sqlite_db_path}")
    elif _signal_from_text(normalized_db_path, markers=UNSAFE_TARGET_MARKERS):
        unsafe_signals.append(f"sqlite_db_path={sqlite_db_path}")

    if _normalize_path(sqlite_db_path) == _normalize_path(str(ROOT_DIR / "site.db")):
        safe_signals.append("sqlite_db_path=project_default_site_db")

    for key in ("render_service_name", "render_external_url"):
        value = markers[key]
        if not value:
            continue
        if _signal_from_text(value, markers=SAFE_TARGET_MARKERS):
            safe_signals.append(f"{key}={value}")
        elif _signal_from_text(value, markers=UNSAFE_TARGET_MARKERS):
            unsafe_signals.append(f"{key}={value}")
            hard_deny_reason = f"{key}={value}"

    database_url = os.environ.get("DATABASE_URL", "").strip()
    fingerprint = _database_fingerprint(database_url)
    if fingerprint:
        if _signal_from_text(fingerprint, markers=SAFE_TARGET_MARKERS):
            safe_signals.append("database_fingerprint=dev_like")
        elif _signal_from_text(fingerprint, markers=UNSAFE_TARGET_MARKERS):
            unsafe_signals.append("database_fingerprint=prod_like")
            hard_deny_reason = "database_fingerprint=prod_like"

    if hard_deny_reason is not None:
        return False, safe_signals, unsafe_signals, hard_deny_reason, None

    if len(safe_signals) >= 2:
        return True, safe_signals, unsafe_signals, None, None

    if _env_flag(ALLOW_OVERRIDE_ENV):
        safe_signals.append(f"{ALLOW_OVERRIDE_ENV}=true")
        ambiguous_reason = "allow_override_used"
        return True, safe_signals, unsafe_signals, None, ambiguous_reason

    ambiguous_reason = "insufficient_dev_fingerprint"
    return False, safe_signals, unsafe_signals, None, ambiguous_reason


def describe_target() -> dict[str, Any]:
    safe_target, safe_signals, unsafe_signals, hard_deny_reason, ambiguous_reason = is_safe_target()
    markers = _target_markers_from_env()
    return {
        "safe_target": safe_target,
        "safe_signals": tuple(safe_signals),
        "unsafe_signals": tuple(unsafe_signals),
        "hard_deny_reason": hard_deny_reason,
        "ambiguous_reason": ambiguous_reason,
        "app_env": markers["app_env"] or "<unset>",
        "app_db_path": markers["app_db_path"] or "<unset>",
        "database_url_set": markers["database_url_set"],
        "render_service_name": markers["render_service_name"] or "<unset>",
        "render_external_url": markers["render_external_url"] or "<unset>",
        "sqlite_db_path": markers["sqlite_db_path"],
        "sqlite_db_source": markers["sqlite_db_source"],
    }


def _fetch_vendor_rows(conn: sqlite3.Connection, *, username: str, vendor_name: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, username, vendor_name, is_active, created_at, updated_at
        FROM vendor_accounts
        WHERE username = ? OR vendor_name = ?
        ORDER BY id
        """,
        (username, vendor_name),
    ).fetchall()
    return [dict(row) for row in rows]


def select_safe_sheet(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT s.id, s.name, s.site_id, COUNT(vwe.id) AS existing_vendor_entry_count
        FROM sheets s
        LEFT JOIN vendor_work_entries vwe ON vwe.sheet_id = s.id
        GROUP BY s.id, s.name, s.site_id
        ORDER BY existing_vendor_entry_count DESC, s.id ASC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row is not None else None


def collect_dev_vendor_preview_inventory(conn: sqlite3.Connection) -> dict[str, Any]:
    preview_vendor_rows = _fetch_vendor_rows(
        conn,
        username=PREVIEW_USERNAME,
        vendor_name=PREVIEW_VENDOR_NAME,
    )
    empty_vendor_rows = _fetch_vendor_rows(
        conn,
        username=EMPTY_USERNAME,
        vendor_name=EMPTY_VENDOR_NAME,
    )
    preview_entry_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM vendor_work_entries WHERE vendor_name = ?",
            (PREVIEW_VENDOR_NAME,),
        ).fetchone()[0]
    )
    empty_entry_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM vendor_work_entries WHERE vendor_name = ?",
            (EMPTY_VENDOR_NAME,),
        ).fetchone()[0]
    )
    return {
        "target": describe_target(),
        "preview_vendor_rows": preview_vendor_rows,
        "empty_vendor_rows": empty_vendor_rows,
        "preview_entry_count": preview_entry_count,
        "empty_entry_count": empty_entry_count,
        "safe_sheet": select_safe_sheet(conn),
    }


def _summarize_vendor_rows(
    rows: list[dict[str, Any]],
    *,
    expected_username: str,
    expected_vendor_name: str,
) -> dict[str, Any]:
    exact_matches = [
        row
        for row in rows
        if row["username"] == expected_username and row["vendor_name"] == expected_vendor_name
    ]
    active_exact_matches = [row for row in exact_matches if int(row["is_active"] or 0) == 1]
    return {
        "rows": rows,
        "exact_match_count": len(exact_matches),
        "active_exact_match_count": len(active_exact_matches),
        "ready": len(active_exact_matches) == 1 and len(rows) == 1,
        "missing": len(rows) == 0,
        "conflict": not (len(active_exact_matches) == 1 and len(rows) == 1) and len(rows) > 0,
        "row": active_exact_matches[0] if len(active_exact_matches) == 1 and len(rows) == 1 else None,
    }


def build_status_summary(inventory: dict[str, Any]) -> dict[str, Any]:
    preview_vendor = _summarize_vendor_rows(
        inventory["preview_vendor_rows"],
        expected_username=PREVIEW_USERNAME,
        expected_vendor_name=PREVIEW_VENDOR_NAME,
    )
    empty_vendor = _summarize_vendor_rows(
        inventory["empty_vendor_rows"],
        expected_username=EMPTY_USERNAME,
        expected_vendor_name=EMPTY_VENDOR_NAME,
    )
    preview_entry_count = int(inventory["preview_entry_count"])
    empty_entry_count = int(inventory["empty_entry_count"])
    safe_sheet = inventory["safe_sheet"]
    target = inventory["target"]

    preview_entries = {
        "count": preview_entry_count,
        "ready": preview_entry_count == EXPECTED_PREVIEW_ENTRY_COUNT,
        "missing": preview_entry_count == 0,
        "conflict": preview_entry_count not in {0, EXPECTED_PREVIEW_ENTRY_COUNT},
    }
    empty_entries = {
        "count": empty_entry_count,
        "ready": empty_entry_count == 0,
        "missing": empty_entry_count == 0,
        "conflict": empty_entry_count != 0,
    }
    safe_sheet_summary = {
        "ready": safe_sheet is not None,
        "sheet": safe_sheet,
    }

    return {
        "target": target,
        "preview_vendor": preview_vendor,
        "empty_vendor": empty_vendor,
        "preview_entries": preview_entries,
        "empty_entries": empty_entries,
        "safe_sheet": safe_sheet_summary,
    }


def is_ready_for_authenticated_verification(summary: dict[str, Any]) -> bool:
    return all(
        (
            bool(summary["target"]["safe_target"]),
            bool(summary["preview_vendor"]["ready"]),
            bool(summary["empty_vendor"]["ready"]),
            bool(summary["preview_entries"]["ready"]),
            bool(summary["empty_entries"]["ready"]),
            bool(summary["safe_sheet"]["ready"]),
        )
    )


def format_status_lines(summary: dict[str, Any]) -> list[str]:
    target = summary["target"]
    safe_signals = ", ".join(target["safe_signals"]) if target["safe_signals"] else "none"
    unsafe_signals = ", ".join(target["unsafe_signals"]) if target["unsafe_signals"] else "none"
    hard_deny_reason = target["hard_deny_reason"] or "none"
    ambiguous_reason = target["ambiguous_reason"] or "none"
    safe_sheet = summary["safe_sheet"]["sheet"]
    safe_sheet_label = (
        f"id={safe_sheet['id']} name={safe_sheet['name']} existing_vendor_entry_count={safe_sheet['existing_vendor_entry_count']}"
        if safe_sheet is not None
        else "missing"
    )

    return [
        f"target_safe: {str(bool(target['safe_target'])).lower()}",
        f"target_app_env: {target['app_env']}",
        f"target_app_db_path: {target['app_db_path']}",
        f"target_database_url_set: {target['database_url_set']}",
        f"target_render_service_name: {target['render_service_name']}",
        f"target_render_external_url: {target['render_external_url']}",
        f"target_sqlite_db_path: {target['sqlite_db_path']}",
        f"target_sqlite_db_source: {target['sqlite_db_source']}",
        f"target_safe_signals: {safe_signals}",
        f"target_unsafe_signals: {unsafe_signals}",
        f"target_hard_deny_reason: {hard_deny_reason}",
        f"target_ambiguous_reason: {ambiguous_reason}",
        f"preview_vendor_ready: {str(bool(summary['preview_vendor']['ready'])).lower()}",
        f"preview_vendor_missing: {str(bool(summary['preview_vendor']['missing'])).lower()}",
        f"preview_vendor_conflict: {str(bool(summary['preview_vendor']['conflict'])).lower()}",
        f"preview_vendor_row_count: {len(summary['preview_vendor']['rows'])}",
        f"empty_vendor_ready: {str(bool(summary['empty_vendor']['ready'])).lower()}",
        f"empty_vendor_missing: {str(bool(summary['empty_vendor']['missing'])).lower()}",
        f"empty_vendor_conflict: {str(bool(summary['empty_vendor']['conflict'])).lower()}",
        f"empty_vendor_row_count: {len(summary['empty_vendor']['rows'])}",
        f"preview_entries_count: {summary['preview_entries']['count']}",
        f"preview_entries_ready: {str(bool(summary['preview_entries']['ready'])).lower()}",
        f"preview_entries_missing: {str(bool(summary['preview_entries']['missing'])).lower()}",
        f"preview_entries_conflict: {str(bool(summary['preview_entries']['conflict'])).lower()}",
        f"empty_entries_count: {summary['empty_entries']['count']}",
        f"empty_entries_ready: {str(bool(summary['empty_entries']['ready'])).lower()}",
        f"empty_entries_conflict: {str(bool(summary['empty_entries']['conflict'])).lower()}",
        f"safe_sheet_ready: {str(bool(summary['safe_sheet']['ready'])).lower()}",
        f"safe_sheet: {safe_sheet_label}",
        f"ready_for_authenticated_verification: {str(is_ready_for_authenticated_verification(summary)).lower()}",
    ]
