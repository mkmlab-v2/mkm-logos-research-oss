# MKM Secure Agent Runtime V0.6 — local setup

This is a bounded development setup, not a production deployment.

## Requirements

- Windows
- Python 3.10+
- isolated environment with V0.6 requirements
- explicit filesystem roots
- state directory outside those roots

Install:

```powershell
python -m pip install -r experiments\mkm_secure_agent_runtime_v0\requirements-mcp-v0.1.txt
```

Current dependency range includes MCP v2, pystray, Pillow, pywinauto 0.6.x, and psutil.

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

## Desktop Action Layer policy

Observation:
- top-level windows can be listed
- window titles are hidden by default
- controls receive short-lived opaque `ui_ref` identifiers
- content-bearing Edit/Text/Document labels are hidden

Mutation:
- low-risk click -> request approval -> local Approve once -> execute exact action
- clean text on Edit -> request approval -> local Approve once -> execute exact text
- password controls -> DENY
- PERSONAL/PHI/SECRET input -> DENY
- high-risk labels (Delete/Send/Pay/Transfer/Purchase/Deploy etc.) -> DENY

There is intentionally:
- no raw coordinate click tool
- no raw keyboard/hotkey tool
- no model-visible human_approved boolean
- no UI secret injection tool

## UIA isolation

pywinauto UIA runs in `desktop_worker.py`, a separate Python subprocess.

This is deliberate: an observed in-process COM fatal exception showed that UI Automation can terminate its host process. The isolated worker limits that failure domain to the worker. A worker crash/timeout becomes a runtime error rather than direct MCP-process termination.

The worker JSON pipe is explicitly UTF-8 because Windows default CP949 decoding failed when Korean UI text was present.

## Current limits

- no bank/credential-manager automation
- no EMR write authorization
- no SEND/payment/transfer/destructive UI automation
- no browser secret injection
- no remote relay
- no general mouse/keyboard automation
- no PHI production authorization

Evidence ceiling: `BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_6_CANDIDATE`.
