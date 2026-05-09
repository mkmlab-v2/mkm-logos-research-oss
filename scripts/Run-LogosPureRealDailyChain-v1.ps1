param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$MaxAllowedDelta = 0.15
)

$ErrorActionPreference = "Stop"

$py = "py"
$chain = Join-Path $WorkspaceRoot "scripts\run_logos_pure_real_collection_chain_v1.py"
$outJson = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_pure_real_collection_chain_latest.json"

& $py $chain --output-json $outJson --max-allowed-delta $MaxAllowedDelta
if ($LASTEXITCODE -ne 0) {
  throw "Run-LogosPureRealDailyChain-v1 failed with exit code $LASTEXITCODE"
}

Write-Output "{`"ok`":true,`"script`":`"Run-LogosPureRealDailyChain-v1.ps1`",`"output_json`":`"$outJson`"}"

