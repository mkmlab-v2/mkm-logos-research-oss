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
$probeJson = Join-Path $repoRoot "reports\notebooklm_mcp_health_probe_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("o")

Write-Host "=== NotebookLM MCP auth auto-repair ===" -ForegroundColor Cyan

function Invoke-PyQuiet {
    param([string[]]$PyArgs)
    $proc = Start-Process -FilePath "py" `
        -ArgumentList $PyArgs `
        -WorkingDirectory $repoRoot `
        -Wait -PassThru -NoNewWindow
    if ($null -eq $proc.ExitCode) { return 0 }
    return [int]$proc.ExitCode
}

function Invoke-NlSyncAndProbe {
    Write-Host "[sync] nlm cookies -> MCP state.json" -ForegroundColor Yellow
    $syncExit = Invoke-PyQuiet @($syncPy)
    if ($syncExit -ne 0) { throw "sync exit $syncExit" }

    $probeArgs = @($probePy, "--no-sync-nlm-first")
    if ($AllowInteractiveSetupAuth) { $probeArgs += "--setup-if-needed" }

    Write-Host "[probe] MCP get_health via stdio" -ForegroundColor Yellow
    return (Invoke-PyQuiet $probeArgs)
}

function Read-NlProbeAuthenticated {
    if (-not (Test-Path -LiteralPath $probeJson)) { return $false }
    $probe = Get-Content -LiteralPath $probeJson -Raw -Encoding utf8 | ConvertFrom-Json
    return ([bool]$probe.authenticated -and [bool]$probe.ok)
}

function Write-NlRepairArtifact {
    param(
        [int]$NlmCheckExit,
        [int]$ProbeExit,
        [bool]$Authenticated,
        [bool]$Ok
    )
    $payload = [ordered]@{
        schema           = "notebooklm_mcp_auth_auto_repair_v1"
        generated_at_utc = $utc
        nlm_check_exit   = $NlmCheckExit
        probe_exit       = $ProbeExit
        authenticated    = $Authenticated
        account_expected = "admin@no1kmedi.com"
        cursor_note      = "If Cursor MCP shows Not connected: Developer Reload Window + new chat; get_health in chat."
        ssot             = "docs/NotebookLM_sources_manifest.md"
        ok               = $Ok
    }
    ($payload | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $outJson -Encoding utf8
    return $payload
}

if (Test-Path -LiteralPath $recovery) {
    $recArgs = @()
    if ($SkipPrereqCheck) { $recArgs += "-SkipPrereqCheck" }
    if ($WhatIfOnly) { $recArgs += "-WhatIfOnly" }
    & $recovery @recArgs
    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) { throw "recovery helper exit $LASTEXITCODE" }
}

# Fast path: cookie sync + stdio probe before nlm CLI (avoids Chrome CDP login hang in solo_ops).
$probeExit = Invoke-NlSyncAndProbe
$authenticated = Read-NlProbeAuthenticated
if ($authenticated) {
    $payload = Write-NlRepairArtifact -NlmCheckExit 0 -ProbeExit $probeExit -Authenticated $true -Ok $true
    Write-Host "OK: NotebookLM MCP authenticated=$authenticated (fast path, skipped nlm login) -> $outJson" -ForegroundColor Green
    exit 0
}

Write-Host "[nlm] login check" -ForegroundColor Yellow
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& nlm login --check 2>&1 | Write-Host
$nlmCheck = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }

$nlmLoginExit = 0
if ($nlmCheck -ne 0) {
    Write-Host "[nlm] login refresh (Chrome CDP)" -ForegroundColor Yellow
    & nlm login 2>&1 | Write-Host
    $nlmLoginExit = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($nlmLoginExit -ne 0) {
        Write-Warning "nlm login exit $nlmLoginExit (tier_3 human: run nlm login in terminal); continuing to cookie sync/probe"
    }
}
$ErrorActionPreference = $prevEap

$probeExit = Invoke-NlSyncAndProbe
$authenticated = Read-NlProbeAuthenticated
$payload = Write-NlRepairArtifact -NlmCheckExit $nlmCheck -ProbeExit $probeExit -Authenticated $authenticated -Ok $authenticated

if (-not $payload.ok) {
    Write-Warning "NL auto-repair incomplete authenticated=$authenticated probe_exit=$probeExit"
    exit 1
}

Write-Host "OK: NotebookLM MCP authenticated=$authenticated -> $outJson" -ForegroundColor Green
exit 0
