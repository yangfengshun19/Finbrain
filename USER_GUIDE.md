# FinBrain installation and user guide

Use this guide to start the English prototype on a teammate's computer, demonstrate its permission-aware workflows, and continue development. All included people, events, and business records are synthetic.

## 1. Extract and install

Extract the entire ZIP to a writable folder. Keep `finbrain` and `finbrain_mock` beside each other. Do not run inside the ZIP or move only the application directory.

Python 3.11+ is required. Internet access is needed for initial dependency installation. Afterward, the default demo works offline. The English frontend is already built; Node.js is needed only for frontend development.

### Windows PowerShell

From the extracted package root:

```powershell
cd finbrain
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

These commands do not require activating PowerShell scripts. If your installation uses the Python launcher, substitute `py -3 -m venv .venv` for the environment creation command and verify Python is 3.11 or later.

### macOS or Linux

```sh
cd finbrain
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

If venv is unavailable, install your operating system's Python venv support. This package was validated on Windows; macOS/Linux instructions use the same portable source but were not executed on those platforms.

Open **http://127.0.0.1:8765**. Leave the terminal running; press **Ctrl+C** there to stop. For later launches, run only the final startup command from `finbrain`.

Startup creates `finbrain/runtime/` with a local database and encryption key. The delivered package contains no previous sessions, tokens, approvals, or personal queries.

## 2. Navigate the application

| View | Purpose |
|---|---|
| My briefing | Review ranked changes, inspect evidence, mark cards as read |
| Evidence Q&A | Ask questions, inspect citations, submit resolved/unresolved feedback |
| Knowledge demand | Inspect aggregate needs; eligible owners can publish closed windows |
| Knowledge improvements | Compare a template draft and approve or deny a local update |
| Decision timeline | Follow changing findings and check cited versions |
| Access audit | Inspect PAY-042 access metadata with an authorized auditor identity |
| Connect WorkBuddy | Generate a token and configure the stdio MCP bridge |

The sliders icon at the top right opens **Demo console**. Select an employee and event checkpoint. Identity switching is a test feature; checkpoint changes affect every browser and MCP session using that backend. UI dates use Singapore time (UTC+8); JSON timestamps use UTC.

## 3. Demonstration walkthrough

1. **Same role, different access.** Choose Alice at T06 and ask `SL16`. Open the private-channel evidence. Switch to Ben and ask again: the old answer clears and restricted evidence is not returned.
2. **Temporary access.** Choose Chloe at T04 and ask `CF01`. At T12, repeat: her temporary grant has expired. Historical content cannot restore revoked access.
3. **Changing findings.** For Alice, `SL16` at T03 contains an unverified vendor hypothesis. At T07, `CF12` identifies the connection pool cause. `JR15` at T09 is merged but not deployed; at T10 it records deployment and recovery. Related fix evidence is grouped in the briefing.
4. **Aggregate demand.** Click **Generate demo requests** once. It executes mock queries and unresolved feedback for six fictional employees at T10. Select Alice at T13, open **Knowledge demand**, and click **Publish closed windows**. The payment guidance hotspot shows no raw queries or exact contributor count.
5. **Reviewed improvements.** Create a draft from the hotspot. Open **Knowledge improvements**, compare the text, and choose **Approve local update**. Query `CF01` again to see the status interpretation addendum. A source-version conflict requires a fresh draft. No real Confluence document is modified.
6. **Audit scope.** Karen can inspect PAY-042 metadata. Leo lacks this scope at T12 and gains it at T13. Audit access does not automatically grant document access.

Try these English questions:

- `What caused PAY-042, and has the fix been deployed?`
- `What changed in the CF01 runbook?`
- `What is the difference between a merged and deployed fix?`

Default answers are local evidence excerpts, not model-generated synthesis. Retrieval uses deterministic keywords, not vector search. Exact resource IDs are the most precise demonstration queries.

## 4. WorkBuddy and optional models

See [finbrain/README.md](finbrain/README.md#connect-workbuddy) for the complete MCP configuration. Keep the backend running, generate your own eight-hour token, and substitute absolute paths for your computer. Match `FINBRAIN_URL` to the server port.

To enable a remote model in the web UI, copy `.env.example` to `.env` inside `finbrain`, configure the endpoint, model, and key, then restart. The question and authorized evidence will be sent to that provider. Errors fall back to local excerpts. The default package requires no API key; actual WorkBuddy client and remote-model integration need your own testing.

## 5. Development and tests

Windows, starting in `finbrain`:

```powershell
.\.venv\Scripts\python.exe test.py
cd ..\finbrain_mock
..\finbrain\.venv\Scripts\python.exe -m unittest -v
```

On macOS/Linux use `.venv/bin/python test.py` from `finbrain`, then `../finbrain/.venv/bin/python -m unittest -v` from `finbrain_mock`.

For frontend changes, install Node.js 22.12+ and pnpm. From `finbrain/frontend`:

```sh
pnpm install --frozen-lockfile
pnpm dev
```

Keep the backend on port 8765 for the development proxy. Before sharing changes, run `pnpm run build`; it also checks TypeScript. If pnpm requests build-script approval, run `pnpm approve-builds`, select esbuild, and rebuild. npm is an alternative (`npm install`, `npm run build`), but pnpm uses the supplied lockfile.

Edit `finbrain_mock/generate.py` to change source data. Run `python generate.py` there using your Python environment, rerun its tests, and restart the backend. Do not edit derived snapshots directly. See [DATA_DICTIONARY.md](finbrain_mock/DATA_DICTIONARY.md).

## 6. Troubleshooting

| Symptom | Action |
|---|---|
| Python not found | Install Python 3.11+ or use its absolute path; Windows may provide `py` |
| Missing package | Install requirements using the same interpreter that starts the app |
| Missing dataset | Keep `finbrain_mock/data/dataset.json` beside the application directory |
| Port busy | Stop your known old instance or select another port; do not terminate unknown processes |
| Browser cannot connect | Keep the terminal open; use `127.0.0.1` and the correct port |
| Empty result | Check identity and checkpoint; try `CF01` or another exact ID |
| No hotspot | Generate demo requests, select Alice at T13, publish closed windows |
| Draft conflict | Generate a new draft from the current resource version |
| MCP unauthorized | Generate a fresh token for the intended active identity |
| Old state appears | Select the intended identity/checkpoint; state persists across restarts |
| Frontend changes missing | Run `pnpm run build`, confirm success, then refresh |

For another port in PowerShell, set `$env:FINBRAIN_PORT='8766'` before startup. On macOS/Linux use `FINBRAIN_PORT=8766 .venv/bin/python run.py`. Update the browser URL and MCP `FINBRAIN_URL`. The development proxy stays on 8765 unless you edit `frontend/vite.config.js`.

For a fresh demo, stop the server and move `finbrain/runtime` to a backup location, then restart. Keep the database and key together to preserve the old state. Replacing only the key makes encrypted history unreadable.

## 7. Sharing

Share this clean ZIP or a new clean package. Exclude `.env`, tokens, and `runtime/`. Each computer installs its own dependencies; `.venv`, `.deps`, `node_modules`, and caches are not portable deliverables. The original source directory was not modified to create this edition.
