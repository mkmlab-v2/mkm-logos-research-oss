#Requires -Version 5.1
<#
.SYNOPSIS
  Mode B: small live trading (VPS) + fixed daily prophecy/insight chain (local Windows).

.DESCRIPTION
  Registers (or refreshes) three scheduled tasks:
  1. MKM-BTrack-DailyHypothesis-Chain  — run_btrack_daily_hypothesis_chain.ps1 (BTC research lane)
  2. MKM-Prophecy-Daily-Eval-Report   — run_daily_prophecy_eval_and_report.ps1
  3. MKM-Prophecy-Panel-24h-Alerts     — Check-ProphecyPanel24hAlerts.ps1 (after chain)

  Does NOT enable/disable VPS ENABLE_TRADING. VPS Fact-Safe 4h cron is separate (register on server).

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Register-MkmSmallLiveProphecyDailyOps_v1.ps1

.EXAMPLE
  pwsh -File scripts/Register-MkmSmallLiveProphecyDailyOps_v1.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$HypothesisAt = "08:05",
    [string]$EvalAt = "08:18",
    [string]$PanelAt = "08:42",
    [string]$DigestAt = "08:28",
    [switch]$SkipProphecyContemplationGemini,
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($Remove) {
    foreach ($tn in @(
            "MKM-BTrack-DailyHypothesis-Chain",
            "MKM-Prophecy-Daily-Eval-Report",
            "MKM-Prophecy-Panel-24h-Alerts"
        )) {
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
        Write-Host "[REMOVED] $tn" -ForegroundColor Yellow
    }
    exit 0
}

$btrackReg = @{
    WorkspaceRoot                 = $WorkspaceRoot
    At                            = $HypothesisAt
    ResearchEvaluationInstrument  = "btc"
    IncludeDawnScore              = $true
    SkipProphecyContemplationGemini = $true
}
if ($RunWhenLoggedOff) { $btrackReg["RunWhenLoggedOff"] = $true }
if (-not $SkipProphecyContemplationGemini) {
    $btrackReg.Remove("SkipProphecyContemplationGemini")
}

Write-Host "=== Mode B: register daily prophecy + panel tasks ===" -ForegroundColor Cyan

& (Join-Path $WorkspaceRoot "scripts\Register-BTrackDailyHypothesisTask.ps1") @btrackReg

$evalRunner = Join-Path $WorkspaceRoot "scripts\run_daily_prophecy_eval_and_report.ps1"
if (-not (Test-Path -LiteralPath $evalRunner)) {
    throw "Missing: $evalRunner"
}

$evalTask = "MKM-Prophecy-Daily-Eval-Report"
$btcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$evalArgLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$evalRunner`" -WorkspaceRoot `"$WorkspaceRoot`" -RecentTradingDays 7 -SkipTrinityEvolution -BtcCsvPath `"$btcCsv`" -IncludeShadowPanelEval -ShadowPanelMode walkforward_aggregate -IncludeKospiMorningBrief -IncludeCrossLensRagFusion"
$evalAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $evalArgLine -WorkingDirectory $WorkspaceRoot
$evalTrigger = New-ScheduledTaskTrigger -Daily -At $EvalAt
$evalSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$evalPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
Register-ScheduledTask -TaskName $evalTask -Action $evalAction -Trigger $evalTrigger -Settings $evalSettings -Principal $evalPrincipal `
    -Description "Daily B-track score+eval+Trinity+risk sync (no live orders)." -Force | Out-Null
Write-Host "[DONE] $evalTask at $EvalAt (LogonType=$logonType)" -ForegroundColor Green

$panelReg = @{ WorkspaceRoot = $WorkspaceRoot; At = $PanelAt; KpiBOperationalHeadline = $true }
if ($RunWhenLoggedOff) { $panelReg["RunWhenLoggedOff"] = $true }
& (Join-Path $WorkspaceRoot "scripts\Register-ProphecyPanel24hAlertsTask.ps1") @panelReg

Write-Host ""
Write-Host "Registered Mode B tasks. Verify:" -ForegroundColor Cyan
Get-ScheduledTask -TaskName @(
    "MKM-BTrack-DailyHypothesis-Chain",
    "MKM-Prophecy-Daily-Eval-Report",
    "MKM-Prophecy-Panel-24h-Alerts",
    "MKM-FactSafe-RiskProfile-Sync-4H"
) -ErrorAction SilentlyContinue | ForEach-Object {
    $i = Get-ScheduledTaskInfo -TaskName $_.TaskName
    "{0}  Next={1}  LogonType={2}" -f $_.TaskName, $i.NextRunTime, $_.Principal.LogonType
}
& (Join-Path $WorkspaceRoot "scripts\Register-TelegramMinimalDailyDigestTask.ps1") -WorkspaceRoot $WorkspaceRoot -At $DigestAt

Write-Host "Morning order (KST): $HypothesisAt hypothesis -> $EvalAt eval+brief -> $DigestAt Telegram (advanced) -> $PanelAt panel" -ForegroundColor DarkGray
Write-Host "VPS: Fact-Safe 4h cron + bitcoin-live-small-24h (small qty). See CENTRAL 「운영 모드 B」." -ForegroundColor DarkGray
