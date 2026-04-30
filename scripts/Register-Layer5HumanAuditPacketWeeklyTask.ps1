<#
.SYNOPSIS
  Register (or remove) weekly task that builds Layer5 human audit packet/template.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Layer5_HumanAuditPacket_Weekly",
    [string]$SundayAt = "09:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\build_layer5_human_audit_packet_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 09:00), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"py `"$runner`" --goldset-jsonl `"docs/final/artifacts/layer5_incident_goldset_human_v1_latest.jsonl`" --packet-json `"docs/final/artifacts/layer5_human_audit_packet_latest.json`" --review-csv `"docs/final/artifacts/layer5_human_audit_review_template_v1.csv`"`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly build of Layer5 human audit packet + review CSV template."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
