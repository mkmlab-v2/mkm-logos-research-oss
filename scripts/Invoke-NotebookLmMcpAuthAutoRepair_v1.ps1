<#
.SYNOPSIS
  NotebookLM MCP auth auto-repair (tier_0, no paid API).

.DESCRIPTION
  1) prereq + zombie repair + KO selectors patch
  2) nlm login --check (refresh via nlm login if needed)
  3) sync nlm CLI cookies -> MCP state.json
  4) stdio get_health probe (authenticated=true target)

  Does NOT call setup_auth unless -AllowInteractiveSetupAuth and probe still fails.
  Account SSOT: admin@no1kmedi.com (Workspace) per notebooklm-mcp-session-bridge.mdc.

.EXAMPLE
  powershell -File scripts\Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1
#>
param(
    [switch]$SkipPrereqCheck,
    [switch]$AllowInteractiveSetupAuth,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $repoRoot

$recovery = Join-Path $PSScriptRoot "invoke_notebooklm_mcp_auth_recovery_v1.ps1"
$syncPy = Join-Path $PSScriptRoot "sync_notebooklm_nlm_credentials_to_mcp_v1.py"
$probePy = Join-Path $PSScriptRoot "probe_notebooklm_mcp_health_v1.py"
$outJson = Join-Path $repoRoot "reports\notebooklm_mcp_auth_auto_repair_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("o")

Write-Host "=== NotebookLM MCP auth auto-repair ===" -ForegroundColor Cyan

if (Test-Path -LiteralPath $recovery) {
    $recArgs = @()
    if ($SkipPrereqCheck) { $recArgs += "-SkipPrereqCheck" }
    if ($WhatIfOnly) { $recArgs += "-WhatIfOnly" }
    & $recovery @recArgs
    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) { throw "recovery helper exit $LASTEXITCODE" }
}

Write-Host "[nlm] login check" -ForegroundColor Yellow
& nlm login --check 2>&1 | Write-Host
$nlmCheck = $LASTEXITCODE
if ($null -eq $nlmCheck) { $nlmCheck = 0 }

if ($nlmCheck -ne 0) {
    Write-Host "[nlm] login refresh (Chrome CDP)" -ForegroundColor Yellow
    & nlm login 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) { throw "nlm login exit $LASTEXITCODE" }
}

Write-Host "[sync] nlm cookies -> MCP state.json" -ForegroundColor Yellow
& py $syncPy
if ($LASTEXITCODE -ne 0) { throw "sync exit $LASTEXITCODE" }

$probeArgs = @($probePy, "--no-sync-nlm-first")
if ($AllowInteractiveSetupAuth) { $probeArgs += "--setup-if-needed" }

Write-Host "[probe] MCP get_health via stdio" -ForegroundColor Yellow
& py @probeArgs
$probeExit = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }

$probeJson = Join-Path $repoRoot "reports\notebooklm_mcp_health_probe_v1_latest.json"
$authenticated = $false
if (Test-Path -LiteralPath $probeJson) {
    $probe = Get-Content -LiteralPath $probeJson -Raw -Encoding utf8 | ConvertFrom-Json
    $authenticated = [bool]$probe.authenticated
}

$payload = [ordered]@{
    schema           = "notebooklm_mcp_auth_auto_repair_v1"
    generated_at_utc = $utc
    nlm_check_exit   = $nlmCheck
    probe_exit       = $probeExit
    authenticated    = $authenticated
    account_expected = "admin@no1kmedi.com"
    cursor_note      = "If Cursor MCP shows Not connected: Developer Reload Window + new chat; get_health in chat."
    ssot             = "docs/NotebookLM_sources_manifest.md"
    ok               = ($probeExit -eq 0 -and $authenticated)
}

($payload | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $outJson -Encoding utf8

if (-not $payload.ok) {
    Write-Warning "NL auto-repair incomplete authenticated=$authenticated probe_exit=$probeExit"
    exit 1
}

Write-Host "OK: NotebookLM MCP authenticated=$authenticated -> $outJson" -ForegroundColor Green
exit 0
