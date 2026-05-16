#Requires -Version 5.1
<#
.SYNOPSIS
  권장 GPU 인접 스모크 번들: Control-Integrity LoRA(oracle 끝단) + Pack 0-B 명리 결정론 LoRA CI pytest 슬라이스.

.DESCRIPTION
  1) Run-MkmControlIntegrityTrainInferEval.ps1 -OracleInference — prep·train dry-run·oracle 추론·eval (실 가중치 학습 아님).
  2) Pack 0-B 관련 pytest 5종(CONSTITUTION §1.2.1·§6 Pack 0-B 행과 동일 선상).

  Chronos-Forward KOSPI 전체는 장시간이므로 본 번들에 포함하지 않음. GPU 여유 시 별도:
    pwsh -File scripts/run_chronos_forward_kospi_baseline.ps1 -Mode both -Detached

.PARAMETER SkipControlIntegrity
  2단계(Pack 0-B pytest)만 실행.

.PARAMETER SkipPack0B
  1단계(Control-Integrity)만 실행.
#>
param(
    [switch]$SkipControlIntegrity,
    [switch]$SkipPack0B
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $SkipControlIntegrity) {
    Write-Host "[bundle] Control-Integrity oracle chain..." -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "Run-MkmControlIntegrityTrainInferEval.ps1") -OracleInference
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipPack0B) {
    Write-Host "[bundle] Pack 0-B pytest slice..." -ForegroundColor Cyan
    $tests = @(
        "tests/test_myeongri_deterministic_lora_golden_set_schema_v1.py",
        "tests/test_build_myeongri_deterministic_lora_golden_bulk_v1.py",
        "tests/test_eval_myeongri_deterministic_lora_golden_fit_v1.py",
        "tests/test_myeongri_deterministic_lora_pack_copy_guardrails_v1.py",
        "tests/test_mkm_promotion_gate_evidence_bundle_v1.py"
    )
    py -m pytest @tests -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: Run-MkmGpuRecommendedBundle_v1 (Control-Integrity oracle + Pack 0-B pytest)" -ForegroundColor Green
Write-Host "Optional long GPU: scripts/run_chronos_forward_kospi_baseline.ps1 -Mode both -Detached" -ForegroundColor DarkGray
exit 0
