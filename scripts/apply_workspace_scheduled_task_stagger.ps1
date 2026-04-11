<#
.SYNOPSIS
  Applies schtasks /Change /ST from workspace_scheduled_tasks_stagger_plan_latest.json.

.DESCRIPTION
  Without -Apply: prints schtasks lines only (safe). With -Apply: runs schtasks /Change
  (use an elevated PowerShell if tasks require admin).

.PARAMETER Apply
  Run schtasks /Change. Default is dry-run (print only).

.PARAMETER OnlyTaskNames
  If set, only plan rows whose TaskName is in this list are processed (retry failed renames with spaces).

.PARAMETER OnlyTaskNamesJoined
  Same as -OnlyTaskNames but one string with task names separated by | (for nested powershell -File where arrays split badly).

.PARAMETER WorkspaceRoot
  Repo root; default C:\workspace. Declared after -OnlyTaskNames so stray positional tokens do not overwrite it when using -OnlyTaskNames from a child powershell.exe.
#>
param(
    [switch]$Apply,
    [string[]]$OnlyTaskNames = @(),
    [string]$OnlyTaskNamesJoined = "",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
if ($OnlyTaskNamesJoined -and $OnlyTaskNamesJoined.Trim().Length -gt 0) {
    $split = $OnlyTaskNamesJoined.Split("|", [System.StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
    $OnlyTaskNames = [string[]]$split
}

$planPath = Join-Path $WorkspaceRoot "reports\workspace_scheduled_tasks_stagger_plan_latest.json"
if (-not (Test-Path -LiteralPath $planPath)) {
    throw "Missing plan. Run plan_workspace_scheduled_task_stagger.ps1 first: $planPath"
}

$doApply = [bool]$Apply

$rows = Get-Content -LiteralPath $planPath -Encoding UTF8 | ConvertFrom-Json
if ($rows -isnot [array]) { $rows = @($rows) }

$reportDir = Join-Path $WorkspaceRoot "reports"
$logPath = Join-Path $reportDir "workspace_scheduled_tasks_stagger_apply_log_latest.txt"
$log = New-Object System.Collections.Generic.List[string]
$stamp = (Get-Date).ToString("o")
[void]$log.Add("[$stamp] Apply=$doApply")

$ok = 0
$fail = 0
$skip = 0
foreach ($r in $rows) {
    if ($OnlyTaskNames.Count -gt 0) {
        $name = [string]$r.TaskName
        if ($name -notin $OnlyTaskNames) {
            $skip++
            continue
        }
    }
    $tn = [string]$r.FullTaskName
    if (-not $tn.StartsWith("\")) {
        $tn = "\" + [string]$r.TaskName
    }
    $st = [string]$r.SchtasksST
    $line = "schtasks.exe /Change /TN `"$tn`" /ST $st"
    if (-not $doApply) {
        Write-Host $line
        [void]$log.Add("DRYRUN $line")
        continue
    }
    # Use call operator so /TN stays one argument when the task name has spaces (Start-Process -ArgumentList splits wrong).
    & schtasks.exe /Change /TN $tn /ST $st
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        $ok++
        [void]$log.Add("OK $line")
    }
    else {
        $fail++
        [void]$log.Add("FAIL exit=$code $line")
        Write-Warning "schtasks failed ($code): $line"
    }
}

$log | Set-Content -LiteralPath $logPath -Encoding UTF8
Write-Host ""
Write-Host "Log:" $logPath
if ($doApply) {
    Write-Host "Applied OK:" $ok "Failed:" $fail
    if ($skip -gt 0) { Write-Host "Skipped (not in -OnlyTaskNames):" $skip }
}
else {
    $applySelf = Join-Path $PSScriptRoot "apply_workspace_scheduled_task_stagger.ps1"
    Write-Host "Dry-run only. To apply: powershell -NoProfile -ExecutionPolicy Bypass -File `"$applySelf`" -Apply (as Administrator if needed)."
    Write-Host "Subset retry (avoids nested -File array issues): -OnlyTaskNamesJoined 'Task A|Task B' OR run in this shell: & `"$applySelf`" -Apply -OnlyTaskNames @('Task A','Task B')"
}
