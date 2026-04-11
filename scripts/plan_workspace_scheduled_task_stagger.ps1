<#
.SYNOPSIS
  Builds a stagger plan for overloaded next-run hour buckets (workspace tasks only).

.DESCRIPTION
  Groups tasks by the hour of Get-ScheduledTaskInfo.NextRunTime and, for buckets with
  at least -MinBucketCount tasks, spreads start minutes evenly across 00-59 within that hour.
  Does not change the system. Output: reports/workspace_scheduled_tasks_stagger_plan_latest.json

.PARAMETER MinBucketCount
  Only buckets with at least this many tasks get a stagger plan (default: 8).

.PARAMETER IncludeDisabled
  If set, Disabled tasks participate in the plan (default: Ready only).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MinBucketCount = 8,
    [string[]]$ExcludePattern = @(),
    [switch]$IncludeDisabled
)

$ErrorActionPreference = "Stop"
$workspaceRootResolved = $WorkspaceRoot
$csvPath = Join-Path $workspaceRootResolved "reports\workspace_scheduled_tasks_audit_latest.csv"
if (-not (Test-Path -LiteralPath $csvPath)) {
    throw "Run audit_workspace_scheduled_tasks.ps1 first: missing $csvPath"
}

function Test-Excluded([string]$name, [string[]]$patterns) {
    foreach ($p in $patterns) {
        if ([string]::IsNullOrWhiteSpace($p)) { continue }
        if ($name -like $p) { return $true }
    }
    return $false
}

function Get-StaggerMinute([int]$index, [int]$total) {
    if ($total -le 1) { return 0 }
    return [int][math]::Floor($index * 59.0 / ($total - 1))
}

$rows = Import-Csv -LiteralPath $csvPath
$items = New-Object System.Collections.Generic.List[object]
foreach ($row in $rows) {
    $tp = $row.TaskPath
    $tn = $row.TaskName
    if (Test-Excluded $tn $ExcludePattern) { continue }

    $t = Get-ScheduledTask -TaskName $tn -TaskPath $tp -ErrorAction SilentlyContinue
    if (-not $t) { continue }
    $state = [string]$t.State
    if (-not $IncludeDisabled -and $state -eq "Disabled") { continue }

    $info = Get-ScheduledTaskInfo -InputObject $t -ErrorAction SilentlyContinue
    $nr = $null
    try { $nr = $info.NextRunTime } catch {}
    if (-not $nr) { continue }

    $bucket = "{0:D2}:00" -f $nr.Hour
    [void]$items.Add([pscustomobject]@{
        TaskPath    = $tp
        TaskName    = $tn
        State       = $state
        NextRunTime = $nr
        HourBucket  = $bucket
    })
}

$grouped = $items | Group-Object HourBucket | Where-Object { $_.Count -ge $MinBucketCount } | Sort-Object Name

$plan = New-Object System.Collections.Generic.List[object]
foreach ($g in $grouped) {
    $sorted = @($g.Group | Sort-Object TaskName)
    $n = $sorted.Count
    for ($i = 0; $i -lt $n; $i++) {
        $row = $sorted[$i]
        $nr = $row.NextRunTime
        $min = Get-StaggerMinute -index $i -total $n
        $suggested = Get-Date -Year $nr.Year -Month $nr.Month -Day $nr.Day -Hour $nr.Hour -Minute $min -Second 0
        $fullTn = "$($row.TaskPath)$($row.TaskName)"
        [void]$plan.Add([pscustomobject]@{
            TaskPath           = $row.TaskPath
            TaskName           = $row.TaskName
            FullTaskName       = $fullTn
            State              = $row.State
            PreviousNextRunUtc = $nr.ToUniversalTime().ToString("o")
            SuggestedLocal     = $suggested.ToString("o")
            SchtasksST         = $suggested.ToString("HH:mm")
            HourBucket         = $g.Name
            StaggerIndex       = $i
            StaggerCount       = $n
        })
    }
}

$reportDir = Join-Path $workspaceRootResolved "reports"
if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
$outPath = Join-Path $reportDir "workspace_scheduled_tasks_stagger_plan_latest.json"
$plan | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $outPath

Write-Host "Planned stagger entries:" $plan.Count "JSON:" $outPath
Write-Host "Buckets processed (>= $MinBucketCount tasks):" $grouped.Count
foreach ($g in $grouped) {
    Write-Host ("  {0}: {1} tasks -> staggered minutes 0..59 within that hour" -f $g.Name, $g.Count)
}
Write-Host ""
Write-Host "Next: review JSON, then run apply_workspace_scheduled_task_stagger.ps1 (dry-run), then the same with -Apply (admin if needed)."
