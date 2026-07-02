from __future__ import annotations

import hashlib
import os
import platform
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import DB_PATH  # noqa: E402
from sqlite_db_path import resolve_sqlite_db_path  # noqa: E402


def _fingerprint(value: str) -> str:
    if not value.strip():
        return ""
    digest = hashlib.sha256(value.strip().encode("utf-8")).hexdigest()
    return digest[:12]


def _normalize(value: str) -> str:
    return value.strip().lower()


def _storage_backend(database_url: str) -> str:
    if database_url.strip():
        return "database_url"
    return "sqlite"


def _branch_mapping(render_service_name: str, render_external_url: str) -> str:
    service_name = _normalize(render_service_name)
    external_url = _normalize(render_external_url)
    if "handover-system-dev" in service_name or "handover-system-dev.onrender.com" in external_url:
        return "develop"
    if "handover-system-staging" in service_name or "handover-system-staging.onrender.com" in external_url:
        return "staging"
    if service_name == "handover-system" or "handover-system.onrender.com" in external_url:
        return "main"
    return "unknown"


def collect_runtime_inventory(*, label: str) -> dict[str, Any]:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    render_service_name = os.environ.get("RENDER_SERVICE_NAME", "").strip()
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    app_env = os.environ.get("APP_ENV", "").strip()
    app_db_path = os.environ.get("APP_DB_PATH", "").strip()

    sqlite_resolution = resolve_sqlite_db_path(app_db_path or None)
    database_parts = urlsplit(database_url) if database_url else None

    database_scheme = database_parts.scheme if database_parts else ""
    database_host = database_parts.hostname if database_parts and database_parts.hostname else ""
    database_name = ""
    if database_parts and database_parts.path:
        database_name = database_parts.path.lstrip("/")

    runtime_summary = {
        "label": label,
        "app_env": app_env or "<unset>",
        "render_service_name": render_service_name or "<unset>",
        "render_external_url": render_external_url or "<unset>",
        "branch_mapping": _branch_mapping(render_service_name, render_external_url),
        "storage_backend": _storage_backend(database_url),
        "database_url_present": bool(database_url),
        "database_url_fingerprint": {
            "scheme": database_scheme or "<unset>",
            "host": _fingerprint(database_host) or "<unset>",
            "database": _fingerprint(database_name) or "<unset>",
        },
        "database_host_fingerprint": _fingerprint(database_host) or "<unset>",
        "database_name_fingerprint": _fingerprint(database_name) or "<unset>",
        "sqlite_db_path": str(DB_PATH),
        "sqlite_db_path_fingerprint": _fingerprint(str(DB_PATH)) or "<unset>",
        "sqlite_db_source": sqlite_resolution.source,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname_fingerprint": _fingerprint(socket.gethostname()) or "<unset>",
    }
    return runtime_summary


def json_ready_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": summary["label"],
        "app_env": summary["app_env"],
        "render_service_name": summary["render_service_name"],
        "render_external_url": summary["render_external_url"],
        "branch_mapping": summary["branch_mapping"],
        "storage_backend": summary["storage_backend"],
        "database_url_present": summary["database_url_present"],
        "database_url_fingerprint": summary["database_url_fingerprint"],
        "database_host_fingerprint": summary["database_host_fingerprint"],
        "database_name_fingerprint": summary["database_name_fingerprint"],
        "sqlite_db_path": summary["sqlite_db_path"],
        "sqlite_db_path_fingerprint": summary["sqlite_db_path_fingerprint"],
        "sqlite_db_source": summary["sqlite_db_source"],
        "python_version": summary["python_version"],
        "platform": summary["platform"],
        "hostname_fingerprint": summary["hostname_fingerprint"],
    }


def format_runtime_summary(summary: dict[str, Any]) -> list[str]:
    url_fingerprint = summary["database_url_fingerprint"]
    return [
        f"label: {summary['label']}",
        f"app_env: {summary['app_env']}",
        f"render_service_name: {summary['render_service_name']}",
        f"render_external_url: {summary['render_external_url']}",
        f"branch_mapping: {summary['branch_mapping']}",
        f"storage_backend: {summary['storage_backend']}",
        f"database_url_present: {str(summary['database_url_present']).lower()}",
        (
            "database_url_fingerprint: "
            f"scheme={url_fingerprint['scheme']} "
            f"host={url_fingerprint['host']} "
            f"database={url_fingerprint['database']}"
        ),
        f"database_host_fingerprint: {summary['database_host_fingerprint']}",
        f"database_name_fingerprint: {summary['database_name_fingerprint']}",
        f"sqlite_db_path: {summary['sqlite_db_path']}",
        f"sqlite_db_path_fingerprint: {summary['sqlite_db_path_fingerprint']}",
        f"sqlite_db_source: {summary['sqlite_db_source']}",
        f"python_version: {summary['python_version']}",
        f"platform: {summary['platform']}",
        f"hostname_fingerprint: {summary['hostname_fingerprint']}",
    ]


def build_diff_summary(current: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    diff_fields: list[dict[str, str]] = []
    for key in (
        "app_env",
        "render_service_name",
        "render_external_url",
        "branch_mapping",
        "storage_backend",
        "database_url_present",
        "database_host_fingerprint",
        "database_name_fingerprint",
        "sqlite_db_path_fingerprint",
        "sqlite_db_source",
        "python_version",
        "platform",
        "hostname_fingerprint",
    ):
        current_value = str(current.get(key, "<missing>"))
        other_value = str(other.get(key, "<missing>"))
        if current_value != other_value:
            diff_fields.append(
                {
                    "field": key,
                    "current": current_value,
                    "other": other_value,
                }
            )

    current_url_fingerprint = current.get("database_url_fingerprint", {})
    other_url_fingerprint = other.get("database_url_fingerprint", {})
    for key in ("scheme", "host", "database"):
        current_value = str(current_url_fingerprint.get(key, "<missing>"))
        other_value = str(other_url_fingerprint.get(key, "<missing>"))
        if current_value != other_value:
            diff_fields.append(
                {
                    "field": f"database_url_fingerprint.{key}",
                    "current": current_value,
                    "other": other_value,
                }
            )

    return {
        "current_label": current.get("label", "current"),
        "other_label": other.get("label", "other"),
        "diff_count": len(diff_fields),
        "diff_fields": diff_fields,
    }


def format_diff_summary(diff_summary: dict[str, Any]) -> list[str]:
    lines = [
        f"compare_current_label: {diff_summary['current_label']}",
        f"compare_other_label: {diff_summary['other_label']}",
        f"compare_diff_count: {diff_summary['diff_count']}",
    ]
    for item in diff_summary["diff_fields"]:
        lines.append(
            f"compare_diff: {item['field']} current={item['current']} other={item['other']}"
        )
    if not diff_summary["diff_fields"]:
        lines.append("compare_diff: none")
    return lines
