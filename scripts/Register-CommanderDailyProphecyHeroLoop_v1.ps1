#Requires -Version 5.1
<#
.SYNOPSIS
  Register full Commander daily prophecy hero loop (Task Scheduler).

.DESCRIPTION
  Morning stack (08:00–08:42) + midday general prophecy (10:00) + evening score/evolution (20:30).
  B-track [HYPO] · research_only · no live trading enable.

.EXAMPLE
  pwsh -File scripts/Register-CommanderDailyProphecyHeroLoop_v1.ps1
  pwsh -File scripts/Register-CommanderDailyProphecyHeroLoop_v1.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$HypothesisAt = "08:00",
    [string]$EvalAt = "08:18",
    [string]$RegistryAt = "08:22",
    [string]$DigestAt = "08:28",
    [string]$PanelAt = "08:42",
    [string]$MiddayGeneralAt = "10:00",
    [string]$EveningAt = "20:30",
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($Remove) {
    & (Join-Path $WorkspaceRoot "scripts\Register-MkmSmallLiveProphecyDailyOps_v1.ps1") -WorkspaceRoot $WorkspaceRoot -Remove
    & (Join-Path $WorkspaceRoot "scripts\Register-TelegramMinimalDailyDigestTask.ps1") -WorkspaceRoot $WorkspaceRoot -Remove -ErrorAction SilentlyContinue
    schtasks /Delete /TN "GeneralProphecyDailyQueueV1" /F 2>$null | Out-Null
    & (Join-Path $WorkspaceRoot "scripts\Register-CommanderEveningBriefingScoreTask.ps1") -WorkspaceRoot $WorkspaceRoot -Remove
    Write-Host "[REMOVED] Commander daily prophecy hero loop tasks" -ForegroundColor Yellow
    exit 0
}

Write-Host "=== Register Commander Daily Prophecy Hero Loop ===" -ForegroundColor Cyan

$modeB = @{
    WorkspaceRoot = $WorkspaceRoot
    HypothesisAt  = $HypothesisAt
    EvalAt        = $EvalAt
    RegistryAt    = $RegistryAt
    DigestAt      = $DigestAt
    PanelAt       = $PanelAt
}
if ($RunWhenLoggedOff) { $modeB["RunWhenLoggedOff"] = $true }
& (Join-Path $WorkspaceRoot "scripts\Register-MkmSmallLiveProphecyDailyOps_v1.ps1") @modeB

& (Join-Path $WorkspaceRoot "scripts\Register-GeneralProphecyDailyQueueTask.ps1") `
    -WorkspaceRoot $WorkspaceRoot -DailyAt $MiddayGeneralAt -HoldoutGateProfile research

& (Join-Path $WorkspaceRoot "scripts\Register-CommanderEveningBriefingScoreTask.ps1") `
    -WorkspaceRoot $WorkspaceRoot -At $EveningAt

# Enable R-IBL block in morning prophecy digest (process env for manual runs; task uses Invoke script)
$riblFlag = "MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL=1"
$envExample = Join-Path $WorkspaceRoot ".env.example"
if (Test-Path -LiteralPath $envExample) {
    $ex = Get-Content -LiteralPath $envExample -Raw
    if ($ex -notmatch "MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL") {
        Add-Content -LiteralPath $envExample -Value "`n# Hero loop: seal diverse lens predictions in 08:28 TG`n# MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL=1"
    }
}

$schedule = [ordered]@{
    schema          = "commander_daily_prophecy_hero_loop_schedule_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    hypothesis_tier = "B"
    research_only   = $true
    track_wall      = "no_track_a_live_auto_merge"
    kst_order       = @(
        @{ at = $HypothesisAt; task = "MKM-BTrack-DailyHypothesis-Chain"; role = "diverse_hypothesis_gen" }
        @{ at = $EvalAt; task = "MKM-Prophecy-Daily-Eval-Report"; role = "score_eval_brief" }
        @{ at = $RegistryAt; task = "MKM-Research-Morning-Prediction-Registry"; role = "ribl_seal" }
        @{ at = $DigestAt; task = "MKM-Telegram-Minimal-Daily-Digest"; role = "morning_prophecy_tg" }
        @{ at = $PanelAt; task = "MKM-Prophecy-Panel-24h-Alerts"; role = "panel_alerts" }
        @{ at = $MiddayGeneralAt; task = "GeneralProphecyDailyQueueV1"; role = "midday_general_prophecy" }
        @{ at = $EveningAt; task = "MKM-Commander-Evening-Briefing-Score"; role = "evening_score_evolution_tg" }
    )
    manual_one_shot = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CommanderDailyProphecyHeroLoop_v1.ps1 -Phase All"
    hero_evolution  = "run_commander_briefing_evolution_v1.py (dry-run proposals from evening scores)"
    evening_a_code_ops = [ordered]@{
        governor = "Run-ACodeGovernorResearchBundle_v1.ps1 -SkipMultiday"
        operator_lane = "Run-ACodeOperatorAssistLaneLightRoutine_v1.ps1"
        persona = "OperatorAssistLaneLight"
        research_only = $true
        non_gating = $true
    }
}

$outJson = Join-Path $WorkspaceRoot "reports\commander_daily_prophecy_hero_loop_schedule_latest.json"
$schedule | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outJson -Encoding utf8

Write-Host ""
Write-Host "KST daily rhythm:" -ForegroundColor Green
Write-Host "  $HypothesisAt  가설·렌즈 예측 생성 (B-track)"
Write-Host "  $EvalAt  적중·브리프 갱신"
Write-Host "  $RegistryAt  R-IBL 봉인 (저녁 채점용)"
Write-Host "  $DigestAt  Telegram 아침 prophecy (+ R-IBL if .env flag)"
Write-Host "  $MiddayGeneralAt  일반예언·다도메인 큐 (남는 배치)"
Write-Host "  $EveningAt  정답 채점 + briefing evolution + evening_review TG"
Write-Host ""
Write-Host "Wrote $outJson" -ForegroundColor DarkGray
Write-Host "Verify: pwsh -File scripts/Verify-CommanderDailyProphecyHeroLoopReadiness_v1.ps1" -ForegroundColor DarkGray
