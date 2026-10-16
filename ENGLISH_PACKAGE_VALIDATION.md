# English distribution validation

Prepared and checked on **2026-10-16**, on Windows. This record distinguishes completed checks from limitations so teammates can plan their own validation.

## Passed

| Check | Result |
|---|---|
| Application unit/integration suite | 15 tests passed |
| Mock dataset suite | 15 tests passed, including 33 independently authored cases |
| TypeScript | `tsc --noEmit` passed |
| Production frontend | Vite build passed; English HTML, JS, and CSS included |
| Live local server | Health endpoint and English built index served successfully |
| Live stdio MCP | Initialize, six tool schemas, briefing, and permission-filtered question passed against the running backend |
| Non-disclosure | Ben received no restricted SL16 evidence or incident canary in the live MCP check |
| Translation scan | No Han characters in the scanned first-party text, code, data, and built frontend files |
| Syntax/data integrity | All Python sources parsed; all JSON files parsed |
| Permission preservation | All 15 computed access matrices exactly matched the original |
| Dataset dimensions | Original counts preserved: 14 users, 60 resource IDs, 15 checkpoints, 67 versions, 33 authored cases |
| Reference preservation | Supplied English handbook, TRTC guide, and handbook images preserved byte-for-byte |

## Recorded issues and unverified areas

1. **Browser visual review was not completed.** Attempts to open the temporary preview from the in-app browser timed out or were refused. A separate same-process live HTTP/MCP smoke check passed. The English UI has a successful build, but its full visual layout, long-label wrapping, and cross-browser behavior still need a teammate's browser check.
2. **Sandbox-specific test startup:** the first application test attempt stalled during Windows loopback initialization. After network permission was granted, all 15 application tests passed. This was an execution-environment limitation, not an application change.
3. **Sandbox-specific frontend build:** the normal build encountered an EPERM during native path resolution. The successful Vite build used the same source with `resolve.preserveSymlinks=true` in a temporary build harness. The shipped Vite configuration remains the project's normal configuration. A teammate should run the documented standard build on their machine before further development.
4. **Dependency warning:** Starlette's httpx test-client compatibility layer emitted a deprecation warning. Tests passed; this dependency migration has not been undertaken.
5. **Fresh-computer installation was not independently repeated.** Checks used locally available dependency versions. Dependency manifests and lockfile are included, but initial installation requires package-registry access. No portable dependency binaries are bundled.
6. **External services remain unverified.** No real WorkBuddy client, remote language model, Confluence, Jira, Slack, Drive, or TRTC integration was completed. The successful MCP check is protocol/local-backend validation, not a real-client claim.
7. **Platform scope:** macOS/Linux instructions were not executed; mobile and cross-browser compatibility were not fully tested. The optional PDF conversion helper was translated but not rerun.
8. **Runtime cleanup:** some temporary validation database files remained locked during workspace cleanup. Runtime directories are excluded from the ZIP; no validation database, local key, session, or token is delivered.

The original project's historical verification is separately translated in `finbrain/docs/VERIFICATION.md`. It must not be read as a fresh browser validation of this English edition.

## Suggested teammate acceptance

Install from the extracted ZIP, start the app, and follow the six scenarios in `USER_GUIDE.md`. Inspect all seven views for English layout and wrapping. Run `python test.py`, the mock dataset tests, and the normal frontend build on the target computer. Configure external clients only if needed for the team's demonstration.
