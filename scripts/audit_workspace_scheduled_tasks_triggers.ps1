# Summarizes triggers for workspace tasks (read-only). Use to stagger heavy windows and reduce overlap.
# Requires: reports/workspace_scheduled_tasks_audit_latest.csv from audit_workspace_scheduled_tasks.ps1
$ErrorActionPreference = "SilentlyContinue"
$workspaceRoot = "C:\workspace"
$csvPath = Join-Path $workspaceRoot "reports\workspace_scheduled_tasks_audit_latest.csv"
if (-not (Test-Path -LiteralPath $csvPath)) {
    throw "Run audit_workspace_scheduled_tasks.ps1 first: missing $csvPath"
}

function Get-TriggerSummary([Microsoft.Management.Infrastructure.CimInstance[]]$triggers) {
    if (-not $triggers -or $triggers.Count -eq 0) { return "" }
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($tr in $triggers) {
        $cn = $null
        try { $cn = $tr.CimClass.CimClassName } catch {}
        $line = if ($cn) { $cn } else { "Trigger" }
        try {
            if ($tr.Repetition -and $tr.Repetition.Interval) {
                $line += " every=$($tr.Repetition.Interval)"
            }
        }
        catch {}
        try {
            if ($tr.StartBoundary) { $line += " start=$($tr.StartBoundary)" }
        }
        catch {}
        [void]$parts.Add($line)
    }
    return ($parts -join " | ")
}

function Get-StartHourBucket([datetime]$dt) {
    return "{0:D2}:00" -f $dt.Hour
}

$rows = Import-Csv -LiteralPath $csvPath
$out = New-Object System.Collections.Generic.List[object]
foreach ($row in $rows) {
    $tp = $row.TaskPath
    $tn = $row.TaskName
    $t = Get-ScheduledTask -TaskName $tn -TaskPath $tp -ErrorAction SilentlyContinue
    if (-not $t) {
        [void]$out.Add([pscustomobject]@{
            TaskName       = $tn
            State          = "MISSING"
            NextRunTime    = $null
            TriggerCount   = 0
            TriggerSummary = ""
            StartHourBucket = ""
        })
        continue
    }
    $info = Get-ScheduledTaskInfo -InputObject $t -ErrorAction SilentlyContinue
    $nr = $null
    try { $nr = $info.NextRunTime } catch {}
    $bucket = ""
    if ($nr) { $bucket = Get-StartHourBucket $nr }
    $sum = Get-TriggerSummary -triggers @($t.Triggers)
    [void]$out.Add([pscustomobject]@{
        TaskName        = $tn
        State           = [string]$t.State
        NextRunTime     = $nr
        TriggerCount    = @($t.Triggers).Count
        TriggerSummary  = $sum
        StartHourBucket = $bucket
    })
}

$reportDir = Join-Path $workspaceRoot "reports"
if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
$csvOut = Join-Path $reportDir "workspace_scheduled_tasks_triggers_latest.csv"
$out | Export-Csv -NoTypeInformation -Encoding UTF8 $csvOut

$heat = $out | Where-Object { $_.StartHourBucket -and $_.State -ne "MISSING" } |
    Group-Object StartHourBucket | Sort-Object Count -Descending

Write-Host "Tasks:" $out.Count "CSV:" $csvOut
Write-Host ""
Write-Host "Next-run hour buckets (rough load proxy; many tasks in same hour = consider staggering):"
$heat | Select-Object -First 12 | ForEach-Object { Write-Host ("  {0}: {1} tasks" -f $_.Name, $_.Count) }
Write-Host ""
Write-Host "Tip: stagger triggers in Task Scheduler UI, or re-register with register_*.ps1 -StartTime / -MO."
