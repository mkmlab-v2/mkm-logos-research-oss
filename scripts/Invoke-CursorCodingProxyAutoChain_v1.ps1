# Auto chain: backup → compress bench → agent-extract gate → adapter plan → optional stub smoke
param(
    [switch]$SkipStubSmoke,
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:COMPRESSION_HARDENING_CONFIG_PATH = "data/btrack/compression_coding_proxy_hardening_v1.json"

if (-not $SkipBackup) {
    Write-Host "[1/7] backup manifest" -ForegroundColor Cyan
    py scripts/build_local_dev_backup_manifest_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[2/7] proxy-aligned compress bench" -ForegroundColor Cyan
py scripts/run_cursor_coding_compress_bench_v1.py --proxy-aligned
$benchRc = $LASTEXITCODE
if ($benchRc -ne 0 -and $benchRc -ne 2) { exit $benchRc }

Write-Host "[3/7] agent-extract structural gate" -ForegroundColor Cyan
py scripts/sandbox/build_cursor_coding_agent_extract_input_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/run_cursor_coding_agent_extract_gate_v1.py
$extractRc = $LASTEXITCODE
if ($extractRc -ne 0) {
    Write-Host "EXTRACT_GATE FAIL (expected until must_keep tuning) — see reports/cursor_coding_agent_extract_gate_v1_latest.json" -ForegroundColor Yellow
}

Write-Host "[4/7] adapter plan" -ForegroundColor Cyan
py scripts/build_local_cursor_compress_adapter_v1.py --write-plan
$planRc = $LASTEXITCODE
if ($planRc -ne 0 -and $planRc -ne 2) { exit $planRc }

Write-Host "[5/7] chat shim plan" -ForegroundColor Cyan
py scripts/build_local_cursor_chat_shim_v1.py --write-plan
$shimPlanRc = $LASTEXITCODE
if ($shimPlanRc -ne 0 -and $shimPlanRc -ne 2) { exit $shimPlanRc }

Write-Host "[6/7] chat shim compress A/B bench (n40)" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ChatShimCompressAbBench_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipStubSmoke) {
    Write-Host "[7/7] stub + shim smoke skipped" -ForegroundColor DarkGray
    if ($extractRc -ne 0) { exit 1 }
    exit 0
}

Write-Host "[7/7] stub smoke" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LocalCursorCompressProxySmoke_v1.ps1
$smokeRc = $LASTEXITCODE
if ($smokeRc -ne 0) { exit $smokeRc }

Write-Host "[+] chat shim dry-run smoke" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LocalCursorChatShimSmoke_v1.ps1
$shimSmokeRc = $LASTEXITCODE
if ($extractRc -ne 0) { exit 1 }
exit $shimSmokeRc
