#Requires -Version 5.1
<#
.SYNOPSIS
  One-click daily lens ops: Logos OOS promote · parallel advance · Telegram four_lens.

.DESCRIPTION
  B-track / research_only. No Track A promotion. Exit 0 if Telegram sent.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipBtrack10Lane,
    [switch]$SkipTelegram,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if ($WhatIf) {
    Write-Host "[WhatIf] logos_oos_gate_promote -> Run-LensAdvanceParallel -> telegram"
    exit 0
}

Write-Host "==> logos OOS promote (best 252/120/60d -> latest)" -ForegroundColor Cyan
& $py scripts/logos_oos_gate_promote_v1.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] no go=true OOS snapshot to promote; maturity may use stale latest" -ForegroundColor Yellow
}

$advanceArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", "scripts\Run-LensAdvanceParallel_v1.ps1",
    "-WorkspaceRoot", $WorkspaceRoot
)
if (-not $SkipBtrack10Lane) { $advanceArgs += "-IncludeBtrack10Lane" }
if (-not $SkipTelegram) { $advanceArgs += "-SendTelegram" }
else { $advanceArgs += "-SkipTelegram" }

& powershell @advanceArgs
exit $LASTEXITCODE
