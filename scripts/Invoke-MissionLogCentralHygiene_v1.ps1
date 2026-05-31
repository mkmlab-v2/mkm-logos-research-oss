<#
.SYNOPSIS
  MISSION_LOG + CENTRAL hygiene: session cap, optional bulk split, timeline archive.

.DESCRIPTION
  1) rotate_mission_log_sessions_v1.py (default keep 14)
  2) archive_central_timeline_v1.py (default keep 45 rows)
  3) split_mission_log_old_v1.py when MISSION_LOG line count exceeds -SplitLineThreshold
  4) build_mkm_ops_memory_index_v1.py — anchor index rebuild ([HYPO] / research_only)

  Writes reports/mission_log_central_hygiene_latest.json

.PARAMETER DryRun
  Plan only; no file writes.

.PARAMETER SkipSplit
  Never run split_mission_log_old_v1.py.

.PARAMETER SkipCentralArchive
  Skip CENTRAL timeline prune.

.PARAMETER SkipSessionRotate
  Skip session line rotation.
#>
param(
    [switch]$DryRun,
    [switch]$SkipSplit,
    [switch]$SkipCentralArchive,
    [switch]$SkipSessionRotate,
    [switch]$SkipOpsMemoryIndex,
    [int]$SessionMaxKeep = 14,
    [int]$CentralMaxRows = 45,
    [int]$SplitLineThreshold = 320
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
Set-Location -LiteralPath $workspaceRoot

$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$report = @{
    schema = "mission_log_central_hygiene_v1"
    ran_at_utc = $stamp
    dry_run = [bool]$DryRun
    steps = @()
    overall_ok = $true
}

function Invoke-Step {
    param(
        [string]$Name,
        [string[]]$Command
    )
    $step = @{
        name = $Name
        command = ($Command -join " ")
        exit_code = $null
        stdout = $null
        skipped = $false
    }
    if ($DryRun -and $Command -notcontains "--dry-run") {
        $Command = @($Command[0]) + @("--dry-run") + $Command[1..($Command.Length - 1)]
    }
    Write-Host "==> $Name"
    Write-Host ($Command -join " ")
    $out = & $Command[0] $Command[1..($Command.Length - 1)] 2>&1 | Out-String
    $code = $LASTEXITCODE
    $step.exit_code = $code
    $step.stdout = $out.Trim()
    Write-Host $out
    if ($code -ne 0) {
        $script:report.overall_ok = $false
    }
    $script:report.steps += $step
}

if (-not $SkipSessionRotate) {
    Invoke-Step -Name "rotate_sessions" -Command @(
        "py", "scripts/rotate_mission_log_sessions_v1.py", "--max-keep", "$SessionMaxKeep"
    )
}

if (-not $SkipCentralArchive) {
    Invoke-Step -Name "archive_central_timeline" -Command @(
        "py", "scripts/archive_central_timeline_v1.py", "--max-rows", "$CentralMaxRows"
    )
}

if (-not $SkipSplit) {
    $missionLog = Join-Path $workspaceRoot "MISSION_LOG.md"
    $lineCount = 0
    if (Test-Path -LiteralPath $missionLog) {
        $lineCount = (Get-Content -LiteralPath $missionLog | Measure-Object -Line).Lines
    }
    $report.mission_log_lines = $lineCount
    $report.split_line_threshold = $SplitLineThreshold
    if ($lineCount -gt $SplitLineThreshold) {
        Invoke-Step -Name "split_mission_log" -Command @(
            "py", "scripts/split_mission_log_old_v1.py"
        )
    } else {
        $report.steps += @{
            name = "split_mission_log"
            skipped = $true
            reason = "lines=$lineCount threshold=$SplitLineThreshold"
        }
        Write-Host "==> split_mission_log SKIPPED (lines=$lineCount <= $SplitLineThreshold)"
    }
}

if (-not $SkipOpsMemoryIndex) {
    $indexCmd = @("py", "scripts/build_mkm_ops_memory_index_v1.py")
    if ($DryRun) {
        $indexCmd += "--dry-run"
    }
    Invoke-Step -Name "build_ops_memory_index" -Command $indexCmd
}

$reportPath = Join-Path $workspaceRoot "reports/mission_log_central_hygiene_latest.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Host "Report: $reportPath"
Write-Host "overall_ok=$($report.overall_ok)"

if (-not $report.overall_ok) { exit 1 }
exit 0
