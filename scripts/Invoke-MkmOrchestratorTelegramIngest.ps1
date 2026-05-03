param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$py = Join-Path $WorkspaceRoot "scripts\mkm_orchestrator_telegram_v1.py"
if (-not (Test-Path -LiteralPath $py)) { throw "Not found: $py" }

$args = @("ingest", "--workspace-root", $WorkspaceRoot)
if ($DryRun) { $args += "--dry-run" }

& py $py @args
exit $LASTEXITCODE
