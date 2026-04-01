param(
    [ValidateSet("weekly_lite", "monthly_full", "skip")]
    [string]$Phase1Mode = "weekly_lite",
    [switch]$RunPhase2,
    [string]$NightWatchmanDecision = "PASS",
    [switch]$ConfirmLiveAlert,
    [int]$CdnRounds = 3,
    [int]$CdnRoundSleepSec = 20,
    [switch]$StrictGateway
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
$artifactDir = Join-Path $workspace "docs\final\artifacts"
$sopLog = Join-Path $artifactDir "fused_quant_pixel_sop_latest.log"

function Write-SopLog([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $sopLog -Value $line
    Write-Host $message
}

function Assert-ExitCode([string]$stepName) {
    if ($LASTEXITCODE -ne 0) {
        throw "$stepName failed with exit code $LASTEXITCODE"
    }
}

Set-Location $workspace
Write-SopLog "Fused SOP start mode=$Phase1Mode phase2=$RunPhase2 decision=$NightWatchmanDecision confirmLive=$ConfirmLiveAlert"

# -------------------------------
# Phase 0: Public Event Gateway health
# -------------------------------
Write-SopLog "[Phase0] ensure public event gateway healthy"
$gatewayArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\ensure_public_event_gateway.ps1"
)
if ($StrictGateway) {
    $gatewayArgs += "-Strict"
    Write-SopLog "[Phase0] gateway mode=STRICT"
}
& powershell @gatewayArgs
Assert-ExitCode "ensure_public_event_gateway.ps1"

# -------------------------------
# Phase 0.1: Public metrics task status
# -------------------------------
$publicMetricsTask = "Bitcoin-Public-Metrics-Snapshot-1min"
Write-SopLog "[Phase0.1] check public metrics task status ($publicMetricsTask)"
schtasks /Query /TN $publicMetricsTask /FO LIST
if ($LASTEXITCODE -ne 0) {
    Write-SopLog "[Phase0.1] WARN: public metrics task not found: $publicMetricsTask"
} else {
    Write-SopLog "[Phase0.1] public metrics task query OK"
}

# -------------------------------
# Phase 1: Quant / Risk
# -------------------------------
if ($Phase1Mode -eq "weekly_lite") {
    Write-SopLog "[Phase1] weekly_lite: run KPI snapshot + BTC primary daily wrapper"
    & powershell -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_kpi_snapshot.ps1"
    Assert-ExitCode "run_kpi_snapshot.ps1"

    & powershell -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_waiting_queue_btc_binance_daily.ps1"
    Assert-ExitCode "run_waiting_queue_btc_binance_daily.ps1"
} elseif ($Phase1Mode -eq "monthly_full") {
    Write-SopLog "[Phase1] monthly_full: run full waiting queue monthly check"
    & powershell -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_waiting_queue_monthly_check.ps1"
    Assert-ExitCode "run_waiting_queue_monthly_check.ps1"
} else {
    Write-SopLog "[Phase1] skipped by mode=skip"
}

# -------------------------------
# Phase 2: Pixel / Night Watchman
# -------------------------------
if ($RunPhase2) {
    Write-SopLog "[Phase2] build public map from pilot map + PIXEL_BATTALION_BASE_URL"
    py "C:\workspace\scripts\build_pixel_battalion_public_map.py"
    Assert-ExitCode "build_pixel_battalion_public_map.py"

    $publicMapPath = "C:\workspace\docs\final\artifacts\pixel_battalion_character_map_public_latest.json"
    if (-not (Test-Path -LiteralPath $publicMapPath)) {
        throw "public character map missing: $publicMapPath"
    }

    $publicMap = Get-Content -LiteralPath $publicMapPath -Raw -Encoding utf8 | ConvertFrom-Json
    $baseUrlEnv = [string]$env:PIXEL_BATTALION_BASE_URL
    $baseUrlMap = [string]$publicMap.public_base_url
    if (-not [string]::IsNullOrWhiteSpace($baseUrlEnv) -and ($baseUrlMap -ne $baseUrlEnv.TrimEnd('/'))) {
        throw "PIXEL_BATTALION_BASE_URL mismatch: env='$baseUrlEnv' map='$baseUrlMap'"
    }

    Write-SopLog "[Phase2] CDN smoke verify rounds=$CdnRounds sleep=${CdnRoundSleepSec}s"
    py "C:\workspace\scripts\verify_pixel_battalion_cdn_urls.py" --rounds $CdnRounds --round-sleep $CdnRoundSleepSec
    Assert-ExitCode "verify_pixel_battalion_cdn_urls.py"

    Write-SopLog "[Phase2] Night Watchman dry-run first"
    py "C:\workspace\scripts\send_night_watchman_character_alert.py" --decision $NightWatchmanDecision --dry-run
    Assert-ExitCode "send_night_watchman_character_alert.py --dry-run"

    if ($ConfirmLiveAlert) {
        Write-SopLog "[Phase2] Night Watchman live alert"
        py "C:\workspace\scripts\send_night_watchman_character_alert.py" --decision $NightWatchmanDecision
        Assert-ExitCode "send_night_watchman_character_alert.py"
    } else {
        Write-SopLog "[Phase2] live alert skipped (use -ConfirmLiveAlert to send)"
    }
} else {
    Write-SopLog "[Phase2] skipped by flag"
}

Write-SopLog "Fused SOP completed successfully."
