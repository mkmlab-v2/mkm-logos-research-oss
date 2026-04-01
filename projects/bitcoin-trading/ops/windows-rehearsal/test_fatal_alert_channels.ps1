param(
    [switch]$Send,
    [string]$OutPath = "C:\workspace\docs\final\artifacts\fatal_alert_channel_test_latest.json"
)

$ErrorActionPreference = "Stop"

function Send-Slack([string]$Webhook, [string]$Text) {
    Invoke-RestMethod -Method Post -Uri $Webhook -ContentType "application/json" -Body (@{ text = $Text } | ConvertTo-Json -Compress) | Out-Null
}

function Send-Telegram([string]$BotToken, [string]$ChatId, [string]$Text) {
    $uri = "https://api.telegram.org/bot$BotToken/sendMessage"
    Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body (@{ chat_id = $ChatId; text = $Text } | ConvertTo-Json -Compress) | Out-Null
}

$slackWebhook = [string]$env:FACT_SAFE_FATAL_SLACK_WEBHOOK
$tgBot = [string]$env:TELEGRAM_BOT_TOKEN
$tgChat = [string]$env:TELEGRAM_CHAT_ID
$ts = ([DateTimeOffset]::UtcNow).ToString("o")
$text = "[FATAL-TEST] waiting_queue alert channel smoke @ $ts"

$slackReady = -not [string]::IsNullOrWhiteSpace($slackWebhook)
$telegramReady = (-not [string]::IsNullOrWhiteSpace($tgBot)) -and (-not [string]::IsNullOrWhiteSpace($tgChat))

$slackSent = $false
$telegramSent = $false
$errors = @()

if ($Send) {
    if ($slackReady) {
        try {
            Send-Slack -Webhook $slackWebhook -Text $text
            $slackSent = $true
        } catch {
            $errors += "slack_send_failed"
        }
    }
    if ($telegramReady) {
        try {
            Send-Telegram -BotToken $tgBot -ChatId $tgChat -Text $text
            $telegramSent = $true
        } catch {
            $errors += "telegram_send_failed"
        }
    }
}

$obj = [ordered]@{
    schema = "fatal_alert_channel_test_v1"
    checked_at_utc = $ts
    mode = $(if ($Send) { "send" } else { "dry_run" })
    ready = [ordered]@{
        slack = $slackReady
        telegram = $telegramReady
    }
    sent = [ordered]@{
        slack = $slackSent
        telegram = $telegramSent
    }
    errors = $errors
}

$dir = Split-Path -Parent $OutPath
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$obj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutPath -Encoding utf8

if ($Send -and $errors.Count -gt 0) {
    Write-Host "WARN fatal alert channel test completed with errors"
    exit 1
}

Write-Host "OK fatal alert channel test completed"
exit 0
