#Requires -Version 5.1
<#
.SYNOPSIS
  AI-to-AI governance delegation v1 — meta envelope + ops memory AUTO chain.

.DESCRIPTION
  SSOT: reports/ai_to_ai_governance_delegation_v1_latest.json
  승인표: reports/delegation_ai_to_ai_governance_approval_map_v1_latest.json
  Track A / live / apply-active / MISSION_LOG 쓰기 금지.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AiToAiGovernanceDelegation_v1.ps1
  powershell … -ParallelPytest -SkipP0
#>
param(
    [switch]$DryRun,
    [switch]$SkipP0,
    [switch]$SkipWebOpsOverlay,
    [switch]$ParallelPytest
)

$ErrorActionPreference = 'Stop'
$Root = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Push-Location -LiteralPath $Root
try {
    $pyArgs = @('scripts/run_ai_to_ai_governance_delegation_v1.py')
    if ($DryRun) { $pyArgs += '--dry-run' }
    if ($SkipP0) { $pyArgs += '--skip-p0' }
    if ($SkipWebOpsOverlay) { $pyArgs += '--skip-web-ops-overlay' }
    if ($ParallelPytest) { $pyArgs += '--parallel-pytest' }
    & py @pyArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
