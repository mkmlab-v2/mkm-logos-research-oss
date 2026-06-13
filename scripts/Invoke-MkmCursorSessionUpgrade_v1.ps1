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

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1 -Lane oracle
#>
param(
    [ValidateSet("", "oracle", "ms", "infra", "web_ops")]
    [string]$Lane = "",
    [switch]$SkipSoloOps,
    [switch]$SkipIndexRebuild,
    [switch]$SkipL2Shadow,
    [switch]$SkipTier3WireHandoff
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $root

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

# --- S2: ops memory index + resume pack (coordinate inject) ---
$opsRoutine = Join-Path $root "scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1"
if ($SkipIndexRebuild) {
    $packArgs = @("py", "scripts/build_mkm_chat_resume_pack_v1.py")
    if ($Lane) { $packArgs += @("--lane", $Lane) }
    Invoke-Step "resume_pack_only" {
        & $packArgs[0] $packArgs[1..($packArgs.Length - 1)]
    } | Out-Null
} else {
    $routineArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $opsRoutine,
        "-SkipBench"
    )
    if ($Lane) { $routineArgs += @("-Lane", $Lane) }
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

# --- Context diet audit (report only; strict gate is separate CI/pytest) ---
Invoke-Step "cursor_rules_context_diet" {
    py (Join-Path $root "scripts\check_cursor_rules_context_diet_v1.py")
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
    commander_trigger_ko = "장기기억 맥락이어"
    read_first = $resumePackMd
    read_fallback = "docs/final/CENTRAL_AGENT_MEMORY_V1.md (checkpoint block only)"
    never_on_resume = "Full MISSION_LOG.md paste; alwaysApply expansion"
    mission_log_mode = "resume pack next_one table pin only (commander default)"
    inject_mode = "essence + must_keep_tags + commander slices on CENTRAL+next_one ([HYPO] B-track)"
    nl_sync_ssot = "reports/notebooklm_ltm_graph_ops_push_result_v1_latest.json"
    token_bench_ssot = "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
}

$latest = [ordered]@{
    schema = "mkm_cursor_session_upgrade_v1"
    generated_at_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    last_run_local_date = $localDate
    ok = $ok
    lane = if ($Lane) { $Lane } else { $null }
    solo_ops_ran = $soloRan
    solo_ops_skipped_already_ok = $soloSkipped
    resume_pack_pins = $pinCount
    context_diet = $contextDiet
    rhythm = $rhythm
    human_gate = $humanGate
    steps = $steps
    boundary_ack = '[HYPO] ops memory inject - Track A live trading auto-merge forbidden'
    reproducible_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1" + $(if ($Lane) { " -Lane $Lane" } else { "" })
}

$reportDir = Join-Path $root "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$outPath = Join-Path $reportDir "mkm_cursor_session_upgrade_v1_latest.json"
($latest | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host "WROTE: $outPath"
$laneLabel = if ($Lane) { $Lane } else { "default" }
Write-Host "CURSOR_SESSION_UPGRADE_OK=$ok pins=$pinCount lane=$laneLabel"
if (-not $ok) { exit 1 }
exit 0
