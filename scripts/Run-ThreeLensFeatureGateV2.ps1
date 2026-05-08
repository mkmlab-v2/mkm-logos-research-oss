[CmdletBinding()]
param(
    [string]$PythonExe = "py",
    [string]$FusionOutputJson = "docs/final/artifacts/three_lens_fusion_coordinator_v1_latest.json",
    [string]$GateOutputJson = "docs/final/artifacts/three_lens_feature_gate_v2_latest.json",
    [double]$HoldRiskCut = 0.75,
    [double]$WatchRiskCut = 0.58,
    [double]$GoOpportunityCut = 0.62
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

Write-Host "[ThreeLensV2] repo root: $RepoRoot"
Write-Host "[ThreeLensV2] step 1/2: build fusion artifact"
& $PythonExe "scripts/build_three_lens_fusion_coordinator_v1.py" `
  "--output-json" $FusionOutputJson
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_fusion_coordinator_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensV2] step 2/3: build conditional GO market check"
& $PythonExe "scripts/build_conditional_go_market_check_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_conditional_go_market_check_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensV2] step 3/3: evaluate feature gate v2"
& $PythonExe "scripts/check_three_lens_feature_gate_v2.py" `
  "--input-json" $FusionOutputJson `
  "--output-json" $GateOutputJson `
  "--hold-risk-cut" $HoldRiskCut `
  "--watch-risk-cut" $WatchRiskCut `
  "--go-opportunity-cut" $GoOpportunityCut
if ($LASTEXITCODE -ne 0) {
    throw "check_three_lens_feature_gate_v2.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensV2] done"
