#Requires -Version 5.1
<#
.SYNOPSIS
  Build prophecy shadow ingest packet; optional POST to jemaai public-event gateway.
.NOTES
  research_only — does not enable live trading. Default is build-only (no POST).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Post,
    [switch]$AllowGoTrading
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$packetPath = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_jemaai_shadow_ingest_packet_v1_latest.json"
$buildArgs = @("scripts/build_btrack_prophecy_jemaai_shadow_ingest_packet_v1.py")
if ($AllowGoTrading) { $buildArgs += "--allow-go-trading" }

& $py @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $Post) {
    Write-Host "OK: packet built (no POST). Use -Post after human review + token env set." -ForegroundColor Green
    exit 0
}

if (-not (Test-Path -LiteralPath $packetPath)) {
    Write-Error "missing packet: $packetPath"
}

$doc = Get-Content -LiteralPath $packetPath -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $doc.ingest_ready) {
    Write-Host "WARN: ingest_ready=false (human review JSON missing). POST blocked." -ForegroundColor Yellow
    Write-Host "Record review: py scripts/record_btrack_align_panel_auto_promote_human_review_v1.py"
    exit 4
}

if (-not $doc.public_event_v1) {
    Write-Error "public_event_v1 missing in packet"
}

$payload = $doc.public_event_v1 | ConvertTo-Json -Depth 20 -Compress
$url = [Environment]::GetEnvironmentVariable("SHOWROOM_INGEST_URL", "Process")
if ([string]::IsNullOrWhiteSpace($url)) {
    $url = "https://api.jemaai.cloud/api/public-events/ingest"
}

$headers = @{ "Content-Type" = "application/json; charset=utf-8" }
$tok = [Environment]::GetEnvironmentVariable("PUBLIC_EVENT_GATEWAY_TOKEN", "Process")
if (-not [string]::IsNullOrWhiteSpace($tok)) {
    $headers["X-Public-Event-Token"] = $tok
}

try {
    $resp = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $payload
    Write-Host "OK: shadow ingest POST $url" -ForegroundColor Green
    $resp | ConvertTo-Json -Compress
    exit 0
} catch {
    Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
