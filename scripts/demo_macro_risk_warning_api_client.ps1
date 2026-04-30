param(
    [string]$ApiHost = "127.0.0.1",
    [int]$Port = 8021,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h"
)

$ErrorActionPreference = "Stop"

$url = "http://$ApiHost`:$Port/v1/risk/warning"
$payload = @{
    client_request_id = "demo-$(Get-Date -Format yyyyMMdd-HHmmss)"
    asset_scope = $AssetScope
    horizon = $Horizon
    include_evidence_ref = $true
} | ConvertTo-Json -Depth 5

Write-Host "[macro-risk-demo] POST $url"
$resp = Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $payload

Write-Host ""
Write-Host "[macro-risk-demo] Result"
Write-Host "  state      : $($resp.decision_state)"
Write-Host "  warning    : $($resp.risk_warning_level)"
Write-Host "  confidence : $($resp.confidence_band)"
Write-Host "  posture    : $($resp.recommended_operator_posture)"
Write-Host "  regime     : $($resp.regime_context.primary_regime_id) ($($resp.regime_context.similarity_score))"
Write-Host "  evidence   : $($resp.evidence_ref.artifact_hash_sha256)"

