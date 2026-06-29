#Requires -Version 5.1
<#
.SYNOPSIS
  Apply MKM company email 3-tier policy: User env, digest schedule, policy artifact.

.DESCRIPTION
  Public: support@mkmlife.com | Ops: moksorinw@no1kmedi.com | Workspace: admin@no1kmedi.com
  Inbox hub: moksorinw@gmail.com (CF Email Routing). Morning digest: Gmail SMTP 08:28, Telegram OFF.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$InboxHub = "moksorinw@gmail.com",
    [switch]$SkipTaskRegister
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$envMap = @{
    MKM_MKMLIFE_SUPPORT_FORWARD_TO       = $InboxHub
    MKM_KOSPI_MORNING_EMAIL_TO           = $InboxHub
    MKM_KOSPI_MORNING_EMAIL_ENABLED      = "1"
    MKM_KOSPI_MORNING_EMAIL_TRANSPORT    = "auto"
    MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED  = "0"
    MKM_TELEGRAM_EVENING_DIGEST_ENABLED  = "0"
    MKM_TELEGRAM_FOUR_LENS_ENABLED       = "0"
    MKM_ORCHESTRATOR_TELEGRAM_NOTIFY     = "0"
    MKM_TELEGRAM_PROPHECY_SLIM           = "1"
    MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE = "0"
}
foreach ($k in $envMap.Keys) {
    [Environment]::SetEnvironmentVariable($k, $envMap[$k], "User")
    [Environment]::SetEnvironmentVariable($k, $envMap[$k], "Process")
}
Write-Host "[policy] User+Process env applied ($InboxHub hub)" -ForegroundColor Green

foreach ($tn in @("MKM-Telegram-Minimal-Daily-Digest", "MKM-Telegram-Afternoon-Daily-Digest")) {
    $t = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if ($t -and $t.State -ne "Disabled") {
        Disable-ScheduledTask -TaskName $tn | Out-Null
        Write-Host "[policy] Disabled $tn" -ForegroundColor Yellow
    }
}

if (-not $SkipTaskRegister) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Register-KospiMorningEmailDigestTask.ps1") -WorkspaceRoot $WorkspaceRoot
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $py (Join-Path $WorkspaceRoot "scripts\build_mkm_company_email_ops_policy_v1.py")

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Verify-KospiMorningEmailDigestReadiness_v1.ps1") -WorkspaceRoot $WorkspaceRoot
exit $LASTEXITCODE
