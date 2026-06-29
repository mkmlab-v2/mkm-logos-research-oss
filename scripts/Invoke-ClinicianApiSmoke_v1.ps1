#Requires -Version 5.1
<#
.SYNOPSIS
  Live CDSS API smoke (no VPS deploy) — mirrors Deploy-No1kmediDestinyTarball_v1.ps1 -RunApiSmoke POST chain.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ClinicianApiSmoke_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$consultJson = @'
{"schema":"patient_consult_input_v1","request_id":"api_smoke","actor_id":"smoke","lane_a_profile":{"birth_instant_utc":"1987-12-31T15:00:00Z","iana_tz":"Asia/Seoul","constitution_survey":{"digestion_pattern":"post-meal bloating"}},"lane_b_clinical":{"chief_complaint":"chronic fatigue","onset":"6mo","severity":"moderate","medication":"none","health_survey":{"sleep_quality":"delayed sleep onset"}}}
'@

$consultBody = Join-Path $env:TEMP "no1kmedi-api-smoke-consult-$stamp.json"
[System.IO.File]::WriteAllText($consultBody, $consultJson.Trim(), [System.Text.UTF8Encoding]::new($false))
$consultOut = Join-Path $env:TEMP "no1kmedi-api-smoke-consult-out-$stamp.json"
$consultCode = (& curl.exe -s -o $consultOut -w "%{http_code}" --max-time 60 -X POST "https://app.jema-ai.com/api/cdss/advanced-consult?validate_km_cds_envelope=1" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" --data-binary "@$consultBody")
if ($consultCode -ne "200") { throw "advanced-consult smoke failed http $consultCode" }

$consult = Get-Content $consultOut -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $consult.km_cds.validation.ok) {
    throw "km_cds.validation not ok: $($consult.km_cds.validation.error)"
}

$bundleReq = @{
    schema               = "patient_care_bundle_from_cds_request_v1"
    request_id           = "api_smoke"
    birth_instant_utc    = "1987-12-31T15:00:00Z"
    iana_tz              = "Asia/Seoul"
    cds_envelope         = $consult.km_cds.envelope
    soap                 = @{
        subjective = @{ text = "chronic fatigue (api smoke)" }
        objective  = @{ text = "not recorded" }
        assessment = @{ text = "preliminary hypothesis" }
        plan       = @{ text = "physician confirmation" }
    }
    options              = @{
        apply_slot_templates = $true
        validate_policy      = $true
        validate_bundle      = $true
        render_patient_md    = $true
    }
} | ConvertTo-Json -Depth 25 -Compress

$bundleFile = Join-Path $env:TEMP "no1kmedi-api-smoke-bundle-$stamp.json"
[System.IO.File]::WriteAllText($bundleFile, $bundleReq, [System.Text.UTF8Encoding]::new($false))
$bundleOut = Join-Path $env:TEMP "no1kmedi-api-smoke-bundle-out-$stamp.json"
$bundleCode = (& curl.exe -s -o $bundleOut -w "%{http_code}" --max-time 90 -X POST "https://app.jema-ai.com/api/cdss/patient-care-bundle-from-cds" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" -H "Referer: https://app.jema-ai.com/clinician" --data-binary "@$bundleFile")
if ($bundleCode -ne "200") { throw "patient-care-bundle smoke failed http $bundleCode" }

$bundle = Get-Content $bundleOut -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $bundle.success) { throw "patient-care-bundle success=false" }
$mdLen = ($bundle.patient_facing_markdown | Out-String).Trim().Length
if ($mdLen -lt 20) { throw "patient_facing_markdown too short ($mdLen)" }

Write-Host "[clinician-api-smoke] graph build-from-cds" -ForegroundColor Cyan
$graphBuildReq = @{
    schema               = "clinician_graph_build_from_cds_request_v1"
    request_id           = "api_smoke_graph_$stamp"
    cds_envelope         = $consult.km_cds.envelope
    reasoning            = @{
        syndrome_hypothesis = ($consult.draft.reasoning.syndrome_hypothesis | Out-String).Trim()
        care_direction      = ($consult.draft.reasoning.care_direction | Out-String).Trim()
        caution             = ($consult.draft.reasoning.caution | Out-String).Trim()
    }
    patient_care_bundle  = $bundle.patient_care_bundle
    options              = @{
        include_sasang_hint    = $true
        include_conflict_paths = $true
        include_bundle_slots   = $true
    }
} | ConvertTo-Json -Depth 30 -Compress
$graphBuildFile = Join-Path $env:TEMP "no1kmedi-api-smoke-graph-$stamp.json"
[System.IO.File]::WriteAllText($graphBuildFile, $graphBuildReq, [System.Text.UTF8Encoding]::new($false))
$graphBuildOut = Join-Path $env:TEMP "no1kmedi-api-smoke-graph-out-$stamp.json"
$graphBuildCode = (& curl.exe -s -o $graphBuildOut -w "%{http_code}" --max-time 60 -X POST "https://app.jema-ai.com/api/clinician/graph/build-from-cds" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" --data-binary "@$graphBuildFile")
if ($graphBuildCode -ne "200") { throw "graph build-from-cds smoke failed http $graphBuildCode" }
$graphBuild = Get-Content $graphBuildOut -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $graphBuild.success) { throw "graph build-from-cds success=false" }
$graphNodes = @($graphBuild.graph_bundle_v1.nodes).Count

$artifact = Join-Path $WorkspaceRoot "reports\clinician_api_smoke_latest.json"
$doc = @{
    schema            = "clinician_api_smoke_v1"
    at_utc            = (Get-Date).ToUniversalTime().ToString("o")
    consult_http      = [int]$consultCode
    validation_ok     = $true
    bundle_http       = [int]$bundleCode
    bundle_success    = $true
    patient_md_len    = $mdLen
    graph_build_http  = [int]$graphBuildCode
    graph_build_ok    = $true
    graph_node_count  = $graphNodes
    reproduce         = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ClinicianApiSmoke_v1.ps1"
} | ConvertTo-Json -Depth 5
Set-Content -Path $artifact -Value $doc -Encoding UTF8
Write-Host "[clinician-api-smoke] OK validation.ok=true md_len=$mdLen graph_nodes=$graphNodes -> $artifact" -ForegroundColor Green
