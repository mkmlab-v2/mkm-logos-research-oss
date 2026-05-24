#Requires -Version 5.1
<#
.SYNOPSIS
  O-P22 wrapper: coordinator lens conflict observation (info webhook, exit 0 on semantic conflict).

.DESCRIPTION
  Runs check_coordinator_lens_conflict_observation_v1.py.
  Webhook: MKM_COORD_CONFLICT_WEBHOOK_URL, else OPS_ALARM_WEBHOOK_URL.
  Infrastructure/schema failure from Python exits 1.

.PARAMETER SkipWebhook
  Pass --skip-webhook to Python (no POST).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipWebhook
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($WorkspaceRoot) { $WorkspaceRoot } else { Split-Path -Parent $PSScriptRoot }
Set-Location -LiteralPath $repoRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$script = Join-Path $PSScriptRoot "check_coordinator_lens_conflict_observation_v1.py"
if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing script: $script"
}

$cli = @($script, "--workspace-root", $repoRoot)
if ($SkipWebhook) {
    $cli += "--skip-webhook"
}

& $py @cli
$exitCode = [int]$LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "[CRITICAL] Coordinator lens conflict observation: infrastructure or schema failure (exit=$exitCode)."
    exit $exitCode
}

Write-Host "coordinator_lens_conflict_observation_ok exit=0" -ForegroundColor Green
exit 0
