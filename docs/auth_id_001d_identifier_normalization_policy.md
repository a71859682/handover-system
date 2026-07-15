# AUTH-ID-001D — Identifier Normalization Policy

Status: policy design baseline

Scope: docs-only

Implementation status: not started

## 1. Baseline and purpose

- Canonical repository: `C:\Users\耀祥\Documents\handover-system-formal`
- Design worktree base: `origin/develop`
- Frozen local / origin `main`: `50abaa5f40f2e51972392e4d1943f672ad714af7`
- Frozen local / origin `develop`: `50abaa5f40f2e51972392e4d1943f672ad714af7`
- Frozen Production: `50abaa5f40f2e51972392e4d1943f672ad714af7`
- AUTH-ID-001C: Production Frozen
- Known canonical-repository untracked file, preserved and excluded from this worktree: `.codex/environments/environment.toml`

This document freezes the target identifier-normalization policy for the future Global Identity Registry. It separates raw alias preservation from recognition comparison, defines collision and version boundaries, and identifies the evidence required before schema work. It does not change usernames, schema, login behavior, session authority, or runtime.

## 2. Current-state accuracy

Current behavior remains backend-local and unchanged:

- Internal and vendor credential backends are separate.
- Internal `POST /login` reads `username` and applies Python `strip()` at the request boundary.
- Vendor `POST /vendor/login` reads `username` and applies Python `strip()` at the request boundary; vendor verification also applies `strip()` before lookup.
- Stored usernames preserve their existing case and Unicode text.
- Internal lookup uses backend-local exact equality: `users.username = supplied_value`.
- Vendor lookup uses backend-local exact equality: `vendor_accounts.username = supplied_value`.
- There is no global normalization key.
- There is no global identifier namespace or global uniqueness constraint.
- AUTH-ID-001B observed zero exact, `NFC(strip).casefold`, and `NFKC(strip).casefold` collisions in DEV and Production. That evidence is not a normalization policy and does not prove future safety.
- None of the target behavior in this document is implemented current behavior.

## 3. Identity and authority boundary

### 3.1 Raw alias

Frozen policy:

- Preserve the username text supplied by the user or source backend as the raw alias.
- Raw alias supports display, audit, source fidelity, and backward compatibility.
- Raw alias is not a `GlobalIdentity` primary key.
- Raw alias is not a credential and is not authorization authority.
- Normalization must not overwrite an existing backend username.
- Rename, retirement, alias history, and replacement lifecycle belong to later schema and workflow slices.

### 3.2 Normalized lookup key

Frozen policy:

- A normalized lookup key is derived only for registry recognition candidate lookup.
- It is not a credential, identity primary key, or authorization authority.
- It must not be copied into a session as write authority.
- It may resolve to zero, one, or multiple `GlobalIdentity` candidates.
- Password verification remains confined to one already-selected canonical credential backend.
- Cross-backend password fallback is forbidden.

Recognition is therefore a candidate-discovery step, not authentication or authorization.

## 4. Candidate algorithm comparison

The comparison input below is a raw alias value. `strip()` means Python's Unicode-aware boundary trim. No candidate removes or collapses internal characters.

| Option | Pipeline | Backward compatibility | Collision expansion | Unicode behavior | Determinism / drift | Rollback and security boundary | AUTH-ID-001B correspondence |
|---|---|---|---|---|---|---|---|
| A. Exact trimmed value | `value.strip()` | Closest to current request handling and exact backend lookup; preserves case and compatibility distinctions | Lowest expansion beyond boundary whitespace | No canonical-equivalence, compatibility, or case folding | Simple, but Python whitespace tables remain runtime-defined | Easy comparison with current lookup; poor recognition across equivalent spellings and does not address spoofing | Exact trimmed evidence corresponds only to the exact-analysis family |
| B. NFC + casefold | `NFC(value.strip()).casefold()` | Preserves compatibility-character distinctions while accepting canonical equivalents and case variants | Expands collisions for case, canonical equivalents, `ß` / `SS`, and sigma forms | Canonical equivalence and locale-independent case folding; no compatibility folding | Depends on Unicode data version; output after casefold is not guaranteed normalized | Requires collision quarantine and versioned reindex; does not solve homoglyph spoofing | Exactly matches the 001B `NFC(strip).casefold()` analysis |
| C. NFKC + casefold | `NFKC(value.strip()).casefold()` | More aliases compare equal, including many compatibility forms; greater departure from current exact lookup | Expands collisions for case, canonical and compatibility equivalents | Adds compatibility folding, including full-width forms; output after casefold is not guaranteed normalized | Depends on Unicode data version | Greater reindex and rollback risk; still does not solve cross-script confusables | Exactly matches the 001B `NFKC(strip).casefold()` analysis |
| D. Versioned NFKC_Casefold-style pipeline | boundary trim → `NFKC` → `casefold()` → final `NFKC` | Preserves raw alias while giving stable comparison semantics in a separately versioned key | Same broad collision classes as C, with a final normalized representation | Canonical and compatibility folding plus locale-independent case folding; final NFKC repairs decompositions introduced by casefold | Deterministic only when the policy version, implementation, and Unicode data version are recorded | Requires dry-run, collision quarantine, compatibility window, rollback, and reconciliation; does not remove spoofing risk | Does **not** exactly match 001B because 001B omitted the final NFKC step |

### 4.1 Chosen recognition comparison policy

The single recommended target policy is Option D. This document freezes both:

- the logical algorithm family: `NFKC_CASEFOLD_V1`
- the active, non-drifting conformance profile: `NFKC_CASEFOLD_V1_UCD16_0_0`

`NFKC_CASEFOLD_V1_UCD16_0_0` is the approved active profile for future recognition-key generation and conformance evidence. It freezes:

- boundary-trim semantics: the approved Python `3.14.6` / Unicode `16.0.0` `str.strip()` behavior as the V1 trim baseline
- first normalization step: `unicodedata.normalize("NFKC", value)`
- case step: locale-independent `casefold()`
- final normalization step: `unicodedata.normalize("NFKC", value)`
- synthetic conformance vector set in this document
- normative synthetic output expectations derived from that vector set

Normative pseudocode for the active profile:

1. Apply the pinned V1 boundary-trim semantics, conformant with Python `3.14.6` / Unicode `16.0.0` `str.strip()`.
2. Reject an empty-after-trim value as invalid input.
3. Apply `unicodedata.normalize("NFKC", value)`.
4. Apply locale-independent `casefold()`.
5. Apply final `unicodedata.normalize("NFKC", value)`.

If any step above cannot be reproduced exactly for the active profile, the implementation must not generate or mutate lookup keys under that profile.

The logical algorithm family is frozen here. Its physical schema representation is deferred, but the active profile semantics and their Unicode / trim baseline are not allowed to drift with later runtimes.

Option D is selected because raw storage remains untouched while recognition gets explicit compatibility, canonical-equivalence, case, and final-normal-form semantics. It is not a confusable detector and must not be treated as identity proof.

AUTH-ID-001B used `NFKC(strip).casefold()` without final NFKC. Its zero-collision result cannot be treated as complete live-data proof for `NFKC_CASEFOLD_V1_UCD16_0_0`. Exact-profile read-only evidence is required before schema work.

## 5. Whitespace policy

Frozen rules:

- Leading and trailing whitespace is removed using the pinned V1 boundary-trim semantics approved by this document.
- ASCII and recognized Unicode boundary whitespace are treated consistently by that boundary step.
- Internal whitespace is preserved exactly.
- Repeated internal whitespace is not collapsed.
- Empty-after-trim input is invalid and produces no recognition candidate.
- Normalization must not silently remove internal whitespace or any other internal character.
- Existing stored usernames are not rewritten in this slice.
- Python `3.14.6` / Unicode `16.0.0` `str.strip()` behavior is the V1 conformance baseline for boundary trimming.
- V1 trim semantics must not drift automatically with a later Python or Unicode runtime.
- Implementations must pass versioned trim conformance vectors before generating keys for the active profile.
- If a runtime produces a different trim result, it must either fail closed for the active profile or use a compatibility implementation that reproduces the approved V1 trim semantics exactly.
- Adopting a different trim behavior requires a new normalization profile / version rather than silent reuse of the existing profile name.

## 6. Unicode security policy

### 6.1 Equivalence handled by the chosen key

- NFKC handles canonical and compatibility normalization before case comparison.
- `casefold()` provides locale-independent case folding rather than locale-sensitive lowercasing.
- Final NFKC restores a normalized representation after casefold expansion.
- Composed and decomposed accents may compare equal.
- Full-width compatibility characters may compare equal to their ASCII forms.
- German `ß` may compare equal to `SS`.
- Greek medial and final sigma forms may compare equal after casefold.
- Turkish `I` and `i` compare equal, while dotted `İ` and dotless `ı` remain distinct under this locale-independent policy unless their exact transformed values match another alias.

These equivalences create recognition candidates only. They do not prove that two raw aliases belong to the same human or actor.

### 6.2 Characters and risks not erased by normalization

- Canonical normalization must not silently delete zero-width or other format characters.
- Control-character and format-character validation, including legacy-data handling, requires a separate design slice.
- Until that validation policy is frozen, implementation must not silently repair, strip, merge, or authorize based on such characters.
- Cross-script homoglyphs and visually confusable text are not canonical equality.
- A confusable skeleton must not become the canonical equality key without a separate security assessment.
- Visually similar aliases do not imply the same identity.
- Any ambiguity or risk state must not auto-link, auto-merge, or select an actor.

## 7. Synthetic test-vector evidence

This evidence was generated only from synthetic strings with Python stdlib `unicodedata`; it used no file, database, username sample, or runtime account data.

- Python: `3.14.6`
- `unicodedata.unidata_version`: `16.0.0`
- Escapes such as `\u200b` show code points explicitly so invisible characters are auditable.
- A = exact trimmed, B = NFC + casefold, C = NFKC + casefold, D = chosen final-NFKC pipeline.
- These vectors are part of the active profile conformance baseline for `NFKC_CASEFOLD_V1_UCD16_0_0`.
- Their code-point outputs are normative evidence for active-profile conformance.
- Any runtime upgrade must rerun this vector set and compare outputs against the pinned profile expectations.
- If any normative output differs, the implementation is not conformant with the existing active profile and must not continue writing keys under that profile name.
- A mostly-matching vector set is insufficient; any normative mismatch requires fail-closed behavior, an exact compatibility implementation, or a new profile / version.

| Synthetic vector | Input | A output | B output | C output | D output |
|---|---|---|---|---|---|
| ASCII case lower | `Sample` | `Sample` | `sample` | `sample` | `sample` |
| ASCII case upper | `SAMPLE` | `SAMPLE` | `sample` | `sample` | `sample` |
| Leading / trailing ASCII whitespace | `  Sample  ` | `Sample` | `sample` | `sample` | `sample` |
| Unicode boundary whitespace | `\u2003Sample\xa0` | `Sample` | `sample` | `sample` | `sample` |
| Internal single whitespace | `Sample Name` | `Sample Name` | `sample name` | `sample name` | `sample name` |
| Internal repeated whitespace | `Sample  Name` | `Sample  Name` | `sample  name` | `sample  name` | `sample  name` |
| Full-width Latin | `\uff33\uff41\uff4d\uff50\uff4c\uff45` | same as input | `\uff53\uff41\uff4d\uff50\uff4c\uff45` | `sample` | `sample` |
| Composed accent | `Caf\xe9` | `Caf\xe9` | `caf\xe9` | `caf\xe9` | `caf\xe9` |
| Decomposed accent | `Cafe\u0301` | `Cafe\u0301` | `caf\xe9` | `caf\xe9` | `caf\xe9` |
| German sharp s | `Stra\xdfe` | `Stra\xdfe` | `strasse` | `strasse` | `strasse` |
| German SS | `STRASSE` | `STRASSE` | `strasse` | `strasse` | `strasse` |
| Greek capital sigma | `\u039f\u03a3` | same as input | `\u03bf\u03c3` | `\u03bf\u03c3` | `\u03bf\u03c3` |
| Greek medial sigma | `\u03bf\u03c3` | same as input | `\u03bf\u03c3` | `\u03bf\u03c3` | `\u03bf\u03c3` |
| Greek final sigma | `\u03bf\u03c2` | same as input | `\u03bf\u03c3` | `\u03bf\u03c3` | `\u03bf\u03c3` |
| Turkish Latin I | `I` | `I` | `i` | `i` | `i` |
| Turkish Latin i | `i` | `i` | `i` | `i` | `i` |
| Turkish dotted capital I | `\u0130` | same as input | `i\u0307` | `i\u0307` | `i\u0307` |
| Turkish dotless i | `\u0131` | same as input | `\u0131` | `\u0131` | `\u0131` |
| Zero-width format present | `ab\u200bcd` | same as input | same as input | same as input | same as input |
| Zero-width format absent | `abcd` | `abcd` | `abcd` | `abcd` | `abcd` |
| Latin homoglyph sample | `papa` | `papa` | `papa` | `papa` | `papa` |
| Cyrillic homoglyph sample | `\u0440\u0430\u0440\u0430` | same as input | same as input | same as input | same as input |
| Compatibility ligature | `\ufb03` | `\ufb03` | `ffi` | `ffi` | `ffi` |
| Expanded ligature | `ffi` | `ffi` | `ffi` | `ffi` | `ffi` |
| NFKC / casefold composition | `\u01f0` | `\u01f0` | `j\u030c` | `j\u030c` | `\u01f0` |
| Decomposed caron | `j\u030c` | `j\u030c` | `j\u030c` | `j\u030c` | `\u01f0` |

### 7.1 Collision and distinction results

- A collides only the unpadded `Sample` value with its ASCII- and Unicode-boundary-whitespace variants in this vector set.
- B collides ASCII case and boundary variants; composed / decomposed accent; `ß` / `SS`; Greek sigma forms; `I` / `i`; compatibility ligature / expanded text; and the caron pair.
- C has all B collision groups and additionally folds the full-width Latin vector into `sample`.
- D has the same synthetic collision groups as C, but the caron group ends in normalized `\u01f0` instead of decomposed `j\u030c`.
- Internal single and repeated whitespace remain distinct under every option.
- Turkish dotted `\u0130` and dotless `\u0131` remain distinct from plain `i` except that plain `I` and `i` collide.
- Zero-width-present and zero-width-absent vectors remain distinct.
- Latin `papa` and visually similar Cyrillic `\u0440\u0430\u0440\u0430` remain distinct.

These are synthetic algorithm observations, not live-data conclusions.

## 8. Collision contract

Frozen rules:

- A normalized key may resolve to zero, exactly one, or multiple `GlobalIdentity` candidates.
- A normalized key must not be assumed globally unique.
- A collision must not auto-link, auto-merge, select a backend, or select an actor.
- A collision must not establish an authority-bearing session.
- Outward responses must not disclose account count, account type, backend type, site, vendor organization, or trusted target.
- Import or backfill collisions must enter a quarantine / ambiguous workflow.
- The current observed collision count of zero does not relax any guardrail.
- Password verification must not be used as cross-backend collision resolution.

## 8.1 Invalid, unsupported, and ambiguous no-fallback rule

The following states must all fail closed:

- empty-after-trim
- normalization exception
- unsupported normalization profile
- failed conformance check
- invalid control / format policy state
- ambiguous candidate result

For any such state:

- return only a generic invalid / unavailable / ambiguous result
- do not create recognition-candidate authority
- do not create a session
- do not execute password verification
- do not fall back to exact lookup
- do not fall back to another normalization version
- do not switch to or attempt another credential backend
- do not guess an older backend-local rule path

## 9. Version and upgrade boundary

Frozen rules:

- Every normalized lookup key must be attributable to explicit logical provenance.
- `NFKC_CASEFOLD_V1` identifies the logical algorithm family selected in this document.
- `NFKC_CASEFOLD_V1_UCD16_0_0` is the frozen active normalization profile for this document.
- The same active profile must never produce different outputs because Python or Unicode data changed.
- Existing keys retain the provenance of the profile under which they were generated.
- Future normalized-alias records must be able to identify:
  - algorithm family / version
  - Unicode data version
  - boundary-trim profile
  - key-generation / conformance profile
- Python patch or runtime version may be recorded as execution evidence metadata, but it is not by itself the normative identity of a normalization profile.
- If an implementation cannot reproduce the active profile exactly, new key generation must fail closed.
- If an implementation cannot reproduce the active profile exactly, alias mutation or backfill under that profile must fail closed.
- Unsupported-runtime behavior must not fall back to exact lookup, another normalization version, another backend, or guessed legacy behavior.
- A policy or Unicode-version upgrade must not perform an in-place, unproven recomputation.
- Adopting a new Unicode data version requires a new normalization profile / version rather than reuse of the existing active-profile name.
- Every upgrade requires an isolated read-only dry-run, old/new collision comparison, rollback plan, compatibility window, and post-deploy reconciliation.
- Every upgrade must report newly-colliding and newly-distinct aggregates before approval.
- Recognition compatibility across versions may use only a formally designed, version-aware path.
- A normalization upgrade must not share a slice with an authority switch.
- A normalization upgrade must not overwrite old keys in place under the old profile identity.
- Upgrade and rollback planning must not assume hot-maintenance identity merge capability or uninterrupted safe writes across old and new key versions.
- The physical columns, types, indexes, and constraints for version storage are not designed here.

## 10. Recommended decision summary

| Policy area | Frozen target decision |
|---|---|
| Raw-storage policy | Preserve source raw alias exactly for display, audit, and compatibility; do not rewrite backend username |
| Logical algorithm family | `NFKC_CASEFOLD_V1` |
| Active normalization profile | `NFKC_CASEFOLD_V1_UCD16_0_0` |
| Recognition comparison policy | Pinned boundary trim → NFKC → casefold → final NFKC under the active profile |
| Collision policy | Zero / one / many candidates; many is ambiguous and fail-closed; never auto-link or create authority |
| Version policy | Record logical provenance for algorithm family, Unicode data version, boundary-trim profile, and conformance profile; upgrades require isolated dry-run, collision comparison, rollback, compatibility, and reconciliation |
| Pinned Unicode / trim semantics | Unicode data `16.0.0` plus the approved Python `3.14.6` / Unicode `16.0.0` boundary-trim conformance baseline |
| Conformance rule | Synthetic vector outputs and trim behavior are normative for the active profile; mismatch means the runtime is not conformant with that profile |
| Unsupported-runtime behavior | Fail closed for key generation, alias mutation, and backfill unless an exact compatibility implementation reproduces the active profile |
| New-version creation rule | Any adopted trim or Unicode-data change requires a new normalization profile / version and must not reuse the old profile name |
| Alias provenance requirements | Future normalized-alias records must identify algorithm family, Unicode data version, boundary-trim profile, and key-generation / conformance profile |
| Legacy compatibility policy | Existing exact backend usernames remain canonical credential lookup data until separately migrated; raw aliases remain available |
| New-alias validation policy | Empty-after-trim is invalid; no silent internal-character removal; invalid / unsupported / ambiguous states fail closed and must not fall back to exact lookup or another backend |
| Unresolved items | Exact live-data proof, physical version representation, legacy lifecycle, control / format handling, collision UX, recognition consumption, and upgrade operations remain separately owned |

## 11. Required next evidence and sequencing

The mandatory next slice is:

`AUTH-ID-001D1 — Exact Normalization Runtime Evidence`

It must:

- remain read-only and aggregate-only
- output no identifier or account sample
- execute the exact `NFKC_CASEFOLD_V1_UCD16_0_0` active profile, including pinned boundary trim, first NFKC, locale-independent casefold, and final NFKC
- record the implementation and Unicode versions used to prove conformance
- prove conformance against the synthetic vector baseline for the active profile
- evaluate DEV and Production separately
- prove no database write
- create no schema
- report raw exact collision groups as aggregates without disclosing identifiers
- report AUTH-ID-001B C-algorithm collision groups as aggregates without disclosing identifiers
- report selected D-profile collision groups as aggregates without disclosing identifiers
- report zero / one / multiple candidate key distributions
- report newly-colliding groups for D relative to AUTH-ID-001B C
- report newly-distinct groups for D relative to AUTH-ID-001B C
- report affected internal-row aggregates
- report affected vendor-row aggregates
- report maximum group size
- report invalid / empty-after-trim aggregate counts
- report control / format risk aggregates

If the runtime cannot reproduce the approved active profile exactly, AUTH-ID-001D1 must report `BLOCKED` and must not substitute a newer runtime result as evidence for the frozen profile.

Only after AUTH-ID-001D1 completes may `AUTH-ID-001E — Registry Schema Baseline` begin. AUTH-ID-001D1 must not implement schema or authority behavior.

## 12. Deferred decisions and owners

| Decision | Owner slice | Why deferred | Frozen invariant |
|---|---|---|---|
| Exact normalization algorithm rollout eligibility | `AUTH-ID-001D1` | The active profile is frozen here, but live-data rollout still needs exact-profile aggregate evidence, conformance proof, and drift-safe runtime validation. | Evidence must use `NFKC_CASEFOLD_V1_UCD16_0_0` exactly, remain read-only, report newly-colliding and newly-distinct aggregates, and must not weaken ambiguous-candidate handling. |
| Normalization version identifier representation | `AUTH-ID-001E` | The logical provenance requirements are frozen here, while physical storage representation depends on the independently reviewed registry schema. | Version provenance must be explicit and queryable; alias text must not become identity primary key; schema must not perform backfill. |
| Legacy alias handling | `AUTH-ID-001F` | Rename, retirement, compatibility, and history states require lifecycle semantics after schema shape is frozen. | Existing backend username must not be silently rewritten or cease being canonical credential lookup data before a controlled migration. |
| Invalid control / format character handling | `AUTH-ID-001D2` | Category-specific reject, quarantine, and legacy exceptions need separate evidence and UX review; normalization alone is not validation. | No silent deletion or repair; risk state must not auto-link, authenticate, or authorize. |
| Alias lifecycle | `AUTH-ID-001F` | Creation, activation, retirement, replacement, and history ownership depend on registry lifecycle state design. | Retired or historical alias must not silently retain or create authority; raw audit history must remain attributable. |
| Collision resolution UX | `AUTH-UX-001B` | User interaction for ambiguous recognition depends on the frozen collision state but can be designed without changing the normalization key. | UX must not reveal candidate count/type/backend/site/vendor/target and must not establish authority before resolution and authentication. |
| Schema representation | `AUTH-ID-001E` | Physical records, types, indexes, and constraints follow the frozen provenance model and exact-profile evidence. | Schema must preserve raw alias separately from versioned lookup key and must not impose an unproven global unique key. |
| Recognition API consumption | `AUTH-READ-001` | API shape depends on registry schema and collision semantics, while this slice only freezes comparison policy. | Recognition remains read-only and non-authoritative, creates no session, and leaks no account or target existence detail. |
| Normalization upgrade workflow | `AUTH-ID-001H` | Operational dry-run, dual-version compatibility, cutover, rollback, reconciliation, and active-profile succession need a dedicated deployment design after schema exists. | Upgrade must not recompute in place without evidence, must not reuse an old profile name for new Unicode behavior, and must not share a slice with authority switch. |

Every deferred decision has an owner, a concrete deferral reason, and an invariant that later work must preserve.

## 13. Out of scope

Explicitly excluded:

- changes to `app.py`, tests, templates, or static assets
- backend username modification or repair
- schema, migration, DDL, physical column, index, or constraint design
- backfill, data cleanup, or identity merge
- global unique identifier constraint
- password, hash, credential, or credential-backend change
- login route, recognition API, session, UI, or routing implementation
- database, DEV, or Production operation
- `vendor_id` implementation
- authority switch
- AUTH-ID-001D1 or AUTH-ID-001E implementation

## 14. Review checklist

- Current `strip()` plus backend-local exact equality is described as current behavior; target normalization is not.
- Raw alias and normalized lookup key are separate, and neither is authorization authority.
- A / B / C / D are compared, with one policy selected.
- The chosen D pipeline includes final NFKC, has explicit logical family `NFKC_CASEFOLD_V1`, and has an explicit active profile `NFKC_CASEFOLD_V1_UCD16_0_0`.
- The trim, Unicode-data, and conformance baseline for the active profile are pinned and not runtime-drifting.
- The 001B evidence mismatch is explicit, and AUTH-ID-001D1 is mandatory before schema.
- Whitespace, Unicode, format/control, and confusable boundaries are explicit.
- Synthetic evidence records Python and Unicode versions and uses no live identifier.
- Unsupported runtime, invalid input, and ambiguous states fail closed without exact-lookup or cross-backend fallback.
- Collisions remain fail-closed and non-disclosing even when current observed count is zero.
- Version upgrades require dry-run, rollback, compatibility, and reconciliation and cannot share an authority-switch slice.
- All deferred decisions have owners and frozen invariants.
- No schema, migration, backfill, runtime, DB, API, session, UI, or authority change is included.
