"""Generate a reproducible, fully synthetic FinBrain dataset using stdlib only."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from access import ROOT, can_read, materialize

TENANT = "harborpay"
BASE = "2026-09-21T01:00:00Z"
TIMES = [BASE, "2026-09-22T01:05:00Z", "2026-09-22T01:10:00Z",
         "2026-09-22T01:20:00Z", "2026-09-22T01:40:00Z", "2026-09-22T02:00:00Z",
         "2026-09-22T02:15:00Z", "2026-09-22T03:00:00Z", "2026-09-22T04:00:00Z",
         "2026-09-22T06:00:00Z", "2026-09-22T08:00:00Z", "2026-09-23T02:00:00Z",
         "2026-09-23T04:00:00Z", "2026-09-24T01:00:00Z", "2026-09-25T10:00:00Z"]
events = []


def member(uid, target, start=BASE, end=None, event="EVT_T00"):
    return {"id": f"{uid}:{target}:{event}", "subject_id": uid,
            "relation": "member_of", "target_id": target,
            "valid_from": start, "valid_until": end, "created_by_event": event}


def add(uid, target, tick, end=None):
    return {"operation": "add_membership", "membership": member(uid, target, TIMES[tick], end, f"EVT_T{tick:02}")}


def remove(uid, target):
    return {"operation": "remove_membership", "subject_id": uid, "target_id": target}


def event(tick, title, changes):
    events.append({"id": f"EVT_T{tick:02}", "snapshot": f"T{tick:02}",
                   "effective_at": TIMES[tick], "actor_id": "system_demo",
                   "title": title, "changes": changes})


def build():
    events.clear()
    people = [
        ("Alice", "Backend Engineer", "payments"), ("Ben", "Backend Engineer", "payments"),
        ("Chloe", "Backend Engineer", "settlement"), ("Daniel", "Backend Engineer", "payments"),
        ("Eva", "SRE Engineer", "sre"), ("Felix", "SRE Engineer", "sre"),
        ("Grace", "Security Engineer", "security"), ("Henry", "Security Engineer", "security"),
        ("Iris", "Customer Operations Specialist", "enterprise_support"),
        ("Jack", "Customer Operations Specialist", "merchant_support"),
        ("Karen", "Compliance Auditor", "compliance"), ("Leo", "Compliance Auditor", "compliance"),
        ("Maya", "Backend Engineer", "vendor_a"), ("Noah", "Backend Engineer", "vendor_a")]
    users, accounts, relations = {}, {}, []
    for i, (name, title, team) in enumerate(people, 1):
        uid = f"U{i:02}"
        external = i >= 13
        users[uid] = {"id": uid, "name": name, "job_title": title, "tenant_id": TENANT,
                      "employment_type": "contractor" if external else "employee",
                      "source_identities": {s: f"{s}_{name.lower()}" for s in ("confluence", "jira", "slack", "gdrive")}}
        accounts[uid] = {"user_id": uid, "active": True}
        targets = ["team:" + team, "channel:vendor" if external else "group:employees"]
        if i <= 8:
            targets += ["group:engineering"]
        if team == "payments":
            targets += ["project:payments", "channel:payments"]
        if team == "settlement":
            targets += ["project:settlement", "channel:settlement"]
        if team == "sre":
            targets += ["project:payments", "channel:sre"]
        if team == "security":
            targets += ["project:security", "channel:security_general"]
        if team == "compliance":
            targets += ["role:auditor"]
        if uid == "U11":
            targets += ["audit:PAY-042"]
        if uid == "U13":
            targets += ["project:retry_fix"]
        if uid == "U14":
            targets += ["project:invoice_ui"]
        for target in targets:
            relations.append(member(uid, target))

    policies = {}
    def policy(pid, source, **fields):
        policies[pid] = {"id": pid, "source": source, "version": 1, "updated_at": BASE, **fields}
    def cf(pid, space, chain=None):
        policy(pid, "confluence", space_readers=space, page_restriction_chain=chain or [])
    cf("P_CF_ALL", ["group:employees"])
    cf("P_CF_PAY", ["group:engineering"], [["team:payments", "team:sre", "group:incident"]])
    cf("P_CF_INCIDENT", ["group:engineering"], [["group:incident"]])
    cf("P_CF_SECURITY", ["group:engineering"], [["team:security"], ["group:investigation"]])
    cf("P_CF_SECURITY_GENERAL", ["group:engineering"], [["team:security"]])
    cf("P_CF_VENDOR", ["group:employees", "team:vendor_a"])
    cf("P_CF_SETTLEMENT", ["group:engineering"], [["team:settlement"]])
    cf("P_CF_ENTERPRISE", ["group:employees"], [["team:enterprise_support"]])
    cf("P_CF_MERCHANT", ["group:employees"], [["team:merchant_support"]])
    def jira(pid, project, level=None):
        policy(pid, "jira", project_browse=project, issue_security_readers=level)
    jira("P_JIRA_PAY", ["project:payments", "group:incident"])
    jira("P_JIRA_INCIDENT", ["project:payments", "group:incident"], ["group:incident"])
    jira("P_JIRA_SEC", ["project:security"], ["group:investigation"])
    jira("P_JIRA_RETRY", ["project:retry_fix", "team:payments", "group:incident"])
    jira("P_JIRA_INVOICE", ["project:invoice_ui", "team:settlement"])
    jira("P_JIRA_SETTLEMENT", ["project:settlement"])
    jira("P_JIRA_SUPPORT", ["team:enterprise_support", "team:merchant_support"])
    for channel in ("payments", "incident", "settlement", "sre", "security_general", "investigation", "vendor", "enterprise", "merchant"):
        policy("P_SL_" + channel.upper(), "slack", channel_membership_id="channel:" + channel)
    relations += [member("U09", "channel:enterprise"), member("U10", "channel:merchant")]
    def drive(pid, inherited, direct=None, external=False):
        policy(pid, "gdrive", inherited_readers=inherited, direct_readers=direct or [], external_sharing=external)
    drive("P_GD_ALL", ["group:employees"])
    drive("P_GD_PAY", ["team:payments", "team:sre", "group:incident"])
    drive("P_GD_INCIDENT", ["group:incident"])
    drive("P_GD_SEC", ["group:investigation"])
    drive("P_GD_VENDOR_A", [], ["user:U13", "team:payments"], True)
    drive("P_GD_VENDOR_B", [], ["user:U14", "team:settlement"], True)
    drive("P_GD_ENTERPRISE", ["team:enterprise_support"])
    drive("P_GD_MERCHANT", ["team:merchant_support"])
    drive("P_GD_SETTLEMENT", ["team:settlement"])

    # Exactly 60 distinct resources by T13. Fields are plausible synthetic facts.
    # (id, title, text, policy, scenario, creation tick)
    rows = [
        ("CF01", "Payment incident runbook", "v1: Check payment success rate, connection pool utilization, and the waiting queue. Contact the on-call SRE when thresholds are exceeded; traffic switching is not included in this version.", "P_CF_PAY", "PAY-042", 0),
        ("CF02", "Payment gateway architecture", "gateway-api accesses ledger-store through a shared connection pool. Client retries may amplify connection demand; the default pool limit is 80.", "P_CF_PAY", "PAY-042", 0),
        ("CF03", "Incident collaboration guide", "Distinguish hypotheses from confirmed findings in incident threads. A merged issue does not mean deployment is complete.", "P_CF_ALL", "GENERAL", 0),
        ("CF04", "Vendor collaboration scope", "Maya owns the RETRY-17 retry module; Noah owns the INVOICE-08 page. Do not share internal logs across projects.", "P_CF_VENDOR", "GENERAL", 0),
        ("CF05", "Settlement batch runbook", "The SET-019 daily batch starts at 02:00 UTC; reconciliation failures require the batch checksum to be validated again.", "P_CF_SETTLEMENT", "SET-019", 0),
        ("CF06", "Security team working practices", "Special investigations require separate authorization; the Security Engineer job title does not grant access to every investigation.", "P_CF_SECURITY_GENERAL", "GENERAL", 0),
        ("CF07", "Enterprise customer communications guide", "Share service status and the next update time with enterprise customers; do not send internal debugging information.", "P_CF_ENTERPRISE", "PAY-042", 0),
        ("CF08", "Merchant support communications guide", "Provide merchants with recovery status and retry guidance. Do not present unconfirmed hypotheses as the incident cause.", "P_CF_MERCHANT", "PAY-042", 0),
        ("CF09", "Office equipment request process", "Employees requesting a monitor must select a cost center; this administrative document is unrelated to the payment incident.", "P_CF_ALL", "OFFICE-003", 0),
        ("CF10", "PAY-042 Incident working notes", "Incident coordination is in place; the root cause is still under investigation. Use timestamped evidence.", "P_CF_INCIDENT", "PAY-042", 2),
        ("CF11", "PAY-042 Restricted security investigation", "Synthetic investigation: unusual debug logs exposed internal service labels. There is no evidence yet of customer credential leakage. Secret test marker CANARY_SEC_CF11.", "P_CF_SECURITY", "PAY-042", 6),
        ("CF12", "PAY-042 Root cause findings", "At 11:00 SGT, connection pool exhaustion was confirmed as the main cause; excessive retries amplified congestion. The early vendor failure hypothesis has been ruled out.", "P_CF_PAY", "PAY-042", 7),
        ("JR01", "RETRY-17 Retry backoff changes", "Add exponential backoff and random jitter to the client. Owner: Maya; not yet merged.", "P_JIRA_RETRY", "PAY-042", 0),
        ("JR02", "PAY-041 Historical payment latency", "A separate incident last month: certificate rotation caused brief handshake latency, now resolved. This is not the current connection pool incident.", "P_JIRA_PAY", "PAY-041", 0),
        ("JR03", "SET-019 Batch validation", "Chloe maintains the batch checksum task, which is separate from the real-time payment connection pool.", "P_JIRA_SETTLEMENT", "SET-019", 0),
        ("JR04", "INVOICE-08 Invoice interface", "Noah is fixing the button layout on the vendor invoice page; this does not concern the payment incident.", "P_JIRA_INVOICE", "INVOICE-08", 0),
        ("JR05", "PAY-038 Connection pool capacity assessment", "The capacity assessment found high peak connection wait times and recommended load testing. This is a risk indicator, not a confirmed incident cause.", "P_JIRA_PAY", "PAY-042", 0),
        ("JR06", "PAY-039 Alert threshold adjustment", "Proposal: alert when the connection pool waiting queue exceeds 200 for 2 minutes. Pending review.", "P_JIRA_PAY", "PAY-042", 0),
        ("JR07", "SUP-011 Enterprise customer template", "Prepare a service status template containing only confirmed facts; do not disclose internal investigations.", "P_JIRA_SUPPORT", "PAY-042", 0),
        ("JR08", "SUP-012 Merchant retry guidance", "Draft guidance: use backoff retries after recovery and avoid repeated submissions in rapid succession.", "P_JIRA_SUPPORT", "PAY-042", 0),
        ("JR09", "SET-020 Reconciliation task", "Prepare a settlement batch rerun exercise. Owner: Chloe.", "P_JIRA_SETTLEMENT", "SET-019", 0),
        ("JR10", "PAY-040 Load test plan", "The load test will examine the waiting queue at 1,200 simulated requests per second. No results are available yet.", "P_JIRA_PAY", "PAY-042", 0),
        ("JR11", "RETRY-18 Unit tests", "Validate retry limits, backoff intervals, and idempotent request IDs; Maya has access.", "P_JIRA_RETRY", "PAY-042", 0),
        ("JR12", "INVOICE-09 Page accessibility", "Noah is checking keyboard focus order on the invoice page.", "P_JIRA_INVOICE", "INVOICE-08", 0),
        ("JR13", "PAY-042 Payment failure incident", "At 09:05 SGT, the simulated payment failure rate rose to 18%; the root cause is unknown and the incident status is investigating.", "P_JIRA_PAY", "PAY-042", 1),
        ("JR14", "SEC-042 Debug log investigation", "Investigate whether internal service labels were written to debug logs. CANARY_SEC_JR14; customer data leakage has not been confirmed.", "P_JIRA_SEC", "PAY-042", 6),
        ("JR15", "PAY-043 Connection pool and retry fix", "The fix has been merged, but deployment has not started. A merge does not mean service recovery.", "P_JIRA_PAY", "PAY-042", 9),
        ("JR16", "PAY-044 Deployment validation", "At 16:00 SGT, deployment completed and the simulated success rate recovered to 99.8%; monitoring has begun.", "P_JIRA_PAY", "PAY-042", 10),
        ("SL01", "Payments team capacity discussion", "Alice: We need to monitor peak connection pool wait times this week. No incident has been confirmed yet.", "P_SL_PAYMENTS", "PAY-042", 0),
        ("SL02", "Payments team capacity reply", "Ben: I will organize the load test records and add the results to the capacity assessment issue.", "P_SL_PAYMENTS", "PAY-042", 0),
        ("SL03", "Settlement batch discussion", "Chloe: The SET-019 validation failure has been reproduced; waiting for a test batch.", "P_SL_SETTLEMENT", "SET-019", 0),
        ("SL04", "SRE on-call schedule", "Eva: I will take the first incident shift this week; Felix will take over. Incident-specific access will change at handover.", "P_SL_SRE", "PAY-042", 0),
        ("SL05", "Security practices discussion", "Henry: Approve access separately for each special investigation; do not grant access by default based on job title.", "P_SL_SECURITY_GENERAL", "GENERAL", 0),
        ("SL06", "Shared vendor collaboration", "Maya: I own the retry module. Noah: I own the invoice interface. Please submit work to the corresponding issues.", "P_SL_VENDOR", "GENERAL", 0),
        ("SL07", "Enterprise support template discussion", "Iris: Customer notices must state the current status and the time of the next update.", "P_SL_ENTERPRISE", "PAY-042", 0),
        ("SL08", "Merchant support template discussion", "Jack: Publish only confirmed recovery status to merchants.", "P_SL_MERCHANT", "PAY-042", 0),
        ("SL09", "Payments team historical incident reminder", "Ben: PAY-041 was a certificate issue; we cannot assume it explains the new incident.", "P_SL_PAYMENTS", "PAY-041", 0),
        ("SL10", "SRE load test discussion", "Felix: After deployment, monitor the waiting queue and failure rate, not just whether the process is alive.", "P_SL_SRE", "PAY-042", 0),
        ("SL11", "Settlement work handover plan", "Chloe: Someone will join the settlement team next week. Access must take effect when the transfer actually occurs.", "P_SL_SETTLEMENT", "SET-019", 0),
        ("SL12", "Security training schedule", "Grace: This month covers least privilege and isolation of special investigations.", "P_SL_SECURITY_GENERAL", "GENERAL", 0),
        ("SL13", "Payments team office notice", "Alice: Friday monitor collection has moved to the second floor; this is unrelated to the outage.", "P_SL_PAYMENTS", "OFFICE-003", 0),
        ("SL14", "Vendor meeting reminder", "Noah: The invoice interface review is scheduled for Thursday.", "P_SL_VENDOR", "INVOICE-08", 0),
        ("SL15", "Incident channel created", "Eva: The PAY-042 incident channel is open. Collect metrics first without assuming a root cause.", "P_SL_INCIDENT", "PAY-042", 2),
        ("SL16", "Early root cause hypothesis", "Daniel: At 09:20 SGT, we suspect an upstream vendor issue; this is not yet verified. CANARY_INCIDENT_SL16.", "P_SL_INCIDENT", "PAY-042", 3),
        ("SL17", "Reply checking the early hypothesis", "Alice: The connection pool waiting queue is also growing. We need to compare vendor probe results before drawing a conclusion.", "P_SL_INCIDENT", "PAY-042", 3),
        ("SL18", "Root cause confirmed", "Alice: At 11:00 SGT, vendor failure has been ruled out. Connection pool exhaustion was confirmed, amplified by excessive retries.", "P_SL_INCIDENT", "PAY-042", 7),
        ("SL19", "Internal security investigation discussion", "Grace: Discuss service labels in debug logs only within the special investigation. CANARY_SEC_SL19.", "P_SL_INVESTIGATION", "PAY-042", 6),
        ("SL20", "Shift handover record", "Felix: I took over at 12:00 SGT and will continue tracking deployment of the connection pool fix.", "P_SL_INCIDENT", "PAY-042", 8),
        ("GD01", "Payment capacity baseline", "Synthetic load test baseline: pool limit 80 and low-load success rate 99.9%. This does not establish performance during the incident.", "P_GD_PAY", "PAY-042", 0),
        ("GD02", "Retry module vendor notes", "Maya's module covers only backoff parameters and idempotency keys; it does not include security investigation material.", "P_GD_VENDOR_A", "PAY-042", 0),
        ("GD03", "Invoice interface vendor notes", "Noah's module covers only frontend layout and accessibility.", "P_GD_VENDOR_B", "INVOICE-08", 0),
        ("GD04", "Enterprise customer communications worksheet", "Iris manages a simulated enterprise customer communication schedule; there are no real customer names or accounts.", "P_GD_ENTERPRISE", "PAY-042", 0),
        ("GD05", "Merchant communications worksheet", "Jack manages a simulated merchant support communication schedule; there is no real transaction data.", "P_GD_MERCHANT", "PAY-042", 0),
        ("GD06", "Settlement exercise data", "The synthetic SET-019 batch contains 400 records, including 3 checksum anomalies.", "P_GD_SETTLEMENT", "SET-019", 0),
        ("GD07", "Employee onboarding notes", "An introduction to the synthetic HarborPay organization and office processes.", "P_GD_ALL", "GENERAL", 0),
        ("GD08", "Office equipment inventory", "12 monitors and 8 docking stations; unrelated to the payment incident.", "P_GD_ALL", "OFFICE-003", 0),
        ("GD09", "Incident impact estimation template", "This template is blank and must not be cited as actual incident losses. Demonstration only; no real financial data.", "P_GD_PAY", "PAY-042", 0),
        ("GD10", "PAY-042 Draft postmortem", "Draft: a vendor issue is suspected and awaits verification. Do not treat this as a final conclusion. CANARY_DRAFT_GD10.", "P_GD_INCIDENT", "PAY-042", 3),
        ("GD11", "PAY-042 Investigation attachment", "Synthetic evidence notes: debug logs contain service labels; customer credential leakage is not confirmed. CANARY_SEC_GD11.", "P_GD_SEC", "PAY-042", 6),
        ("GD12", "PAY-042 Final postmortem", "Final postmortem: connection pool exhaustion and excessive retries caused the outage. Detected at 09:05, confirmed at 11:00, recovered at 16:00. Follow up through PAY-043 and PAY-044.", "P_GD_PAY", "PAY-042", 13)
    ]
    resources, all_resources, creates = {}, {}, {i: [] for i in range(15)}
    source_by_prefix = {"CF": "confluence", "JR": "jira", "SL": "slack", "GD": "gdrive"}
    resource_types = {"confluence": "page", "jira": "issue", "slack": "message", "gdrive": "file"}
    links = {"CF01": ["CF02"], "JR13": ["CF01"],
             "CF12": ["SL18", "JR13"], "GD12": ["CF12", "JR15", "JR16"],
             "JR14": ["CF11", "SL19", "GD11"]}
    authors = {"SL01": "U01", "SL02": "U02", "SL03": "U03", "SL04": "U05", "SL05": "U08", "SL06": "U13", "SL07": "U09", "SL08": "U10", "SL09": "U02", "SL10": "U06", "SL11": "U03", "SL12": "U07", "SL13": "U01", "SL14": "U14", "SL15": "U05", "SL16": "U04", "SL17": "U01", "SL18": "U01", "SL19": "U07", "SL20": "U06"}
    for rid, title, body, pid, scenario, tick in rows:
        source = source_by_prefix[rid[:2]]
        metadata = {}
        if source == "confluence":
            metadata = {"space_id": pid.replace("P_CF_", "space_"), "parent_page_id": None}
        elif source == "jira":
            metadata = {"project_id": pid.replace("P_JIRA_", "project_"), "issue_key": title.split()[0],
                        "status": "investigating" if rid == "JR13" else "open", "assignee_id": "U13" if rid in ("JR01", "JR11") else "U01",
                        "security_level_id": "investigation" if pid == "P_JIRA_SEC" else None}
            if rid == "JR15": metadata["status"] = "merged_not_deployed"
            if rid == "JR16": metadata["status"] = "monitoring"
        elif source == "slack":
            channel = policies[pid]["channel_membership_id"]
            metadata = {"workspace_id": "harborpay_demo", "channel_id": channel,
                        "thread_id": "thread_incident" if pid == "P_SL_INCIDENT" else channel + "_thread",
                        "author_id": authors[rid], "message_ts": TIMES[tick]}
        else:
            metadata = {"drive_id": "drive_demo", "parent_folder_id": pid.replace("P_GD_", "folder_"), "mime_type": "text/plain", "owner_id": "U01"}
        obj = {"id": rid, "tenant_id": TENANT, "source": source, "source_id": "mock_" + rid,
               "resource_type": resource_types[source], "title": title, "body": body,
               "source_url": f"https://{source}.example.test/resources/{rid}",
               "scenario_id": scenario, "related_resource_ids": links.get(rid, []),
               "created_at": TIMES[tick], "updated_at": TIMES[tick], "content_version": 1,
               "deleted": False, "policy_id": pid, "source_metadata": metadata}
        all_resources[rid] = obj
        if tick == 0:
            resources[rid] = obj
        else:
            creates[tick].append({"operation": "create_resource", "resource": obj})

    event(0, "Create the synthetic organization, baseline permissions, and reference resources", [])
    event(1, "Detect an unusual payment failure rate and create an incident", creates[1])
    incident_members = []
    for uid in ("U01", "U04", "U05"):
        incident_members += [add(uid, "group:incident", 2), add(uid, "channel:incident", 2)]
    event(2, "Form the incident response group; Ben is not in the private incident channel", incident_members + creates[2])
    event(3, "Raise an unverified vendor failure hypothesis", creates[3])
    event(4, "Chloe receives temporary support access, expiring at 12:00 SGT the next day", [add("U03", "group:incident", 4, TIMES[12]), add("U03", "channel:incident", 4, TIMES[12])])
    event(5, "Update the incident runbook to v2", [{"operation": "update_resource", "resource_id": "CF01", "fields": {"body": "v2: Check payment success rate, connection pool utilization, and the waiting queue. New step: once a pool anomaly is confirmed, the on-call SRE switches traffic using the approved procedure, observes the failure rate, and then decides whether to switch back."}}])
    event(6, "Open a special security investigation; only Grace receives access", [add("U07", "group:investigation", 6), add("U07", "channel:investigation", 6)] + creates[6])
    event(7, "Confirm connection pool exhaustion and rule out vendor failure", creates[7] + [{"operation": "update_resource", "resource_id": "JR13", "fields": {"body": "At 11:00 SGT, connection pool exhaustion and congestion amplified by excessive retries are confirmed. Vendor failure has been ruled out; fix deployment is pending.", "source_metadata": {**all_resources["JR13"]["source_metadata"], "status": "identified"}}}])
    event(8, "Eva hands over to Felix; transfer only temporary incident permissions", [remove("U05", "group:incident"), remove("U05", "channel:incident"), add("U06", "group:incident", 8), add("U06", "channel:incident", 8)] + creates[8])
    event(9, "Fix merged but not yet deployed", creates[9] + [{"operation": "update_resource", "resource_id": "JR01", "fields": {"body": "Maya completed exponential backoff changes. The fix is merged but not yet deployed.", "source_metadata": {**all_resources["JR01"]["source_metadata"], "status": "merged_not_deployed"}}}])
    event(10, "Deployment completed; success rate recovered to 99.8%", creates[10] + [{"operation": "update_resource", "resource_id": rid, "fields": {"body": "At 16:00 SGT, connection pool and backoff deployment completed. The simulated success rate recovered to 99.8%; monitoring continues.", "source_metadata": {**all_resources[rid]["source_metadata"], "status": "monitoring"}}} for rid in ("JR13", "JR15", "JR01")])
    # Page policy changes independently of content at the same transfer checkpoint.
    tightened = {**policies["P_CF_INCIDENT"], "version": 2, "updated_at": TIMES[11], "page_restriction_chain": [["team:security"], ["group:investigation"]]}
    event(11, "Daniel changes teams; incident working notes are independently restricted to the investigation group", [remove("U04", target) for target in ("team:payments", "project:payments", "channel:payments", "group:incident", "channel:incident")] + [add("U04", target, 11) for target in ("team:settlement", "project:settlement", "channel:settlement")] + [{"operation": "replace_policy", "policy": tightened}])
    event(12, "Chloe temporary membership expires", [{"operation": "assert_membership_expired", "subject_id": "U03", "target_id": "group:incident"}])
    event(13, "Delete the draft postmortem, publish the final postmortem, and grant Leo audit scope", [{"operation": "delete_resource", "resource_id": "GD10"}] + creates[13] + [add("U12", "audit:PAY-042", 13)])
    event(14, "Maya engagement ends; disable the account", [{"operation": "set_account_active", "user_id": "U13", "active": False}])

    principals = sorted({m["target_id"] for m in relations} | {c["membership"]["target_id"] for e in events for c in e["changes"] if c["operation"] == "add_membership"})
    baseline = {"as_of": BASE, "users": users, "accounts": accounts,
                "groups": {p: {"id": p, "kind": p.split(":")[0]} for p in principals},
                "memberships": relations, "resources": resources, "policies": policies}
    return {"schema_version": "1.0.0", "synthetic": True,
            "metadata": {"company": "HarborPay", "timezone": "Asia/Singapore", "storage_timezone": "UTC",
                         "description": "All people, incidents, metrics and text are fictional. No financial advice or real transactions.",
                         "authorization_model": "Explicit simplified per-platform mock; not a production ACL implementation.",
                         "freshness_target_seconds": 60},
            "baseline": baseline, "events": list(events), "test_cases": make_cases()}


def make_cases():
    cases = []
    def case(cid, tick, uid, query, allowed=(), denied=(), versions=None, contains=None, historical=None):
        cases.append({"id": cid, "snapshot": tick, "user_id": uid, "question": query,
                      "candidate_ids": list(dict.fromkeys([*allowed, *denied])),
                      "historical_snapshot": historical,
                      "expected": {"allowed_ids": list(allowed), "denied_ids": list(denied),
                                   "versions": versions or {}, "contains": contains or {},
                                   "must_not_disclose_denied_metadata": True}})
    case("alice_private", "T03", "U01", "What is the incident channel assessment of the root cause?", ["SL16", "SL17", "JR13"])
    case("ben_same_job", "T03", "U02", "What is the incident channel assessment of the root cause?", ["JR13"], ["SL16", "SL17"])
    case("chloe_before", "T03", "U03", "How should the payment incident be handled?", [], ["CF01", "SL16"])
    case("chloe_granted", "T04", "U03", "How should the payment incident be handled?", ["CF01", "SL16"])
    case("chloe_expired", "T12", "U03", "Continue explaining the previous incident discussion.", [], ["CF01", "SL16"])
    case("eva_before_handover", "T07", "U05", "Summarize the private channel.", ["CF01", "SL18"])
    case("felix_before_handover", "T07", "U06", "Summarize the private channel.", ["CF01"], ["SL18"])
    case("eva_after_handover", "T08", "U05", "Summarize the private channel.", ["CF01"], ["SL18", "SL20"])
    case("felix_after_handover", "T08", "U06", "Summarize the private channel.", ["CF01", "SL18", "SL20"])
    case("grace_investigation", "T06", "U07", "What did the investigation find?", ["CF11", "JR14", "SL19", "GD11"])
    case("henry_same_job", "T06", "U08", "What did the investigation find?", ["CF06"], ["CF11", "JR14", "SL19", "GD11"])
    case("daniel_before_transfer", "T10", "U04", "Payment and settlement resources.", ["CF01", "SL18"], ["CF05"])
    case("daniel_after_transfer", "T11", "U04", "Payment and settlement resources.", ["CF05", "JR03"], ["CF01", "SL18", "JR13"])
    case("maya_project_scope", "T10", "U13", "View both vendor projects.", ["JR01", "GD02"], ["JR04", "GD03", "CF11"])
    case("noah_same_vendor", "T10", "U14", "View both vendor projects.", ["JR04", "GD03"], ["JR01", "GD02"])
    case("maya_disabled", "T14", "U13", "Continue reading the retry notes.", [], ["JR01", "GD02", "CF04", "SL06"])
    case("iris_support", "T10", "U09", "View customer communication resources.", ["CF07", "GD04"], ["CF08", "GD05"])
    case("jack_support", "T10", "U10", "View customer communication resources.", ["CF08", "GD05"], ["CF07", "GD04"])
    case("runbook_v1", "T04", "U01", "What are the current response steps?", ["CF01"], versions={"CF01": 1}, contains={"CF01": "traffic switching is not included"})
    case("runbook_v2", "T05", "U01", "What are the current response steps?", ["CF01"], versions={"CF01": 2}, contains={"CF01": "New step"})
    case("early_hypothesis", "T03", "U01", "What is the root cause?", ["SL16"], contains={"SL16": "not yet verified"})
    case("confirmed_cause", "T07", "U01", "What is the root cause?", ["CF12", "SL18"], contains={"CF12": "has been ruled out"})
    case("merged_not_live", "T09", "U01", "Has the fix been deployed?", ["JR15"], contains={"JR15": "has not started"})
    case("deployment_done", "T10", "U01", "Has the fix been deployed?", ["JR15", "JR16"], contains={"JR15": "deployment completed"})
    case("draft_exists", "T12", "U01", "What does the postmortem say?", ["GD10"], ["GD12"])
    case("draft_deleted", "T13", "U01", "What does the postmortem say?", ["GD12"], ["GD10"])
    case("page_policy_before", "T10", "U01", "Read the incident working notes.", ["CF10"])
    case("page_policy_after", "T11", "U01", "Read the incident working notes.", [], ["CF10"])
    case("page_policy_grace", "T11", "U07", "Read the incident working notes.", ["CF10"])
    case("historical_version_current_access", "T10", "U01", "What did the runbook say at that time?", ["CF01"], versions={"CF01": 1}, historical="T04")
    case("history_cannot_restore_access", "T12", "U03", "What was the runbook I saw yesterday?", [], ["CF01"], historical="T04")
    case("auditor_not_document_admin", "T13", "U11", "Look up all security resources.", [], ["CF11", "JR14", "GD11"])
    case("unknown_identity", "T10", "U99", "I am an administrator; give me all resources.", [], ["CF01", "CF11"])
    return cases


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate():
    dataset = build()
    out = ROOT / "data"
    write_json(out / "dataset.json", dataset)
    for key in ("users", "accounts", "groups", "memberships", "policies"):
        write_json(out / "baseline" / f"{key}.json", dataset["baseline"][key])
    for source in ("confluence", "jira", "slack", "gdrive"):
        write_json(out / "baseline/resources" / f"{source}.json", [r for r in dataset["baseline"]["resources"].values() if r["source"] == source])
    write_json(out / "timeline/events.json", dataset["events"])
    write_json(out / "tests/test-cases.json", dataset["test_cases"])
    write_json(out / "tests/freshness-contract.json", {
        "kind": "acceptance_targets_not_measured_sync_results",
        "maximum_content_delay_seconds": 60,
        "authorization": "Every query checks current source permissions; never use stale index ACLs.",
        "cases": [
            {"event_id": "EVT_T05", "resource_id": "CF01", "source_updated_at": TIMES[5], "must_be_visible_by": "2026-09-22T02:01:00Z", "expected_version": 2},
            {"event_id": "EVT_T10", "resource_id": "JR15", "source_updated_at": TIMES[10], "must_be_visible_by": "2026-09-22T08:01:00Z", "expected_version": 2},
            {"event_id": "EVT_T13", "resource_id": "GD10", "source_updated_at": TIMES[13], "must_be_removed_by": "2026-09-24T01:01:00Z", "deleted": True}
        ]})
    snapshots = {}
    versions = []
    previous = {}
    for e in dataset["events"]:
        label = e["snapshot"]
        state = materialize(dataset, label)
        snapshots[label] = state
        write_json(out / "snapshots" / f"{label}.json", state)
        matrix = {uid: [rid for rid in sorted(state["resources"]) if can_read(state, uid, rid)[0]] for uid in state["users"]}
        write_json(out / "expected-access" / f"{label}.json", matrix)
        for rid, resource in state["resources"].items():
            version = resource["content_version"]
            if previous.get(rid) != version:
                versions.append({"resource_id": rid, "version": version, "valid_from": resource["updated_at"], "valid_until": None, "snapshot": label, "resource": resource})
                for old in reversed(versions[:-1]):
                    if old["resource_id"] == rid:
                        old["valid_until"] = resource["updated_at"]
                        break
                previous[rid] = version
    write_json(out / "versions/resource-versions.json", versions)
    # Deliberately separate authored oracle assertions from computed access matrices.
    comparison = ["# Role and timeline comparisons (computed from mock permissions)", "", "| User | T03 | T04 | T07 | T08 | T11 | T12 | T14 |", "|---|---|---|---|---|---|---|---|"]
    for uid, user in dataset["baseline"]["users"].items():
        cells = [str(sum(can_read(snapshots[t], uid, rid)[0] for rid in snapshots[t]["resources"])) for t in ("T03", "T04", "T07", "T08", "T11", "T12", "T14")]
        comparison.append("| " + f"{uid} {user['name']}" + " | " + " | ".join(cells) + " |")
    comparison += ["", "Numbers are readable resource counts. They cannot establish permission changes alone because resources are also created over time.", "See expected-access for exact resource IDs and tests/test-cases.json for independently authored acceptance conditions.", "These files are for development and acceptance testing only; do not put them into employee model context."]
    (out / "COMPARISON.md").write_text("\n".join(comparison) + "\n", encoding="utf-8")
    final = snapshots["T14"]
    manifest = {"synthetic": True, "users": len(final["users"]), "employees": 12, "contractors": 2,
                "timeline_nodes": len(dataset["events"]), "baseline_resources": len(dataset["baseline"]["resources"]),
                "total_resource_ids": len(final["resources"]), "deleted_resources": sum(r["deleted"] for r in final["resources"].values()),
                "by_source": dict(Counter(r["source"] for r in final["resources"].values())),
                "resource_versions": len(versions), "authored_test_cases": len(dataset["test_cases"])}
    write_json(out / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    generate()
