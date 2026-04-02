param(
    [string]$ApiBaseUrl = "https://api.jemaai.cloud",
    [string]$LogPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_alert_log.txt",
    [string]$StatePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_alert_state.json",
    [string]$StatusPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_status_latest.json",
    [string]$SmokeReportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_report_latest.json"
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

function Save-Status(
    [int]$exitCode,
    [bool]$smokeOk,
    [bool]$slackReady,
    [bool]$telegramReady,
    [bool]$slackSent,
    [bool]$telegramSent,
    [bool]$duplicateSuppressed,
    [bool]$showroomQualityHooksOk
) {
    $parent = Split-Path -Parent $StatusPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $obj = [ordered]@{
        schema = "jemaai_e2e_smoke_alert_status_v1"
        checked_at_utc = [DateTime]::UtcNow.ToString("o")
        api_base = $ApiBaseUrl
        smoke_ok = $smokeOk
        exit_code = $exitCode
        channels = [ordered]@{
            slack_ready = $slackReady
            telegram_ready = $telegramReady
            slack_sent = $slackSent
            telegram_sent = $telegramSent
        }
        duplicate_suppressed = $duplicateSuppressed
        showroom_quality_hooks_ok = $showroomQualityHooksOk
        smoke_report_path = $SmokeReportPath
        host = $env:COMPUTERNAME
    }
    $obj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
}

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

$smokeScript = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_jemaai_public_event_e2e_smoke.ps1"
if (-not (Test-Path -LiteralPath $smokeScript)) {
    throw "Missing smoke script: $smokeScript"
}

Write-TaskLog "RUN jemaai_e2e_smoke start"
& powershell -NoProfile -ExecutionPolicy Bypass -File $smokeScript -ApiBaseUrl $ApiBaseUrl -OutputPath $SmokeReportPath
$exitCode = $LASTEXITCODE
$smokeReportObj = Read-JsonOrNull -path $SmokeReportPath
$showroomQualityHooksOk = $false
if ($null -ne $smokeReportObj -and $null -ne $smokeReportObj.checks) {
    $showroomQualityHooksOk = [bool]$smokeReportObj.checks.showroom_quality_hooks_ok
}
$slackReady = -not [string]::IsNullOrWhiteSpace([string]$env:FACT_SAFE_FATAL_SLACK_WEBHOOK)
$telegramReady = (-not [string]::IsNullOrWhiteSpace([string]$env:TELEGRAM_BOT_TOKEN)) -and (-not [string]::IsNullOrWhiteSpace([string]$env:TELEGRAM_CHAT_ID))

if ($exitCode -eq 0) {
    Save-Status -exitCode $exitCode -smokeOk $true -slackReady $slackReady -telegramReady $telegramReady -slackSent $false -telegramSent $false -duplicateSuppressed $false -showroomQualityHooksOk $showroomQualityHooksOk
    Write-TaskLog "OK jemaai_e2e_smoke passed"
    exit 0
}

$today = Get-Date -Format "yyyy-MM-dd"
$alertKey = "{0}|exit={1}|api={2}" -f $today, $exitCode, $ApiBaseUrl
$state = Get-State
if ($state.last_alert_key -eq $alertKey) {
    Save-Status -exitCode $exitCode -smokeOk $false -slackReady $slackReady -telegramReady $telegramReady -slackSent $false -telegramSent $false -duplicateSuppressed $true -showroomQualityHooksOk $showroomQualityHooksOk
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
Save-Status -exitCode $exitCode -smokeOk $false -slackReady $slackReady -telegramReady $telegramReady -slackSent $slackSent -telegramSent $telegramSent -duplicateSuppressed $false -showroomQualityHooksOk $showroomQualityHooksOk
if ($slackSent -or $telegramSent) {
    Save-State -key $alertKey
    Write-TaskLog "ALERT sent (slack=$slackSent telegram=$telegramSent)"
} else {
    Write-TaskLog "WARN alert channels unavailable"
}

exit $exitCode
