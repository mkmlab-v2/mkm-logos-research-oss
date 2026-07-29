<#
.SYNOPSIS
  Cursor session upgrade — context diet + lane resume pack + rhythm hints + human_gate ([HYPO] B-track inject).

.DESCRIPTION
  One entry for session start (replaces ad-hoc solo ops + index + pack chain):
  1) Solo background ops if today last_ok is false
  2) Ops memory index + resume pack (coordinate inject, no full MISSION_LOG paste)
  3) Rhythm suggestion (daily Amsaeng / weekly Athena — report only, no auto heavy run)
  4) human_gate reminder (TITAN + amsaeng_eosa scope)

  Does NOT run: live trade, Track A promotion, K-Startup 340 submit, secret export, destructive ops.

.PARAMETER Lane
  oracle | ms | infra | web_ops — omit for default top-3 pins.

.PARAMETER SkipSoloOps
  Skip Invoke-MkmSoloBackgroundOps even when stale.

.PARAMETER SkipIndexRebuild
  Only rebuild resume pack from existing index (faster follow-up in same lane).

.PARAMETER SkipL2Shadow
  Skip Tier 2 L2 shadow log append after resume pack (human MD unchanged either way).

.PARAMETER SkipTier3WireHandoff
  Skip Tier 3 parallel-chat wire handoff when -Lane is set (default: Tier 3 runs automatically with -Lane).

.PARAMETER ResumeMode
  Standard (default) or AdvancedLogos — maps to commander trigger 「장기기억 맥락이어 고급해석」 (forces -Lane oracle when omitted).

.PARAMETER SkipResumeForceGate
  Skip disk resume-force gate (default = "on" meaning gate runs unless this switch or MKM_RESUME_FORCE_GATE=0).

.PARAMETER SkipOneshotContract
  Skip oneshot contract advisory refresh (ACTIVE_LANE/ONE_SHOT_GOAL/DONE_WHEN + pin/hygiene).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1 -Lane oracle
#>
param(
    [ValidateSet("", "oracle", "ms", "infra", "web_ops")]
    [string]$Lane = "",
    [ValidateSet("", "Standard", "AdvancedLogos")]
    [string]$ResumeMode = "",
    [switch]$SkipSoloOps,
    [switch]$SkipIndexRebuild,
    [switch]$SkipL2Shadow,
    [switch]$SkipTier3WireHandoff,
    [switch]$SkipBrowserAutoFix,
    [switch]$SkipResumeForceGate,
    [switch]$SkipOneshotContract
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $root

if ($ResumeMode -eq "AdvancedLogos" -and -not $Lane) {
    $Lane = "oracle"
}
$resumeModePy = if ($ResumeMode -eq "AdvancedLogos") { "advanced_logos" } else { "standard" }

$steps = [ordered]@{}
$ok = $true
$utcNow = (Get-Date).ToUniversalTime()
$localDate = (Get-Date).ToString("yyyy-MM-dd")

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    try {
        & $Block
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        $steps[$Name] = @{ exit_code = $code; ok = ($code -eq 0) }
        if ($code -ne 0) { $script:ok = $false }
        return $code
    } catch {
        $steps[$Name] = @{ exit_code = 1; ok = $false; error = $_.Exception.Message }
        $script:ok = $false
        return 1
    }
}

# --- S3: solo ops (today) ---
$soloStatePath = Join-Path $root "reports\mkm_solo_background_ops_state.json"
$soloRan = $false
$soloSkipped = $true
if (-not $SkipSoloOps -and (Test-Path -LiteralPath $soloStatePath)) {
    $soloState = Get-Content -LiteralPath $soloStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($soloState.last_run_local_date -ne $localDate -or -not $soloState.last_ok) {
        $soloSkipped = $false
        Invoke-Step "solo_background_ops" {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-MkmSoloBackgroundOps_v1.ps1")
        } | Out-Null
        $soloRan = $true
    }
} elseif (-not $SkipSoloOps) {
    $soloSkipped = $false
    Invoke-Step "solo_background_ops" {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-MkmSoloBackgroundOps_v1.ps1")
    } | Out-Null
    $soloRan = $true
}

# --- IDE Browser: warmup (no reload) then full auto-fix if still not ready (non-fatal) ---
if (-not $SkipBrowserAutoFix) {
    $warmup = Join-Path $root "scripts\Invoke-CursorIdeBrowserWarmup_v1.ps1"
    $browserFix = Join-Path $root "scripts\Invoke-CursorIdeBrowserAutoFix_v1.ps1"
    if (Test-Path -LiteralPath $warmup) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $warmup -WorkspaceRoot $root | Out-Null
        $warmupExit = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        $steps["ide_browser_warmup"] = @{ exit_code = $warmupExit; non_fatal = $true }
    }
    $readinessPath = Join-Path $root "reports\cursor_ide_browser_readiness_latest.json"
    $hostReady = $false
    if (Test-Path -LiteralPath $readinessPath) {
        try {
            $rd = Get-Content -LiteralPath $readinessPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $hostReady = [bool]$rd.host_ready_for_new_chat
        } catch { }
    }
    if (-not $hostReady -and (Test-Path -LiteralPath $browserFix)) {
        Write-Host "Browser host not ready after warmup — running AUTO fix with Reload..." -ForegroundColor Yellow
        powershell -NoProfile -ExecutionPolicy Bypass -File $browserFix -WorkspaceRoot $root | Out-Null
        $browserFixExit = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        $steps["ide_browser_auto_fix"] = @{ exit_code = $browserFixExit; non_fatal = $true }
        if ($browserFixExit -ne 0) {
            Write-Host "WARN: ide_browser_auto_fix exit $browserFixExit — NEW Agent chat after Reload" -ForegroundColor Yellow
        }
    }
}

# --- S2: ops memory index + resume pack (coordinate inject) ---
$opsRoutine = Join-Path $root "scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1"
if ($SkipIndexRebuild) {
    $packArgs = @("py", "scripts/build_mkm_chat_resume_pack_v1.py", "--resume-mode", $resumeModePy)
    if ($Lane) { $packArgs += @("--lane", $Lane, "--infer-topic-from-lane") }
    Invoke-Step "resume_pack_only" {
        & $packArgs[0] $packArgs[1..($packArgs.Length - 1)]
    } | Out-Null
} else {
    $routineArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $opsRoutine,
        "-SkipBench"
    )
    if ($Lane) { $routineArgs += @("-Lane", $Lane) }
    if ($ResumeMode) { $routineArgs += @("-ResumeMode", $ResumeMode) }
    Invoke-Step "ops_memory_index_and_resume_pack" {
        powershell @routineArgs
    } | Out-Null
}

if (-not $SkipL2Shadow) {
    $shadowArgs = @("py", "scripts/build_a2a_l2_shadow_measurement_v1.py", "--append-log")
    if ($Lane) { $shadowArgs += @("--lane", $Lane) }
    Invoke-Step "l2_shadow_measurement" {
        & $shadowArgs[0] $shadowArgs[1..($shadowArgs.Length - 1)]
    } | Out-Null
}

if ($Lane -and -not $SkipTier3WireHandoff) {
    $tier3Args = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', (Join-Path $root 'scripts\Run-A2aTier3CursorWireHandoffPilot_v1.ps1'),
        '-Lane', $Lane, '-AppendLog', '-StrictExit'
    )
    Invoke-Step "tier3_wire_handoff_pilot" {
        powershell @tier3Args
    } | Out-Null
}

# --- Pillar A: LTM deep handoff envelope (resume + handoff + tier3 path only) ---
$envelopeLane = if ($Lane) { $Lane } else { "infra" }
$envelopeArgs = @("py", "scripts/build_mkm_cursor_deep_handoff_envelope_v1.py", "--lane", $envelopeLane)
Invoke-Step "deep_handoff_envelope" {
    & $envelopeArgs[0] $envelopeArgs[1..($envelopeArgs.Length - 1)]
} | Out-Null

# --- Pillar A: graph resolve → patch envelope deep_fetch (suspect-first coordinates) ---
$resolveArgs = @("py", "scripts/resolve_deep_fetch_from_handoff_v1.py", "--lane", $envelopeLane, "--patch-envelope")
Invoke-Step "deep_fetch_resolve_patch" {
    & $resolveArgs[0] $resolveArgs[1..($resolveArgs.Length - 1)]
} | Out-Null

$envelopeArtifact = Join-Path $root "docs\final\artifacts\mkm_cursor_deep_handoff_envelope_v1_latest.json"
$envelopeReports = Join-Path $root "reports\mkm_cursor_deep_handoff_envelope_v1_latest.json"

# --- Context diet audit (report only; strict gate is separate CI/pytest) ---
Invoke-Step "cursor_rules_context_diet" {
    py (Join-Path $root "scripts\check_cursor_rules_context_diet_v1.py")
} | Out-Null

# --- 3-lens horizon reintro guard (fail-closed: sets upgrade ok=false on non-zero) ---
Invoke-Step "three_lens_forbidden_reintro_guard" {
    py (Join-Path $root "scripts\check_mkm_three_lens_forbidden_reintro_guard_v1.py") --strict
} | Out-Null

# --- Rhythm suggestion (report only — no auto Amsaeng/Athena on session start) ---
$dow = (Get-Date).DayOfWeek.value__
$rhythm = [ordered]@{
    daily_suggestion = 'Invoke-MkmPersonaHealth_v1.ps1 -Persona AmsaengHealth'
    daily_trigger_ko = 'AmsaengHealth persona / amsaeng eosa daily'
    weekly_suggestion = 'Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle'
    weekly_trigger_ko = 'AthenaBundle persona / weekly Sunday suggested'
    weekly_due = ($dow -eq 0)
    note_ko = 'Session start stays light; heavy health on commander trigger or weekly'
}

# --- human_gate (TITAN + amsaeng scope) ---
$humanGate = [ordered]@{
    scope_ssot = 'docs/final/artifacts/amsaeng_eosa_governance_scope_v1.json'
    titan_ssot = '.cursorrules'
    requires_human = @(
        'live_trading ENABLE_TRADING VPS order activation'
        'Track_A promotion MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT overwrite'
        'K-Startup OpenData 340 portal submit by commander only'
        'secrets .env DPAPI keys in chat or commit'
        'destructive delete hard reset irreversible schema'
    )
    agent_never = 'Agent must not auto-run promote submit or expose secrets; observe and low_risk automate only'
}

$resumePackJson = Join-Path $root "docs\final\artifacts\mkm_chat_resume_pack_latest.json"
$resumePackMd = Join-Path $root "docs\final\artifacts\mkm_chat_resume_pack_latest.md"
$pinCount = 0
if (Test-Path -LiteralPath $resumePackJson) {
    $pack = Get-Content -LiteralPath $resumePackJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($pack.ops_memory_pins) { $pinCount = @($pack.ops_memory_pins).Count }
}

$contextDiet = [ordered]@{
    commander_trigger_ko = if ($ResumeMode -eq "AdvancedLogos") { "장기기억 맥락이어 고급해석" } else { "장기기억 맥락이어" }
    commander_triggers_ssot = "docs/final/artifacts/mkm_commander_resume_triggers_v1.json"
    resume_mode = $resumeModePy
    read_first = $resumePackMd
    read_second = $envelopeArtifact
    read_third = "MISSION_LOG.md"
    required_ssot_contract = "docs/final/artifacts/mkm_meta_coordinator_turn_contract_v1_latest.md"
    agent_self_check = "suspect_first — doubt chat memory; verify CONSTITUTION+exit0; envelope.agent_self_check"
    oneshot_first_reply = "ACTIVE_LANE= · ONE_SHOT_GOAL= · DONE_WHEN= (3 lines; Day1 Azure HQ underperform advice)"
    oneshot_contract_ssot = "docs/final/artifacts/mkm_resume_oneshot_contract_v1_latest.md"
    oneshot_contract_cmd = 'py scripts/run_mkm_resume_oneshot_contract_v1.py --lane <lane> --goal "..." --done-when "..."'
    session_end_command = 'py scripts/run_mkm_cursor_session_end_v1.py --lane <lane> --continuity-id <id> --message "<line>"'
    read_fallback = "docs/final/CENTRAL_AGENT_MEMORY_V1.md (checkpoint block only)"
    never_on_resume = "Full MISSION_LOG.md paste; alwaysApply expansion"
    mission_log_mode = "resume pack next_one table pin only (commander default)"
    inject_mode = "essence + must_keep_tags + commander slices on CENTRAL+next_one ([HYPO] B-track)"
    nl_sync_ssot = "reports/notebooklm_ltm_graph_ops_push_result_v1_latest.json"
    token_bench_ssot = "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
}

$reproCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1"
if ($Lane) { $reproCmd += " -Lane $Lane" }
if ($ResumeMode) { $reproCmd += " -ResumeMode $ResumeMode" }

# --- Resume force gate (default ON; write upgrade stamp first so age check can pass) ---
$forceGateEnv = ($env:MKM_RESUME_FORCE_GATE | ForEach-Object { "$_".Trim().ToLowerInvariant() })
$forceGateSkipEnv = @("0", "false", "no", "off") -contains $forceGateEnv
$oneshotAdvisory = $null
$forceGateStatus = $null

# Pre-write upgrade stamp so force gate sees a fresh artifact (chicken-egg fix).
$preWrite = [ordered]@{
    schema = "mkm_cursor_session_upgrade_v1"
    generated_at_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    last_run_local_date = $localDate
    ok = $ok
    lane = if ($Lane) { $Lane } else { $null }
    resume_mode = if ($ResumeMode) { $ResumeMode } else { "Standard" }
    solo_ops_ran = $soloRan
    solo_ops_skipped_already_ok = $soloSkipped
    resume_pack_pins = $pinCount
    context_diet = $contextDiet
    rhythm = $rhythm
    human_gate = $humanGate
    steps = $steps
    boundary_ack = '[HYPO] ops memory inject - Track A live trading auto-merge forbidden'
    deep_handoff_envelope = $envelopeArtifact
    deep_handoff_envelope_reports = $envelopeReports
    reproducible_command = $reproCmd
    prewrite = $true
}
$reportDir = Join-Path $root "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$outPath = Join-Path $reportDir "mkm_cursor_session_upgrade_v1_latest.json"
($preWrite | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $outPath -Encoding UTF8

if ((-not [bool]$SkipResumeForceGate) -and -not $forceGateSkipEnv) {
    Invoke-Step "resume_force_gate" {
        py (Join-Path $root "scripts\run_mkm_resume_force_gate_v1.py") --trigger-phrase "장기기억 맥락이어"
    } | Out-Null
    $fgPath = Join-Path $root "docs\final\artifacts\mkm_resume_force_gate_v1_latest.json"
    if (Test-Path -LiteralPath $fgPath) {
        try {
            $fg = Get-Content -LiteralPath $fgPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $forceGateStatus = $fg.status
        } catch { }
    }
}

if (-not $SkipOneshotContract) {
    # Advisory only — do not fail upgrade when oneshot fields unset (agent fills post-resume).
    $osArgs = @("py", (Join-Path $root "scripts\run_mkm_resume_oneshot_contract_v1.py"), "--check-only")
    try {
        & $osArgs[0] $osArgs[1..($osArgs.Length - 1)] | Out-Null
        $osCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    } catch {
        $osCode = 1
    }
    $steps["resume_oneshot_contract_advisory"] = @{ exit_code = $osCode; non_fatal = $true }
    $osPath = Join-Path $root "docs\final\artifacts\mkm_resume_oneshot_contract_v1_latest.json"
    if (Test-Path -LiteralPath $osPath) {
        try {
            $oneshotAdvisory = Get-Content -LiteralPath $osPath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch { }
    }
}

$latest = [ordered]@{
    schema = "mkm_cursor_session_upgrade_v1"
    generated_at_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    last_run_local_date = $localDate
    ok = $ok
    lane = if ($Lane) { $Lane } else { $null }
    resume_mode = if ($ResumeMode) { $ResumeMode } else { "Standard" }
    solo_ops_ran = $soloRan
    solo_ops_skipped_already_ok = $soloSkipped
    resume_pack_pins = $pinCount
    context_diet = $contextDiet
    rhythm = $rhythm
    human_gate = $humanGate
    steps = $steps
    resume_force_gate_status = $forceGateStatus
    resume_oneshot_execution_mode = if ($oneshotAdvisory) { $oneshotAdvisory.execution_mode } else { $null }
    boundary_ack = '[HYPO] ops memory inject - Track A live trading auto-merge forbidden'
    deep_handoff_envelope = $envelopeArtifact
    deep_handoff_envelope_reports = $envelopeReports
    reproducible_command = $reproCmd
}

($latest | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host "WROTE: $outPath"
$laneLabel = if ($Lane) { $Lane } else { "default" }
$osMode = if ($oneshotAdvisory) { $oneshotAdvisory.execution_mode } else { "n/a" }
Write-Host "CURSOR_SESSION_UPGRADE_OK=$ok pins=$pinCount lane=$laneLabel force_gate=$forceGateStatus oneshot_mode=$osMode"
if (-not $ok) { exit 1 }
exit 0
