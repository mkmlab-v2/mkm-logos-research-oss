# MKM Secure Agent Runtime V0.5 — local setup

This is a bounded development setup, not a production deployment.

## Requirements

- Windows for DPAPI secret storage and tray shell
- Python 3.10+
- isolated environment with the V0.5 requirements
- explicit filesystem roots
- approval/secret/snapshot state directory outside those roots

Install into an isolated environment:

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

The runtime fails closed if `MKM_AGENT_ROOTS` or `MKM_AGENT_STATE` is missing.

## Run stdio MCP server

```powershell
python experiments\mkm_secure_agent_runtime_v0\mcp_server.py
```

## Run Windows tray UI

```powershell
experiments\mkm_secure_agent_runtime_v0\start_tray.cmd
```

or:

```powershell
python experiments\mkm_secure_agent_runtime_v0\tray_app.py
```

The tray app:
- watches local REQUESTED approvals
- opens a popup only when a new approval arrives
- supports Approve once / Deny
- shows bounded runtime/Ollama status
- can start local Ollama with OLLAMA_HOST forced to 127.0.0.1:11434
- stops only Ollama processes that it started itself when the tray exits

Set `MKM_OLLAMA_AUTOSTART=0` to disable tray-start Ollama autostart.

## Write / command approval

The model can request an action but cannot set an approval boolean. Approval must occur through the local CLI or local tray UI.

CLI fallback:

```powershell
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py show <approval_id>
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py approve <approval_id>
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py deny <approval_id>
```

The approval is bound to the exact target + argument digest and is consumed once.

## Local DPAPI secret management

```powershell
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py set secret://github/main --service github --label main
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py show secret://github/main
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py list
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py verify secret://github/main
```

There is intentionally no CLI or MCP command that prints decrypted secret material.

## Rollback

Approved text writes return a `snapshot_id` when rollback storage is available.

```powershell
python experiments\mkm_secure_agent_runtime_v0\rollback_cli.py show <snapshot_id>
python experiments\mkm_secure_agent_runtime_v0\rollback_cli.py restore <snapshot_id>
```

Rollback remains local CLI only.

## Privacy gate

Before `read_text_file` releases local text through MCP, a deterministic local scan runs.

- SECRET -> body blocked / DENY
- direct identifier + medical context -> body blocked / PHI HOLD
- PERSONAL -> body blocked / HOLD
- otherwise -> INTERNAL / ALLOW

This is a prefilter, not complete DLP. Person-name detection is NOT_ESTABLISHED.

## Current limits

- no third-party GUI/browser automation
- no delete/move tool
- no git push/deploy/SEND
- no secret injection into commands/browser
- no remote relay/device pairing
- no PHI production authorization
- no persistent Windows installer/startup registration yet

Evidence ceiling: `BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_5_CANDIDATE`.
