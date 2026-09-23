# MKM Secure Agent Runtime V0.8 — local setup

Development candidate only.

## Environment

```powershell
$env:MKM_AGENT_ROOTS = "C:\workspace\SAFE;F:\MKM_SAFE"
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

## V0.8 developer workflow

1. Observe a visible VS Code/Cursor window through `ui_list_windows`.
2. Confirm it identifies as `editor.vscode.v0` or `editor.cursor.v0`.
3. Supply an explicit approved `workspace_path`.
4. Use:
   - `dev_workspace_status`
   - `dev_git_diff`
   - `dev_detect_tests`
5. To run tests:
   - `request_dev_test`
   - approve locally in tray/CLI
   - `execute_dev_test`

Only the fixed profile is supported:

```text
pytest.quiet.v0
python -m pytest -q
```

The model cannot provide an arbitrary test command string.

## Important association limit

The current V0.8 pairing does not prove that a given Cursor/VS Code window has the supplied workspace open.

Returned binding state:

`REQUEST_SCOPED_PAIR_ASSOCIATION_NOT_ESTABLISHED`

The workspace remains protected independently by `MKM_AGENT_ROOTS`.

## Developer hard denials

- arbitrary terminal input
- git mutation/push/deploy
- package install
- secret injection
- SEND
- workspace outside approved roots

Evidence ceiling: `BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_8_CANDIDATE`.
