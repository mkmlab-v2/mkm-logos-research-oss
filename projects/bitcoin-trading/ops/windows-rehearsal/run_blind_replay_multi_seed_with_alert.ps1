param(
    [string]$InputCsv = "C:\workspace\data\external\historical_btcusdt_1d.csv",
    [string]$Seeds = "41,42,43,44,45",
    [int]$SampleSize = 60,
    [string]$Profiles = "A,B,C",
    [int]$MinMatched = 20,
    [string]$LogPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_log.txt",
    [string]$StatePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_alert_state.json",
    [string]$StatusPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_status_latest.json"
)

$ErrorActionPreference = "Stop"

function Write-TaskLog([string]$message) {
    $parent = Split-Path -Parent $LogPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -LiteralPath $LogPath -Value $line
    Write-Host $line
}

function Send-Slack([string]$text) {
    $webhook = [string]$env:FACT_SAFE_FATAL_SLACK_WEBHOOK
    if ([string]::IsNullOrWhiteSpace($webhook)) { return $false }
    try { Invoke-RestMethod -Method Post -Uri $webhook -ContentType "application/json" -Body (@{ text = $text } | ConvertTo-Json -Compress) | Out-Null; return $true } catch { return $false }
}

function Send-Telegram([string]$text) {
    $token = [string]$env:TELEGRAM_BOT_TOKEN
    $chat = [string]$env:TELEGRAM_CHAT_ID
    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chat)) { return $false }
    $uri = "https://api.telegram.org/bot{0}/sendMessage" -f $token.Trim()
    try { Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body (@{ chat_id = $chat; text = $text } | ConvertTo-Json -Compress) | Out-Null; return $true } catch { return $false }
}

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

function Save-Status([bool]$ok, [int]$exitCode, [bool]$slackSent, [bool]$telegramSent, [bool]$suppressed) {
    $parent = Split-Path -Parent $StatusPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $gridPath = "C:\workspace\reports\constitution\btrack_pilot\blind_replay\blind_replay_dataset_grid_latest.json"
    $grid = Read-JsonOrNull -path $gridPath
    $bestTag = ""
    $bestBal = 0.0
    $bestHit = 0.0
    if ($null -ne $grid -and $null -ne $grid.best_config) {
        $bestTag = [string]$grid.best_config.config_tag
        $bestBal = [double]$grid.best_config.eligible_best_profile_balanced_accuracy_mean
        $bestHit = [double]$grid.best_config.eligible_best_profile_hit_rate_mean
    }
    $obj = [ordered]@{
        schema = "blind_replay_multi_seed_status_v1"
        checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
        run_ok = $ok
        exit_code = $exitCode
        input_csv = $InputCsv
        seeds = $Seeds
        sample_size = $SampleSize
        profiles = $Profiles
        min_matched = $MinMatched
        best_config = $bestTag
        best_balanced_accuracy_mean = $bestBal
        best_hit_rate_mean = $bestHit
        alerts = [ordered]@{
            slack_sent = $slackSent
            telegram_sent = $telegramSent
            duplicate_suppressed = $suppressed
        }
    }
    $obj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
}

function Get-State() {
    $obj = Read-JsonOrNull -path $StatePath
    if ($null -eq $obj) { return @{ last_alert_key = "" } }
    return @{ last_alert_key = [string]$obj.last_alert_key }
}

function Save-State([string]$key) {
    $parent = Split-Path -Parent $StatePath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    @{ last_alert_key = $key } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

$fallbackCsv = "C:\workspace\research\market_data\btc_daily_external_yf.csv"
if (-not (Test-Path -LiteralPath $InputCsv)) {
    if (Test-Path -LiteralPath $fallbackCsv) {
        Write-TaskLog "WARN primary CSV missing; using fallback: $fallbackCsv"
        $InputCsv = $fallbackCsv
    }
}

Write-TaskLog "RUN blind_replay_multi_seed start"
$cmd = @(
    "C:\workspace\scripts\run_blind_replay_dataset_grid.py",
    "--input-csv", $InputCsv,
    "--sample-size", "$SampleSize",
    "--seeds", $Seeds,
    "--profiles", $Profiles,
    "--dense-grid",
    "--min-matched", "$MinMatched"
)
& py @cmd
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Save-Status -ok $true -exitCode $exitCode -slackSent $false -telegramSent $false -suppressed $false
    Write-TaskLog "OK blind_replay_multi_seed passed"
    exit 0
}

$today = Get-Date -Format "yyyy-MM-dd"
$alertKey = "{0}|exit={1}|csv={2}" -f $today, $exitCode, $InputCsv
$state = Get-State
if ($state.last_alert_key -eq $alertKey) {
    Save-Status -ok $false -exitCode $exitCode -slackSent $false -telegramSent $false -suppressed $true
    Write-TaskLog "INFO duplicate failure today; alert suppressed"
    exit $exitCode
}

$message = @"
🚨 Blind Replay multi-seed FAILED
- exit_code: $exitCode
- input_csv: $InputCsv
- seeds: $Seeds
- sample_size: $SampleSize
- host: $env:COMPUTERNAME
"@

$slackSent = Send-Slack -text $message
$telegramSent = Send-Telegram -text $message
Save-Status -ok $false -exitCode $exitCode -slackSent $slackSent -telegramSent $telegramSent -suppressed $false
if ($slackSent -or $telegramSent) {
    Save-State -key $alertKey
    Write-TaskLog "ALERT sent (slack=$slackSent telegram=$telegramSent)"
} else {
    Write-TaskLog "WARN alert channels unavailable"
}
exit $exitCode
