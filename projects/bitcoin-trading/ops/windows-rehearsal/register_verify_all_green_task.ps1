param(
    [string]$TaskName = "\Bitcoin-Verify-All-Green-30min",
    [int]$IntervalMinutes = 30,
    [int]$StartDelayMinutes = 1,
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json",
    [switch]$EnforceRegistry,
    [switch]$SlackNotifyLive
)

$ErrorActionPreference = "Stop"

$taskCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$env:WORKSPACE\projects\bitcoin-trading\ops\windows-rehearsal\verify_all_green.ps1`" -OutputPath `"$OutputPath`""
if ($EnforceRegistry) {
    $taskCmd += " -EnforceRegistry"
}
if ($SlackNotifyLive) {
    $taskCmd += " -SlackNotifyLive"
}

# Ensure consistent command; schtasks TR expects the whole command in one string.
$taskCmdEscaped = $taskCmd.Replace('"', '""')

$st = (Get-Date).AddMinutes($StartDelayMinutes).ToString("HH:mm")

# Best-effort delete (no-op if missing)
schtasks /Delete /TN $TaskName /F | Out-Null 2>&1

$tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\verify_all_green.ps1`" -OutputPath `"$OutputPath`""
if ($EnforceRegistry) {
    $tr += " -EnforceRegistry"
}
if ($SlackNotifyLive) {
    $tr += " -SlackNotifyLive"
}

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /ST $st /TR $tr /F | Out-Null

Write-Host "Created task: $TaskName"
Write-Host "Schedule: every $IntervalMinutes minutes; start=$st"
Write-Host "TR: $tr"

# Also run immediately to populate "latest"
& powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\verify_all_green.ps1" -OutputPath $OutputPath | Out-Null

exit 0

