<#
.SYNOPSIS
  Write todo_queue_latest.json from mkm_trackc_plan_orchestrator_bridge_v1.json (Track C business plan SSOT link).

.DESCRIPTION
  Does not parse the Markdown plan — edits the bridge JSON when milestones change. Then run the orchestrator poll (or register a scheduled task).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$py = Join-Path $WorkspaceRoot "scripts\apply_trackc_plan_bridge_to_queue_v1.py"
if (-not (Test-Path -LiteralPath $py)) { throw "Not found: $py" }

$args = @("--workspace-root", $WorkspaceRoot)
if ($DryRun) { $args += "--dry-run" }

& py $py @args
exit $LASTEXITCODE
