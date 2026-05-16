#Requires -Version 5.1
<#
.SYNOPSIS
  Fact-Lock 페르소나 래퍼 — 고정 스크립트만 호출한다 (판단·추측 금지, exit code SSOT).

.DESCRIPTION
  AGENTS.md 「페르소나 단축 호출」표와 1:1. 추가 스위치는 하위 스크립트를 직접 호출할 것.

.PARAMETER Persona
  AthenaBundle = run_fact_lock_bundle.ps1
  PremiumMultilensQueue = Invoke-PremiumMultilensQueueRoutine_v1.ps1 (pytest 4 + drain allow-missing + S1 promotion gate --skip-pytest)
  AmsaengHealth = run_workspace_automation_health.ps1 (기본 인자만)
  P0 = verify_p0_constitution_gate_paths.ps1
  AramaicDailyReadiness = Verify-AramaicMvpDailyTaskReadiness.ps1 (Windows Task Scheduler; 미등록 시 실패)
  GpuRecommendedBundle = run_workspace_automation_health.ps1 -MkmGpuRecommendedBundleOnly (P0 + reconcile + Run-MkmGpuRecommendedBundle_v1)

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona PremiumMultilensQueue

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AmsaengHealth

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona P0

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AramaicDailyReadiness

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona GpuRecommendedBundle
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('AthenaBundle', 'PremiumMultilensQueue', 'AmsaengHealth', 'P0', 'AramaicDailyReadiness', 'GpuRecommendedBundle')]
    [string]$Persona
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$WorkspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    throw "WorkspaceRoot not found: $WorkspaceRoot"
}

Push-Location -LiteralPath $WorkspaceRoot
try {
    $ps = 'powershell.exe'
    $common = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File')

    switch ($Persona) {
        'AthenaBundle' {
            $script = Join-Path $PSScriptRoot 'run_fact_lock_bundle.ps1'
            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }
            & $ps @common $script
            exit $LASTEXITCODE
        }
        'PremiumMultilensQueue' {
            $script = Join-Path $PSScriptRoot 'Invoke-PremiumMultilensQueueRoutine_v1.ps1'
            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }
            & $ps @common $script
            exit $LASTEXITCODE
        }
        'AmsaengHealth' {
            $script = Join-Path $PSScriptRoot 'run_workspace_automation_health.ps1'
            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }
            & $ps @common $script
            exit $LASTEXITCODE
        }
        'P0' {
            $script = Join-Path $PSScriptRoot 'verify_p0_constitution_gate_paths.ps1'
            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }
            & $ps @common $script
            exit $LASTEXITCODE
        }
        'AramaicDailyReadiness' {
            $script = Join-Path $PSScriptRoot 'Verify-AramaicMvpDailyTaskReadiness.ps1'
            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }
            & $ps @common $script
            exit $LASTEXITCODE
        }
        'GpuRecommendedBundle' {
            $script = Join-Path $PSScriptRoot 'run_workspace_automation_health.ps1'
            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }
            & $ps @common $script -WorkspaceRoot $WorkspaceRoot -MkmGpuRecommendedBundleOnly
            exit $LASTEXITCODE
        }
        default {
            throw "Unhandled Persona: $Persona"
        }
    }
}
finally {
    Pop-Location
}
