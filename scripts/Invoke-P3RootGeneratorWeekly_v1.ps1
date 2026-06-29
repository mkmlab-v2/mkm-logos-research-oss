<#
.SYNOPSIS
  Weekly P3 Root Generator: pytest + extension chain + replacement logos seed + shallow slice.

.DESCRIPTION
  Track B · research_only · send_gate HOLD
  Runner: py scripts/run_p3_root_generator_weekly_v1.py

.PARAMETER OfflineShallow
  Skip live Ollama shallow router slice (offline skip only).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$OfflineShallow,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Set-Location -LiteralPath $resolvedRoot

$weeklyArgs = @("scripts/run_p3_root_generator_weekly_v1.py")
if ($OfflineShallow) {
    $weeklyArgs += "--offline-shallow"
}

py @weeklyArgs
if ($LASTEXITCODE -ne 0) {
    throw "p3_root_generator_weekly failed exit=$LASTEXITCODE"
}

Write-Host "p3_root_weekly: OK artifact=reports/p3_root_generator_ops_paste_v1_latest.md"
exit 0
