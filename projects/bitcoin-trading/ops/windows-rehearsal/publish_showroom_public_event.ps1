# POSTs public_event_v1 from showroom_public_bundle_v1.json to the Public Event Gateway ingest endpoint.
# Requires PUBLIC_EVENT_GATEWAY_TOKEN when the gateway enforces auth.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ...\publish_showroom_public_event.ps1
# Env:
#   SHOWROOM_INGEST_URL (default https://api.jemaai.cloud/api/public-events/ingest)
#   PUBLIC_EVENT_GATEWAY_TOKEN (optional; must match gateway)

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$BundlePath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BundlePath)) {
    $BundlePath = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"
}

if (-not (Test-Path -LiteralPath $BundlePath)) {
    Write-Host "[showroom-publish] FAIL: bundle missing: $BundlePath"
    exit 1
}

$doc = Get-Content -LiteralPath $BundlePath -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $doc.public_event_v1) {
    Write-Host "[showroom-publish] FAIL: public_event_v1 missing in bundle"
    exit 1
}

$payload = $doc.public_event_v1 | ConvertTo-Json -Depth 20 -Compress
$url = [Environment]::GetEnvironmentVariable("SHOWROOM_INGEST_URL", "Process")
if ([string]::IsNullOrWhiteSpace($url)) {
    $url = "https://api.jemaai.cloud/api/public-events/ingest"
}

$payloadBytes = [System.Text.Encoding]::UTF8.GetByteCount($payload)
$contextDepth = 0
if (-not [string]::IsNullOrWhiteSpace([string]$doc.public_event_v1.abstract_reason)) { $contextDepth++ }
if (-not [string]::IsNullOrWhiteSpace([string]$doc.public_event_v1.direction_abstract)) { $contextDepth++ }
if ($null -ne $doc.public_event_v1.delayed_metrics) { $contextDepth++ }
if (-not [string]::IsNullOrWhiteSpace([string]$doc.public_event_v1.disclaimer_ref)) { $contextDepth++ }
Write-Host "[showroom-publish] payload_bytes=$payloadBytes context_depth=$contextDepth"

$headers = @{ "Content-Type" = "application/json; charset=utf-8" }
$tok = [Environment]::GetEnvironmentVariable("PUBLIC_EVENT_GATEWAY_TOKEN", "Process")
if (-not [string]::IsNullOrWhiteSpace($tok)) {
    $headers["X-Public-Event-Token"] = $tok
}

try {
    $resp = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $payload
    Write-Host "[showroom-publish] OK: $url"
    $resp | ConvertTo-Json -Compress

    $latestUrl = [Environment]::GetEnvironmentVariable("SHOWROOM_LATEST_URL", "Process")
    if ([string]::IsNullOrWhiteSpace($latestUrl)) {
        $latestUrl = $url -replace "/ingest/?$", "/latest"
    }
    $latest = Invoke-RestMethod -Uri $latestUrl -Method Get -Headers $headers

    $expectedEventId = [string]$doc.public_event_v1.event_id
    $expectedSource = [string]$doc.public_event_v1.source
    $actualEventId = [string]$latest.event_id
    $actualSource = [string]$latest.source

    if ($actualEventId -ne $expectedEventId -or $actualSource -ne $expectedSource) {
        Write-Host "[showroom-publish] FAIL: post-verify mismatch expected(event_id=$expectedEventId, source=$expectedSource) actual(event_id=$actualEventId, source=$actualSource)"
        exit 1
    }

    Write-Host "[showroom-publish] verify_ok latest_url=$latestUrl event_id=$actualEventId source=$actualSource"
    exit 0
} catch {
    Write-Host "[showroom-publish] FAIL: $($_.Exception.Message)"
    exit 1
}
