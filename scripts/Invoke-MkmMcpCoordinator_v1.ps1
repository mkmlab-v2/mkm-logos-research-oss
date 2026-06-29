#Requires -Version 5.1
<#
.SYNOPSIS
  MKM MCP coordinator (S-stage) — lane preset advice + hygiene chain + coordinator JSON.

.DESCRIPTION
  research_only · send_gate HOLD · read-mostly orchestrator.
  Does NOT auto-switch mcp.json profile unless -ApplyProfileSwitch (commander ack).

  SSOT: docs/research/mcp_runtime_budget_routing.md
        docs/final/artifacts/mkm_mcp_lane_presets_v1.json

.PARAMETER Lane
  oracle | prophecy | ops | infra | design | web_ops | ms — overrides resume pack lane.

.PARAMETER ApplyPluginDiet
  Run apply_cursor_mcp_plugin_diet_auto_v1.py (default true).

.PARAMETER ApplyProfileSwitch
  Run Switch-McpProfile for lane preset (default false — HOLD).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmMcpCoordinator_v1.ps1 -Lane oracle
#>
param(
    [ValidateSet("", "oracle", "prophecy", "ops", "infra", "design", "web_ops", "ms")]
    [string]$Lane = "",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$ResumePackJson = "",
    [string]$OutJson = "",
    [bool]$ApplyPluginDiet = $true,
    [switch]$SkipPluginDiet,
    [switch]$SkipBudgetGate,
    [switch]$SkipDelegationGate,
    [switch]$ApplyProfileSwitch,
    [switch]$SkipBrowserAutoFix,
    [switch]$BrowserAutoFixWithReload
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $ResumePackJson) {
    $ResumePackJson = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_chat_resume_pack_latest.json"
}
if (-not $OutJson) {
    $OutJson = Join-Path $WorkspaceRoot "reports\mkm_mcp_coordinator_v1_latest.json"
}

$presetsPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_mcp_lane_presets_v1.json"
if (-not (Test-Path -LiteralPath $presetsPath)) {
    throw "Missing preset SSOT: $presetsPath"
}
$presetsDoc = Get-Content -LiteralPath $presetsPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-McpInventory {
    param([string]$McpsRoot)
    $servers = [System.Collections.Generic.List[object]]::new()
    $total = 0
    $pluginTotal = 0
    if (-not (Test-Path -LiteralPath $McpsRoot)) {
        return @{
            servers              = @()
            total_tool_count     = 0
            plugin_tool_count    = 0
        }
    }
    foreach ($dir in Get-ChildItem -LiteralPath $McpsRoot -Directory) {
        $toolsDir = Join-Path $dir.FullName "tools"
        if (-not (Test-Path -LiteralPath $toolsDir)) { continue }
        $count = @(Get-ChildItem -LiteralPath $toolsDir -Filter "*.json" -ErrorAction SilentlyContinue).Count
        if ($count -le 0) { continue }
        $isPlugin = $dir.Name -like "plugin-*"
        $servers.Add([ordered]@{
            server_folder = $dir.Name
            tool_count    = $count
            is_plugin     = $isPlugin
        })
        $total += $count
        if ($isPlugin) { $pluginTotal += $count }
    }
    $sorted = @($servers | Sort-Object { $_.tool_count } -Descending)
    return @{
        servers              = $sorted
        total_tool_count     = $total
        plugin_tool_count    = $pluginTotal
    }
}

function Invoke-ChildStep {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [hashtable]$Params = @{},
        [switch]$Optional
    )
    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        if ($Optional) { return 0 }
        throw "Missing script: $ScriptPath"
    }
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $ScriptPath @Params
    $code = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($code -ne 0 -and -not $Optional) {
        throw "${Name} exit $code"
    }
    return $code
}

# --- lane resolution ---
$laneSource = "default.ops"
$resolvedLane = "ops"
if ($Lane) {
    $resolvedLane = $Lane
    $laneSource = "-Lane"
}
elseif (Test-Path -LiteralPath $ResumePackJson) {
    try {
        $pack = Get-Content -LiteralPath $ResumePackJson -Raw -Encoding UTF8 | ConvertFrom-Json
        $packLane = $pack.ops_memory_options.lane
        if ($packLane) {
            $resolvedLane = [string]$packLane
            $laneSource = $ResumePackJson + " ops_memory_options.lane"
        }
    } catch {
        Write-Warning "Resume pack lane parse failed; using ops"
    }
}

$lanePreset = $presetsDoc.lanes.$resolvedLane
if (-not $lanePreset) {
    Write-Warning "Unknown lane '$resolvedLane' in presets; fallback ops"
    $resolvedLane = "ops"
    $lanePreset = $presetsDoc.lanes.ops
}

$budgetMax = [int]$presetsDoc.defaults.budget_host_remediate
if ($budgetMax -le 0) { $budgetMax = 80 }

$actionsTaken = [ordered]@{}
$stepExit = @{}

# --- chain ---
$leanScript = Join-Path $WorkspaceRoot "scripts\Invoke-McpLeanProfileAlign_v1.ps1"
if (Test-Path -LiteralPath $leanScript) {
    $stepExit["lean_align"] = Invoke-ChildStep -Name "lean_align" -ScriptPath $leanScript -Params @{
        WorkspaceRoot = $WorkspaceRoot
        SkipReadiness = $true
    } -Optional
    $actionsTaken["lean_align_ran"] = $true
} else {
    $actionsTaken["lean_align_ran"] = $false
}

if ($ApplyPluginDiet -and -not $SkipPluginDiet) {
    $persistPy = Join-Path $WorkspaceRoot "scripts\persist_cursor_mcp_disabled_servers_v1.py"
    if (Test-Path -LiteralPath $persistPy) {
        Write-Host "==> mcp_disabled_servers_sync" -ForegroundColor Cyan
        & py $persistPy sync --apply
        $stepExit["mcp_disabled_servers_sync"] = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        $actionsTaken["plugin_diet_ran"] = $true
        $actionsTaken["mcp_persist_sync_ran"] = $true
    } else {
        $dietPy = Join-Path $WorkspaceRoot "scripts\apply_cursor_mcp_plugin_diet_auto_v1.py"
        if (Test-Path -LiteralPath $dietPy) {
            Write-Host "==> plugin_diet" -ForegroundColor Cyan
            & py $dietPy
            $stepExit["plugin_diet"] = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
            $actionsTaken["plugin_diet_ran"] = $true
        } else {
            $actionsTaken["plugin_diet_ran"] = $false
        }
        $actionsTaken["mcp_persist_sync_ran"] = $false
    }
} else {
    $actionsTaken["plugin_diet_ran"] = $false
    $actionsTaken["mcp_persist_sync_ran"] = $false
}

if (-not $SkipBudgetGate) {
    $budgetScript = Join-Path $WorkspaceRoot "scripts\Invoke-McpPluginToolBudgetGate_v1.ps1"
    $stepExit["budget_gate"] = Invoke-ChildStep -Name "budget_gate" -ScriptPath $budgetScript -Params @{
        WorkspaceRoot = $WorkspaceRoot
    } -Optional
    $actionsTaken["budget_gate_ran"] = $true
} else {
    $actionsTaken["budget_gate_ran"] = $false
}

$browserScript = Join-Path $WorkspaceRoot "scripts\check_cursor_ide_browser_readiness_v1.ps1"
$stepExit["browser_check"] = Invoke-ChildStep -Name "browser_check" -ScriptPath $browserScript -Params @{
    WorkspaceRoot = $WorkspaceRoot
} -Optional
$actionsTaken["browser_check_ran"] = $true

$actionsTaken["browser_auto_fix_ran"] = $false
if (-not $SkipBrowserAutoFix) {
    $browserReportPath = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_readiness_latest.json"
    $autoFixScript = Join-Path $WorkspaceRoot "scripts\Invoke-CursorIdeBrowserAutoFix_v1.ps1"
    $needsBrowserFix = $false
    if (Test-Path -LiteralPath $browserReportPath) {
        try {
            $brDoc = Get-Content -LiteralPath $browserReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $needsBrowserFix = -not [bool]$brDoc.host_ready_for_new_chat
        } catch {
            Write-Warning "browser readiness parse failed; skip auto-fix"
        }
    }
    if ($needsBrowserFix -and (Test-Path -LiteralPath $autoFixScript)) {
        Write-Host "==> browser_auto_fix (host not ready; not mcp.json)" -ForegroundColor Yellow
        $fixArgs = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $autoFixScript,
            "-WorkspaceRoot", $WorkspaceRoot
        )
        if (-not $BrowserAutoFixWithReload) {
            $fixArgs += "-SkipReload"
        }
        & powershell.exe @fixArgs
        $stepExit["browser_auto_fix"] = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        $actionsTaken["browser_auto_fix_ran"] = $true
    }
}

$hygieneScript = Join-Path $WorkspaceRoot "scripts\check_cursor_state_vscdb_hygiene_v1.ps1"
$stepExit["hygiene_check"] = Invoke-ChildStep -Name "hygiene_check" -ScriptPath $hygieneScript -Params @{
    WorkspaceRoot = $WorkspaceRoot
} -Optional
$actionsTaken["hygiene_check_ran"] = $true

$delegationDecision = $null
if (-not $SkipDelegationGate) {
    $gateScript = Join-Path $WorkspaceRoot "scripts\Invoke-MkmDelegationResearchAssistGate_v1.ps1"
    $stepExit["delegation_gate"] = Invoke-ChildStep -Name "delegation_gate" -ScriptPath $gateScript -Params @{
        Lane = $resolvedLane
    } -Optional
    $actionsTaken["delegation_gate_ran"] = $true
    $gateJson = Join-Path $WorkspaceRoot "reports\delegation_research_assist_gate_v1_latest.json"
    if (Test-Path -LiteralPath $gateJson) {
        try {
            $gateDoc = Get-Content -LiteralPath $gateJson -Raw -Encoding UTF8 | ConvertFrom-Json
            $delegationDecision = [string]$gateDoc.decision
        } catch { }
    }
} else {
    $actionsTaken["delegation_gate_ran"] = $false
}

$profileSwitchApplied = $false
if ($ApplyProfileSwitch -and $lanePreset.switch_profile_command) {
    $prof = [string]$lanePreset.mcp_profile
    $switchScript = Join-Path $WorkspaceRoot "scripts\Switch-McpProfile.ps1"
    if ($prof -and (Test-Path -LiteralPath $switchScript)) {
        Write-Host "==> profile_switch ($prof)" -ForegroundColor Yellow
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $switchScript -Profile $prof
        $stepExit["profile_switch"] = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        $profileSwitchApplied = ($stepExit["profile_switch"] -eq 0)
    }
}
$actionsTaken["profile_switch_applied"] = $profileSwitchApplied

# --- inventory snapshot ---
$mcpsRoot = Join-Path $env:USERPROFILE ".cursor\projects\c-workspace\mcps"
$inv = Get-McpInventory -McpsRoot $mcpsRoot
$leanServerCount = 0
$mcpJsonPath = Join-Path $WorkspaceRoot ".cursor\mcp.json"
if (Test-Path -LiteralPath $mcpJsonPath) {
    try {
        $mcpJson = Get-Content -LiteralPath $mcpJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $leanServerCount = @($mcpJson.mcpServers.PSObject.Properties.Name).Count
    } catch { }
}

$topServers = @($inv.servers | Select-Object -First 6)

# --- operator actions ---
$operatorActions = [System.Collections.Generic.List[string]]::new()
if (($ApplyPluginDiet -and -not $SkipPluginDiet) -or $actionsTaken["budget_gate_ran"]) {
    $operatorActions.Add("Developer: Reload Window after plugin diet / budget gate")
}
foreach ($srv in @($lanePreset.servers_suggest_off)) {
    if ($srv) {
        $operatorActions.Add("Settings -> MCP: OFF $srv (lane suggest_off)")
    }
}
foreach ($srv in @($lanePreset.servers_suggest_on)) {
    if ($srv) {
        $operatorActions.Add("Settings -> MCP: ON $srv when this lane needs it (suggest_on)")
    }
}
if ([int]$lanePreset.browser_tier -ge 2) {
    $operatorActions.Add("Browser Tab once: Ctrl+Shift+J -> Browser Automation -> Browser Tab (or Cursor: Open Browser Tab)")
}
if ($inv.total_tool_count -gt $budgetMax) {
    $operatorActions.Add("descriptor_total $($inv.total_tool_count) > budget $budgetMax — lean_servers=$leanServerCount is separate axis; trim unused workspace MCP servers")
}
$operatorActions.Add("New Agent chat if tool catalog must refresh after Reload")

$reloadRequired = $false
$browserTabRequired = ([int]$lanePreset.browser_tier -ge 2)
$hygienePath = Join-Path $WorkspaceRoot "reports\cursor_host_hygiene_latest.json"
$hostHygieneOk = $false
if (Test-Path -LiteralPath $hygienePath) {
    try {
        $hyg = Get-Content -LiteralPath $hygienePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $hostHygieneOk = -not [bool]$hyg.degraded
        if ($hyg.reload_required) { $reloadRequired = $true }
    } catch { }
}
if ($BrowserAutoFixWithReload -and $actionsTaken["browser_auto_fix_ran"]) {
    $reloadRequired = $true
}
$browserPath = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_readiness_latest.json"
if (Test-Path -LiteralPath $browserPath) {
    try {
        $br = Get-Content -LiteralPath $browserPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $br.host_ready_for_new_chat) {
            $browserTabRequired = $true
            if ($actionsTaken["browser_auto_fix_ran"]) {
                $operatorActions.Insert(0, "Browser view still missing after auto-fix — Command Palette: Cursor: Open Browser Tab once, then Reload Window, then NEW Agent chat")
            }
        }
    } catch { }
}

$presetOut = [ordered]@{
    mcp_profile           = [string]$lanePreset.mcp_profile
    label_ko              = [string]$lanePreset.label_ko
    servers_suggest_off   = @($lanePreset.servers_suggest_off)
    servers_suggest_on    = @($lanePreset.servers_suggest_on)
    switch_profile_command = $(if ($lanePreset.switch_profile_command) { [string]$lanePreset.switch_profile_command } else { $null })
    browser_tier          = [int]$lanePreset.browser_tier
}

$inventoryOut = [ordered]@{
    lean_server_count        = $leanServerCount
    descriptor_total         = [int]$inv.total_tool_count
    plugin_descriptor_count  = [int]$inv.plugin_tool_count
    budget_max               = $budgetMax
    over_budget              = ($inv.total_tool_count -gt $budgetMax)
    top_servers_by_tools     = $topServers
}

$repro = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmMcpCoordinator_v1.ps1 -Lane $resolvedLane"
if (-not $ApplyPluginDiet) { $repro += " -ApplyPluginDiet:`$false" }

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$payload = [ordered]@{
    schema                           = "mkm_mcp_coordinator_v1"
    generated_at_utc                 = $utc
    research_only                    = $true
    send_gate                        = "HOLD"
    lane                             = $resolvedLane
    lane_source                      = $laneSource
    preset                           = $presetOut
    inventory                        = $inventoryOut
    actions_taken                    = $actionsTaken
    step_exit_codes                  = $stepExit
    operator_actions                 = @($operatorActions)
    reload_required                  = [bool]$reloadRequired
    browser_tab_required             = [bool]$browserTabRequired
    host_hygiene_ok                  = [bool]$hostHygieneOk
    delegation_research_assist_decision = $delegationDecision
    reproducible_command             = $repro
    boundary_ack                     = "Advisory coordinator only; no Track A·live·auto profile switch unless -ApplyProfileSwitch"
    ssot                             = "docs/research/mcp_runtime_budget_routing.md"
}

$outDir = Split-Path -Parent $OutJson
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$jsonText = ($payload | ConvertTo-Json -Depth 10) + "`n"
[System.IO.File]::WriteAllText($OutJson, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "WROTE: $OutJson" -ForegroundColor Green
Write-Host "lane=$resolvedLane descriptor_total=$($inv.total_tool_count) host_hygiene_ok=$hostHygieneOk send_gate=HOLD"

# Schema smoke (non-fatal)
$schemaPy = Join-Path $WorkspaceRoot "scripts\check_mkm_mcp_coordinator_schema_v1.py"
if (Test-Path -LiteralPath $schemaPy) {
    & py $schemaPy --json $OutJson
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "coordinator schema check exit $LASTEXITCODE"
    }
}

exit 0
