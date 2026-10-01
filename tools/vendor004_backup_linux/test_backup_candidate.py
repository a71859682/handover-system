"""New scratch SQLite fixtures only. No deletion, live access or credentials."""
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import backup_candidate as candidate

ROOT = Path(__file__).parent.resolve()
CONNECT = sqlite3.connect
PROOFS = []

class Fixture:
    def __init__(self, wal=False, keep_open=False):
        self.root = Path(tempfile.mkdtemp(prefix="vendor004f-backup-synthetic-")).resolve()
        self.source = self.root / "source.sqlite"
        db = CONNECT(self.source)
        db.executescript("CREATE TABLE state_a(id INTEGER PRIMARY KEY, version INTEGER);"
                         "CREATE TABLE state_b(id INTEGER PRIMARY KEY, version INTEGER);"
                         "CREATE TABLE payload(id INTEGER PRIMARY KEY, value BLOB);"
                         "CREATE TABLE credentials(id INTEGER PRIMARY KEY, password_hash TEXT);"
                         "INSERT INTO state_a VALUES(1,0); INSERT INTO state_b VALUES(1,0);"
                         "INSERT INTO credentials VALUES(1,'SYNTHETIC_HASH_DO_NOT_PRINT');")
        db.executemany("INSERT INTO payload VALUES(?,?)", [(i, b"fabricated-" * 400) for i in range(256)])
        db.commit()
        if wal:
            assert db.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
            db.execute("UPDATE state_a SET version=7")
            db.execute("UPDATE state_b SET version=7")
            db.commit()
        self.keeper = db if keep_open else None
        if not keep_open:
            db.close()

    def request(self, seconds=10):
        operation = os.urandom(8).hex().upper()
        current = candidate.now()
        return {"schema": candidate.SCHEMA, "mode": "synthetic", "operation_id": operation,
                "candidate_sha256": candidate.code_sha(), "approval_reference": "SYNTHETIC-TEST-ONLY",
                "target": dict(candidate.TARGET), "source_path": str(self.source),
                "source_device": self.source.stat().st_dev,
                "destination_dir": str(self.root / ("004f-backup-" + operation)),
                "issued_at_utc": (current-dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                "expires_at_utc": (current+dt.timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                "timeout_seconds": seconds,
                "permissions": {"source_backup_page_read": True, "source_sql_write": False,
                    "source_vfs_side_effects": True, "destination_create_and_write": True,
                    "destination_normalize": True, "receipt_write": True,
                    "raw_database_export": False, "dev_execution_authorized": False}}

    def close(self):
        if self.keeper is not None:
            self.keeper.close()

def cli(a):
    p = subprocess.run([sys.executable, "-I", "-S", "-B", str(ROOT/"backup_candidate.py")],
                       input=candidate.canonical(a), capture_output=True, timeout=20)
    return p, json.loads(p.stdout)

def claim(a):
    root = Path(a["destination_dir"])
    os.mkdir(root, 0o700)
    candidate.write_new(root/"claim.json", {"input_sha256": candidate.digest(candidate.canonical(a)),
                                            "operation_id": a["operation_id"]})
    return root

def state(path):
    db = CONNECT(path.as_uri()+"?mode=ro", uri=True)
    try:
        return (db.execute("SELECT version FROM state_a").fetchone()[0],
                db.execute("SELECT version FROM state_b").fetchone()[0],
                db.execute("SELECT password_hash FROM credentials").fetchone()[0],
                db.execute("SELECT COUNT(*),SUM(LENGTH(value)) FROM payload").fetchone())
    finally:
        db.close()

class Qualification(unittest.TestCase):
    def setUp(self):
        self.fixtures = []

    def fixture(self, **kwargs):
        fx = Fixture(**kwargs)
        self.fixtures.append(fx)
        return fx

    def tearDown(self):
        for fx in self.fixtures:
            fx.close()

    def assert_success(self, a, result):
        self.assertEqual(result["status"], "SNAPSHOT_CREATED", result)
        self.assertTrue(result["backup_done"])
        self.assertTrue(result["destination_usable"])
        self.assertEqual(result["source_opens"], 1)
        self.assertEqual(result["source_sql_statements"], 0)
        self.assertEqual(result["source_authorizer_calls"], 0)
        path = Path(a["destination_dir"])/"backup.sqlite"
        self.assertEqual(path.read_bytes()[18:20], b"\x01\x01")
        self.assertFalse(any(candidate.sidecars(path).values()))
        self.assertEqual(candidate.digest(path.read_bytes()), result["destination_sha256"])
        self.assertEqual(path.stat().st_mode & 0o222, 0)
        self.assertFalse(result["immutable_storage_proven"])
        if "receipt_persisted" in result:
            self.assertTrue(result["receipt_persisted"])
            raw_receipt = (path.parent/"receipt.json").read_bytes()
            self.assertEqual(candidate.digest(raw_receipt), result["receipt_file_sha256"])
            self.assertFalse(json.loads(raw_receipt)["receipt_persisted"])
        self.assertNotIn("SYNTHETIC_HASH_DO_NOT_PRINT", candidate.canonical(result).decode())
        return path

    def test_rollback_full_copy_source_bytes_and_data_unchanged(self):
        fx = self.fixture()
        original = fx.source.read_bytes()
        before = state(fx.source)
        a = fx.request()
        p, result = cli(a)
        self.assertEqual(p.returncode, 0)
        target = self.assert_success(a, result)
        self.assertEqual(state(target), before)
        self.assertEqual(state(fx.source), before)
        self.assertEqual(fx.source.read_bytes(), original)
        self.assertTrue((target.parent/"receipt.json").is_file())
        PROOFS.append({"case": "rollback", "source_main_bytes_equal": True,
                       "logical_copy_equal": True, "receipt": result})

    def test_live_wal_committed_pages_included_without_checkpoint_command(self):
        fx = self.fixture(wal=True, keep_open=True)
        self.assertTrue(Path(str(fx.source)+"-wal").exists())
        original = fx.source.read_bytes()
        a = fx.request()
        _, result = cli(a)
        target = self.assert_success(a, result)
        self.assertEqual(state(target)[:2], (7,7))
        self.assertEqual(state(fx.source)[:2], (7,7))
        self.assertEqual(fx.source.read_bytes(), original)
        PROOFS.append({"case": "wal_committed_uncheckpointed", "source_main_bytes_equal": True,
                       "committed_version_copied": 7, "receipt": result})

    def test_clean_closed_wal_without_sidecars(self):
        fx = self.fixture(wal=True)
        self.assertEqual(fx.source.read_bytes()[18:20], b"\x02\x02")
        self.assertFalse(any(candidate.sidecars(fx.source).values()))
        original = fx.source.read_bytes()
        a = fx.request()
        _, result = cli(a)
        target = self.assert_success(a, result)
        self.assertEqual(state(target)[:2], (7,7))
        self.assertEqual(fx.source.read_bytes(), original)
        PROOFS.append({"case": "closed_wal_no_initial_sidecars", "source_main_bytes_equal": True,
                       "receipt": result})

    def test_real_commit_between_backup_steps_preserves_transaction_consistency(self):
        fx = self.fixture(wal=True, keep_open=True)
        a = fx.request()
        claim(a)
        commits = []
        class ConcurrentConnection(sqlite3.Connection):
            def backup(self, destination, **kwargs):
                actual = kwargs["progress"]
                def during(status, remaining, total):
                    if remaining > 0 and not commits:
                        fx.keeper.execute("BEGIN IMMEDIATE")
                        fx.keeper.execute("UPDATE state_a SET version=8")
                        fx.keeper.execute("UPDATE state_b SET version=8")
                        fx.keeper.commit()
                        commits.append({"remaining_before_commit": remaining, "version": 8})
                    actual(status, remaining, total)
                kwargs["progress"] = during
                return super().backup(destination, **kwargs)
        def traced(*args, **kwargs):
            kwargs["factory"] = ConcurrentConnection
            self.assertIn("mode=ro" if "source.sqlite" in args[0] else "mode=rw", args[0])
            return CONNECT(*args, **kwargs)
        with patch.object(candidate.sqlite3, "connect", side_effect=traced):
            result = candidate.worker(a)
        target = self.assert_success(a, result)
        self.assertEqual(len(commits), 1)
        self.assertEqual(state(target)[:2], (8,8))
        self.assertEqual(state(fx.source)[:2], (8,8))
        PROOFS.append({"case": "concurrent_committed_transaction", "commits_during_backup": commits,
                       "destination_versions": [8,8], "receipt": result})

    def test_busy_source_timeout_retains_destination_and_consumes_operation(self):
        fx = self.fixture()
        lock = CONNECT(fx.source)
        lock.execute("BEGIN EXCLUSIVE")
        lock.execute("UPDATE state_a SET version=999")
        a = fx.request(seconds=0.6)
        start = time.monotonic()
        try:
            process, result = cli(a)
        finally:
            lock.rollback()
            lock.close()
        elapsed = time.monotonic()-start
        self.assertIn(result["status"], ("TIMEOUT_CONSUMED", "FAILED"))
        self.assertEqual(process.returncode, 2)
        self.assertFalse(result["destination_usable"])
        self.assertTrue(result["worker_reaped"])
        self.assertLess(elapsed, 5)
        root = Path(a["destination_dir"])
        self.assertTrue((root/"backup.sqlite").exists())
        self.assertTrue((root/"receipt.json").exists())
        p, replay = cli(a)
        self.assertEqual(p.returncode, 3)
        self.assertEqual(replay["reason"], "operation_already_claimed")
        self.assertEqual(state(fx.source)[:2], (0,0))
        PROOFS.append({"case": "busy_timeout", "elapsed_seconds": elapsed, "partial_retained": True,
                       "replay_rejected": True, "receipt": result})

    def test_done_callback_deadline_never_promotes_completed_but_late_copy(self):
        fx = self.fixture()
        a = fx.request(seconds=0.1)
        root = claim(a)
        class LateConnection(sqlite3.Connection):
            def backup(self, destination, **kwargs):
                actual = kwargs["progress"]
                def late(status, remaining, total):
                    if status == sqlite3.SQLITE_DONE:
                        time.sleep(0.15)
                    actual(status, remaining, total)
                kwargs["progress"] = late
                return super().backup(destination, **kwargs)
        with patch.object(candidate.sqlite3, "connect", side_effect=lambda *x, **k: CONNECT(*x, **k, factory=LateConnection)):
            result = candidate.worker(a)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["reason"], "deadline_exceeded")
        self.assertFalse(result["destination_usable"])
        self.assertGreater((root/"backup.sqlite").stat().st_size, 0)
        PROOFS.append({"case": "late_done_callback", "completed_bytes_retained_but_unusable": True,
                       "receipt": result})

    def test_existing_destination_never_overwritten_or_source_opened(self):
        fx = self.fixture()
        a = fx.request()
        root = claim(a)
        sentinel = b"SYNTHETIC-EXISTING-DESTINATION"
        (root/"backup.sqlite").write_bytes(sentinel)
        with patch.object(candidate.sqlite3, "connect", side_effect=AssertionError("SQLite opened")) as opened:
            result = candidate.worker(a)
        self.assertEqual(opened.call_count, 0)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual((root/"backup.sqlite").read_bytes(), sentinel)
        self.assertFalse(result["destination_usable"])

    def test_cross_process_replay_success_and_direct_worker_replay_rejected(self):
        fx = self.fixture()
        a = fx.request()
        _, first = cli(a)
        target = self.assert_success(a, first)
        before = target.read_bytes()
        p, second = cli(a)
        self.assertEqual(p.returncode, 3)
        self.assertEqual(second["reason"], "operation_already_claimed")
        with patch.object(candidate.sqlite3, "connect", side_effect=AssertionError("SQLite opened")) as opened:
            with self.assertRaises(FileExistsError):
                candidate.worker(a)
            self.assertEqual(opened.call_count, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_expiry_pin_permissions_and_path_fail_before_claim(self):
        fx = self.fixture()
        cases = []
        a = fx.request(); a["expires_at_utc"] = "2000-01-01T00:00:00Z"; cases.append(a)
        a = fx.request(); a["issued_at_utc"] = "2099-01-01T00:00:00Z"; cases.append(a)
        a = fx.request(); a["candidate_sha256"] = "0"*64; cases.append(a)
        a = fx.request(); a["permissions"]["source_vfs_side_effects"] = False; cases.append(a)
        a = fx.request(); a["destination_dir"] = str(fx.source); cases.append(a)
        a = fx.request(); a["target"]["commit"] = "wrong"; cases.append(a)
        for a in cases:
            with self.subTest(reason_fields=a["operation_id"]):
                with patch.object(candidate.sqlite3, "connect", side_effect=AssertionError("SQLite opened")):
                    with self.assertRaises(candidate.Rejected):
                        candidate.run(a)
                self.assertFalse((fx.root/("004f-backup-"+a["operation_id"])).exists())

    def test_source_hardlink_and_unknown_header_fail_closed(self):
        fx = self.fixture()
        os.link(fx.source, fx.root/"duplicate.sqlite")
        with self.assertRaisesRegex(candidate.Rejected, "source_metadata_rejected"):
            candidate.run(fx.request())
        bad = self.fixture()
        raw = bad.source.read_bytes()
        bad.source.write_bytes(raw[:18]+b"\x01\x02"+raw[20:])
        a = bad.request()
        _, result = cli(a)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["source_open_attempts"], 0)
        self.assertEqual(result["reason"], "source_header_rejected")
        self.assertFalse((Path(a["destination_dir"])/"backup.sqlite").exists())
        self.assertTrue((Path(a["destination_dir"])/"receipt.json").exists())

    def test_integrity_failure_withholds_details_and_preserves_copy(self):
        fx = self.fixture()
        a = fx.request()
        root = claim(a)
        class BadIntegrity(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if sql == "PRAGMA main.integrity_check":
                    class Rows:
                        def fetchall(self):
                            return [("SYNTHETIC_PRIVATE_DIAGNOSTIC",)]
                    return Rows()
                return super().execute(sql, *args, **kwargs)
        with patch.object(candidate.sqlite3, "connect", side_effect=lambda *x, **k: CONNECT(*x, **k, factory=BadIntegrity)):
            result = candidate.worker(a)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["reason"], "destination_integrity_failed")
        self.assertFalse(result["destination_usable"])
        self.assertTrue((root/"backup.sqlite").exists())
        self.assertNotIn("SYNTHETIC_PRIVATE_DIAGNOSTIC", candidate.canonical(result).decode())

    def test_duplicate_json_and_unapproved_dev_capability_rejected(self):
        with self.assertRaisesRegex(candidate.Rejected, "duplicate_json_key"):
            candidate.parse(b'{"mode":"synthetic","mode":"dev"}')
        fx = self.fixture()
        a = fx.request(); a["mode"] = "dev"
        with self.assertRaisesRegex(candidate.Rejected, "permission_mismatch"):
            candidate.validate(a)

    def test_claim_hardlink_rejected_before_source_bytes_or_sqlite(self):
        fx = self.fixture()
        a = fx.request()
        root = claim(a)
        os.link(root/"claim.json", fx.root/"claim-alias.json")
        with patch.object(candidate.sqlite3, "connect", side_effect=AssertionError("SQLite opened")):
            with self.assertRaisesRegex(candidate.Rejected, "claim_file_rejected"):
                candidate.worker(a)
        self.assertFalse((root/"worker-started.json").exists())
        self.assertFalse((root/"backup.sqlite").exists())

    def test_claim_write_failure_still_reports_consumed_and_no_source_open(self):
        fx = self.fixture()
        a = fx.request()
        actual = candidate.write_new
        def failed_claim(path, payload):
            if path.name == "claim.json":
                raise OSError("SYNTHETIC_PRIVATE_WRITE_DIAGNOSTIC")
            return actual(path, payload)
        with patch.object(candidate, "write_new", side_effect=failed_claim):
            result = candidate.run(a)
        self.assertTrue(result["consumed"])
        self.assertTrue(result["receipt_persisted"])
        self.assertEqual(result["reason"], "claim_write_failed")
        self.assertEqual(result["source_opens"], 0)
        self.assertFalse(result["worker_started"])
        self.assertTrue(Path(a["destination_dir"]).is_dir())
        with self.assertRaisesRegex(candidate.Rejected, "operation_already_claimed"):
            candidate.run(a)
        self.assertNotIn("SYNTHETIC_PRIVATE_WRITE_DIAGNOSTIC", candidate.canonical(result).decode())

    def test_final_receipt_write_failure_never_promotes_copy(self):
        fx = self.fixture()
        a = fx.request()
        actual = candidate.write_new
        def failed_receipt(path, payload):
            if path.name == "receipt.json":
                raise OSError("SYNTHETIC_PRIVATE_WRITE_DIAGNOSTIC")
            return actual(path, payload)
        with patch.object(candidate, "write_new", side_effect=failed_receipt):
            result = candidate.run(a)
        self.assertEqual(result["status"], "RECEIPT_WRITE_FAILED_CONSUMED")
        self.assertTrue(result["consumed"])
        self.assertFalse(result["receipt_persisted"])
        self.assertFalse(result["destination_usable"])
        self.assertTrue((Path(a["destination_dir"])/"backup.sqlite").exists())
        self.assertTrue(result["worker_reaped"])
        self.assertNotIn("SYNTHETIC_PRIVATE_WRITE_DIAGNOSTIC", candidate.canonical(result).decode())

    def test_parent_interruption_reaps_worker_and_preserves_claim(self):
        fx = self.fixture()
        a = fx.request()
        class Child:
            stdin = stdout = stderr = None
            returncode = None
            terminated = False
            def communicate(self, *_, **__):
                raise KeyboardInterrupt
            def poll(self):
                return self.returncode
            def terminate(self):
                self.terminated = True
            def wait(self, **_):
                self.returncode = -15
                return self.returncode
            def kill(self):
                raise AssertionError("terminate should have sufficed")
        child = Child()
        with patch.object(candidate.subprocess, "Popen", return_value=child):
            result = candidate.run(a)
        self.assertTrue(child.terminated)
        self.assertTrue(result["worker_reaped"])
        self.assertEqual(result["status"], "UNKNOWN_CONSUMED")
        self.assertTrue(result["consumed"])
        self.assertFalse(result["destination_usable"])
        self.assertIsNone(result["source_opens"])
        self.assertTrue((Path(a["destination_dir"])/"claim.json").exists())

class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test.id(), "status": "PASS"})

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Qualification)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    evidence = {"status": "SYNTHETIC_QUALIFIED" if result.wasSuccessful() else "SYNTHETIC_FAILED",
                "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                "results": result.records, "proofs": PROOFS, "python": sys.version,
                "sqlite_version": sqlite3.sqlite_version, "candidate_sha256": candidate.code_sha(),
                "test_source_sha256": candidate.digest(Path(__file__).read_bytes()),
                "fixtures_retained": True, "live_executed": False, "dev_authority_issued": False}
    (ROOT/"evidence"/"test-results.json").write_bytes(candidate.canonical(evidence)+b"\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
