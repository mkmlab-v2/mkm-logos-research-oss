# Local dev insulation chain: backup manifest → coding compress bench → adapter plan
param(
    [switch]$DryRunBench,
    [switch]$SkipBench
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[1/3] backup manifest" -ForegroundColor Cyan
py scripts/build_local_dev_backup_manifest_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipBench) {
    Write-Host "[2/3] cursor coding compress bench" -ForegroundColor Cyan
    $benchArgs = @("scripts/run_cursor_coding_compress_bench_v1.py")
    if ($DryRunBench) { $benchArgs += "--dry-run" }
    py @benchArgs
    $benchRc = $LASTEXITCODE
    if ($DryRunBench -and $benchRc -ne 0) { exit $benchRc }
    if (-not $DryRunBench -and $benchRc -ne 0 -and $benchRc -ne 2) { exit $benchRc }
}

Write-Host "[3/3] adapter plan" -ForegroundColor Cyan
py scripts/build_local_cursor_compress_adapter_v1.py --write-plan
exit $LASTEXITCODE
