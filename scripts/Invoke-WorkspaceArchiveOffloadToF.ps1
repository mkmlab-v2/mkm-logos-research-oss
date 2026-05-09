<# 
.SYNOPSIS
  Offload old workspace files to F:\workspace_archive\auto_offload and optionally remove source files.

.DESCRIPTION
  Targets:
  - tmp: files older than 14 days
  - logs: files older than 7 days
  - reports: files older than 14 days, excluding *latest*

  Default mode is dry-run. Use -Apply to move files.
#>
param(
    [switch]$Apply,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$ArchiveRoot = "F:\workspace_archive\auto_offload",
    [int]$TmpDays = 14,
    [int]$LogDays = 7,
    [int]$ReportDays = 14
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    throw "Workspace root not found: $WorkspaceRoot"
}
if (-not (Test-Path -LiteralPath "F:\")) {
    throw "F drive not found."
}

New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null

$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runRoot = Join-Path $ArchiveRoot $runStamp
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null

$jobs = @(
    @{
        Name = "tmp_older${TmpDays}d"
        Src = (Join-Path $WorkspaceRoot "tmp")
        Days = $TmpDays
        Exclude = @()
    },
    @{
        Name = "logs_older${LogDays}d"
        Src = (Join-Path $WorkspaceRoot "logs")
        Days = $LogDays
        Exclude = @()
    },
    @{
        Name = "reports_older${ReportDays}d"
        Src = (Join-Path $WorkspaceRoot "reports")
        Days = $ReportDays
        Exclude = @("*latest*")
    }
)

$summary = @()

foreach ($job in $jobs) {
    if (-not (Test-Path -LiteralPath $job.Src)) {
        $summary += [PSCustomObject]@{
            bucket = $job.Name
            source = $job.Src
            archive = $null
            mode = if ($Apply) { "apply" } else { "dry_run" }
            robocopy_exit = -1
            note = "source_missing"
        }
        continue
    }

    $dst = Join-Path $runRoot $job.Name
    New-Item -ItemType Directory -Path $dst -Force | Out-Null

    $args = @(
        $job.Src,
        $dst,
        "/E",
        "/R:1",
        "/W:1",
        "/MINAGE:$($job.Days)",
        "/NFL",
        "/NDL",
        "/NP",
        "/NJH",
        "/NJS"
    )

    if ($Apply) {
        $args += "/MOV"
    }
    else {
        $args += "/L"
    }

    if ($job.Exclude.Count -gt 0) {
        $args += "/XF"
        $args += $job.Exclude
    }

    robocopy @args | Out-Null
    $code = $LASTEXITCODE

    $dstBytes = (
        Get-ChildItem -LiteralPath $dst -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum
    ).Sum

    $summary += [PSCustomObject]@{
        bucket = $job.Name
        source = $job.Src
        archive = $dst
        mode = if ($Apply) { "apply" } else { "dry_run" }
        robocopy_exit = $code
        archived_gb = [Math]::Round(($dstBytes / 1GB), 3)
    }
}

$reportRoot = Join-Path $WorkspaceRoot "reports"
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$summaryPath = Join-Path $reportRoot "workspace_archive_offload_latest.json"

$result = [PSCustomObject]@{
    schema = "workspace_archive_offload_v1"
    generated_at = (Get-Date).ToString("o")
    run_root = $runRoot
    mode = if ($Apply) { "apply" } else { "dry_run" }
    summary = $summary
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Run root: $runRoot"
Write-Host "Summary: $summaryPath"
$summary | Format-Table -AutoSize
