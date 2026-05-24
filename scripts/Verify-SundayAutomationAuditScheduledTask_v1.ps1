#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM-Sunday-Automation-LastResult-Audit task registration and runner script.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-SundayAutomationAuditScheduledTask_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Sunday-Automation-LastResult-Audit"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$fail = $false
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-CheckSundayAutomationLastResult_v1.ps1"
if (Test-Path -LiteralPath $runner) {
    Write-Host "[OK] $runner" -ForegroundColor Green
} else {
    Write-Host "[MISS] $runner" -ForegroundColor Red
    $fail = $true
}

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $t) {
    Write-Host "[MISS] Task $TaskName" -ForegroundColor Red
    exit 1
}
$i = Get-ScheduledTaskInfo -TaskName $TaskName
$logon = $t.Principal.LogonType.ToString()
Write-Host "[OK] Task $TaskName State=$($t.State) Next=$($i.NextRunTime) Logon=$logon" -ForegroundColor Green
if ($logon -notin @("S4U", "ServiceAccount", "Interactive")) {
    Write-Host "[WARN] LogonType=$logon (S4U recommended for logged-off Sunday chain)" -ForegroundColor Yellow
}

if ($fail) { exit 1 }
exit 0
