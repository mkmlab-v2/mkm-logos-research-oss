<#
.SYNOPSIS
  One-click weekly fusion wrapper for Myeongni + Sasang market timeline (B-track).

.DESCRIPTION
  Runs the recommended sequence while keeping Track A gating isolated:
  1) Myeongni weekly ops summary wrapper
  2) KOSPI market psychology CSV from yfinance
  3) Sasang DNA + market reasoning
  4) Sasang rule-based response (prod mode)
  5) Sasang response mode guard
  6) (Optional) bio strict comparison rehydrate

  This wrapper is orchestration-only. SSOT remains underlying JSON artifacts.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-MyeongniSasangWeeklyFusion_v1.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-MyeongniSasangWeeklyFusion_v1.ps1 -Include16StateProbe -SkipYFinance
#>
[CmdletBinding()]
param(
    [switch]$Include16StateProbe,
    [switch]$SkipYFinance,
    [switch]$SkipBioRehydrate,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$myeongniWeekly = Join-Path $PSScriptRoot "Run-MyeongniWeeklyOpsSummary_v1.ps1"
$buildMarketPsych = Join-Path $PSScriptRoot "build_market_psychology_kospi_from_yfinance_v1.py"
$sasangReasoning = Join-Path $PSScriptRoot "run_sasang_dna_market_reasoning_v1.py"
$sasangResponse = Join-Path $PSScriptRoot "build_sasang_rule_based_response_v1.py"
$sasangGuard = Join-Path $PSScriptRoot "check_sasang_response_mode_guard_v1.py"
$bioRehydrate = Join-Path $PSScriptRoot "build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py"

$required = @($myeongniWeekly, $sasangReasoning, $sasangResponse, $sasangGuard)
if (-not $SkipYFinance) { $required += $buildMarketPsych }
if (-not $SkipBioRehydrate) { $required += $bioRehydrate }
foreach ($p in $required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Required file not found: $p"
    }
}

$marketPsychCsv = Join-Path $repoRoot "data\market_sasang\market_psychology_kospi_from_yfinance_latest.csv"
$reasoningOut = Join-Path $repoRoot "reports\sasang_dna_market_reasoning_kospi_from_yfinance_latest.json"
$responseJson = Join-Path $repoRoot "reports\sasang_rule_based_response_kospi_from_yfinance_latest.json"
$responseMd = Join-Path $repoRoot "reports\sasang_rule_based_response_kospi_from_yfinance_latest.md"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "[myeongni-sasang-weekly] $Name"
    if ($DryRun) {
        Write-Host "[myeongni-sasang-weekly] DRY_RUN: skipped"
        return
    }
    Set-Location -LiteralPath $repoRoot
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit=$LASTEXITCODE)"
    }
}

$myeongniArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $myeongniWeekly
)
if ($Include16StateProbe) {
    $myeongniArgs += "-Include16StateProbe"
}

Invoke-Step -Name "Run-MyeongniWeeklyOpsSummary_v1.ps1" -Action {
    powershell @myeongniArgs
}

if (-not $SkipYFinance) {
    Invoke-Step -Name "build_market_psychology_kospi_from_yfinance_v1.py" -Action {
        py $buildMarketPsych
    }
}
else {
    Write-Host "[myeongni-sasang-weekly] skip yfinance market psych refresh (SkipYFinance)"
}

if (-not (Test-Path -LiteralPath $marketPsychCsv)) {
    throw "Missing market psychology CSV: $marketPsychCsv"
}

Invoke-Step -Name "run_sasang_dna_market_reasoning_v1.py" -Action {
    py $sasangReasoning --market-psych-csv $marketPsychCsv --output-json $reasoningOut
}

Invoke-Step -Name "build_sasang_rule_based_response_v1.py (prod)" -Action {
    py $sasangResponse --reasoning-json $reasoningOut --output-json $responseJson --output-md $responseMd --response-mode prod
}

Invoke-Step -Name "check_sasang_response_mode_guard_v1.py" -Action {
    py $sasangGuard --response-json $responseJson
}

if (-not $SkipBioRehydrate) {
    Invoke-Step -Name "build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py" -Action {
        py $bioRehydrate
    }
}
else {
    Write-Host "[myeongni-sasang-weekly] skip bio rehydrate (SkipBioRehydrate)"
}

Write-Host "[myeongni-sasang-weekly] PASS"
Write-Host "[myeongni-sasang-weekly] myeongni_summary_md=$repoRoot\reports\myeongni_weekly_ops_summary_latest.md"
Write-Host "[myeongni-sasang-weekly] sasang_reasoning_json=$reasoningOut"
Write-Host "[myeongni-sasang-weekly] sasang_response_json=$responseJson"
Write-Host "[myeongni-sasang-weekly] sasang_guard_json=$repoRoot\reports\sasang_response_mode_guard_latest.json"
