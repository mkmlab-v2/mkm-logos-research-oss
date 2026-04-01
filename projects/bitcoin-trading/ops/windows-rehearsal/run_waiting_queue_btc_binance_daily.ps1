param(
    [switch]$StrictCloseReturn
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
$runner = Join-Path $workspace "scripts\run_waiting_queue_monthly_check.ps1"
$taskLog = Join-Path $workspace "docs\final\artifacts\waiting_queue_btc_binance_daily_task.log"
$waitingLogPath = Join-Path $workspace "docs\final\artifacts\waiting_queue_monthly_check_log.jsonl"
$distributionPath = Join-Path $workspace "docs\final\artifacts\trinity_scoring_distribution_latest.json"

function Write-TaskLog([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $taskLog -Value $line
}

function Send-CriticalAlert([string]$title, [string]$detail) {
    $payloadText = "[FATAL] $title`n$detail"
    $slackWebhook = [string]$env:FACT_SAFE_FATAL_SLACK_WEBHOOK
    if (-not [string]::IsNullOrWhiteSpace($slackWebhook)) {
        try {
            Invoke-RestMethod -Method Post -Uri $slackWebhook -ContentType "application/json" -Body (@{ text = $payloadText } | ConvertTo-Json -Compress) | Out-Null
        } catch {
            Write-TaskLog "WARN fatal_alert slack_send_failed"
        }
    }

    $bot = [string]$env:TELEGRAM_BOT_TOKEN
    $chat = [string]$env:TELEGRAM_CHAT_ID
    if ((-not [string]::IsNullOrWhiteSpace($bot)) -and (-not [string]::IsNullOrWhiteSpace($chat))) {
        try {
            $tgUrl = "https://api.telegram.org/bot$bot/sendMessage"
            Invoke-RestMethod -Method Post -Uri $tgUrl -ContentType "application/json" -Body (@{ chat_id = $chat; text = $payloadText } | ConvertTo-Json -Compress) | Out-Null
        } catch {
            Write-TaskLog "WARN fatal_alert telegram_send_failed"
        }
    }
}

function Get-PendingCloseStreak {
    param(
        [string]$LogPath,
        [string]$Metric = "BTC_BINANCE_D1_RETURN_PCT"
    )
    if (-not (Test-Path $LogPath)) {
        return 0
    }
    $rows = Get-Content -LiteralPath $LogPath -Encoding utf8
    if (-not $rows) {
        return 0
    }
    $streak = 0
    for ($i = $rows.Count - 1; $i -ge 0; $i--) {
        $line = $rows[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $obj = $line | ConvertFrom-Json
        } catch {
            continue
        }
        if ([string]$obj.hypothesis_metric -ne $Metric) { continue }
        $decision = [string]$obj.post_close_eval_decision
        if ($decision -eq "PENDING_CLOSE") {
            $streak += 1
            continue
        }
        break
    }
    return $streak
}

function Get-PendingCloseRateD5 {
    param([string]$DistributionPath)
    if (-not (Test-Path $DistributionPath)) {
        return $null
    }
    try {
        $obj = Get-Content -LiteralPath $DistributionPath -Raw -Encoding utf8 | ConvertFrom-Json
        return [double]$obj.windows.d5.pending_close_rate
    } catch {
        return $null
    }
}

function Get-BtcBinanceD1ReturnPct {
    param([int]$TimeoutSec = 8)
    $urls = @(
        "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT",
        "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    )
    foreach ($url in $urls) {
        try {
            $resp = Invoke-RestMethod -Method Get -Uri $url -TimeoutSec $TimeoutSec
            $pct = $resp.priceChangePercent
            if ($null -eq $pct) {
                continue
            }
            $value = [double]$pct
            return [math]::Round($value, 8)
        } catch {
            continue
        }
    }
    return $null
}

function Get-BtcCoingeckoD1ReturnPct {
    param([int]$TimeoutSec = 8)
    $url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
    try {
        $resp = Invoke-RestMethod -Method Get -Uri $url -TimeoutSec $TimeoutSec
        $pct = $resp.bitcoin.usd_24h_change
        if ($null -eq $pct) {
            return $null
        }
        return [math]::Round([double]$pct, 8)
    } catch {
        return $null
    }
}

function Get-DailyCloseInputPath {
    $raw = [string]$env:DAILY_CLOSE_INPUT_JSON_PATH
    if (-not [string]::IsNullOrWhiteSpace($raw)) {
        return $raw
    }
    return (Join-Path $workspace "docs\final\artifacts\daily_market_close_inputs_latest.json")
}

function Update-DailyCloseInputFromEnv {
    $path = Get-DailyCloseInputPath
    $current = @{}
    if (Test-Path -LiteralPath $path) {
        try {
            $obj = Get-Content -LiteralPath $path -Raw -Encoding utf8 | ConvertFrom-Json
            if ($null -ne $obj) {
                foreach ($p in $obj.PSObject.Properties) {
                    $current[$p.Name] = $p.Value
                }
            }
        } catch {
        }
    }

    $updated = $false
    $envBtc = [string]$env:DAILY_BTC_BINANCE_D1_RETURN_PCT
    if (-not [string]::IsNullOrWhiteSpace($envBtc)) {
        $current["btc_binance_d1_return_pct"] = [math]::Round([double]$envBtc, 8)
        $updated = $true
    }
    $envKospi = [string]$env:DAILY_KOSPI_D1_RETURN_PCT
    if (-not [string]::IsNullOrWhiteSpace($envKospi)) {
        $current["kospi_d1_return_pct"] = [math]::Round([double]$envKospi, 8)
        $updated = $true
    }

    if (-not $updated) {
        return
    }

    $current["schema"] = "daily_market_close_inputs_v1"
    $current["generated_at_utc"] = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    if (-not $current.ContainsKey("notes")) {
        $current["notes"] = "Set daily close return percentages before strict daily tasks run."
    }

    $dir = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $ordered = [ordered]@{}
    foreach ($k in @("schema", "generated_at_utc", "notes", "kospi_d1_return_pct", "btc_binance_d1_return_pct")) {
        if ($current.ContainsKey($k)) {
            $ordered[$k] = $current[$k]
        }
    }
    $ordered | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding utf8
    Write-TaskLog "INFO local_input_json refreshed from env path=$path"
}

function Get-BtcReturnFromLocalInputFile {
    $path = Get-DailyCloseInputPath
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }
    try {
        $obj = Get-Content -LiteralPath $path -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $obj) {
            return $null
        }
        $v = $obj.btc_binance_d1_return_pct
        if ($null -eq $v -or [string]::IsNullOrWhiteSpace([string]$v)) {
            return $null
        }
        return [math]::Round([double]$v, 8)
    } catch {
        return $null
    }
}

function Get-StrictModeEnabled {
    param([bool]$CliStrict)
    if ($CliStrict) {
        return $true
    }
    $raw = [string]$env:DAILY_REQUIRE_CLOSE_RETURN
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $false
    }
    return $raw.Trim().ToLower() -in @("1", "true", "yes", "on")
}

if (-not (Test-Path $runner)) {
    Write-TaskLog "ERROR runner missing: $runner"
    throw "Waiting queue runner not found: $runner"
}

try {
    Set-Location $workspace
    $strictMode = Get-StrictModeEnabled -CliStrict:$StrictCloseReturn
    Update-DailyCloseInputFromEnv

    $invokeArgs = @{
        SkipBundle = $true
        SkipNightWatchmanHarness = $true
        SkipBtrackGates = $true
        HypothesisMetric = "BTC_BINANCE_D1_RETURN_PCT"
        MarketVenue = "BINANCE"
        PredictedBand = "DOWN_STRONG"
        HitThresholdPct = "-1.0"
        FailThresholdPct = "1.8"
    }
    $btcReturnPct = $null
    if (-not [string]::IsNullOrWhiteSpace([string]$env:DAILY_BTC_BINANCE_D1_RETURN_PCT)) {
        $btcReturnPct = [string]$env:DAILY_BTC_BINANCE_D1_RETURN_PCT
        Write-TaskLog "INFO close_return source=env value=$btcReturnPct"
    } else {
        $localPct = Get-BtcReturnFromLocalInputFile
        if ($null -ne $localPct) {
            $btcReturnPct = [string]$localPct
            Write-TaskLog "INFO close_return source=local_input_json value=$btcReturnPct"
        } else {
            $apiPct = Get-BtcBinanceD1ReturnPct
            if ($null -ne $apiPct) {
                $btcReturnPct = [string]$apiPct
                Write-TaskLog "INFO close_return source=binance_api value=$btcReturnPct"
            } else {
                $cgPct = Get-BtcCoingeckoD1ReturnPct
                if ($null -ne $cgPct) {
                    $btcReturnPct = [string]$cgPct
                    Write-TaskLog "INFO close_return source=coingecko_api value=$btcReturnPct"
                } else {
                    Write-TaskLog "WARN close_return source=none fallback=PENDING_CLOSE"
                }
            }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$btcReturnPct)) {
        $invokeArgs["CloseReturnPct"] = [string]$btcReturnPct
    } elseif ($strictMode) {
        Write-TaskLog "ERROR strict_close_return=true and source unavailable; aborting run"
        throw "StrictCloseReturn enabled: close return could not be resolved from env/local/binance/coingecko"
    }

    $stdoutFile = Join-Path $workspace "docs\final\artifacts\waiting_queue_btc_binance_daily_task.stdout.log"
    $stderrFile = Join-Path $workspace "docs\final\artifacts\waiting_queue_btc_binance_daily_task.stderr.log"
    $maxAttempts = 2
    $attempt = 0
    $lastExitCode = 0
    do {
        $attempt += 1
        & $runner @invokeArgs 1>> $stdoutFile 2>> $stderrFile
        $lastExitCode = $LASTEXITCODE
        if ($lastExitCode -eq 0) {
            break
        }
        $stderrTail = ""
        if (Test-Path $stderrFile) {
            $stderrTail = (Get-Content $stderrFile -Tail 20 -ErrorAction SilentlyContinue) -join " | "
        }
        Write-TaskLog "WARN attempt=$attempt/$maxAttempts exit_code=$lastExitCode; stderr_tail=$stderrTail"
        if ($attempt -lt $maxAttempts) {
            Start-Sleep -Seconds 10
        }
    } while ($attempt -lt $maxAttempts)
    if ($lastExitCode -ne 0) {
        throw "BTC Binance daily waiting queue failed after $maxAttempts attempts (last exit code: $lastExitCode)"
    }

    $pendingAlertStreak = 3
    if (-not [string]::IsNullOrWhiteSpace([string]$env:DAILY_PENDING_CLOSE_ALERT_STREAK)) {
        try { $pendingAlertStreak = [int]$env:DAILY_PENDING_CLOSE_ALERT_STREAK } catch { $pendingAlertStreak = 3 }
    }
    $pendingStreak = Get-PendingCloseStreak -LogPath $waitingLogPath -Metric "BTC_BINANCE_D1_RETURN_PCT"
    if ($pendingStreak -ge $pendingAlertStreak) {
        Write-TaskLog "WARN pending_close_streak=$pendingStreak threshold=$pendingAlertStreak metric=BTC_BINANCE_D1_RETURN_PCT"
    }
    $pendingRateD5 = Get-PendingCloseRateD5 -DistributionPath $distributionPath
    if (($null -ne $pendingRateD5) -and ($pendingRateD5 -ge 0.6)) {
        Write-TaskLog "WARN pending_close_rate_d5=$pendingRateD5 threshold=0.6 metric=BTC_BINANCE_D1_RETURN_PCT"
    }

    Write-TaskLog "OK btc binance daily waiting queue success (attempt=$attempt)"
    exit 0
} catch {
    Write-TaskLog "ERROR exception: $($_.Exception.Message)"
    Send-CriticalAlert -title "waiting_queue_btc_binance_daily_failed" -detail "$($_.Exception.Message)"
    exit 1
}
