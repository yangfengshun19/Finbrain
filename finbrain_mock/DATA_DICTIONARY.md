# Data fields and consumer contract

## Top-level files

`dataset.json` is authoritative and contains `schema_version`, `synthetic`, `metadata`, `baseline`, `events`, and `test_cases`. The baseline, timeline, snapshot, and version directories are split or derived representations of that data.

## Baseline

| Field | Type | Meaning |
|---|---|---|
| as_of | UTC timestamp | Baseline time |
| users | Object keyed by user ID | Identity, job title, employment type, four-platform account mappings |
| accounts | Object keyed by user ID | Whether the global mock account is active |
| groups | Object keyed by principal ID | Team, project, channel, group, role, and audit principals |
| memberships | Array | Time-bounded relations between users and principals |
| policies | Object keyed by policy ID | Platform-specific authorization rules |
| resources | Object keyed by resource ID | Resources created by that point |

Users have no static `team` field because membership changes over time. `source_identities` anticipates future mapping; the reference authorizer uses trusted internal IDs, not OAuth or login.

## Membership

| Field | Meaning |
|---|---|
| id | Unique membership record ID |
| subject_id | Internal user ID, such as U03 |
| relation | Currently only `member_of` |
| target_id | Principal such as `group:incident` or `channel:incident` |
| valid_from | Inclusive start |
| valid_until | Exclusive end; null means no predetermined expiry |
| created_by_event | Event creating this relation |
| ended_by_event | Optional explicit revocation event |

There is no nested group inheritance. Joining `group:incident` does not join `channel:incident`; events specify each relation.

## Resource

| Field | Meaning |
|---|---|
| id / source_id | Internal / mock platform ID |
| tenant_id | Company boundary; baseline is harborpay, tests inject other tenants to check denial |
| source / resource_type | Platform and page/issue/message/file type |
| title / body | English resource content |
| source_url | Mock example.test citation URL, not a live platform link |
| scenario_id | Test scenario label; must not be used to obtain an answer oracle |
| related_resource_ids | Existing related resources, each requiring renewed authorization |
| created_at / updated_at | Source creation/update time |
| content_version | Version; deletion also creates a tombstone version |
| deleted | Deletion flag; do not return body |
| policy_id | Current policy reference; policy versions are maintained independently |
| source_metadata | Platform-specific fields |

Creation/update timestamps describe content changes; times within body text describe business events and may differ. `CANARY_*` strings are synthetic disclosure-test markers, not credentials.

## Source metadata

- Confluence: `space_id`, `parent_page_id`; inherited restrictions are represented in an ordered policy chain.
- Jira: `project_id`, `issue_key`, `status`, `assignee_id`, `security_level_id`.
- Slack: `workspace_id`, `channel_id`, `thread_id`, `author_id`, `message_ts`. Authorize each message before assembling a thread. Mock timestamps are not Slack API-native ts values.
- Drive: `drive_id`, `parent_folder_id`, `mime_type`, `owner_id`. Authorization follows policy only; owner metadata does not implicitly grant access.

## Policy

Every policy has `id`, `source`, `version`, and `updated_at`. `user:U13` denotes a direct grant; other principal strings reference membership target IDs.

| Platform | Fields | Rule |
|---|---|---|
| Confluence | space_readers, page_restriction_chain | Match at least one space reader AND one reader at every restriction level |
| Jira | project_browse, issue_security_readers | Match project access AND issue restrictions; null means no additional issue restriction |
| Slack | channel_membership_id | Current channel membership required |
| Drive | direct_readers, inherited_readers, external_sharing | Match direct or effective inherited access; external identities also require external_sharing |

Empty principal lists grant nothing. An empty Confluence restriction chain adds no page restriction. Unknown users, disabled accounts, missing/deleted resources, tenant mismatch, and missing policies are denied by default.

## Events

Each event has `id`, `snapshot`, `effective_at`, `actor_id`, `title`, and ordered `changes`. Operations execute in array order; checkpoint queries see the completed event.

| Operation | Payload and behavior |
|---|---|
| add_membership | membership |
| remove_membership | subject_id, target_id |
| create_resource | resource |
| update_resource | resource_id, fields; increments content_version |
| delete_resource | resource_id; sets deleted and increments version |
| replace_policy | policy; author explicitly sets the new policy version |
| set_account_active | user_id, active |
| assert_membership_expired | Explicit timeline marker; actual expiry follows valid_until |

Replay does not mutate the dataset. Editing a snapshot does not change subsequent replay.

## Historical versions and acceptance cases

Each `versions/resource-versions.json` record includes resource_id, version, valid_from, valid_until, snapshot, and resource. Validity is start-inclusive/end-exclusive. Historical bodies still require current permissions.

Test cases contain id, snapshot, user_id, question, candidate_ids, historical_snapshot, and expected. `allowed_ids`/`denied_ids` are authored expectations; `versions`/`contains` check versions and facts. Natural-language questions are prompts for future LLM evaluation; this mock CLI does not perform semantic search or answer scoring.

## Employee output

`authorized_context` returns only authorized id, source, title, body, source_url, content_version, and updated_at. It does not expose full ACLs, candidates, denial reasons, or denied counts. IDs themselves may be restricted metadata and must not leak through errors or log endpoints.

## Audit demonstration

Records contain sequence, previous_hash, payload, and hash. Payload contains scenario_id, timestamp, user_id, query, authorization, retrieved_resource_ids, and answer. The answer is the actual evidence returned, not fabricated model prose. Timestamps are simulated event times. Hashes use SHA-256 over canonical JSON; checkpoints store count and head_hash. Audit data may contain restricted content and is exposed only to explicitly scoped auditors; audit scope does not expand source access. The sibling application adds encrypted storage and HMAC chaining separately.
