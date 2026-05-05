<#
.SYNOPSIS
  MKM-Orchestrator poll wrapper — delegates to mkm_orchestrator_poll_v1.py (PS 5.1-safe JSON).

.DESCRIPTION
  For full behavior see scripts/mkm_orchestrator_poll_v1.py. Queue: todo_queue_v1 JSON.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$QueuePath = "",
    [switch]$DryRun,
    [int]$MaxTasksPerInvocation = 1,
    [switch]$SkipLock,
    [switch]$SkipHeavy,
    [switch]$HeavyOnly
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
$py = Join-Path $root "scripts\mkm_orchestrator_poll_v1.py"
if (-not (Test-Path -LiteralPath $py)) { throw "Not found: $py" }

$args = @("--workspace-root", $root, "--max-tasks", "$MaxTasksPerInvocation")
if ($QueuePath) { $args += @("--queue", $QueuePath) }
if ($DryRun) { $args += "--dry-run" }
if ($SkipLock) { $args += "--skip-lock" }
if ($SkipHeavy) { $args += "--skip-heavy" }
if ($HeavyOnly) { $args += "--heavy-only" }

& py $py @args
exit $LASTEXITCODE
