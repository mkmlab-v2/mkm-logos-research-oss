#Requires -Version 5.1
<#
.SYNOPSIS
  Daily 08:28 KST Korean prophecy-only Telegram digest (after 08:18 eval).

.DESCRIPTION
  research_only B-track briefing · no advanced/personal/RAG paste in morning window.
  Used by MKM-Telegram-Minimal-Daily-Digest (avoid fragile inline -Command in schtasks).
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
foreach ($n in @("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED")) {
    $cur = [Environment]::GetEnvironmentVariable($n, "Process")
    if ($cur) { continue }
    $u = [Environment]::GetEnvironmentVariable($n, "User")
    if ($u) { [Environment]::SetEnvironmentVariable($n, $u, "Process") }
}
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", "1", "Process")
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_DIGEST_STYLE", "prophecy", "Process")
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_INCLUDE_PERSONAL_FORTUNE", "0", "Process")
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_MORNING_KOSPI_ONLY", "1", "Process")

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

& $py scripts/send_telegram_minimal_ops_digest_v1.py --scheduled-morning
exit $LASTEXITCODE
