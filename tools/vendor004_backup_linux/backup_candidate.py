"""Bounded whole-SQLite backup candidate. No network, app import or source SQL.

DEV interface exists for separate exact approval; current qualification is synthetic only.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

SCHEMA = "004F_ONLINE_BACKUP_INPUT_R02"
TARGET = {"workspace_id": "tea-d8vmr4ok1i2s73etn1tg",
          "service_id": "srv-d8vqk58k1i2s73f1v7sg",
          "deploy_id": "dep-d9gdh64vikkc73bfkua0",
          "commit": "ef0554d02343addf3156985aa217fc64f07e50f9",
          "disk_mount": "/var/data"}
FIELDS = {"schema", "mode", "operation_id", "candidate_sha256", "approval_reference",
          "target", "source_path", "source_device", "destination_dir", "issued_at_utc",
          "expires_at_utc", "timeout_seconds", "permissions"}
MAX_BYTES = 64 * 1024 * 1024

class Rejected(Exception):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")

def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()

def code_sha():
    return digest(Path(__file__).read_bytes())

def now():
    return dt.datetime.now(dt.timezone.utc)

def stamp():
    return now().isoformat().replace("+00:00", "Z")

def parse_time(value):
    if type(value) is not str or not value.endswith("Z"):
        raise Rejected("invalid_utc_time")
    try:
        return dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise Rejected("invalid_utc_time") from None

def parse(raw):
    if len(raw) > 8192:
        raise Rejected("input_size_limit")
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise Rejected("duplicate_json_key")
            result[k] = v
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rejected("nonfinite_json")))
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected("invalid_json") from None

def write_new(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(canonical(payload) + b"\n")
        out.flush()
        os.fsync(out.fileno())

def file_meta(path):
    info = path.stat()
    return {"device": info.st_dev, "inode": info.st_ino, "bytes": info.st_size,
            "mtime_ns": info.st_mtime_ns, "nlink": info.st_nlink}

def sidecars(path):
    return {suffix: Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")}

def validate(a):
    if type(a) is not dict or set(a) != FIELDS or a["schema"] != SCHEMA:
        raise Rejected("input_schema_mismatch")
    if a["mode"] not in ("synthetic", "dev"):
        raise Rejected("mode_rejected")
    dev = a["mode"] == "dev"
    expected = {"source_backup_page_read": True, "source_sql_write": False,
                "source_vfs_side_effects": True, "destination_create_and_write": True,
                "destination_normalize": True, "receipt_write": True,
                "raw_database_export": False, "dev_execution_authorized": dev}
    if (type(a["permissions"]) is not dict or a["permissions"] != expected
            or any(type(v) is not bool for v in a["permissions"].values())):
        raise Rejected("permission_mismatch")
    if a["target"] != TARGET or type(a["target"]) is not dict:
        raise Rejected("target_mismatch")
    if a["candidate_sha256"] != code_sha():
        raise Rejected("candidate_pin_mismatch")
    if (type(a["operation_id"]) is not str
            or re.fullmatch(r"[A-F0-9]{16}", a["operation_id"]) is None
            or type(a["approval_reference"]) is not str
            or re.fullmatch(r"[A-Za-z0-9_-]{8,96}", a["approval_reference"]) is None):
        raise Rejected("operation_or_approval_reference_invalid")
    issued, expiry = parse_time(a["issued_at_utc"]), parse_time(a["expires_at_utc"])
    if not issued <= now() < expiry or not 0 < (expiry-issued).total_seconds() <= 900:
        raise Rejected("expired_or_invalid_window")
    if type(a["timeout_seconds"]) not in (float, int) or not 0.1 <= a["timeout_seconds"] <= 60:
        raise Rejected("timeout_invalid")
    if type(a["source_device"]) is not int or a["source_device"] < 0:
        raise Rejected("source_device_invalid")
    if any(type(a[k]) is not str or len(a[k]) > 1024 for k in ("source_path", "destination_dir")):
        raise Rejected("path_invalid")
    source, directory = Path(a["source_path"]), Path(a["destination_dir"])
    if dev:
        if os.name != "posix" or source != Path("/var/data/site.db") or a["source_device"] != 66326:
            raise Rejected("dev_locator_mismatch")
        base = Path("/var/data")
    else:
        base = source.parent
        if (source.name != "source.sqlite" or base.parent != Path(tempfile.gettempdir()).resolve()
                or re.fullmatch(r"vendor004f-backup-synthetic-[A-Za-z0-9_-]+", base.name) is None):
            raise Rejected("synthetic_path_out_of_scope")
    if (not source.is_absolute() or source.resolve() != source or source.is_symlink()
            or base.resolve() != base or base.is_symlink()
            or directory != base / ("004f-backup-" + a["operation_id"])):
        raise Rejected("path_binding_mismatch")
    info = source.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & 0x400
            or info.st_dev != a["source_device"] or base.stat().st_dev != info.st_dev
            or not 100 <= info.st_size <= MAX_BYTES):
        raise Rejected("source_metadata_rejected")
    return source, directory, expiry

def worker(a):
    source, directory, expiry = validate(a)
    directory_info = directory.lstat()
    claim_path = directory / "claim.json"
    if (not stat.S_ISDIR(directory_info.st_mode) or directory.is_symlink()
            or getattr(directory_info, "st_file_attributes", 0) & 0x400
            or directory.resolve() != directory or directory_info.st_dev != a["source_device"]
            or (os.name == "posix" and (directory_info.st_mode & 0o077
                                       or directory_info.st_uid != os.geteuid()))):
        raise Rejected("claim_directory_rejected")
    claim_info = claim_path.lstat()
    if (not stat.S_ISREG(claim_info.st_mode) or claim_path.is_symlink()
            or getattr(claim_info, "st_file_attributes", 0) & 0x400
            or claim_info.st_nlink != 1 or claim_info.st_size > 8192):
        raise Rejected("claim_file_rejected")
    claim = parse(claim_path.read_bytes())
    if claim != {"input_sha256": digest(canonical(a)), "operation_id": a["operation_id"]}:
        raise Rejected("claim_mismatch")
    write_new(directory / "worker-started.json", {"utc": stamp(), "pid": os.getpid()})
    destination = directory / "backup.sqlite"
    result = {"status": "FAILED", "stage": "claimed", "source_open_attempts": 0,
              "source_opens": 0, "source_sql_statements": 0, "source_authorizer_calls": 0,
              "destination_opens": 0, "backup_done": False, "progress_callbacks": 0,
              "source_vfs_writes": "NOT_MEASURED_POSSIBLE", "destination_usable": False}
    deadline = time.monotonic() + min(float(a["timeout_seconds"]), (expiry-now()).total_seconds())
    def check():
        if time.monotonic() >= deadline or now() >= expiry:
            raise Rejected("deadline_exceeded")
    src = dst = None
    try:
        check()
        result["source_before"] = file_meta(source)
        result["source_sidecars_before"] = sidecars(source)
        with source.open("rb") as stream:
            header = stream.read(100)
        page_size = int.from_bytes(header[16:18], "big")
        page_size = 65536 if page_size == 1 else page_size
        if (len(header) != 100 or header[:16] != b"SQLite format 3\0"
                or header[18:20] not in (b"\x01\x01", b"\x02\x02")
                or page_size < 512 or page_size > 65536 or page_size & (page_size-1)):
            raise Rejected("source_header_rejected")
        result["source_header_versions"] = list(header[18:20])
        if shutil.disk_usage(directory).free < MAX_BYTES * 3:
            raise Rejected("insufficient_free_space")
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        result["stage"] = "destination_reserved"
        check()
        result["source_open_attempts"] += 1
        src = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=0.05, isolation_level=None)
        result["source_opens"] += 1
        def deny_source_sql(*_):
            result["source_authorizer_calls"] += 1
            return sqlite3.SQLITE_DENY
        def source_trace(_):
            result["source_sql_statements"] += 1
        src.set_authorizer(deny_source_sql)
        src.set_trace_callback(source_trace)
        dst = sqlite3.connect(destination.as_uri() + "?mode=rw", uri=True, timeout=0.05, isolation_level=None)
        result["destination_opens"] += 1
        def progress(status, remaining, total):
            result["progress_callbacks"] += 1
            check()
            if (total * page_size > MAX_BYTES or source.stat().st_size > MAX_BYTES
                    or destination.stat().st_size > MAX_BYTES):
                raise Rejected("backup_size_limit")
            result["backup_remaining"] = remaining
            result["backup_total_pages"] = total
            if status == sqlite3.SQLITE_DONE:
                result["backup_done"] = True
        result["stage"] = "backup"
        src.backup(dst, pages=32, progress=progress, sleep=0.01)
        check()
        if not result["backup_done"] or result["source_sql_statements"] or result["source_authorizer_calls"]:
            raise Rejected("backup_completion_or_source_sql_rejected")
        result["stage"] = "destination_validation"
        dst.set_progress_handler(lambda: int(time.monotonic() >= deadline or now() >= expiry), 1000)
        if dst.execute("PRAGMA main.journal_mode=DELETE").fetchone() != ("delete",):
            raise Rejected("destination_rollback_mode_failed")
        if dst.execute("PRAGMA main.integrity_check").fetchall() != [("ok",)]:
            raise Rejected("destination_integrity_failed")
        result["integrity_ok"] = True
        dst.close(); dst = None
        src.close(); src = None
        check()
        result["source_after"] = file_meta(source)
        result["source_sidecars_after"] = sidecars(source)
        if any(result["source_before"][k] != result["source_after"][k] for k in ("device", "inode", "nlink")):
            raise Rejected("source_file_identity_changed")
        if not 100 <= destination.stat().st_size <= MAX_BYTES:
            raise Rejected("destination_size_limit")
        raw = destination.read_bytes()
        if (not 100 <= len(raw) <= MAX_BYTES or raw[:16] != b"SQLite format 3\0"
                or raw[18:20] != b"\x01\x01" or any(sidecars(destination).values())):
            raise Rejected("destination_header_or_sidecars_rejected")
        os.chmod(destination, stat.S_IRUSR)
        if destination.stat().st_mode & 0o222:
            raise Rejected("destination_readonly_mode_failed")
        check()
        result.update(status="SNAPSHOT_CREATED", stage="completed", destination_usable=True,
                      destination_bytes=len(raw), destination_sha256=digest(raw),
                      destination_header_versions=[1, 1], destination_sidecars=sidecars(destination),
                      access_mode_readonly=True, immutable_storage_proven=False)
    except Rejected as exc:
        result["reason"] = str(exc)
    except sqlite3.Error:
        result["reason"] = "sqlite_error_details_withheld"
    except (OSError, ValueError):
        result["reason"] = "filesystem_or_input_error_details_withheld"
    finally:
        for conn in (dst, src):
            if conn is not None:
                try:
                    conn.close()
                except sqlite3.Error:
                    result.update(status="FAILED", destination_usable=False, reason="close_failed")
    return result

class Cancellation:
    """Signals only set state; they cannot unwind Popen bookkeeping or cleanup."""
    def __init__(self):
        self.requested = False
        self.last_signal = None
        self.previous = {}

    def handle(self, signum, _frame):
        self.requested = True
        self.last_signal = signum

    def __enter__(self):
        for name in ("SIGINT", "SIGTERM", "SIGHUP"):
            if hasattr(signal, name):
                number = getattr(signal, name)
                self.previous[number] = signal.signal(number, self.handle)
        return self

    def __exit__(self, *_):
        for number, handler in self.previous.items():
            signal.signal(number, handler)

def reap(child):
    if child is None:
        return True
    def confirmed():
        try:
            return child.poll() is not None
        except (Exception, KeyboardInterrupt):
            return False
    if confirmed():
        return True
    started = time.monotonic()
    # Fixed deadlines: signals do not restart either wait. System calls may still
    # block in the kernel; this is not a whole-command wall-clock guarantee.
    for action, deadline in ((child.terminate, started + 2), (child.kill, started + 4)):
        try:
            action()
        except (Exception, KeyboardInterrupt):
            pass
        try:
            child.wait(timeout=max(0, deadline-time.monotonic()))
        except (Exception, KeyboardInterrupt):
            pass
        if confirmed():
            return True
    return confirmed()

def run(a):
    with Cancellation() as cancellation:
        return supervised_run(a, cancellation)

def supervised_run(a, cancellation):
    _, directory, expiry = validate(a)
    # Every fallible input/code/time/path preparation precedes the one-use mkdir.
    payload = canonical(a)
    input_sha = digest(payload)
    receipt_path = directory / "receipt.json"
    claim_path = directory / "claim.json"
    argv = [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()), "--worker"]
    claim_payload = {"input_sha256": input_sha, "operation_id": a["operation_id"]}
    receipt = {"operation_id": a["operation_id"], "input_sha256": input_sha,
               "candidate_sha256": code_sha(), "mode": a["mode"], "target": TARGET,
               "started_utc": stamp(), "consumed": False, "dev_live_qualified": False,
               "raw_database_exported": False, "automatic_retry": False,
               "stage": "directory_claimed", "worker_started": False, "source_opens": 0,
               "receipt_persisted": False, "status": "UNKNOWN_CONSUMED",
               "destination_usable": False, "remaining_files_preserved": True,
               "timeout_scope": "WORKER_SUPERVISION_NOT_WHOLE_COMMAND",
               "runtime": {"python": list(sys.version_info[:3]), "sqlite": sqlite3.sqlite_version,
                            "platform": sys.platform, "posix_permission_checks": os.name == "posix"}}
    child = None
    consumed = False
    def check_cancel():
        if cancellation.requested:
            raise Rejected("cancellation_requested")
    check_cancel()
    try:
        try:
            os.mkdir(directory, 0o700)  # One-use within trusted parent namespace.
        except FileExistsError:
            raise Rejected("operation_already_claimed") from None
        consumed = True  # Immediately protected; no fallible metadata in this gap.
        receipt["consumed"] = True
        check_cancel()
        write_new(claim_path, claim_payload)
        receipt["stage"] = "claim_persisted"
        check_cancel()
        limit = min(float(a["timeout_seconds"]), (expiry-now()).total_seconds())
        if limit <= 0:
            raise Rejected("expired_before_worker")
        deadline = time.monotonic() + limit
        child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Keep the returned handle before observing cancellation or elapsed spawn.
        receipt.update(worker_started=True, source_opens=None, stage="worker_started")
        pending_input = payload
        while True:
            check_cancel()
            remaining = min(deadline-time.monotonic(), (expiry-now()).total_seconds())
            if remaining <= 0:
                receipt.update(status="TIMEOUT_CONSUMED", destination_usable=False,
                               counters="UNKNOWN_NO_TERMINAL_RECEIPT")
                break
            try:
                output, errors = child.communicate(pending_input, timeout=min(0.1, remaining))
            except subprocess.TimeoutExpired:
                pending_input = None  # communicate retains pending input internally.
                continue
            check_cancel()
            if time.monotonic() >= deadline or now() >= expiry:
                receipt.update(status="TIMEOUT_CONSUMED", destination_usable=False,
                               counters="UNKNOWN_NO_TERMINAL_RECEIPT")
                break
            if child.returncode != 0 or len(output) > 65536:
                raise Rejected("worker_terminal_evidence_rejected")
            terminal = parse(output)
            if type(terminal) is not dict or terminal.get("status") not in ("SNAPSHOT_CREATED", "FAILED"):
                raise Rejected("worker_terminal_schema_rejected")
            receipt.update(terminal)
            receipt.update(stderr_bytes=len(errors), stderr_sha256=digest(errors))
            break
    except (Exception, KeyboardInterrupt) as exc:
        if not consumed:
            raise
        receipt.update(status="UNKNOWN_CONSUMED", destination_usable=False,
                       reason=(str(exc) if isinstance(exc, Rejected) else
                               "claim_write_failed" if receipt["stage"] == "directory_claimed" else
                               "operation_failure_details_withheld"))
    finally:
        if consumed:
            try:
                receipt["worker_reaped"] = reap(child)
                receipt["worker_exit_code"] = None if child is None else child.returncode
            except (Exception, KeyboardInterrupt):
                receipt["worker_reaped"] = False
                receipt["worker_exit_code"] = None
            if not receipt["worker_reaped"]:
                receipt.update(status="UNKNOWN_CONSUMED", destination_usable=False, reason="worker_exit_unconfirmed")
            # communicate may have reader threads holding buffered pipe locks.
            # Do not block on close while child exit/EOF remains unconfirmed.
            if child is not None and receipt["worker_reaped"]:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except (Exception, KeyboardInterrupt):
                            receipt.update(status="UNKNOWN_CONSUMED", destination_usable=False,
                                           reason="pipe_close_failed")
    def record_cancel():
        receipt["cancellation_requested"] = cancellation.requested
        receipt["last_signal"] = cancellation.last_signal
        if cancellation.requested:
            receipt.update(status="UNKNOWN_CONSUMED", destination_usable=False)
            receipt.setdefault("reason", "cancellation_requested")
    record_cancel()
    try:
        receipt["finished_utc"] = stamp()
        write_new(receipt_path, receipt)
        receipt["receipt_file_sha256"] = digest(receipt_path.read_bytes())
        receipt["receipt_persisted"] = True
    except (Exception, KeyboardInterrupt):
        receipt.update(status="RECEIPT_WRITE_FAILED_CONSUMED", destination_usable=False,
                       receipt_persisted=False, reason="receipt_write_failed_details_withheld")
    record_cancel()  # A signal during finalization also prevents promotion.
    return receipt

def main():
    try:
        a = parse(sys.stdin.buffer.read(8193))
        if sys.argv[1:] == ["--worker"]:
            result = worker(a)
        elif not sys.argv[1:]:
            result = run(a)
        else:
            raise Rejected("unexpected_cli_argument")
        sys.stdout.buffer.write(canonical(result) + b"\n")
        return 0 if sys.argv[1:] == ["--worker"] or result.get("status") == "SNAPSHOT_CREATED" else 2
    except Rejected as exc:
        sys.stdout.buffer.write(canonical({"status": "REJECTED", "reason": str(exc)}) + b"\n")
        return 3
    except (Exception, KeyboardInterrupt):
        sys.stdout.buffer.write(b'{"status":"REJECTED","reason":"unexpected_error_details_withheld"}\n')
        return 4

if __name__ == "__main__":
    raise SystemExit(main())
