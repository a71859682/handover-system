"""Focused VR1 tests. app is imported ONLY by the isolated fixture subprocess.

All DBs are newly created below a TemporaryDirectory; no existing site.db is
opened. The subprocess receives its environment before importing app, whose
bootstrap is allowed only inside that fresh fixture. No parent env is changed.
"""

from __future__ import annotations

import copy
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
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from services import vendor_roster_service as service

FIXTURE = REPO / "tests/fixtures/vendor_roster_20260927.json"
FLAGS = ("USE_SQLALCHEMY_READS", "USE_SQLALCHEMY_WRITES", "USERS_READ_COMPARE",
         "DUAL_WRITE_ENABLED", "DUAL_WRITE_DRY_RUN", "DUAL_WRITE_STRICT")
OLD_VENDOR = "11111111-1111-4111-8111-111111111111"
OLD_SITE_LINK = "33333333-3333-4333-8333-333333333333"
TASK_IDS = list(range(301, 313))


def roster():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["vendors"]


def snapshot(conn):
    """Include complete rows and schema, not just selected task columns."""
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM main.sqlite_schema WHERE type='table' ORDER BY name")]
    return {table: sorted(conn.execute('SELECT * FROM main."' + table.replace('"', '""') + '"').fetchall(), key=repr)
            for table in tables}


def audited_insert(conn, table, fields):
    for prefix in ("created", "updated"):
        fields.update({f"{prefix}_actor_kind": "migration", f"{prefix}_actor_id": "fixture",
                       f"{prefix}_reason": "synthetic preservation test", f"{prefix}_source": "VR1 test",
                       f"{prefix}_correlation_id": "fixture"})
    conn.execute(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", tuple(fields.values()))


def seed_protected_rows(conn):
    conn.execute("INSERT INTO users(id,username,password_hash,role) VALUES(101,'fixture-user','synthetic-hash','member')")
    conn.executemany("INSERT INTO sites(id,site_name) VALUES(?,?)", [(101, "工地甲"), (102, "工地乙")])
    conn.executemany("INSERT INTO sheets(id,name,site_id,sort_order) VALUES(?,?,?,?)",
                     [(201, "表甲", 101, 1), (202, "表乙", 101, 2), (203, "表甲", 102, 1)])
    vendors = ["哥德", " \t昭和\u3000", "浤淋", "凱思登企業有限公司", "凱斯登", "未列名公司",
               "大英營造有限公司-新埔段", "工務所", "哥 德", None, "共用", "隆昌"]
    for offset, vendor in enumerate(vendors):
        conn.execute("INSERT INTO tasks(id,sheet_id,col_index,vendor,location,name) VALUES(?,?,?,?,?,?)",
                     (301 + offset, [201, 202, 203][offset % 3], 1001 + offset, vendor, f"位置{offset}", "同名工項"))
    conn.execute("INSERT INTO floors(id,sheet_id,sort_order,name,unit_count) VALUES(401,201,1,'一樓',1)")
    conn.execute("INSERT INTO units(id,floor_id,sort_order,name) VALUES(501,401,1,'一戶')")
    conn.execute("INSERT INTO progress(unit_id,task_id,value,updated_by) VALUES(501,301,'O',101)")
    conn.execute("INSERT INTO unit_extra(unit_id,initial_check,updated_by) VALUES(501,'2026-09-27',101)")
    conn.execute("INSERT INTO extra_fields(sheet_id,field_key,name) VALUES(201,'fixture-extra','保留欄位')")
    conn.execute("INSERT INTO unit_extra_values(unit_id,field_key,value,updated_by) VALUES(501,'fixture-extra','保留內容',101)")
    conn.execute("INSERT INTO user_site_permissions(user_id,site_id,role) VALUES(101,101,'member')")
    conn.execute("INSERT INTO vendor_accounts(id,username,password_hash,vendor_name) VALUES(601,'old-vendor','synthetic-hash','哥德')")
    conn.execute("INSERT INTO vendor_contacts(sheet_id,vendor_name,contact_name) VALUES(201,'哥德','fixture-contact')")
    conn.execute("INSERT INTO vendor_work_entries(sheet_id,vendor_name,business_date,work_content) VALUES(201,'哥德','2026-09-27','保留工作')")
    audited_insert(conn, "vendor_organizations", {"vendor_id": OLD_VENDOR, "display_name": "哥德", "organization_status": "active"})
    audited_insert(conn, "vendor_organization_memberships", {
        "vendor_membership_id": "22222222-2222-4222-8222-222222222222", "vendor_id": OLD_VENDOR,
        "vendor_account_id": 601, "membership_role": "owner", "membership_status": "active"})
    audited_insert(conn, "vendor_site_assignments", {"vendor_site_assignment_id": OLD_SITE_LINK,
        "vendor_id": OLD_VENDOR, "site_id": 101, "assignment_status": "active"})
    audited_insert(conn, "sheet_vendor_bindings", {
        "sheet_vendor_binding_id": "44444444-4444-4444-8444-444444444444", "vendor_id": OLD_VENDOR,
        "sheet_id": 201, "site_id": 101, "vendor_site_assignment_id": OLD_SITE_LINK, "binding_status": "active"})
    conn.execute("""INSERT INTO global_identities(global_identity_id,created_provenance,updated_provenance)
        VALUES('fixture-identity','fixture','fixture')""")
    conn.execute("""INSERT INTO backend_principal_mappings(backend_principal_mapping_id,global_identity_id,
        backend_kind,backend_principal_key,created_provenance,updated_provenance)
        VALUES('fixture-mapping','fixture-identity','vendor',601,'fixture','fixture')""")
    conn.execute("""INSERT INTO login_identifier_aliases(login_identifier_alias_id,global_identity_id,
        raw_alias,normalized_lookup_key,normalization_algorithm_family,normalization_profile,
        unicode_data_version,trim_conformance_profile,created_provenance,updated_provenance)
        VALUES('fixture-alias','fixture-identity','fixture','fixture','NFKC_CASEFOLD_V1',
        'NFKC_CASEFOLD_V1_UCD16_0_0','16.0.0','PY3146_UCD16_0_0_STRIP_V1','fixture','fixture')""")


def isolated_child(path, guard_check):
    """Validate isolation BEFORE the sole app import in this test module."""
    if sys.flags.optimize:
        raise RuntimeError("isolated fixture requires enabled isolation assertions")
    path = path.resolve()
    assert path.name == "fresh-fixture.sqlite3" and not path.exists()
    assert Path(os.environ["APP_DB_PATH"]).resolve() == path
    assert os.environ.get("DATABASE_URL") == ""
    assert os.environ.get("DUAL_WRITE_TABLES") == ""
    assert all(os.environ.get(flag) == "false" for flag in FLAGS)
    # Fail closed on any SQLite connection outside this one disposable file,
    # including connections attempted by app bootstrap or SQLAlchemy.
    def audit(event, args):
        if event == "sqlite3.connect":
            assert Path(args[0]).resolve() == path, "non-fixture SQLite access"
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise AssertionError("network forbidden in isolated test")
    sys.addaudithook(audit)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO meta VALUES('excel_seeded','synthetic-test')")
    import app  # noqa: isolation has been asserted before bootstrap can run
    assert app.DB_PATH.resolve() == path
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        conn.execute("BEGIN")
        seed_protected_rows(conn)
        assert app.ensure_vendor_organization_schema(conn) == "all_exact"
        stages = ["before_supplements"]
        if guard_check:
            service.initialize_schema(conn)
            assert app.ensure_vendor_organization_schema(conn) == "all_exact"
            stages.append("after_supplements")
            first = service.apply_roster(conn, roster(), task_ids=TASK_IDS)
            assert app.ensure_vendor_organization_schema(conn) == "all_exact"
            stages.append("after_import")
            second = service.apply_roster(conn, roster(), task_ids=TASK_IDS)
            assert first["vendor_ids"] == second["vendor_ids"]
            assert not second["created_vendor_ids"] and not second["assignments_created"]
            assert app.ensure_vendor_organization_schema(conn) == "all_exact"
            stages.append("after_rerun")
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        conn.commit()
        print(json.dumps({"isolated": True, "guard": stages, "foreign_keys": 1}))
    finally:
        conn.close()


def run_child(path, *, guard_check=False):
    env = os.environ.copy()
    env.update({flag: "false" for flag in FLAGS})
    env.update(APP_DB_PATH=str(path.resolve()), DATABASE_URL="", DUAL_WRITE_TABLES="", PYTHONDONTWRITEBYTECODE="1")
    child = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                            "--guard-check" if guard_check else "--build-fixture", str(path)],
                           cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")
    if child.returncode != 0:
        raise AssertionError(f"isolated child exit={child.returncode}\n{child.stdout}\n{child.stderr}")
    return json.loads(child.stdout.strip().splitlines()[-1])


class InjectedFailureConnection(sqlite3.Connection):
    fail_sql = None
    remaining = 0

    def execute(self, sql, parameters=()):
        if self.fail_sql and self.fail_sql in sql:
            self.remaining -= 1
            if self.remaining == 0:
                raise sqlite3.OperationalError("injected midpoint failure")
        return super().execute(sql, parameters)


class VendorRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory(prefix="004f-vr1-")
        cls.addClassCleanup(cls.root.cleanup)
        cls.base = Path(cls.root.name) / "fresh-fixture.sqlite3"
        cls.initial_guard = run_child(cls.base)

    def setUp(self):
        self.path = Path(self.root.name) / f"case-{uuid.uuid4().hex}.sqlite3"
        shutil.copyfile(self.base, self.path)
        self.conn = sqlite3.connect(self.path, factory=InjectedFailureConnection)
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("BEGIN")
        self.rows_before = snapshot(self.conn)
        self.schema_before = self.conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name").fetchall()
        service.initialize_schema(self.conn)
        self.entries = roster()

    def assert_preserved(self):
        after = snapshot(self.conn)
        for table, rows in self.rows_before.items():
            if table == "vendor_organizations":
                old_ids = {row[0] for row in rows}
                self.assertEqual(rows, [row for row in after[table] if row[0] in old_ids])
            else:
                self.assertEqual(rows, after[table], table)
        current_schema = self.conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name").fetchall()
        for row in self.schema_before:
            self.assertIn(row, current_schema)
        self.assertEqual([], self.conn.execute("PRAGMA foreign_key_check").fetchall())

    def assert_rejected_unchanged(self, entries, ids=(), error=service.RosterError):
        before = snapshot(self.conn)
        with self.assertRaises(error):
            service.apply_roster(self.conn, entries, task_ids=ids)
        self.assertEqual(before, snapshot(self.conn))
        self.assertTrue(self.conn.in_transaction)

    def test_16_verified_values_persistence_rerun_and_all_protected_data(self):
        expected = [
            ("12275123", "哥德廚具股份有限公司", "哥德", []),
            ("96769654", "呈旭工程有限公司", "呈旭", ["呈旭"]),
            ("69740418", "東園國際有限公司", "東園", ["東園"]),
            ("84646813", "寶勳工程有限公司", "寶勳", ["寶勳"]),
            ("33937872", "永欣鋁業股份有限公司", "永欣", ["昭和"]),
            ("12211281", "金亞金屬工業股份有限公司", "金亞", ["金亞"]),
            ("66572768", "金湧工程有限公司", "金湧", ["金湧"]),
            ("31352752", "大信建設營造股份有限公司", "大信", ["大信"]),
            ("00252579", "浤淋有限公司", "浤淋", ["浤淋"]),
            ("28760874", "凱思登企業有限公司", "凱斯登", ["凱斯登"]),
            ("16670737", "隆昌窯業股份有限公司新竹分公司", "隆昌", ["隆昌"]),
            ("53068936", "富立木業有限公司", "富立", ["富立"]),
            ("84882674", "長田實業股份有限公司", "長田", ["長田"]),
            ("29147257", "鋐賓有限公司", "鋐賓", ["鋐賓"]),
            ("23199101", "大英營造有限公司", "工務所", ["工務所"]),
            ("54502509", "喜士多開發石材有限公司", "喜士多", []),
        ]
        self.assertEqual(expected, [(r["tax_id"], r["legal_name"], r["display_name"], r["aliases"]) for r in self.entries])
        self.assertEqual(list(range(2, 18)), [r["source"]["row"] for r in self.entries])
        first = service.apply_roster(self.conn, self.entries, task_ids=TASK_IDS)
        self.assertEqual(16, len(first["created_vendor_ids"]))
        self.assertNotEqual(OLD_VENDOR, first["vendor_ids"]["12275123"])
        self.assertTrue(all(uuid.UUID(value).version == 4 for value in first["vendor_ids"].values()))
        self.assertEqual(16, self.conn.execute("SELECT count(*) FROM vendor_organizations WHERE organization_status='disabled'").fetchone()[0])
        persisted = service.list_profiles(self.conn)
        self.assertEqual(sorted(self.entries, key=lambda e: e["tax_id"]), [{k: v for k, v in p.items() if k != "vendor_id"} for p in persisted])
        hong = next(p for p in persisted if p["tax_id"] == "00252579")
        self.assertEqual((252579, "00257979", "00252579"), tuple(hong["source"][k] for k in ("original_tax_id", "user_supplement_tax_id", "verified_tax_id")))
        self.assertEqual("text", self.conn.execute("SELECT typeof(tax_id) FROM vendor_profiles WHERE tax_id='00252579'").fetchone()[0])
        self.assert_preserved()
        self.conn.commit()
        self.conn.close()
        self.conn = sqlite3.connect(self.path)
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(persisted, service.list_profiles(self.conn))
        self.conn.execute("BEGIN")
        before = snapshot(self.conn)
        second = service.apply_roster(self.conn, self.entries, task_ids=TASK_IDS)
        self.assertEqual(first["vendor_ids"], second["vendor_ids"])
        self.assertEqual([], second["created_vendor_ids"])
        self.assertEqual([], second["assignments_created"])
        self.assertEqual(before, snapshot(self.conn))
        self.assert_preserved()

    def test_task_id_matching_across_sites_sheets_and_pending(self):
        result = service.apply_roster(self.conn, self.entries, task_ids=TASK_IDS)
        tasks = {row["task_id"]: row for row in service.list_task_assignments(self.conn)}
        mapping = {301: "12275123", 302: "33937872", 303: "00252579", 304: "28760874",
                   305: "28760874", 308: "23199101", 312: "16670737"}
        for task_id, tax_id in mapping.items():
            self.assertEqual(result["vendor_ids"][tax_id], tasks[task_id]["vendor_id"])
        for task_id in (306, 307, 309, 310, 311):
            self.assertTrue(tasks[task_id]["pending"])
        self.assertEqual((201, 101), (tasks[301]["sheet_id"], tasks[301]["site_id"]))
        self.assertEqual((202, 101), (tasks[302]["sheet_id"], tasks[302]["site_id"]))
        self.assertEqual((203, 102), (tasks[303]["sheet_id"], tasks[303]["site_id"]))
        self.assertEqual(12, len(tasks))
        self.assert_preserved()

    def test_invalid_and_duplicate_tax_ids_reject_whole_batch(self):
        for invalid in (252579, True, None, "252579", "002579790", "００２５２５７９", "0025257x", "00252579 "):
            with self.subTest(invalid=invalid):
                bad = copy.deepcopy(self.entries)
                bad[-1]["tax_id"] = invalid
                self.assert_rejected_unchanged(bad, TASK_IDS)
        bad = copy.deepcopy(self.entries)
        bad[-1]["tax_id"] = bad[0]["tax_id"]
        self.assert_rejected_unchanged(bad, TASK_IDS)

    def test_invalid_source_alias_or_task_rejects_without_partial_import(self):
        for field, value in (("aliases", "guess"), ("source", {}), ("display_name", "   ")):
            bad = copy.deepcopy(self.entries)
            bad[-1][field] = value
            self.assert_rejected_unchanged(bad, TASK_IDS)
        for ids in ([301, 999999], [301, 301], [True], ["301"]):
            self.assert_rejected_unchanged(self.entries, ids)

    def test_ambiguity_includes_previously_persisted_profiles(self):
        a, b = copy.deepcopy(self.entries[:2])
        a["aliases"].append("共用")
        b["aliases"].append("共用")
        service.apply_roster(self.conn, [a])
        result = service.apply_roster(self.conn, [b], task_ids=[311])
        self.assertEqual("ambiguous", result["tasks"][0]["status"])
        self.assertTrue(result["tasks"][0]["pending"])
        self.assertEqual(2, len(result["tasks"][0]["candidate_vendor_ids"]))
        self.assertEqual([], result["assignments_created"])

    def test_conflicting_existing_binding_rejects_new_roster_too(self):
        first = service.apply_roster(self.conn, self.entries[:2])
        self.conn.execute("""INSERT INTO task_vendor_assignments VALUES(301,?,'呈旭',
            'explicit_name_exact_trim','{}')""", (first["vendor_ids"]["96769654"],))
        self.assert_rejected_unchanged(self.entries, TASK_IDS, service.RosterConflict)

    def test_existing_binding_cannot_become_ambiguous_or_unmatched(self):
        a, b = copy.deepcopy(self.entries[:2])
        a["aliases"].append("共用")
        b["aliases"].append("共用")
        service.apply_roster(self.conn, [a], task_ids=[311])
        self.assert_rejected_unchanged([b], [311], service.RosterConflict)
        self.conn.execute("UPDATE tasks SET vendor='not declared' WHERE id=311")
        self.assert_rejected_unchanged([b], [311], service.RosterConflict)

    def test_existing_profile_content_or_organization_conflict(self):
        first = service.apply_roster(self.conn, self.entries[:1])
        for field, value in (("legal_name", "變更正式名"), ("aliases", ["新增別名"]),
                             ("source", {**self.entries[0]["source"], "version": "new-version"})):
            bad = copy.deepcopy(self.entries)
            bad[0][field] = value
            self.assert_rejected_unchanged(bad, TASK_IDS, service.RosterConflict)
        self.conn.execute("UPDATE vendor_organizations SET display_name='wrong' WHERE vendor_id=?", (first["vendor_ids"]["12275123"],))
        self.assert_rejected_unchanged(self.entries, TASK_IDS, service.RosterConflict)

    def test_success_does_not_commit_caller_work_or_ddl(self):
        self.conn.execute("INSERT INTO meta VALUES('caller-work','keep-uncommitted')")
        service.apply_roster(self.conn, self.entries, task_ids=TASK_IDS)
        self.assertTrue(self.conn.in_transaction)
        observer = sqlite3.connect(self.path)
        try:
            self.assertIsNone(observer.execute("SELECT 1 FROM meta WHERE key='caller-work'").fetchone())
            self.assertIsNone(observer.execute("SELECT 1 FROM sqlite_schema WHERE name='vendor_profiles'").fetchone())
        finally:
            observer.close()
        self.conn.rollback()
        self.assertEqual(self.rows_before, snapshot(self.conn))

    def test_midpoint_write_failure_rolls_back_only_service_then_recovers(self):
        self.conn.execute("INSERT INTO meta VALUES('caller-work','survive')")
        before = snapshot(self.conn)
        self.conn.fail_sql = "INSERT INTO main.vendor_profiles"
        self.conn.remaining = 2
        with self.assertRaisesRegex(sqlite3.OperationalError, "injected midpoint"):
            service.apply_roster(self.conn, self.entries, task_ids=TASK_IDS)
        self.assertEqual(before, snapshot(self.conn))
        self.assertTrue(self.conn.in_transaction)
        self.conn.fail_sql = None
        result = service.apply_roster(self.conn, self.entries, task_ids=TASK_IDS)
        self.assertEqual(16, len(result["created_vendor_ids"]))
        self.conn.rollback()
        self.assertEqual(self.rows_before, snapshot(self.conn))

    def test_midpoint_ddl_failure_is_atomic(self):
        self.conn.rollback()
        self.conn.execute("BEGIN")
        self.conn.execute("INSERT INTO meta VALUES('caller-work','survive')")
        before = snapshot(self.conn)
        self.conn.fail_sql = "CREATE TABLE task_vendor_assignments"
        self.conn.remaining = 1
        with self.assertRaisesRegex(sqlite3.OperationalError, "injected midpoint"):
            service.initialize_schema(self.conn)
        self.assertEqual(before, snapshot(self.conn))
        self.assertTrue(self.conn.in_transaction)
        self.conn.fail_sql = None
        service.initialize_schema(self.conn)
        self.assertTrue(self.conn.in_transaction)

    def test_foreign_keys_and_caller_transaction_are_required(self):
        self.conn.rollback()
        with self.assertRaisesRegex(service.RosterError, "caller_transaction"):
            service.initialize_schema(self.conn)
        self.conn.execute("PRAGMA foreign_keys=OFF")  # rejection test only; never used to pass an import
        self.conn.execute("BEGIN")
        before = snapshot(self.conn)
        with self.assertRaisesRegex(service.RosterError, "foreign_keys"):
            service.initialize_schema(self.conn)
        self.assertEqual(before, snapshot(self.conn))

    def test_sqlite_relationship_constraints_are_live(self):
        result = service.apply_roster(self.conn, self.entries[:1], task_ids=[301])
        vendor = result["vendor_ids"]["12275123"]
        for task, vendor_id in ((999999, vendor), (302, str(uuid.uuid4())), (301, vendor)):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute("INSERT INTO task_vendor_assignments VALUES(?,?,'x','explicit_name_exact_trim','{}')", (task, vendor_id))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM vendor_organizations WHERE vendor_id=?", (vendor,))
        self.assertEqual([], self.conn.execute("PRAGMA foreign_key_check").fetchall())

    def test_supplemental_triggers_and_schema_drift_are_rejected(self):
        for prefix in ("", "TEMP "):
            self.conn.execute(f"CREATE {prefix}TRIGGER fixture_trigger AFTER INSERT ON main.vendor_profiles BEGIN UPDATE tasks SET vendor='corrupted'; END")
            self.assert_rejected_unchanged(self.entries, TASK_IDS)
            self.conn.execute("DROP TRIGGER fixture_trigger")
        self.conn.execute("ALTER TABLE vendor_profiles ADD COLUMN unexpected TEXT")
        self.assert_rejected_unchanged(self.entries, TASK_IDS)

    def test_main_tables_not_temp_shadows_and_sqlite_row_factory(self):
        self.conn.execute("CREATE TEMP TABLE tasks(id INTEGER, vendor TEXT)")
        self.conn.execute("INSERT INTO temp.tasks VALUES(301,'呈旭')")
        self.conn.row_factory = sqlite3.Row
        result = service.apply_roster(self.conn, self.entries, task_ids=[301])
        self.assertEqual(result["vendor_ids"]["12275123"], service.list_task_assignments(self.conn, task_ids=[301])[0]["vendor_id"])
        self.assertEqual(16, len(service.list_profiles(self.conn)))

    def test_actual_four_table_guard_accepts_supplements_import_and_rerun(self):
        with tempfile.TemporaryDirectory(prefix="004f-vr1-guard-") as directory:
            result = run_child(Path(directory) / "fresh-fixture.sqlite3", guard_check=True)
        self.assertEqual(["before_supplements", "after_supplements", "after_import", "after_rerun"], result["guard"])
        self.assertTrue(result["isolated"])
        self.assertEqual(1, result["foreign_keys"])
        self.assertNotIn("app", sys.modules)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in {"--build-fixture", "--guard-check"}:
        isolated_child(Path(sys.argv[2]), sys.argv[1] == "--guard-check")
    else:
        unittest.main()
