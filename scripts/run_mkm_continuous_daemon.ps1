<#
.SYNOPSIS
  Continuous MKM daemon loop with safe Track C bridge merge + orchestrator poll.

.DESCRIPTION
  Use for live local operation where queue should be refreshed periodically without resetting task lifecycle.
  Bridge merge mode preserves existing task states/history by task_id.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$LoopSeconds = 300,
    [int]$MaxTasksPerInvocation = 4,
    [int]$HeavyEveryCycles = 12,
    [switch]$SkipLock,
    [switch]$OneShot
)

$ErrorActionPreference = "Stop"
$apply = Join-Path $WorkspaceRoot "scripts\apply_trackc_plan_bridge_to_queue_v1.py"
$poll = Join-Path $WorkspaceRoot "scripts\mkm_orchestrator_poll_v1.py"

if (-not (Test-Path -LiteralPath $apply)) { throw "Not found: $apply" }
if (-not (Test-Path -LiteralPath $poll)) { throw "Not found: $poll" }
if ($LoopSeconds -lt 10) { throw "LoopSeconds must be >= 10" }
if ($HeavyEveryCycles -lt 1) { throw "HeavyEveryCycles must be >= 1" }

$cycle = 0
while ($true) {
    $cycle += 1
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "[$ts] [daemon] bridge merge start"
    & py $apply --workspace-root $WorkspaceRoot --merge-existing
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[$ts] [daemon] bridge merge failed: exit=$LASTEXITCODE" -ForegroundColor Yellow
    }

    $args = @("--workspace-root", $WorkspaceRoot, "--max-tasks", "$MaxTasksPerInvocation", "--skip-heavy")
    if ($SkipLock) { $args += "--skip-lock" }

    Write-Host "[$ts] [daemon] quick poll start"
    & py $poll @args
    $pollCode = $LASTEXITCODE
    $ts2 = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "[$ts2] [daemon] quick poll exit=$pollCode"

    # Heavy tasks run on slower cadence to avoid loop overload.
    if (($cycle % $HeavyEveryCycles) -eq 0) {
        $hArgs = @(
            "--workspace-root", $WorkspaceRoot,
            "--max-tasks", "$MaxTasksPerInvocation",
            "--heavy-only"
        )
        if ($SkipLock) { $hArgs += "--skip-lock" }
        $ts3 = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        Write-Host "[$ts3] [daemon] heavy poll start (cycle=$cycle)"
        & py $poll @hArgs
        $hCode = $LASTEXITCODE
        $ts4 = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        Write-Host "[$ts4] [daemon] heavy poll exit=$hCode"
    }

    if ($OneShot) {
        exit $pollCode
    }

    Start-Sleep -Seconds $LoopSeconds
}
