# MKM Secure Agent Runtime V0.9 — local setup

Development candidate only.

## Environment

```powershell
$env:MKM_AGENT_ROOTS = "C:\workspace\SAFE"
$env:MKM_AGENT_STATE = "$env:USERPROFILE\.mkm-agent-runtime"
$env:MKM_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:MKM_OLLAMA_AUTOSTART = "1"
```

Install:

```powershell
python -m pip install -r experiments\mkm_secure_agent_runtime_v0\requirements-mcp-v0.1.txt
```

Run MCP:

```powershell
python experiments\mkm_secure_agent_runtime_v0\mcp_server.py
```

Run tray:

```powershell
experiments\mkm_secure_agent_runtime_v0\start_tray.cmd
```

## V0.9 dedicated Cursor worker workflow

1. Request:
   `request_dev_session_start(workspace_path)`
2. Approve locally in tray/CLI.
3. Execute:
   `execute_dev_session_start(session_id, approval_id)`
4. Require:
   `binding_state = BOUND_ESTABLISHED`
5. Use session-scoped semantic actions:
   - `dev_session_workspace_status`
   - `dev_session_git_diff`
   - `dev_session_detect_tests`
6. To run tests:
   - `request_dev_session_test`
   - approve locally
   - `execute_dev_session_test`
7. To close:
   - `request_dev_session_close`
   - approve locally
   - `execute_dev_session_close`

## Dedicated session construction

The runtime generates a state-local `.code-workspace` file pointing at the exact approved workspace and assigns a unique window title marker.

Cursor is launched in a new window with a unique user-data-dir and extensions disabled.

The model does not supply arbitrary CLI flags.

## Binding semantics

`BOUND_ESTABLISHED` requires both semantic and process evidence:

- workspace file exact mapping and hash
- unique title marker present in a visible Cursor window
- visible window PID belongs to the process set carrying the exact session user-data-dir

If the PID changes, title fingerprint changes, marker disappears, or the workspace file changes, V0.9 does not silently rebind. It moves toward stale/fail-closed state.

## Fixed test command

```text
python -B -m pytest -q -p no:cacheprovider
```

This is fixed by code. No arbitrary test command string is accepted.

## Close semantics

Session close terminates only Cursor processes whose command lines carry the exact dedicated session user-data-dir.

The session state and user-data directory are retained for evidence in V0.9; they are not automatically deleted.

## Still prohibited

- arbitrary terminal command
- arbitrary Cursor CLI flags
- git commit/push/deploy
- secret injection
- SEND/payment/transfer/destructive actions
- PHI production use
- remote control

Evidence ceiling: `BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_9_CANDIDATE`.
