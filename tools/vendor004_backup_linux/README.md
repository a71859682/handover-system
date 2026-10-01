# vendor004 private SQLite qualification preparation

This revision is PREPARATION ONLY, based on qualification commit
`05e90a8cc50f31ea0788e9a7cd8a903a5c51a0f5` on
`ci-vendor004-backup-linux-r01`. Product base remains
`f95c028f782028f214e0340ec4732ac66d386450`.
No build, installation, test execution, commit, push, CI, live access, merge or
deployment is included in this preparation. This branch is for isolated
qualification only. The backup implementation, original 16+9 tests, seven POSIX
cases, application workflow and product guards remain byte-identical.

## Accepted predecessor and current limitation

Prior run `36859202075` completed 32 functional cases and returned LIMITED,
exit 2. Its Ubuntu SQLite 3.45.1-1ubuntu2.8 library hash was
`85265A9D4AFCA6F4B325CEB078B669C754FB881ABED4CAFE91CCEBE9D625D975`.
That library is not accepted as WAL-reset fixed. Those results remain historical
functional evidence, not patch qualification. Actual DEV runtime is unknown;
this change neither inspects nor upgrades DEV.

The new recipe uses official SQLite 3.51.3, whose release includes the WAL-reset
fix. `pins.json` records the exact URL, archive size/SHA256/SHA3, member hashes,
source ID and recipe. Archive and member SHA256 values were computed from
official HTTPS bytes on 2026-10-01; the C file SHA3 and source ID also match the
official release publication. Archive hashes are not described as a historical
official checksum publication. No compiled binary has been observed or approved.
`reviewed_linux_sqlite` remains null: even a future 38-case success must return
LIMITED/exit 2 until the exact actual binary is independently reviewed. There is
no wildcard allowlist, automatic approval or version-only qualification.

## Private build and runtime contract

Python remains 3.14.7/x64 on ubuntu-24.04, with unchanged full action commit pins.
A future authorized job builds only pinned `sqlite3.c` using resolved
`/usr/bin/gcc`, `-O2 -fPIC -shared -DSQLITE_THREADSAFE=1`, SONAME
`libsqlite3.so.0`, RELRO/NOW and `-ldl -lpthread -lm`. There is no apt, sudo,
configure, make install, system-library replacement or toolcache modification.
The official previous runner-image report lists GCC and Python 3.14.7; a future
floating image is not assumed identical. Build evidence records actual compiler
path/hash/version, command, runner image, source identity and output binary SHA.

All output stays in a fresh 0700 direct child of RUNNER_TEMP named
`vendor004-sqlite-<run-id>-<attempt>`. Source/archive/library become 0400 and the
build manifest is create-new. Existing directories are rejected, never reused
or removed. Files must be canonical, owned by the current non-root UID, regular,
single-link and inaccessible to other users. Trusted parent directories and
same-UID processes remain prerequisites; these checks do not provide hostile
same-UID atomic immutability.

The launcher starts the supervisor with exactly
`<private-prefix>/lib:<Python-LIBDIR>` before Python imports SQLite. Suite and
worker processes inherit the same constructed loader environment. Arbitrary
LD_LIBRARY_PATH, LD_PRELOAD and LD_AUDIT are not inherited. The suite receives no
credentials or GITHUB_OUTPUT. Parent and suite verify actual `/proc` mappings,
private library SHA, SQLite version/full source ID/compile options, Python and
`_sqlite3` hashes against the build probe, before and after the suite. Missing,
multiple, deleted, system-fallback or mismatched libraries are rejected.

The new six cases cover exact identity, identity mismatch, mapping/hash rejection,
clean loader environment, an actual frozen worker's verified private mapping
before stdin, and rejection of a worker launched without the private path before
any payload is sent. The positive case uses fresh synthetic WAL data and the
unchanged worker argv. Worker source ID is explicitly INFERRED from the exact
same mapped binary observed in the queried parent/suite; the frozen worker does
not report its own source ID. The other transient workers in the original 32
cases inherit this environment; this is not individual per-PID attestation of
every original case. Original 16+9+7 cases stay unchanged; planned total is 38.
These six cases have been statically reviewed only, not executed.

## Future execution and retained evidence

Only after separate execution approval, the workflow would run:

```bash
python -I -S -B tools/vendor004_backup_linux/private_sqlite.py build --runtime-root "$QUAL_SQLITE_ROOT"
python -I -S -B tools/vendor004_backup_linux/private_sqlite.py launch --runtime-root "$QUAL_SQLITE_ROOT" --evidence-root "$QUAL_EVIDENCE_DIR"
```

The build step has a 3-minute cap (compiler subprocess 120 seconds); qualification
has a 5-minute cap and the unchanged 240-second supervisor budget, including
cleanup/finalization. The job cap becomes 9 minutes to include the new build and
upload margin. These are emergency bounds, not guaranteed interruption of stuck
kernel I/O or qualification of a DEV whole-command supervisor. No retry or
fallback is authorized by an UNKNOWN result. Source VFS WAL/SHM effects remain
possible under the existing synthetic contract; source SQL remains forbidden.
The download's 30-second timeout is a socket timeout, not a total download
deadline. The compiler's 120-second subprocess timeout stops the direct GCC
process; complete cc1/as/ld descendant cleanup has not been qualified. The outer
workflow step/job caps provide emergency containment, not a verified build-tree
supervisor or cleanup guarantee.

Upload has 16 literal filenames: eight Python files, README/pins, four existing
runtime/suite/console/supervisor files, plus sqlite-build.json/sqlite-build.log.
There is no upload of DB/WAL/SHM/journal, binary, archive, scratch, raw input or
environment dump. The existing artifact validation and conditional upload remain
in place. A build failure can leave runner logs/local private files but has no
qualified-suite artifact authorization. No candidate cleanup deletes files;
hosted-runner disposal is a platform lifecycle effect.

The unchanged application CI also runs on a later push. Its source-universe guard
already rejected the prior six new harness files and will see eight after this
revision; do not patch that guard or claim that expected failure is fixed. The
prior deployment-settings review found no service tracking this branch, but that
historical snapshot is not a fresh or universal deployment guarantee. No merge,
production preflight, F apply, G reconciliation or authority switch is implied.

## Review boundary and references

Preparation validation is limited to AST parsing (no imports), byte/hash checks,
static case counts and diff review. Next action is external review of the exact
patch/pins. Commit/push/build/CI require separate authorization. After that first
build, actual binary SHA/source ID/compile options, ABI/load behavior and worker
evidence must be reviewed before proposing an exact approved runtime pin.

- [SQLite 3.51.3 release](https://sqlite.org/releaselog/3_51_3.html)
- [Official source ZIP](https://sqlite.org/2026/sqlite-amalgamation-3510300.zip)
- [Compilation](https://www.sqlite.org/howtocompile.html)
- [Compile options](https://www.sqlite.org/compile.html)
- [Observed runner image software](https://github.com/actions/runner-images/blob/ubuntu24/20260927.320/images/ubuntu/Ubuntu2404-Readme.md)
- [WAL-reset advisory](https://sqlite.org/wal.html#the_wal_reset_bug)
