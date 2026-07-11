from __future__ import annotations

from copy import deepcopy
from typing import Final


_INTERNAL_ACTOR_SCOPE: Final[tuple[str, ...]] = (
    "site_member",
    "current_site_constrained_admin",
)
_CANONICAL_BUSINESS_DATE_POLICY: Final[str] = "canonical_per_form_reset_business_date"
_COMMON_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "actor_role",
    "current_site_id",
    "sheet_id",
    "intent_key",
    "source_family",
    "business_date",
    "as_of",
    "item_count",
    "empty_state_reason",
)

_SUPPORTED_AI_READ_INTENTS: Final[tuple[dict[str, object], ...]] = (
    {
        "key": "today_due_crew_entries_not_entered",
        "display_name": "今日到期尚未進場工班紀錄",
        "actor_scope": _INTERNAL_ACTOR_SCOPE,
        "readiness": "ready_candidate",
        "source_family": "crew_missing",
        "authorization_policy": "internal_current_site_sheet_read",
        "business_date_policy": _CANONICAL_BUSINESS_DATE_POLICY,
        "result_kind": "bounded_items",
        "max_items": 25,
        "evidence_fields": _COMMON_EVIDENCE_FIELDS,
    },
    {
        "key": "today_pending_requirements",
        "display_name": "今日待確認需求",
        "actor_scope": _INTERNAL_ACTOR_SCOPE,
        "readiness": "ready_candidate",
        "source_family": "dashboard_pending_requirements",
        "authorization_policy": "internal_dashboard_current_site_sheet_read",
        "business_date_policy": _CANONICAL_BUSINESS_DATE_POLICY,
        "result_kind": "bounded_items",
        "max_items": 25,
        "evidence_fields": _COMMON_EVIDENCE_FIELDS,
    },
    {
        "key": "current_blocked_items",
        "display_name": "目前 Blocked 項目",
        "actor_scope": _INTERNAL_ACTOR_SCOPE,
        "readiness": "ready_candidate",
        "source_family": "scheduling_blocked_entries",
        "authorization_policy": "internal_dashboard_current_site_sheet_read",
        "business_date_policy": _CANONICAL_BUSINESS_DATE_POLICY,
        "result_kind": "bounded_items",
        "max_items": 25,
        "evidence_fields": _COMMON_EVIDENCE_FIELDS,
    },
    {
        "key": "today_formally_scheduled_count",
        "display_name": "今日正式排程筆數",
        "actor_scope": _INTERNAL_ACTOR_SCOPE,
        "readiness": "ready_candidate",
        "source_family": "dashboard_today_schedule_count",
        "authorization_policy": "internal_dashboard_current_site_sheet_read",
        "business_date_policy": _CANONICAL_BUSINESS_DATE_POLICY,
        "result_kind": "count_only",
        "max_items": 1,
        "evidence_fields": _COMMON_EVIDENCE_FIELDS,
    },
)

_SUPPORTED_AI_READ_INTENTS_BY_KEY: Final[dict[str, dict[str, object]]] = {
    str(entry["key"]): entry for entry in _SUPPORTED_AI_READ_INTENTS
}


def list_supported_ai_read_intents() -> list[dict[str, object]]:
    return [deepcopy(entry) for entry in _SUPPORTED_AI_READ_INTENTS]


def get_supported_ai_read_intent(intent_key: str) -> dict[str, object] | None:
    if not isinstance(intent_key, str):
        return None
    entry = _SUPPORTED_AI_READ_INTENTS_BY_KEY.get(intent_key)
    return deepcopy(entry) if entry is not None else None
