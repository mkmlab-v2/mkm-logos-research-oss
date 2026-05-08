[CmdletBinding()]
param(
    [string]$PythonExe = "py",
    [string]$PolicyJson = "docs/final/artifacts/three_lens_staged_inclusion_policy_v1.json",
    [string]$StatusOutJson = "docs/final/artifacts/three_lens_staged_inclusion_status_latest.json",
    [string]$FusionOutJson = "docs/final/artifacts/three_lens_fusion_coordinator_v1_latest.json",
    [string]$GateOutJson = "docs/final/artifacts/three_lens_feature_gate_v2_latest.json",
    [double]$HoldRiskCut = 0.75,
    [double]$WatchRiskCut = 0.58,
    [double]$GoOpportunityCut = 0.62,
    [switch]$SkipMkmlifeGuardrailDaily
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

Write-Host "[ThreeLensStagedDaily] repo root: $RepoRoot"

Write-Host "[ThreeLensStagedDaily] step 1/3: staged inclusion status"
& $PythonExe "scripts/build_three_lens_staged_inclusion_status_v1.py" `
  "--policy-json" $PolicyJson `
  "--output-json" $StatusOutJson
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_staged_inclusion_status_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 2/3: build fusion coordinator"
& $PythonExe "scripts/build_three_lens_fusion_coordinator_v1.py" `
  "--output-json" $FusionOutJson
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_fusion_coordinator_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 3/8: build external intel snapshot"
& $PythonExe "scripts/build_three_lens_external_intel_snapshot_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_external_intel_snapshot_v1.py failed with exit code $LASTEXITCODE"
}

if (-not $SkipMkmlifeGuardrailDaily) {
    Write-Host "[ThreeLensStagedDaily] step 4/9: run mkmlife guardrail redteam daily gate"
    & "scripts/Invoke-MkmlifeGuardrailRedteamDaily.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Invoke-MkmlifeGuardrailRedteamDaily.ps1 failed with exit code $LASTEXITCODE"
    }
} else {
    Write-Host "[ThreeLensStagedDaily] step 4/9: mkmlife guardrail redteam daily gate skipped"
}

Write-Host "[ThreeLensStagedDaily] step 5/11: build conditional GO market inputs"
& $PythonExe "scripts/build_conditional_go_market_inputs_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_conditional_go_market_inputs_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 6/11: build conditional GO market check"
& $PythonExe "scripts/build_conditional_go_market_check_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_conditional_go_market_check_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 7/11: evaluate feature gate v2"
& $PythonExe "scripts/check_three_lens_feature_gate_v2.py" `
  "--input-json" $FusionOutJson `
  "--output-json" $GateOutJson `
  "--policy-json" $PolicyJson `
  "--require-external-intel" `
  "--hold-risk-cut" $HoldRiskCut `
  "--watch-risk-cut" $WatchRiskCut `
  "--go-opportunity-cut" $GoOpportunityCut
if ($LASTEXITCODE -ne 0) {
    throw "check_three_lens_feature_gate_v2.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 8/11: build coordinator decision pack"
& $PythonExe "scripts/build_three_lens_coordinator_decision_pack_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_coordinator_decision_pack_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 9/11: build solution planner"
& $PythonExe "scripts/build_three_lens_solution_planner_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_solution_planner_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 10/11: build evidence trace"
& $PythonExe "scripts/build_three_lens_evidence_trace_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "build_three_lens_evidence_trace_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] step 11/11: append shadow history"
& $PythonExe "scripts/append_three_lens_shadow_history_v1.py"
if ($LASTEXITCODE -ne 0) {
    throw "append_three_lens_shadow_history_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[ThreeLensStagedDaily] done"
