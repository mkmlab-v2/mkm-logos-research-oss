# MKM Secure Agent Runtime V0.9

Bounded local-first runtime candidate for MKM's Desktop Commander-class tool layer.

## Layer history

- V0: approved-root file/command primitives, Thin Coordinates, receipts
- V0.1: MCP stdio + exact one-time out-of-band HUMAN_GATE
- V0.2: deterministic privacy prefilter
- V0.3: Windows current-user DPAPI secret store
- V0.4: DPAPI-encrypted rollback snapshots
- V0.5: Windows tray approval UI + loopback-only Ollama manager
- V0.6: isolated Windows UIA Desktop Action Layer
- V0.7: process/class based App Adapter Layer
- V0.8: semantic Developer Adapter for VS Code/Cursor
- V0.9: dedicated Cursor Worker Session binding

## V0.9 Dedicated Cursor Worker Session

V0.9 does not infer that an arbitrary existing Cursor window has a supplied workspace open.

Instead it creates a dedicated worker session with:

- explicit approved workspace
- generated `.code-workspace` under MKM state, not inside the project
- exact folder mapping to that approved workspace
- unique `window.title` marker
- unique Cursor `--user-data-dir`
- `--new-window`
- `--disable-extensions`
- `--suppress-popups-on-startup`
- fixed Cursor CLI path discovered locally
- no arbitrary Cursor CLI argument input from the model

A session becomes `BOUND_ESTABLISHED` only when all of these hold:

1. generated workspace file hash still matches
2. workspace file still maps the exact approved workspace
3. a visible `cursor.exe` window contains the unique local marker
4. that window PID belongs to the Cursor process set carrying the exact session user-data-dir

Raw window title content is never returned through MCP.

## V0.9 session tools

- `request_dev_session_start`
- `execute_dev_session_start`
- `dev_session_status`
- `dev_session_workspace_status`
- `dev_session_git_diff`
- `dev_session_detect_tests`
- `request_dev_session_test`
- `execute_dev_session_test`
- `request_dev_session_close`
- `execute_dev_session_close`

Session start, test execution, and close are HUMAN_GATE actions.

## Session-scoped developer actions

Once a session is freshly verified as `BOUND_ESTABLISHED`, semantic developer actions use the verified session's own:

- `window_ref`
- `workspace_path`
- `bound_window_pid`

The old V0.8 request-scoped pair remains available for bounded research but still reports:

`REQUEST_SCOPED_PAIR_ASSOCIATION_NOT_ESTABLISHED`

The V0.9 session path is the first path in this branch that established a dedicated Cursor window/workspace association in an actual Windows smoke.

## Fixed test profile

The fixed pytest profile was hardened after a fresh side-effect observation.

Current profile:

```text
python -B -m pytest -q -p no:cacheprovider
```

This disables Python bytecode cache creation and pytest's cache provider.

Still unavailable:

- arbitrary terminal strings
- arbitrary shell command strings
- git commit/push/pull/fetch/checkout/reset
- package installation
- deploy/SEND
- secret injection

## Actual V0.9 Windows smoke

A synthetic Git workspace was used; no production repo, real secret, or patient data was involved.

Observed:

- Cursor CLI version: **3.17.19**
- MCP protocol: **2026-07-28**
- MCP tool count: **39**
- request before approval executed: **false**
- dedicated session start: **BOUND_ESTABLISHED**
- bound visible Cursor window PID observed
- session-specific Cursor process set observed
- session re-verification: **BOUND_ESTABLISHED**
- session-scoped Git status: 0 changes before test
- pytest profile detected
- approved session pytest return code: 0
- close status: `CLOSED_PROCESS_ONLY`
- only processes carrying the session user-data-dir were targeted for termination
- existing Cursor process count before/after close was unchanged
- session user-data/evidence directory was retained rather than deleted

### Fresh side effect retained

The first successful real V0.9 session test used the older fixed profile:

`python -m pytest -q`

It created untracked `__pycache__` artifacts in the synthetic workspace.

That is retained as a fresh failure / side-effect observation.

The profile was then changed to:

`python -B -m pytest -q -p no:cacheprovider`

A post-fix confirmation run on a new synthetic workspace observed:

- `BOUND_ESTABLISHED`
- pytest return code 0
- Cursor process count before/after: 32 -> 32
- worktree clean after test: true

This post-fix rerun confirms the patch behavior but is not promoted to independent fresh validation.

## Current validation

- full V0-V0.9 targeted Windows suite: **87 PASS**
- V0.8 + V0.9 targeted suite after cache-clean hardening: **17 PASS**
- V0.9 session-specific synthetic tests: **7 PASS**
- no V0.9 session Cursor process remained after final cleanup check

## Retained earlier failures

- in-process UIA COM fatal 0x8001010d -> UIA isolated in worker subprocess
- Windows CP949 decoding failure on UTF-8 Korean UI JSON -> explicit UTF-8 worker transport
- initial synthetic click without observable effect -> UIA InvokePattern preference
- Notepad launcher PID smoke NOT_FOUND -> retained; later Notepad observation was read-only only

## Evidence ceiling

`BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_9_CANDIDATE`

### FACT

- a dedicated Cursor worker window can be launched against an approved synthetic workspace
- its window/workspace association can be locally established through the V0.9 session binding mechanism
- session-scoped Git status/test actions can run under HUMAN_GATE
- the dedicated session can be closed without reducing the pre-existing Cursor process count in the observed smoke

### NOT_ESTABLISHED

- autonomous Cursor AI/Agent prompt submission
- Cursor-generated code editing as a worker
- cross-project reliability
- production repo safety
- independent security review
- production readiness

### HOLD / NOT AUTHORIZED

- arbitrary terminal commands
- git push/deploy/SEND
- browser mutation
- password/secret UI injection
- EMR production write
- PHI production use
- remote relay/device pairing
