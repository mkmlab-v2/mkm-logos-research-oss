param(
    [string]$ApiHost = "127.0.0.1",
    [int]$Port = 8020
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$url = "http://$ApiHost`:$Port/v1/risk/warning"

$payload = @{
    client_request_id = "smoke-$(Get-Date -Format yyyyMMdd-HHmmss)"
    asset_scope = "BTC-USD"
    horizon = "24h"
    include_evidence_ref = $true
} | ConvertTo-Json -Depth 5

Write-Host "[macro-risk-smoke] POST $url"
$resp = Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $payload

if (-not $resp.decision_state) {
    throw "missing decision_state in response"
}
if (-not $resp.disclaimer.not_investment_advice) {
    throw "missing disclaimer.not_investment_advice=true"
}
if (-not $resp.evidence_ref.artifact_hash_sha256) {
    throw "missing evidence_ref.artifact_hash_sha256"
}

$outDir = Join-Path $repoRoot "docs\final\artifacts"
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$outPath = Join-Path $outDir "macro_risk_warning_api_smoke_latest.json"

$resp | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding utf8

Write-Host "[macro-risk-smoke] PASS"
Write-Host "[macro-risk-smoke] decision_state=$($resp.decision_state) risk_warning_level=$($resp.risk_warning_level)"
Write-Host "[macro-risk-smoke] saved=$outPath"
