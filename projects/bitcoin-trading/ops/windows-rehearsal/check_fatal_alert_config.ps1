param(
    [string]$OutPath = "C:\workspace\docs\final\artifacts\fatal_alert_config_status_latest.json"
)

$ErrorActionPreference = "Stop"

$slack = [string]$env:FACT_SAFE_FATAL_SLACK_WEBHOOK
$tgBot = [string]$env:TELEGRAM_BOT_TOKEN
$tgChat = [string]$env:TELEGRAM_CHAT_ID

$slackReady = -not [string]::IsNullOrWhiteSpace($slack)
$telegramReady = (-not [string]::IsNullOrWhiteSpace($tgBot)) -and (-not [string]::IsNullOrWhiteSpace($tgChat))
$ready = $slackReady -or $telegramReady

$missing = @()
if (-not $slackReady) {
    $missing += "FACT_SAFE_FATAL_SLACK_WEBHOOK"
}
if (-not $telegramReady) {
    if ([string]::IsNullOrWhiteSpace($tgBot)) {
        $missing += "TELEGRAM_BOT_TOKEN"
    }
    if ([string]::IsNullOrWhiteSpace($tgChat)) {
        $missing += "TELEGRAM_CHAT_ID"
    }
}

$obj = [ordered]@{
    schema = "fatal_alert_config_status_v1"
    checked_at_utc = ([DateTimeOffset]::UtcNow).ToString("o")
    fatal_alert_ready = $ready
    channels = [ordered]@{
        slack = [ordered]@{ ready = $slackReady }
        telegram = [ordered]@{ ready = $telegramReady }
    }
    missing_env = $missing
}

$dir = Split-Path -Parent $OutPath
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$obj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutPath -Encoding utf8

if ($ready) {
    Write-Host "OK fatal alert config ready"
    exit 0
}

Write-Host "WARN fatal alert config incomplete"
exit 0
