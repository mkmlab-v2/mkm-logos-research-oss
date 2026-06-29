# Logos Graph Studio — internal B2B pilot day preflight (one-click · no external SEND).
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipMeetingPackRebuild,
    [switch]$SkipCommercialReadiness,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) {
    $WorkspaceRoot.TrimEnd('\', '/')
} elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $root

$outJson = Join-Path $root "reports/logos_graph_studio_b2b_pilot_day_preflight_v1_latest.json"
$steps = @(
    @{
        id = "meeting_pack"
        skip = $SkipMeetingPackRebuild
        ps1 = "build_logos_graph_studio_b2b_meeting_pack_v1.py"
        py = $true
    }
    @{ id = "trace_live"; skip = $false; cmd = @("py", "scripts/check_logos_trace_public_v1.py") }
    @{ id = "trust_viz_chain"; skip = $false; cmd = @("py", "scripts/check_showroom_trust_viz_public_chain_v1.py") }
    @{ id = "logos_jema_deploy"; skip = $false; ps1 = "verify_logos_jema_ai_deploy_v1.ps1" }
    @{ id = "graph_studio_rehearsal"; skip = $false; cmd = @("py", "scripts/check_logos_graph_studio_b2b_rehearsal_live_v1.py") }
    @{
        id = "commercial_readiness"
        skip = $SkipCommercialReadiness
        cmd = @("py", "scripts/build_logos_observatory_commercial_readiness_v1.py")
    }
    @{ id = "gtm_copy_scan"; skip = $false; cmd = @("py", "scripts/check_logos_gtm_linkedin_b2b_copy_scan_v1.py") }
    @{ id = "public_docs_copy_scan"; skip = $false; cmd = @("py", "scripts/check_logos_research_public_docs_copy_v1.py") }
    @{ id = "counsel_handoff_bundle"; skip = $false; cmd = @("py", "scripts/build_logos_gtm_counsel_handoff_bundle_v1.py") }
    @{ id = "meeting_pack_readiness"; skip = $false; cmd = @("py", "scripts/check_logos_graph_studio_b2b_meeting_pack_readiness_v1.py") }
    @{ id = "external_b2b_meeting_kit"; skip = $false; cmd = @("py", "scripts/build_logos_graph_studio_external_b2b_meeting_kit_v1.py", "--skip-chain") }
    @{ id = "counsel_handoff_chain"; skip = $false; ps1 = "Invoke-LogosGtmCounselHandoffChain_v1.ps1" }
)

if ($WhatIf) {
    foreach ($s in $steps) {
        Write-Host ("plan: {0} skip={1}" -f $s.id, $s.skip)
    }
    exit 0
}

$ran = @()
$failed = @()
foreach ($s in $steps) {
    if ($s.skip) {
        Write-Host ("[skip] {0}" -f $s.id) -ForegroundColor DarkGray
        $ran += @{ id = $s.id; skipped = $true; ok = $true }
        continue
    }
    Write-Host ("`n[run] {0}" -f $s.id) -ForegroundColor Cyan
    if ($s.ps1 -and $s.py) {
        & py (Join-Path $root "scripts/$($s.ps1)")
    } elseif ($s.ps1) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts/$($s.ps1)")
    } else {
        $exe = $s.cmd[0]
        $args = @()
        if ($s.cmd.Count -gt 1) { $args = $s.cmd[1..($s.cmd.Count - 1)] }
        & $exe @args
    }
    $code = $LASTEXITCODE
    $ok = ($code -eq 0)
    $ran += @{ id = $s.id; exit_code = $code; ok = $ok }
    if (-not $ok) { $failed += $s.id }
}

$approvalPath = Join-Path $root "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json"
$approval = @{}
if (Test-Path -LiteralPath $approvalPath) {
    $approval = Get-Content -LiteralPath $approvalPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$doc = [ordered]@{
    schema = "logos_graph_studio_b2b_pilot_day_preflight_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    ok = ($failed.Count -eq 0)
    send_gate = "HOLD"
    ready_for_external_send = $false
    ready_for_internal_b2b_pilot = [bool]$approval.ready_for_internal_b2b_pilot
    commander_signoff = [bool]$approval.commander_signoff
    demo_primary_url = "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html?preset=job_job_suffering_reason"
    commercial_workspace_url = "https://logos.jema-ai.com/logos-research"
    demo_script = "docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md"
    meeting_pack_index = "docs/final/artifacts/logos_graph_studio_b2b_meeting_pack_index_v1_latest.md"
    live_rehearsal_checklist = "docs/final/artifacts/logos_graph_studio_b2b_live_rehearsal_checklist_v1_latest.md"
    counsel_handoff_chain = "scripts/Invoke-LogosGtmCounselHandoffChain_v1.ps1"
    counsel_submission_draft = "docs/final/artifacts/logos_gtm_counsel_submission_email_draft_v1_latest.json"
    external_b2b_meeting_kit = "reports/logos_graph_studio_external_b2b_meeting_kit_v1_latest.json"
    steps = $ran
    failed_steps = $failed
    post_pilot_record = "py scripts/record_logos_graph_studio_pilot_session_v1.py --outcome completed --notes `"`""
    reproduce = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LogosGraphStudioB2bPilotDay_v1.ps1"
}

$outDir = Split-Path -Parent $outJson
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$doc | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outJson -Encoding UTF8

if ($failed.Count -gt 0) {
    Write-Error ("logos_graph_studio_b2b_pilot_day: FAIL steps={0}" -f ($failed -join ", "))
}
Write-Host ""
Write-Host "logos_graph_studio_b2b_pilot_day: ok" -ForegroundColor Green
Write-Host "handoff: $outJson"
Write-Host "30s script: docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md"
Write-Host "ready_for_external_send: false"
exit 0
