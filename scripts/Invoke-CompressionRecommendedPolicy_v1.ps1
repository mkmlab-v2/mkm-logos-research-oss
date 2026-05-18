<#
.SYNOPSIS
  M-COMP-A1 권장안 원클릭: production baseline 고정 + cmp2_min_pair 연구 지표 자동 갱신.

.PARAMETER RegisterWeekly
  성공 후 MKM_Compression_WeeklyGovernance 예약 작업 등록(없으면 덮어씀).

.PARAMETER SkipPytest
  체인 말단 pytest 생략.

.PARAMETER PromoteMinPair
  지휘관 saving-floor waiver 승인 후 cmp2_min_pair 프로덕션 shard 승격.
#>
param(
    [switch]$RegisterWeekly,
    [switch]$SkipPytest,
    [switch]$PromoteMinPair
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root

$argsPy = @("scripts/run_compression_recommended_policy_chain_v1.py")
if ($SkipPytest) { $argsPy += "--skip-pytest" }
if ($PromoteMinPair) { $argsPy += "--promote-min-pair" }

& py @argsPy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RegisterWeekly) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Register-CompressionWeeklyGovernanceTask.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[Invoke-CompressionRecommendedPolicy_v1] OK" -ForegroundColor Green
exit 0
