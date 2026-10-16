# FinBrain / HarborPay complete mock dataset

This package supports development, comparison experiments, and demonstrations for Aspire / The Internal Brain. All employees, events, metrics, content, and domains are fictional. It requires Python 3.10+ and no network, API keys, or third-party Python packages.

## Start here

- `data/dataset.json`: authoritative baseline, events, and independently authored test cases.
- `data/snapshots/T00.json` through `T14.json`: complete checkpoint states.
- `data/manifest.json`: counts and dataset dimensions.
- `data/COMPARISON.md` and `data/expected-access/`: readable-resource comparisons.
- `DATA_DICTIONARY.md`: fields, semantics, and trust boundaries.
- `demo.py`: reference CLI; `generate.py`: source definitions and deterministic generation.

There are 12 employees and 2 contractors, with 12 Confluence pages, 16 Jira issues, 20 Slack messages, and 12 Drive files. T00 has 44 resources; 16 are created later, for 60 distinct IDs. One resource is deleted at T13. The dataset includes 67 content versions, 15 checkpoints, and 33 independently authored acceptance cases. Snapshots retain deletion tombstones for testing; retrieval must not return deleted bodies.

## Run

From this directory:

```sh
python generate.py
python -m unittest -v
python demo.py compare
python demo.py query --user U01 --snapshot T07 --ids CF12 JR13 SL18 --question "What caused the incident?"
python demo.py audit-demo
```

Windows `run.ps1` locates installed Python or optional Codex bundled Python, for example `./run.ps1 -m unittest -v` or `./run.ps1 demo.py compare`. A normal Python installation works without Codex.

`generate.py` rewrites only this package's `data/` files and never accesses real business systems. Generation is reproducible without randomness, current-machine time, or network requests. Regenerate after changing definitions.

## People and permission contrasts

| ID | Person | Role | Initial scope and changes |
|---|---|---|---|
| U01 | Alice | Backend Engineer | Payments; joins incident group/channel at T02 |
| U02 | Ben | Backend Engineer | Payments; never joins the private incident channel |
| U03 | Chloe | Backend Engineer | Settlement; temporary incident access T04–T12 |
| U04 | Daniel | Backend Engineer | Payments; transfers to Settlement at T11 and loses prior project/channel/incident access |
| U05 | Eva | SRE | On call at T02; temporary incident access ends at T08, base SRE access remains |
| U06 | Felix | SRE | Takes over and receives incident access at T08 |
| U07 | Grace | Security Engineer | Receives special investigation access at T06 |
| U08 | Henry | Security Engineer | Same security team, without special investigation access |
| U09 | Iris | Customer Operations | Enterprise customer communications |
| U10 | Jack | Customer Operations | Merchant communications |
| U11 | Karen | Auditor | PAY-042 audit scope; no default source-document access |
| U12 | Leo | Auditor | Receives PAY-042 audit scope at T13 |
| U13 | Maya | External Backend Engineer | Retry fix project; account disabled at T14 |
| U14 | Noah | External Backend Engineer | Same vendor, invoice interface project only |

`job_title` does not authorize access. Team, project, channel, investigation, and audit memberships are independent.

## Timeline

The following times are Singapore time (UTC+8); JSON timestamps use UTC `Z`.

| Checkpoint | Local time | Change |
|---|---|---|
| T00 | 2026-09-21 09:00 | Initial organization and 44 resources |
| T01 | 09-22 09:05 | Simulated payment failures rise to 18%; incident created |
| T02 | 09-22 09:10 | Alice, Daniel, Eva join incident group/channel |
| T03 | 09-22 09:20 | Early vendor hypothesis and draft postmortem |
| T04 | 09-22 09:40 | Chloe receives temporary access |
| T05 | 09-22 10:00 | Runbook v2 adds traffic switching |
| T06 | 09-22 10:15 | Special investigation; Grace only |
| T07 | 09-22 11:00 | Connection pool exhaustion and retry amplification confirmed; vendor failure ruled out |
| T08 | 09-22 12:00 | Eva hands over to Felix |
| T09 | 09-22 14:00 | Fix merged, not deployed |
| T10 | 09-22 16:00 | Deployment complete; simulated success rate 99.8% |
| T11 | 09-23 10:00 | Daniel transfers; CF10 independently restricted to investigation group |
| T12 | 09-23 12:00 | Chloe temporary access expires |
| T13 | 09-24 09:00 | Draft deleted, final postmortem published, Leo audit scope granted |
| T14 | 09-25 18:00 | Maya account disabled |

The T11 membership and page-policy changes are separate operations that can be tested independently.

## Four demonstration cases

```sh
python demo.py compare --resource SL16 --users U01 U02 --snapshots T03
python demo.py compare --resource SL16 --users U03 --snapshots T03 T04 T12
python demo.py query --user U01 --snapshot T04 --ids CF01
python demo.py query --user U01 --snapshot T05 --ids CF01
python demo.py query --user U03 --snapshot T12 --historical T04 --ids CF01 SL16
python demo.py audit-demo
```

Alice can read SL16 but Ben cannot; both can read the ordinary payment issue JR13. Chloe's temporary-access sequence is false → true → false, with access denied exactly at expiry. CF01 changes from v1 to v2. Historical queries use current permissions and cannot recover Chloe's expired access.

The audit demo executes four mock queries and writes `output/audit-log.json` and `output/audit-checkpoint.json`. It records identities, queries, decisions, actual evidence, and returned content, not fabricated AI answers. Tests detect modification, tail truncation, and recomputation against the original checkpoint. A local actor can modify both checkpoint and log, so this is not an immutable audit system; production needs a separately protected signature/anchor or controlled append-only storage.

## Integration boundaries

This mock subpackage does not itself implement MCP, authentication, live platform connections, vector retrieval, or LLM synthesis. The sibling `finbrain` application adds its web and MCP service layer. CLI `--user` selects a test identity and is not authentication.

The intended pipeline is trusted session → user ID → candidate resource retrieval → current source authorization → authorized evidence → answer → controlled audit.

- Full datasets, snapshots, permission matrices, and test expectations are trusted backend/development inputs. Never place them wholesale into employee-model context.
- A developer can inspect all data. To simulate an employee, provide only identity-filtered evidence and isolate any prior conversation that saw unrestricted data.
- Rebuild old context from source IDs after revocation. This reference does not scrub arbitrary free-text history or retract information already seen.
- Employee context omits denied IDs, titles, and counts. `compare` is a developer tool, not an employee endpoint.
- Audit examples cover PAY-042 only. Production needs scoped log partitions and controls for restricted answers.

## Freshness and platform semantics

`materialize` reads mock source truth at the selected checkpoint without background synchronization delay. `data/tests/freshness-contract.json` defines a future 60-second acceptance target, not measured connector performance. An index may lag, but each answer must check current source permissions and deny affected content if authorization is unavailable.

The permission model is explicitly simplified: Confluence requires space access AND every page restriction level (OR within each level); Jira requires project access AND optional issue security; Slack requires current channel membership; Drive requires direct/effective inherited access and permits external identities only when external sharing is allowed. Full DM, discovery, retention, shared-drive, and link-sharing semantics are outside scope. Group-to-platform associations are explicit; group names alone grant nothing.

## Validation and modifications

The suite has 15 methods, one of which runs 33 independently authored cases. It covers role comparisons, exact expiry, transfers, handover, disabled accounts, policy changes, versions, deletion, history, tenants, default denial, combined source rules, and audit integrity. It does not prove LLM factuality, live connector correctness, or production security.

Change `people`, `rows`, or `event(...)` definitions in `generate.py`, add independent before/after expectations for new permission changes, regenerate, and rerun tests. `expected-access` is computed by the reference implementation; independently authored `test_cases` provide the separate acceptance oracle.
