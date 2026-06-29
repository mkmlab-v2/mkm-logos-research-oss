#Requires -Version 5.1
<#
.SYNOPSIS
  Register MKM_BtrackDailyHeroBoard (morning 08:10 + evening 19:05 KST) — Disabled by default.

.EXAMPLE
  pwsh -File scripts\Register-BtrackDailyHeroBoardTask_v1.ps1
  pwsh -File scripts\Register-BtrackDailyHeroBoardTask_v1.ps1 -Enable
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$MorningAt = "08:10",
    [string]$EveningAt = "19:05",
    [switch]$Enable,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path

function Register-One([string]$Name, [string]$At, [string]$Phase) {
    $action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$root\scripts\Run-BtrackDailyHeroBoardChain_v1.ps1`" -Phase $Phase -WorkspaceRoot `"$root`""
    if ($Remove) {
        schtasks /Delete /TN $Name /F 2>$null | Out-Null
        return
    }
    schtasks /Create /TN $Name /TR $action /SC DAILY /ST $At /F | Out-Null
    if (-not $Enable) { schtasks /Change /TN $Name /DISABLE | Out-Null }
    $state = if ($Enable) { "ENABLED" } else { "DISABLED" }
    Write-Host "[OK] Registered $state : $Name at $At -> Phase $Phase"
}

if ($Remove) {
    Register-One "MKM_BtrackDailyHeroBoard_Morning" "" "Morning"
    Register-One "MKM_BtrackDailyHeroBoard_Evening" "" "Evening"
    Write-Host "[REMOVED] Hero board tasks"
    exit 0
}

Register-One "MKM_BtrackDailyHeroBoard_Morning" $MorningAt "Morning"
Register-One "MKM_BtrackDailyHeroBoard_Evening" $EveningAt "Evening"
if (-not $Enable) {
    Write-Host "Enable: Enable-ScheduledTask -TaskName MKM_BtrackDailyHeroBoard_Morning|Evening"
}
