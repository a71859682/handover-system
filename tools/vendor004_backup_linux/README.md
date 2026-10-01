# vendor004 backup Linux qualification candidate r01

PREPARATION ONLY. No commit, push, CI, Linux execution, Windows rerun, DEV input/grant or live database access occurred. The local branch is `ci-vendor004-backup-linux-r01`, based on reviewed `ci-vr-schema-compat-r01` at `f95c028f782028f214e0340ec4732ac66d386450`. New files are confined to this directory and `.github/workflows/vendor004-backup-linux.yml`; application/runtime code and the existing CI are unchanged. This branch inherits the reviewed baseline; it is not an orphan branch.

## What a later separately approved push would do

The new workflow matches only this branch and these qualification paths. **The unchanged existing `.github/workflows/ci.yml` also matches every push and will run its Linux portable, Windows native and verify jobs.** That additional application CI is not silently disabled or claimed to be avoided. Future authorization must include both workflows, or a separately approved trigger change must be reviewed first. No PR or merge is part of this candidate.

Read-only repo hooks/rulesets returned empty lists. Default `main` has only an application CI workflow with no deploy step. Five services in the selected Render workspace were inspected: auto-deploy tracks main/develop/staging; both preview services have auto-deploy and previews off; none follows this new branch. No deployment path was found in the inspected settings. `deployment-review.json` records the snapshot and its visibility limits; unlisted external integrations or later setting changes are not attested. No Render secrets, env vars or DB were read.

## Fixed inputs and provenance

The r02 candidate, original16 tests and9 regression supplement are copied byte-identically. Per-directory Git attributes disable text normalization for these originals. Their SHA256 pins are:

| Original | SHA256 |
| --- | --- |
| backup_candidate.py | 9042FE33A26BC903BB27D364EB67AEE202EF68483BAF5B5603E64655D293BC54 |
| test_backup_candidate.py | A0BDD8F0E7CC2F134C5898797B41870E661618BDC63F55EA55CF28CA1315079F |
| test_r02_regressions.py | 49A4E8E1A58FB5D35FAC777E656266E636B6F9F1C59ACB722F775029C16D9038 |

All six Python files are checked before/after the future suite using `pins.json`. Python is fixed at3.14.7/x64 on ubuntu-24.04. Checkout v7.0.1, setup-python v7.0.0 and upload-artifact v7.0.1 use full official commit pins; URLs and published Python asset metadata are in `pins.json`.

setup-python can use runner toolcache or official actions/python-versions downloads. The upstream3.14.7 Linux24.04 x64 asset has published SHA25676d5ddab6d2dd89a39c06220f6efeda486a48ed481eae97bfc596c74ac3623db, but this preparation has not downloaded/hashed it and cannot claim it is what a future runner will use. The official builder uses a distribution SQLite dependency; a Python version does not fix the loaded SQLite library.

**Actual Linux linked SQLite version/source ID/library hashes and patch provenance remain unknown.** `reviewed_linux_sqlite` is deliberately null. The future supervisor records the real Python binary, `_sqlite3`, mapped SQLite library hashes/package ownership and independent `:memory:` SQLite version/source ID/compile options. It does not query a backed-up source for provenance. It classifies known fixed version lines conservatively (3.51.3+, or3.50.7+/3.44.6+ on those specific branches), but version alone is not reviewed distro backport proof. If functional tests pass without reviewed actual-library provenance, overall status is **LIMITED, exit2**, not PASS. Review the observed runtime before proposing any subsequent qualification; no private binary download or DEV upgrade is included.

## Minimal additional Linux proof

The future suite contains the unchanged16 + unchanged9 cases and7 POSIX cases. Three cases send real external SIGINT/SIGTERM/SIGHUP to the known synthetic parent PID; another repeats mixed signals during both cleanup waits. A ready/phase/ack handshake chooses the phase. A real helper child ignores SIGTERM, so actual terminate/wait must escalate to SIGKILL/reap. No candidate source patch is made; a test-local Popen/wait hook binds the real helper and observes phase. Tests demand actual `-SIGKILL`, consumed/unusable receipt, confirmed child exit and replay rejection.

Other cases reject unsafe claim-directory modes and source/directory/claim symlinks before source opening, and verify a0400 synthetic main with a writable sidecar directory plus destination0400/private0700/0600 modes. Same-UID/root path replacement remains outside the candidate's atomic guarantees; trusted parent directories and same-UID processes are prerequisites. No test changes this trust contract. Source VFS WAL/SHM effects remain possible; source SQL is still forbidden.

## Supervisor, artifacts and exact future command

Only after external review and explicit commit/push/CI authorization, the single new job would execute:

```bash
python -I -S -B tools/vendor004_backup_linux/supervise.py --evidence-root "$QUAL_EVIDENCE_DIR"
```

The workflow sets QUAL_EVIDENCE_DIR to a new direct child of RUNNER_TEMP suffixed with GitHub run ID and run attempt. Existing evidence paths are refused. The supervisor requires Linux/non-root, sets umask0077, creates separate home/scratch/artifact directories, runs tests with a minimal environment and no credentials, and starts its test tree in its own process group. No live mount, /var/data source, application dependency, service container or Render secret is used. Synthetic failures and unknown results remain retained; no cleanup deletes files.

One absolute monotonic240-second budget reserves the last10 seconds for cleanup/finalization: suite stops by230s, cleanup by234s, artifact stages check the240s deadline. Only the supervisor-owned process group can receive fallback TERM/KILL. Signals set cancellation state. Elapsed values distinguish receipt-write time from final artifact validation. The workflow's5-minute cap is emergency containment. Neither mechanism is currently executed/qualified, neither can guarantee interruption of stuck kernel I/O, and neither constitutes a qualified DEV whole-command supervisor. A missing terminal/suite receipt or unconfirmed process group means UNKNOWN, never permission to retry an operation.

The upload step uses12 literal filenames only (six code files, README/pins, runtime/suite/console/supervisor evidence); no DB/WAL/SHM/journal, scratch tree, input JSON, env dump or broad repository upload. No artifacts are overwritten. An explicit output is produced only after the entire artifact validation succeeds before the deadline; the `always()` upload additionally requires that output. Safe FAIL/UNKNOWN evidence can be retained, but failed/incomplete content validation is not published and remains local. Hard job cancellation may still prevent upload. Hosted-runner disposal is platform lifecycle, not candidate deletion authority.

The suite also measures its own linked library/source ID/hashes under the exact clean environment and must match supervisor observations before any future qualification. External signal tests here cover cleanup; external signaling during spawn remains untested (the original9 supplement covers its own in-process spawn cancellation only).

This preparation used static Python parsing, byte/hash checks and diff review only. It does not establish Linux results, patch safety, DEV source identity or grant. The next handoff is external review of this exact diff and pins; only then may an exact commit/push/CI request be put to the user.

Official references: [SQLite WAL-reset advisory](https://sqlite.org/wal.html#the_wal_reset_bug), [setup-python fixed source](https://github.com/actions/setup-python/blob/5fda3b95a4ea91299a34e894583c3862153e4b97/README.md), [Python build release](https://github.com/actions/python-versions/releases/tag/3.14.7-31064857500).
