[CmdletBinding()]
param(
    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "[fragility-chain] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit=$LASTEXITCODE)"
    }
}

$inputsScript = Join-Path $PSScriptRoot "build_macro_fragility_inputs_v1.py"
$bootstrapScript = Join-Path $PSScriptRoot "bootstrap_fragility_quaternion_history_v1.py"
$fragilityScript = Join-Path $PSScriptRoot "build_fragility_composite_v1.py"
$offlineApiScript = Join-Path $PSScriptRoot "build_macro_risk_warning_api_offline_snapshot_v1.py"
$policyScript = Join-Path $PSScriptRoot "apply_macro_risk_decision_policy.py"

foreach ($script in @($inputsScript, $bootstrapScript, $fragilityScript, $offlineApiScript, $policyScript)) {
    if (-not (Test-Path -LiteralPath $script)) {
        throw "Required script not found: $script"
    }
}

Invoke-Step -Name "build macro fragility inputs" -Action {
    $args = @($inputsScript)
    if ($PreferFred) { $args += "--prefer-fred" }
    py @args
}

Invoke-Step -Name "bootstrap quaternion history" -Action {
    py $bootstrapScript
}

Invoke-Step -Name "build fragility composite v1" -Action {
    py $fragilityScript
}

Invoke-Step -Name "build macro risk offline snapshot" -Action {
    py $offlineApiScript --asset-scope $AssetScope --horizon $Horizon --include-evidence-ref
}

Invoke-Step -Name "apply policy binding" -Action {
    py $policyScript
}

$fragilityArtifact = Join-Path $repoRoot "docs\final\artifacts\fragility_composite_v1_latest.json"
$responseArtifact = Join-Path $repoRoot "docs\final\artifacts\macro_risk_warning_api_smoke_latest.json"
$bindingArtifact = Join-Path $repoRoot "docs\final\artifacts\macro_risk_warning_policy_binding_latest.json"

Write-Host "[fragility-chain] PASS"
Write-Host "[fragility-chain] fragility=$fragilityArtifact"
Write-Host "[fragility-chain] response=$responseArtifact"
Write-Host "[fragility-chain] binding=$bindingArtifact"
