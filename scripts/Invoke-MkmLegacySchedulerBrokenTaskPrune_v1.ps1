#Requires -Version 5.1
<#
.SYNOPSIS
  Remove MKM/Athena scheduled tasks whose runner scripts are missing from the repo.

.DESCRIPTION
  Idempotent hygiene for legacy scheduler entries (e.g. SleepMode distillation script removed).
  Does not touch Ready MKM core stack tasks. Writes reports/mkm_legacy_scheduler_prune_v1_latest.json.

  Non-admin: tries Unregister; on access denied falls back to Disable (partial).
  Admin or -SelfElevate: full Unregister (recommended finish).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmLegacySchedulerBrokenTaskPrune_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmLegacySchedulerBrokenTaskPrune_v1.ps1 -SelfElevate
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmLegacySchedulerBrokenTaskPrune_v1.ps1 -WhatIfOnly
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$WhatIfOnly,
    [switch]$SelfElevate
)

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($SelfElevate -and -not (Test-IsAdmin)) {
    $path = $MyInvocation.MyCommand.Path
    Write-Host "[INFO] Requesting elevation (UAC) for full Unregister..." -ForegroundColor Yellow
    $argList = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $path,
        '-WorkspaceRoot', $WorkspaceRoot
    )
    if ($WhatIfOnly) { $argList += '-WhatIfOnly' }
    $proc = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList -Wait -PassThru
    exit $proc.ExitCode
}

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$isAdmin = Test-IsAdmin

# TaskName -> relative script path that must exist
$brokenCatalog = [ordered]@{
    "Athena_SleepMode_Distillation" = "scripts\run_sleep_mode_distillation.py"
    "MKM_DailyMeta"                 = "scripts\meta_orchestrator\run_daily_full.ps1"
}

$actions = [System.Collections.Generic.List[object]]::new()
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Invoke-TaskUnregister {
    param([string]$TaskName)
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
}

function Invoke-TaskUnregisterSchtasks {
    param([string]$TaskName)
    $tn = if ($TaskName.StartsWith('\')) { $TaskName } else { "\$TaskName" }
    & schtasks.exe /Delete /TN $tn /F 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "schtasks /Delete failed exit $LASTEXITCODE for $tn"
    }
}

foreach ($entry in $brokenCatalog.GetEnumerator()) {
    $taskName = [string]$entry.Key
    $relPath = [string]$entry.Value
    $fullPath = Join-Path $WorkspaceRoot $relPath
    $scriptMissing = -not (Test-Path -LiteralPath $fullPath)

    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task) {
        $actions.Add([ordered]@{
            task_name = $taskName
            action    = "skip_not_registered"
            script    = $relPath
        }) | Out-Null
        continue
    }

    if (-not $scriptMissing) {
        $actions.Add([ordered]@{
            task_name = $taskName
            action    = "skip_script_present"
            script    = $relPath
        }) | Out-Null
        continue
    }

    if ($WhatIfOnly) {
        $actions.Add([ordered]@{
            task_name = $taskName
            action    = "would_unregister"
            script    = $relPath
            reason    = "runner_missing"
            prior_state = [string]$task.State
        }) | Out-Null
        continue
    }

    $actionTaken = $null
    $priorState = [string]$task.State
    try {
        if ($isAdmin) {
            try {
                Invoke-TaskUnregister -TaskName $taskName
                $actionTaken = "unregistered"
            } catch {
                Invoke-TaskUnregisterSchtasks -TaskName $taskName
                $actionTaken = "unregistered_schtasks"
            }
        } else {
            Invoke-TaskUnregister -TaskName $taskName
            $actionTaken = "unregistered"
        }
        Write-Host "$actionTaken : $taskName (runner missing: $relPath)" -ForegroundColor Yellow
    } catch {
        $fqid = [string]$_.FullyQualifiedErrorId
        $msg = [string]$_.Exception.Message
        if ($fqid -match '80070005' -or $msg -match '80070005' -or $msg -match 'Access is denied') {
            try {
                Disable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
                $actionTaken = "disabled_needs_admin_unregister"
                Write-Host "Disabled only (run -SelfElevate to remove): $taskName" -ForegroundColor DarkYellow
            } catch {
                $actions.Add([ordered]@{
                    task_name     = $taskName
                    action        = "failed"
                    script        = $relPath
                    reason        = "runner_missing"
                    prior_state   = $priorState
                    error         = [string]$_.Exception.Message
                    admin_hint    = "scripts\\Invoke-MkmLegacySchedulerBrokenTaskPrune_v1.ps1 -SelfElevate"
                }) | Out-Null
                continue
            }
        } else {
            throw
        }
    }

    $actions.Add([ordered]@{
        task_name   = $taskName
        action      = $actionTaken
        script      = $relPath
        reason      = "runner_missing"
        prior_state = $priorState
        is_admin    = $isAdmin
    }) | Out-Null
}

$stillRegistered = @()
foreach ($entry in $brokenCatalog.GetEnumerator()) {
    $t = Get-ScheduledTask -TaskName ([string]$entry.Key) -ErrorAction SilentlyContinue
    if ($t) { $stillRegistered += [string]$entry.Key }
}

$report = [ordered]@{
    schema              = "mkm_legacy_scheduler_prune_v1"
    generated_at_utc    = $utc
    workspace_root      = $WorkspaceRoot
    what_if_only        = [bool]$WhatIfOnly
    is_admin            = $isAdmin
    catalog             = $brokenCatalog
    actions             = $actions
    still_registered    = $stillRegistered
    finish_recommended  = if ($stillRegistered.Count -gt 0) {
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmLegacySchedulerBrokenTaskPrune_v1.ps1 -SelfElevate"
    } else { $null }
    note_ko             = "Broken-runner legacy only; do not re-register SleepMode until run_sleep_mode_distillation.py exists in repo"
}

$outPath = Join-Path $WorkspaceRoot "reports\mkm_legacy_scheduler_prune_v1_latest.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath" -ForegroundColor Green

if ($stillRegistered.Count -gt 0 -and -not $WhatIfOnly) {
    Write-Host "PARTIAL: still registered: $($stillRegistered -join ', ') — run with -SelfElevate" -ForegroundColor DarkYellow
    exit 2
}
exit 0
