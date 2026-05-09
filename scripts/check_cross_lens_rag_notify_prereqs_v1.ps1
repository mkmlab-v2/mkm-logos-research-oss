<#
.SYNOPSIS
  Read-only check: cross-lens RAG alert notify env (no secret values printed).

.DESCRIPTION
  Verifies send_cross_lens_rag_alert_v1.py exists and reports whether webhook/Telegram
  env keys appear set in .env (value presence only: set / empty / missing).
  Use before enabling Register-DailyExecutionInsightBriefTask or after editing .env.

  Exit 0 always (informational). Use -Strict to exit 1 if Telegram is enabled but token/chat missing.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$scriptPath = Join-Path $root "scripts\send_cross_lens_rag_alert_v1.py"
$envPath = Join-Path $root ".env"

function Read-DotenvKeys {
    param([string]$Path)
    $out = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $out }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $k = $line.Substring(0, $eq).Trim()
        $v = $line.Substring($eq + 1).Trim()
        if ($v.Contains(" #")) { $v = $v.Split("#")[0].Trim() }
        if ($v.Length -ge 2 -and $v[0] -eq $v[-1] -and ($v[0] -eq "'" -or $v[0] -eq '"')) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        if ($k) { $out[$k] = $v }
    }
    return $out
}

function Format-Presence {
    param([string]$Val)
    if ($null -eq $Val) { return "missing" }
    if ([string]::IsNullOrWhiteSpace($Val)) { return "empty" }
    return "set"
}

if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-Host "FAIL: notifier script not found: $scriptPath" -ForegroundColor Red
    exit 1
}

$kv = Read-DotenvKeys -Path $envPath
function Key-Val($name) {
    if ($kv.ContainsKey($name)) { return $kv[$name] }
    $e = [Environment]::GetEnvironmentVariable($name, "User")
    if ($e) { return $e }
    return [Environment]::GetEnvironmentVariable($name, "Machine")
}

$cross = Key-Val "CROSS_LENS_RAG_ALERT_WEBHOOK_URL"
$ops = Key-Val "OPS_ALARM_WEBHOOK_URL"
$tgOn = Key-Val "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY"
$tgMin = Key-Val "CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS"
$tgTok = Key-Val "TELEGRAM_BOT_TOKEN"
$tgChat = Key-Val "TELEGRAM_CHAT_ID"

Write-Host "send_cross_lens_rag_alert_v1.py: OK ($scriptPath)"
Write-Host ".env path: $(if (Test-Path $envPath) { $envPath } else { '(no file)' })"
Write-Host "CROSS_LENS_RAG_ALERT_WEBHOOK_URL : $(Format-Presence $cross)"
Write-Host "OPS_ALARM_WEBHOOK_URL             : $(Format-Presence $ops)"
Write-Host "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY : $(Format-Presence $tgOn)  (use 1/true to enable)"
Write-Host "CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS : $(if ($tgMin) { $tgMin } else { '(default red)' })"
Write-Host "TELEGRAM_BOT_TOKEN                : $(Format-Presence $tgTok)"
Write-Host "TELEGRAM_CHAT_ID                  : $(Format-Presence $tgChat)"

$tgEnabled = $tgOn -and ($tgOn.ToString().Trim().ToLower() -in @("1", "true", "yes", "on"))
if ($Strict -and $tgEnabled -and (([string]::IsNullOrWhiteSpace($tgTok)) -or ([string]::IsNullOrWhiteSpace($tgChat)))) {
    Write-Host "STRICT: Telegram notify enabled but token/chat missing or empty." -ForegroundColor Red
    exit 1
}

exit 0
