<#
.SYNOPSIS
  Register/remove/query monthly genius governance task suite.
#>
param(
    [switch]$Remove,
    [switch]$StatusOnly
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"

$tasks = @(
    @{
        Name = "MKM_GeniusReasoning_MonthlyRefresh"
        RegisterScript = "scripts\Register-GeniusReasoningMonthlyRefreshTask.ps1"
        Args = @("-DayOfMonth", "1", "-MonthlyAt", "08:30")
    },
    @{
        Name = "MKM_GeniusDispatch_Chaos_MonthlyDrill"
        RegisterScript = "scripts\Register-GeniusDispatchChaosMonthlyDrillTask.ps1"
        Args = @("-DayOfMonth", "1", "-MonthlyAt", "08:40")
    },
    @{
        Name = "MKM_GeniusHumanReview_HoldRehearsal_Monthly"
        RegisterScript = "scripts\Register-GeniusHumanReviewHoldRehearsalMonthlyTask.ps1"
        Args = @("-DayOfMonth", "1", "-MonthlyAt", "08:50")
    }
)

function Show-TaskStatus {
    param([string]$TaskName)
    & schtasks.exe /Query /TN $TaskName /V /FO LIST
}

if (-not $StatusOnly) {
    foreach ($t in $tasks) {
        $scriptPath = Join-Path $workspaceRoot $t.RegisterScript
        if (-not (Test-Path -LiteralPath $scriptPath)) {
            throw "Register script not found: $scriptPath"
        }
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $scriptPath)
        if ($Remove) {
            $args += "-Remove"
        } else {
            $args += $t.Args
        }
        & powershell @args
        if ($LASTEXITCODE -ne 0) {
            throw "Task register/remove failed: $($t.Name)"
        }
    }
}

Write-Host "=== Genius Governance Monthly Suite Status ==="
foreach ($t in $tasks) {
    Write-Host ""
    Write-Host "[Task] $($t.Name)"
    Show-TaskStatus -TaskName $t.Name
}

Write-Host ""
Write-Host "DONE: Register-GeniusGovernanceMonthlySuite"
