[CmdletBinding()]
param(
    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h",
    [switch]$SkipFragilityChain
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "[forward-daily] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit=$LASTEXITCODE)"
    }
}

$fragilityChain = Join-Path $PSScriptRoot "run_fragility_macro_risk_chain_v1.ps1"
$freezeScript = Join-Path $PSScriptRoot "freeze_macro_risk_forward_preregister_v1.py"
$forwardLogScript = Join-Path $PSScriptRoot "run_macro_risk_forward_log_v1.py"
$weeklyScript = Join-Path $PSScriptRoot "build_macro_risk_forward_weekly_report_v1.py"

foreach ($script in @($freezeScript, $forwardLogScript, $weeklyScript)) {
    if (-not (Test-Path -LiteralPath $script)) {
        throw "Required script not found: $script"
    }
}
if (-not $SkipFragilityChain -and -not (Test-Path -LiteralPath $fragilityChain)) {
    throw "Required script not found: $fragilityChain"
}

if (-not $SkipFragilityChain) {
    Invoke-Step -Name "run fragility macro risk chain" -Action {
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $fragilityChain, "-AssetScope", $AssetScope, "-Horizon", $Horizon)
        if ($PreferFred) { $args += "-PreferFred" }
        powershell @args
    }
}
else {
    Write-Host "[forward-daily] skip fragility macro risk chain (SkipFragilityChain)"
}

Invoke-Step -Name "freeze preregister lock" -Action {
    py $freezeScript
}

Invoke-Step -Name "append forward log row" -Action {
    py $forwardLogScript
}

Invoke-Step -Name "build weekly forward report" -Action {
    py $weeklyScript --window-days 7
}

$preregArtifact = Join-Path $repoRoot "docs\final\artifacts\macro_risk_forward_preregister_lock_latest.json"
$logArtifact = Join-Path $repoRoot "reports\macro_risk\forward\macro_risk_forward_log_v1.jsonl"
$latestArtifact = Join-Path $repoRoot "docs\final\artifacts\macro_risk_forward_log_latest.json"
$weeklyArtifact = Join-Path $repoRoot "docs\final\artifacts\macro_risk_forward_weekly_report_latest.json"

Write-Host "[forward-daily] PASS"
Write-Host "[forward-daily] preregister=$preregArtifact"
Write-Host "[forward-daily] log=$logArtifact"
Write-Host "[forward-daily] latest=$latestArtifact"
Write-Host "[forward-daily] weekly=$weeklyArtifact"

