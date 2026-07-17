<#
.SYNOPSIS
  High-delegation preflight — session upgrade, P0, MCP host probe, browser host probe, NL gate, optional approval map.

.DESCRIPTION
  고차원 위임(L/M) 시작 **전** 호스트·레포 측 선점검. 채팅 주입(MCP get_health, browser_tabs)은
  에이전트 첫 턴 잔여 — 본 JSON에 chat_only_remainder 로 명시.

  Flow: plan/승인표(선택) -> 본 스크립트 exit 0 -> 에이전트 chat NL/browser probe -> AUTO chain.

.PARAMETER Scale
  M = pytest/chain 1개급 | L = 승인표 권장

.PARAMETER Lane
  oracle | prophecy | ops | infra | design | web_ops | ms

.PARAMETER ApprovalMap
  Optional path to reports/delegation_*_approval_map_*_latest.json

.PARAMETER StrictBrowser
  browser descriptor missing 시 exit 1

.EXAMPLE
  powershell -File scripts\Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale L -Lane prophecy -ApprovalMap reports\delegation_parallel_passive_loop_approval_map_v1_latest.json
#>
param(
    [ValidateSet("M", "L")]
    [string]$Scale = "M",
    [ValidateSet("", "oracle", "prophecy", "ops", "infra", "design", "web_ops", "ms")]
    [string]$Lane = "",
    [string]$ApprovalMap = "",
    [string]$OutJson = "",
    [switch]$StrictBrowser,
    [switch]$SkipSessionUpgrade,
    [switch]$SkipHostGates
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $root

function Resolve-ResumePackLane {
    param([string]$Lane)
    switch ($Lane) {
        "prophecy" { return "oracle" }
        "ops"      { return "infra" }
        "design"   { return "web_ops" }
        default    { return $Lane }
    }
}

if (-not $OutJson) {
    $OutJson = Join-Path $root "reports\mkm_high_delegation_preflight_v1_latest.json"
}

$utc = (Get-Date).ToUniversalTime().ToString("o")
$steps = [ordered]@{}
$ok = $true

function Add-Step {
    param([string]$Name, [int]$ExitCode, [string]$Note = "")
    $script:steps[$Name] = [ordered]@{
        exit_code = $ExitCode
        ok        = ($ExitCode -eq 0)
        note      = $Note
    }
    if ($ExitCode -ne 0) { $script:ok = $false }
}

# 1) Session upgrade + resume + NL assist gate (when lane)
if (-not $SkipSessionUpgrade) {
    $suArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $root 'scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1'), '-SkipSoloOps')
    $resumeLane = Resolve-ResumePackLane -Lane $Lane
    if ($resumeLane -and $resumeLane -in @('oracle', 'ms', 'infra', 'web_ops')) {
        $suArgs += @('-Lane', $resumeLane)
    }
    & powershell @suArgs
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    Add-Step "cursor_session_upgrade" $code
} else {
    Add-Step "cursor_session_upgrade" 0 "skipped"
}

# 2–5) Host gates (P0, MCP, browser, NL gate) — optional skip for aux D6 thin workspace
if ($SkipHostGates) {
    Add-Step "p0_constitution_paths" 0 "skipped_aux_host"
    Add-Step "mcp_host_hygiene" 0 "skipped_aux_host"
    Add-Step "browser_host_readiness" 0 "skipped_aux_host"
    Add-Step "delegation_research_assist_gate" 0 "skipped_aux_host"
} else {
    # 2) P0 paths
    $p0 = Join-Path $root "scripts\verify_p0_constitution_gate_paths.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $p0
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    Add-Step "p0_constitution_paths" $code

    # 3) MCP host hygiene (not get_health — chat-only)
    $mcpProbe = Join-Path $root "scripts\Invoke-McpHygieneProbe.ps1"
    $mcpOut = Join-Path $root "reports\mcp_hygiene_probe_latest.json"
    if (Test-Path -LiteralPath $mcpProbe) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $mcpProbe -WorkspaceRoot $root -OutJson $mcpOut
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        Add-Step "mcp_host_hygiene" $code "NotebookLM prereq; authenticated=get_health in chat"
    } else {
        Add-Step "mcp_host_hygiene" 1 "missing Invoke-McpHygieneProbe.ps1"
    }

    # 4) IDE browser host readiness (not browser_tabs — chat-only)
    $browserScript = Join-Path $root "scripts\check_cursor_ide_browser_readiness_v1.ps1"
    $browserOut = Join-Path $root "reports\cursor_ide_browser_readiness_latest.json"
    if (Test-Path -LiteralPath $browserScript) {
        $bArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $browserScript, '-WorkspaceRoot', $root, '-OutJson', $browserOut)
        if ($StrictBrowser) { $bArgs += '-Strict' }
        & powershell @bArgs
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        # Without -StrictBrowser: exit 2 (browser_view_missing) is Tier-3 chat inject — record but do not fail preflight ok.
        if (-not $StrictBrowser -and $code -eq 2) {
            $script:steps["browser_host_readiness"] = [ordered]@{
                exit_code = $code
                ok        = $false
                note      = "soft:browser_view_missing_tier3_chat_inject"
            }
        } else {
            Add-Step "browser_host_readiness" $code "browser_* inject per chat; Settings Browser ON + new chat"
        }
    } else {
        Add-Step "browser_host_readiness" 1 "missing check_cursor_ide_browser_readiness_v1.ps1"
    }

    # 5) NL research assist gate (chat-only REVIEW — do not fail preflight ok)
    $gateScript = Join-Path $root "scripts\Invoke-MkmDelegationResearchAssistGate_v1.ps1"
    if (Test-Path -LiteralPath $gateScript) {
        $gArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $gateScript)
        if ($Lane) { $gArgs += @('-Lane', $Lane) }
        & powershell @gArgs
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        $script:steps["delegation_research_assist_gate"] = [ordered]@{
            exit_code = $code
            ok        = ($code -eq 0)
            note      = "chat_only_review_non_fatal"
        }
    } else {
        Add-Step "delegation_research_assist_gate" 1 "missing gate script"
    }
}

# 6) Approval map (L recommended)
$approvalSummary = [ordered]@{
    path              = $(if ($ApprovalMap) { $ApprovalMap } else { $null })
    scale             = $Scale
    l_requires_map    = ($Scale -eq "L")
    map_present       = $false
    stop_nodes        = @()
    auto_pending      = @()
    delegation_status = $null
}
if ($ApprovalMap -and (Test-Path -LiteralPath $ApprovalMap)) {
    $map = Get-Content -LiteralPath $ApprovalMap -Raw -Encoding UTF8 | ConvertFrom-Json
    $approvalSummary.map_present = $true
    $approvalSummary.delegation_status = $map.delegation_status
    foreach ($node in @($map.nodes)) {
        if ($node.approval -eq "STOP" -or $node.approval -eq "REVIEW") {
            if ($node.status -ne "done" -and $node.status -ne "skipped") {
                $approvalSummary.stop_nodes += $node.id
            }
        }
        if ($node.approval -eq "AUTO" -and $node.status -eq "pending") {
            $approvalSummary.auto_pending += $node.id
        }
    }
    Add-Step "approval_map_parse" 0 "stop=$($approvalSummary.stop_nodes.Count) auto_pending=$($approvalSummary.auto_pending.Count)"
} elseif ($Scale -eq "L") {
    Add-Step "approval_map_parse" 0 "warn:L_scale_without_approval_map_path"
    $approvalSummary.note = "L-grade: pass -ApprovalMap reports/delegation_*_approval_map_*_latest.json before AUTO execution"
} else {
    Add-Step "approval_map_parse" 0 "skipped_m_scale"
}

$chatOnly = @(
    "NotebookLM MCP: get_health in this chat (authenticated=false -> setup_auth)",
    "Cursor IDE browser: browser_tabs once (tool_not_found -> Browser ON + Reload + new chat)",
    "Human STOP nodes from approval_map before live/Track A/SEND/apply-active"
)

$hostReady = ($steps.p0_constitution_paths.ok -and $steps.mcp_host_hygiene.ok -and $steps.browser_host_readiness.ok -and $steps.cursor_session_upgrade.ok)
$readyForAuto = $hostReady -and ($Scale -ne "L" -or $approvalSummary.map_present) -and ($approvalSummary.stop_nodes.Count -eq 0)

$payload = [ordered]@{
    schema               = "mkm_high_delegation_preflight_v1"
    generated_at_utc     = $utc
    scale                = $Scale
    lane                 = $(if ($Lane) { $Lane } else { $null })
    ok                   = $ok
    host_ready           = $hostReady
    ready_for_auto       = $readyForAuto
    steps                = $steps
    approval_map         = $approvalSummary
    chat_only_remainder  = $chatOnly
    artifacts            = [ordered]@{
        session_upgrade = "reports/mkm_cursor_session_upgrade_v1_latest.json"
        nl_gate         = "reports/delegation_research_assist_gate_v1_latest.json"
        mcp_probe       = "reports/mcp_hygiene_probe_latest.json"
        browser         = "reports/cursor_ide_browser_readiness_latest.json"
    }
    next_agent_sequence  = @(
        "Read this JSON + approval_map STOP list",
        "Chat: get_health + browser_tabs if UI/NL needed",
        "Execute AUTO nodes / M chain; checkpoint + MISSION_LOG next 1 line"
    )
    reproducible_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale $Scale" + $(if ($Lane) { " -Lane $Lane" } else { "" }) + $(if ($ApprovalMap) { " -ApprovalMap `"$ApprovalMap`"" } else { "" })
}

$outDir = Split-Path -Parent $OutJson
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$jsonText = ($payload | ConvertTo-Json -Depth 10) + "`n"
[System.IO.File]::WriteAllText($OutJson, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "host_ready=$hostReady ready_for_auto=$readyForAuto ok=$ok -> $OutJson" -ForegroundColor $(if ($readyForAuto) { "Green" } elseif ($hostReady) { "Yellow" } else { "Red" })
if (-not $ok) { exit 1 }
exit 0
