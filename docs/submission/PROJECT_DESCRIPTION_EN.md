# FinBrain — The Internal Brain

**Tagline:** Permission-aware enterprise knowledge, with cited answers and auditability.

**Track:** FinTech — Aspire / The Internal Brain
**Edition:** English local prototype, 16 October 2026

## Project overview

FinBrain helps employees understand fragmented enterprise knowledge without receiving information outside their current access rights. It brings simulated Confluence pages, Jira issues, Slack messages, and Google Drive files into one permission-aware workflow. Employees can explore a personal briefing, ask questions with evidence, follow a decision timeline, and contribute to reviewed knowledge improvements.

The demonstrated AI experience runs through WorkBuddy. WorkBuddy invokes FinBrain's MCP tools, receives permission-filtered evidence, and synthesizes an English answer with source references. The web application currently provides deterministic evidence excerpts rather than live model-generated answers. A remote-model adapter exists, but a live provider and ADP have not been connected or validated.

## The problem and intended users

An engineer investigating a payment incident may need a Jira status update, a Slack discussion, a Confluence runbook, and a Drive postmortem. These sources may disagree because they were written at different stages. A preliminary theory can survive in an old draft after a later investigation has disproved it. A merged fix can be mistaken for a deployed fix.

Access makes this harder: employees with the same job title may have different channel memberships, project access, or temporary grants. A useful assistant must combine evidence while preserving those distinctions. FinBrain targets incident responders, engineers joining or changing teams, knowledge owners, and authorized auditors. HarborPay and all people, events, and business metrics in this prototype are fictional.

## How the solution works

The React web client and WorkBuddy share a Python/FastAPI backend and the same authorization engine. The backend resolves the caller from a session cookie or bearer token, checks account status, retrieves candidate resources, and filters them using current source-specific permissions before returning evidence. Evidence assembly checks permissions again, and question responses are checked before release. Resource-preview requests also reauthorize access.

The policy model combines roles and group memberships with resource rules and grant validity periods. It preserves distinct permission semantics: Confluence space and page restrictions, Jira project and issue restrictions, Slack channel membership, and Drive direct or inherited grants with an external-sharing restriction. Cross-tenant access, unknown identities, unavailable resources, and invalid policies are rejected.

The backend uses deterministic keyword retrieval over the synthetic sources. It is not a vector-search system. Internal retrieval can inspect candidate content, but only authorized evidence is returned to the employee or AI client. Source previews use guarded local endpoints; example source URLs are not live enterprise integrations.

## AI interaction and prompt design

The WorkBuddy connector exposes six tools: `ask_knowledge`, `get_my_briefing`, `get_event_context`, `get_knowledge_hotspots`, `submit_answer_feedback`, and `draft_knowledge_improvement`. Tool identity comes from the configured token, not an employee ID supplied by the model. Publishing a knowledge improvement remains a human action in the web application.

The demonstration prompt asks WorkBuddy to retrieve a briefing, investigate PAY-042 using FinBrain tools, answer in English, cite returned evidence, and distinguish hypotheses, confirmed findings, code merges, and deployments. It explicitly asks the assistant to state evidence gaps and avoid local-file access or other connectors. These instructions guide generation; backend authorization controls which source evidence the tools expose.

In the supplied demonstration output, WorkBuddy distinguished a superseded vendor-failure hypothesis from confirmed connection-pool exhaustion and reported the simulated deployment outcome with citations. Missing merge evidence was described as unverified. This illustrates grounded synthesis; it is not a formal guarantee against hallucination or prompt injection. Independent WorkBuddy file access could bypass the demonstration boundary, so employee demonstrations use fresh conversations and FinBrain tools only.

## Features beyond question answering

- **Personal briefings:** deterministic ranking by responsibilities, updates, and importance, with related repair events grouped together.
- **Decision timeline:** currently authorized historical evidence and version checks before action.
- **Knowledge demand:** predefined topic aggregates, at least five contributors, daily deduplication, and no individual drill-down in the published view.
- **Reviewed improvement:** knowledge owners can create and approve local update drafts; approval changes synthetic sources only.
- **Audit:** encrypted backend query/response payloads and authorization decisions, with an HMAC-linked log. The UI exposes restricted PAY-042 metadata and chain verification rather than full query and answer reconstruction.

## Validation and demonstration evidence

The synthetic dataset contains 14 identities, 60 resource IDs, 15 timeline checkpoints, 67 content versions, and 33 authored dataset acceptance cases. These are test-fixture dimensions, not real customer or usage metrics.

During English-package verification, all 15 application tests passed. Live HTTP checks confirmed that the English page, static assets, login, and question endpoint worked. WorkBuddy discovered all six MCP tools; user-provided outputs showed briefing and cited Q&A calls.

| Scenario | Evidence and qualification |
|---|---|
| Cross-source question | Supplied WorkBuddy output combines Jira, Confluence, Slack, and Drive evidence at T10. |
| Negative authorization | A verified Alice query returned SL16. A subsequent user-reported Ben test returned no evidence; preserve client identity and tool results together for submission. |
| Revocation | The user reports Chloe could read CF01 at T04 and could not at T12 with the same token. Preserve both results; not independently rechecked in this submission-writing pass. |
| Source freshness | Checkpoint replay demonstrates content-version changes. Real connector ingestion and a measured update-to-answer latency are not implemented. |
| Audit inquiry | Automated coverage includes audit permissions and integrity. Prepare a live walkthrough of the limited metadata viewer; full auditor reconstruction remains future work. |

## Business value and evaluation plan

FinBrain is intended to reduce manual cross-platform investigation, help employees distinguish current findings from old hypotheses, and make source access reviewable. Business impact has not been measured with real users. A pilot should compare time to answer a fixed set of incident questions against manual search, measure citation correctness and unsupported claims, track unauthorized evidence exposure on an adversarial test set, and measure source-update and revocation latency with real connectors. The security acceptance target is zero unauthorized evidence in the defined tests, not a claimed universal guarantee.

## Design trade-offs and current limits

The local prototype favors reproducible policy tests and transparent evidence over production infrastructure. It uses a single-process backend, SQLite, explicit policies, and synthetic source replay. It does not implement enterprise SSO, live connectors, or multi-tenant production isolation. A local operator can select fictional identities, so the demo must not be exposed publicly as an enterprise access-control service.

The MCP token is bound to one employee and lasts eight hours; changing the web identity does not change that token. Permission changes apply to subsequent reads. FinBrain cannot erase content already seen, copied, or retained in WorkBuddy conversations. The web client clears its current answer on identity/checkpoint changes, but cross-client historical-context invalidation is not implemented.

Sensitive stored payloads are encrypted, but the default encryption key is held on the same machine. The HMAC chain has no independent external anchor and cannot prove that every tail deletion is detectable. FinBrain records its own tool/backend responses; WorkBuddy's final synthesized text is not automatically captured in that log.

Future work includes trusted enterprise identity, real source connectors, stronger invalidation and conversation isolation, externally anchored audit integrity, authorized full audit reconstruction, and a web AI adapter such as ADP. ADP remains planned, not delivered.

## Development-tool evidence and submission materials

WorkBuddy was used for real MCP integration verification, evidence-based Q&A, and permission-scenario testing. Preserve the corresponding authentic development/debugging conversations and at least three screenshots as required by the handbook. Do not attribute work performed in other tools to WorkBuddy or CodeBuddy. No screenshots, repository URL, or video URL are fabricated in this description.

Companion files: `ARCHITECTURE.svg`, `TRUST_BOUNDARIES.svg`, and editable Mermaid sources in `DIAGRAMS.md`. The figures describe the current prototype; optional model integration is explicitly marked as unvalidated.
