# Full Majung push: E2E demo chain + forward daily (light) + Track C dashboard + evidence pack E1-E4.

param(
    [switch]$SkipE2e,
    [switch]$SkipForwardDaily,
    [switch]$SkipDashboard,
    [switch]$IncludeFragilityChain
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    if (-not $SkipE2e) {
        Write-Host "[majung-push] === E2E demo chain ===" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "Run-MajungE2eDemoChain_v1.ps1")
        if ($LASTEXITCODE -ne 0) { throw "E2E chain failed exit=$LASTEXITCODE" }
    }

    if (-not $SkipForwardDaily) {
        Write-Host "[majung-push] === macro forward daily (light) ===" -ForegroundColor Cyan
        $fwdArgs = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", (Join-Path $PSScriptRoot "run_macro_risk_forward_daily_chain_v1.ps1")
        )
        if (-not $IncludeFragilityChain) {
            $fwdArgs += "-SkipFragilityChain"
        }
        & powershell @fwdArgs
        if ($LASTEXITCODE -ne 0) { throw "forward daily failed exit=$LASTEXITCODE" }
    }

    if (-not $SkipDashboard) {
        $dashScript = Join-Path $PSScriptRoot "build_mkm_trackc_ops_dashboard_v1.py"
        if (Test-Path -LiteralPath $dashScript) {
            Write-Host "[majung-push] === Track C ops dashboard ===" -ForegroundColor Cyan
            py $dashScript
            if ($LASTEXITCODE -ne 0) { throw "dashboard build failed exit=$LASTEXITCODE" }
        }
    }

    Write-Host "[majung-push] === commercial package pointer ===" -ForegroundColor Cyan
    py scripts/build_mkm_trackc_commercial_package.py
    if ($LASTEXITCODE -ne 0) { throw "commercial package failed exit=$LASTEXITCODE" }

    Write-Host "[majung-push] === evidence pack E1-E4 + E2E ===" -ForegroundColor Cyan
    py scripts/build_majung_submission_evidence_pack_v1.py
    $packExit = $LASTEXITCODE
    if ($packExit -ne 0 -and $packExit -ne 2) {
        throw "evidence pack failed exit=$packExit"
    }

    Write-Host ""
    Write-Host "[majung-push] DONE" -ForegroundColor Green
    Write-Host "  docs/final/artifacts/majung_e2e_demo_latest.md"
    Write-Host "  docs/final/artifacts/majung_submission_evidence_pack_manifest_latest.json"
    Write-Host "  reports/majung_submission_evidence_pack_v1/INDEX.md  (+ copied E1-E4)"
    Write-Host "  docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md (if built)"
    if ($packExit -eq 2) {
        Write-Host "[majung-push] WARN: some required evidence files missing (see manifest)" -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}
