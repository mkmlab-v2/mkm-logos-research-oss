# Clinician graph deploy smoke: build + KPI artifact + optional HTTP graph API chain.
#
# .EXAMPLE
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ClinicianGraphDeploySmoke_v1.ps1
#   powershell -File scripts\Invoke-ClinicianGraphDeploySmoke_v1.ps1 -SkipHttp
#   powershell -File scripts\Invoke-ClinicianGraphDeploySmoke_v1.ps1 -BaseUrl https://app.jema-ai.com
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$BaseUrl = "https://app.jema-ai.com",
    [switch]$SkipHttp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$no1k = Join-Path $WorkspaceRoot "projects\no1kmedi"
$stamp = Get-Date -Format "yyyyMMddHHmmss"
$artifact = Join-Path $WorkspaceRoot "reports\clinician_graph_deploy_smoke_latest.json"
$steps = [ordered]@{}

Write-Host "[clinician-graph-deploy-smoke] npm run build" -ForegroundColor Cyan
Push-Location $no1k
try {
    npm run build | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed exit $LASTEXITCODE" }
    $steps.build = @{ ok = $true }
}
finally {
    Pop-Location
}

Write-Host "[clinician-graph-deploy-smoke] pilot KPI report" -ForegroundColor Cyan
& py (Join-Path $WorkspaceRoot "scripts\build_clinician_graph_pilot_kpi_report_v1.py") | Out-Host
if ($LASTEXITCODE -ne 0) { throw "build_clinician_graph_pilot_kpi_report_v1.py failed" }
$steps.pilot_kpi_report = @{ ok = $true }

$graphBuildOk = $false
$graphFeedbackOk = $false
$graphKpiOk = $false
$httpNote = "skipped"

if (-not $SkipHttp) {
    $fixturePath = Join-Path $WorkspaceRoot "tests\fixtures\km_physician_cds_assist_envelope_with_tri_layer_v1.example.json"
    if (-not (Test-Path $fixturePath)) { throw "fixture missing: $fixturePath" }
    $envelope = Get-Content $fixturePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $encounterRef = "deploy_graph_smoke_$stamp"

    $buildReq = @{
        schema         = "clinician_graph_build_from_cds_request_v1"
        request_id     = $encounterRef
        cds_envelope   = $envelope
        reasoning      = @{
            syndrome_hypothesis = "Illustrative pattern (deploy smoke)"
            care_direction      = "Physician review required"
            caution             = "Deploy smoke caution"
        }
        options        = @{
            include_sasang_hint    = $true
            include_conflict_paths   = $true
        }
    } | ConvertTo-Json -Depth 30 -Compress

    $buildBody = Join-Path $env:TEMP "clinician-graph-build-$stamp.json"
    [System.IO.File]::WriteAllText($buildBody, $buildReq, [System.Text.UTF8Encoding]::new($false))
    $buildOut = Join-Path $env:TEMP "clinician-graph-build-out-$stamp.json"
    $buildCode = (& curl.exe -s -o $buildOut -w "%{http_code}" --max-time 60 -X POST "$BaseUrl/api/clinician/graph/build-from-cds" -H "Content-Type: application/json; charset=utf-8" -H "Origin: $BaseUrl" -H "Referer: $BaseUrl/clinician" --data-binary "@$buildBody")
    if ($buildCode -ne "200") { throw "graph build-from-cds failed http $buildCode (deploy graph routes first?)" }
    $build = Get-Content $buildOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $build.success) { throw "graph build-from-cds success=false" }
    if (-not $build.graph_bundle_v1.nodes) { throw "graph nodes missing" }
    $graphBuildOk = $true

    $targetId = $build.graph_bundle_v1.nodes[1].id
    $fbReq = @{
        schema          = "clinician_graph_review_feedback_request_v1"
        encounter_ref   = $encounterRef
        target_id       = $targetId
        target_kind     = "node"
        feedback        = "hold"
        reason_code     = "deploy_smoke"
    } | ConvertTo-Json -Compress
    $fbBody = Join-Path $env:TEMP "clinician-graph-fb-$stamp.json"
    [System.IO.File]::WriteAllText($fbBody, $fbReq, [System.Text.UTF8Encoding]::new($false))
    $fbOut = Join-Path $env:TEMP "clinician-graph-fb-out-$stamp.json"
    $fbCode = (& curl.exe -s -o $fbOut -w "%{http_code}" --max-time 30 -X POST "$BaseUrl/api/clinician/graph/review-feedback" -H "Content-Type: application/json; charset=utf-8" -H "Origin: $BaseUrl" --data-binary "@$fbBody")
    if ($fbCode -ne "200") { throw "graph review-feedback failed http $fbCode" }
    $fb = Get-Content $fbOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $fb.success) { throw "graph review-feedback success=false" }
    $graphFeedbackOk = $true

    $kpiCode = (& curl.exe -s -o $fbOut -w "%{http_code}" --max-time 30 "$BaseUrl/api/clinician/graph/pilot-kpi-summary")
    if ($kpiCode -ne "200") { throw "pilot-kpi-summary failed http $kpiCode" }
    $graphKpiOk = $true
    $httpNote = "live_ok"
    $steps.http = @{
        base_url     = $BaseUrl
        build_http   = [int]$buildCode
        feedback_http = [int]$fbCode
        kpi_http     = [int]$kpiCode
        node_count   = @($build.graph_bundle_v1.nodes).Count
    }
}

$doc = @{
    schema      = "clinician_graph_deploy_smoke_v1"
    at_utc      = (Get-Date).ToUniversalTime().ToString("o")
    research_only = $true
    send_gate   = "HOLD"
    build_ok    = $true
    pilot_kpi_ok = $true
    graph_build_ok = $graphBuildOk
    graph_feedback_ok = $graphFeedbackOk
    graph_kpi_ok = $graphKpiOk
    http_note   = $httpNote
    steps       = $steps
    reproduce   = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ClinicianGraphDeploySmoke_v1.ps1"
} | ConvertTo-Json -Depth 8
Set-Content -Path $artifact -Value $doc -Encoding UTF8
Write-Host "[clinician-graph-deploy-smoke] OK -> $artifact" -ForegroundColor Green
