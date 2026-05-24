# DF-P2-02 (Lane B) + DF-P2-04 (Lane D) parallel bundle
param(
    [switch]$SkipMsPasteReadiness,
    [switch]$SkipSingularity,
    [switch]$SkipGraphExpand,
    [int]$SingularityMaxRows = 800,
    [int]$GraphExpandBatchSize = 500
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failed = @()

if (-not $SkipMsPasteReadiness) {
    Write-Host "== MS-PASTE readiness (warn-only) ==" -ForegroundColor Yellow
    if (Test-Path "scripts/Invoke-MsRq019PastePackReadiness_v1.ps1") {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "warn: MS-PASTE readiness exit $LASTEXITCODE" -ForegroundColor DarkYellow
        }
    }
}

$jobs = @()
if (-not $SkipSingularity) {
    $jobs += @{
        Name = "DF-P2-02"
        Script = "py scripts/run_logos_corpus_regime_singularity_report_v1.py --max-rows $SingularityMaxRows"
    }
}
if (-not $SkipGraphExpand) {
    $jobs += @{
        Name = "DF-P2-04"
        Script = "py scripts/run_logos_graph_expand_batch_v1.py --batch-size $GraphExpandBatchSize"
    }
}

foreach ($j in $jobs) {
    Write-Host "== $($j.Name) ==" -ForegroundColor Cyan
    Invoke-Expression $j.Script
    if ($LASTEXITCODE -ne 0) { $failed += $j.Name }
}

Write-Host "== DF-P2-02/04 pytest ==" -ForegroundColor Cyan
py -m pytest tests/test_run_logos_corpus_regime_singularity_report_v1.py tests/test_run_logos_graph_expand_batch_v1.py -q
if ($LASTEXITCODE -ne 0) { $failed += "pytest" }

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "P2 Lane B+D OK" -ForegroundColor Green
exit 0
