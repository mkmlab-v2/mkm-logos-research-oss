<#
.SYNOPSIS
  Register (or remove) a daily scheduled task for MKM Myeongri AI prompt chain.

.DESCRIPTION
  Schedules scripts/Run-MyeongriAiPromptChainDaily_v1.ps1 once per day.
  Default time avoids dense 07:00~09:50 automation window.
#>
param(
    [switch]$Remove,
    [switch]$WhatIf,
    [string]$TaskName = "MKM_MyeongriAiPromptChain_Daily",
    [string]$DailyAt = "10:40",
    [string]$Profile = "daewoon",
    [string]$TopN = "5",
    [string]$Lang = "ko",
    [string]$Query = "",
    [string]$DeterministicJson = "C:\workspace\docs\final\artifacts\myeongni_independent_lens_from_chain_latest.json",
    [switch]$BuildAnswerDraft
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-MyeongriAiPromptChainDaily_v1.ps1"

if ($Remove) {
    if ($WhatIf) {
        Write-Host "[WhatIf] Unregister-ScheduledTask -TaskName $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 10:40), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`"",
    "-Profile", $Profile,
    "-TopN", $TopN,
    "-Lang", $Lang,
    "-DeterministicJson", "`"$DeterministicJson`""
)
if ($BuildAnswerDraft) { $runnerArgs += "-BuildAnswerDraft" }
if ($Query -and $Query.Trim().Length -gt 0) {
    $runnerArgs += @("-Query", "`"$Query`"")
}
$argLine = $runnerArgs -join " "

if ($WhatIf) {
    Write-Host "[WhatIf] Register-ScheduledTask -TaskName $TaskName -DailyAt $DailyAt"
    Write-Host "[WhatIf] Action: powershell.exe $argLine"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily MKM Myeongri prompt+reference chain (B-track enrichment, no live trigger)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Argument: $argLine"
exit 0
