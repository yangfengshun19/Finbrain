# Historical verification record

This is the translated record of the original project's verification on **2026-10-12**, on Windows with a local Python server, React build, and `127.0.0.1:8765`. These historical observations are distinct from the English package checks in [ENGLISH_PACKAGE_VALIDATION.md](../../ENGLISH_PACKAGE_VALIDATION.md).

## Automation recorded in the original project

- `start.ps1 -Test`: all 15 application tests passed.
- TypeScript `tsc --noEmit` and the Vite production build passed.
- `scripts/smoke_mcp.py` completed initialize, tools/list, get_my_briefing, and ask_knowledge against the running backend. Six tools were discoverable; Ben received no SL16 restricted evidence; tokens were not printed.
- Tests covered identity injection, same-role comparisons, revocation, disabling, deletion, versions, encrypted payloads, feedback ownership, hotspot thresholds/deduplication, fixed publication results, draft review/conflicts, audit scope/chain, and origin/session boundaries.
- Added regressions covered grouped fix evidence, de-emphasizing old hypotheses when confirmed findings are visible, and invalidating overlays based on older source versions.

## Browser results recorded in the original project

| Workflow | Recorded result |
|---|---|
| Alice queries SL16 | Authorized private-channel excerpts and citations |
| Switch to Ben and repeat | Previous answer cleared; insufficient material; zero sources |
| Chloe T04 queries SL16 | Readable |
| Chloe T12 repeats | Restricted evidence no longer returned |
| Six help requests; Alice publishes at T13 | Payment hotspot without employee list or raw questions |
| Create and approve draft | Published locally; CF01 v3 contains addendum |
| Karen audit | Valid chain and PAY-042 allow/deny metadata |
| Restart service | Sessions, document updates, and simulated time persisted |
| Homepage | Five grouped briefing cards; fix card linked four authorized sources |

The original Chinese-interface screenshot `preview.jpg` is not included as an English preview.

## Unverified or unimplemented integrations

No real model credentials were supplied. MCP protocol/local HTTP were checked, but the user's actual WorkBuddy client was not configured. The four source platforms remain mocks without live APIs or incremental sync. Demo login is not SSO; a local key is not KMS; the HMAC chain has no independent external anchor. Approval updates local mock data only. Historical browser checks used the default desktop viewport, not a full browser/mobile compatibility matrix. New reads reauthorize but already displayed/copied content is not remotely withdrawn.

The original tests emitted a Starlette httpx compatibility deprecation warning while passing. Future dependency updates may need test-client adjustments.
