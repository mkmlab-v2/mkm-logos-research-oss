# COMP parallel round: verify + pointer + OOV bench + corpus probe + closure
param(
    [switch]$SkipAbRefresh
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$failed = @()

if (-not $SkipAbRefresh) {
    py scripts/comp_atom01_ab_refresh_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "ab-refresh" }
}

py scripts/comp_atom02_pointer_hit_refresh_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "pointer-refresh" }

py scripts/comp_atom02_oov_policy_bench_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "oov-bench" }

py scripts/comp_corpus01_readiness_v1.py
# exit 2 = blocked paths expected
if ($LASTEXITCODE -eq 1) { $failed += "corpus-readiness" }

py scripts/comp_atom_track_b_closure_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "closure" }

py scripts/comp_atom_research_manifest_refresh_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "manifest" }

py scripts/run_ultra_compression_promotion_sweep_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "sweep" }

py scripts/comp_atom04_promotion_dryrun_refresh_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "dryrun" }

Write-Host "== pytest COMP bundle ==" -ForegroundColor Cyan
py -m pytest tests/test_compression_profile_v1.py tests/test_compression_token_api_v2_stub.py tests/test_gematria_4d_bridge.py tests/test_ultra_compression_promotion_sweep_v1.py tests/test_sasang_cross_ref_draft.py -q
if ($LASTEXITCODE -ne 0) { $failed += "pytest" }

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "COMP parallel round OK" -ForegroundColor Green
exit 0
