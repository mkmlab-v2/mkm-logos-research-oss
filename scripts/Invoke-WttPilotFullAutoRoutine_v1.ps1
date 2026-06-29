# WTT pilot full auto: enrollment + operator panel + deck + solo drill + stub + sales (SEND HOLD).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipStubIntake,
    [switch]$SkipEnrollmentIntake,
    [switch]$SkipOperatorPanel,
    [switch]$SkipDeckRefresh,
    [switch]$SkipDropWatch,
    [switch]$IncludePremiumCsClosure,
    [switch]$SkipCompressionIntakeOnClosure,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$reportOut = Join-Path $WorkspaceRoot "reports/wtt_pilot_full_auto_routine_v1_latest.json"

Write-Host "=== WTT Pilot Full Auto Routine ===" -ForegroundColor Cyan
Write-Host "lanes: enrollment stub + operator_panel 30/30 + stress deck | SEND HOLD | not customer SEND" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] enrollment -> operator panel -> deck -> drill -> stub -> tune -> sales -> dropwatch -> report" -ForegroundColor DarkGray
    exit 0
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Invoke-Step "1/8 enrollment pack + n30 gate" {
    $enrollArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/Invoke-WttPilotEnrollmentRoutine_v1.ps1")
    if ($SkipEnrollmentIntake) { $enrollArgs += "-SkipIntakeRehearsal" }
    & powershell @enrollArgs
}

if (-not $SkipOperatorPanel) {
    Invoke-Step "2/8 operator panel (SkipBuild — curated corpus SSOT)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttOperatorPanelRoutine_v1.ps1 -SkipBuild
    }
} else {
    Write-Host "=== 2/8 operator panel skipped ===" -ForegroundColor DarkGray
}

Invoke-Step "3/8 solo internal drill" {
    & py scripts/check_wtt_customer_masked_intake_drill_v1.py --solo-internal-rehearsal
}

if (-not $SkipStubIntake) {
    $stubJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"
    Invoke-Step "4/8 stub intake rehearsal (solo internal)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 `
            -TenantId wtt-solo-internal-v1 `
            -SessionJsonl $stubJsonl `
            -AllowStubTemplate
    }
} else {
    Write-Host "=== 4/8 stub intake skipped ===" -ForegroundColor DarkGray
}

Invoke-Step "5/8 spicy policy tune (labeled corpus)" {
    $spicyJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
    & py scripts/tune_wtt_dialog_risk_policy_from_corpus_v1.py --jsonl $spicyJsonl --round 2
}

if (-not $SkipDeckRefresh) {
    Invoke-Step "6/8 deck refresh last (restore spicy 25 FSM SSOT + stress MD)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttOperatorPanelDeckRefresh_v1.ps1
    }
} else {
    Write-Host "=== 6/8 deck refresh skipped ===" -ForegroundColor DarkGray
}

Invoke-Step "7/8 sales sheet render" {
    & py scripts/build_governed_ai_customization_sales_sheet_render_v1.py
}

if (-not $SkipDropWatch) {
    Invoke-Step "8/10 intake drop watch (poll once)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPilotIntakeDropWatch_v1.ps1
    }
} else {
    Write-Host "=== 8/10 drop watch skipped ===" -ForegroundColor DarkGray
}

Invoke-Step "9/10 customer intake readiness + cross-lane status" {
    & py scripts/check_wtt_customer_intake_readiness_v1.py
    & py scripts/build_wtt_premium_cs_cross_lane_status_v1.py
}

if ($IncludePremiumCsClosure) {
    Invoke-Step "10/10 premium CS closure (deck + bridge)" {
        $closureArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/Invoke-WttPremiumCsClosure_v1.ps1")
        if ($SkipCompressionIntakeOnClosure) { $closureArgs += "-SkipCompressionIntake" }
        & powershell @closureArgs
    }
} else {
    Write-Host "=== 10/10 premium CS closure skipped (use -IncludePremiumCsClosure) ===" -ForegroundColor DarkGray
}

& py scripts/build_wtt_pilot_full_auto_routine_report_v1.py --out $reportOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK full auto report: $reportOut" -ForegroundColor Green
Write-Host "OK stress deck: reports/wtt_stress_certified_deck_v1_latest.md" -ForegroundColor Green
Write-Host "OK operator gate: reports/wtt_operator_panel_gate_v1_latest.json (30/30, not SEND-eligible)" -ForegroundColor Green
exit 0
