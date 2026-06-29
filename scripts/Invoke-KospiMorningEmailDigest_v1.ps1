#Requires -Version 5.1
<#
.SYNOPSIS
  Morning KOSPI slim digest via email (Telegram OFF default path).

.DESCRIPTION
  Runs prophecy refresh then send_kospi_morning_email_digest_v1.py (slim ~10 lines, Korean).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$secureMail = Join-Path $WorkspaceRoot "scripts\Use-GraphMailSecureSession.ps1"
if (Test-Path -LiteralPath $secureMail) {
    . $secureMail
}
$gmailMail = Join-Path $WorkspaceRoot "scripts\Use-GmailSmtpSecureSession.ps1"
if (Test-Path -LiteralPath $gmailMail) {
    . $gmailMail
}

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
foreach ($n in @(
    "MKM_KOSPI_MORNING_EMAIL_ENABLED",
    "MKM_KOSPI_MORNING_EMAIL_TO",
    "MKM_MKMLIFE_SUPPORT_FORWARD_TO",
    "GRAPH_TENANT_ID",
    "GRAPH_CLIENT_ID",
    "GRAPH_CLIENT_SECRET",
    "GRAPH_SENDER_UPN"
)) {
    $cur = [Environment]::GetEnvironmentVariable($n, "Process")
    if ($cur) { continue }
    $u = [Environment]::GetEnvironmentVariable($n, "User")
    if ($u) { [Environment]::SetEnvironmentVariable($n, $u, "Process") }
}
[Environment]::SetEnvironmentVariable("MKM_KOSPI_MORNING_EMAIL_ENABLED", "1", "Process")
if (-not [Environment]::GetEnvironmentVariable("MKM_KOSPI_MORNING_EMAIL_TO", "Process")) {
    $to = [Environment]::GetEnvironmentVariable("MKM_KOSPI_MORNING_EMAIL_TO", "User")
    if (-not $to) { $to = [Environment]::GetEnvironmentVariable("MKM_MKMLIFE_SUPPORT_FORWARD_TO", "User") }
    if (-not $to) { $to = "moksorinw@gmail.com" }
    [Environment]::SetEnvironmentVariable("MKM_KOSPI_MORNING_EMAIL_TO", $to, "Process")
}
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_PROPHECY_SLIM", "1", "Process")
[Environment]::SetEnvironmentVariable("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0", "Process")

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$refreshPs1 = Join-Path $WorkspaceRoot "scripts\Invoke-TelegramMorningProphecyRefresh_v1.ps1"
if (Test-Path -LiteralPath $refreshPs1) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $refreshPs1 -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Prophecy brief refresh failed (exit $LASTEXITCODE); email uses last-known artifacts."
    }
}

$emailArgs = @("scripts/send_kospi_morning_email_digest_v1.py", "--force")
if ($DryRun) { $emailArgs += "--dry-run" }
& $py @emailArgs
exit $LASTEXITCODE
