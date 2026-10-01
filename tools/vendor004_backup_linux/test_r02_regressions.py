"""r02-only regressions plus the unchanged original 16 synthetic cases."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
import backup_candidate as candidate
import test_backup_candidate as baseline

ROOT = Path(__file__).parent.resolve()
POPEN = subprocess.Popen
PROOFS = []

def sleeper():
    return POPEN([sys.executable, '-I', '-S', '-B', '-c', 'import time; time.sleep(30)'],
                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def ensure_exit(child):
    if child.poll() is None:
        child.kill()
        child.wait(timeout=3)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None and not stream.closed:
            stream.close()

class R02Qualification(baseline.Qualification):
    # Build only the new methods from this subclass below, avoiding duplicate
    # inherited baseline executions. Baseline file is copied byte-for-byte.
    def test_r02_real_cleanup_signals_do_not_skip_kill_or_reap(self):
        fx = self.fixture()
        a = fx.request(seconds=0.1)
        child = sleeper()
        actual_wait, actual_kill = child.wait, child.kill
        signals = []
        kills = []
        wait_budgets = []
        def wait_with_signals(*args, **kwargs):
            wait_budgets.append(kwargs['timeout'])
            for name in ('SIGINT', 'SIGTERM', 'SIGHUP', 'SIGINT'):
                if hasattr(signal, name):
                    signal.raise_signal(getattr(signal, name))
                    signals.append(name)
            return actual_wait(*args, **kwargs)
        def kill():
            kills.append(True)
            return actual_kill()
        child.wait = wait_with_signals
        child.kill = kill
        child.terminate = lambda: None  # Fault: force real wait timeout and kill path.
        started = time.monotonic()
        try:
            with patch.object(candidate.subprocess, 'Popen', return_value=child):
                result = candidate.run(a)
            elapsed = time.monotonic()-started
            self.assertEqual(result['status'], 'UNKNOWN_CONSUMED')
            self.assertTrue(result['consumed'])
            self.assertTrue(result['cancellation_requested'])
            self.assertTrue(result['worker_reaped'])
            self.assertFalse(result['destination_usable'])
            self.assertIsNotNone(child.poll())
            self.assertEqual(len(kills), 1)
            self.assertEqual(len(wait_budgets), 2)
            self.assertTrue(all(0 < x <= 2.1 for x in wait_budgets))
            self.assertGreaterEqual(signals.count('SIGINT'), 4)
            self.assertLess(elapsed, 5.5)
            self.assertTrue((Path(a['destination_dir'])/'claim.json').exists())
            PROOFS.append({'case': 'actual_child_cleanup_signals', 'pid': child.pid,
                           'signals': signals, 'wait_budgets': wait_budgets,
                           'actual_exit_code': child.returncode, 'kill_calls': len(kills),
                           'elapsed_seconds': elapsed, 'receipt': result,
                           'fault_injection': 'terminate intentionally no-op; wait/kill/process real',
                           'platform_limit': 'raise_signal delivery; external POSIX signaling pending'})
        finally:
            child.wait, child.kill = actual_wait, actual_kill
            ensure_exit(child)

    def test_r02_cancel_during_real_spawn_keeps_handle(self):
        fx = self.fixture()
        a = fx.request()
        children = []
        def spawn(*_, **__):
            child = sleeper()
            children.append(child)
            signal.raise_signal(signal.SIGINT)
            return child
        try:
            with patch.object(candidate.subprocess, 'Popen', side_effect=spawn):
                result = candidate.run(a)
            self.assertEqual(result['status'], 'UNKNOWN_CONSUMED')
            self.assertTrue(result['worker_started'])
            self.assertTrue(result['worker_reaped'])
            self.assertTrue(result['consumed'])
            self.assertFalse(result['destination_usable'])
            self.assertIsNotNone(children[0].poll())
            PROOFS.append({'case': 'cancel_before_popen_returns_handle', 'receipt': result,
                           'actual_exit_code': children[0].returncode})
        finally:
            for child in children:
                ensure_exit(child)

    def test_r02_spawn_delay_consumes_absolute_worker_budget(self):
        fx = self.fixture()
        a = fx.request(seconds=0.1)
        children = []
        communications = []
        def spawn(*_, **__):
            child = sleeper()
            children.append(child)
            actual = child.communicate
            def communicate(*args, **kwargs):
                communications.append(True)
                return actual(*args, **kwargs)
            child.communicate = communicate
            time.sleep(0.2)
            return child
        try:
            with patch.object(candidate.subprocess, 'Popen', side_effect=spawn):
                result = candidate.run(a)
            self.assertEqual(result['status'], 'TIMEOUT_CONSUMED')
            self.assertEqual(communications, [])
            self.assertTrue(result['worker_reaped'])
            self.assertFalse(result['destination_usable'])
            self.assertIsNotNone(children[0].poll())
            PROOFS.append({'case': 'spawn_exhausts_budget_no_communicate', 'receipt': result})
        finally:
            for child in children:
                ensure_exit(child)

    def test_r02_signal_immediately_after_mkdir_is_consumed(self):
        fx = self.fixture()
        a = fx.request()
        actual = candidate.os.mkdir
        def mkdir(*args, **kwargs):
            actual(*args, **kwargs)
            signal.raise_signal(signal.SIGINT)
        with patch.object(candidate.os, 'mkdir', side_effect=mkdir):
            result = candidate.run(a)
        self.assertEqual(result['status'], 'UNKNOWN_CONSUMED')
        self.assertTrue(result['consumed'])
        self.assertFalse(result['worker_started'])
        self.assertEqual(result['source_opens'], 0)
        self.assertTrue(Path(a['destination_dir']).is_dir())
        self.assertFalse((Path(a['destination_dir'])/'claim.json').exists())
        with self.assertRaisesRegex(candidate.Rejected, 'operation_already_claimed'):
            candidate.run(a)
        PROOFS.append({'case': 'mkdir_return_boundary_signal', 'receipt': result})

    def test_r02_fallible_metadata_precedes_mkdir(self):
        fx = self.fixture()
        a = fx.request()
        calls = []
        actual = candidate.code_sha
        def pin():
            calls.append(True)
            if len(calls) == 2:
                raise OSError('SYNTHETIC_METADATA_FAILURE')
            return actual()
        with patch.object(candidate, 'code_sha', side_effect=pin):
            with self.assertRaises(OSError):
                candidate.run(a)
        self.assertFalse(Path(a['destination_dir']).exists())

    def test_r02_post_mkdir_metadata_failure_cannot_escape_consumed(self):
        fx = self.fixture()
        a = fx.request()
        claimed = []
        actual_mkdir, actual_sha, actual_stamp = candidate.os.mkdir, candidate.code_sha, candidate.stamp
        def mkdir(*args, **kwargs):
            actual_mkdir(*args, **kwargs)
            claimed.append(True)
        def metadata(actual):
            def value():
                if claimed:
                    raise OSError('SYNTHETIC_POST_MKDIR_METADATA_FAILURE')
                return actual()
            return value
        with patch.object(candidate.os, 'mkdir', side_effect=mkdir), \
             patch.object(candidate, 'code_sha', side_effect=metadata(actual_sha)), \
             patch.object(candidate, 'stamp', side_effect=metadata(actual_stamp)):
            result = candidate.run(a)
        self.assertEqual(result['status'], 'RECEIPT_WRITE_FAILED_CONSUMED')
        self.assertTrue(result['consumed'])
        self.assertTrue(result['worker_reaped'])
        self.assertFalse(result['destination_usable'])
        self.assertFalse(result['receipt_persisted'])
        with self.assertRaisesRegex(candidate.Rejected, 'operation_already_claimed'):
            candidate.run(a)
        PROOFS.append({'case': 'post_mkdir_metadata_fault', 'receipt': result})

    def test_r02_unconfirmed_cleanup_is_unknown_consumed(self):
        fx = self.fixture()
        a = fx.request(seconds=0.1)
        class UnconfirmedChild:
            stdin = stdout = stderr = None
            returncode = None
            def communicate(self, *_, **__):
                raise KeyboardInterrupt
            def poll(self):
                return None
            def terminate(self):
                raise OSError('synthetic')
            def kill(self):
                raise OSError('synthetic')
            def wait(self, **_):
                raise subprocess.TimeoutExpired('synthetic', 0)
        with patch.object(candidate.subprocess, 'Popen', return_value=UnconfirmedChild()):
            result = candidate.run(a)
        self.assertEqual(result['status'], 'UNKNOWN_CONSUMED')
        self.assertEqual(result['reason'], 'worker_exit_unconfirmed')
        self.assertFalse(result['worker_reaped'])
        self.assertFalse(result['destination_usable'])
        self.assertTrue(result['consumed'])

    def test_r02_signal_during_receipt_finalization_never_promotes(self):
        fx = self.fixture()
        a = fx.request()
        actual = candidate.write_new
        def write(path, value):
            actual(path, value)
            if path.name == 'receipt.json':
                signal.raise_signal(signal.SIGTERM)
        with patch.object(candidate, 'write_new', side_effect=write):
            result = candidate.run(a)
        self.assertEqual(result['status'], 'UNKNOWN_CONSUMED')
        self.assertTrue(result['consumed'])
        self.assertTrue(result['cancellation_requested'])
        self.assertFalse(result['destination_usable'])
        self.assertTrue(result['receipt_persisted'])
        self.assertEqual(result['receipt_file_sha256'], candidate.digest((Path(a['destination_dir'])/'receipt.json').read_bytes()))
        PROOFS.append({'case': 'receipt_finalization_cancel', 'receipt': result})

    def test_r02_real_unconfirmed_child_does_not_block_closing_live_pipes(self):
        fx = self.fixture()
        a = fx.request(seconds=0.1)
        child = sleeper()
        actual_kill = child.kill
        watchdog_fired = []
        def emergency_kill():
            watchdog_fired.append(True)
            try:
                actual_kill()
            except OSError:
                pass
        watchdog = threading.Timer(7, emergency_kill)
        child.terminate = lambda: None
        child.kill = lambda: None
        watchdog.start()
        started = time.monotonic()
        try:
            with patch.object(candidate.subprocess, 'Popen', return_value=child):
                result = candidate.run(a)
            elapsed = time.monotonic()-started
            self.assertEqual(watchdog_fired, [])
            self.assertLess(elapsed, 6)
            self.assertEqual(result['status'], 'UNKNOWN_CONSUMED')
            self.assertTrue(result['consumed'])
            self.assertFalse(result['worker_reaped'])
            self.assertFalse(result['destination_usable'])
            self.assertIsNone(child.poll())
            self.assertFalse(child.stdout.closed)
            self.assertFalse(child.stderr.closed)
            PROOFS.append({'case': 'actual_unconfirmed_child_live_pipes',
                           'receipt': result, 'elapsed_seconds': elapsed,
                           'actual_child_still_alive_at_return': True,
                           'stdout_stderr_not_closed': True, 'watchdog_fired': False,
                           'fault_injection': 'terminate/kill intentionally no-op; real communicate and waits'})
        finally:
            watchdog.cancel()
            child.kill = actual_kill
            ensure_exit(child)
            watchdog.join(timeout=1)

if __name__ == '__main__':
    if len(sys.argv) != 2 or not sys.argv[1].startswith('attempt') or not sys.argv[1][7:].isdigit():
        raise SystemExit('required new evidence suffix: attemptNN')
    destination = ROOT/'evidence'/('test-results-' + sys.argv[1] + '.json')
    if destination.exists():
        raise SystemExit('evidence already exists; no rerun/overwrite')
    baseline_hash = hashlib.sha256((ROOT/'test_backup_candidate.py').read_bytes()).hexdigest().upper()
    assert baseline_hash == 'A0BDD8F0E7CC2F134C5898797B41870E661618BDC63F55EA55CF28CA1315079F'
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(baseline.Qualification)
    assert suite.countTestCases() == 16
    for name in sorted(R02Qualification.__dict__):
        if name.startswith('test_r02_'):
            suite.addTest(R02Qualification(name))
    result = unittest.TextTestRunner(verbosity=2, resultclass=baseline.Result).run(suite)
    evidence = {'status': 'SYNTHETIC_PASS' if result.wasSuccessful() else 'SYNTHETIC_FAILED',
                'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                'results': result.records, 'failure_details': [str(t) for t, _ in result.failures],
                'error_details': [str(t) for t, _ in result.errors], 'proofs': baseline.PROOFS + PROOFS,
                'python': sys.version, 'sqlite_version': candidate.sqlite3.sqlite_version,
                'platform': sys.platform, 'candidate_sha256': candidate.code_sha(),
                'original_16_tests_sha256': baseline_hash,
                'r02_test_source_sha256': candidate.digest(Path(__file__).read_bytes()),
                'fixtures_retained': True, 'live_executed': False, 'dev_authority_issued': False,
                'linux_qualification': 'NOT_QUALIFIED', 'wal_reset_patch_qualified': False}
    with destination.open('xb') as f:
        f.write(candidate.canonical(evidence)+b'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
