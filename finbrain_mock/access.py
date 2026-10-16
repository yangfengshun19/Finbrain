"""Deterministic mock authorization. No network, LLM, or third-party packages."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_dataset(path=None):
    return json.loads(Path(path or ROOT / "data/dataset.json").read_text(encoding="utf-8"))


def materialize(dataset, at):
    """Replay from baseline at a Txx label or arbitrary UTC/offset timestamp."""
    labels = {e["snapshot"]: e["effective_at"] for e in dataset["events"]}
    timestamp = labels.get(at, at)
    instant = parse_time(timestamp)
    if instant < parse_time(dataset["baseline"]["as_of"]):
        raise ValueError("Requested time precedes the dataset baseline")
    state = copy.deepcopy(dataset["baseline"])
    state["as_of"] = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    state["applied_event_ids"] = []
    for event in dataset["events"]:
        if parse_time(event["effective_at"]) > instant:
            break
        for change in event["changes"]:
            op = change["operation"]
            if op == "add_membership":
                state["memberships"].append(copy.deepcopy(change["membership"]))
            elif op == "remove_membership":
                for member in state["memberships"]:
                    if (member["subject_id"] == change["subject_id"]
                            and member["target_id"] == change["target_id"]
                            and parse_time(member["valid_from"]) <= parse_time(event["effective_at"])
                            and (member["valid_until"] is None or parse_time(member["valid_until"]) > parse_time(event["effective_at"]))):
                        member["valid_until"] = event["effective_at"]
                        member["ended_by_event"] = event["id"]
            elif op == "create_resource":
                resource = copy.deepcopy(change["resource"])
                if resource["id"] in state["resources"]:
                    raise ValueError("Duplicate resource: " + resource["id"])
                state["resources"][resource["id"]] = resource
            elif op == "update_resource":
                resource = state["resources"][change["resource_id"]]
                resource.update(copy.deepcopy(change["fields"]))
                resource["content_version"] += 1
                resource["updated_at"] = event["effective_at"]
            elif op == "delete_resource":
                resource = state["resources"][change["resource_id"]]
                resource["deleted"] = True
                resource["updated_at"] = event["effective_at"]
                resource["content_version"] += 1
            elif op == "replace_policy":
                state["policies"][change["policy"]["id"]] = copy.deepcopy(change["policy"])
            elif op == "set_account_active":
                state["accounts"][change["user_id"]]["active"] = change["active"]
            elif op == "assert_membership_expired":
                # An explicit timeline marker. Expiry itself is time based.
                pass
            else:
                raise ValueError("Unknown operation: " + op)
        state["applied_event_ids"].append(event["id"])
    return state


def memberships(state, user_id):
    now = parse_time(state["as_of"])
    return {
        m["target_id"] for m in state["memberships"]
        if m["subject_id"] == user_id
        and parse_time(m["valid_from"]) <= now
        and (m["valid_until"] is None or now < parse_time(m["valid_until"]))
    }


def _matches(principals, user_id, member_of):
    return any(p == "user:" + user_id or p in member_of for p in principals)


def can_read(state, user_id, resource_id):
    """Return internal decisions; do not expose denial reasons/IDs to ordinary users."""
    user = state["users"].get(user_id)
    if not user or not state["accounts"].get(user_id, {}).get("active", False):
        return False, "inactive_or_unknown_identity"
    resource = state["resources"].get(resource_id)
    if not resource or resource["deleted"]:
        return False, "unavailable"
    if user["tenant_id"] != resource["tenant_id"]:
        return False, "tenant_mismatch"
    policy = state["policies"].get(resource["policy_id"])
    if not policy or policy["source"] != resource["source"]:
        return False, "missing_or_invalid_policy"
    member_of = memberships(state, user_id)
    source = resource["source"]
    if source == "confluence":
        allowed = _matches(policy["space_readers"], user_id, member_of)
        # Every restriction is ANDed; each inner principal list is ORed.
        allowed = allowed and all(
            _matches(level, user_id, member_of)
            for level in policy["page_restriction_chain"]
        )
    elif source == "jira":
        allowed = _matches(policy["project_browse"], user_id, member_of)
        level = policy["issue_security_readers"]
        allowed = allowed and (level is None or _matches(level, user_id, member_of))
    elif source == "slack":
        allowed = policy["channel_membership_id"] in member_of
    elif source == "gdrive":
        # Simplified Drive model: explicit effective inherited grants, no public links.
        principals = policy["direct_readers"] + policy["inherited_readers"]
        allowed = _matches(principals, user_id, member_of)
        if policy["external_sharing"] is False and user["employment_type"] == "contractor":
            allowed = False
    else:
        return False, "unsupported_source"
    return bool(allowed), "allowed" if allowed else "source_permission_denied"


def authorized_context(state, user_id, candidate_ids, content_state=None):
    """Recheck CURRENT access even when requesting historical content.

    candidate_ids may come from an index or a prior chat's provenance list.
    Only authorized source excerpts are returned. Arbitrary old chat text is
    intentionally not accepted: it cannot reliably be sanitized this way.
    """
    evidence = []
    content = content_state or state
    if parse_time(content["as_of"]) > parse_time(state["as_of"]):
        raise ValueError("Historical content cannot be later than the current query time")
    for resource_id in dict.fromkeys(candidate_ids):
        if not can_read(state, user_id, resource_id)[0]:
            continue
        resource = content["resources"].get(resource_id)
        if not resource or resource["deleted"]:
            continue
        evidence.append({key: copy.deepcopy(resource[key]) for key in (
            "id", "source", "title", "body", "source_url", "content_version", "updated_at"
        )})
    return evidence


def can_audit(state, user_id, scenario_id):
    if not state["accounts"].get(user_id, {}).get("active", False):
        return False
    groups = memberships(state, user_id)
    return "role:auditor" in groups and "audit:" + scenario_id in groups
