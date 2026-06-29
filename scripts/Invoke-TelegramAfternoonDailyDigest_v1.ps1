#Requires -Version 5.1
<#
.SYNOPSIS
  Daily 18:00 KST Korean afternoon Telegram — commander fortune + KOSPI [HYPO].

.DESCRIPTION
  research_only B-track · refreshes commander fortune then sends afternoon style only.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$dotEnv = Join-Path $WorkspaceRoot ".env"
if (Test-Path -LiteralPath $dotEnv) {
    Get-Content -LiteralPath $dotEnv -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $k = $line.Substring(0, $eq).Trim()
        $v = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if ($k) { [Environment]::SetEnvironmentVariable($k, $v, "Process") }
    }
}
foreach ($n in @("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")) {
    $cur = [Environment]::GetEnvironmentVariable($n, "Process")
    if ($cur) { continue }
    $u = [Environment]::GetEnvironmentVariable($n, "User")
    if ($u) { [Environment]::SetEnvironmentVariable($n, $u, "Process") }
}
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", "1", "Process")
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_DIGEST_STYLE", "afternoon", "Process")
foreach ($k in @(
    "MKM_TELEGRAM_EVENING_DIGEST_ENABLED",
    "MKM_TELEGRAM_FOUR_LENS_ENABLED",
    "MKM_TELEGRAM_LEGACY_DIGEST_ENABLED",
    "CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY",
    "FACT_SAFE_TELEGRAM_FALLBACK_ENABLED",
    "MKM_ORCHESTRATOR_TELEGRAM_NOTIFY"
)) {
    [Environment]::SetEnvironmentVariable($k, "0", "Process")
}

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

Write-Host "[afternoon-digest] build_commander_daily_fortune_v1.py" -ForegroundColor Cyan
& $py scripts/build_commander_daily_fortune_v1.py --skip-regenerate
if ($LASTEXITCODE -ne 0) {
    Write-Warning "fortune refresh failed (exit $LASTEXITCODE); sending with last-known fortune."
}

$juneLoop = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026ProphecyLoop_v1.ps1"
if (Test-Path -LiteralPath $juneLoop) {
    Write-Host "[afternoon-digest] KospiJune Evening (SkipHeavyResearch)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $juneLoop -WorkspaceRoot $WorkspaceRoot -Phase Evening -YearMonth 2026-06 -SkipHeavyResearch
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "KospiJune evening loop exit $LASTEXITCODE (continuing send)"
    }
}

& $py scripts/send_telegram_minimal_ops_digest_v1.py --scheduled-afternoon
exit $LASTEXITCODE
