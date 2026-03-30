Param(
  [string]$BaseUrl = "http://127.0.0.1:8010"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-JsonPost {
  param(
    [string]$Url,
    [hashtable]$Body
  )
  $json = ($Body | ConvertTo-Json -Depth 8)
  Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body $json
}

Write-Host "== Token API demo: mode_none =="
$reqNone = @{
  text = "bible test hangul 테스트"
  client_request_id = "demo-none-001"
}
$resNone = Invoke-JsonPost -Url "$BaseUrl/v1/compress" -Body $reqNone
$resNone | ConvertTo-Json -Depth 8

Write-Host "`n== Token API demo: mode_decision_fallback =="
$reqDecision = @{
  text = "compression hydration test 텍스트"
  client_request_id = "demo-decision-001"
  eval_context = @{
    hydrate_metrics = $true
    runner_hint = "decision_lock"
  }
}
$resDecision = Invoke-JsonPost -Url "$BaseUrl/v1/compress" -Body $reqDecision
$resDecision | ConvertTo-Json -Depth 8

Write-Host "`n== Token API demo: mode_live =="
$reqLive = @{
  text = "live eval hydration path 성능 테스트"
  client_request_id = "demo-live-001"
  eval_context = @{
    hydrate_metrics = $true
    hydrate_live_eval = $true
    runner_hint = "active_default"
  }
  hydration_hints = @{
    atom_ids = @("atom:x", "atom:y")
  }
}
$resLive = Invoke-JsonPost -Url "$BaseUrl/v1/compress" -Body $reqLive
$resLive | ConvertTo-Json -Depth 8

Write-Host "`n== Token API demo: expand roundtrip (live payload) =="
$exp = Invoke-JsonPost -Url "$BaseUrl/v1/expand" -Body @{ payload = $resLive }
$exp | ConvertTo-Json -Depth 8
