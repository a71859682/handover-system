"""Unchanged 16+9+7 functional cases plus six private-runtime contract cases."""
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import backup_candidate as candidate
import test_backup_candidate as baseline
import test_r02_regressions as r02
import posix_cases as posix
import supervise
import private_sqlite
import test_private_sqlite as private_tests

if __name__ == '__main__':
    if sys.platform != 'linux' or os.geteuid() == 0 or len(sys.argv) != 2:
        raise SystemExit('Linux non-root and one fresh evidence directory required')
    output = Path(sys.argv[1]).resolve()/'suite.json'
    if output.exists():
        raise SystemExit('Evidence exists; no overwrite/retry')
    pin = private_sqlite.pins()
    private_root = private_sqlite.private_root(os.environ['QUAL_SQLITE_ROOT'])
    build, private_identity = private_sqlite.require_current(private_root, pin)
    runtime = supervise.runtime_info()  # Actual suite process in its clean environment.
    runtime['private_sqlite'] = private_identity
    runtime['build_manifest_sha256'] = supervise.digest(private_root/'build.json')
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(baseline.Qualification)
    assert suite.countTestCases() == 16
    for cls, prefix in ((r02.R02Qualification, 'test_r02_'), (posix.PosixQualification, 'test_posix_')):
        for name in sorted(cls.__dict__):
            if name.startswith(prefix):
                suite.addTest(cls(name))
    assert suite.countTestCases() == 32
    for name in sorted(private_tests.RuntimeQualification.__dict__):
        if name.startswith('test_runtime_'):
            suite.addTest(private_tests.RuntimeQualification(name))
    assert suite.countTestCases() == 38
    result = unittest.TextTestRunner(verbosity=2, resultclass=baseline.Result).run(suite)
    build_after, identity_after = private_sqlite.require_current(private_root, pin)
    unchanged = build_after == build and identity_after == private_identity
    evidence = {'status': 'FUNCTIONAL_PASS' if result.wasSuccessful() and unchanged else 'FAIL',
                'original_functional_cases': 32, 'runtime_contract_cases': 6,
                'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                'results': result.records, 'proofs': baseline.PROOFS + r02.PROOFS + posix.PROOFS + private_tests.PROOFS,
                'python': sys.version, 'sqlite': candidate.sqlite3.sqlite_version, 'euid': os.geteuid(),
                'runtime': runtime,
                'live_executed': False, 'dev_grant_issued': False,
                'whole_command_dev_supervisor_qualified': False}
    with output.open('xb') as stream:
        stream.write(candidate.canonical(evidence)+b'\n')
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
