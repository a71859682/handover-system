"""Synthetic-only POSIX additions; never execute on the preparation Windows host."""
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import backup_candidate as candidate
import test_backup_candidate as baseline

PROOFS = []

def publish(path, value):
    with Path(path).open('x', encoding='utf-8') as out:
        json.dump(value, out)

def await_file(path, timeout=4):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return json.loads(Path(path).read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # A create-new file may be visible before its short write closes.
        if time.monotonic() >= deadline:
            raise RuntimeError('synthetic_handshake_timeout')
        time.sleep(0.005)

def signal_parent(request_path, channel):
    a = json.loads(Path(request_path).read_text(encoding='utf-8'))
    channel = Path(channel)
    # Child deliberately ignores TERM; candidate cleanup must really escalate.
    child = subprocess.Popen([sys.executable, '-I', '-S', '-B', __file__,
                              '--sleeper', str(channel/'child-ready.json')],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    actual_wait = child.wait
    waits = []
    try:
        await_file(channel/'child-ready.json')
        def wait(*args, **kwargs):
            number = len(waits)+1
            started = time.monotonic()
            waits.append(number)
            publish(channel/f'phase-{number}.json', {'parent_pid': os.getpid(), 'child_pid': child.pid,
                                                    'phase': 'terminate_wait' if number == 1 else 'kill_wait'})
            await_file(channel/f'ack-{number}.json', timeout=0.6)
            kwargs['timeout'] = max(0, kwargs['timeout']-(time.monotonic()-started))
            return actual_wait(*args, **kwargs)
        child.wait = wait
        with patch.object(candidate.subprocess, 'Popen', return_value=child):
            result = candidate.run(a)
        publish(channel/'result.json', {'receipt': result, 'actual_exit': child.returncode,
                                       'waits': waits, 'parent_pid': os.getpid(), 'child_pid': child.pid})
    finally:
        child.wait = actual_wait
        if child.poll() is None:
            child.kill()
            actual_wait(timeout=2)
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None and not stream.closed:
                stream.close()

class PosixQualification(baseline.Qualification):
    def external_cleanup(self, names):
        fx = self.fixture()
        channel = fx.root/'handshake'
        channel.mkdir(mode=0o700)
        a = fx.request(seconds=0.15)
        request = channel/'synthetic-input.json'
        publish(request, a)
        parent = subprocess.Popen([sys.executable, '-I', '-S', '-B', __file__,
                                   '--signal-parent', str(request), str(channel)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sent = []
        child_pid = None
        child_confirmed = False
        started = time.monotonic()
        try:
            for phase in (1, 2):
                observation = await_file(channel/f'phase-{phase}.json')
                self.assertEqual(observation['parent_pid'], parent.pid)
                child_pid = observation['child_pid']
                for name in names:
                    os.kill(parent.pid, getattr(signal, name))
                    sent.append({'sender_pid': os.getpid(), 'recipient_pid': parent.pid,
                                 'signal': name, 'phase': observation['phase']})
                publish(channel/f'ack-{phase}.json', {'ack': True})
            stdout, stderr = parent.communicate(timeout=3)
            self.assertEqual(parent.returncode, 0)
            self.assertEqual(stdout, b'')
            self.assertEqual(stderr, b'')
            result = await_file(channel/'result.json')
            receipt = result['receipt']
            self.assertEqual(result['actual_exit'], -signal.SIGKILL)
            self.assertEqual(result['waits'], [1, 2])
            self.assertEqual(receipt['status'], 'UNKNOWN_CONSUMED')
            self.assertTrue(receipt['consumed'])
            self.assertTrue(receipt['worker_reaped'])
            self.assertTrue(receipt['cancellation_requested'])
            self.assertFalse(receipt['destination_usable'])
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            child_confirmed = True
            with self.assertRaisesRegex(candidate.Rejected, 'operation_already_claimed'):
                candidate.run(a)
            PROOFS.append({'case': self._testMethodName, 'sent': sent, 'result': result,
                           'elapsed_seconds': time.monotonic()-started})
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=2)
            if child_pid is not None and not child_confirmed:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            for stream in (parent.stdout, parent.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    def test_posix_external_sigint_cleanup(self):
        self.external_cleanup(['SIGINT'])

    def test_posix_external_sigterm_cleanup(self):
        self.external_cleanup(['SIGTERM'])

    def test_posix_external_sighup_cleanup(self):
        self.external_cleanup(['SIGHUP'])

    def test_posix_repeated_mixed_signals_during_cleanup(self):
        self.external_cleanup(['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGINT', 'SIGTERM'])

    def test_posix_unsafe_claim_permissions_rejected(self):
        fx = self.fixture()
        a = fx.request()
        directory = baseline.claim(a)
        directory.chmod(0o750)
        with self.assertRaisesRegex(candidate.Rejected, 'claim_directory_rejected'):
            candidate.worker(a)
        self.assertFalse((directory/'worker-started.json').exists())
        self.assertFalse((directory/'backup.sqlite').exists())

    def test_posix_source_directory_and_claim_symlinks_rejected(self):
        for kind in ('source', 'directory', 'claim'):
            with self.subTest(kind=kind):
                fx = self.fixture()
                a = fx.request()
                directory = Path(a['destination_dir'])
                if kind == 'source':
                    # Preserve original inode/content; create a symlink at a new
                    # sibling synthetic locator, never rename or delete fixtures.
                    import tempfile
                    linked = Path(tempfile.mkdtemp(prefix='vendor004f-backup-synthetic-')).resolve()
                    (linked/'source.sqlite').symlink_to(fx.source)
                    a['source_path'] = str(linked/'source.sqlite')
                    a['destination_dir'] = str(linked/directory.name)
                    with self.assertRaises(candidate.Rejected):
                        candidate.run(a)
                    self.assertFalse(Path(a['destination_dir']).exists())
                elif kind == 'directory':
                    actual = fx.root/'real-operation'
                    actual.mkdir(mode=0o700)
                    directory.symlink_to(actual, target_is_directory=True)
                    with self.assertRaises(candidate.Rejected):
                        candidate.worker(a)
                    self.assertFalse((actual/'worker-started.json').exists())
                else:
                    directory.mkdir(mode=0o700)
                    actual = fx.root/'real-claim.json'
                    candidate.write_new(actual, {'input_sha256': candidate.digest(candidate.canonical(a)),
                                                 'operation_id': a['operation_id']})
                    (directory/'claim.json').symlink_to(actual)
                    with self.assertRaisesRegex(candidate.Rejected, 'claim_file_rejected'):
                        candidate.worker(a)
                    self.assertFalse((directory/'worker-started.json').exists())
                self.assertFalse((directory/'backup.sqlite').exists())

    def test_posix_readonly_source_and_private_destination_modes(self):
        fx = self.fixture(wal=True)
        a = fx.request()
        fx.source.chmod(0o400)
        before = fx.source.read_bytes()
        result = candidate.run(a)
        destination = self.assert_success(a, result)
        self.assertEqual(fx.source.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(destination.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o400)
        for name in ('claim.json', 'worker-started.json', 'receipt.json'):
            self.assertEqual(stat.S_IMODE((destination.parent/name).stat().st_mode), 0o600)
        self.assertEqual(destination.stat().st_uid, os.geteuid())
        PROOFS.append({'case': self._testMethodName, 'receipt': result,
                       'source_mode': '0400', 'directory_mode': '0700', 'destination_mode': '0400',
                       'same_uid_parent_namespace_trust_required': True})

if __name__ == '__main__':
    if sys.platform != 'linux' or os.geteuid() == 0:
        raise SystemExit('Linux non-root synthetic environment required')
    if sys.argv[1:2] == ['--sleeper'] and len(sys.argv) == 3:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        publish(sys.argv[2], {'pid': os.getpid()})
        time.sleep(30)
    elif sys.argv[1:2] == ['--signal-parent'] and len(sys.argv) == 4:
        signal_parent(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit('Only fixed synthetic helper modes supported')
