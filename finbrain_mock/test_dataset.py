"""Meaningful invariants, authored authorization cases, expiry and audit tests."""
import copy
import json
import unittest

from access import ROOT, authorized_context, can_audit, can_read, load_dataset, materialize, memberships
from audit import append_record, checkpoint, digest, query_records, verify
from demo import run_query
from generate import build


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_dataset()

    def test_generation_is_reproducible(self):
        self.assertEqual(self.dataset, build())
        self.assertEqual(build(), build())

    def test_size_and_reference_integrity(self):
        ds = self.dataset
        final = materialize(ds, "T14")
        self.assertEqual(len(final["users"]), 14)
        self.assertEqual(len(final["resources"]), 60)
        self.assertEqual(len(ds["events"]), 15)
        self.assertEqual(sum(r["deleted"] for r in final["resources"].values()), 1)
        self.assertEqual(sorted(e["effective_at"] for e in ds["events"]), [e["effective_at"] for e in ds["events"]])
        self.assertEqual(len({m["id"] for m in final["memberships"]}), len(final["memberships"]))
        for m in final["memberships"]:
            self.assertIn(m["subject_id"], final["users"])
            self.assertIn(m["target_id"], final["groups"])
            if m["valid_until"]:
                self.assertLess(m["valid_from"], m["valid_until"])
        for r in final["resources"].values():
            self.assertIn(r["policy_id"], final["policies"])
            self.assertIn(".example.test/", r["source_url"])
            for related in r["related_resource_ids"]:
                self.assertIn(related, final["resources"])
        for uid in final["users"]:
            for source in ("confluence", "jira", "slack", "gdrive"):
                self.assertTrue(final["users"][uid]["source_identities"][source])

    def test_authored_cases(self):
        for case in self.dataset["test_cases"]:
            with self.subTest(case=case["id"]):
                current = materialize(self.dataset, case["snapshot"])
                historical = materialize(self.dataset, case["historical_snapshot"]) if case["historical_snapshot"] else None
                context = authorized_context(current, case["user_id"], case["candidate_ids"], historical)
                found = {r["id"]: r for r in context}
                self.assertEqual(set(found), set(case["expected"]["allowed_ids"]))
                for rid in case["expected"]["denied_ids"]:
                    self.assertFalse(can_read(current, case["user_id"], rid)[0])
                    self.assertNotIn(rid, found)
                for rid, version in case["expected"]["versions"].items():
                    self.assertEqual(found[rid]["content_version"], version)
                for rid, text in case["expected"]["contains"].items():
                    self.assertIn(text, found[rid]["body"])

    def test_expiry_boundary_not_only_snapshots(self):
        before = materialize(self.dataset, "2026-09-23T03:59:59Z")
        exact = materialize(self.dataset, "2026-09-23T04:00:00Z")
        self.assertTrue(can_read(before, "U03", "SL16")[0])
        self.assertFalse(can_read(exact, "U03", "SL16")[0])

    def test_confluence_ancestor_and_page_are_both_required(self):
        state = materialize(self.dataset, "T06")
        # Giving an investigator membership without space access must not suffice.
        state["memberships"].append({"subject_id": "U13", "target_id": "group:investigation", "valid_from": state["as_of"], "valid_until": None})
        self.assertFalse(can_read(state, "U13", "CF11")[0])
        # Henry satisfies space+security-team, but lacks investigation membership.
        self.assertFalse(can_read(state, "U08", "CF11")[0])

    def test_jira_project_and_issue_security_are_both_required(self):
        state = materialize(self.dataset, "T06")
        state["memberships"].append({"subject_id": "U13", "target_id": "group:investigation", "valid_from": state["as_of"], "valid_until": None})
        self.assertFalse(can_read(state, "U13", "JR14")[0])
        self.assertFalse(can_read(state, "U08", "JR14")[0])

    def test_drive_external_restriction(self):
        state = materialize(self.dataset, "T10")
        state["policies"]["P_GD_SEC"]["direct_readers"] = ["user:U13"]
        self.assertFalse(can_read(state, "U13", "GD11")[0])

    def test_default_deny_tenant_and_missing_policy(self):
        state = materialize(self.dataset, "T10")
        self.assertFalse(can_read(state, "U01", "DOES_NOT_EXIST")[0])
        state["users"]["U01"]["tenant_id"] = "other_company"
        self.assertFalse(can_read(state, "U01", "CF01")[0])
        state["users"]["U01"]["tenant_id"] = "harborpay"
        del state["policies"]["P_CF_PAY"]
        self.assertFalse(can_read(state, "U01", "CF01")[0])

    def test_no_future_materialization(self):
        before = materialize(self.dataset, "2026-09-22T01:04:59Z")
        self.assertNotIn("JR13", before["resources"])
        with self.assertRaises(ValueError):
            materialize(self.dataset, "2026-01-01T00:00:00Z")
        with self.assertRaises(ValueError):
            run_query(self.dataset, "T03", "U01", "history", ["CF01"], historical="T10")
        with self.assertRaises(ValueError):
            authorized_context(materialize(self.dataset, "T03"), "U01", ["CF01"], materialize(self.dataset, "T10"))

    def test_versions_and_policy_versions_are_independent(self):
        before = materialize(self.dataset, "T10")
        after = materialize(self.dataset, "T11")
        self.assertEqual(before["resources"]["CF10"], after["resources"]["CF10"])
        self.assertNotEqual(before["policies"]["P_CF_INCIDENT"]["version"], after["policies"]["P_CF_INCIDENT"]["version"])
        versions = json.loads((ROOT / "data/versions/resource-versions.json").read_text(encoding="utf-8"))
        runbook = [v for v in versions if v["resource_id"] == "CF01"]
        self.assertEqual(len(runbook), 2)
        self.assertEqual(runbook[0]["valid_until"], runbook[1]["valid_from"])

    def test_no_metadata_leak_in_employee_response(self):
        denied = run_query(self.dataset, "T06", "U08", "What investigations are available?", ["CF11", "JR14", "SL19", "GD11"])
        missing = run_query(self.dataset, "T06", "U08", "What investigations are available?", ["DOES_NOT_EXIST"])
        self.assertEqual(denied, missing)
        self.assertNotIn("CANARY", json.dumps(denied))

    def test_provenance_context_rebuilt_after_revocation(self):
        old = materialize(self.dataset, "T04")
        prior = authorized_context(old, "U03", ["CF01", "SL16"])
        self.assertEqual(len(prior), 2)
        current = materialize(self.dataset, "T12")
        self.assertEqual(authorized_context(current, "U03", [e["id"] for e in prior], old), [])

    def test_audit_scope_is_not_document_access(self):
        before = materialize(self.dataset, "T12")
        after = materialize(self.dataset, "T13")
        self.assertTrue(can_audit(before, "U11", "PAY-042"))
        self.assertFalse(can_audit(before, "U12", "PAY-042"))
        self.assertTrue(can_audit(after, "U12", "PAY-042"))
        self.assertFalse(can_audit(after, "U12", "SET-019"))
        self.assertFalse(can_read(after, "U12", "CF11")[0])

    def test_audit_real_query_and_tamper_detection(self):
        records = []
        run_query(self.dataset, "T06", "U02", "What is the investigation status?", ["CF01", "CF11"], records=records)
        run_query(self.dataset, "T06", "U07", "What is the investigation status?", ["CF11"], records=records)
        anchor = checkpoint(records)
        self.assertTrue(verify(records, anchor))
        changed = copy.deepcopy(records)
        changed[0]["payload"]["query"] = "tampered"
        self.assertFalse(verify(changed, anchor))
        self.assertFalse(verify(records[:-1], anchor))
        # Even a recomputed chain must fail against the independently retained head.
        rebuilt = []
        for r in changed:
            append_record(rebuilt, r["payload"])
        self.assertFalse(verify(rebuilt, anchor))
        state = materialize(self.dataset, "T12")
        with self.assertRaises(PermissionError):
            query_records(state, "U12", records, "PAY-042")
        self.assertEqual(len(query_records(state, "U11", records, "PAY-042", "U02")), 1)
        self.assertEqual(records[0]["payload"]["retrieved_resource_ids"], ["CF01"])
        with self.assertRaises(ValueError):
            run_query(self.dataset, "T06", "U08", "Mixed scope", ["CF06", "CF11"], records=records)

    def test_snapshot_files_match_replay(self):
        for event in self.dataset["events"]:
            path = ROOT / "data/snapshots" / (event["snapshot"] + ".json")
            state = materialize(self.dataset, event["snapshot"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), state)
            for resource in state["resources"].values():
                for related_id in resource["related_resource_ids"]:
                    self.assertIn(related_id, state["resources"], "No future-resource links in earlier snapshots")


if __name__ == "__main__":
    unittest.main(verbosity=2)
