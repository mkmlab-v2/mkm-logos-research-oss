param(
    [ValidateSet("Quiet", "Restore")]
    [string]$Mode = "Quiet",
    [string]$BackupPath = "C:\workspace\reports\scheduler_quiet_mode_disable_backup_latest.json",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Get-TargetTasksForQuietMode {
    $all = Get-ScheduledTask
    $keepPattern = '(?i)(NotebookLM|MemoryRevival|EmotionWeightMemory|Notebook-Compression|Vault_Sync|Daily_Sync)'
    $targets = @()

    foreach ($t in $all) {
        $name = [string]$t.TaskName
        $intervals = @()
        foreach ($tr in $t.Triggers) {
            if ($tr.Repetition -and $tr.Repetition.Interval) {
                $intervals += [string]$tr.Repetition.Interval
            }
        }

        $hasFast = $intervals | Where-Object { $_ -in @('PT1M', 'PT5M', 'PT10M', 'PT15M', 'PT30M', 'PT1H') }
        if ($hasFast -and $name -match '^(Bitcoin-|MKM_|MKM-|Autonomous|Prophecy)' -and $name -notmatch $keepPattern) {
            $targets += $t
        }
    }

    return $targets
}

function Set-QuietMode {
    $targets = Get-TargetTasksForQuietMode
    $snapshot = @()
    foreach ($t in $targets) {
        $snapshot += [pscustomobject]@{
            TaskName = $t.TaskName
            TaskPath = $t.TaskPath
            State    = $t.State
        }
    }

    $backupDir = Split-Path -Parent $BackupPath
    if (-not (Test-Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir | Out-Null
    }
    $snapshot | ConvertTo-Json -Depth 4 | Set-Content -Path $BackupPath -Encoding UTF8

    $disabled = @()
    foreach ($t in $targets) {
        if ($t.State -eq "Disabled") {
            continue
        }
        if ($WhatIf) {
            Write-Output ("[WhatIf] Disable-ScheduledTask {0}" -f $t.TaskName)
            continue
        }
        Disable-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath | Out-Null
        $disabled += $t.TaskName
    }

    Write-Output ("mode=quiet target_count={0} disabled_now={1} backup={2}" -f $targets.Count, $disabled.Count, $BackupPath)
}

function Restore-QuietBackup {
    if (-not (Test-Path $BackupPath)) {
        throw "Backup file not found: $BackupPath"
    }

    $raw = Get-Content -Path $BackupPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "Backup file is empty: $BackupPath"
    }
    $rows = $raw | ConvertFrom-Json
    if ($rows -isnot [System.Collections.IEnumerable]) {
        $rows = @($rows)
    }

    $enabled = @()
    foreach ($row in $rows) {
        if ([string]$row.State -eq "Disabled") {
            continue
        }
        if ($WhatIf) {
            Write-Output ("[WhatIf] Enable-ScheduledTask {0}" -f $row.TaskName)
            continue
        }
        try {
            Enable-ScheduledTask -TaskName $row.TaskName -TaskPath $row.TaskPath | Out-Null
            $enabled += [string]$row.TaskName
        } catch {
            Write-Warning ("Enable failed: {0} ({1})" -f $row.TaskName, $_.Exception.Message)
        }
    }

    Write-Output ("mode=restore enabled_now={0} backup={1}" -f $enabled.Count, $BackupPath)
}

if ($Mode -eq "Quiet") {
    Set-QuietMode
} else {
    Restore-QuietBackup
}
