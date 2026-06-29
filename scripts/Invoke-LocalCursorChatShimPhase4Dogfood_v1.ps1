# Phase 4 BYOK dogfood — start shim (if needed) + readiness probe (B-track)
param(
    [int]$ShimPort = 8011,
    [switch]$SkipLiveProbe,
    [switch]$SkipStart
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-ShimHealth {
    param([int]$Port)
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        return ($h.status -eq "ok")
    }
    catch { return $false }
}

$job = $null
if (-not $SkipStart) {
    $healthy = Test-ShimHealth -Port $ShimPort
    if (-not $healthy) {
        Write-Host "[*] starting chat shim on :$ShimPort" -ForegroundColor Cyan
        $job = Start-Job -ScriptBlock {
            param($r, $p)
            Set-Location $r
            $env:MKM_CHAT_SHIM_PORT = "$p"
            py scripts/sandbox/launch_chat_shim_server_v1.py 2>&1
        } -ArgumentList $Root, $ShimPort
        foreach ($i in 1..25) {
            Start-Sleep -Seconds 1
            if (Test-ShimHealth -Port $ShimPort) { break }
        }
    }
}

$args = @(
    "scripts/sandbox/check_chat_shim_phase4_dogfood_readiness_v1.py",
    "--strict",
    "--port", $ShimPort
)
if ($SkipLiveProbe) { $args += "--skip-live" }

py @args
$code = $LASTEXITCODE

if ($job) {
    Stop-Job $job -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $job -Force -ErrorAction SilentlyContinue | Out-Null
    Get-NetTCPConnection -LocalPort $ShimPort -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

if ($code -ne 0) { exit $code }

Write-Host ""
Write-Host "=== Phase 4 Cursor BYOK (human) ===" -ForegroundColor Yellow
Write-Host "1. py scripts/sandbox/launch_chat_shim_server_v1.py  # keep terminal open"
Write-Host "2. Cursor → Override OpenAI Base URL: http://127.0.0.1:$ShimPort/v1"
Write-Host "3. API Key: any non-empty string · send one short coding request"
Write-Host "ready_for_cursor_override stays false until signoff artifact." -ForegroundColor DarkGray
exit 0
