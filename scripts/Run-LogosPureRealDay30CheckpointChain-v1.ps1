param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$TargetUniqueDays = 30,
    [double]$MaxAllowedDelta = 0.15
)

$ErrorActionPreference = "Stop"

$py = "py"
$chain = Join-Path $WorkspaceRoot "scripts\run_logos_pure_real_day30_checkpoint_chain_v1.py"
$outJson = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_pure_real_day30_checkpoint_chain_latest.json"

& $py $chain --target-unique-days $TargetUniqueDays --max-allowed-delta $MaxAllowedDelta --output-json $outJson
$exitCode = $LASTEXITCODE

Write-Output "{`"ok`":true,`"script`":`"Run-LogosPureRealDay30CheckpointChain-v1.ps1`",`"output_json`":`"$outJson`",`"exit_code`":$exitCode}"
exit $exitCode

