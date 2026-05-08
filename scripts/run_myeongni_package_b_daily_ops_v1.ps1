<#
.SYNOPSIS
  Daily MKM Myeongni package_b ops: run chain, append one-line JSON audit log.

.DESCRIPTION
  B-track pipeline health / reproducibility — NOT KOSPI outcome calibration.
  Default runs balanced mode once (fast). Use -IncludePytest for regression guard
  or -Mode both for full dual-profile refresh (slower).

.PARAMETER Mode
  balanced | attack | both — passed to run_myeongni_package_b_chain_v1.py

.PARAMETER IncludePytest
  After successful chain, run focused pytest (same scope as smoke).

.PARAMETER DryRun
  Print actions only.
#>
param(
    [ValidateSet("balanced", "attack", "both")]
    [string]$Mode = "balanced",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$IncludePytest,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$logDir = Join-Path $WorkspaceRoot "reports"
$logPath = Join-Path $logDir "myeongni_package_b_daily_ops_log.jsonl"
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$chainScript = Join-Path $WorkspaceRoot "scripts\run_myeongni_package_b_chain_v1.py"
if (-not (Test-Path -LiteralPath $chainScript)) {
    throw "Chain script not found: $chainScript"
}

$exitChain = 1
$exitPytest = $null

if ($DryRun) {
    Write-Host "[DryRun] py `"$chainScript`" --mode $Mode"
    if ($IncludePytest) {
        Write-Host "[DryRun] pytest tests\test_run_myeongni_package_b_chain_v1.py tests\test_build_mkm_myeongni_response_v2.py -q"
    }
    exit 0
}

& py $chainScript --mode $Mode
$exitChain = $LASTEXITCODE

if ($IncludePytest -and $exitChain -eq 0) {
    & py -m pytest `
        "tests\test_run_myeongni_package_b_chain_v1.py" `
        "tests\test_build_mkm_myeongni_response_v2.py" -q
    $exitPytest = $LASTEXITCODE
}

$summaryPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_myeongni_package_b_chain_summary_latest.json"
$recPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_myeongni_profile_switch_recommendation_latest.json"
$worksheetPath = Join-Path $WorkspaceRoot "docs\final\artifacts\myeongni_manual_signoff_worksheet_latest.json"
$summaryPresent = Test-Path -LiteralPath $summaryPath
$recPresent = Test-Path -LiteralPath $recPath
$worksheetExit = $null

if ($exitChain -eq 0) {
    & py "scripts\build_myeongni_manual_signoff_worksheet_v1.py"
    $worksheetExit = $LASTEXITCODE
}
$worksheetPresent = (Test-Path -LiteralPath $worksheetPath) -and ($worksheetExit -eq 0)

$record = [ordered]@{
    ts_utc          = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    task            = "myeongni_package_b_daily_ops_v1"
    mode            = $Mode
    chain_exit_code = $exitChain
    pytest_exit_code = $exitPytest
    artifacts       = @{
        chain_summary_present            = $summaryPresent
        profile_recommendation_present   = $recPresent
        signoff_worksheet_present        = $worksheetPresent
    }
    note            = "pipeline_health_not_price_skill"
}

$line = ($record | ConvertTo-Json -Compress -Depth 6)
Add-Content -LiteralPath $logPath -Value $line -Encoding utf8

if ($exitChain -ne 0) {
    exit $exitChain
}
if ($null -ne $exitPytest -and $exitPytest -ne 0) {
    exit $exitPytest
}
if ($null -ne $worksheetExit -and $worksheetExit -ne 0) {
    exit $worksheetExit
}
exit 0
