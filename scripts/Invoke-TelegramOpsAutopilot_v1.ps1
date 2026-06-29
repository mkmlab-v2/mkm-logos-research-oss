#Requires -Version 5.1
<#
.SYNOPSIS
  One-click Telegram ops: noise env guard, KOSPI refresh, optional send, n8n Telegram mute.

.DESCRIPTION
  research_only B-track morning prophecy path. Idempotent User env writes.
  Default: email slim digest (Telegram OFF). Use -SendTelegram to force legacy TG send.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipSend,
    [switch]$SendTelegram,
    [switch]$SkipN8nMute,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$envMap = @{
    MKM_TELEGRAM_FOUR_LENS_ENABLED           = "0"
    FACT_SAFE_TELEGRAM_FALLBACK_ENABLED      = "0"
    CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY     = "0"
    OPS_TELEGRAM_FALLBACK_ENABLED            = "0"
    MKM_ORCHESTRATOR_TELEGRAM_NOTIFY         = "0"
    MKM_TELEGRAM_MORNING_KOSPI_ONLY          = "1"
    MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED      = "0"
    MKM_TELEGRAM_EVENING_DIGEST_ENABLED      = "0"
    MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE    = "0"
    MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL       = "0"
    MKM_TELEGRAM_PROPHECY_INCLUDE_OPS_CONTEXT = "0"
    MKM_TELEGRAM_PROPHECY_INCLUDE_MISSION_C_SHADOW = "0"
    MKM_TELEGRAM_PROPHECY_SLIM               = "1"
    MKM_TELEGRAM_LEGACY_DIGEST_ENABLED       = "0"
    MKM_KOSPI_MORNING_EMAIL_ENABLED          = "1"
    MKM_KOSPI_MORNING_EMAIL_TO               = "moksorinw@gmail.com"
}
foreach ($k in $envMap.Keys) {
    [Environment]::SetEnvironmentVariable($k, $envMap[$k], "User")
    [Environment]::SetEnvironmentVariable($k, $envMap[$k], "Process")
}
Write-Host "[autopilot] User+Process env noise guard applied" -ForegroundColor Green

$refresh = Join-Path $WorkspaceRoot "scripts\Invoke-TelegramMorningProphecyRefresh_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $refresh -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
    if ($Strict) { throw "Prophecy refresh exit $LASTEXITCODE" }
    Write-Warning "Prophecy refresh failed; continuing"
}

if (-not $SkipN8nMute) {
    Write-Host "[autopilot] mute_n8n_telegram_workflows_v1.py --vps" -ForegroundColor Cyan
    & $py scripts/mute_n8n_telegram_workflows_v1.py --vps
    if ($LASTEXITCODE -ne 0 -and $Strict) { throw "n8n telegram mute exit $LASTEXITCODE" }
    Write-Host "[autopilot] mute_n8n_telegram_workflows_v1.py (local)" -ForegroundColor Cyan
    & $py scripts/mute_n8n_telegram_workflows_v1.py
    if ($LASTEXITCODE -ne 0 -and $Strict) { throw "local n8n telegram mute exit $LASTEXITCODE" }
}

if (-not $SkipSend) {
    if ($SendTelegram) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-TelegramMinimalDailyDigest_v1.ps1") -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) {
            if ($Strict) { throw "Telegram send exit $LASTEXITCODE" }
            Write-Warning "Telegram send failed"
        }
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-KospiMorningEmailDigest_v1.ps1") -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) {
            if ($Strict) { throw "Email digest exit $LASTEXITCODE" }
            Write-Warning "Email digest failed (check HOSTINGER_SMTP_* / MKM_KOSPI_MORNING_EMAIL_TO)"
        }
    }
} else {
    & $py scripts/send_kospi_morning_email_digest_v1.py --dry-run --force
}

foreach ($tn in @("MKM-Telegram-Minimal-Daily-Digest", "MKM-Telegram-Afternoon-Daily-Digest")) {
    $t = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if ($t -and $t.State -ne "Disabled") {
        Disable-ScheduledTask -TaskName $tn | Out-Null
        Write-Host "[autopilot] Disabled scheduled task: $tn" -ForegroundColor Yellow
    }
}

$task = Get-ScheduledTask -TaskName "MKM-Telegram-Minimal-Daily-Digest" -ErrorAction SilentlyContinue
$info = if ($task) { Get-ScheduledTaskInfo -TaskName "MKM-Telegram-Minimal-Daily-Digest" } else { $null }
Write-Host "[autopilot] OK · TG task next=$($info.NextRunTime)" -ForegroundColor Green
exit 0
