# Chat shim upstream shadow — 3 live requests (B-track; costs apply)
param(
    [int]$ShimPort = 8011,
    [int]$MaxRequests = 3,
    [switch]$DryRun,
    [switch]$ReuseRunningShim
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:COMPRESSION_HARDENING_CONFIG_PATH = "data/btrack/compression_coding_proxy_hardening_v1.json"
Remove-Item Env:MKM_CHAT_SHIM_DRY_RUN -ErrorAction SilentlyContinue

$args = @(
    "scripts/sandbox/run_chat_shim_upstream_shadow_v1.py",
    "--strict",
    "--port", $ShimPort,
    "--max-requests", $MaxRequests
)
if ($DryRun) { $args += "--dry-run" }
if ($ReuseRunningShim) { $args += "--reuse-running-shim" }
else {
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$ShimPort/health" -TimeoutSec 2
        if ($h.status -eq "ok") { $args += "--reuse-running-shim" }
    } catch { }
}

py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[+] refresh chat shim plan" -ForegroundColor Cyan
py scripts/build_local_cursor_chat_shim_v1.py --write-plan
exit $LASTEXITCODE
