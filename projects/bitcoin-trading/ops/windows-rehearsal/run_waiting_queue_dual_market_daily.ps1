param(
    [switch]$StrictCloseReturn,
    [switch]$SkipExternalFeedValidation,
    [switch]$StrictExternalFeedValidation
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
$runner = Join-Path $workspace "scripts\run_waiting_queue_monthly_check.ps1"
$taskLog = Join-Path $workspace "docs\final\artifacts\waiting_queue_dual_market_daily_task.log"
$lockPath = Join-Path $workspace "docs\final\artifacts\locks\waiting_queue_dual_market_daily.lock.json"

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

function Get-KospiD1ReturnPct {
    param([int]$TimeoutSec = 8)

    $yahooUrl = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=%5EKS11"
    try {
        $resp = Invoke-RestMethod -Method Get -Uri $yahooUrl -TimeoutSec $TimeoutSec
        $pct = $resp.quoteResponse.result[0].regularMarketChangePercent
        if ($null -ne $pct) {
            return [math]::Round([double]$pct, 8)
        }
    } catch {
    }

    $stooqUrl = "https://stooq.com/q/d/l/?s=%5Ekospi&i=d"
    try {
        $resp = Invoke-WebRequest -Method Get -Uri $stooqUrl -TimeoutSec $TimeoutSec
        $lines = @($resp.Content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
        if ($lines.Count -ge 3) {
            $latest = $lines[1].Split(",")
            $prev = $lines[2].Split(",")
            if ($latest.Count -ge 5 -and $prev.Count -ge 5) {
                $latestClose = [double]$latest[4]
                $prevClose = [double]$prev[4]
                if ($prevClose -ne 0) {
                    $pct = (($latestClose - $prevClose) / $prevClose) * 100.0
                    return [math]::Round($pct, 8)
                }
            }
        }
    } catch {
    }
    return $null
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
    $envKospi = [string]$env:DAILY_KOSPI_D1_RETURN_PCT
    if (-not [string]::IsNullOrWhiteSpace($envKospi)) {
        $current["kospi_d1_return_pct"] = [math]::Round([double]$envKospi, 8)
        $updated = $true
    }
    $envBtc = [string]$env:DAILY_BTC_BINANCE_D1_RETURN_PCT
    if (-not [string]::IsNullOrWhiteSpace($envBtc)) {
        $current["btc_binance_d1_return_pct"] = [math]::Round([double]$envBtc, 8)
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

function Get-DailyCloseFromLocalInputFile {
    param([string]$Key)
    $path = Get-DailyCloseInputPath
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }
    try {
        $obj = Get-Content -LiteralPath $path -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $obj) {
            return $null
        }
        $v = $obj.$Key
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

function Acquire-TaskLock {
    param([string]$Path)
    $lockDir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $lockDir)) {
        New-Item -ItemType Directory -Path $lockDir -Force | Out-Null
    }
    if (Test-Path -LiteralPath $Path) {
        Write-TaskLog "WARN lock_exists path=$Path -> skip duplicated run"
        return $false
    }
    $payload = @{
        schema = "task_lock_v1"
        task = "waiting_queue_dual_market_daily"
        created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        host = $env:COMPUTERNAME
        pid = $PID
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Path -Encoding utf8
    return $true
}

function Release-TaskLock {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $runner)) {
    Write-TaskLog "ERROR runner missing: $runner"
    throw "Waiting queue runner not found: $runner"
}

try {
    if (-not (Acquire-TaskLock -Path $lockPath)) {
        exit 0
    }
    Set-Location $workspace
    $strictMode = Get-StrictModeEnabled -CliStrict:$StrictCloseReturn
    Update-DailyCloseInputFromEnv

    $stdoutFile = Join-Path $workspace "docs\final\artifacts\waiting_queue_dual_market_daily_task.stdout.log"
    $stderrFile = Join-Path $workspace "docs\final\artifacts\waiting_queue_dual_market_daily_task.stderr.log"
    $invokeArgs = @{
        SkipBundle = $true
        SkipNightWatchmanHarness = $true
        SkipBtrackGates = $true
        HypothesisMetric = "KOSPI_D1_RETURN_PCT"
        MarketVenue = "KRX"
        PredictedBand = "DOWN_STRONG"
        HitThresholdPct = "-0.8"
        FailThresholdPct = "1.5"
        SecondaryHypothesisMetric = "BTC_BINANCE_D1_RETURN_PCT"
        SecondaryMarketVenue = "BINANCE"
        SecondaryPredictedBand = "DOWN_STRONG"
        SecondaryHitThresholdPct = "-1.0"
        SecondaryFailThresholdPct = "1.8"
    }
    if ($SkipExternalFeedValidation) {
        $invokeArgs["SkipExternalFeedValidation"] = $true
    }
    if ($StrictExternalFeedValidation) {
        $invokeArgs["StrictExternalFeedValidation"] = $true
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$env:DAILY_KOSPI_D1_RETURN_PCT)) {
        $invokeArgs["CloseReturnPct"] = [string]$env:DAILY_KOSPI_D1_RETURN_PCT
        Write-TaskLog "INFO close_return source=env value=$($invokeArgs["CloseReturnPct"])"
    } else {
        $localKospi = Get-DailyCloseFromLocalInputFile -Key "kospi_d1_return_pct"
        if ($null -ne $localKospi) {
            $invokeArgs["CloseReturnPct"] = [string]$localKospi
            Write-TaskLog "INFO close_return source=local_input_json value=$($invokeArgs["CloseReturnPct"])"
        } else {
            $kospiPct = Get-KospiD1ReturnPct
            if ($null -ne $kospiPct) {
                $invokeArgs["CloseReturnPct"] = [string]$kospiPct
                Write-TaskLog "INFO close_return source=kospi_api value=$($invokeArgs["CloseReturnPct"])"
            }
        }
    }
    if (-not $invokeArgs.ContainsKey("CloseReturnPct") -and $strictMode) {
        Write-TaskLog "ERROR strict_close_return=true and primary close_return unavailable"
        throw "StrictCloseReturn enabled: KOSPI close return unavailable from env/local/yahoo/stooq"
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$env:DAILY_BTC_BINANCE_D1_RETURN_PCT)) {
        $invokeArgs["SecondaryCloseReturnPct"] = [string]$env:DAILY_BTC_BINANCE_D1_RETURN_PCT
        Write-TaskLog "INFO secondary_close_return source=env value=$($invokeArgs["SecondaryCloseReturnPct"])"
    } else {
        $localBtc = Get-DailyCloseFromLocalInputFile -Key "btc_binance_d1_return_pct"
        if ($null -ne $localBtc) {
            $invokeArgs["SecondaryCloseReturnPct"] = [string]$localBtc
            Write-TaskLog "INFO secondary_close_return source=local_input_json value=$($invokeArgs["SecondaryCloseReturnPct"])"
        } else {
            $apiPct = Get-BtcBinanceD1ReturnPct
            if ($null -ne $apiPct) {
                $invokeArgs["SecondaryCloseReturnPct"] = [string]$apiPct
                Write-TaskLog "INFO secondary_close_return source=binance_api value=$($invokeArgs["SecondaryCloseReturnPct"])"
            } else {
                $cgPct = Get-BtcCoingeckoD1ReturnPct
                if ($null -ne $cgPct) {
                    $invokeArgs["SecondaryCloseReturnPct"] = [string]$cgPct
                    Write-TaskLog "INFO secondary_close_return source=coingecko_api value=$($invokeArgs["SecondaryCloseReturnPct"])"
                } else {
                    Write-TaskLog "WARN secondary_close_return source=none fallback=PENDING_CLOSE"
                    if ($strictMode) {
                        Write-TaskLog "ERROR strict_close_return=true and secondary close_return unavailable"
                        throw "StrictCloseReturn enabled: secondary close return unavailable from env/local/binance/coingecko"
                    }
                }
            }
        }
    }
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
        throw "Dual market waiting queue failed after $maxAttempts attempts (last exit code: $lastExitCode)"
    }

    Write-TaskLog "OK dual market waiting queue success (attempt=$attempt)"
    exit 0
} catch {
    Write-TaskLog "ERROR exception: $($_.Exception.Message)"
    Send-CriticalAlert -title "waiting_queue_dual_market_daily_failed" -detail "$($_.Exception.Message)"
    exit 1
} finally {
    Release-TaskLock -Path $lockPath
}
