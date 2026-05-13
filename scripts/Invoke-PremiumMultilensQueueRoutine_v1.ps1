#Requires -Version 5.1
<#
.SYNOPSIS
  프리미엄 멀티렌즈 파일 큐 권장 루틴 — pytest 4종 + queue drain v0 + S1 promotion gate.

.DESCRIPTION
  SSOT: docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md Premium 행.
  기본 drain은 `--allow-missing-queue`(큐 파일 없으면 SKIP·exit 0). ack 기록은 `-WriteAck`.
  선택 `-ExportPendingJson`로 `export-pending` 산출(대기 행 + 렌즈 스크립트 포인터; 서브프로세스 없음).
  말단 **S1 shadow 승격 게이트** `build_premium_multilens_queue_promotion_gate_v1.py --skip-pytest`(pytest 직후 중복 회피)는 기본 실행; `-SkipPromotionGate`로 생략.
  Fact-Lock 번들 `run_fact_lock_bundle.ps1` 단계 4b는 동일 pytest 직후 drain(allow-missing)+gate(--skip-pytest)를 포함한다.

.PARAMETER SkipPromotionGate
  말단 S1 shadow 승격 게이트(`build_premium_multilens_queue_promotion_gate_v1.py`) 생략.

.PARAMETER WorkspaceRoot
  비우면 MKM_WORKSPACE_ROOT, 없으면 본 스크립트 상위(모노레포 루트).

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PremiumMultilensQueueRoutine_v1.ps1

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PremiumMultilensQueueRoutine_v1.ps1 -WriteAck -DrainMaxJobs 10

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PremiumMultilensQueueRoutine_v1.ps1 -ExportPendingJson reports\premium_multilens_queue_pending_export_v0_latest.json
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipPytest,
    [switch]$SkipDrain,
    [switch]$WriteAck,
    [switch]$StrictMissingQueue,
    [ValidateRange(1, 9999)]
    [int]$DrainMaxJobs = 25,
    [string]$ExportPendingJson = "",
    [switch]$SkipPromotionGate
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = if ($WorkspaceRoot -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    (Resolve-Path -LiteralPath $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')).Path
}
else {
    (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
}

if (-not (Test-Path -LiteralPath $root)) {
    throw "WorkspaceRoot not found: $root"
}

$prSchema = Join-Path $root 'tests\test_premium_btrack_multilens_report_schema_v1.py'
$prBuild = Join-Path $root 'tests\test_build_premium_btrack_multilens_report_v1.py'
$prQueue = Join-Path $root 'tests\test_premium_multilens_job_queue_stub_v1.py'
$prGate = Join-Path $root 'tests\test_build_premium_multilens_queue_promotion_gate_v1.py'
$stub = Join-Path $root 'scripts\premium_multilens_job_queue_stub_v1.py'
$gate = Join-Path $root 'scripts\build_premium_multilens_queue_promotion_gate_v1.py'

Push-Location -LiteralPath $root
try {
    if (-not $SkipPytest) {
        if (-not ((Test-Path -LiteralPath $prSchema) -and (Test-Path -LiteralPath $prBuild) -and (Test-Path -LiteralPath $prQueue) -and (Test-Path -LiteralPath $prGate))) {
            throw "Missing premium multilens pytest file(s) under $root"
        }
        Write-Host '== Premium multilens: pytest (schema + builder + queue stub + promotion gate) ==' -ForegroundColor Cyan
        & py -m pytest $prSchema $prBuild $prQueue $prGate -q --tb=short
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    if (-not $SkipDrain) {
        if (-not (Test-Path -LiteralPath $stub)) {
            throw "Missing: $stub"
        }
        Write-Host '== Premium multilens: queue drain v0 ==' -ForegroundColor Cyan
        $drainArgs = @($stub, 'drain', '--root', $root, '--max-jobs', "$DrainMaxJobs")
        if (-not $StrictMissingQueue) {
            $drainArgs += '--allow-missing-queue'
        }
        if ($WriteAck) {
            $drainArgs += '--write-ack'
        }
        & py @drainArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    if ($ExportPendingJson -and $ExportPendingJson.Trim().Length -gt 0) {
        if (-not (Test-Path -LiteralPath $stub)) {
            throw "Missing: $stub"
        }
        Write-Host '== Premium multilens: export-pending v0 ==' -ForegroundColor Cyan
        $expArgs = @($stub, 'export-pending', '--root', $root, '--out-json', $ExportPendingJson.Trim(), '--allow-missing-queue', '--max-items', '50')
        & py @expArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    if (-not $SkipPromotionGate) {
        if (-not (Test-Path -LiteralPath $gate)) {
            throw "Missing: $gate"
        }
        Write-Host '== Premium multilens: promotion gate v1 (S1 shadow) ==' -ForegroundColor Cyan
        if ($SkipPytest) {
            & py $gate --root $root
        }
        else {
            & py $gate --skip-pytest --root $root
        }
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}
finally {
    Pop-Location
}
