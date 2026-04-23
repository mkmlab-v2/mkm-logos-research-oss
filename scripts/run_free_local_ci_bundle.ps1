<#
.SYNOPSIS
  무료(Hosted Runner 미사용) 운영용 로컬 CI 번들 실행기.

.DESCRIPTION
  GitHub Actions의 핵심 워크플로를 로컬에서 순차 실행한다.
  기본 실행:
    1) scripts/run_fact_lock_bundle.ps1
    2) scripts/run_manseryeok_validation_smoke_v1.py
    3) scripts/run_l1_inverse_decoder_spike_test.py

  선택 실행:
    - projects/no1kmedi npm ci + npm run build

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_free_local_ci_bundle.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_free_local_ci_bundle.ps1 -SkipFactLock -SkipNo1kmediBuild
#>
param(
    [switch]$SkipFactLock,
    [switch]$SkipManseryeok,
    [switch]$SkipL1Smoke,
    [switch]$RunNo1kmediBuild,
    [switch]$SkipNo1kmediBuild
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    Write-Host "== Local CI: $Name ==" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit=$LASTEXITCODE)"
    }
}

Set-Location -LiteralPath $workspaceRoot

if (-not $SkipFactLock) {
    $factLockScript = Join-Path $workspaceRoot 'scripts\run_fact_lock_bundle.ps1'
    if (-not (Test-Path -LiteralPath $factLockScript)) {
        throw "Missing script: $factLockScript"
    }
    Invoke-Step -Name 'Fact-Lock bundle' -Action {
        powershell -NoProfile -ExecutionPolicy Bypass -File $factLockScript
    }
}

if (-not $SkipManseryeok) {
    $manseryeokScript = Join-Path $workspaceRoot 'scripts\run_manseryeok_validation_smoke_v1.py'
    if (-not (Test-Path -LiteralPath $manseryeokScript)) {
        throw "Missing script: $manseryeokScript"
    }
    Invoke-Step -Name 'manseryeok validation smoke' -Action {
        py $manseryeokScript
    }
}

if (-not $SkipL1Smoke) {
    $l1Script = Join-Path $workspaceRoot 'scripts\run_l1_inverse_decoder_spike_test.py'
    if (-not (Test-Path -LiteralPath $l1Script)) {
        throw "Missing script: $l1Script"
    }
    Invoke-Step -Name 'L1 inverse decoder spike smoke' -Action {
        py $l1Script --samples 24 --noise-level 0.1 --seed 701
    }
}

$shouldRunNo1kmedi = $RunNo1kmediBuild -and (-not $SkipNo1kmediBuild)
if ($shouldRunNo1kmedi) {
    $no1kmediDir = Join-Path $workspaceRoot 'projects\no1kmedi'
    if (-not (Test-Path -LiteralPath $no1kmediDir)) {
        throw "Missing directory: $no1kmediDir"
    }
    Invoke-Step -Name 'no1kmedi npm ci' -Action {
        npm --prefix $no1kmediDir ci
    }
    Invoke-Step -Name 'no1kmedi npm run build' -Action {
        npm --prefix $no1kmediDir run build
    }
}

Write-Host 'Local CI bundle completed.' -ForegroundColor Green
exit 0
