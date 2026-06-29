#Requires -Version 5.1
<#
.SYNOPSIS
  Daily ops patrol health — P0 + MCP hygiene + registry reconcile (no SafeOps/trading).
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$health = Join-Path $WorkspaceRoot 'scripts\run_workspace_automation_health.ps1'
if (-not (Test-Path -LiteralPath $health)) {
    throw "missing: $health"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $health `
    -SkipGateAlert -SkipExodusSourceFetch -SkipCompressionKpi -SkipGitSanity `
    -SafeOpsShadowSolo
exit $LASTEXITCODE
