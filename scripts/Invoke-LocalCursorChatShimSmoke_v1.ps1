# Chat shim v0 smoke: plan → dry-run shim → /health + /v1/chat/completions
param(
    # Default 8012 — dogfood launcher uses 8011; smoke must not kill a live shim on 8011.
    [int]$ShimPort = 8012
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:COMPRESSION_HARDENING_CONFIG_PATH = "data/btrack/compression_coding_proxy_hardening_v1.json"
$env:MKM_CHAT_SHIM_DRY_RUN = "1"

Write-Host "[1/2] chat shim plan" -ForegroundColor Cyan
py scripts/build_local_cursor_chat_shim_v1.py --write-plan
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/2] shim dry-run smoke on 127.0.0.1:$ShimPort" -ForegroundColor Cyan
$job = Start-Job -ScriptBlock {
    param($r, $p)
    Set-Location $r
    $env:COMPRESSION_HARDENING_CONFIG_PATH = "data/btrack/compression_coding_proxy_hardening_v1.json"
    $env:MKM_CHAT_SHIM_DRY_RUN = "1"
    py -m uvicorn scripts.cursor_chat_shim_v1:app --host 127.0.0.1 --port $p 2>&1
} -ArgumentList $Root, $ShimPort

try {
    $ready = $false
    foreach ($i in 1..25) {
        Start-Sleep -Seconds 1
        try {
            $h = Invoke-WebRequest -Uri "http://127.0.0.1:$ShimPort/health" -UseBasicParsing -TimeoutSec 3
            if ($h.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { Write-Host "shim health timeout" -ForegroundColor Red; exit 3 }

    $sample = @"
Task: add scripts/build_local_dev_backup_manifest_v1.py.
Constraints: B-track research_only, no active report mutation, pytest smoke.
Files: scripts/*.py, data/btrack/*.jsonl.
Verify with py -m pytest -q.
"@

    $payload = @{
        model = "mkm-shim-smoke"
        messages = @(
            @{ role = "system"; content = $sample }
            @{ role = "user"; content = "List 3 constraints only." }
        )
    } | ConvertTo-Json -Depth 5 -Compress

    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$ShimPort/v1/chat/completions" `
        -Method POST -Body $payload -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
    $doc = $resp.Content | ConvertFrom-Json
    $audit = $doc.mkm_shim_integrity.message_audit
    if (-not $audit) {
        Write-Host "missing mkm_shim_integrity.message_audit" -ForegroundColor Red
        exit 4
    }
    $structured = ($audit | Where-Object { $_.structured_preserve -eq $true })
    if (-not $structured) {
        Write-Host "expected structured_preserve in audit" -ForegroundColor Red
        exit 5
    }
    Write-Host "chat shim dry-run OK (structured_preserve=$($structured.Count))" -ForegroundColor Green
    exit 0
}
finally {
    Stop-Job $job -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $job -Force -ErrorAction SilentlyContinue | Out-Null
}
