#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly web_ops chain: full bundle → ops_memory web_ops overlay → optional retrieval bench.

.DESCRIPTION
  [HYPO] B-track. After gate/health JSON refresh, merges JSON-slice pins into
  storage/meta/mkm_ops_memory_index_v1.json for --lane web_ops resume inject.

.EXAMPLE
  pwsh -File scripts/Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1
  pwsh -File scripts/Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1 -SkipLiveCdp -SkipRetrievalBench
  pwsh -File scripts/Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1 -IncludeLargeScaleBenchSmoke
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipLiveCdp,
    [switch]$SkipOpsMemoryOverlay,
    [switch]$SkipRetrievalBench,
    [switch]$IncludeLargeScaleBenchSmoke,
    [switch]$NoSeedBaselines,
    [switch]$RequireDualAlignment,
    [switch]$FailOnPointerDrift
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$bundle = Join-Path $WorkspaceRoot "scripts\Run-WebOpsRegimeFullBundle_v1.ps1"
if (-not (Test-Path -LiteralPath $bundle)) { throw "Missing: $bundle" }

$bundleArgs = @()
if ($SkipLiveCdp) { $bundleArgs += "--skip-live-cdp" }
if ($NoSeedBaselines) { $bundleArgs += "--no-seed-baselines" }
if ($RequireDualAlignment) { $bundleArgs += "--require-dual-alignment" }
if ($FailOnPointerDrift) { $bundleArgs += "--fail-on-pointer-drift" }

Write-Host "[web_ops_weekly] full bundle..." -ForegroundColor Cyan
& $bundle @bundleArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[web_ops_weekly] bundle failed — skip overlay" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

if (-not $SkipOpsMemoryOverlay) {
    Write-Host "[web_ops_weekly] ops_memory web_ops overlay..." -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\build_mkm_ops_memory_web_ops_overlay_v1.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipRetrievalBench) {
    Write-Host "[web_ops_weekly] retrieval bench (n=20)..." -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\bench_mkm_ops_memory_web_ops_retrieval_v1.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($IncludeLargeScaleBenchSmoke) {
    Write-Host "[web_ops_weekly] large-scale pinset bench smoke (n=50, sample 8)..." -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\bench_mkm_ops_memory_large_scale_v1.py") `
        --smoke --sample-scenarios-in-out 8
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: Invoke-WebOpsRegimeWeeklyRoutine_v1 completed"
exit 0
