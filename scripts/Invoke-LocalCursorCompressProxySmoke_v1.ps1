# Coding proxy PoC: bench (proxy-aligned) → adapter plan → optional stub /health + /v1/compress smoke
param(
    [switch]$SkipStubSmoke,
    [int]$StubPort = 8010
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[1/3] proxy-aligned coding bench" -ForegroundColor Cyan
py scripts/run_cursor_coding_compress_bench_v1.py --proxy-aligned
$benchRc = $LASTEXITCODE
if ($benchRc -ne 0 -and $benchRc -ne 2) { exit $benchRc }

Write-Host "[2/3] adapter plan" -ForegroundColor Cyan
py scripts/build_local_cursor_compress_adapter_v1.py --write-plan
$planRc = $LASTEXITCODE
if ($planRc -ne 0 -and $planRc -ne 2) { exit $planRc }

if ($planRc -eq 2) {
    Write-Host "WIRING_HOLD: poc_gate.pass=false — fix bench before stub smoke" -ForegroundColor Yellow
    exit 2
}

if ($SkipStubSmoke) {
    Write-Host "Skip stub smoke (-SkipStubSmoke)" -ForegroundColor DarkGray
    exit 0
}

Write-Host "[3/3] stub smoke on 127.0.0.1:$StubPort" -ForegroundColor Cyan
$env:COMPRESSION_HARDENING_CONFIG_PATH = "data/btrack/compression_coding_proxy_hardening_v1.json"
$stubJob = Start-Job -ScriptBlock {
    param($r, $p, $hc)
    Set-Location $r
    $env:COMPRESSION_HARDENING_CONFIG_PATH = $hc
    py -m uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port $p 2>&1
} -ArgumentList $Root, $StubPort, $env:COMPRESSION_HARDENING_CONFIG_PATH

try {
    $ready = $false
    foreach ($i in 1..20) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$StubPort/health" -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) {
        Write-Host "stub health timeout" -ForegroundColor Red
        exit 3
    }
    Write-Host "health OK" -ForegroundColor Green

    $body = @{
        text = "def gate_check(): return exit_code == 0  # pytest minimal"
        client_request_id = "proxy-smoke-v1"
    } | ConvertTo-Json -Compress
    $compress = Invoke-WebRequest -Uri "http://127.0.0.1:$StubPort/v1/compress" `
        -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
    if ($compress.StatusCode -lt 200 -or $compress.StatusCode -ge 300) {
        Write-Host "compress HTTP $($compress.StatusCode)" -ForegroundColor Red
        exit 4
    }
    Write-Host "POST /v1/compress OK ($($compress.Content.Length) bytes)" -ForegroundColor Green
    exit 0
}
finally {
    Stop-Job $stubJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $stubJob -Force -ErrorAction SilentlyContinue | Out-Null
    Get-NetTCPConnection -LocalPort $StubPort -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
