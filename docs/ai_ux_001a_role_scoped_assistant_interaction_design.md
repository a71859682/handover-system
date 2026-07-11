# AI-UX-001A — Role-Scoped AI Assistant Interaction Design Baseline

## 1. Document Status And Scope

- Slice: `AI-UX-001A`
- Type: docs-only interaction design baseline
- Source production baseline: `f233a0adc08bba227085f17ee47efba47bdb5ba6`
- Source status: `M4-IMP-004A — PRODUCTION BASELINE / FROZEN`
- Implementation status: not implemented

This document defines the first role-scoped AI assistant interaction boundary. It does not authorize or implement an AI button, modal, drawer, bottom sheet, text input, voice input, model call, API, database write, permission change, workflow change, schema change, or audit subsystem.

The assistant is a future interaction layer over existing product capabilities. It is not a new source of truth and is never an independent authorization layer.

## 2. Product Purpose

The product purpose is to let field users complete supported data entry and queries with the least practical amount of text or voice while keeping the result visible, reviewable, and controlled.

This direction extends the product principle:

> Minimize Field Input, Maximize Management Insight

It also remains aligned with the existing Product Mission, Task-Driven Construction Operations Platform, Role-Oriented Work Hub, Mobile First, Read Before Write, and Progressive Product Evolution principles.

The assistant must:

- reduce repetitive field input without reducing authorization, confirmation, or audit quality
- help users express an operational goal before making them navigate to a feature
- present management insight from authorized read models without re-judging business rules
- use the authenticated actor, current site, current sheet, and route-specific action boundary already established by the product
- fail closed when identity, scope, target, action, or intended value is not unique

The assistant must not:

- become a super-permission layer
- infer that natural-language fluency equals authority
- create a second business-rule engine or write path
- treat generated text as an operational fact or write-success record

## 3. Existing Surface And Contract Inventory

### 3.1 Floating navigation

`templates/sheet.html` currently renders a right-side `nav.sheet-bidirectional-floating-navigation` with two anchor controls:

1. `↑` links to `#top`
2. `↓` links to `#sheet-lower-table-start`

The navigation has an `aria-label`, and each link has its own destination-specific `aria-label`. The glyphs are hidden from assistive technology with `aria-hidden="true"`.

`static/styles.css` currently positions this navigation as a fixed grid on the right and above the bottom safe-area inset. Each control has a 44 by 44 pixel minimum target, outline styling, hover feedback, and a visible keyboard-focus treatment. The navigation is excluded from print output.

### 3.2 Frontend interaction baseline

`static/app.js` currently contains:

- render helpers for Management Insight, Work Hub cards, focus sections, and crew entry rows
- read fetches for `/api/grid`, `/api/crew-forms`, `/api/management-read-model`, `/api/work-hub-runtime`, `/api/dashboard`, and `/api/scheduling`
- POST action entry points for requirement confirmation, formal approval, progress, unit-extra values, and sheet reset
- a shared `postJson(...)` helper for the grid's current progress and extra-field writes
- keyboard activation patterns for existing Work Hub interactive items
- native `window.confirm(...)` for destructive sheet reset confirmation
- a date popover, but no reusable dialog/modal manager, focus trap, drawer, or bottom-sheet component

The future assistant shell therefore must not claim that a complete accessible modal contract already exists. `AI-UX-001B` must define and verify that shell explicitly.

### 3.3 Auth and identity contracts

The current runtime separates internal and vendor identity:

- internal sessions use `user_id`, `username`, `display_name`, `role`, current-site state, and selected-sheet state
- `login_required` checks the internal `user_id` session boundary
- `admin_required` additionally requires global `role == "admin"`
- vendor sessions use `identity_type == "vendor"`, `vendor_account_id`, `vendor_username`, and `vendor_name`
- `vendor_login_required` and vendor identity helpers keep vendor identity separate from internal identity
- vendor scope is currently described as `vendor_identity_only`

The assistant must derive actor identity only from the authenticated server session. It must never accept actor role, vendor identity, site membership, or administrative status from a prompt or client-controlled preview field.

### 3.4 Current-site, sheet, and site isolation contracts

Existing helpers provide reusable authorization boundaries:

- non-admin reads require a valid active `current_site_id` and a current `user_site_permissions` row
- sheet reads resolve the persisted `sheets.site_id` and reject a sheet outside the current site
- dashboard, Work Hub, scheduling, and management read-model routes reject unauthenticated, vendor, missing-current-site, and cross-site access as applicable
- progress writes resolve unit → floor → sheet → site and verify task/sheet consistency
- unit-extra writes resolve unit → floor → sheet → site and verify extra-field/sheet consistency
- Vendor Work Entry writes resolve persisted sheet/site/vendor/entry relationships before authorization
- requirement confirmation, formal approval, and scheduling resolve the entry's persisted sheet/site lineage
- admin site-content writes use an admin route gate plus current-site-aware target authorization

An AI request must reuse these server-side resolutions. Client context such as the visible sheet, a label, or the phrase “目前工地” is only a target hint and is never authorization evidence.

### 3.5 Existing canonical read contracts

Candidate reusable read paths include:

- `/api/grid`
- `/api/crew-forms`
- `/api/dashboard`
- `/api/scheduling`
- `/api/work-hub-runtime`
- `/api/management-read-model`
- vendor-authenticated business read surfaces that are already scoped to the current vendor identity

Work Hub remains a frozen read-only presentation boundary. The assistant may summarize authorized Work Hub/read-model output, but must not make its own blocked, readiness, formal-approval, or scheduling decision.

AI query results must be grounded only in canonical read data returned after role/site authorization, must distinguish persisted fact, computed decision, and AI interpretation, and must report no data rather than infer or complete a missing database fact.

### 3.6 Existing canonical write contracts

Potential future reuse is limited to the actor-compatible canonical routes that already own validation and authorization:

| Existing path | Existing purpose | Reuse boundary for future AI |
| --- | --- | --- |
| `POST /api/progress` | Set one unit/task value to `O` or `X` | Resolve one unit and one task; rerun authorization; preview exact before/after; confirm |
| `POST /api/unit-extra` | Set one unit extra-field value | Resolve one unit and one active field on the same sheet; rerun authorization; confirm |
| `POST /api/vendor-work-entry` | Create/update one Vendor Work Entry through its current trusted runtime context | Preserve identity, site, sheet, vendor, entry, validation, and route compatibility; do not assume every role can call it |
| `POST /api/crew-work-entry-requirement-confirm` | Confirm one entry requirement | Internal crew/site boundary only; vendor forbidden; preserve idempotent repeated-confirm behavior |
| `POST /api/crew-work-entry/formal-approve` | Persist one allowed formal approval | Preserve action value, readiness gate, current-site checks, vendor prohibition, and duplicate guard |
| `POST /api/schedule-entry` | Persist one schedulable entry | Preserve formal-approval/gate checks and duplicate guard; scheduling is not an initial AI use case |

The endpoint name alone does not establish role compatibility. Before any future AI write is enabled, its implementation slice must prove that the authenticated role can call the selected canonical path without changing that path's permission or workflow behavior.

The assistant must never reproduce SQL, call database helpers directly, or create an “AI write API” that bypasses the domain route/service boundary.

Calling a canonical write path does not mean making an HTTP request from the backend to its own Flask route. Future AI writes must reuse the existing mutation helper/service and authorization contract; if no safely reusable service exists, `AI-WRITE-001` must first complete a design/readiness slice and must not copy route logic.

### 3.7 Confirmation, approval, and audit capability

Existing confirmation and approval capabilities are domain-specific:

- requirement confirmation persists confirmation status, actor, and timestamp
- formal approval persists actor/timestamp and rejects a duplicate approval through an entry/action uniqueness guard
- sheet reset uses explicit native confirmation and admin password re-entry
- some writes persist `updated_by` and `updated_at`

These fields are useful operational evidence, but they are not a complete, general AI action audit log. No baseline reviewed here establishes a universal audit event containing prompt/transcript, resolved intent, before/after, actor, site, sheet, timestamp, result, and idempotency key.

Accordingly:

- read-only assistant use may proceed in a later isolated slice without claiming write audit support
- no confirmed AI write may be production-enabled until the required audit evidence and idempotency guardrail exist and are verified
- the product must not assume maintenance mode, write freeze, rollback tooling, retry queue, or post-deploy reconciliation capability

## 4. Floating AI Entry

### 4.1 Placement and appearance

Desktop and mobile should add an `AI` control at the top of the existing right-side floating navigation, producing this visual order:

```text
AI
↑
↓
```

The `AI` control should use the product primary color as a solid fill. The `↑` and `↓` navigation controls should retain their existing outline appearance. All three controls should preserve at least the existing 44 by 44 pixel target size and safe-area behavior.

The control must remain absent from print output.

### 4.2 Open behavior

Activating `AI` must not navigate away from, reload, or discard the current page state.

- desktop: modal or right-side drawer
- mobile: bottom sheet

The later shell slice must select one desktop presentation through implementation review. The behavioral contract is the same regardless of container:

- open above the current page
- preserve the page as context, not as authorization
- move focus into the assistant
- prevent focus from escaping while modal behavior is active
- restore focus to the `AI` control on close
- close through a visible close button or `Escape`, except while a non-cancellable confirmed request is already submitting
- expose an accessible name, role, description, status announcements, and control labels
- support keyboard-only operation and screen readers
- avoid using color alone for listening, error, forbidden, or success state
- respect reduced-motion preferences

## 5. Input Methods

### 5.1 Text input

The assistant should accept short natural-language requests. The original text remains visible while the request is parsed, clarified, previewed, or rejected.

### 5.2 Voice input

Voice is an input convenience, not a separate command channel.

Required sequence:

1. user explicitly starts listening
2. the UI visibly indicates listening
3. captured speech is transcribed
4. the transcript is shown as editable text
5. the user confirms or modifies the transcript
6. only the visible transcript proceeds to parsing

Voice capture must not implicitly submit, confirm, or write. The microphone must stop when the user stops it, closes the assistant, or the capture fails.

This baseline does not choose a speech provider, browser speech API, server transcription service, AI model, or paid vendor.

## 6. First Use Cases

### 6.1 Candidate Vendor Work Entry

Input:

> 星旭，室內放樣，8人

Candidate parse:

- intent: create Vendor Work Entry draft
- vendor: 星旭
- work content: 室內放樣
- headcount: 8
- unresolved required context: business date, sheet, and any other canonical required field not deterministically supplied by trusted page/session context

The result is a candidate structured draft, not a write. If more than one `星旭` target or sheet relationship exists in authorized scope, the assistant must ask for clarification.

### 6.2 Candidate progress change

Input:

> 19樓 A1，星旭，室內放樣已完成

Candidate parse:

- floor: 19樓
- unit: A1
- vendor/task hint: 星旭／室內放樣
- intended transition: current value `X` → candidate value `O`

Before preview, the runtime must resolve exactly one persisted unit and exactly one task on the same authorized sheet. The preview must show the current value and proposed value. If the current value is already `O`, the UI must report no change rather than manufacturing a second successful update.

### 6.3 Read-only query examples

> 今天有哪些廠商還沒進場？

> 19樓還有哪些工項未完成？

The assistant must define terms such as “還沒進場” by mapping them to an existing authorized field/read-model contract. If no frozen field or decision contract supports the term, it must explain the ambiguity and ask the user to choose a supported meaning. It must not invent attendance or entry facts.

### 6.4 Role boundary

- site members may query and propose supported actions only inside their current site, current sheet, membership, and route-specific action permission
- vendors may query only their own authorized business data and may create/modify only their own data through a vendor-compatible canonical path
- admins remain constrained by existing global role plus current-site, sheet, target, and action authorization; AI does not broaden admin powers

## 7. Controlled Write Flow

Every future AI-assisted write must follow this sequence:

```text
User input
  → AI parses intent
  → server resolves exactly one target
  → existing authorization is executed
  → structured preview is displayed
  → user explicitly confirms
  → existing canonical write path is called
  → canonical result is displayed
  → audit evidence is written
```

### 7.1 Required separation

- parsing proposes an intent; it does not authorize
- target resolution uses persisted IDs and relationships; it does not trust labels alone
- authorization runs after target resolution and again at write time
- preview is not authority; on confirmation the server must re-resolve the target, validate actor identity and current-site/sheet lineage, execute action-specific authorization, and verify that current data still matches the preview
- preview is derived from server-resolved current state
- confirmation applies only to the exact preview version shown
- any target, value, actor, site, sheet, permission, or current-state change invalidates the preview and requires re-resolution/reconfirmation
- success is shown only from the canonical write response after commit
- the AI response itself is never write-success evidence

### 7.2 Structured preview minimum

The preview must show:

- intended action
- actor identity and role in human-readable form
- current site and sheet
- resolved target IDs plus human-readable floor/unit/vendor/task/entry labels
- current value or “new record”
- proposed value
- fields that will not change
- confirmation requirement
- any irreversible or follow-on consequence already defined by the canonical contract

The confirmation control must state the action, for example `確認將 A1／室內放樣由 X 改為 O`, rather than a generic `OK`.

### 7.3 Prohibited behavior

- AI directly connects to or modifies the database
- bypassing existing API/service authorization
- writing without explicit confirmation
- guessing a floor, unit, vendor, task, entry, site, or sheet
- cross-site operation
- vendor access to another vendor's data
- expanding admin authority because the request is made through AI
- treating an AI response as proof of persistence
- silently changing the request after preview

## 8. Permission Matrix

“Draft” in this matrix means an assistant-local, non-persisted structured preview. It is not a database record. A “write intent” is only a proposal until target resolution, authorization, preview, confirmation, canonical write, and audit all succeed.

| Role | Authorized queries | May create assistant-local draft | Candidate write intents | Required confirmation | Forbidden scope |
| --- | --- | --- | --- | --- | --- |
| Site member | Current authorized site/sheet reads exposed by existing crew/grid/Work Hub/read-model contracts | Yes, for one uniquely resolved supported action | Single Vendor Work Entry create/update where current route permission permits; single progress `X/O`; single unit-extra update; single requirement confirmation or formal approval only where the existing action contract permits | Visible structured preview and action-specific explicit confirmation; authorization rerun at submission | Other sites/sheets; admin maintenance; vendor identity impersonation; ambiguous or bulk targets; permissions/schema; unsupported workflow override |
| Vendor | Only business data belonging to the authenticated vendor identity and exposed by vendor-authorized reads | Yes, limited to own data | Create/modify one own Vendor Work Entry only after a vendor-compatible canonical write path is confirmed; no crew-side confirmation/approval | Editable transcript/text, own-vendor structured preview, explicit confirmation, canonical vendor identity recheck at submission | Other vendors; crew/admin reads; progress/unit-extra; requirement confirmation; formal approval; scheduling authority; cross-site inference; any internal-only route |
| Admin | Existing admin-authorized reads, still scoped to the active current site/sheet where the contract requires it | Yes, for one uniquely resolved supported action | Only actions already available to admin through an actor-compatible canonical path; initial AI baseline does not add admin CRUD, reset, permission, or override intents | Same explicit preview/confirmation as other roles; existing stronger confirmation such as password re-entry remains mandatory where already required | Cross-current-site mutation; permission expansion; hidden maintenance/reset/bulk behavior; schema or user/role administration through AI; bypass of stronger existing confirmation |
| Future 工區管理部 | None in this baseline | No | None | Not applicable | Entire role is disabled; extension point only until a separate role, permission, read, write, and governance baseline is approved |

The first implementation must maintain an explicit allowlist keyed by authenticated identity type, effective role, intent, canonical action, and target scope. Unknown roles or intents are denied by default.

## 9. Ambiguity And Safety

### 9.1 Unique resolution rule

If resolution finds zero or multiple matching vendors, floors, units, tasks, fields, sheets, or entries, the assistant must not write.

- zero matches: explain that no authorized target was found and allow correction
- multiple matches: list the minimum safe distinguishing information and request clarification
- one match: continue to server authorization and preview

The assistant must not rank alternatives and silently select the highest-scoring target for a write.

### 9.2 Clarification rule

Clarification must be narrow and must not leak inaccessible data. For example, a vendor must not receive other vendor names merely because those names were candidate matches outside vendor scope.

After clarification, target resolution and authorization start again from trusted context.

### 9.3 Retry and idempotency

Repeated voice segments, double taps, network retries, browser resubmission, and delayed responses can repeat an intent. Future confirmed writes require:

- a server-issued preview/version token bound to actor, site, sheet, intent, target, proposed value, and expiry
- a unique idempotency key bound to one confirmation
- deterministic handling of an already-completed, rejected, expired, or changed request
- no second mutation when the canonical result is already known
- safe reconciliation of the displayed result with the canonical read state, without assuming a general reconciliation subsystem exists today

Existing domain uniqueness or idempotent behavior may remain the final domain guard, but it does not replace the AI-level confirmation/idempotency record.

### 9.4 Required audit evidence

Before any confirmed AI write is production-enabled, durable audit evidence must include at least:

- actor identity and effective role
- site and sheet
- input mode and the confirmed visible text/transcript
- normalized intent
- resolved target identity
- before and after values
- preview/version token reference
- confirmation timestamp
- canonical action/path identifier
- request/idempotency key
- final timestamp and result category
- canonical success/failure reference sufficient to investigate the action

Sensitive voice audio should not be retained by default. Any future audio or transcript retention requires a separate policy for retention period, consent, access, and deletion.

Audit coverage must include confirmed attempts, rejected/forbidden outcomes, stale previews, duplicate/idempotent replays, and the canonical write result, not only successful writes. Existing audit-adjacent fields are not sufficient evidence for production AI writes.

### 9.5 Explicitly excluded risk classes

The following are out of scope:

- bulk write
- cross-floor or multi-floor mass update
- delete
- sheet reset
- permission or role management
- schema or migration operations
- maintenance mode actions
- override or bypass actions

## 10. UI States

| State | Meaning | Allowed user action | Exit/transition guard |
| --- | --- | --- | --- |
| Closed | Assistant is not displayed | Open AI entry | Opening moves focus into shell |
| Open / idle | Ready for text or voice | Type, start listening, close | No implicit request |
| Listening | Microphone capture is active | Stop/cancel listening | No parsing or submission from audio directly |
| Transcribing | Audio is becoming visible text | Cancel/close | Must end with visible editable transcript or error |
| Parsing | Confirmed visible input is classified | Cancel if safe | Produces clarification, preview candidate, read result, forbidden, or error |
| Needs clarification | Target/meaning is missing or non-unique | Supply/edit details | Must restart resolution; no write control |
| Preview | Exact authorized target and proposed before/after are shown | Edit, cancel, proceed to confirm | Stale or changed context invalidates preview |
| Confirming | User is making the explicit final decision | Confirm exact action or cancel | Generic consent is insufficient |
| Submitting | Canonical write and audit outcome are pending | Wait; prevent duplicate submit | Do not report success early; retry is idempotency-controlled |
| Success | Canonical write committed and audit evidence recorded | Review result, close, start new request | Refresh relevant read state from canonical result/read path |
| Rejected / forbidden | Validation, gate, or authorization denies action | Review reason, edit, close | Never offer a bypass; do not leak inaccessible targets |
| Error / retry-safe | Transient or unknown failure with no unambiguous success evidence | Retry using same idempotency key, reconcile, or cancel | Never issue a new mutation merely to discover whether the first succeeded |

### 10.1 State flow

```text
Closed
  → Open / idle
      ├─ text ───────────────────────────────┐
      └─ Listening → Transcribing → edit ────┤
                                              ↓
                                           Parsing
                       ┌──────────────────────┼─────────────────────┐
                       ↓                      ↓                     ↓
             Needs clarification          read result     Rejected / forbidden
                       │
                       └─ revised input → Parsing

Parsing → Preview → Confirming
                      ├─ cancel → Open / idle
                      └─ confirm → Submitting
                                      ├─ Success
                                      ├─ Rejected / forbidden
                                      └─ Error / retry-safe
```

Close from any non-submitting state returns to `Closed` and restores focus. If submission cannot safely be cancelled, closing may hide the shell but must not manufacture a result; reopening must reconcile by the same idempotency key.

## 11. Future Slice Decomposition

### AI-UX-001B — Floating AI Entry and Modal Shell Baseline

- add only the accessible floating entry and responsive shell
- define desktop modal/right-drawer choice and mobile bottom sheet
- keyboard, focus trap, focus restore, Escape, close button, accessible naming, live-region, safe-area, print, and reduced-motion guardrails
- no AI model, voice capture, query, or write behavior
- add no AI SDK, model call, API, database/schema change, or persistent write
- any text field is local UI state only; any microphone control is disabled and explicitly marked as future functionality
- production UI must clearly state that AI data handling is not enabled and must not imply that requests are being processed

### AI-READ-001 — Role-Scoped Read-only Query Baseline

- consume only existing authorized read contracts
- define supported read intents and terminology mappings
- preserve current-site, sheet, vendor identity, and Work Hub business-rule boundaries
- add no write capability

### AI-INTENT-001 — Text Intent Parsing and Structured Preview

- define an allowlisted structured intent schema
- parse text into candidates without executing writes
- implement unique target resolution and clarification
- produce non-persisted structured previews
- model/provider selection remains a separate procurement/security decision if still unresolved

### AI-VOICE-001 — Voice Transcript Capture Baseline

- explicit microphone start/stop and permission UX
- visible editable transcript before parsing
- accessibility, timeout, cancellation, failure, privacy, and unsupported-browser behavior
- no voice-triggered confirmation or automatic write

### AI-AUDIT-001 — AI Action Audit and Idempotency Guardrail

- define and implement durable AI action evidence
- bind preview/version tokens and idempotency keys to actor/scope/intent/target/value
- define duplicate, stale, expired, ambiguous-result, and retry-safe contracts
- this slice is a prerequisite for production-enabling confirmed AI writes

### AI-WRITE-001 — Confirmed Canonical Write Baseline

- allow only a minimal, explicitly approved single-target write intent
- rerun authorization at submission
- call only the actor-compatible canonical write path
- prove preview/confirmation fidelity, success evidence, failure non-mutation, audit, and idempotency
- must not be production-enabled before `AI-AUDIT-001` guardrails are available

Recommended implementation order:

1. `AI-UX-001B`
2. `AI-READ-001`
3. `AI-INTENT-001`
4. `AI-VOICE-001`
5. `AI-AUDIT-001`
6. `AI-WRITE-001`

Each slice requires its own design/contract, regression guardrail, baseline, and production review appropriate to its risk.

## 12. Explicit Out-of-Scope

This slice does not:

- modify production code
- modify templates, CSS, JavaScript, Python, or tests
- add an AI SDK or dependency
- add a secret or environment variable
- add an API
- add schema or migration
- change permission, workflow, authorization, or write behavior
- implement text input
- implement voice input
- add a clickable AI button
- modify the frozen `M4-IMP-004A` scope
- select an AI model, speech provider, browser API, or paid vendor
- update `docs/ROADMAP.md` or `docs/production_baselines.md`

Any roadmap index update, if desired, must be reviewed and authorized as a separate explicit documentation change.

## 13. Design Acceptance Criteria

This design baseline is ready for review when reviewers agree that:

- AI is an interaction entry over existing authority, not a new authority
- the floating entry placement and responsive shell behavior are clear
- text and voice both require visible user-controlled input
- read and write paths remain separated
- every write requires unique resolution, existing authorization, structured preview, explicit confirmation, canonical write, canonical result, and audit evidence
- the permission matrix fails closed for site member, vendor, admin, and the disabled future role
- ambiguity, cross-site, cross-vendor, bulk, retry, and idempotency risks are explicit
- the state flow includes accessible, forbidden, error, and retry-safe outcomes
- future slices keep UI shell, read, intent, voice, audit, and write capability independently reviewable
- this file is the only repository change in `AI-UX-001A`
