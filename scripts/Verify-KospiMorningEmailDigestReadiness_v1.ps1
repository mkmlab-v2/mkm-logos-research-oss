#Requires -Version 5.1
<#
.SYNOPSIS
  Readiness check for automatic KOSPI morning email digest (Graph/Gmail → moksorinw@gmail.com).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$graphMail = Join-Path $WorkspaceRoot "scripts\Use-GraphMailSecureSession.ps1"
if (Test-Path -LiteralPath $graphMail) {
    . $graphMail
}

$checks = @(
    @{ Name = "script"; Path = "scripts\send_kospi_morning_email_digest_v1.py" },
    @{ Name = "invoke"; Path = "scripts\Invoke-KospiMorningEmailDigest_v1.ps1" },
    @{ Name = "register"; Path = "scripts\Register-KospiMorningEmailDigestTask.ps1" }
)
foreach ($c in $checks) {
    $p = Join-Path $WorkspaceRoot $c.Path
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Host "[FAIL] missing $($c.Name): $p" -ForegroundColor Red
        exit 1
    }
}

& $py -c @"
import sys
sys.path.insert(0, 'scripts')
from send_kospi_morning_email_digest_v1 import (
    _default_recipient,
    _graph_ready,
    _gmail_ready,
    _load_dotenv,
)
_load_dotenv()
recipient = _default_recipient()
if not recipient:
    print('RECIPIENT_MISSING')
    raise SystemExit(1)
if _graph_ready():
    print('TRANSPORT_OK graph recipient=' + recipient)
    raise SystemExit(0)
if _gmail_ready():
    print('TRANSPORT_OK gmail recipient=' + recipient)
    raise SystemExit(0)
print('TRANSPORT_MISSING: set Graph (GRAPH_*) or Gmail (GMAIL_SMTP_USER + GMAIL_APP_PASSWORD)')
print('recipient_default=' + recipient)
raise SystemExit(1)
"@
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] outbound transport not ready (Graph/Gmail). Inbound CF routing to Gmail is separate." -ForegroundColor Red
    exit 1
}

$taskName = "MKM-Kospi-Morning-Email-Digest"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "[WARN] task not registered: $taskName (run Register-KospiMorningEmailDigestTask.ps1)" -ForegroundColor Yellow
    exit 2
}
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host "[OK] $taskName State=$($task.State) Next=$($info.NextRunTime)" -ForegroundColor Green
exit 0
