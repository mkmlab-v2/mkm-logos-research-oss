param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun,
    [switch]$JsonPlan,
    [string]$PlanOut = "",
    [switch]$IncludeCompressionChain
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$pyArgs = @("scripts\run_multilens_p1_production_chain.py")
if ($DryRun) { $pyArgs += "--dry-run" }
if ($JsonPlan) { $pyArgs += "--json-plan" }
if ($PlanOut) { $pyArgs += @("--plan-out", $PlanOut) }
if ($IncludeCompressionChain) { $pyArgs += "--include-compression-chain" }

py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
