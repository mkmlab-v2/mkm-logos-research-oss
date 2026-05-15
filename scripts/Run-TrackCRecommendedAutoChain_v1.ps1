# Track C / MKM 권장 자동 루틴 (v1)
# 기본: n8n 생략(로컬 n8n 인프라 제거 2026-05-15). -IncludeN8nCheck 시에만 레거시 일일 점검.
# MVP+B2B 아티팩트 갱신 -> copy guard -> 오케스트레이터 번들·noop 스모크
# Usage (repo root):  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-TrackCRecommendedAutoChain_v1.ps1

[CmdletBinding()]
param(
    [switch]$IncludeN8nCheck,
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

if ($SkipN8nCheck -and $IncludeN8nCheck) {
    throw "Use only one of -IncludeN8nCheck or -SkipN8nCheck (legacy alias)."
}
if ($IncludeN8nCheck) {
    Write-Step "1) Macro risk n8n daily check (legacy; continues on non-zero exit)"
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
    $legacyNote = if ($SkipN8nCheck) { " (-SkipN8nCheck is default since 2026-05-15)" } else { "" }
    Write-Host "Skip: n8n daily check (default; use -IncludeN8nCheck for legacy)$legacyNote" -ForegroundColor DarkGray
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

Write-Step "4) Track C morning briefing (json + ko/en markdown)"
$morningBrief = Join-Path $PSScriptRoot "build_trackc_macro_risk_morning_briefing_v1.py"
if (Test-Path -LiteralPath $morningBrief) {
    & py $morningBrief
    if ($LASTEXITCODE -ne 0) { $failed = $true; throw "morning briefing build failed with exit $LASTEXITCODE" }
}
else {
    Write-Warning "Missing: $morningBrief"
}

if (-not $SkipOrchestrator) {
    Write-Step "5) verify_mkm_orchestrator_bundle_v1"
    $v = Join-Path $PSScriptRoot "verify_mkm_orchestrator_bundle_v1.py"
    if (Test-Path -LiteralPath $v) {
        & py $v
        if ($LASTEXITCODE -ne 0) { Write-Warning "orchestrator bundle verify exit $LASTEXITCODE" }
    }
    else {
        Write-Warning "Missing: $v"
    }

    Write-Step "6) mkm_orchestrator_noop_smoke_v1"
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
