# Local Main + SSH Ops Runbook

## Operating Model

- Development main: local Cursor
- Server operations: SSH Cursor
- Sync axis: Git (`push`/`pull`) + GitHub Actions

## Command Bootstrap (PowerShell)

Load local commands once per terminal:

```powershell
. C:\workspace\projects\bitcoin-trading\ops\v2\tasks\set-local-main-aliases.ps1
```

Available commands:

- `devsync`: fetch + rebase pull + short status
- `gsync`: sync NotebookLM source manifest to MKM data vault
- `gsyncall`: `devsync` + `gsync`
- `server-check`: remote host/process health check
- `deploy`: remote `git pull` deployment

## Environment Variables For SSH Ops

Set these in your shell profile or user environment:

- `MKM_VPS_HOST`
- `MKM_VPS_USER`

Examples:

```powershell
$env:MKM_VPS_HOST = "your.vps.host"
$env:MKM_VPS_USER = "ubuntu"
server-check
deploy
```

## CI/CD Separation Rule

- `CI/CD Pipeline` runs on `push`/`pull_request` for validation.
- Deploy job only runs on manual `workflow_dispatch`.
- This avoids accidental deploy failures on main pushes when deploy secrets are not set.
