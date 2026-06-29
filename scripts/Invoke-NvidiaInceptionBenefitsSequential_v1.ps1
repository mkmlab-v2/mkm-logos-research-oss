# Sequential NVIDIA Inception partner benefits (GCP/Lambda done; Nebius -> Azure).
param(
    [switch]$SkipNebius,
    [switch]$SkipAzure
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

$cdp = 'http://127.0.0.1:9222'
try {
    Invoke-WebRequest -Uri "$cdp/json/version" -UseBasicParsing -TimeoutSec 3 | Out-Null
} catch {
    Write-Host 'CDP Chrome not on 9222 — starting...'
    & "$PSScriptRoot\Start-ChromeForNvidiaInceptionCdp_v1.ps1"
    Start-Sleep -Seconds 3
}

if (-not $SkipNebius) {
    Write-Host '=== 4/5 Nebius ==='
    py scripts\nvidia_inception_nebius_finish_v1.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Nebius: human_gate likely (auth.nebius.com password). Log in then re-run with -SkipNebius:$false'
    }
}

if (-not $SkipAzure) {
    Write-Host '=== 5/5 Azure ==='
    py scripts\nvidia_inception_azure_startup_fill_v1.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Azure: human_gate likely (Microsoft login). Log in then re-run with -SkipNebius'
    }
}

Write-Host 'Done. See reports/nvidia_nebius_finish_latest.json and reports/nvidia_azure_startup_fill_latest.json'
