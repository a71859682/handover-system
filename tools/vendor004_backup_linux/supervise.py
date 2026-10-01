"""Linux-only synthetic job supervisor; not a qualified DEV supervisor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import _sqlite3
import subprocess
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parent
CODE = ('backup_candidate.py', 'test_backup_candidate.py', 'test_r02_regressions.py',
        'posix_cases.py', 'qualify.py', 'supervise.py')
ARTIFACTS = CODE + ('README.md', 'pins.json', 'runtime.json', 'suite.json', 'console.txt', 'supervisor.json')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write('\n')

def pins_match(pins):
    return set(pins['files']) == set(CODE) and all(
        not (ROOT/name).is_symlink() and digest(ROOT/name) == pins['files'][name]
        for name in CODE)

def runtime_info():
    # This introspection database is independent in-memory synthetic state.
    with sqlite3.connect(':memory:') as db:
        source_id = db.execute('SELECT sqlite_source_id()').fetchone()[0]
        options = [row[0] for row in db.execute('PRAGMA compile_options')]
    mapped = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                     if '/libsqlite3' in line and line.split()[-1].startswith('/')})
    libraries = []
    for name in mapped:
        p = Path(name)
        owner = subprocess.run(['/usr/bin/dpkg-query', '-S', str(p)],
                               capture_output=True, text=True, timeout=3, check=False)
        package = owner.stdout.split(': ', 1)[0].strip() if owner.returncode == 0 else None
        metadata = None
        if package and '\n' not in package and not package.startswith('-'):
            query = subprocess.run(['/usr/bin/dpkg-query', '-W',
                                    '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n', package],
                                   capture_output=True, text=True, timeout=3, check=False)
            metadata = {'exit_code': query.returncode, 'package_source_version': query.stdout.strip()[:2048]}
        libraries.append({'path': str(p), 'sha256': digest(p),
                          'package_owner_status': owner.returncode,
                          'package_owner': owner.stdout.strip()[:2048], 'package_metadata': metadata})
    version = sqlite3.sqlite_version_info
    fixed_line = (version >= (3, 51, 3) or version[:2] == (3, 50) and version[2] >= 7
                  or version[:2] == (3, 44) and version[2] >= 6)
    return {'python': list(sys.version_info[:3]), 'python_full': sys.version,
            'python_executable': sys.executable, 'python_sha256': digest(sys.executable),
            'sqlite_version': sqlite3.sqlite_version, 'sqlite_source_id': source_id,
            'sqlite_compile_options': options, 'sqlite_extension_sha256': digest(_sqlite3.__file__),
            'linked_libraries': libraries, 'version_in_official_fix_line': fixed_line,
            'patch_provenance': 'UNREVIEWED_RUNTIME_OBSERVATION',
            'euid': os.geteuid(), 'platform': sys.platform, 'uname': list(os.uname()),
            'runner_image': {k: os.environ.get(k) for k in ('ImageOS', 'ImageVersion')},
            'umask': '0077', 'live_access': False}

def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False

def stop_group(child, end):
    # Only the process group created by this supervisor is targeted.
    for sig, allowance in ((signal.SIGTERM, 2), (signal.SIGKILL, 2)):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        until = min(end, time.monotonic()+allowance)
        while time.monotonic() < until:
            child.poll()  # Reap the direct child; descendants exit/reap separately.
            if not group_exists(child.pid):
                return True
            time.sleep(0.02)
    child.poll()
    return not group_exists(child.pid)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or os.geteuid() == 0:
        raise SystemExit('Only Linux non-root synthetic job is supported')
    started = time.monotonic()
    end = started + 240  # Includes scheduled cleanup budget, not stuck kernel I/O.
    suite_end, cleanup_end = end-10, end-6
    os.umask(0o077)
    base = Path(args.evidence_root)
    temp = Path(os.environ['RUNNER_TEMP']).resolve()
    if not base.is_absolute() or base.parent.resolve() != temp or base.resolve() != base:
        raise SystemExit('Evidence must be a new direct child of RUNNER_TEMP')
    base.mkdir(mode=0o700)  # Existing run/attempt suffix is never overwritten.
    artifact = base/'artifact'
    artifact.mkdir(mode=0o700)
    scratch = base/'scratch'
    scratch.mkdir(mode=0o700)
    home = base/'home'
    home.mkdir(mode=0o700)
    report = {'status': 'UNKNOWN', 'dev_supervisor_qualified': False, 'live_executed': False,
              'dev_grant_issued': False, 'candidate_rerun_on_windows': False,
              'evidence_retained': True, 'process_group_exit_confirmed': False}
    child = None
    cancelled = []
    def cancel(signum, _):
        cancelled.append(signum)
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, cancel)
    verified = False
    try:
        pins = json.loads((ROOT/'pins.json').read_text())
        if tuple(sys.version_info[:3]) != (3, 14, 7) or not pins_match(pins):
            raise ValueError('runtime_or_code_pin_mismatch')
        verified = True
        runtime = runtime_info()
        write_new(artifact/'runtime.json', runtime)
        env = {'PATH': str(Path(sys.executable).parent)+':/usr/bin:/bin', 'HOME': str(home),
               'TMPDIR': str(scratch), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
               'LD_LIBRARY_PATH': str(sysconfig.get_config_var('LIBDIR'))}
        if cancelled or time.monotonic() >= suite_end:
            raise TimeoutError('No remaining suite budget')
        with (artifact/'console.txt').open('xb') as console:
            child = subprocess.Popen([sys.executable, '-I', '-S', '-B', str(ROOT/'qualify.py'), str(artifact)],
                                     cwd=ROOT, env=env, start_new_session=True,
                                     stdin=subprocess.DEVNULL, stdout=console, stderr=console)
            report['owned_process_group'] = child.pid
            while child.poll() is None and not cancelled and time.monotonic() < suite_end:
                time.sleep(0.05)
            timed_out = child.poll() is None or bool(cancelled)
            exists = group_exists(child.pid)
            report['process_group_exit_confirmed'] = not exists or stop_group(child, cleanup_end)
            report['suite_exit_code'] = child.returncode
            report['timeout_or_cancel'] = timed_out
        same = pins_match(pins)
        verified = verified and same
        report['input_hashes_unchanged'] = same
        suite_path = artifact/'suite.json'
        suite = json.loads(suite_path.read_text()) if suite_path.is_file() else {}
        functional = suite.get('status') == 'FUNCTIONAL_PASS'
        actual = suite.get('runtime', {})
        matched_runtime = all(actual.get(k) == runtime[k] for k in
                              ('python', 'sqlite_version', 'sqlite_source_id',
                               'sqlite_extension_sha256', 'linked_libraries'))
        report['suite_runtime_matches_supervisor'] = matched_runtime
        expected = pins.get('reviewed_linux_sqlite')
        patch_verified = bool(expected and matched_runtime and expected.get('wal_reset_fixed') is True
                              and expected.get('evidence_url')
                              and (actual.get('version_in_official_fix_line') or expected.get('documented_backport_fixed') is True)
                              and expected['sqlite_version'] == actual.get('sqlite_version')
                              and expected['sqlite_source_id'] == actual.get('sqlite_source_id')
                              and expected['library_sha256'] == [x['sha256'] for x in actual.get('linked_libraries', [])])
        report['wal_patch_provenance_verified'] = patch_verified
        if timed_out or not report['process_group_exit_confirmed']:
            report['status'] = 'UNKNOWN'
        elif not same or not functional or child.returncode != 0 or not matched_runtime:
            report['status'] = 'FAIL'
        elif not patch_verified:
            report['status'] = 'LIMITED'
            report['limitation'] = 'Actual linked SQLite version/patch provenance requires independent review; no DEV upgrade performed.'
        else:
            report['status'] = 'SYNTHETIC_QUALIFIED_ONLY'
    except Exception as exc:
        report['status'] = 'UNKNOWN'
        report['error_type'] = type(exc).__name__  # No arbitrary exception/env dump.
    finally:
        if child is not None and group_exists(child.pid):
            report['process_group_exit_confirmed'] = stop_group(child, cleanup_end)
            report['status'] = 'UNKNOWN'
        report['signals'] = cancelled
        report['five_minute_ci_cap_is_emergency_only'] = True
        if verified:
            for name in CODE + ('README.md', 'pins.json'):
                if time.monotonic() >= end:
                    raise TimeoutError('Finalization budget exhausted; no upload permission')
                source = ROOT/name
                raw = source.read_bytes()
                if source.is_symlink() or len(raw) > 262144 or b'\x00' in raw:
                    raise ValueError('Artifact rejected')
                with (artifact/name).open('xb') as out:
                    out.write(raw)
        report['elapsed_before_receipt_write'] = time.monotonic()-started
        if time.monotonic() >= end:
            report['status'] = 'UNKNOWN'
        write_new(artifact/'supervisor.json', report)
        # All emitted artifact filenames are explicit; synthetic DBs stay scratch.
        for path in artifact.iterdir():
            if (time.monotonic() >= end or path.name not in ARTIFACTS or path.is_symlink() or not path.is_file()
                    or path.stat().st_size > 2*1024*1024 or path.read_bytes().startswith(b'SQLite format 3\0')):
                raise ValueError('Artifact allowlist violation; nothing removed')
            raw = path.read_bytes()
            raw.decode('utf-8-sig')
            if path.suffix == '.json':
                json.loads(raw)
        report['elapsed_after_artifact_validation'] = time.monotonic()-started
        if time.monotonic() >= end:
            raise TimeoutError('No upload permission after deadline')
        # The suite never receives GITHUB_OUTPUT. A failed/incomplete validation
        # cannot authorize the workflow's always-on evidence retention step.
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
                out.write('artifacts_validated=true\n')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] == 'SYNTHETIC_QUALIFIED_ONLY' else 2

if __name__ == '__main__':
    raise SystemExit(main())
