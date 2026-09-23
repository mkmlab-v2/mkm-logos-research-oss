# MKM Secure Agent Runtime V0.3 — local stdio setup

This is a bounded development setup, not a production deployment.

## Requirements

- Windows for DPAPI secret storage
- Python 3.10+
- isolated environment with `mcp>=2,<3`
- explicit filesystem roots
- approval/secret state directory outside those roots

## Environment

```powershell
$env:MKM_AGENT_ROOTS = "C:\workspace\SAFE;F:\MKM_SAFE"
$env:MKM_AGENT_STATE = "$env:USERPROFILE\.mkm-agent-runtime"
$env:MKM_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
```

The server fails closed if `MKM_AGENT_ROOTS` or `MKM_AGENT_STATE` is missing.

## Run stdio MCP server

```powershell
python experiments\mkm_secure_agent_runtime_v0\mcp_server.py
```

The host should launch that command as an MCP stdio subprocess.

## Write / command approval

The model can only request an action. It cannot set an approval boolean.

```powershell
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py show <approval_id>
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py approve <approval_id>
# or
python experiments\mkm_secure_agent_runtime_v0\approval_cli.py deny <approval_id>
```

The approval is bound to the exact target + argument digest and is consumed once.

## Local DPAPI secret management

Set a secret from the local terminal; input is collected through `getpass` and is not echoed.

```powershell
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py set secret://github/main --service github --label main
```

Metadata only:

```powershell
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py show secret://github/main
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py list
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py verify secret://github/main
```

Removal is local CLI only:

```powershell
python experiments\mkm_secure_agent_runtime_v0\secret_cli.py remove secret://github/main
```

There is intentionally no command that prints the decrypted secret.

## Privacy gate

Before `read_text_file` releases local text to the MCP host, a deterministic local scan runs.

- SECRET -> body blocked / DENY
- direct identifier + medical context -> body blocked / PHI HOLD
- PERSONAL -> body blocked / HOLD
- otherwise -> INTERNAL / ALLOW

This is a prefilter, not complete DLP. Person-name detection is explicitly NOT_ESTABLISHED.

## Current limits

- no deletion/move
- no git push/deploy/SEND
- no secret injection into commands or browser
- no remote relay
- no browser/GUI automation
- no PHI production authorization
- Ollama must be loopback-only

Evidence ceiling: `BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_3_CANDIDATE`.
