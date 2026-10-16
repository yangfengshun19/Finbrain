"""CLI simulation. --user is a fixture selector, NOT trusted authentication."""
import argparse
import json
from pathlib import Path

from access import ROOT, authorized_context, can_read, load_dataset, materialize
from audit import append_record, checkpoint, query_records, verify


def run_query(dataset, snapshot, uid, query, candidate_ids, historical=None, records=None):
    state = materialize(dataset, snapshot)
    content = materialize(dataset, historical) if historical else None
    if content and content["as_of"] > state["as_of"]:
        raise ValueError("Historical time cannot be later than the current query time")
    evidence = authorized_context(state, uid, candidate_ids, content)
    response = {"mode": "authorized_evidence_only_no_llm", "as_of": state["as_of"],
                "message": "The following evidence is accessible to the current identity; no AI synthesis has been requested." if evidence else "The currently accessible material is insufficient to answer this question.",
                "evidence": evidence}
    if records is not None:
        scoped = {state["resources"][rid]["scenario_id"] for rid in candidate_ids if rid in state["resources"]}
        if scoped - {"PAY-042"}:
            raise ValueError("Audit demo only supports PAY-042 resources; mixed-scope queries need a production audit partition design")
        # Restricted metadata lives only in the auditor-facing record.
        # For this demo, a request has a fixed PAY-042 audit scope. Do not use
        # this implementation for multi-scope production log partitioning.
        append_record(records, {"scenario_id": "PAY-042", "timestamp": state["as_of"],
                                "user_id": uid, "query": query,
                                "authorization": [{"resource_id": rid, "allowed": can_read(state, uid, rid)[0], "reason": can_read(state, uid, rid)[1]} for rid in candidate_ids],
                                "retrieved_resource_ids": [r["id"] for r in evidence],
                                "answer": response})
    return response


def main():
    parser = argparse.ArgumentParser(description="FinBrain deterministic mock demo; not an authenticated application")
    sub = parser.add_subparsers(dest="command", required=True)
    compare = sub.add_parser("compare", help="Developer-only comparison of access to a resource")
    compare.add_argument("--resource", default="SL16")
    compare.add_argument("--users", nargs="+", default=["U01", "U02", "U03"])
    compare.add_argument("--snapshots", nargs="+", default=["T03", "T04", "T12"])
    query = sub.add_parser("query", help="Return permitted evidence, not a generated AI answer")
    query.add_argument("--user", required=True)
    query.add_argument("--snapshot", default="T10")
    query.add_argument("--ids", nargs="+", required=True)
    query.add_argument("--question", default="Please provide relevant evidence.")
    query.add_argument("--historical")
    sub.add_parser("audit-demo", help="Run real mock queries and generate a hash-linked audit fixture")
    args = parser.parse_args()
    dataset = load_dataset()
    if args.command == "compare":
        result = []
        for label in args.snapshots:
            state = materialize(dataset, label)
            for uid in args.users:
                allowed, reason = can_read(state, uid, args.resource)
                result.append({"snapshot": label, "user_id": uid, "resource_id": args.resource, "allowed": allowed, "reason": reason})
    elif args.command == "query":
        result = run_query(dataset, args.snapshot, args.user, args.question, args.ids, args.historical)
    else:
        records = []
        for snapshot, uid in (("T03", "U01"), ("T03", "U02"), ("T04", "U03"), ("T12", "U03")):
            run_query(dataset, snapshot, uid, "What was discussed while troubleshooting the payment incident?", ["JR13", "SL16", "SL17"], records=records)
        head = checkpoint(records)
        output = ROOT / "output"
        output.mkdir(exist_ok=True)
        (output / "audit-log.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "audit-checkpoint.json").write_text(json.dumps(head, indent=2) + "\n", encoding="utf-8")
        result = {"verification": verify(records, head), "record_count": len(records),
                  "karen_access_count": len(query_records(materialize(dataset, "T12"), "U11", records, "PAY-042")),
                  "note": "Checkpoint is stored locally for demonstration. Production needs an independently protected anchor.",
                  "output": str(output)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
