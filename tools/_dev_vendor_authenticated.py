from __future__ import annotations

import os
import sqlite3
import sys
from importlib import util
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import db  # noqa: E402
from tools._dev_vendor_preview import (  # noqa: E402
    build_status_summary,
    collect_dev_vendor_preview_inventory,
    describe_target,
    is_ready_for_authenticated_verification,
)


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"
SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_ERROR = "ERROR"
PASSWORD_ENV = "DEV_VENDOR_PREVIEW_PASSWORD"

PHASE_PREFLIGHT = "Preflight"
PHASE_AUTHENTICATION = "Authentication"
PHASE_SESSION = "Session"
PHASE_AUTHORIZATION = "Authorization"
PHASE_PREVIEW_CONTRACT = "Preview Contract"
PHASE_CLEANUP = "Cleanup"
PHASE_SUMMARY = "Summary"


@dataclass
class VerificationResult:
    name: str
    phase: str
    status: str
    severity: str
    reason: str
    explainability: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pass_result(
    name: str,
    *,
    phase: str,
    reason: str,
    explainability: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> VerificationResult:
    return VerificationResult(
        name=name,
        phase=phase,
        status=STATUS_PASS,
        severity=SEVERITY_INFO,
        reason=reason,
        explainability=explainability or [],
        details=details or {},
    )


def blocked_result(
    name: str,
    *,
    phase: str,
    reason: str,
    explainability: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> VerificationResult:
    return VerificationResult(
        name=name,
        phase=phase,
        status=STATUS_BLOCKED,
        severity=SEVERITY_INFO,
        reason=reason,
        explainability=explainability or [],
        details=details or {},
    )


def fail_result(
    name: str,
    *,
    phase: str,
    reason: str,
    explainability: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> VerificationResult:
    return VerificationResult(
        name=name,
        phase=phase,
        status=STATUS_FAIL,
        severity=SEVERITY_ERROR,
        reason=reason,
        explainability=explainability or [],
        details=details or {},
    )


def collect_runtime_preflight(*, label: str = "development") -> tuple[dict[str, Any], VerificationResult]:
    target = describe_target()
    explainability = [
        f"label={label}",
        f"safe_target={str(bool(target['safe_target'])).lower()}",
        f"app_env={target['app_env']}",
        f"render_service_name={target['render_service_name']}",
        f"render_external_url={target['render_external_url']}",
    ]
    details = {
        "label": label,
        "target": target,
    }
    if bool(target["safe_target"]):
        return details, pass_result(
            "runtime_inventory",
            phase=PHASE_PREFLIGHT,
            reason="runtime_dev_identity_confirmed",
            explainability=explainability,
            details=details,
        )
    return details, blocked_result(
        "runtime_inventory",
        phase=PHASE_PREFLIGHT,
        reason="runtime_not_development_like",
        explainability=explainability,
        details=details,
    )


def collect_preview_readiness_preflight() -> tuple[dict[str, Any], VerificationResult]:
    with db() as conn:
        conn.row_factory = sqlite3.Row
        inventory = collect_dev_vendor_preview_inventory(conn)

    summary = build_status_summary(inventory)
    details = {"summary": summary}
    if is_ready_for_authenticated_verification(summary):
        return details, pass_result(
            "dev_vendor_preview_readiness",
            phase=PHASE_PREFLIGHT,
            reason="preview_readiness_confirmed",
            explainability=["shared _dev_vendor_preview.py helper reports readiness PASS"],
            details=details,
        )
    return details, blocked_result(
        "dev_vendor_preview_readiness",
        phase=PHASE_PREFLIGHT,
        reason="preview_readiness_not_ready",
        explainability=["shared _dev_vendor_preview.py helper reports readiness not ready"],
        details=details,
    )


def check_password_preflight() -> VerificationResult:
    available = bool(os.environ.get(PASSWORD_ENV, "").strip())
    if available:
        return pass_result(
            "dev_vendor_password",
            phase=PHASE_PREFLIGHT,
            reason="password_env_present",
            explainability=[f"{PASSWORD_ENV}=present"],
            details={"password_available": True},
        )
    return blocked_result(
        "dev_vendor_password",
        phase=PHASE_PREFLIGHT,
        reason="password_env_missing",
        explainability=[f"{PASSWORD_ENV}=missing"],
        details={"password_available": False},
    )


def _preflight_passed(results: list[VerificationResult]) -> bool:
    return all(result.status == STATUS_PASS for result in results)


def _load_app_module():
    app_path = ROOT_DIR / "app.py"
    spec = util.spec_from_file_location("stage4b_app_under_test", app_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load app module from {app_path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _session_snapshot(client) -> dict[str, Any]:
    with client.session_transaction() as sess:
        return dict(sess)


def _extract_location(response) -> str:
    return response.headers.get("Location", "")


def _is_login_redirect(response, *, expected_fragment: str) -> bool:
    location = _extract_location(response)
    return response.status_code in {301, 302, 303, 307, 308} and expected_fragment in location


def _set_internal_session(
    client,
    *,
    user_id: int = 1,
    username: str = "internal_member",
    role: str = "member",
    current_site_id: int = 1,
    current_site_name: str = "Internal Current Site",
) -> None:
    with client.session_transaction() as sess:
        sess.clear()
        sess["user_id"] = user_id
        sess["username"] = username
        sess["display_name"] = username
        sess["role"] = role
        sess["current_site_id"] = current_site_id
        sess["current_site_name"] = current_site_name
        sess["site_selection_required"] = False


def _has_vendor_contract_keys(session_data: dict[str, Any]) -> bool:
    return (
        session_data.get("identity_type") == "vendor"
        and bool(session_data.get("vendor_account_id"))
        and bool(session_data.get("vendor_username"))
        and bool(session_data.get("vendor_name"))
    )


def _forbidden_internal_session_keys(session_data: dict[str, Any]) -> list[str]:
    return [key for key in ("user_id", "role", "display_name") if key in session_data]


def _authentication_phase_passed(results: list[VerificationResult]) -> bool:
    return all(
        result.status == STATUS_PASS for result in results if result.phase == PHASE_AUTHENTICATION
    )


def _session_phase_passed(results: list[VerificationResult]) -> bool:
    return all(result.status == STATUS_PASS for result in results if result.phase == PHASE_SESSION)


def _authorization_phase_passed(results: list[VerificationResult]) -> bool:
    return all(
        result.status == STATUS_PASS for result in results if result.phase == PHASE_AUTHORIZATION
    )


def _sorted_unique_business_dates(entries: list[dict[str, Any]]) -> list[str]:
    return sorted({entry.get("business_date", "") for entry in entries if entry.get("business_date", "")}, reverse=True)


def _entry_contract_keys() -> set[str]:
    return {
        "vendor_name",
        "business_date",
        "planned_at",
        "planned_headcount",
        "actual_headcount",
        "work_content",
        "work_headcount",
        "entry_order",
    }


def build_runtime_context(preflight_results: list[VerificationResult]) -> tuple[dict[str, Any] | None, list[VerificationResult]]:
    auth_names = [
        ("vendor_login_page", PHASE_AUTHENTICATION),
        ("vendor_preview_login", PHASE_AUTHENTICATION),
        ("vendor_wrong_password", PHASE_AUTHENTICATION),
        ("vendor_empty_login", PHASE_AUTHENTICATION),
        ("preview_vendor_session_contract", PHASE_SESSION),
        ("empty_vendor_session_contract", PHASE_SESSION),
    ]
    if not _preflight_passed(preflight_results):
        reason = "preflight_not_satisfied"
        explainability = ["Authentication and Session phases are skipped until all preflight checks PASS."]
        return None, [
            blocked_result(name, phase=phase, reason=reason, explainability=explainability)
            for name, phase in auth_names
        ]

    try:
        module = _load_app_module()
    except Exception as exc:  # pragma: no cover - defensive path
        explainability = [f"app_import_error={exc!r}"]
        return None, [
            fail_result(name, phase=phase, reason="app_import_failed", explainability=explainability)
            for name, phase in auth_names
        ]

    app = module.app
    route_rules = {str(rule) for rule in app.url_map.iter_rules()}
    required_routes = {"/vendor/login", "/vendor/logout"}
    missing_routes = sorted(required_routes - route_rules)
    if missing_routes:
        explainability = [f"missing_routes={', '.join(missing_routes)}"]
        return None, [
            fail_result(
                name,
                phase=phase,
                reason="vendor_runtime_contract_missing",
                explainability=explainability,
                details={"missing_routes": missing_routes},
            )
            for name, phase in auth_names
        ]

    password = os.environ.get(PASSWORD_ENV, "").strip()
    return {
        "app": app,
        "password": password,
        "preview_username": "vendor_preview_dev",
        "empty_username": "vendor_empty_dev",
        "wrong_password": f"{password}-wrong",
    }, []


def run_authentication_and_session_phases(
    runtime_context: dict[str, Any] | None,
    *,
    prerequisite_results: list[VerificationResult],
) -> list[VerificationResult]:
    auth_names = [
        "vendor_login_page",
        "vendor_preview_login",
        "vendor_wrong_password",
        "vendor_empty_login",
    ]
    session_names = [
        "preview_vendor_session_contract",
        "empty_vendor_session_contract",
    ]
    if runtime_context is None:
        if prerequisite_results:
            return prerequisite_results
        reason = "runtime_context_missing"
        explainability = ["Runtime context is unavailable."]
        return (
            [
                blocked_result(name, phase=PHASE_AUTHENTICATION, reason=reason, explainability=explainability)
                for name in auth_names
            ]
            + [
                blocked_result(name, phase=PHASE_SESSION, reason=reason, explainability=explainability)
                for name in session_names
            ]
        )

    app = runtime_context["app"]
    password = runtime_context["password"]
    preview_username = runtime_context["preview_username"]
    empty_username = runtime_context["empty_username"]
    wrong_password = runtime_context["wrong_password"]

    results: list[VerificationResult] = []
    preview_client = app.test_client()
    empty_client = app.test_client()
    wrong_password_client = app.test_client()

    login_page_response = preview_client.get("/vendor/login")
    if login_page_response.status_code == 200:
        results.append(
            pass_result(
                "vendor_login_page",
                phase=PHASE_AUTHENTICATION,
                reason="vendor_login_page_available",
                details={"status_code": login_page_response.status_code},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_login_page",
                phase=PHASE_AUTHENTICATION,
                reason="vendor_login_page_unavailable",
                details={"status_code": login_page_response.status_code},
            )
        )

    preview_login_response = preview_client.post(
        "/vendor/login",
        data={"username": preview_username, "password": password},
        follow_redirects=False,
    )
    preview_session = _session_snapshot(preview_client)
    if _has_vendor_contract_keys(preview_session):
        results.append(
            pass_result(
                "vendor_preview_login",
                phase=PHASE_AUTHENTICATION,
                reason="preview_vendor_login_passed",
                details={"status_code": preview_login_response.status_code},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_preview_login",
                phase=PHASE_AUTHENTICATION,
                reason="preview_vendor_login_failed",
                explainability=["Vendor session keys were not established after preview vendor login."],
                details={"status_code": preview_login_response.status_code, "session_keys": sorted(preview_session)},
            )
        )

    wrong_login_response = wrong_password_client.post(
        "/vendor/login",
        data={"username": preview_username, "password": wrong_password},
        follow_redirects=False,
    )
    wrong_session = _session_snapshot(wrong_password_client)
    if not _has_vendor_contract_keys(wrong_session):
        results.append(
            pass_result(
                "vendor_wrong_password",
                phase=PHASE_AUTHENTICATION,
                reason="wrong_password_rejected",
                details={"status_code": wrong_login_response.status_code},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_wrong_password",
                phase=PHASE_AUTHENTICATION,
                reason="wrong_password_unexpectedly_logged_in",
                details={"status_code": wrong_login_response.status_code, "session_keys": sorted(wrong_session)},
            )
        )

    empty_login_response = empty_client.post(
        "/vendor/login",
        data={"username": empty_username, "password": password},
        follow_redirects=False,
    )
    empty_session = _session_snapshot(empty_client)
    if _has_vendor_contract_keys(empty_session):
        results.append(
            pass_result(
                "vendor_empty_login",
                phase=PHASE_AUTHENTICATION,
                reason="empty_vendor_login_passed",
                details={"status_code": empty_login_response.status_code},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_empty_login",
                phase=PHASE_AUTHENTICATION,
                reason="empty_vendor_login_failed",
                details={"status_code": empty_login_response.status_code, "session_keys": sorted(empty_session)},
            )
        )

    if not _authentication_phase_passed(results):
        explainability = ["Session phase is blocked until all Authentication checks PASS."]
        results.extend(
            [
                blocked_result(
                    name,
                    phase=PHASE_SESSION,
                    reason="authentication_not_passed",
                    explainability=explainability,
                )
                for name in session_names
            ]
        )
        return results

    preview_forbidden_keys = _forbidden_internal_session_keys(preview_session)
    if _has_vendor_contract_keys(preview_session) and not preview_forbidden_keys:
        results.append(
            pass_result(
                "preview_vendor_session_contract",
                phase=PHASE_SESSION,
                reason="preview_vendor_session_contract_confirmed",
                details={"session_keys": sorted(preview_session)},
            )
        )
    else:
        explainability: list[str] = []
        if preview_forbidden_keys:
            explainability.append(f"forbidden_internal_keys_present={', '.join(preview_forbidden_keys)}")
        if not _has_vendor_contract_keys(preview_session):
            explainability.append("required vendor session keys are missing")
        results.append(
            fail_result(
                "preview_vendor_session_contract",
                phase=PHASE_SESSION,
                reason="preview_vendor_session_contract_mismatch",
                explainability=explainability,
                details={"session_keys": sorted(preview_session)},
            )
        )

    empty_forbidden_keys = _forbidden_internal_session_keys(empty_session)
    if _has_vendor_contract_keys(empty_session) and not empty_forbidden_keys:
        results.append(
            pass_result(
                "empty_vendor_session_contract",
                phase=PHASE_SESSION,
                reason="empty_vendor_session_contract_confirmed",
                details={"session_keys": sorted(empty_session)},
            )
        )
    else:
        explainability = []
        if empty_forbidden_keys:
            explainability.append(f"forbidden_internal_keys_present={', '.join(empty_forbidden_keys)}")
        if not _has_vendor_contract_keys(empty_session):
            explainability.append("required vendor session keys are missing")
        results.append(
            fail_result(
                "empty_vendor_session_contract",
                phase=PHASE_SESSION,
                reason="empty_vendor_session_contract_mismatch",
                explainability=explainability,
                details={"session_keys": sorted(empty_session)},
            )
        )

    return results


def run_authorization_phase(
    runtime_context: dict[str, Any] | None,
    *,
    authentication_session_results: list[VerificationResult],
) -> list[VerificationResult]:
    phase_names = [
        "unauthenticated_redirect",
        "vendor_session_only",
        "internal_session_isolation",
        "internal_cannot_impersonate_vendor",
        "vendor_cannot_pass_internal_boundary",
        "current_site_session_isolation",
        "vendor_identity_continuity",
        "post_logout_boundary",
    ]
    if not _session_phase_passed(authentication_session_results):
        return [
            blocked_result(
                name,
                phase=PHASE_AUTHORIZATION,
                reason="session_not_passed",
                explainability=["Authorization phase requires Session phase to PASS."],
            )
            for name in phase_names
        ]
    if runtime_context is None:
        return [
            blocked_result(
                name,
                phase=PHASE_AUTHORIZATION,
                reason="runtime_context_missing",
                explainability=["Authorization phase requires runtime context."],
            )
            for name in phase_names
        ]

    app = runtime_context["app"]
    password = runtime_context["password"]
    preview_username = runtime_context["preview_username"]
    results: list[VerificationResult] = []

    unauth_client = app.test_client()
    vendor_client = app.test_client()
    internal_client = app.test_client()

    unauth_response = unauth_client.get("/vendor/business-read-preview", follow_redirects=False)
    if _is_login_redirect(unauth_response, expected_fragment="/vendor/login"):
        results.append(
            pass_result(
                "unauthenticated_redirect",
                phase=PHASE_AUTHORIZATION,
                reason="unauthenticated_redirect_confirmed",
                details={"status_code": unauth_response.status_code, "location": _extract_location(unauth_response)},
            )
        )
    else:
        results.append(
            fail_result(
                "unauthenticated_redirect",
                phase=PHASE_AUTHORIZATION,
                reason="unauthenticated_redirect_missing",
                details={"status_code": unauth_response.status_code, "location": _extract_location(unauth_response)},
            )
        )

    vendor_client.post(
        "/vendor/login",
        data={"username": preview_username, "password": password},
        follow_redirects=False,
    )
    vendor_session = _session_snapshot(vendor_client)
    vendor_preview_response = vendor_client.get("/vendor/business-read-preview", follow_redirects=False)
    if vendor_preview_response.status_code == 200 and _has_vendor_contract_keys(vendor_session):
        results.append(
            pass_result(
                "vendor_session_only",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_session_only_boundary_confirmed",
                details={"status_code": vendor_preview_response.status_code, "session_keys": sorted(vendor_session)},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_session_only",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_session_only_boundary_failed",
                details={"status_code": vendor_preview_response.status_code, "session_keys": sorted(vendor_session)},
            )
        )

    _set_internal_session(internal_client)
    internal_attempt = internal_client.get("/vendor/business-read-preview", follow_redirects=False)
    if _is_login_redirect(internal_attempt, expected_fragment="/vendor/login"):
        results.append(
            pass_result(
                "internal_session_isolation",
                phase=PHASE_AUTHORIZATION,
                reason="internal_session_blocked_from_vendor_route",
                details={"status_code": internal_attempt.status_code, "location": _extract_location(internal_attempt)},
            )
        )
        results.append(
            pass_result(
                "internal_cannot_impersonate_vendor",
                phase=PHASE_AUTHORIZATION,
                reason="internal_identity_not_accepted_as_vendor",
                details={"status_code": internal_attempt.status_code, "location": _extract_location(internal_attempt)},
            )
        )
    else:
        results.append(
            fail_result(
                "internal_session_isolation",
                phase=PHASE_AUTHORIZATION,
                reason="internal_session_unexpectedly_accessed_vendor_route",
                details={"status_code": internal_attempt.status_code, "location": _extract_location(internal_attempt)},
            )
        )
        results.append(
            fail_result(
                "internal_cannot_impersonate_vendor",
                phase=PHASE_AUTHORIZATION,
                reason="internal_identity_unexpectedly_accepted_as_vendor",
                details={"status_code": internal_attempt.status_code, "location": _extract_location(internal_attempt)},
            )
        )

    internal_boundary_response = vendor_client.get("/sheet", follow_redirects=False)
    if _is_login_redirect(internal_boundary_response, expected_fragment="/login"):
        results.append(
            pass_result(
                "vendor_cannot_pass_internal_boundary",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_blocked_from_internal_route",
                details={"status_code": internal_boundary_response.status_code, "location": _extract_location(internal_boundary_response)},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_cannot_pass_internal_boundary",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_unexpectedly_accessed_internal_route",
                details={"status_code": internal_boundary_response.status_code, "location": _extract_location(internal_boundary_response)},
            )
        )

    polluted_keys = [key for key in ("current_site_id", "current_site_name", "site_selection_required") if key in vendor_session]
    if not polluted_keys:
        results.append(
            pass_result(
                "current_site_session_isolation",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_session_did_not_pollute_current_site_state",
                details={"session_keys": sorted(vendor_session)},
            )
        )
    else:
        results.append(
            fail_result(
                "current_site_session_isolation",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_session_polluted_current_site_state",
                explainability=[f"unexpected_keys={', '.join(polluted_keys)}"],
                details={"session_keys": sorted(vendor_session)},
            )
        )

    continuity_response = vendor_client.get("/vendor/business-read-preview", follow_redirects=False)
    continuity_session = _session_snapshot(vendor_client)
    if continuity_response.status_code == 200 and continuity_session.get("vendor_username") == preview_username:
        results.append(
            pass_result(
                "vendor_identity_continuity",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_identity_continuity_confirmed",
                details={"status_code": continuity_response.status_code, "session_keys": sorted(continuity_session)},
            )
        )
    else:
        results.append(
            fail_result(
                "vendor_identity_continuity",
                phase=PHASE_AUTHORIZATION,
                reason="vendor_identity_continuity_failed",
                details={"status_code": continuity_response.status_code, "session_keys": sorted(continuity_session)},
            )
        )

    vendor_client.get("/vendor/logout", follow_redirects=False)
    post_logout_response = vendor_client.get("/vendor/business-read-preview", follow_redirects=False)
    if _is_login_redirect(post_logout_response, expected_fragment="/vendor/login"):
        results.append(
            pass_result(
                "post_logout_boundary",
                phase=PHASE_AUTHORIZATION,
                reason="post_logout_boundary_confirmed",
                details={"status_code": post_logout_response.status_code, "location": _extract_location(post_logout_response)},
            )
        )
    else:
        results.append(
            fail_result(
                "post_logout_boundary",
                phase=PHASE_AUTHORIZATION,
                reason="post_logout_boundary_failed",
                details={"status_code": post_logout_response.status_code, "location": _extract_location(post_logout_response)},
            )
        )

    return results


def run_preview_contract_phase(
    runtime_context: dict[str, Any] | None,
    *,
    authorization_results: list[VerificationResult],
) -> list[VerificationResult]:
    phase_names = [
        "preview_top_level_contract",
        "preview_entry_contract",
        "preview_forbidden_fields",
        "preview_business_dates_dedupe",
        "preview_business_dates_sort",
        "preview_numeric_normalization",
        "preview_planned_at_normalization",
        "preview_empty_contract",
    ]
    if not _authorization_phase_passed(authorization_results):
        return [
            blocked_result(
                name,
                phase=PHASE_PREVIEW_CONTRACT,
                reason="authorization_not_passed",
                explainability=["Preview Contract phase requires Authorization phase to PASS."],
            )
            for name in phase_names
        ]
    if runtime_context is None:
        return [
            blocked_result(
                name,
                phase=PHASE_PREVIEW_CONTRACT,
                reason="runtime_context_missing",
                explainability=["Preview Contract phase requires runtime context."],
            )
            for name in phase_names
        ]

    app = runtime_context["app"]
    password = runtime_context["password"]
    preview_username = runtime_context["preview_username"]
    empty_username = runtime_context["empty_username"]

    preview_client = app.test_client()
    empty_client = app.test_client()
    preview_client.post("/vendor/login", data={"username": preview_username, "password": password}, follow_redirects=False)
    empty_client.post("/vendor/login", data={"username": empty_username, "password": password}, follow_redirects=False)

    preview_response = preview_client.get("/vendor/business-read-preview", follow_redirects=False)
    empty_response = empty_client.get("/vendor/business-read-preview", follow_redirects=False)
    try:
        preview_payload = preview_response.get_json()
        empty_payload = empty_response.get_json()
    except Exception as exc:  # pragma: no cover
        explainability = [f"json_decode_error={exc!r}"]
        return [
            fail_result(
                name,
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_contract_json_decode_failed",
                explainability=explainability,
            )
            for name in phase_names
        ]

    results: list[VerificationResult] = []
    top_level_keys = {"ok", "vendor_account_id", "vendor_username", "vendor_name", "entry_count", "business_dates", "entries"}
    if isinstance(preview_payload, dict) and set(preview_payload.keys()) == top_level_keys:
        results.append(
            pass_result(
                "preview_top_level_contract",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_top_level_contract_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_top_level_contract",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_top_level_contract_mismatch",
                details={"observed_keys": sorted(preview_payload.keys()) if isinstance(preview_payload, dict) else []},
            )
        )

    entries = preview_payload.get("entries", []) if isinstance(preview_payload, dict) else []
    if isinstance(entries, list) and all(set(entry.keys()) == _entry_contract_keys() for entry in entries):
        results.append(
            pass_result(
                "preview_entry_contract",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_entry_contract_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_entry_contract",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_entry_contract_mismatch",
                details={"entry_count": len(entries) if isinstance(entries, list) else 0},
            )
        )

    forbidden_fields = {"password_hash", "site_id", "sheet_id", "allowed_site_ids", "allowed_sheet_ids"}
    forbidden_hits: list[str] = []
    if isinstance(preview_payload, dict):
        forbidden_hits.extend(sorted(forbidden_fields & set(preview_payload.keys())))
        for entry in entries if isinstance(entries, list) else []:
            forbidden_hits.extend(sorted(forbidden_fields & set(entry.keys())))
    if not forbidden_hits:
        results.append(
            pass_result(
                "preview_forbidden_fields",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_forbidden_fields_absent",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_forbidden_fields",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_forbidden_fields_present",
                explainability=[f"forbidden_hits={', '.join(sorted(set(forbidden_hits)))}"],
            )
        )

    observed_business_dates = preview_payload.get("business_dates", []) if isinstance(preview_payload, dict) else []
    expected_business_dates = _sorted_unique_business_dates(entries if isinstance(entries, list) else [])
    if len(observed_business_dates) == len(set(observed_business_dates)):
        results.append(
            pass_result(
                "preview_business_dates_dedupe",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_business_dates_dedupe_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_business_dates_dedupe",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_business_dates_dedupe_failed",
                details={"business_dates": observed_business_dates},
            )
        )

    if observed_business_dates == expected_business_dates:
        results.append(
            pass_result(
                "preview_business_dates_sort",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_business_dates_sort_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_business_dates_sort",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_business_dates_sort_failed",
                details={"observed_business_dates": observed_business_dates, "expected_business_dates": expected_business_dates},
            )
        )

    numeric_ok = True
    numeric_notes: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        for key in ("planned_headcount", "actual_headcount", "work_headcount", "entry_order"):
            if not isinstance(entry.get(key), int):
                numeric_ok = False
                numeric_notes.append(f"{key} is not int")
    if numeric_ok:
        results.append(
            pass_result(
                "preview_numeric_normalization",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_numeric_normalization_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_numeric_normalization",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_numeric_normalization_failed",
                explainability=numeric_notes,
            )
        )

    planned_at_ok = all(entry.get("planned_at") != None for entry in entries if isinstance(entries, list))
    planned_at_empty_string_ok = all(isinstance(entry.get("planned_at"), str) for entry in entries if isinstance(entries, list))
    if planned_at_ok and planned_at_empty_string_ok:
        results.append(
            pass_result(
                "preview_planned_at_normalization",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_planned_at_normalization_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_planned_at_normalization",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_planned_at_normalization_failed",
            )
        )

    empty_ok = (
        isinstance(empty_payload, dict)
        and empty_payload.get("ok") is True
        and empty_payload.get("entry_count") == 0
        and empty_payload.get("business_dates") == []
        and empty_payload.get("entries") == []
    )
    if empty_ok:
        results.append(
            pass_result(
                "preview_empty_contract",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_empty_contract_confirmed",
            )
        )
    else:
        results.append(
            fail_result(
                "preview_empty_contract",
                phase=PHASE_PREVIEW_CONTRACT,
                reason="preview_empty_contract_mismatch",
                details=empty_payload if isinstance(empty_payload, dict) else {},
            )
        )

    return results


def build_verification_skeleton(preflight_results: list[VerificationResult]) -> list[VerificationResult]:
    if any(result.status == STATUS_FAIL for result in preflight_results):
        return [
            fail_result(
                "verification_framework",
                phase=PHASE_SUMMARY,
                reason="preflight_failed",
                explainability=["At least one preflight check returned FAIL."],
            )
        ]
    if any(result.status == STATUS_BLOCKED for result in preflight_results):
        return [
            blocked_result(
                "verification_framework",
                phase=PHASE_SUMMARY,
                reason="preflight_blocked",
                explainability=["Verification framework is intentionally blocked until all preflight checks PASS."],
            )
        ]
    return [
        pass_result(
            "verification_framework",
            phase=PHASE_SUMMARY,
            reason="framework_ready_for_future_phases",
            explainability=["Preflight checks passed. Later Stage 4B slices can attach Authentication, Session, Authorization, and Contract phases here."],
        )
    ]


def overall_status(results: list[VerificationResult]) -> str:
    if any(result.status == STATUS_FAIL for result in results):
        return STATUS_FAIL
    if any(result.status == STATUS_BLOCKED for result in results):
        return STATUS_BLOCKED
    return STATUS_PASS


def build_summary_payload(
    runtime_details: dict[str, Any],
    readiness_details: dict[str, Any],
    results: list[VerificationResult],
) -> dict[str, Any]:
    preflight_names = {"runtime_inventory", "dev_vendor_preview_readiness", "dev_vendor_password"}
    return {
        "runtime": runtime_details,
        "readiness": readiness_details,
        "preflight": [result.to_dict() for result in results if result.name in preflight_names],
        "verification": [result.to_dict() for result in results if result.name not in preflight_names],
        "overall_status": overall_status(results),
    }


def format_output_lines(payload: dict[str, Any]) -> list[str]:
    runtime_target = payload["runtime"]["target"]
    readiness_summary = payload["readiness"]["summary"]
    lines = [
        "Runtime",
        "-------",
        f"label: {payload['runtime'].get('label', 'development')}",
        f"target_safe: {str(bool(runtime_target.get('safe_target'))).lower()}",
        f"app_env: {runtime_target.get('app_env', '<unset>')}",
        f"render_service_name: {runtime_target.get('render_service_name', '<unset>')}",
        f"render_external_url: {runtime_target.get('render_external_url', '<unset>')}",
        "",
        "Preflight",
        "---------",
    ]
    for result in payload["preflight"]:
        lines.append(f"[{result['phase']}] {result['name']}: {result['status']} ({result['reason']})")
        for item in result["explainability"]:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "Readiness Snapshot",
            "------------------",
            f"preview_vendor_ready: {str(bool(readiness_summary['preview_vendor']['ready'])).lower()}",
            f"empty_vendor_ready: {str(bool(readiness_summary['empty_vendor']['ready'])).lower()}",
            f"preview_entries_ready: {str(bool(readiness_summary['preview_entries']['ready'])).lower()}",
            f"empty_entries_ready: {str(bool(readiness_summary['empty_entries']['ready'])).lower()}",
            f"safe_sheet_ready: {str(bool(readiness_summary['safe_sheet']['ready'])).lower()}",
            "",
            "Verification Summary",
            "--------------------",
        ]
    )
    for result in payload["verification"]:
        lines.append(f"[{result['phase']}] {result['name']}: {result['status']} ({result['reason']})")
        for item in result["explainability"]:
            lines.append(f"- {item}")
    lines.extend(["", "Overall Status", "--------------", payload["overall_status"]])
    return lines
