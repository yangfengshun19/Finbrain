# FinBrain — editable diagram sources

## Architecture: current English prototype

```mermaid
flowchart TB
  Web[React web application<br/>Briefings, excerpts, review, scoped audit]
  WB[WorkBuddy AI client<br/>Generates final English synthesis]
  Bridge[Local stdio MCP bridge<br/>Six tools; employee-bound token]
  API[FastAPI on loopback<br/>Resolve identity; validate requests]
  Gate[Current-permission retrieval<br/>Source-specific policy checks<br/>Recheck on evidence reads and response]
  Sources[(Synthetic source adapter<br/>Confluence / Jira / Slack / Drive<br/>15 checkpoints)]
  Service[Application services<br/>Excerpts, briefing, timeline<br/>Aggregates and reviewed local updates]
  Store[(SQLite<br/>Encrypted sensitive payloads<br/>HMAC-linked audit records)]
  Remote[Optional remote model adapter<br/>Not configured or live-validated<br/>ADP integration not implemented]
  Web -->|Session cookie + HTTP| API
  WB -->|MCP stdio| Bridge
  Bridge -->|Bearer token + loopback HTTP| API
  API --> Gate
  Sources -->|Internal candidates and policies| Gate
  Gate -->|Authorized evidence only| Service
  Service -->|Backend response and decisions| Store
  Service -->|Result via API| Web
  Service -->|Evidence via API and MCP| WB
  Service -.->|Optional authorized context| Remote
```

## Trust boundaries: authority and data exposure

```mermaid
flowchart TB
  subgraph Client[Boundary A — employee-facing clients]
    Browser[Browser<br/>Current demo identity]
    WorkBuddy[WorkBuddy and its model runtime<br/>Untrusted generated output<br/>Retains its own conversation]
  end
  subgraph Backend[Boundary B — trusted local application]
    Auth[Resolve session or token<br/>Check active account]
    Policy[Authorization gate<br/>Tenant, memberships, resource rules<br/>Grant validity at simulated time]
    Result[Authorized evidence / backend answer<br/>Reauthorize preview requests]
    Audit[Restricted audit storage and viewer<br/>Separate audit-scope permission]
  end
  subgraph Source[Boundary C — backend-only source data]
    Data[Full synthetic corpus and policies<br/>Never supplied wholesale to the AI]
  end
  Browser -->|Session cookie| Auth
  WorkBuddy -->|Employee-bound token via MCP| Auth
  Auth --> Policy
  Data -->|Internal retrieval| Policy
  Policy -->|Allowed resources only| Result
  Policy -->|Allowed / denied decisions| Audit
  Result -->|Encrypted backend payload| Audit
  Result -->|Authorized result| Browser
  Result -->|Authorized evidence| WorkBuddy
  WorkBuddy -.->|Final synthesis is NOT captured automatically| Gap[Audit coverage gap]
```

The source-data and backend boxes are logical boundaries on one machine, not separate OS sandboxes. The filesystem owner can access the dataset, database, and local key. Demo identity selection is not SSO. Denied document metadata is excluded from ordinary evidence responses. Revocation governs new reads, not already disclosed information or WorkBuddy memory. Optional remote-adapter citation checks validate IDs, not the truth of generated statements.
