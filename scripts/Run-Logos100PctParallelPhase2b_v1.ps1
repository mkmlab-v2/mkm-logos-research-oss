# Parallel LOGOS-100PCT Phase2b: CDIM registry refresh + wire + envelope + LLM plan + closure.
# Does NOT run bootstrap gold reset. Does NOT RefreshStaging on VPS sync.
param(
    [switch]$SkipCdim,
    [switch]$SkipWire,
    [switch]$SkipEnvelope,
    [switch]$SkipLlmPlan,
    [switch]$SkipSignoffReadiness,
    [switch]$BtrackOperatorProxyAck,
    [switch]$SkipClosure,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "python" }

Write-Host "==> LOGOS-100PCT parallel Phase2b" -ForegroundColor Cyan

$jobs = @()

if (-not $SkipCdim) {
    $jobs += Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location -LiteralPath $Root
        & $Py scripts/assemble_logos_cross_domain_interface_v1.py --use-bridge-registry --validate
        if ($LASTEXITCODE -ne 0) { throw "cdim failed" }
    } -ArgumentList $WorkspaceRoot, $py
}

if (-not $SkipWire) {
    $jobs += Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location -LiteralPath $Root
        & $Py scripts/build_mkm_graph_wire_rag_poc_v1.py
        if ($LASTEXITCODE -ne 0) { throw "wire poc failed" }
    } -ArgumentList $WorkspaceRoot, $py
}

if (-not $SkipEnvelope) {
    $jobs += Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location -LiteralPath $Root
        & $Py scripts/assemble_three_lens_sphere_envelope_v1.py
        if ($LASTEXITCODE -ne 0) { throw "envelope failed" }
    } -ArgumentList $WorkspaceRoot, $py
}

if (-not $SkipLlmPlan) {
    $jobs += Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location -LiteralPath $Root
        & $Py scripts/build_logos_concept_bridge_llm_plan_v1.py
        if ($LASTEXITCODE -ne 0) { throw "llm plan failed" }
    } -ArgumentList $WorkspaceRoot, $py
}

foreach ($j in $jobs) {
    Wait-Job -Job $j | Out-Null
    $state = (Receive-Job -Job $j -ErrorAction Stop)
    if ($j.State -ne "Completed") {
        throw "parallel job failed: $($j.Id)"
    }
    Remove-Job -Job $j
}

if (-not $SkipSignoffReadiness) {
    Write-Host "==> signoff readiness" -ForegroundColor Cyan
    & $py scripts/check_logos_concept_bridge_signoff_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { throw "signoff readiness failed" }
}

if ($BtrackOperatorProxyAck) {
    Write-Host "==> btrack operator proxy ack (research only)" -ForegroundColor Yellow
    & $py scripts/mark_logos_concept_bridge_human_signoff_v1.py --btrack-operator-proxy-ack
    if ($LASTEXITCODE -ne 0) { throw "signoff apply failed" }
    & $py scripts/build_logos_concept_bridge_registry_v1.py
    if ($LASTEXITCODE -ne 0) { throw "registry refresh failed" }
}

Write-Host "==> chronology hardset closure (tier_v2 SSOT + margin report)" -ForegroundColor Cyan
& $py scripts/run_logos_chronology_hardset_closure_v1.py
if ($LASTEXITCODE -ne 0) { throw "chronology hardset closure failed" }

if (-not $SkipClosure) {
    Write-Host "==> closure" -ForegroundColor Cyan
    & $py scripts/build_logos_100pct_closure_v1.py --run-pytest
    if ($LASTEXITCODE -ne 0) { throw "closure failed" }
}

Write-Host "==> done" -ForegroundColor Green
