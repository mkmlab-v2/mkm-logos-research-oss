# MKM Secure Agent Runtime V0.7 — local setup

This is a bounded development setup, not a production deployment.

## Requirements

- Windows
- Python 3.10+
- isolated environment
- explicit filesystem roots
- state directory outside those roots

Install:

```powershell
python -m pip install -r experiments\mkm_secure_agent_runtime_v0\requirements-mcp-v0.1.txt
```

## Environment

```powershell
$env:MKM_AGENT_ROOTS = "C:\workspace\SAFE;F:\MKM_SAFE"
$env:MKM_AGENT_STATE = "$env:USERPROFILE\.mkm-agent-runtime"
$env:MKM_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:MKM_OLLAMA_AUTOSTART = "1"
```

## Start stdio MCP

```powershell
python experiments\mkm_secure_agent_runtime_v0\mcp_server.py
```

## Start local tray

```powershell
experiments\mkm_secure_agent_runtime_v0\start_tray.cmd
```

## V0.7 App Adapter rule

V0.7 adapters are a mandatory narrowing layer for UI mutation in the normal server path.

Observation:
- `ui_list_windows` and `ui_inspect_window` remain available
- window titles are hidden by default
- content-bearing control strings are hidden

Mutation:
- legacy `request_ui_click` / `request_ui_set_text` are denied when adapters are active
- use `app_identify_window` first
- use `app_inspect_window` to obtain bounded controls
- use `request_app_click` or `request_app_set_text`
- local tray/CLI approval is still required
- execute exact approved action through `execute_app_*`

Adapter permission does not override the Desktop Action Layer:
- high-risk control label -> DENY
- password field -> DENY
- sensitive text -> DENY
- stale/ambiguous UI ref -> DENY/error
- wrong window/control binding -> DENY

## Builtin policy

Browsers:
- OBSERVE_ONLY

Windows Explorer:
- OBSERVE_ONLY

Notepad / VS Code / Cursor:
- bounded click/edit candidate
- still subject to all Desktop Action Layer DENY rules

Unmatched app:
- OBSERVE_ONLY

Ambiguous adapter match:
- fail closed

## Current limits

- no browser mutation
- no password/secret injection
- no raw hotkeys
- no coordinate automation
- no SEND/payment/transfer/destructive actions
- no EMR production write
- no PHI production authorization
- no remote control

Evidence ceiling: `BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_7_CANDIDATE`.
