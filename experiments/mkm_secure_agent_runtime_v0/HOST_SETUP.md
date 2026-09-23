# MKM Secure Agent Runtime V0.1 — local stdio setup

This is a bounded development setup, not a production deployment.

## Requirements

- Python 3.10+
- isolated environment with `mcp>=2,<3`
- explicit filesystem roots
- approval state directory outside those roots

## Environment

Windows example:

```powershell
$env:MKM_AGENT_ROOTS = "C:\workspace\SAFE;F:\MKM_SAFE"
$env:MKM_AGENT_STATE = "$env:USERPROFILE\.mkm-agent-runtime"
$env:MKM_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
```

The server fails closed if `MKM_AGENT_ROOTS` or `MKM_AGENT_STATE` is missing.

## Run stdio server

```powershell
python experiments\mkm_secure_agent_runtime_v0\mcp_server.py
```

A host should launch that command as an MCP stdio subprocess. The official MCP Python SDK v2 negotiates the protocol.

## Human gate

When the model requests a write or command it receives an `approval_id` and nothing is executed.

Review locally:

```powershell
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py show <approval_id>
```

Approve once:

```powershell
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py approve <approval_id>
```

Or deny:

```powershell
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py deny <approval_id>
```

The model then has to resubmit the exact action and approval id. Changed path/content/argv does not match the approval digest.

## Current limits

- no deletion/move
- no git push/deploy/SEND
- no real credential retrieval
- no remote relay
- no browser/GUI automation
- no PHI production authorization
- Ollama must be loopback-only

Evidence ceiling: `BOUNDED_LOCAL_MCP_RUNTIME_CANDIDATE`.
