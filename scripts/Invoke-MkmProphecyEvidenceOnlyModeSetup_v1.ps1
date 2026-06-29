#Requires -Version 5.1
<#
.SYNOPSIS
  Disable live trading (local + VPS) and register prophecy/insight promotion-evidence dev stack.

.DESCRIPTION
  - Local: .env observe-only flags, emergency stop, Fact-Safe sync, GO/NO_GO rebuild
  - VPS: ENABLE_TRADING=false, pm2 stop bitcoin-live-small-24h, risk/go_nogo sync
  - Tasks: Commander daily prophecy hero loop + weekly B-track learning
  - Artifact: reports/mkm_prophecy_evidence_only_mode_latest.json

  No orders placed. research_only / B-track promotion evidence lane only.

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmProphecyEvidenceOnlyModeSetup_v1.ps1
.EXAMPLE
  pwsh -File scripts/Invoke-MkmProphecyEvidenceOnlyModeSetup_v1.ps1 -SkipVps
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$Pm2App = "bitcoin-live-small-24h",
    [switch]$SkipVps,
    [switch]$SkipTaskRegister
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

function Upsert-DotEnvKey([string]$path, [string]$key, [string]$value) {
    $lines = [System.Collections.Generic.List[string]]@()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]]@(Get-Content -LiteralPath $path -Encoding UTF8)
    }
    $pattern = "^\s*$([regex]::Escape($key))\s*="
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) { $idx = $i; break }
    }
    $newLine = "$key=$value"
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
    Set-Content -LiteralPath $path -Value ($lines -join "`n") -Encoding UTF8
}

Write-Host "=== MKM prophecy-evidence-only mode setup ===" -ForegroundColor Cyan

$envPath = Join-Path $WorkspaceRoot ".env"
foreach ($kv in @(
        @{ Key = "ENABLE_TRADING"; Value = "false" }
        @{ Key = "ALLOW_LIVE_TRADING_ON_LOCAL"; Value = "0" }
        @{ Key = "LOCAL_DAEMON_HOLD_SHADOW"; Value = "1" }
        @{ Key = "MKM_OPERATION_MODE"; Value = "prophecy_evidence_only" }
    )) {
    Upsert-DotEnvKey -path $envPath -key $kv.Key -value $kv.Value
    Write-Host "[local .env] $($kv.Key)=$($kv.Value)" -ForegroundColor DarkGray
}

$emergency = Join-Path $WorkspaceRoot "scripts\_emergency_stop_local_live_trading_v1.ps1"
if (-not (Test-Path -LiteralPath $emergency)) { throw "Missing: $emergency" }
& $emergency
if ($LASTEXITCODE -ne 0) { throw "_emergency_stop_local_live_trading exit $LASTEXITCODE" }

$vpsResult = [ordered]@{
    attempted = (-not $SkipVps)
    live_disabled = $false
    pm2_stopped = $false
    go_no_go = $null
    error = $null
}

if (-not $SkipVps) {
    Write-Host "==> VPS: disable live trading + stop $Pm2App" -ForegroundColor Cyan
    $vpsCmd = @"
cd $DestinyRoot && touch .env && (grep -v '^ENABLE_TRADING=' .env > .env.tmp || true) && echo ENABLE_TRADING=false >> .env.tmp && (grep -v '^ALLOW_LIVE_TRADING_ON_LOCAL=' .env.tmp > .env.tmp2 || true) && mv .env.tmp2 .env.tmp && echo ALLOW_LIVE_TRADING_ON_LOCAL=0 >> .env.tmp && mv .env.tmp .env && pm2 stop $Pm2App 2>/dev/null || true && python3 scripts/sync_fact_safe_risk_profile.py --repo-source --allow-metadata-downgrade && python3 scripts/build_trading_go_nogo_status_v1.py --exit-zero-on-no-go && python3 -c "import json; d=json.load(open('docs/final/artifacts/trading_go_no_go_latest.json')); print('VPS_GO_NO_GO', d.get('go_no_go'), 'risk', d.get('risk_mode'))"
"@
    try {
        $vpsOut = ssh $VpsHost $vpsCmd 2>&1 | Out-String
        Write-Host $vpsOut
        $vpsResult.live_disabled = $true
        if ($vpsOut -match "VPS_GO_NO_GO\s+(\S+)") { $vpsResult.go_no_go = $Matches[1] }
        $pm2List = ssh $VpsHost "pm2 jlist" 2>&1 | Out-String
        if ($pm2List -match "`"$Pm2App`".*?`"status`":\s*`"stopped`"") {
            $vpsResult.pm2_stopped = $true
        }
    } catch {
        $vpsResult.error = $_.Exception.Message
        Write-Host "WARN: VPS step failed: $($vpsResult.error)" -ForegroundColor Yellow
    }
}

if (-not $SkipTaskRegister) {
    Write-Host "==> Register daily prophecy hero loop + weekly B-track learning" -ForegroundColor Cyan
    & (Join-Path $WorkspaceRoot "scripts\Register-CommanderDailyProphecyHeroLoop_v1.ps1") -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "Register-CommanderDailyProphecyHeroLoop exit $LASTEXITCODE" }
    & (Join-Path $WorkspaceRoot "scripts\Register-BtrackRecommendedEvalAutoSweepWeeklyTask.ps1") -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "Register-BtrackRecommendedEvalAutoSweepWeekly exit $LASTEXITCODE" }
    & (Join-Path $WorkspaceRoot "scripts\Register-MkmBtrackProphecyWeeklyLearningTask_v1.ps1") -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "Register-MkmBtrackProphecyWeeklyLearning exit $LASTEXITCODE" }
}

Write-Host "==> Local Fact-Safe + GO/NO_GO + phase0 observe-only" -ForegroundColor Cyan
& (Join-Path $WorkspaceRoot "scripts\Run-FactSafeRiskProfileSyncChain_v1.ps1") -WorkspaceRoot $WorkspaceRoot -ExitZeroOnNoGo
if ($LASTEXITCODE -ne 0) { throw "Run-FactSafeRiskProfileSyncChain exit $LASTEXITCODE" }

py (Join-Path $WorkspaceRoot "scripts\build_btrack_phase0_observe_only_status_v1.py")
if ($LASTEXITCODE -ne 0) { throw "build_btrack_phase0_observe_only_status exit $LASTEXITCODE" }

$obsLoop = Join-Path $WorkspaceRoot "scripts\Run-TradingObservationLoop.ps1"
if (Test-Path -LiteralPath $obsLoop) {
    & $obsLoop
    if ($LASTEXITCODE -ne 0) { throw "Run-TradingObservationLoop exit $LASTEXITCODE" }
}

$goPath = Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json"
$phase0Path = Join-Path $WorkspaceRoot "reports\btrack_phase0_observe_only_readiness_v1_latest.json"
$go = $null
$phase0 = $null
if (Test-Path -LiteralPath $goPath) { $go = Get-Content -LiteralPath $goPath -Raw | ConvertFrom-Json }
if (Test-Path -LiteralPath $phase0Path) { $phase0 = Get-Content -LiteralPath $phase0Path -Raw | ConvertFrom-Json }

$artifact = [ordered]@{
    schema            = "mkm_prophecy_evidence_only_mode_v1"
    generated_at_utc  = (Get-Date).ToUniversalTime().ToString("o")
    research_only     = $true
    hypothesis_tag    = "[HYPO]"
    operation_mode    = "prophecy_evidence_only"
    live_trading      = [ordered]@{
        local_enable_trading = "false"
        vps_pm2_app          = $Pm2App
        vps                  = $vpsResult
    }
    promotion_lane    = [ordered]@{
        daily_tasks = @(
            "MKM-BTrack-DailyHypothesis-Chain"
            "MKM-Prophecy-Daily-Eval-Report"
            "MKM-Research-Morning-Prediction-Registry"
            "MKM-Telegram-Minimal-Daily-Digest"
            "MKM-Prophecy-Panel-24h-Alerts"
            "GeneralProphecyDailyQueueV1"
            "MKM-Commander-Evening-Briefing-Score"
        )
        weekly_tasks = @(
            "MKM-BTrack-RecommendedEval-AutoSweep-Weekly"
            "MKM-BTrack-Prophecy-Weekly-Learning"
        )
        track_a_auto_promote = $false
        live_order_auto_merge = $false
    }
    local_go_no_go      = if ($go) { $go.go_no_go } else { $null }
    local_risk_mode     = if ($go) { $go.risk_mode } else { $null }
    phase0_ready        = if ($phase0) { $phase0.phase0_observe_only_ready } else { $null }
    reproduce_command   = "pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmProphecyEvidenceOnlyModeSetup_v1.ps1"
    manual_one_shot     = "pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CommanderDailyProphecyHeroLoop_v1.ps1 -Phase All"
}

$outJson = Join-Path $WorkspaceRoot "reports\mkm_prophecy_evidence_only_mode_latest.json"
$artifact | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outJson -Encoding utf8

$verify = Join-Path $WorkspaceRoot "scripts\Verify-CommanderDailyProphecyHeroLoopReadiness_v1.ps1"
if (Test-Path -LiteralPath $verify) {
    & $verify -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN: Verify-CommanderDailyProphecyHeroLoopReadiness exit $LASTEXITCODE" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "[OK] prophecy-evidence-only mode" -ForegroundColor Green
Write-Host "  artifact: $outJson"
Write-Host "  local go_no_go: $($artifact.local_go_no_go) risk: $($artifact.local_risk_mode)"
Write-Host "  phase0_observe_only_ready: $($artifact.phase0_ready)"
exit 0
