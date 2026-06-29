# Job four-slot showroom publish — delegates to UTF-8 safe Python runner.
param(
    [switch]$DryRun,
    [switch]$SkipDeploy,
    [switch]$SkipKv,
    [switch]$SkipSmoke,
    [switch]$SkipChain
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }
Set-Location $root

$pyArgs = @("-3", "scripts/run_logos_job_four_slot_showroom_publish_v1.py")
if ($SkipChain) { $pyArgs += "--skip-chain" }
if ($SkipDeploy) { $pyArgs += "--skip-deploy" }
if ($SkipKv) { $pyArgs += "--skip-kv" }
if ($SkipSmoke) { $pyArgs += "--skip-smoke" }
if ($DryRun) { $pyArgs += "--dry-run" }

& py @pyArgs
exit $LASTEXITCODE
