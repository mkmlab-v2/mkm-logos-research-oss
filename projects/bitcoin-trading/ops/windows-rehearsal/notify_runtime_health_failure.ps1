param(
    [string]$RuntimeHealthPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_health_latest.json",
    [string]$RuntimeBootstrapPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_bootstrap_report_latest.json",
    [string]$RuntimeTaskChainPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_task_chain_latest.json",
    [string]$RuntimeScheduleIntegrityPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_schedule_integrity_latest.json",
    [string]$StatePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_alert_state.json",
    [string]$LogPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_alert_log.txt"
)

$ErrorActionPreference = "Stop"

function Write-AlertLog([string]$message) {
    $parent = Split-Path -Parent $LogPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -LiteralPath $LogPath -Value $line
    Write-Host $line
}

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }
    try {
        return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-State() {
    $obj = Read-JsonOrNull -path $StatePath
    if ($null -eq $obj) {
        return @{ last_alert_key = "" }
    }
    return @{
        last_alert_key = [string]$obj.last_alert_key
    }
}

function Save-State([string]$key) {
    $parent = Split-Path -Parent $StatePath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    @{ last_alert_key = $key } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

function Send-Telegram([string]$text) {
    $token = [string]$env:TELEGRAM_BOT_TOKEN
    $chatId = [string]$env:TELEGRAM_CHAT_ID
    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chatId)) {
        Write-AlertLog "WARN telegram credentials missing, skipping telegram send."
        return $false
    }
    $url = "https://api.telegram.org/bot{0}/sendMessage" -f $token.Trim()
    $payload = @{
        chat_id = $chatId.Trim()
        text = $text
    }
    try {
        $null = Invoke-RestMethod -Method Post -Uri $url -Body $payload -TimeoutSec 10
        return $true
    } catch {
        Write-AlertLog ("ERROR telegram send failed: {0}" -f $_.Exception.Message)
        return $false
    }
}

$runtimeHealth = Read-JsonOrNull -path $RuntimeHealthPath
$runtimeBootstrap = Read-JsonOrNull -path $RuntimeBootstrapPath
$runtimeTaskChain = Read-JsonOrNull -path $RuntimeTaskChainPath
$runtimeScheduleIntegrity = Read-JsonOrNull -path $RuntimeScheduleIntegrityPath

if ($null -eq $runtimeHealth -or $null -eq $runtimeBootstrap -or $null -eq $runtimeTaskChain -or $null -eq $runtimeScheduleIntegrity) {
    Write-AlertLog "WARN runtime report files missing or unreadable; skipping alert cycle."
    exit 0
}

$healthOk = [bool]$runtimeHealth.overall_ok
$bootstrapOk = [bool]$runtimeBootstrap.all_ok
$chainOk = [bool]$runtimeTaskChain.all_ok
$scheduleOk = [bool]$runtimeScheduleIntegrity.integrity_ok

if ($healthOk -and $bootstrapOk -and $chainOk -and $scheduleOk) {
    Write-AlertLog "OK runtime health/bootstrap/task-chain/schedule all healthy."
    exit 0
}

$healthTs = [string]$runtimeHealth.timestamp
$bootTs = [string]$runtimeBootstrap.timestamp
$chainTs = [string]$runtimeTaskChain.timestamp
$scheduleTs = [string]$runtimeScheduleIntegrity.timestamp
$alertKey = "{0}|{1}|{2}|{3}|health={4}|boot={5}|chain={6}|schedule={7}" -f $healthTs, $bootTs, $chainTs, $scheduleTs, $healthOk, $bootstrapOk, $chainOk, $scheduleOk
$state = Get-State

if ($state.last_alert_key -eq $alertKey) {
    Write-AlertLog "INFO duplicate failure state; alert suppressed."
    exit 0
}

$message = @"
🚨 Runtime automation failure detected

- runtime_health.overall_ok: $healthOk (ts: $healthTs)
- runtime_bootstrap.all_ok: $bootstrapOk (ts: $bootTs)
- runtime_task_chain.all_ok: $chainOk (ts: $chainTs)
- runtime_schedule_integrity.integrity_ok: $scheduleOk (ts: $scheduleTs)
- host: $env:COMPUTERNAME
- workspace: C:\workspace
"@

$sent = Send-Telegram -text $message
if ($sent) {
    Save-State -key $alertKey
    Write-AlertLog "ALERT telegram sent and state updated."
} else {
    Write-AlertLog "WARN alert not sent (telegram unavailable/failure)."
}

exit 0
