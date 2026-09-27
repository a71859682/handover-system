"""VR2 behavior tests using fresh disposable DBs and the accepted VR1 fixture.

The parent never imports app. Only --guard-child uses the VR1 isolated bootstrap
with a fresh APP_DB_PATH, disabled backend switching and SQLite/network audit.
No VR1 unittest case is collected or rerun by this module.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
import test_vendor_roster_service as fixture
from services import vendor_access_service as access
from services import vendor_roster_service as roster

ADMIN = access.InternalActor(601)  # Same numeric ID as a vendor owner; separate domain.
M1, M2, MP = [str(uuid.UUID(int=value, version=4)) for value in (11, 12, 13)]
A1, A2, B1 = [str(uuid.UUID(int=value, version=4)) for value in (21, 22, 23)]
BA1, BA2, BA3, BB1 = [str(uuid.UUID(int=value, version=4)) for value in (31, 32, 33, 34)]


def all_site(site=101, *, assignment=None):
    return {"site_id": site, "assignment_id": assignment or (A1 if site == 101 else A2), "mode": "ALL", "task_ids": []}


def selected(tasks, site=101):
    return {**all_site(site), "mode": "SELECTED", "task_ids": tasks}


def task_ids(result):
    return [task["task_id"] for site in result["sites"] for sheet in site["sheets"] for task in sheet["tasks"]]


def seed(conn):
    result = roster.apply_roster(conn, fixture.roster()[:2])
    vendor, other = [result["vendor_ids"][tax] for tax in ("12275123", "96769654")]
    conn.execute("UPDATE vendor_organizations SET organization_status='active' WHERE vendor_id IN (?,?)", (vendor, other))
    conn.executemany("INSERT INTO users(id,username,password_hash,role) VALUES(?,?,?,?)",
                     [(601, "global-admin", "synthetic", "admin"), (102, "site-admin", "synthetic", "member")])
    conn.execute("INSERT INTO user_site_permissions(user_id,site_id,role) VALUES(102,101,'admin')")
    conn.executemany("INSERT INTO vendor_accounts(id,username,password_hash,vendor_name) VALUES(?,?,?,?)",
                     [(602, "member-a", "synthetic", "same old name"),
                      (603, "member-b", "synthetic", "same old name"),
                      (604, "pending", "synthetic", "same old name"),
                      (605, "unassigned-account", "synthetic", "same old name")])
    for mid, account, status in ((M1, 602, "active"), (M2, 603, "active"), (MP, 604, "pending")):
        fixture.audited_insert(conn, "vendor_organization_memberships", {
            "vendor_membership_id": mid, "vendor_id": vendor, "vendor_account_id": account,
            "membership_status": status, "membership_role": "member"})
    for aid, vid, site in ((A1, vendor, 101), (A2, vendor, 102), (B1, other, 101)):
        fixture.audited_insert(conn, "vendor_site_assignments", {
            "vendor_site_assignment_id": aid, "vendor_id": vid, "site_id": site, "assignment_status": "active"})
    for bid, vid, sheet, site, aid in ((BA1, vendor, 201, 101, A1), (BA2, vendor, 202, 101, A1),
                                      (BA3, vendor, 203, 102, A2), (BB1, other, 201, 101, B1)):
        fixture.audited_insert(conn, "sheet_vendor_bindings", {
            "sheet_vendor_binding_id": bid, "vendor_id": vid, "sheet_id": sheet, "site_id": site,
            "vendor_site_assignment_id": aid, "binding_status": "active"})
    for task, vid in ((301, vendor), (302, vendor), (303, vendor), (304, other), (305, vendor)):
        conn.execute("INSERT INTO task_vendor_assignments VALUES(?,?,'fixture','explicit_name_exact_trim','{}')", (task, vid))
    return vendor, other


def save(conn, scopes, *, membership=M1, revision=0, actor=ADMIN):
    return access.save_scopes(conn, actor=actor, membership_id=membership, scopes=scopes,
                              expected_revision=revision, reason="synthetic administration")


def guard_child(path):
    # Reuses accepted isolation before app import. Does not run VR1 tests.
    fixture.isolated_child(path, False)
    app = sys.modules["app"]
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        roster.initialize_schema(conn)
        seed(conn)
        before = fixture.snapshot(conn)
        assert app.ensure_vendor_organization_schema(conn) == "all_exact"
        access.initialize_schema(conn)
        assert app.ensure_vendor_organization_schema(conn) == "all_exact"
        save(conn, [all_site()])
        assert app.ensure_vendor_organization_schema(conn) == "all_exact"
        for name, rows in before.items():
            assert fixture.snapshot(conn)[name] == rows, name
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        conn.commit()
        assert task_ids(access.resolve_scope(conn, vendor_account_id=602)) == [301, 302, 305]
        print(json.dumps({"guard_before": "all_exact", "guard_after_ddl": "all_exact",
                          "guard_after_save": "all_exact", "protected_rows_preserved": True,
                          "effective_tasks": [301, 302, 305], "foreign_keys": 1}))


class VendorAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory(prefix="004f-vr2-")
        cls.addClassCleanup(cls.root.cleanup)
        cls.base = Path(cls.root.name) / "fresh-fixture.sqlite3"
        fixture.run_child(cls.base)

    def setUp(self):
        self.path = Path(self.root.name) / f"case-{uuid.uuid4().hex}.sqlite3"
        shutil.copyfile(self.base, self.path)
        self.conn = sqlite3.connect(self.path, factory=fixture.InjectedFailureConnection)
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("BEGIN")
        roster.initialize_schema(self.conn)
        self.vendor, self.other = seed(self.conn)
        self.protected = fixture.snapshot(self.conn)
        access.initialize_schema(self.conn)
        self.conn.commit()

    def grant(self, scopes=None, *, membership=M1, revision=0):
        self.conn.execute("BEGIN")
        result = save(self.conn, [all_site()] if scopes is None else scopes, membership=membership, revision=revision)
        self.conn.commit()
        return result

    def effective(self, account=602):
        return access.resolve_scope(self.conn, vendor_account_id=account)

    def assert_denied_unchanged(self, scopes, *, membership=M1, revision=0, actor=ADMIN, error=access.ScopeError):
        if not self.conn.in_transaction:
            self.conn.execute("BEGIN")
        before = fixture.snapshot(self.conn)
        changes = self.conn.total_changes
        with self.assertRaises(error):
            save(self.conn, scopes, membership=membership, revision=revision, actor=actor)
        self.assertEqual(before, fixture.snapshot(self.conn))
        self.assertEqual(changes, self.conn.total_changes, "validation must precede any DML")
        self.assertTrue(self.conn.in_transaction)

    def test_persistence_idempotence_audit_and_protected_data(self):
        self.assertEqual(1, self.grant([all_site(), selected([303], 102)]))
        original = self.effective()
        self.conn.close()
        self.conn = sqlite3.connect(self.path)
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(original, self.effective())
        before = fixture.snapshot(self.conn)
        self.assertEqual(1, self.grant([selected([303], 102), all_site()], revision=1))
        self.assertEqual(before, fixture.snapshot(self.conn))
        for name, rows in self.protected.items():
            self.assertEqual(rows, fixture.snapshot(self.conn)[name], name)
        event = self.conn.execute("SELECT revision,actor_id,reason,scopes_json FROM vr2_scope_events").fetchone()
        self.assertEqual((1, 601, "synthetic administration"), event[:3])
        self.assertEqual([101, 102], [s["site_id"] for s in json.loads(event[3])])

    def test_typed_internal_admin_only_and_live_role_check(self):
        for actor in (601, {"user_id": 601, "role": "admin"}, {"vendor_account_id": 601},
                      access.InternalActor(101), access.InternalActor(102), access.InternalActor(602),
                      access.InternalActor(999999), access.InternalActor(True)):
            with self.subTest(actor=actor):
                self.assert_denied_unchanged([all_site()], actor=actor)
                with self.assertRaises(access.ScopeError):
                    access.preview_scopes(self.conn, actor=actor, membership_id=M1)
        self.conn.execute("UPDATE users SET role='member' WHERE id=601")
        self.assert_denied_unchanged([all_site()])
        self.conn.rollback()
        self.assertEqual(1, self.grant())
        self.assertEqual(1, access.preview_scopes(self.conn, actor=ADMIN, membership_id=M1)["revision"])

    def test_all_intersection_grouping_names_and_dynamic_new_tasks(self):
        self.assertEqual([], task_ids(self.effective()))
        self.grant()
        result = self.effective()
        self.assertEqual([301, 302, 305], task_ids(result))
        self.assertEqual(3, result["task_count"])
        self.assertEqual([101], [s["site_id"] for s in result["sites"]])
        self.assertEqual([1, 2], [s["task_count"] for s in result["sites"][0]["sheets"]])
        self.assertNotIn("工地乙", json.dumps(result, ensure_ascii=False))
        self.assertTrue(all(t["task_name"] == "同名工項" for s in result["sites"] for h in s["sheets"] for t in h["tasks"]))
        for tid, sheet in ((401, 201), (402, 203), (403, 204)):
            self.conn.execute("INSERT INTO tasks(id,sheet_id,col_index,name,vendor) VALUES(?,?,?,?,?)", (tid, sheet, tid, "同名工項", "untrusted"))
            self.conn.execute("INSERT INTO task_vendor_assignments VALUES(?,?,'fixture','explicit_name_exact_trim','{}')", (tid, self.vendor))
        self.conn.execute("INSERT INTO sheets(id,name,site_id) VALUES(204,'新表格',101)")
        self.conn.commit()
        self.assertEqual([301, 401, 302, 305], task_ids(self.effective()))
        fixture.audited_insert(self.conn, "sheet_vendor_bindings", {
            "sheet_vendor_binding_id": str(uuid.uuid4()), "vendor_id": self.vendor,
            "sheet_id": 204, "site_id": 101, "vendor_site_assignment_id": A1, "binding_status": "active"})
        self.conn.commit()
        self.assertEqual([301, 401, 302, 305, 403], task_ids(self.effective()))
        self.assertEqual(2, self.grant([all_site(), all_site(102)], revision=1))
        self.assertIn(402, task_ids(self.effective()))

    def test_selected_empty_switch_and_complete_set_removal(self):
        self.grant([selected([305, 301]), all_site(102)])
        self.assertEqual([301, 305, 303], task_ids(self.effective()))
        self.grant([selected([])], revision=1)
        self.assertEqual([], task_ids(self.effective()))
        self.grant([all_site()], revision=2)
        self.assertEqual(0, self.conn.execute("SELECT count(*) FROM vr2_selected_tasks").fetchone()[0])
        self.grant([selected([302])], revision=3)
        self.assertEqual([302], task_ids(self.effective()))
        self.grant([], revision=4)
        self.assertEqual([], task_ids(self.effective()))
        self.assertEqual(5, self.conn.execute("SELECT revision FROM vr2_scope_versions").fetchone()[0])
        self.assertEqual(0, self.conn.execute("SELECT count(*) FROM vr2_site_scopes").fetchone()[0])
        self.assertEqual(0, self.conn.execute("SELECT count(*) FROM vr2_selected_tasks").fetchone()[0])

    def test_selected_does_not_include_new_task(self):
        self.grant([selected([301])])
        self.conn.execute("INSERT INTO tasks(id,sheet_id,col_index,name) VALUES(401,201,401,'同名工項')")
        self.conn.execute("INSERT INTO task_vendor_assignments VALUES(401,?,'fixture','explicit_name_exact_trim','{}')", (self.vendor,))
        self.conn.commit()
        self.assertEqual([301], task_ids(self.effective()))

    def test_bad_ids_modes_and_complete_batch_reject_before_writes(self):
        invalid = [selected([999999]), selected([304]), selected([303]), selected([307]),
                   selected([True]), selected(["301"]), selected([301, 301]),
                   {"site_id": 101, "task_ids": []}, {**all_site(), "mode": "all"},
                   {**all_site(), "task_ids": [301]},
                   {**all_site(), "vendor_id": self.vendor},
                   {**all_site(), "assignment_id": B1},
                   all_site(True), all_site(999999)]
        for bad in invalid:
            with self.subTest(bad=bad):
                self.assert_denied_unchanged([all_site(102), bad])
        self.assert_denied_unchanged([all_site(), all_site()])
        self.conn.execute("UPDATE sheet_vendor_bindings SET binding_status='inactive' WHERE sheet_vendor_binding_id=?", (BA2,))
        self.assert_denied_unchanged([selected([302])])

    def test_missing_assignment_profile_or_retired_organization(self):
        self.conn.execute("UPDATE vendor_site_assignments SET assignment_status='inactive' WHERE vendor_site_assignment_id=?", (A1,))
        with self.assertRaisesRegex(access.ScopeError, "尚未建立廠商工地關係"):
            save(self.conn, [all_site()])
        self.assertEqual(0, self.conn.execute("SELECT count(*) FROM vr2_scope_versions").fetchone()[0])
        self.conn.rollback()
        self.conn.execute("UPDATE vendor_organizations SET organization_status='retired' WHERE vendor_id=?", (self.vendor,))
        self.assert_denied_unchanged([all_site()])
        self.conn.rollback()
        # Old-name owner has no VR1 profile and cannot use roster identity.
        self.assert_denied_unchanged([all_site()], membership="22222222-2222-4222-8222-222222222222")

    def test_pending_disabled_and_inactive_configuration_is_not_access(self):
        self.conn.execute("UPDATE vendor_accounts SET is_active=0 WHERE id=604")
        self.conn.execute("UPDATE vendor_organizations SET organization_status='disabled' WHERE vendor_id=?", (self.vendor,))
        self.assertEqual(1, save(self.conn, [selected([301])], membership=MP))
        preview = access.preview_scopes(self.conn, actor=ADMIN, membership_id=MP)
        self.assertEqual([301], task_ids(preview["configured_scope"]))
        self.assertEqual([], task_ids(preview["effective_scope"]))
        self.assertEqual("account_inactive", preview["inactive_reason"])
        self.conn.commit()
        self.assertEqual([], task_ids(self.effective(604)))
        self.conn.execute("UPDATE vendor_accounts SET is_active=1 WHERE id=604")
        self.conn.commit()
        self.assertEqual("membership_not_active", access.preview_scopes(self.conn, actor=ADMIN, membership_id=MP)["inactive_reason"])
        self.conn.execute("UPDATE vendor_organization_memberships SET membership_status='active' WHERE vendor_membership_id=?", (MP,))
        self.conn.commit()
        self.assertEqual("organization_not_active", self.effective(604)["reason"])
        self.conn.execute("UPDATE vendor_organizations SET organization_status='active' WHERE vendor_id=?", (self.vendor,))
        self.conn.commit()
        self.assertEqual([301], task_ids(self.effective(604)))
        with self.assertRaises(TypeError):
            access.resolve_scope(self.conn, vendor_account_id=604, ignore_active=True)

    def test_member_successor_and_other_member_independence(self):
        self.grant()
        self.grant([selected([302])], membership=M2)
        self.conn.execute("UPDATE vendor_organization_memberships SET membership_status='revoked' WHERE vendor_membership_id=?", (M1,))
        self.assert_denied_unchanged([], revision=1)
        successor = str(uuid.uuid4())
        fixture.audited_insert(self.conn, "vendor_organization_memberships", {
            "vendor_membership_id": successor, "vendor_id": self.vendor, "vendor_account_id": 602,
            "membership_status": "active", "predecessor_membership_id": M1})
        self.conn.commit()
        self.assertEqual([], task_ids(self.effective()))
        self.assertEqual([302], task_ids(self.effective(603)))
        self.grant([selected([301])], membership=successor)
        self.assertEqual([301], task_ids(self.effective()))

    def test_membership_in_place_vendor_or_account_change_rejected(self):
        self.grant()
        for column, value in (("vendor_id", self.other), ("vendor_account_id", 605)):
            with self.subTest(column=column):
                self.conn.execute(f"UPDATE vendor_organization_memberships SET {column}=? WHERE vendor_membership_id=?", (value, M1))
                self.assert_denied_unchanged([all_site()], revision=1)
                self.conn.commit()
                self.assertEqual([], task_ids(self.effective(value if column == "vendor_account_id" else 602)))
                self.conn.execute(f"UPDATE vendor_organization_memberships SET {column}=? WHERE vendor_membership_id=?", (self.vendor if column == "vendor_id" else 602, M1))
                self.conn.commit()

    def test_assignment_successor_requires_explicit_new_save(self):
        self.grant()
        successor = str(uuid.uuid4())
        self.conn.execute("UPDATE vendor_site_assignments SET assignment_status='inactive' WHERE vendor_site_assignment_id=?", (A1,))
        fixture.audited_insert(self.conn, "vendor_site_assignments", {
            "vendor_site_assignment_id": successor, "vendor_id": self.vendor, "site_id": 101,
            "assignment_status": "active", "predecessor_assignment_id": A1})
        self.conn.execute("UPDATE sheet_vendor_bindings SET vendor_site_assignment_id=? WHERE vendor_site_assignment_id=?", (successor, A1))
        self.conn.commit()
        self.assertEqual([], task_ids(self.effective()))
        self.assert_denied_unchanged([all_site()], revision=1, error=access.ScopeConflict)
        self.conn.rollback()
        self.assertEqual(2, self.grant([all_site(assignment=successor)], revision=1))
        self.assertEqual([301, 302, 305], task_ids(self.effective()))

    def test_each_status_revocation_seen_on_next_request(self):
        self.grant()
        mutations = [
            ("vendor_accounts", "is_active", 0, 1, "id", 602, []),
            ("vendor_organization_memberships", "membership_status", "revoked", "active", "vendor_membership_id", M1, []),
            ("vendor_organizations", "organization_status", "disabled", "active", "vendor_id", self.vendor, []),
            ("sites", "is_active", 0, 1, "id", 101, []),
            ("vendor_site_assignments", "assignment_status", "inactive", "active", "vendor_site_assignment_id", A1, []),
            ("sheet_vendor_bindings", "binding_status", "inactive", "active", "sheet_vendor_binding_id", BA1, [302, 305]),
        ]
        writer = sqlite3.connect(self.path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA foreign_keys=ON")
        for table, field, bad, good, key, value, expected in mutations:
            with self.subTest(table=table):
                writer.execute(f"UPDATE {table} SET {field}=? WHERE {key}=?", (bad, value))
                writer.commit()
                self.assertEqual(expected, task_ids(self.effective()))
                self.assertFalse(self.conn.in_transaction)
                writer.execute(f"UPDATE {table} SET {field}=? WHERE {key}=?", (good, value))
                writer.commit()
                self.assertEqual([301, 302, 305], task_ids(self.effective()))

    def test_fk_valid_but_mismatched_relationships_and_reassignment(self):
        self.grant()
        cases = [
            ("UPDATE sheet_vendor_bindings SET site_id=102 WHERE sheet_vendor_binding_id=?", (BA1,)),
            ("UPDATE sheet_vendor_bindings SET vendor_site_assignment_id=? WHERE sheet_vendor_binding_id=?", (A2, BA1)),
            ("UPDATE sheet_vendor_bindings SET vendor_site_assignment_id=? WHERE sheet_vendor_binding_id=?", (B1, BA1)),
            ("UPDATE vendor_site_assignments SET site_id=102 WHERE vendor_site_assignment_id=?", (A1,)),
            ("UPDATE sheets SET site_id=102 WHERE id=201", ()),
            ("UPDATE task_vendor_assignments SET vendor_id=? WHERE task_id=301", (self.other,)),
        ]
        for sql, params in cases:
            with self.subTest(sql=sql, params=params):
                self.conn.execute("BEGIN")
                # Avoid the legitimate active-pair unique constraint only for
                # the assignment-site mismatch fixture, by retiring the other pair.
                if sql.startswith("UPDATE vendor_site_assignments"):
                    self.conn.execute("UPDATE vendor_site_assignments SET assignment_status='inactive' WHERE vendor_site_assignment_id=?", (A2,))
                self.conn.execute(sql, params)
                self.assertEqual([], self.conn.execute("PRAGMA foreign_key_check").fetchall())
                self.assert_denied_unchanged([selected([301])], revision=1)
                preview = access.preview_scopes(self.conn, actor=ADMIN, membership_id=M1)
                self.assertNotIn(301, task_ids(preview["effective_scope"]))
                self.conn.rollback()
        self.conn.execute("UPDATE sheet_vendor_bindings SET binding_status='inactive' WHERE sheet_vendor_binding_id=?", (BB1,))
        self.conn.execute("UPDATE sheet_vendor_bindings SET vendor_id=? WHERE sheet_vendor_binding_id=?", (self.other, BA1))
        self.conn.commit()
        self.assertEqual([302, 305], task_ids(self.effective()))

    def test_stale_editors_cannot_restore_revoked_configuration(self):
        self.grant()
        stale = access.preview_scopes(self.conn, actor=ADMIN, membership_id=M1)["revision"]
        writer = sqlite3.connect(self.path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA foreign_keys=ON")
        writer.execute("BEGIN")
        self.assertEqual(2, save(writer, [], revision=stale))
        writer.commit()
        self.assert_denied_unchanged([all_site()], revision=stale, error=access.ScopeConflict)
        self.assert_denied_unchanged([all_site()], revision=0, error=access.ScopeConflict)
        self.conn.rollback()
        self.assertEqual([], task_ids(self.effective()))

    def test_wal_stale_snapshot_writer_cannot_overwrite_new_revocation(self):
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.grant()
        self.conn.execute("BEGIN")
        stale = access.preview_scopes(self.conn, actor=ADMIN, membership_id=M1)["revision"]
        writer = sqlite3.connect(self.path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA foreign_keys=ON")
        writer.execute("BEGIN")
        save(writer, [], revision=stale)
        writer.commit()
        with self.assertRaises(sqlite3.OperationalError):
            save(self.conn, [selected([301])], revision=stale)
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()
        self.assertEqual([], task_ids(self.effective()))
        self.assertEqual(2, access.preview_scopes(self.conn, actor=ADMIN, membership_id=M1)["revision"])

    def test_resolver_rejects_caller_transaction_without_ending_it(self):
        self.grant()
        self.conn.execute("BEGIN")
        self.conn.execute("INSERT INTO meta VALUES('caller-work','preserve')")
        self.assertEqual([], task_ids(self.effective()))
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual("preserve", self.conn.execute("SELECT value FROM meta WHERE key='caller-work'").fetchone()[0])
        self.conn.rollback()
        self.assertEqual([301, 302, 305], task_ids(self.effective()))

    def test_one_request_uses_consistent_snapshot_during_concurrent_revocation(self):
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.grant()
        writer = sqlite3.connect(self.path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA foreign_keys=ON")
        fired = []
        def interleave(sql):
            if "SELECT m.vendor_id" in sql and not fired:
                fired.append(True)
                writer.execute("UPDATE vendor_accounts SET is_active=0 WHERE id=602")
                writer.commit()
        self.conn.set_trace_callback(interleave)
        result = self.effective()
        self.conn.set_trace_callback(None)
        self.assertEqual([True], fired)
        self.assertEqual([301, 302, 305], task_ids(result))
        self.assertEqual([], task_ids(self.effective()))

    def test_successful_save_never_commits_callers_other_work(self):
        self.conn.execute("BEGIN")
        self.conn.execute("INSERT INTO meta VALUES('caller-work','preserve')")
        save(self.conn, [all_site()])
        observer = sqlite3.connect(self.path)
        self.addCleanup(observer.close)
        self.assertEqual(0, observer.execute("SELECT count(*) FROM vr2_scope_versions").fetchone()[0])
        self.assertIsNone(observer.execute("SELECT value FROM meta WHERE key='caller-work'").fetchone())
        self.conn.rollback()
        self.assertEqual(0, self.conn.execute("SELECT count(*) FROM vr2_scope_versions").fetchone()[0])

    def test_midpoint_save_failure_rolls_back_own_work_only(self):
        self.grant()
        self.conn.execute("BEGIN")
        self.conn.execute("INSERT INTO meta VALUES('caller-work','preserve')")
        before = fixture.snapshot(self.conn)
        self.conn.fail_sql, self.conn.remaining = "INSERT INTO main.vr2_selected_tasks", 2
        with self.assertRaisesRegex(sqlite3.OperationalError, "injected midpoint"):
            save(self.conn, [selected([301, 302])], revision=1)
        self.assertEqual(before, fixture.snapshot(self.conn))
        self.assertTrue(self.conn.in_transaction)
        self.conn.fail_sql = None
        self.assertEqual(2, save(self.conn, [], revision=1))
        self.conn.commit()
        self.assertEqual("preserve", self.conn.execute("SELECT value FROM meta WHERE key='caller-work'").fetchone()[0])

    def test_midpoint_ddl_failure_rolls_back_own_tables_only(self):
        self.conn.execute("BEGIN")
        for name in reversed(access._SCHEMA):
            self.conn.execute(f"DROP TABLE {name}")
        self.conn.commit()
        self.conn.execute("BEGIN")
        self.conn.execute("INSERT INTO meta VALUES('caller-work','preserve')")
        before = fixture.snapshot(self.conn)
        self.conn.fail_sql, self.conn.remaining = "CREATE TABLE main.vr2_selected_tasks", 1
        with self.assertRaisesRegex(sqlite3.OperationalError, "injected midpoint"):
            access.initialize_schema(self.conn)
        self.assertEqual(before, fixture.snapshot(self.conn))
        self.assertTrue(self.conn.in_transaction)
        self.conn.fail_sql = None
        access.initialize_schema(self.conn)
        self.conn.rollback()
        self.assertIsNone(self.conn.execute("SELECT name FROM sqlite_schema WHERE name='vr2_scope_versions'").fetchone())

    def test_schema_missing_drift_view_and_trigger_fail_closed_without_writes(self):
        self.grant()
        self.conn.execute("DROP TABLE vr2_scope_events")
        before = fixture.snapshot(self.conn)
        self.assertEqual([], task_ids(self.effective()))
        self.assertEqual(before, fixture.snapshot(self.conn))
        self.conn.execute("BEGIN")
        self.conn.execute("CREATE VIEW vr2_scope_events AS SELECT 1 AS wrong")
        self.assert_denied_unchanged([], revision=1)
        with self.assertRaises(access.ScopeError):
            access.initialize_schema(self.conn)
        self.conn.rollback()
        self.conn.execute("BEGIN")
        access.initialize_schema(self.conn)
        self.conn.commit()
        for prefix in ("", "TEMP "):
            self.conn.execute(f"CREATE {prefix}TRIGGER unexpected AFTER INSERT ON main.vr2_site_scopes BEGIN UPDATE tasks SET name='corrupted'; END")
            self.assert_denied_unchanged([selected([301])], revision=1)
            self.conn.rollback()
            self.assertEqual([], task_ids(self.effective()))
            self.conn.execute("DROP TRIGGER unexpected")
        self.conn.execute("ALTER TABLE vr2_site_scopes ADD COLUMN unexpected TEXT")
        self.assertEqual([], task_ids(self.effective()))

    def test_temp_identity_scope_and_task_shadows_cannot_grant_or_write(self):
        self.grant()
        for name in ("users", "vendor_accounts", "vendor_organization_memberships", "tasks", "vr2_site_scopes"):
            with self.subTest(table=name):
                self.conn.execute(f"CREATE TEMP TABLE {name} AS SELECT * FROM main.{name}")
                self.assertEqual([], task_ids(self.effective()))
                self.assert_denied_unchanged([], revision=1)
                self.conn.rollback()
                self.conn.execute(f"DROP TABLE temp.{name}")
        self.conn.row_factory = sqlite3.Row
        self.assertEqual([301, 302, 305], task_ids(self.effective()))

    def test_foreign_keys_required_and_real_constraints_enforced(self):
        with self.assertRaisesRegex(access.ScopeError, "caller_transaction"):
            access.initialize_schema(self.conn)
        self.conn.execute("PRAGMA foreign_keys=OFF")
        self.conn.execute("BEGIN")
        with self.assertRaisesRegex(access.ScopeError, "foreign_keys"):
            access.initialize_schema(self.conn)
        self.assertEqual([], task_ids(self.effective()))
        self.conn.rollback()
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.grant()
        for sql, params in (("UPDATE vr2_site_scopes SET assignment_id=?", (str(uuid.uuid4()),)),
                            ("INSERT INTO vr2_selected_tasks VALUES(?,?,?)", (M1, 101, 99999)),
                            ("DELETE FROM vendor_organization_memberships WHERE vendor_membership_id=?", (M1,))):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(sql, params)
        self.assertEqual([], self.conn.execute("PRAGMA foreign_key_check").fetchall())

    def test_ambiguous_membership_fails_closed_even_with_corrupt_core_index(self):
        self.grant()
        self.conn.execute("DROP INDEX uq_vendor_organization_memberships_active_account")
        fixture.audited_insert(self.conn, "vendor_organization_memberships", {
            "vendor_membership_id": str(uuid.uuid4()), "vendor_id": self.other,
            "vendor_account_id": 602, "membership_status": "active"})
        self.conn.commit()
        self.assertEqual([], task_ids(self.effective()))
        self.assertEqual("no_unique_active_membership", self.effective()["reason"])

    def test_corrupt_mode_is_not_treated_as_all(self):
        self.grant()
        self.conn.execute("PRAGMA ignore_check_constraints=ON")
        self.conn.execute("UPDATE vr2_site_scopes SET mode='BROKEN'")
        self.conn.commit()
        self.conn.execute("PRAGMA ignore_check_constraints=OFF")
        self.assertEqual([], task_ids(self.effective()))

    def test_resolver_is_read_only_and_no_app_import_in_parent(self):
        self.grant()
        before = fixture.snapshot(self.conn)
        denied_writes = []
        def authorizer(action, a, b, database, trigger):
            if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE, sqlite3.SQLITE_CREATE_TABLE):
                denied_writes.append((action, a))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.conn.set_authorizer(authorizer)
        self.assertEqual([301, 302, 305], task_ids(self.effective()))
        self.conn.set_authorizer(None)
        self.assertEqual([], denied_writes)
        self.assertEqual(before, fixture.snapshot(self.conn))
        self.assertNotIn("app", sys.modules)

    def test_actual_four_table_guard_accepts_schema_and_behavior(self):
        with tempfile.TemporaryDirectory(prefix="004f-vr2-guard-") as directory:
            path = Path(directory) / "fresh-fixture.sqlite3"
            env = os.environ.copy()
            env.update({flag: "false" for flag in fixture.FLAGS})
            env.update(APP_DB_PATH=str(path.resolve()), DATABASE_URL="", DUAL_WRITE_TABLES="", PYTHONDONTWRITEBYTECODE="1")
            child = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--guard-child", str(path)],
                                   cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, child.returncode, child.stdout + child.stderr)
        result = json.loads(child.stdout.strip().splitlines()[-1])
        self.assertEqual(["all_exact"] * 3, [result[k] for k in ("guard_before", "guard_after_ddl", "guard_after_save")])
        self.assertTrue(result["protected_rows_preserved"])
        self.assertEqual([301, 302, 305], result["effective_tasks"])
        self.assertEqual(1, result["foreign_keys"])
        self.assertNotIn("app", sys.modules)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--guard-child":
        guard_child(Path(sys.argv[2]))
    else:
        unittest.main()
