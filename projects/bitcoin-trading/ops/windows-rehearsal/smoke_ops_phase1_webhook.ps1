$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    foreach ($scope in @("Process", "User", "Machine")) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    }
    return $null
}

$urls = @()
$opsUrl = Get-EnvAny "OPS_ALARM_WEBHOOK_URL"
$fatalUrl = Get-EnvAny "FACT_SAFE_FATAL_SLACK_WEBHOOK"
$slackUrl = Get-EnvAny "SLACK_WEBHOOK_URL"
foreach ($candidate in @($opsUrl, $fatalUrl, $slackUrl)) {
    if (-not [string]::IsNullOrWhiteSpace($candidate) -and -not ($urls -contains $candidate)) {
        $urls += $candidate
    }
}
if ($urls.Count -eq 0) {
    Write-Host "[smoke] INFO: no webhook URL found in OPS_ALARM_WEBHOOK_URL / FACT_SAFE_FATAL_SLACK_WEBHOOK / SLACK_WEBHOOK_URL."
}

$bodyObj = [ordered]@{
    event   = "ops_phase1_chain"
    kind    = "smoke_test"
    message = "manual or CI smoke; no chain failure"
    report_path = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json"
    ts_utc  = [DateTimeOffset]::UtcNow.ToString("o")
}
$json = $bodyObj | ConvertTo-Json -Compress -Depth 5

function Test-IsSlackWebhook([string]$u) {
    if ([string]::IsNullOrWhiteSpace($u)) { return $false }
    try {
        $uri = [uri]$u
        return ($uri.Host -match "hooks\.slack\.com$")
    }
    catch {
        return $false
    }
}

function Send-Webhook([string]$u, [string]$genericJson, [hashtable]$obj) {
    if (Test-IsSlackWebhook $u) {
        $text = "[smoke][ops_phase1_chain] kind={0} message={1} ts={2}" -f $obj.kind, $obj.message, $obj.ts_utc
        $slackBody = @{ text = $text } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $u -Method Post -Body $slackBody -ContentType "application/json; charset=utf-8" -TimeoutSec 30 | Out-Null
        return
    }
    Invoke-RestMethod -Uri $u -Method Post -Body $genericJson -ContentType "application/json; charset=utf-8" -TimeoutSec 30 | Out-Null
}

$webhookOk = $false
foreach ($url in $urls) {
    if ($webhookOk) { break }
    try {
        Send-Webhook -u $url -genericJson $json -obj $bodyObj
        Write-Host ("[smoke] OK: POST sent to webhook ({0})" -f $url)
        $webhookOk = $true
    }
    catch {
        Write-Host ("[smoke] WARN webhook failed ({0}): {1}" -f $url, $_.Exception.Message) -ForegroundColor Yellow
    }
}

$tgToken = Get-EnvAny "TELEGRAM_BOT_TOKEN"
$tgChat = Get-EnvAny "TELEGRAM_CHAT_ID"
$telegramOk = $false
$telegramFallbackEnabled = $false
$tgFlag = Get-EnvAny "OPS_TELEGRAM_FALLBACK_ENABLED"
if (-not [string]::IsNullOrWhiteSpace($tgFlag)) {
    $v = $tgFlag.Trim().ToLowerInvariant()
    if ($v -in @("1", "true", "yes", "on")) { $telegramFallbackEnabled = $true }
}
if ($telegramFallbackEnabled -and -not $webhookOk -and -not [string]::IsNullOrWhiteSpace($tgToken) -and -not [string]::IsNullOrWhiteSpace($tgChat)) {
    try {
        $tgUri = "https://api.telegram.org/bot{0}/sendMessage" -f $tgToken.Trim()
        $tgBody = @{ chat_id = $tgChat; text = "[smoke][ops_phase1_chain] alert route test" } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $tgUri -Method Post -Body $tgBody -ContentType "application/json; charset=utf-8" -TimeoutSec 30 | Out-Null
        Write-Host "[smoke] OK: alert routed via Telegram fallback"
        $telegramOk = $true
    }
    catch {
        Write-Host ("[smoke] WARN telegram failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

if ($webhookOk -or $telegramOk) {
    exit 0
}

Write-Host "[smoke] FAIL: no alert channel delivered" -ForegroundColor Red
exit 1
