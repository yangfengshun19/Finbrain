"""Local audit demonstration; external checkpoint required for tail verification."""
import hashlib
import json

from access import can_audit


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def append_record(records, payload):
    record = {"sequence": len(records) + 1, "previous_hash": records[-1]["hash"] if records else "0" * 64, "payload": payload}
    record["hash"] = digest(record)
    records.append(record)
    return record


def checkpoint(records):
    return {"count": len(records), "head_hash": records[-1]["hash"] if records else "0" * 64}


def verify(records, trusted_checkpoint):
    previous = "0" * 64
    for i, record in enumerate(records, 1):
        if record.get("sequence") != i or record.get("previous_hash") != previous:
            return False
        unsigned = {k: v for k, v in record.items() if k != "hash"}
        if record.get("hash") != digest(unsigned):
            return False
        previous = record["hash"]
    return checkpoint(records) == trusted_checkpoint


def query_records(state, auditor_id, records, scenario_id, subject_id=None):
    if not can_audit(state, auditor_id, scenario_id):
        raise PermissionError("Audit scope unavailable")
    return [r for r in records if r["payload"]["scenario_id"] == scenario_id
            and (subject_id is None or r["payload"]["user_id"] == subject_id)]
