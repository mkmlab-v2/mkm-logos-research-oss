<#
.SYNOPSIS
  NL 06: nlm dedupe by title (requires `nlm login` in same Windows user session).

.PARAMETER NotebookId
  Google notebook UUID (default: 06 smartfarm).

.PARAMETER WhatIf
  List duplicate source ids only.

.PARAMETER Confirm
  Actually delete duplicate titles (keeps last per normalized title).
#>
param(
    [string]$NotebookId = "96865180-769e-4a77-89bb-5f03a8083ac3",
    [switch]$WhatIf,
    [switch]$Confirm
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dedupe = Join-Path $root "scripts\notebooklm_dedupe_sources_by_title.ps1"
if (-not (Get-Command nlm -ErrorAction SilentlyContinue)) {
    Write-Error "nlm not in PATH. Install NotebookLM CLI and run: nlm login"
}
$probe = & nlm notebook get $NotebookId --json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "nlm auth failed. In an interactive terminal run: nlm login" -ForegroundColor Yellow
    Write-Host "Then: pwsh -File scripts/Invoke-Notebooklm06NlmPrune_v1.ps1 -WhatIf" -ForegroundColor Yellow
    Write-Host "Delete checklist (web UI): reports/notebooklm_06_delete_titles_web_ui_v1.txt" -ForegroundColor Cyan
    exit 2
}
$args = @("-NotebookId", $NotebookId)
if ($WhatIf) { $args += "-WhatIf" }
if ($Confirm) { $args += "-Confirm" }
& powershell -NoProfile -ExecutionPolicy Bypass -File $dedupe @args
exit $LASTEXITCODE
