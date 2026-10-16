# FinBrain — Permission-aware proactive work knowledge

FinBrain is a local prototype for Aspire / The Internal Brain. The web application and WorkBuddy MCP tools share backend identity, authorization, and audit services. See [USER_GUIDE.md](../USER_GUIDE.md) for installation and a complete walkthrough.

## Current implementation

| Feature | Status |
|---|---|
| 14 people, 60 resources, 15 checkpoints | Deterministic sources in the sibling `finbrain_mock` |
| React UI, Python API, SQLite | Implemented locally |
| Evidence Q&A | Current authorization, keyword retrieval, cited excerpts, optional remote model |
| Proactive briefing | Duties/update/importance ranking, grouped fix events, read records |
| Permission changes | Transfers, temporary expiry, channel membership, account disabling affect new requests |
| Knowledge demand | Fixed daily windows, at least 5 contributors, one contribution per person/topic/day, controlled publication |
| Knowledge improvements | Template drafts, owner review, mock-source updates, version conflict checks |
| Timeline and pre-action check | Historical content under current permissions; cited version validation |
| Audit | Fernet encryption, HMAC chain, PAY-042-scoped metadata |
| WorkBuddy | Six stdio MCP tools; actual client configuration remains user-specific |

**This is a local demo, not a production system connected to four real platforms.** Mock source data stays in the backend. Demo identity switching is not enterprise SSO.

## Startup and development

Keep `finbrain/` and `finbrain_mock/` as siblings. Python 3.11+ is required. Create a virtual environment, install `requirements.txt`, and run `python run.py` using that environment. Open <http://127.0.0.1:8765>; Ctrl+C stops the server. The included English `frontend/dist` removes the need for Node merely to run the demo.

Alternatively install into local `.deps` with `python -m pip install --target .deps -r requirements.txt`. `start.ps1` searches for installed Python, then optional Codex bundled Python. No global environment changes are needed. Use `start.ps1 -Test` or `python test.py` for application tests.

For frontend work, use Node.js 22.12+ and pnpm. Run `pnpm install --frozen-lockfile` and `pnpm run build` from `frontend`. If esbuild requires build-script approval, approve that package with `pnpm approve-builds` and rebuild. npm can run `npm install` and `npm run build`, but pnpm is preferred for the supplied lockfile. `pnpm dev` proxies `/api` to backend port 8765. Restart after Python edits.

Edit the sibling `finbrain_mock/generate.py`, regenerate data, and restart the backend rather than editing snapshots. Source version changes automatically invalidate local overlays based on older versions. sqlite3 is used without an ORM or background queue to simplify hackathon development; real connectors and trusted identity can later be separated behind the interfaces.

## Connect WorkBuddy

Keep the server running. In the web UI's **Connect WorkBuddy** view, generate a token for the current identity. It expires after eight hours and is subject to account disabling and current permissions on each request.

Add a local stdio MCP server using paths for your computer:

```json
{
  "mcpServers": {
    "finbrain": {
      "command": "C:/path/to/FinBrain-English/finbrain/.venv/Scripts/python.exe",
      "args": ["C:/path/to/FinBrain-English/finbrain/mcp_bridge.py"],
      "env": {
        "FINBRAIN_URL": "http://127.0.0.1:8765",
        "FINBRAIN_TOKEN": "PASTE_YOUR_CURRENT_IDENTITY_TOKEN"
      }
    }
  }
}
```

On macOS/Linux, use the absolute `.venv/bin/python` path. The bridge uses only the Python standard library and does not require backend packages in its interpreter.

Tools: `ask_knowledge`, `get_my_briefing`, `get_event_context`, `get_knowledge_hotspots`, `submit_answer_feedback`, `draft_knowledge_improvement`. Tokens determine identity; tools do not accept `user_id`. Approval and publication remain human actions in the web UI.

In a dedicated WorkBuddy conversation, ask: **Use FinBrain tools to tell me what needs my attention, citing evidence I am allowed to access.** Do not supply the entire dataset or backend directory to an employee Q&A conversation; this bypasses the permission demonstration. Start a new conversation after switching identities to avoid retained context. Keep tokens out of screenshots, code, and repositories. Generate a replacement when they expire.

The bridge negotiates MCP `2025-03-26` over stdio; HTTP MCP is not implemented. Original protocol references: [stdio transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) and [lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle). `scripts/smoke_mcp.py` exercises the protocol against a running local backend; inspect its local configuration before use.

## Optional remote language model

Default `extractive` mode does not call a model and is labeled **Local evidence excerpts**. WorkBuddy can synthesize answers from tool evidence. For web model answers, copy `.env.example` to `.env` and configure:

```dotenv
FINBRAIN_ANSWER_MODE=remote
FINBRAIN_MODEL_URL=https://your-provider.example/v1/chat/completions
FINBRAIN_MODEL_NAME=your-model-name
FINBRAIN_MODEL_KEY=your-key
```

Restart to apply. Only the current question and authorized evidence go to that provider. Timeouts, configuration errors, or invalid citations fall back to excerpts without printing keys or raw exceptions. Citation checks establish that references are supplied evidence, not that all natural-language conclusions are correct. No real-model integration is claimed without credentials.

## Data, security, and privacy boundaries

- `runtime/finbrain.db` persists sessions, queries, audit, read state, aggregates, and drafts. Queries, answers, audit bodies, and drafts are Fernet-encrypted.
- The default key is `runtime/local.key`; back it up with the database. `FINBRAIN_DATA_KEY` supplies an external key. Lost keys prevent recovery. The local filesystem owner can read both database and key; this is not KMS or isolation from administrators.
- The HMAC chain can detect content changes but has no independent external anchor and cannot detect every tail deletion.
- Hotspot deduplication uses daily-rotated HMAC identifiers, which remain controlled data. Publication exposes preset topics, interest bands, and reasons only, with no individual drill-down or arbitrary windows.
- A topic needs at least five people, each contributing once per topic/day. The unresolved reason independently requires five people. Published releases stay fixed despite later contributions. This is neither differential privacy nor a formal anonymity guarantee.
- Hotspots require current access to the topic anchor document. There is no company-wide managerial override.
- Source resources and permissions are replayed mock truth. Real incremental sync and measured sync latency are not implemented.
- The server binds to loopback. Any local operator can switch fictional identities; do not expose this demo as a public enterprise authorization service.
- Global checkpoints affect all sessions. Already displayed or copied content cannot be remotely retracted. New reads reauthorize; production needs trusted identity, invalidation notifications, and stronger session isolation.
- Web approval updates only local mock sources. No external messages or real platform updates are sent.

## Structure

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | HTTP routes, input validation, same-origin restrictions |
| `backend/app/service.py` | Shared services, briefing, hotspots, review |
| `backend/app/knowledge.py` | Mock adapter, permissions, retrieval |
| `backend/app/answers.py` | Excerpts and optional remote-model adapter |
| `backend/app/store.py` | SQLite, encryption, audit chain |
| `frontend/src/main.tsx` | Seven views and demo console |
| `frontend/src/style.css` | Responsive styling |
| `mcp_bridge.py` | WorkBuddy stdio entry point |
| `tests/` | Automated acceptance tests |

See `docs/VERIFICATION.md` for historical checks, `../ENGLISH_PACKAGE_VALIDATION.md` for the original English-package checks, and `../docs/REPOSITORY_VERIFICATION.md` for this repository's fresh checks. WorkBuddy calls were subsequently demonstrated; live web-model and four-platform integration remain unimplemented.
