#Requires -Version 5.1
<#
.SYNOPSIS
  BLS May-2026 unemployment general_prophecy: preflight, optional FRED probe, resolve, Brier (B-track).

.DESCRIPTION
  Default -PatrolOnly: no registry write. Use -Outcome true|false after BLS release (~first Friday of month).

.EXAMPLE
  powershell -File scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 -PatrolOnly

.EXAMPLE
  powershell -File scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 -Outcome false -Notes "BLS May 2026 SA unrate 4.2%"
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("true", "false")]
    [string]$Outcome = "",
    [string]$Notes = "BLS May 2026 SA unemployment vs 4.3% threshold (general_prophecy B-rail).",
    [string]$EvidenceUri = "https://www.bls.gov/news.release/empsit.nr0.htm",
    [switch]$PatrolOnly,
    [switch]$SkipMarketRefresh,
    [switch]$SkipProbe,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$Registry = "docs\final\artifacts\general_prophecy_latest.json"
Push-Location $WorkspaceRoot
try {
    & py scripts/check_general_prophecy_bls_unrate_resolve_preflight_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SkipProbe) {
        & py scripts/probe_bls_unemployment_may2026_v1.py
        $probeExit = $LASTEXITCODE
        if (Test-Path -LiteralPath "reports\bls_unemployment_probe_v1_latest.json") {
            $probe = Get-Content -LiteralPath "reports\bls_unemployment_probe_v1_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
            Write-Host ("probe: status={0} suggested={1} ready={2}" -f $probe.status, $probe.suggested_outcome, $probe.may_2026_release_ready) -ForegroundColor Cyan
        }
        if ($PatrolOnly -and $probeExit -ne 0) {
            Write-Host "Patrol: May 2026 UNRATE not in FRED yet (normal before release)." -ForegroundColor DarkYellow
        }
    }

    if (-not $SkipMarketRefresh) {
        & py scripts/fetch_kospi_yfinance_csv.py
        & py scripts/fetch_nasdaq_yfinance_csv.py
        & py scripts/fetch_brent_yfinance_csv.py
        & py scripts/fetch_vix_yfinance_csv.py
    }

    if ($PatrolOnly -or [string]::IsNullOrWhiteSpace($Outcome)) {
        & py scripts/eval_general_prophecy_brier_score.py --ece-bins 10
        & py scripts/build_general_prophecy_brief.py
        Write-Host "PatrolOnly: registry unchanged. After BLS release: -Outcome true|false" -ForegroundColor Green
        exit 0
    }

    if ($WhatIfOnly) {
        Write-Host "WhatIfOnly: would resolve seed.macro.us_bls_unrate_gt_43_20260606 -> $Outcome" -ForegroundColor Yellow
        exit 0
    }

    $resolveArgs = @(
        "scripts/resolve_general_prophecy_question_v1.py",
        "-i", $Registry,
        "--in-place",
        "--question-id", "seed.macro.us_bls_unrate_gt_43_20260606",
        "--resolution-status", "resolved",
        "--outcome", $Outcome,
        "--notes", $Notes,
        "--evidence-uri", $EvidenceUri
    )
    & py @resolveArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & py scripts/eval_general_prophecy_brier_score.py --ece-bins 10
    & py scripts/build_general_prophecy_brief.py
    & py scripts/build_general_prophecy_explainable_v1.py
    Write-Host "BLS resolve chain OK. Track A / live unchanged (B-rail)." -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
