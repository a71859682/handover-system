# AI-READ-001A — Role-Scoped Read-only Query Design and Readiness Baseline

## 1. Document Status and Scope

This document is a docs-only design and readiness baseline for future role-scoped, natural-language queries through the AI assistant shell. It starts from `e0289a262b7b3744c069132eaad1365df64f1b63`, with AI-UX-001A and AI-UX-001B frozen.

This slice does not enable the disabled AI shell and does not add a model, provider, prompt runtime, query UI, API, route, database access path, schema, dependency, secret, environment variable, analytics, audit implementation, or write behavior. Existing production code, permissions, workflows, serializers, and frozen baselines remain unchanged.

The future first query capability is completely read-only. A query must not create a draft, update session scope, persist a prompt or response, trigger a workflow transition, or otherwise change application or database state.

## 2. Product Goal

The product goal is to let an authenticated user ask concise questions about existing construction data in the AI modal while preserving the product principle “Minimize Field Input, Maximize Management Insight.”

Every answer must:

- come only from canonical read data obtained after existing authorization;
- use identity and scope derived from the authenticated session, never from the prompt;
- distinguish persisted facts, existing computed decisions, and AI interpretation;
- state the business date and as-of scope when time affects the answer;
- return an explicit empty state when canonical data contains no matching records; and
- remain read-only from request through response.

AI is a language interface over existing product capabilities. It is not a new permission layer, a direct database reader, or a second implementation of scheduling, readiness, approval, progress, or site-isolation rules.

## 3. Existing Read Contract Inventory

### 3.1 Identity and scope foundations

Internal identity begins with `session.user_id`; `_current_internal_user()` reloads the persisted user and `is_global_admin()` derives the effective admin role from that user. A future query runtime must use this server-derived identity and must not accept `role`, `user_id`, or admin status from user text or model output.

For non-admin internal users, `_resolve_non_admin_read_site_id()` requires a valid active `current_site_id` and a matching active `user_site_permissions` row. `authorize_dashboard_read()` also requires admin to have a valid current site and confirms that the requested sheet belongs to it.

Vendor identity is a separate session type established by `set_vendor_session()`. `require_current_vendor_business_identity()` derives `vendor_account_id`, `vendor_username`, and `vendor_name` from that session. `current_vendor_scope()` explicitly labels this boundary `vendor_identity_only`, version 1. Vendor identity must never be accepted from a prompt parameter.

### 3.2 Canonical internal read surfaces

| Existing surface/helper | Current output and rule ownership | Current authorization boundary | AI readiness use |
|---|---|---|---|
| `GET /api/grid` → `render_grid_payload()` / `load_grid()` | Persisted sheets, floors, units, tasks, progress and extra values; existing floor parent status and summaries | Internal login; non-admin current-site permission and sheet lineage; current `authorize_sheet_read()` admin behavior differs from dashboard-family current-site behavior | Candidate for floor/unit/task fact queries only after the AI adapter enforces the stricter current-site/sheet boundary for every internal role |
| `GET /api/crew-forms` → crew/vendor/contact/work-entry helpers | Active vendors, contacts and business-date work entries with existing readiness and formal-approval state | Internal login plus `authorize_sheet_read()` | Candidate item source; must not expose contact fields unless the supported intent requires and authorizes them |
| `GET /api/crew-followups` | Active vendors without a valid planned time, plus pending item/contact context | Internal login plus `authorize_sheet_read()` | Canonical candidate for “待確認／待聯繫” only if UI terminology is mapped to this exact existing definition |
| `GET /api/crew-missing` | Active-vendor entries whose planned time is valid and due, with zero actual headcount | Internal login plus `authorize_sheet_read()` | Canonical source for “今天有哪些廠商還沒進場？”; AI must preserve its due-time and zero-headcount definition |
| `GET /api/dashboard` → `build_dashboard_payload()` | Today entries, persisted schedules, pending requirement/approval groups and summary counts | `authorize_dashboard_read()`; internal actor only; current-site and sheet lineage required; vendor forbidden | Candidate for item-level operational queries and persisted-schedule counts |
| `GET /api/scheduling` → `build_scheduling_payload()` | Existing `schedulable` and `blocked` decisions derived by upstream gate and approval helpers | Same as dashboard | Canonical computed-decision source; AI must not reproduce its rules |
| `GET /api/work-hub-runtime` → `build_work_hub_runtime_payload()` | Frozen dashboard/scheduling composition and Work Hub projection | Same as dashboard | Preferred scoped composition where its item lists answer the intent |
| `GET /api/management-read-model` → `build_management_read_model_payload()` | Management counts, entry references and drilldown references from existing dashboard/scheduling helpers | Same as dashboard | Preferred management count/reference source; not sufficient alone for item details |

All listed GET surfaces are read contracts, not blanket permission to call a Flask route from another backend component. A future implementation should reuse the underlying authorization and helper/service contracts. If a safely reusable helper boundary is missing, a readiness/refactor slice must establish it without copying route logic or issuing backend HTTP calls to the same Flask application.

### 3.3 Canonical vendor read surfaces

`GET /vendor/profile`, `GET /vendor/scope`, `GET /vendor/work-entry`, and `GET /vendor/business-read-preview` are protected by `vendor_login_required`. `authorize_vendor_business_read()` resolves the authenticated vendor identity, and `fetch_vendor_business_read_preview()` filters rows by that trusted `vendor_name`.

The preview serializer currently exposes entry identity, business date, planned/actual headcount, work content, pre-entry requirement, work headcount, and entry order. It does not expose the complete requirement-confirmation, readiness, formal-approval, scheduling, site, or sheet state needed for every proposed vendor status question.

The current vendor read boundary is vendor-identity-scoped rather than explicitly current-site/sheet-scoped. It may return the authenticated vendor's entries across sheets that share that vendor identity. Therefore:

- vendor “my entries” queries may not be production-enabled until the intended site/sheet semantics are explicitly approved;
- a future query must not invent `current_site_id` or select a sheet on the vendor's behalf;
- a prompt-provided site, sheet, or vendor must not broaden the vendor read; and
- vendor status questions that need fields absent from the canonical vendor response are unsupported until a separate vendor read-readiness slice safely exposes them.

### 3.4 Existing smoke evidence

Current smoke contracts cover representative success, deterministic empty-state, unauthenticated, vendor-forbidden, missing-current-site, permission-removed, cross-site, and database-non-mutation behavior across crew, dashboard, scheduling, Work Hub runtime, management read model, grid/report, and vendor read paths. They also protect the AI-UX-001B disabled shell and prohibit network, voice, storage, and write capability in that shell.

This evidence is reusable but is not yet a dedicated AI query contract. A future implementation requires focused smoke coverage for intent allowlisting, session-derived scope, grounding labels, response evidence, data minimization, prompt-injection handling, and zero mutation.

## 4. First Supported Query Set

### 4.1 Site member

Candidate supported questions are:

- “今天有哪些廠商還沒進場？”
- “今天有哪些工班待確認需求？”
- “目前有哪些 blocked 項目？”
- “19樓還有哪些工項未完成？”
- “今天已正式排程幾筆？”

“今天” means the existing `resolve_crew_business_date()` result unless the UI clearly shows and authorizes a different business date. The server must reuse the canonical business-date/reset-time contract—currently defaulting to 08:30 and remaining a per-form setting long term—not model time, browser time, or a guessed calendar date. If the intent omits a date, the server resolves it through that contract, and query evidence returns the actual `business_date` used. “還沒進場” means the existing `/api/crew-missing` decision: active vendor, valid planned time not later than server `now`, and actual headcount equal to zero. It does not mean every active vendor without an entry or every vendor with unfinished work.

“待確認需求” must map to existing `readiness_reason == requirement_pending` / dashboard pending-requirement data. “Blocked” must map to the existing scheduling payload's `blocked_entries`; AI must not create a new blocked rule. “未完成” must map to authorized grid progress whose canonical value is not complete for the uniquely resolved floor/task context. “正式排程” must use persisted scheduling entries and `today_schedule_count`, not the in-memory scheduling candidate list.

### 4.2 Vendor

Candidate questions are:

- “我今天填了哪些進場資料？”
- “我的哪些進場需求尚未確認？”
- “我今天的進場資料目前是什麼狀態？”

“我” always means the authenticated vendor identity. The model cannot substitute a vendor named in the prompt. The first question is a candidate based on vendor business-read data, subject to the site/sheet readiness gate in section 3.3. The latter two require additional canonical vendor-visible state that the current preview serializer does not fully provide and are not implementation-ready in this baseline.

### 4.3 Admin

Admin may query only data visible through an existing admin-compatible read contract. AI must require an active current-site and sheet context even where a broader legacy helper might currently allow global-admin reads. It must not aggregate another current site, infer a cross-site portfolio, or treat admin as a maintenance/superuser mode.

### 4.4 Future 工區管理部

This remains a disabled extension point. It has no identity source, canonical helper allowlist, query intent, or data access in this baseline. Unknown or future roles fail closed.

## 5. Role and Scope Matrix

| Role | Identity source | Current-site requirement | Sheet scope | Vendor scope | Candidate canonical helpers | Forbidden and failure behavior |
|---|---|---|---|---|---|---|
| Site member | Persisted internal user resolved from `session.user_id`; effective role from server user record | Required; active site plus `user_site_permissions` | Exactly one sheet whose persisted `site_id` equals current site | Only vendors represented inside that authorized sheet/read result | `render_grid_payload`, crew read helpers, dashboard, scheduling, Work Hub runtime, management read model | Missing site or permission: forbidden/no data; cross-site: forbidden; never disclose candidate sites, sheets, vendors, or items from rejected scope |
| Vendor | `identity_type=vendor` plus server session vendor account/name | No internal current-site exists today; this is a readiness gap, not permission to infer one | No explicit safe AI sheet contract today; must be approved before enablement | Exactly authenticated vendor; never prompt-selected vendor | Vendor profile/scope/business identity and business-read helper, only after site/sheet intent is resolved by an approved contract | Cross-vendor always forbidden; site/sheet-dependent intent unsupported until canonical scope exists; missing vendor session redirects/rejects without data |
| Admin | Persisted internal user resolved from `session.user_id`; admin role from server record | Required by AI query policy | Exactly one current-site sheet | Vendors only as records within that authorized sheet | Dashboard-family helpers; grid/crew helpers only behind the stricter AI current-site gate | Missing site: forbidden/clarification to select site; cross-current-site and portfolio aggregation forbidden; no permission expansion |
| Future 工區管理部 | None | Disabled | None | None | None | Reject as unsupported; do not infer equivalence to member or admin |

No role may use a model-selected helper. User text and model output cannot directly select a route, helper, table, or serializer. The server-side supported intent registry is the only selector for authorization, canonical helper, serializer, item limit, and evidence shape. It must be keyed by authenticated identity type, effective role, supported intent, canonical source, current site, sheet, and vendor scope where applicable. Unsupported intents cannot degrade into arbitrary database access or general search.

## 6. Canonical Read Source Mapping

| Query intent | Canonical helper/read model | Classification | Required authorization | Response grounding | Empty-state behavior | Readiness |
|---|---|---|---|---|---|---|
| `today_not_entered_vendors` | `/api/crew-missing` underlying helpers | Existing computed decision over persisted work-entry facts and server time | Internal member/admin; AI-enforced current-site and one-sheet lineage | Business date, as-of time, exact “planned and due with zero actual headcount” definition, returned vendors/items | “依目前時間與所選工地／表單，沒有已到預定時間但尚未進場的廠商。” | Ready for a later internal read implementation after helper reuse is confirmed |
| `today_pending_requirements` | Dashboard `pending_requirements`; Work Hub item list; management read model count/reference | Existing computed decision | `authorize_dashboard_read()` | `requirement_pending` source, business date, item count; details only from authorized item source | “今天沒有待確認需求。” | Ready for internal read-only implementation |
| `current_blocked_items` | Scheduling `blocked_entries`; Work Hub `blocked_entries`; management read model references/count | Existing computed decision | `authorize_dashboard_read()` | State that “blocked” is the existing scheduling decision; include reason fields only if canonical payload provides them | “目前沒有 blocked 項目。” | Ready for internal read-only implementation |
| `floor_incomplete_tasks` | `render_grid_payload()` / `load_grid()` authorized task, floor, unit and progress data | Persisted facts plus existing grid aggregation | Internal role, current-site, exact sheet, uniquely resolved floor | Floor label, task labels, progress values/counts; do not infer completion from dashboard counts | “在所選表單的 19 樓找不到未完成工項。” or distinguish “找不到 19 樓” from a true empty result | Conditional: requires strict admin current-site wrapper and deterministic floor resolution |
| `today_formally_scheduled_count` | Dashboard `today_schedule_count` and `today_schedule`; management read model scheduling overview | Count computed from persisted scheduling rows filtered by business date | `authorize_dashboard_read()` | Label count as persisted schedule-derived; include business date and canonical source | “今天已正式排程 0 筆。” | Ready for internal read-only implementation |
| `vendor_today_entries` | Vendor business-read helper filtered by authenticated vendor identity | Persisted facts | Valid vendor session; authenticated vendor name only | Vendor identity from session, business date, returned entry count; site/sheet only if a future canonical contract supplies it | “你今天沒有已填寫的進場資料。” | Conditional: vendor site/sheet semantics must be approved |
| `vendor_pending_requirements` | No complete vendor-visible canonical response today | Existing computed decision would be required | Vendor identity plus future explicit scope and vendor-visible authorization | Must not derive from internal dashboard data or expose internal-only workflow fields | “目前沒有可安全查詢的已授權資料” rather than guessing | Not ready; separate readiness slice required |
| `vendor_entry_status` | No complete vendor-visible canonical status response today | Persisted facts plus existing computed decisions would be required | Same as above | Each status label must map to an existing vendor-visible field/decision | No data or unsupported, never inferred status | Not ready; separate readiness slice required |

`vendor_pending_requirements` and `vendor_entry_status` must remain Not ready. AI-READ-001B and AI-READ-001C must not implement either intent unless a prior, separately reviewed vendor site/sheet/status contract readiness baseline has passed.

The AI must not directly read an arbitrary table, dynamically compose SQL, recalculate scheduling/readiness/approval rules, use a dashboard count to invent item details, present a computed decision as a persisted fact, or use prompt-provided site/vendor identity in place of session identity.

## 7. Read-only Query Flow

The required server-side flow is:

```text
User text
→ normalize query without changing meaning
→ classify against a closed allowlist of supported read intents
→ derive actor identity and effective role from the server session
→ resolve current-site, sheet, business date, and vendor scope from trusted context
→ execute existing read authorization
→ call the allowlisted canonical read helper
→ construct grounded facts and existing computed decisions
→ optionally generate a scoped interpretation/summary
→ return answer plus source/scope evidence
```

At no point may model output select a role, site, sheet, vendor identity, arbitrary helper, table, SQL predicate, or authorization outcome.

If an intent is unsupported or its target/date/term is ambiguous, the result is `needs_clarification` or `unsupported_intent`. The system must not widen the query, search other sites/vendors to offer candidates, or return candidate labels that could leak unauthorized data. Clarification choices may be built only from already-authorized scope.

The read path must use a read-only transaction/connection policy appropriate to the existing application and must be verified by before/after database snapshots. A read response, model answer, or HTTP 200 is not evidence that authorization was correct; authorization evidence must be constructed server-side.

## 8. Grounding Contract

### 8.1 Classification labels

- **Persisted fact:** a value read from an authorized canonical persisted source, such as an entry's actual headcount, progress value, or scheduling row.
- **Existing computed decision:** a result produced by an existing product helper that owns the rule, such as `blocked`, `schedulable`, `requirement_pending`, or an existing summary count.
- **AI interpretation/summary:** wording that compresses authorized facts or decisions without adding a new business fact, prediction, recommendation, or status.

An answer must not collapse these categories. For example, “2 筆正式排程” is a count computed from persisted scheduling rows; “2 筆可能準時” would be a new unsupported prediction.

### 8.2 Minimum server evidence

Every answer must retain or return server-side evidence containing at least:

- actor identity type and effective role;
- `current_site_id` when the canonical role contract has one;
- `sheet_id` when the query is sheet-scoped;
- authenticated vendor identity when applicable;
- normalized query intent;
- canonical source/helper name and contract version if one exists;
- business date and as-of timestamp;
- returned item count;
- empty-state reason or authorization/clarification outcome; and
- grounding classification for each response section.

Raw internal IDs need not be displayed in conversational UI. They may remain in server evidence for scope validation and investigation. Human-readable labels shown to users must come from the same authorized canonical result.

### 8.3 Evidence is not authority

Evidence describes an already-authorized read; it does not authorize a later read or write. Each new query must derive current identity/scope again and rerun authorization. A cached answer must not survive an actor, permission, current-site, sheet, vendor, business-date, or source-version change without revalidation.

If caching is introduced later, the key must include at least actor identity, role, `current_site_id`, `sheet_id`, vendor identity when applicable, `business_date`, intent, and relevant data version/as-of. Answers and provider context must never be reused across users, sites, sheets, or vendors, and permission/session changes invalidate prior cache entries.

## 9. Prompt Injection and Data Handling

Database values and retrieved fields—including vendor names, task names, work content, requirement text, contact text, unit labels, and scheduling notes—are untrusted data, not system instructions. Retrieved content must not alter the intent allowlist, system prompt, authorization logic, helper selection, output policy, or query scope.

User text and retrieved text must not:

- declare or override role, site, sheet, vendor identity, permission, business rule, or authorization result;
- request hidden system prompts, secrets, unrelated records, or cross-scope context;
- cause another site/vendor's data to enter model context;
- turn an unsupported intent into an unrestricted search; or
- cause a write, navigation side effect, network call to an unapproved destination, or persistent storage.

Before provider selection, this baseline makes no claim that application data will be sent to any third party. A future provider slice must separately review data minimization, transfer fields, retention, training use, consent where applicable, privacy notice, regional processing, subprocessors, incident handling, secret management, logging/redaction, and deletion policy. Only the minimum already-authorized data needed for the supported intent may enter model context.

Each registered intent must define an item-count and response-size limit. Large results return a summary plus controlled pagination or an authorized drilldown reference; the runtime must not send an entire grid, all vendors, or complete cross-floor data into provider context. Truncation must be explicit, must not change authorization, and must not be presented as a complete result.

## 10. Candidate Response Shape

The following is a design candidate only. It is not a formal API contract and does not define or add an API. It must not be frozen before a separate route, authorization, serializer, and implementation-readiness review. Any future vendor response must contain only the authenticated vendor identity and must never expose another vendor identity. An authorized empty state and a forbidden response are different outcomes and must remain visibly and structurally distinguishable.

```json
{
  "ok": true,
  "mode": "read_only",
  "intent": "today_not_entered_vendors",
  "answer": "目前有 2 家廠商尚未進場。",
  "scope": {
    "site_id": 1,
    "sheet_id": 3,
    "business_date": "2026-07-11"
  },
  "evidence": {
    "source": "crew_missing",
    "classification": "existing_computed_decision",
    "item_count": 2,
    "as_of": "2026-07-11T10:15:00+08:00",
    "empty_reason": null
  },
  "items": []
}
```

Candidate non-success modes are `needs_clarification`, `unsupported_intent`, `forbidden`, `no_data`, and `error`. A forbidden result must not include candidate items, counts, labels, or source fragments from the rejected scope. An empty authorized result must be distinguished from missing scope, unsupported data, source failure, and forbidden access.

## 11. Error and Boundary Matrix

| Condition | Required outcome | Clarification allowed? | Non-leakage rule |
|---|---|---|---|
| Unauthenticated | Reject as authentication required using the existing session boundary | No; direct authentication flow only | Do not confirm whether a site, sheet, vendor, or matching item exists |
| Vendor requests an internal-only or otherwise forbidden intent | `forbidden` | No | Do not name allowed internal intents in a way that reveals data, counts, sites, sheets, or other vendors |
| Missing current site for an internal intent | Fail closed; require site selection through the existing product flow | A neutral instruction to select a current site is allowed; do not offer unauthorized site candidates | Do not execute a query or reveal whether the requested sheet/data exists |
| Inactive current site | `forbidden` / invalid scope and clear stale scope | No data-oriented clarification; use existing site-selection recovery only | Treat the inactive scope as unavailable and reveal no item metadata |
| Invalid or nonexistent sheet | Invalid target after authorization-safe parsing | A generic request to choose a sheet from already-authorized UI context is allowed | Do not distinguish nonexistent from inaccessible when that distinction would enable probing |
| Cross-site sheet | `forbidden` | No | Do not reveal the sheet name, site, counts, or whether matching records exist |
| Stale session, removed permission, changed role, vendor deactivation, or changed scope | Reject and require reauthentication or scope refresh | No data-oriented clarification | Discard cached facts and do not disclose the prior scope's results |
| Unsupported intent | `unsupported_intent` | May offer only a generic supported-capability description independent of record existence | Do not search a wider scope or show data-derived suggestions |
| Ambiguous supported intent or multiple authorized targets | `needs_clarification` | Yes, but choices may come only from the already-authorized scope | Never include unauthorized candidates; ambiguity does not relax authorization |
| Authorized query with no matching data | `no_data` or successful empty state | Optional clarification about authorized filters/date | State zero/no data; do not label it forbidden or invent results |
| Canonical source unavailable, timeout, or retry-safe dependency failure | `error` with retry-safe wording | No scope expansion; retry of the same authorized request may be offered | Do not fall back to another broader source, model memory, stale unauthorized cache, or guessed answer |
| Internal error | Generic `error` plus server-side correlation evidence | No | Do not return stack traces, SQL, secrets, internal IDs, raw prompts, or partial unauthorized results |

Permission failures must be decided before record-level response construction. The response must not vary based on whether forbidden data exists. Clarification is for a supported intent inside an already-authorized scope; it is never a mechanism to probe role, site, sheet, vendor, or record existence.

## 12. Read-only Invariants

A future implementation smoke suite must prove all of the following:

- database snapshots before and after success, empty, clarification, unsupported, forbidden, timeout, and error paths are unchanged;
- the AI read path makes no POST or other mutation request and invokes no mutation helper;
- no schema or migration is added or executed;
- permission, role, session, authorization, workflow, readiness, approval, scheduling, and write behavior remain unchanged;
- all existing API response and error contracts remain unchanged unless a separately approved contract slice explicitly versions a new surface;
- cross-site requests disclose no data, candidate labels, counts, or existence signals;
- vendor responses contain only the authenticated vendor's identity and data, with cross-vendor non-leakage proven against mixed-vendor fixtures;
- an authorized empty result is reported as empty/no data, not forbidden;
- a forbidden result reveals neither whether data exists nor what an empty authorized response would contain;
- canonical source failure never falls back to model inference;
- AI output is not accepted as database fact unless grounded to the canonical source classification; and
- an AI response is never write authorization, write confirmation, mutation result, audit evidence, or proof that a write succeeded.

These invariants supplement rather than replace existing route and smoke contracts. No existing audit capability is assumed to be sufficient for AI read observability.

## 13. Readiness Gaps

The following capabilities do not yet exist as an approved AI read-query production contract:

| Gap | Required future decision/evidence |
|---|---|
| Query intent registry | Closed, versioned allowlist with terminology, parameters, eligible roles, source mapping, ambiguity rules, and unsupported behavior |
| Role-scoped orchestration helper | One server-controlled flow for identity, current-site, sheet, vendor scope, authorization, canonical helper selection, and non-leaking failure handling |
| Grounded response serializer | Versioned separation of persisted facts, existing computed decisions, AI interpretation, scope evidence, empty state, and forbidden/error shapes |
| Provider/model decision | Approved model/provider or an explicitly model-free implementation; no provider is selected by this baseline |
| Privacy/retention review | Data minimization, transfer, consent/notice, retention, training use, regional processing, access, redaction, and deletion policy |
| Prompt-injection guardrail | Tested separation of instructions from user/retrieved data, context filtering, output constraints, and adversarial fixtures |
| Read audit/observability policy | Defined events, access control, redaction, retention, correlation, actor/scope evidence, and incident investigation boundary |
| Timeout/retry/fallback contract | Time limits, cancellation, retry safety, stale-result policy, canonical-source failure behavior, and explicit no-guess fallback |
| Cost/rate-limit policy | Per-role and per-session limits, abuse handling, provider budget controls, user feedback, and availability behavior |
| Vendor site/sheet and status contract | Approved identity-wide versus site/sheet semantics and a vendor-visible canonical status serializer |
| Admin current-site consistency | A strict AI read boundary that prevents broader legacy admin helper behavior from bypassing current-site policy |

This baseline does not assume maintenance mode, write freeze, rollback, reconciliation, provider fallback, durable prompt storage, a general AI audit system, or any of the capabilities above.

## 14. Readiness Decision and Future Slice Decomposition

AI-READ-001A is design-ready but does not authorize production implementation. The following gates must be closed before a read-query capability is enabled:

1. **AI-READ-001B — Supported Query Intent Registry Baseline**
   - freeze supported terminology, parameters, roles, source mapping, clarification, empty, forbidden, and unsupported behavior before orchestration code exists.
   - recommend the first internal allowlist contain only `today_not_entered_vendors`, `today_pending_requirements`, `current_blocked_items`, and `today_formally_scheduled_count`; keep `floor_incomplete_tasks` Conditional until bounded grid loading and no business-rule recomputation are proven.
2. **AI-READ-001C — Role-Scoped Read Orchestration Helper**
   - establish reusable non-HTTP authorization/helper boundaries, strict internal current-site/sheet policy, vendor scope policy, grounded fact construction, and zero-mutation guardrails.
3. **AI-READ-001F — Provider／Privacy／Prompt-Safety Readiness**
   - complete provider/model, privacy/retention, prompt-injection, timeout/retry/fallback, observability, cost, and rate-limit review before a provider-backed endpoint processes production data.
4. **AI-READ-001D — Read-only API Contract Baseline**
   - define and implement a versioned read-only route only after 001B, 001C, and all applicable 001F gates pass; preserve existing APIs and distinguish empty, clarification, forbidden, source failure, and internal error.
5. **AI-READ-001E — Disabled Shell to Read-only UI Consumption**
   - enable text query UI only against the approved read-only contract; show scope, as-of time, loading, empty, clarification, forbidden, and retry-safe states while retaining no write or voice capability.
6. **AI-READ-001G — Production Read-only Query Freeze**
   - complete DEV and Production source, authorization, non-leakage, runtime, desktop/mobile/keyboard, failure, observability, and cost Freeze Gates before marking the read capability frozen.

The suggested labels place 001F before API implementation even though its suffix is later. This ordering is intentional: provider/privacy/prompt-safety readiness is a prerequisite for any provider-backed production-data flow, while a demonstrably model-free local classifier could proceed only for the explicitly approved subset that does not depend on 001F provider transfer. No implementation is performed by this document.

## 15. Explicit Out-of-Scope

This slice does not:

- modify `app.py`, templates, static assets, tests, frozen docs, or any production code;
- enable the AI textarea, microphone, submit action, query UI, or modal processing;
- add an AI/model SDK, provider, network call, dependency, secret, or environment variable;
- add or change an API, route, helper, serializer, permission, session, workflow, or business rule;
- add schema, migration, cache, prompt store, transcript store, audit table, or analytics;
- query or modify Production or any other database;
- implement AI read, write, voice, recommendation, prediction, ranking, or cross-site reporting;
- enable Vendor, Admin, or future 工區管理部 AI entry surfaces; or
- change AI-UX-001A, AI-UX-001B, M4-IMP-004A, Work Hub, scheduling, approval, or Vendor Work Entry frozen scope; or
- claim or introduce maintenance mode, rollback, write freeze, or post-deploy reconciliation capability.

## 16. Design Acceptance Criteria

This baseline is ready for design review when reviewers agree that:

- every candidate intent maps to an existing authorized source or is marked not ready;
- persisted facts, existing computed decisions, and AI interpretation remain distinct;
- session identity always overrides prompt claims;
- current-site, sheet, and vendor boundaries fail closed;
- vendor and admin readiness gaps are explicit and do not silently broaden access;
- empty, ambiguous, unsupported, forbidden, and error results are distinguishable;
- retrieved data cannot become instructions or expand model context;
- the proposed response is design-only and creates no API commitment; and
- production code and all frozen baselines remain unchanged.
