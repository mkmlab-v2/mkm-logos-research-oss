# Reads reports/workspace_scheduled_tasks_audit_latest.csv and checks LastRunTime / LastTaskResult per task.
# Note: LastTaskResult is not always the child process exit code; some tasks show 0xFFFD0000 when the engine
# does not surface the real exit code (especially mixed schtasks/Register-ScheduledTask). Treat as "unclear".
$ErrorActionPreference = "SilentlyContinue"
$workspaceRoot = "C:\workspace"
$csvPath = Join-Path $workspaceRoot "reports\workspace_scheduled_tasks_audit_latest.csv"
if (-not (Test-Path -LiteralPath $csvPath)) {
    throw "Run audit_workspace_scheduled_tasks.ps1 first: missing $csvPath"
}

function Get-ResultHex([object]$code) {
    if ($null -eq $code) { return "" }
    try {
        $u = [uint32][int64]$code
        return ("0x{0:X8}" -f $u)
    }
    catch {
        return ""
    }
}

# SCHED_S_* informational range
function Test-BenignTaskResult([uint32]$code) {
    if ($code -eq 0) { return $true }
    $u = [uint32]$code
    if ($u -ge 0x41300 -and $u -le 0x4130F) { return $true }
    return $false
}

function Get-TaskResultCategory([uint32]$u) {
    if ($u -eq 0) { return "OK" }
    if ($u -ge 0x41300 -and $u -le 0x4130F) { return "SchedulerInfo" }
    # Scheduler API often returns this mask when the real child exit code is not surfaced.
    if ($u -eq [uint32]4294770688) { return "Unclear_NotRecorded" }
    # Any HRESULT-style failure (e.g. 0x80070002 file not found)
    if (($u -band [uint32]0xF0000000) -eq [uint32]0x80000000) { return "HRESULT" }
    if ($u -eq 1) { return "ExitCode_1" }
    if ($u -eq 2) { return "ExitCode_2" }
    if ($u -eq 64) { return "ExitCode_64" }
    return "OtherNonZero"
}

$rows = Import-Csv -LiteralPath $csvPath
$results = New-Object System.Collections.Generic.List[object]
foreach ($row in $rows) {
    $tp = $row.TaskPath
    $tn = $row.TaskName
    $t = Get-ScheduledTask -TaskName $tn -TaskPath $tp -ErrorAction SilentlyContinue
    if (-not $t) {
        $results.Add([pscustomobject]@{
            TaskName       = $tn
            TaskPath       = $tp
            State          = "MISSING"
            LastRunTime    = $null
            LastTaskResult = $null
            ResultHex      = ""
            Category       = "MISSING"
            NextRunTime    = $null
            Note           = "Task not found in scheduler (rename? or re-run audit CSV)"
        })
        continue
    }
    $info = Get-ScheduledTaskInfo -InputObject $t -ErrorAction SilentlyContinue
    $nr = $null
    try { $nr = $info.NextRunTime } catch {}
    $ltr = $info.LastTaskResult
    $u = [uint32]0
    try { $u = [uint32][int64]$ltr } catch {}
    $results.Add([pscustomobject]@{
        TaskName       = $tn
        TaskPath       = $tp
        State          = [string]$t.State
        LastRunTime    = $info.LastRunTime
        LastTaskResult = $ltr
        ResultHex      = (Get-ResultHex $ltr)
        Category       = (Get-TaskResultCategory $u)
        NextRunTime    = $nr
        Note           = ""
    })
}

$reportDir = Join-Path $workspaceRoot "reports"
if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
$jsonPath = Join-Path $reportDir "workspace_scheduled_tasks_last_run_latest.json"
$csvOut = Join-Path $reportDir "workspace_scheduled_tasks_last_run_latest.csv"
$results | Export-Csv -NoTypeInformation -Encoding UTF8 $csvOut
$results | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $jsonPath

$missing = @($results | Where-Object { $_.Category -eq "MISSING" })
$ok = @($results | Where-Object { $_.Category -eq "OK" })
$schedInfo = @($results | Where-Object { $_.Category -eq "SchedulerInfo" })
$unclear = @($results | Where-Object { $_.Category -eq "Unclear_NotRecorded" })
$exit1 = @($results | Where-Object { $_.Category -eq "ExitCode_1" })
$exit2 = @($results | Where-Object { $_.Category -eq "ExitCode_2" })
$hr = @($results | Where-Object { $_.Category -eq "HRESULT" })
$unclearNotRec = @($results | Where-Object { $_.Category -eq "Unclear_NotRecorded" })
$other = @($results | Where-Object { $_.Category -eq "OtherNonZero" })

Write-Host "Tasks checked:" $results.Count
Write-Host "CSV:" $csvOut
Write-Host "JSON:" $jsonPath
Write-Host ""
Write-Host "LastTaskResult summary:"
Write-Host "  OK (0):" $ok.Count
Write-Host "  SchedulerInfo (0x4130x, never run / not scheduled / etc.):" $schedInfo.Count
Write-Host "  Unclear 0xFFFD0000 (scheduler may not record real exit code; check script logs):" $unclearNotRec.Count
Write-Host "  Exit code 1 (typical script failure):" $exit1.Count
Write-Host "  Exit code 2:" $exit2.Count
Write-Host "  HRESULT (0x8000xxxx, e.g. 0x80070002):" $hr.Count
Write-Host "  Other non-zero:" $other.Count
Write-Host "  Missing from scheduler vs CSV:" $missing.Count
Write-Host ""

if ($exit1.Count -gt 0) {
    Write-Host "--- Exit code 1 (review script / env) ---"
    $exit1 | Sort-Object TaskName | Format-Table TaskName, State, LastRunTime, ResultHex -AutoSize
}
if ($exit2.Count -gt 0) {
    Write-Host "--- Exit code 2 ---"
    $exit2 | Sort-Object TaskName | Format-Table TaskName, State, LastRunTime, ResultHex -AutoSize
}
if ($hr.Count -gt 0) {
    Write-Host "--- HRESULT (0x8000xxxx) ---"
    $hr | Sort-Object TaskName | Format-Table TaskName, State, LastRunTime, LastTaskResult, ResultHex -AutoSize
}
if ($unclearNotRec.Count -gt 0) {
    Write-Host "--- Unclear 0xFFFD0000 (do not treat as script exit code; verify logs if needed) ---"
    $unclearNotRec | Sort-Object TaskName | Format-Table TaskName, State, LastRunTime, ResultHex -AutoSize
}
if ($other.Count -gt 0) {
    Write-Host "--- Other non-zero ---"
    $other | Sort-Object LastTaskResult | Format-Table TaskName, State, LastRunTime, LastTaskResult, ResultHex -AutoSize
}
if ($missing.Count -gt 0) {
    Write-Host "--- Missing tasks (refresh audit CSV if you renamed tasks) ---"
    $missing | Format-Table TaskName, TaskPath -AutoSize
}
