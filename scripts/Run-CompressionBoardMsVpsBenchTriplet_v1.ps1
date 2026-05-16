# RQ-017: Run 3 VPS L1 benches on vps-mkmlife, pull artifacts, aggregate triplet.
# Prereq: SSH host alias vps-mkmlife, repo at /opt/mkm-destiny-ai-41e38ec6, stub :8010 healthy.

param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$RemoteRepo = "/opt/mkm-destiny-ai-41e38ec6",
    [int]$RunCount = 3
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $root

$benchCmd = "cd $RemoteRepo && BASE_URL=http://127.0.0.1:8010 bash scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh"
for ($i = 1; $i -le $RunCount; $i++) {
    Write-Host "=== VPS bench $i/$RunCount ===" -ForegroundColor Cyan
    ssh -o BatchMode=yes $VpsHost $benchCmd
    if ($LASTEXITCODE -ne 0) { throw "VPS bench run $i failed: $LASTEXITCODE" }
}

New-Item -ItemType Directory -Force -Path (Join-Path $root "docs\final\artifacts\bench_runs") | Out-Null
scp "${VpsHost}:${RemoteRepo}/docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json" `
    (Join-Path $root "docs\final\artifacts\bench_l1_api_load_summary_vps_latest.json")
$remoteGlob = "${RemoteRepo}/docs/final/artifacts/bench_runs/bench_l1_api_load_vps_*.json"
scp "${VpsHost}:${remoteGlob}" (Join-Path $root "docs\final\artifacts\bench_runs\")
if ($LASTEXITCODE -ne 0) { Write-Warning "Some run files may not have copied; check bench_runs/" }

py (Join-Path $root "scripts\build_compression_board_ms_vps_bench_triplet_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py (Join-Path $root "scripts\build_compression_board_ms_correlation_report_v1.py")
exit $LASTEXITCODE
