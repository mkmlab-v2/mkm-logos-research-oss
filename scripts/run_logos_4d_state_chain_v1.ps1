[CmdletBinding()]
param(
    [switch]$PreferFred,
    [switch]$SkipFragilityChain,
    [switch]$SkipExodusSourceFetch,
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
    Write-Host "[logos-4d-chain] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit=$LASTEXITCODE)"
    }
}

$fragilityChain = Join-Path $PSScriptRoot "run_fragility_macro_risk_chain_v1.ps1"
$exodusSourceScript = Join-Path $PSScriptRoot "build_exodus_pressure_source_v1.py"
$exodusScript = Join-Path $PSScriptRoot "build_exodus_pressure_v1.py"
$logosScript = Join-Path $PSScriptRoot "build_logos_4d_state_v1.py"

foreach ($path in @($exodusSourceScript, $exodusScript, $logosScript)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required file not found: $path"
    }
}
if (-not $SkipFragilityChain -and -not (Test-Path -LiteralPath $fragilityChain)) {
    throw "Required file not found: $fragilityChain"
}

if (-not $SkipFragilityChain) {
    Invoke-Step -Name "run fragility macro risk chain" -Action {
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $fragilityChain, "-AssetScope", $AssetScope, "-Horizon", $Horizon)
        if ($PreferFred) { $args += "-PreferFred" }
        powershell @args
    }
}
else {
    Write-Host "[logos-4d-chain] skip fragility macro risk chain (SkipFragilityChain; caller already refreshed Y/smoke)"
}

if (-not $SkipExodusSourceFetch) {
    Invoke-Step -Name "build exodus pressure source v1 (public APIs)" -Action {
        py $exodusSourceScript
    }
}
else {
    Write-Host "[logos-4d-chain] skip build exodus pressure source v1 (SkipExodusSourceFetch)"
}

Invoke-Step -Name "build exodus pressure v1" -Action {
    py $exodusScript
}

Invoke-Step -Name "build logos 4d state v1" -Action {
    py $logosScript
}

$exodusArtifact = Join-Path $repoRoot "docs\final\artifacts\exodus_pressure_v1_latest.json"
$logosArtifact = Join-Path $repoRoot "docs\final\artifacts\logos_4d_state_v1_latest.json"
Write-Host "[logos-4d-chain] PASS"
Write-Host "[logos-4d-chain] exodus=$exodusArtifact"
Write-Host "[logos-4d-chain] logos4d=$logosArtifact"

