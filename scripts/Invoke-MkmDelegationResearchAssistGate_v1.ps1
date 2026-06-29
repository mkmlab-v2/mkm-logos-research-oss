<#
.SYNOPSIS
  Delegation research assist gate — local SSOT first, then recommend NotebookLM MCP when gap remains.

.DESCRIPTION
  M/L 고차원 위임·B-track 갭 시 에이전트/스케줄이 호출. NL 질의 자체는 MCP(채팅) 또는 nlm CLI;
  본 스크립트는 결정론적 게이트 JSON만 씁니다.

  Decision:
  - skip_nl_local_ssot — Topic hit in CONSTITUTION (optional -Topic)
  - skip_nl_lane_hold — MS HOLD 등
  - use_nl_mcp — gap + MCP prereq OK → agent: get_health → ask_question
  - repair_mcp_first — prereq fail → auth recovery path
  - vault_fallback — MCP unavailable; use Vault mirror + manifest

.PARAMETER Lane
  oracle | prophecy | ops | infra | design | web_ops | ms

.PARAMETER Topic
  Optional grep needle for CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md

.PARAMETER OutJson
  Default: reports/delegation_research_assist_gate_v1_latest.json

.EXAMPLE
  powershell -File scripts\Invoke-MkmDelegationResearchAssistGate_v1.ps1 -Lane prophecy -Topic "Layer-1 Brier"
#>
param(
    [ValidateSet("", "oracle", "prophecy", "ops", "infra", "design", "web_ops", "ms")]
    [string]$Lane = "",
    [string]$Topic = "",
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $root

if (-not $OutJson) {
    $OutJson = Join-Path $root "reports\delegation_research_assist_gate_v1_latest.json"
}

$constitution = Join-Path $root "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
$laneMapPath = Join-Path $root "docs\final\artifacts\delegation_nl_lane_notebook_map_v1.json"
$utc = (Get-Date).ToUniversalTime().ToString("o")

$localHit = $false
$localHitCount = 0
if ($Topic -and (Test-Path -LiteralPath $constitution)) {
    $localHitCount = @(Select-String -LiteralPath $constitution -SimpleMatch -Pattern $Topic -ErrorAction SilentlyContinue).Count
    $localHit = ($localHitCount -gt 0)
}

$laneHint = $null
$skipLaneReason = $null
if ($Lane -and (Test-Path -LiteralPath $laneMapPath)) {
    $map = Get-Content -LiteralPath $laneMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $entry = $map.lanes.$Lane
    if ($entry) {
        if ($entry.skip_nl_reason) {
            $skipLaneReason = [string]$entry.skip_nl_reason
        }
        $laneHint = [ordered]@{
            label_ko         = $entry.label_ko
            notebook_mcp_id  = $entry.notebook_mcp_id
            manifest_pointer = $entry.manifest_pointer
        }
    }
}

$mcpPrereqExit = 0
$mcpPrereqPath = Join-Path $root "scripts\check_notebooklm_mcp_prereqs.ps1"
if (Test-Path -LiteralPath $mcpPrereqPath) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $mcpPrereqPath -WorkspaceRoot $root 2>&1 | Out-Null
    $mcpPrereqExit = $LASTEXITCODE
    if ($null -eq $mcpPrereqExit) { $mcpPrereqExit = 0 }
}

$triagePath = Join-Path $root "reports\notebooklm_sync_triage_latest.json"
$triageExit = 0
$triageRunner = Join-Path $root "scripts\Invoke-NotebookLmSyncTriage_v1.ps1"
if (Test-Path -LiteralPath $triageRunner) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $triageRunner -WorkspaceRoot $root -OutJson $triagePath 2>&1 | Out-Null
    $triageExit = $LASTEXITCODE
    if ($null -eq $triageExit) { $triageExit = 0 }
}

$decision = "use_nl_mcp"
$reason = "local_ssot_gap_assumed"
$agentSteps = @(
    "Read CONSTITUTION section + callable script path before NL",
    "MCP get_health; authenticated=false -> setup_auth or vault_fallback",
    "ask_question with lane notebook_mcp_id; reuse session_id on follow-ups",
    "Tag answer [HYPO]; re-verify paths with scripts; never Fact-Lock from NL alone"
)

if ($skipLaneReason) {
    $decision = "skip_nl_lane_hold"
    $reason = $skipLaneReason
    $agentSteps = @("MS/HOLD lane: local SSOT + pytest only; NL optional [HYPO] narrative")
}
elseif ($localHit) {
    $decision = "skip_nl_local_ssot"
    $reason = "topic_found_in_constitution"
    $agentSteps = @("Use CONSTITUTION + scripts only; NL not required for this topic needle")
}
elseif ($mcpPrereqExit -ge 2) {
    $decision = "repair_mcp_first"
    $reason = "mcp_prereq_exit_$mcpPrereqExit"
    $agentSteps = @(
        "powershell -File scripts/Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1",
        "Reload Window + new chat if Cursor MCP Not connected; get_health in chat",
        "Re-run this gate"
    )
}
elseif ($mcpPrereqExit -eq 1) {
    $decision = "vault_fallback"
    $reason = "mcp_prereq_warn_strict"
    $agentSteps = @(
        "Read docs/NotebookLM_sources_manifest.md + Vault mirror under MKM_DATA_VAULT",
        "Optional: Run-NotebookLmMkmHybridRecommendedRoutine_v1.ps1 -SkipLocalDeterministic"
    )
}

$suggestedQuestion = if ($Topic) {
    "[${Lane}] ${Topic} -- summarize alignment with repo SSOT (CONSTITUTION + scripts) only. No implementation/pass claims. Tag [HYPO]."
} else {
    "[${Lane}] List gaps not covered by CONSTITUTION + scripts for current mission. [HYPO] research_only."
}

$payload = [ordered]@{
    schema                = "delegation_research_assist_gate_v1"
    generated_at_utc      = $utc
    lane                  = $(if ($Lane) { $Lane } else { $null })
    topic                 = $(if ($Topic) { $Topic } else { $null })
    local_constitution_hit = $localHit
    local_hit_count       = $localHitCount
    mcp_prereq_exit_code  = $mcpPrereqExit
    triage_exit_code      = $triageExit
    triage_json           = $(if (Test-Path -LiteralPath $triagePath) { $triagePath } else { $null })
    lane_notebook_hint    = $laneHint
    decision              = $decision
    reason                = $reason
    suggested_question    = $suggestedQuestion
    agent_steps           = $agentSteps
    reproducible_command  = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmDelegationResearchAssistGate_v1.ps1" + $(if ($Lane) { " -Lane $Lane" } else { "" }) + $(if ($Topic) { " -Topic `"$Topic`"" } else { "" })
    fact_lock             = "NL output is never completion SSOT; exit 0 artifact path remains local scripts"
}

$outDir = Split-Path -Parent $OutJson
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$jsonText = ($payload | ConvertTo-Json -Depth 8) + "`n"
[System.IO.File]::WriteAllText($OutJson, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "decision=$decision reason=$reason -> $OutJson" -ForegroundColor $(if ($decision -eq "use_nl_mcp") { "Green" } else { "Cyan" })
exit 0
