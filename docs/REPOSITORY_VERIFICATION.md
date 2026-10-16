# Repository release verification

Performed on 16 October 2026 using Windows and Python 3.12.14 in a newly created repository-root virtual environment. This record describes checks run for this GitHub release, separately from the earlier English package record.

| Check | Result |
|---|---|
| Clean Python environment | Created `.venv` without reusing the application's `.deps` directory |
| Dependency installation | `pip install -r finbrain/requirements.txt` succeeded; resolved versions captured in `requirements-lock.txt` |
| Application regression suite | 15 tests passed |
| Synthetic dataset suite | 15 tests passed, including the authored acceptance-case test and deterministic generation test |
| Server startup | Fresh runtime created successfully on loopback port 8878 |
| HTTP delivery | Health check, English index, JavaScript, and stylesheet returned successfully |
| Live stdio MCP | Initialize, six tool schemas, briefing, and Ben's permission-filtered SL16 query passed |
| Isolation from existing demo | Verification server used port 8878 and was stopped afterward; existing port 8765 service was not changed |

The initial sandboxed virtual-environment creation failed. Creating the environment and installing dependencies with the permitted host access succeeded. Network access was used for package resolution; some downloads were served from the local package cache. This is a clean environment on the current machine, not a separate fresh-machine test.

The dependency set emits a Starlette/httpx TestClient deprecation warning; all tests passed. The included English frontend build was copied unchanged from the previously built English distribution and served successfully. Its source-to-build reproduction was not rerun in this release pass. macOS/Linux, other Python versions, real cloud providers, ADP, and real enterprise source connectors were not tested.

No real model API credentials are included. Backend answers remain extractive unless a user explicitly configures a provider. Live WorkBuddy client demonstrations were performed separately by the project owner; this pass verifies the actual MCP bridge through its protocol smoke script.

Private chats, handbook/training PDFs, actual `.env` files, runtime stores, local keys, dependency binaries, and machine-specific MCP credentials are excluded from the release. Review screenshots separately before adding them later.
