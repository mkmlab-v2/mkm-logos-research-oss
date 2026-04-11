<#
.SYNOPSIS
  로컬 Fact-Lock 번들 — GitHub Actions `dual-regime-integrity.yml` 핵심 검증과 동일 순서(Windows).

.DESCRIPTION
  1. `py scripts/integrity_guard.py` (CI 첫 단계)
  2. `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`
     — dual-regime 스모크 + multilens marginal(V1) 후 워크스페이스 루트 Fact-Lock(Thin V2·시장 어댑터 등 명시 목록)

  테스트 파일 목록 이중 관리를 피하기 위해 2단계는 기존 PS1에 위임합니다.

.PARAMETER SkipIntegrityGuard
  `integrity_guard.py` 생략(빠른 확인용). CI와 완전 동치가 아님.

.PARAMETER IncludeP1AB
  Fact-Lock 핵심 검증 후 `scripts/run_p1_ab_bundle.ps1`를 추가 실행한다.

.PARAMETER IncludeCodebookFactSafe
  압축 복원 브리지 이후 `scripts/run_codebook_factsafe_bundle.ps1 -IncludeRecoveredReadiness`를 실행한다(코드북·복구 레일 스모크).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipIntegrityGuard

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipIntegrityGuard -IncludeP1AB

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeCodebookFactSafe

.NOTES
  SSOT 순서: `.github/workflows/dual-regime-integrity.yml`
  pytest·`py` 규칙: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`
#>
param(
    [switch]$SkipIntegrityGuard,
    [switch]$IncludeP1AB,
    [switch]$SkipCompressionRestoreBridge,
    [switch]$IncludeCodebookFactSafe
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$prophecyBundle = Join-Path $workspaceRoot 'projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1'
$p1AbBundle = Join-Path $workspaceRoot 'scripts\run_p1_ab_bundle.ps1'
$insightScoreboardScript = Join-Path $workspaceRoot 'scripts\build_insight_effectiveness_scoreboard.py'
$trackbQuaternionGateScript = Join-Path $workspaceRoot 'scripts\report_trackb_quaternion_two_stage_gate.py'
$compressionRestoreBridgeScript = Join-Path $workspaceRoot 'scripts\run_agent_compression_restore_bridge.ps1'
$codebookFactSafeBundleScript = Join-Path $workspaceRoot 'scripts\run_codebook_factsafe_bundle.ps1'

if (-not (Test-Path -LiteralPath $prophecyBundle)) {
    throw "Bundle script not found: $prophecyBundle"
}

Set-Location -LiteralPath $workspaceRoot

if (-not $SkipIntegrityGuard) {
    Write-Host '== Fact-Lock: integrity_guard.py ==' -ForegroundColor Cyan
    & py (Join-Path $workspaceRoot 'scripts\integrity_guard.py')
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host '== Fact-Lock: run_prophecy_alignment_pytest.ps1 ==' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $prophecyBundle
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if ($IncludeP1AB) {
    if (-not (Test-Path -LiteralPath $p1AbBundle)) {
        throw "P1 A/B bundle script not found: $p1AbBundle"
    }
    Write-Host '== Fact-Lock: run_p1_ab_bundle.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $p1AbBundle
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $insightScoreboardScript)) {
    throw "Insight scoreboard script not found: $insightScoreboardScript"
}
Write-Host '== Fact-Lock: build_insight_effectiveness_scoreboard.py ==' -ForegroundColor Cyan
& py $insightScoreboardScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackbQuaternionGateScript)) {
    throw "Track B quaternion two-stage gate script not found: $trackbQuaternionGateScript"
}
Write-Host '== Fact-Lock: report_trackb_quaternion_two_stage_gate.py ==' -ForegroundColor Cyan
& py $trackbQuaternionGateScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipCompressionRestoreBridge) {
    if (-not (Test-Path -LiteralPath $compressionRestoreBridgeScript)) {
        throw "Compression/restore bridge script not found: $compressionRestoreBridgeScript"
    }
    Write-Host '== Fact-Lock: run_agent_compression_restore_bridge.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $compressionRestoreBridgeScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($IncludeCodebookFactSafe) {
    if (-not (Test-Path -LiteralPath $codebookFactSafeBundleScript)) {
        throw "Codebook Fact-Safe bundle script not found: $codebookFactSafeBundleScript"
    }
    Write-Host '== Fact-Lock: run_codebook_factsafe_bundle.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $codebookFactSafeBundleScript -IncludeRecoveredReadiness
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

exit 0
