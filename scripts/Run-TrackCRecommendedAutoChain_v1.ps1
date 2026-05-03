# Track C / MKM 권장 자동 루틴 (v1)
# n8n 매크로 점검(실패해도 계속) -> MVP+B2B 아티팩트 갱신 -> copy guard -> 오케스트레이터 번들·noop 스모크
# Usage (repo root):  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-TrackCRecommendedAutoChain_v1.ps1

[CmdletBinding()]
param(
    [switch]$SkipN8nCheck,
    [switch]$SkipOrchestrator
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

$failed = $false

if (-not $SkipN8nCheck) {
    Write-Step "1) Macro risk n8n daily check (continues on non-zero exit)"
    $n8nScript = Join-Path $PSScriptRoot "Run-MacroRiskN8nDailyCheck.ps1"
    if (-not (Test-Path -LiteralPath $n8nScript)) {
        Write-Warning "Missing: $n8nScript"
    }
    else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $n8nScript -SkipFailureAlert
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Run-MacroRiskN8nDailyCheck.ps1 exit code: $LASTEXITCODE (MVP will still reflect latest JSON on disk)"
        }
    }
}
else {
    Write-Host "Skip: n8n daily check (-SkipN8nCheck)" -ForegroundColor DarkGray
}

Write-Step "2) build_track_c_macro_risk_mvp_filled_v1 (MVP §2 + B2B one-pager)"
& py (Join-Path $PSScriptRoot "build_track_c_macro_risk_mvp_filled_v1.py")
if ($LASTEXITCODE -ne 0) { $failed = $true; throw "MVP build failed with exit $LASTEXITCODE" }

Write-Step "3) Track C copy guard (MVP + B2B)"
$mvp = Join-Path $repoRoot "docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md"
$b2b = Join-Path $repoRoot "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md"
& py (Join-Path $PSScriptRoot "check_track_c_copy_guard_v1.py") $mvp
if ($LASTEXITCODE -ne 0) { $failed = $true; throw "copy guard failed: MVP" }
& py (Join-Path $PSScriptRoot "check_track_c_copy_guard_v1.py") $b2b
if ($LASTEXITCODE -ne 0) { $failed = $true; throw "copy guard failed: B2B" }

if (-not $SkipOrchestrator) {
    Write-Step "4) verify_mkm_orchestrator_bundle_v1"
    $v = Join-Path $PSScriptRoot "verify_mkm_orchestrator_bundle_v1.py"
    if (Test-Path -LiteralPath $v) {
        & py $v
        if ($LASTEXITCODE -ne 0) { Write-Warning "orchestrator bundle verify exit $LASTEXITCODE" }
    }
    else {
        Write-Warning "Missing: $v"
    }

    Write-Step "5) mkm_orchestrator_noop_smoke_v1"
    $n = Join-Path $PSScriptRoot "mkm_orchestrator_noop_smoke_v1.py"
    if (Test-Path -LiteralPath $n) {
        & py $n
        if ($LASTEXITCODE -ne 0) { Write-Warning "noop smoke exit $LASTEXITCODE" }
    }
}
else {
    Write-Host "Skip: orchestrator (-SkipOrchestrator)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Track C recommended auto chain: DONE" -ForegroundColor Green
exit 0
