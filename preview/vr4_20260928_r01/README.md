# 004F-VR4-PREVIEW/r01 deployment handoff

Status: **PREVIEW_BUILD_READY_PENDING_EXTERNAL_REVIEW**. This package verifies
only the new preview entry on local Windows loopback HTTP. Render deployment,
Linux/Gunicorn execution, and the built-in browser remain external review work.
There is no activation operation in this preview.

## Source and future resource identity

- Repository: `https://github.com/a71859682/handover-system.git`.
- Accepted baseline: `fd2aebe7c15168c6f2cd2a4567067c90d88e4196`;
  tree `4cd962302c4d83f7af8ea336d496fd922dc20aeb`.
- Local baseline branch: `feature/004f-vr4-vendor-registration`.
- Add only `preview/vr4_20260928_r01/{entry.py,fixture.py,smoke.py,README.md}`
  to a dedicated preview branch after external review. That branch has **not**
  been created or pushed by this build. Do not deploy the original `app:app`
  Procfile: it bypasses the preview isolation contract.
- Future Render workspace: `tea-d8vmr4ok1i2s73etn1tg`.
- Future service name: `handover-vr4-preview-20260928-r01`; native Python,
  Ohio (`ohio`), free, autoDeploy=`no`, repository root as working directory.
  No existing disk, database, environment group, or service is attached.
  Service ID, preview branch name, deployment ID and URL are not yet assigned.
- Unchanged Git blobs: requirements `e6dea551cf94fcbe849bba26597082c901c11822`;
  SQLite path resolver `77ce83bc3eba162802fe9b5808a95fd69b9e4716`.

## Exact build and start commands for external deployment

Build (existing requirements only):

```sh
python -m pip install -r requirements.txt
```

Start (one worker, one thread, no preload, debug or reload):

```sh
gunicorn preview.vr4_20260928_r01.entry:app --workers 1 --threads 1 --bind 0.0.0.0:$PORT --timeout 120 --access-logfile /dev/null --error-logfile - --log-level warning
```

Health-check path: `/preview/version`. Render supplies `PORT` and
`RENDER_GIT_COMMIT`; the latter must be a lowercase 40-character commit SHA.
The external deployment must confirm the requested Python runtime is available.
No Linux/Gunicorn execution or package installation occurred in this build.

| Non-secret environment name | Required Render value |
| --- | --- |
| `PYTHON_VERSION` | `3.14.6` (local validated Python version) |
| `PYTHONDONTWRITEBYTECODE` | `1` |
| `VR4_PREVIEW_MODE` | `004F-VR4-PREVIEW/r01` |
| `VR4_PREVIEW_RUNTIME` | `RENDER` |
| `VR4_PREVIEW_ROOT` | `/tmp/004f-vr4-preview-20260928-r01` |
| `APP_DB_PATH` | `/tmp/004f-vr4-preview-20260928-r01/fixture.sqlite3` |
| `DATABASE_URL` | empty string, explicitly present |
| `DUAL_WRITE_TABLES` | empty string, explicitly present |
| `USE_SQLALCHEMY_READS` | `false` |
| `USE_SQLALCHEMY_WRITES` | `false` |
| `USERS_READ_COMPARE` | `false` |
| `DUAL_WRITE_ENABLED` | `false` |
| `DUAL_WRITE_DRY_RUN` | `false` |
| `DUAL_WRITE_STRICT` | `false` |
| `FLASK_DEBUG` | `0` |
| `FLASK_TESTING` | `false` |

Secret/credential names only (no values are delivered):

- `VR4_PREVIEW_ADMIN_USERNAME`: separate temporary internal admin, 4–64
  characters matching `[a-z][a-z0-9._-]{3,63}`, never the reserved `admin` name.
- `VR4_PREVIEW_ADMIN_PASSWORD`: externally generate at least 32 random bytes
  encoded as URL-safe text; accepted length 24–128 with at least 12 distinct
  characters. No default or fallback password exists.
- `APP_SECRET_KEY`: independently generate at least 32 random bytes encoded
  as URL-safe text; accepted length 43–256 with at least 16 distinct characters.
  It must differ from the admin password. Store only as a service secret.

The strength checks cannot prove randomness: use a cryptographic generator.
Missing/weak credentials or missing/incorrect isolation values reject startup
before importing the original app. On an existing fixture, the supplied admin
identity/password must match; startup never silently rotates credentials.

## Fixture lifecycle and original behavior

The entry validates absolute containment, filename, platform, flags, credentials
and symlink/junction/hardlink exclusions first. It rejects the repository DB,
`/var/data`, arbitrary DB paths, unknown databases, incomplete fixtures, and
orphan SQLite journals. A startup lock prevents concurrent fixture initialization.
An unknown/partial database is retained and refused, never rebuilt over.

A new database gets only the identity and `excel_seeded` meta markers before
`app` import. Original bootstrap creates the original schema. An audit hook
rejects fallback SQLite connections and reads of repository `source.xlsx`.
The original roster service creates two wholly synthetic disabled vendors and
six assigned tasks on two synthetic active sites (three sheets). The original
bootstrap's empty default site remains inactive. No real roster fixture or Excel
data is imported. No previous test suite or test-client fixture is imported.

The framework's reserved default account keeps its name to prevent bootstrap
recreation, receives a discarded random password hash and `member` role, and has
no site permissions. Only the environment-supplied preview admin can log in.
Vendor accounts are created by the original `/vendor/register` route; they stay
inactive. Scope saving uses the original admin route, CSRF, signed snapshot,
authorization, transactions and services. Saving creates member/pending, not
owner or active membership. Organizations stay disabled and effective scope is 0.
`TESTING`, debug and reloader are not enabled. No session/current-user/response or
authorization monkeypatch is used.

The preview surface allows the original login/logout, vendor login/logout,
registration, pending-scope editor, site selection, `/sheet`, `/api/grid`, static
assets and the two read-only preview endpoints. Other paths return 404, including
`/admin/users`, `/admin/table`, `/api/reset-sheet`; links to those existing product
tools are outside this preview. No SQL, reset, activation or account-management
endpoint is added. Original product files and handlers are unchanged.

The free service uses ephemeral `/tmp` storage: a free-service restart/redeploy
can lose the fixture. If absent, a cold start creates a new synthetic fixture
and instance identity. If this identified fixture still exists, restart preserves
registrations/scopes. Requests within one boot never reset user actions.
Use the same secrets while that fixture exists. Do not copy it into any real DB.

## Browser review procedure for ChatGPT after deployment

1. Read `/preview/version`: verify baseline, actual `RENDER_GIT_COMMIT`, boot ID,
   fixture instance and `synthetic=true`. Locally the commit field is explicitly
   `LOCAL_SMOKE`. This response exposes no paths, credentials or request data.
2. In an anonymous browser context open `/vendor/register`. Use synthetic company
   `預覽合成甲有限公司`, tax ID `00000001`, a new lowercase vendor username, and
   a newly generated temporary password. Submit the actual page and verify the
   inactive/waiting message. No credentials from local smoke can be reused.
3. Log in normally at `/login` with the external temporary admin; open
   `/admin/vendor-scopes`. Select `預覽合成乙有限公司` / `00000002` and the new
   applicant. Verify the original cross-vendor warning and submitted company fields.
4. Confirm membership; select site 101 with SELECTED tasks 302 and 303, plus
   site 102 with ALL. To exercise server-side 400, bypass only the browser's HTML
   required-field validation for the blank reason; preserve the actual CSRF and
   signed snapshot. Verify warning, safe fields and checked controls survive.
5. With the same authenticated admin, compare `/preview/fixture-state` before
   and after that 400. It has no query parameters, SQL or paths; POST is rejected.
   It rechecks the current internal admin role from this fixture and opens SQLite
   with `mode=ro` and `query_only`. Compare `state`, `state_sha256` and row counts
   in the same boot. No credential/hash/cookie/CSRF/snapshot is returned.
6. Correct the reason and resubmit. Expect inactive account, disabled vendor,
   pending membership, configured count 3, effective count 0, one scope revision
   and one scope event. The original requested vendor remains company A even
   though the administrator deliberately configures company B.

The summary fingerprint covers its fixed safe projection, not all database
bytes. Local smoke separately compared the entire SQLite file bytes in memory
around the 400 and found no change; it did not store a DB copy/hash in evidence.
Metadata is confined to these diagnostic endpoints and this README, not added
to product interface wording. Local HTTP/HTML parsing is not browser/JS proof.

## Local repeat command and retained resources

From the baseline repository on Windows with the already installed requirements:

```powershell
python -B -m preview.vr4_20260928_r01.smoke
```

Every run creates a distinct directory below
`C:\Users\Public\Documents\004f-vr4-preview-20260928-r01\run-<uuid>`.
The smoke supplies explicit `LOCAL_SMOKE` mode, generates secrets only in memory,
uses real `127.0.0.1` HTTP with normal cookie handling and login, and records safe
events instead of HTTP bodies/headers. No secrets are redacted after capture:
they never enter captured events. All child listeners are shut down using their
owned process handles, with true PID, exit status and closed-port verification.
The evidence directories contain only source-safe JSON/stdout/stderr records;
the sibling `fixture/fixture.sqlite3` and `unknown/fixture.sqlite3` must never be
copied to Git, REPORT, ZIP, Drive or another service. No existing DB is accessed.

## Future cleanup (authorized for before formal activation; not performed here)

The temporary admin is only for preview review; the registered vendor account is
only for inactive/pending validation. Inventory future service ID, actual branch,
deployment ID and URL when ChatGPT creates them, beside the resource identities
above. Before any formal activation:

1. Stop and remove only `handover-vr4-preview-20260928-r01` after confirming its
   newly assigned service ID in workspace `tea-d8vmr4ok1i2s73etn1tg`; remove its
   temporary credential/secret values and any stored browser sessions.
2. Remove only its ephemeral `/tmp/004f-vr4-preview-20260928-r01` fixture when the
   service is stopped, if still retained. Deleting the isolated fixture removes
   the temporary admin, disabled default account and synthetic vendor applicants.
   Do not run account SQL against a real database.
3. Once no owned local listener is running, remove only this operation's named
   `run-<uuid>` fixture directories under the new Windows work root if cleanup is
   then requested. They contain hashed temporary credentials. Keep the accepted
   Record evidence under `I:\公司web\record\product-mainline\vendor-id\004f\vr4-preview-20260928-r01`.
4. Retire only the dedicated preview branch when authorized; never merge fixture
   data or temporary credentials into the production deployment. Existing Render
   resources, disks, environment groups, DBs and predecessor Records stay separate.

No cleanup, remote service creation, branch creation, Git metadata mutation,
commit, push, deployment or built-in-browser operation occurred in this build.
