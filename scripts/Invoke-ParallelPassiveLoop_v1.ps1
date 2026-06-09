#Requires -Version 5.1
<#
.SYNOPSIS
  병렬 패시브 루프 v1 — shim · L1 canary · MAX_HYPO(조건부) · web_ops 4레인 AUTO.

.DESCRIPTION
  SSOT: reports/parallel_passive_loop_v1_latest.json
  승인표: reports/delegation_parallel_passive_loop_approval_map_v1_latest.json
  Track A / live / apply-active / MISSION_LOG 쓰기 금지.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ParallelPassiveLoop_v1.ps1
#>
param(
    [switch]$DryRun,
    [switch]$Sequential,
    [switch]$SkipShim,
    [switch]$SkipL1,
    [switch]$SkipMaxHypo,
    [switch]$IncludeWebOps,
    [switch]$SkipLiveCdp
)

$ErrorActionPreference = 'Stop'
$Root = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Push-Location -LiteralPath $Root
try {
    $pyArgs = @('scripts/run_parallel_passive_loop_v1.py')
    if ($DryRun) { $pyArgs += '--dry-run' }
    if ($Sequential) { $pyArgs += '--sequential' }
    if ($SkipShim) { $pyArgs += '--skip-shim' }
    if ($SkipL1) { $pyArgs += '--skip-l1' }
    if ($SkipMaxHypo) { $pyArgs += '--skip-max-hypo' }
    if ($IncludeWebOps) { $pyArgs += '--include-web-ops' }
    if ($SkipLiveCdp) { $pyArgs += '--skip-live-cdp' }

    & py @pyArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
