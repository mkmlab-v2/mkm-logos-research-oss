param(
    [string]$ApiBaseUrl = "https://api.jemaai.cloud",
    [string]$LogPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_alert_log.txt",
    [string]$StatePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_alert_state.json"
)

$ErrorActionPreference = "Stop"

function Write-TaskLog([string]$message) {
    $parent = Split-Path -Parent $LogPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -LiteralPath $LogPath -Value $line
    Write-Host $line
}

function Send-Slack([string]$text) {
    $webhook = [string]$env:FACT_SAFE_FATAL_SLACK_WEBHOOK
    if ([string]::IsNullOrWhiteSpace($webhook)) { return $false }
    try {
        Invoke-RestMethod -Method Post -Uri $webhook -ContentType "application/json" -Body (@{ text = $text } | ConvertTo-Json -Compress) | Out-Null
        return $true
    } catch {
        Write-TaskLog ("WARN slack_send_failed: " + $_.Exception.Message)
        return $false
    }
}

function Send-Telegram([string]$text) {
    $token = [string]$env:TELEGRAM_BOT_TOKEN
    $chat = [string]$env:TELEGRAM_CHAT_ID
    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chat)) { return $false }
    $uri = "https://api.telegram.org/bot{0}/sendMessage" -f $token.Trim()
    try {
        Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body (@{ chat_id = $chat; text = $text } | ConvertTo-Json -Compress) | Out-Null
        return $true
    } catch {
        Write-TaskLog ("WARN telegram_send_failed: " + $_.Exception.Message)
        return $false
    }
}

function Get-State() {
    if (-not (Test-Path -LiteralPath $StatePath)) { return @{ last_alert_key = "" } }
    try {
        $obj = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        return @{ last_alert_key = [string]$obj.last_alert_key }
    } catch {
        return @{ last_alert_key = "" }
    }
}

function Save-State([string]$key) {
    $parent = Split-Path -Parent $StatePath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    @{ last_alert_key = $key } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

$smokeScript = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_jemaai_public_event_e2e_smoke.ps1"
if (-not (Test-Path -LiteralPath $smokeScript)) {
    throw "Missing smoke script: $smokeScript"
}

Write-TaskLog "RUN jemaai_e2e_smoke start"
& powershell -NoProfile -ExecutionPolicy Bypass -File $smokeScript -ApiBaseUrl $ApiBaseUrl
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-TaskLog "OK jemaai_e2e_smoke passed"
    exit 0
}

$today = Get-Date -Format "yyyy-MM-dd"
$alertKey = "{0}|exit={1}|api={2}" -f $today, $exitCode, $ApiBaseUrl
$state = Get-State
if ($state.last_alert_key -eq $alertKey) {
    Write-TaskLog "INFO duplicate failure today; alert suppressed"
    exit $exitCode
}

$message = @"
🚨 Jemaai public-event E2E smoke FAILED
- exit_code: $exitCode
- api_base: $ApiBaseUrl
- host: $env:COMPUTERNAME
- script: run_jemaai_public_event_e2e_smoke.ps1
"@

$slackSent = Send-Slack -text $message
$telegramSent = Send-Telegram -text $message
if ($slackSent -or $telegramSent) {
    Save-State -key $alertKey
    Write-TaskLog "ALERT sent (slack=$slackSent telegram=$telegramSent)"
} else {
    Write-TaskLog "WARN alert channels unavailable"
}

exit $exitCode
