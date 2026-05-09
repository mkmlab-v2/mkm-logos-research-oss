<#
.SYNOPSIS
  Verify default/extended B-Track99 rollup scheduled tasks and print compact status.
#>
[CmdletBinding()]
param(
    [string] $DefaultTaskName = "MKM_BTrack99_Weekly_Rollup",
    [string] $ExtendedTaskName = "MKM_BTrack99_Weekly_Rollup_Extended",
    [string] $JsonOut = ""
)

$ErrorActionPreference = "Stop"

function Get-TaskSummary {
    param([string] $TaskName)
    $lines = schtasks /Query /TN "\$TaskName" /V /FO LIST 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $lines) {
        return [pscustomobject]@{
            TaskName = $TaskName
            Exists = $false
            Status = "MISSING"
            NextRunTime = $null
            Schedule = $null
            Command = $null
        }
    }
    $kv = @{}
    foreach ($line in $lines) {
        if ($line -match "^\s*([^:]+):\s*(.*)$") {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            $kv[$key] = $val
        }
    }
    [pscustomobject]@{
        TaskName = $TaskName
        Exists = $true
        Status = $kv["Status"]
        NextRunTime = $kv["Next Run Time"]
        Schedule = "$($kv["Schedule Type"]) / $($kv["Months"]) / $($kv["Days"]) @ $($kv["Start Time"])"
        Command = $kv["Task To Run"]
    }
}

$rows = @(
    Get-TaskSummary -TaskName $DefaultTaskName
    Get-TaskSummary -TaskName $ExtendedTaskName
)

$rows | Format-Table -AutoSize

if ($JsonOut -ne "") {
    $outObj = [pscustomobject]@{
        schema = "btrack99_rollup_task_status_v1"
        generated_at_utc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        tasks = $rows
    }
    $jsonPath = if ([System.IO.Path]::IsPathRooted($JsonOut)) { $JsonOut } else { Join-Path "C:\workspace" $JsonOut }
    $jsonDir = Split-Path -Parent $jsonPath
    if ($jsonDir -and -not (Test-Path -LiteralPath $jsonDir)) {
        New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
    }
    $outObj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    Write-Host "WROTE: $jsonPath"
}

$missing = @($rows | Where-Object { -not $_.Exists })
if ($missing.Count -gt 0) {
    Write-Host "Missing tasks: $($missing.TaskName -join ', ')" -ForegroundColor Yellow
    exit 2
}

Write-Host "All requested rollup tasks are registered." -ForegroundColor Green
exit 0
