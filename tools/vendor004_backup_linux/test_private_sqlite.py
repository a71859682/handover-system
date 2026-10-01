"""Future Linux-only runtime cases; never execute during static preparation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import time
from unittest.mock import patch
import backup_candidate as candidate
import test_backup_candidate as baseline
import private_sqlite as private

PROOFS = []
ROOT = Path(__file__).resolve().parent

def await_mapping(child, seconds=3):
    end = time.monotonic()+seconds
    while child.poll() is None and time.monotonic() < end:
        paths = private.mapped_sqlite(child.pid)
        if paths:
            return paths
        time.sleep(0.01)
    raise ValueError('worker_mapping_not_observed')

def close_child(child):
    if child.poll() is None:
        child.kill()
    child.wait(timeout=2)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None and not stream.closed:
            stream.close()

class RuntimeQualification(baseline.Qualification):
    def runtime(self):
        root = private.private_root(os.environ['QUAL_SQLITE_ROOT'])
        pin = private.pins()
        manifest, observed = private.require_current(root, pin)
        return root, pin, manifest, observed

    def test_runtime_exact_suite_identity(self):
        _, _, manifest, observed = self.runtime()
        self.assertEqual(observed, manifest['probe'])
        PROOFS.append({'case': 'private_suite_identity', 'identity': observed,
                       'binary_review_status': 'UNREVIEWED'})

    def test_runtime_reject_identity_mismatches(self):
        root, pin, manifest, observed = self.runtime()
        for key, value in (('sqlite_source_id','wrong'), ('sqlite_version','3.45.1'),
                           ('python',[3,14,6]), ('library_sha256','0'*64),
                           ('sqlite_compile_options',[])):
            with self.subTest(key=key):
                changed = copy.deepcopy(observed)
                changed[key] = value
                with self.assertRaises(ValueError):
                    private.verify_observation(changed, root, pin['private_sqlite'], manifest['library_sha256'])

    def test_runtime_reject_fallback_multiple_deleted_or_wrong_hash(self):
        root, _, manifest, _ = self.runtime()
        expected = str(private.library_path(root))
        for paths, digest in (([], manifest['library_sha256']),
                              (['/usr/lib/x86_64-linux-gnu/libsqlite3.so.0.8.6'], manifest['library_sha256']),
                              ([expected, '/tmp/libsqlite3.so.0'], manifest['library_sha256']),
                              ([expected+' (deleted)'], manifest['library_sha256']),
                              ([expected], '0'*64)):
            with self.subTest(paths=paths):
                with self.assertRaises(ValueError):
                    private.verify_mapping(paths, root, digest)

    def test_runtime_clean_environment_drops_loader_overrides(self):
        root, _, _, _ = self.runtime()
        with patch.dict(os.environ, {'LD_LIBRARY_PATH':'/tmp/arbitrary:',
                                     'LD_PRELOAD':'/tmp/arbitrary.so', 'LD_AUDIT':'/tmp/audit.so'}):
            env = private.clean_env(root)
        self.assertEqual(env['LD_LIBRARY_PATH'], str(private.library_path(root).parent)+':'+str(Path(sysconfig.get_config_var('LIBDIR')).resolve()))
        self.assertNotIn('LD_PRELOAD', env)
        self.assertNotIn('LD_AUDIT', env)
        self.assertNotIn('GITHUB_OUTPUT', env)

    def test_runtime_actual_frozen_worker_before_input(self):
        root, _, manifest, _ = self.runtime()
        fx = self.fixture(wal=True, keep_open=True)
        request = fx.request()
        baseline.claim(request)
        child = subprocess.Popen([sys.executable,'-I','-S','-B',str(ROOT/'backup_candidate.py'),'--worker'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            paths = await_mapping(child)
            private.verify_mapping(paths, root, manifest['library_sha256'])
            stdout, stderr = child.communicate(candidate.canonical(request), timeout=10)
            self.assertEqual(child.returncode, 0)
            self.assertEqual(stderr, b'')
            result = json.loads(stdout)
            self.assert_success(request, result)
            PROOFS.append({'case':'actual_frozen_worker_private_mapping', 'child_pid':child.pid,
                           'library_paths':paths, 'library_sha256':manifest['library_sha256'],
                           'sqlite_source_id':manifest['probe']['sqlite_source_id'],
                           'source_id_basis':'INFERRED_FROM_EXACT_SAME_BINARY; no source SQL issued to query worker',
                           'mapping_verified_before_stdin':True, 'worker_reaped':True,
                           'receipt':result})
        finally:
            close_child(child)

    def test_runtime_system_fallback_worker_rejected_before_input(self):
        root, _, manifest, _ = self.runtime()
        env = private.clean_env(root)
        env['LD_LIBRARY_PATH'] = str(Path(sysconfig.get_config_var('LIBDIR')).resolve())
        child = subprocess.Popen([sys.executable,'-I','-S','-B',str(ROOT/'backup_candidate.py'),'--worker'],
                                 env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            paths = await_mapping(child)
            self.assertTrue(paths)
            self.assertNotIn(str(private.library_path(root)), paths)
            with self.assertRaises(ValueError):
                private.verify_mapping(paths, root, manifest['library_sha256'])
        finally:
            close_child(child)
        PROOFS.append({'case':'worker_system_fallback_rejected', 'payload_sent':False,
                       'observed_library_paths':paths,
                       'worker_reaped':child.poll() is not None})
