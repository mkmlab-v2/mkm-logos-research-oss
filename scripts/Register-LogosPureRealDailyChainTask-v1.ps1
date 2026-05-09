param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Logos-PureReal-DailyChain",
    [string]$At = "07:20",
    [double]$MaxAllowedDelta = 0.15
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-LogosPureRealDailyChain-v1.ps1"
if (-not (Test-Path $runner)) {
  throw "Runner script not found: $runner"
}

$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -MaxAllowedDelta $MaxAllowedDelta"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

Write-Output "{`"ok`":true,`"task`":`"$TaskName`",`"at`":`"$At`"}"

