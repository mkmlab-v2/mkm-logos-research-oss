<#
.SYNOPSIS
  고차원 자율진화 v1 — pre-approved mission → preflight → intel → swarm → A2A → completion.

.DESCRIPTION
  가성비(tier_0 기본) + 품질 우선(시간 비구속) 자율 루프.
  Completion: exit 0 + reports/hd_autonomous_evolution_completion_v1_latest.json + reproducible_command.

  [HYPO] / research_only — Track A·live·apply-active 자동 승격 없음.

.PARAMETER Mission
  One-line mission (한 줄 임무).

.PARAMETER Lane
  oracle | prophecy | ops | infra | design | web_ops | ms

.PARAMETER CostTier
  tier_0 (default) | tier_15 — SSOT marketing_ops_cost_tier_v1_latest.json

.PARAMETER MaxQualityPasses
  Quality retry cap (default 5). Same error twice → skip optional node on pass 2+.

.EXAMPLE
  powershell -File scripts\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1 `
    -Mission "B-track intel+swarm tier_a observability" -Lane oracle

.EXAMPLE
  Invoke-MkmPersonaHealth_v1.ps1 -Persona HdAutonomousEvolution
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$Mission = "B-track high-delegation intel + swarm stage1 accumulation observability",
    [ValidateSet("oracle", "prophecy", "ops", "infra", "design", "web_ops", "ms")]
    [string]$Lane = "oracle",
    [ValidateSet("tier_0", "tier_15")]
    [string]$CostTier = "tier_0",
    [int]$MaxQualityPasses = 5,
    [string]$ApprovalMap = "",
    [string]$GithubOwner = "bluesky-social",
    [string]$GithubRepo = "atproto",
    [switch]$SkipSwarmRun,
    [switch]$SkipIntelLiveAtproto,
    [switch]$IncludeP0P1P2Hybrid,
    [switch]$IncludeTelegramDailyWiring,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $root

if (-not $ApprovalMap) {
    $ApprovalMap = Join-Path $root "reports\delegation_hd_autonomous_evolution_approval_map_v1_latest.json"
}

$missionPath = Join-Path $root "reports\hd_autonomous_evolution_mission_v1_latest.json"
$stepsPath = Join-Path $root "reports\hd_autonomous_evolution_run_steps_v1_latest.json"
$completionPath = Join-Path $root "reports\hd_autonomous_evolution_completion_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("o")

$repro = @(
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1",
    "-Mission `"$Mission`"",
    "-Lane $Lane",
    "-CostTier $CostTier"
) -join " "

# Node 0 — mission envelope
$missionObj = [ordered]@{
    schema               = "hd_autonomous_evolution_mission_v1"
    generated_at_utc     = $utc
    mission_line         = $Mission
    lane                 = $Lane
    cost_tier            = $CostTier
    max_quality_passes   = $MaxQualityPasses
    approval_map         = $ApprovalMap.Replace($root + '\', '').Replace('\', '/')
    hypothesis_tag       = "[HYPO]"
    research_only        = $true
    boundary_ack         = "Pre-approved autonomous loop; no Track A/live/Final Action auto-merge."
    reproducible_command = $repro
    definition_ssot      = "docs/final/artifacts/mkm_high_dimensional_autonomous_evolution_v1_latest.json"
}
($missionObj | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $missionPath -Encoding utf8

if ($DryRun) {
    Write-Host "DryRun: mission written to $missionPath"
    exit 0
}

function Add-NodeStep {
    param([string]$Id, [int]$ExitCode, [string]$Note = "", [switch]$Skipped)
    $script:runSteps.nodes[$Id] = [ordered]@{
        exit_code = $ExitCode
        ok        = ($ExitCode -eq 0)
        note      = $Note
        skipped   = [bool]$Skipped
        at_utc    = (Get-Date).ToUniversalTime().ToString("o")
    }
}

$qualityOk = $false
$finalExit = 1

for ($pass = 1; $pass -le $MaxQualityPasses; $pass++) {
    $runSteps = [ordered]@{
        schema           = "hd_autonomous_evolution_run_steps_v1"
        quality_pass     = $pass
        max_passes       = $MaxQualityPasses
        started_at_utc   = $utc
        nodes            = [ordered]@{}
    }

    # NL MCP auth refresh (tier_0, non-fatal — prevents 24h state expiry)
    $nlRepair = Join-Path $root 'scripts\Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1'
    if (Test-Path -LiteralPath $nlRepair) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $nlRepair
        $nlCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        Add-NodeStep -Id "nl" -ExitCode $nlCode -Note $(if ($nlCode -eq 0) { "authenticated_ok" } else { "non_fatal_continue" })
    }

    # Node 1 — preflight
    $pfArgs = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        (Join-Path $root 'scripts\Invoke-MkmHighDelegationPreflight_v1.ps1'),
        '-Scale', 'L', '-Lane', $Lane, '-ApprovalMap', $ApprovalMap
    )
    & powershell @pfArgs
    $pfCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    Add-NodeStep -Id "1" -ExitCode $pfCode

    if ($pfCode -ne 0 -and $pass -lt $MaxQualityPasses) {
        ($runSteps | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $stepsPath -Encoding utf8
        continue
    }

    # Node 2p — P0+P1+완화 P2 hybrid wiring (optional mission package)
    if ($IncludeP0P1P2Hybrid) {
        & py (Join-Path $root 'scripts\run_p0_p1_p2_hybrid_batch_v1.py')
        $hybridCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        Add-NodeStep -Id "2p" -ExitCode $hybridCode
    } else {
        Add-NodeStep -Id "2p" -ExitCode 0 -Note "IncludeP0P1P2Hybrid not set" -Skipped
    }

    # Node 2t — Telegram daily P0 preflight + digest dry-run (tier_0 · P3 forbidden)
    if ($IncludeTelegramDailyWiring) {
        & py (Join-Path $root 'scripts\run_telegram_daily_p0_preflight_v1.py')
        $tgP0Code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        Add-NodeStep -Id "2t" -ExitCode $tgP0Code -Note "telegram_p0_preflight"
        if ($tgP0Code -eq 0) {
            & py (Join-Path $root 'scripts\send_telegram_minimal_ops_digest_v1.py') `
                --dry-run --scheduled-morning --force
            $tgDryCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
            Add-NodeStep -Id "2t2" -ExitCode $tgDryCode -Note "telegram_digest_dry_run"
        } else {
            Add-NodeStep -Id "2t2" -ExitCode 1 -Note "skipped_digest_preflight_failed"
        }
    } else {
        Add-NodeStep -Id "2t" -ExitCode 0 -Note "IncludeTelegramDailyWiring not set" -Skipped
        Add-NodeStep -Id "2t2" -ExitCode 0 -Note "IncludeTelegramDailyWiring not set" -Skipped
    }

    # Node 2 — intel
    $intelArgs = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        (Join-Path $root 'scripts\Invoke-BtrackHighDelegationIntel_v1.ps1'),
        '-Scale', 'L', '-Lane', $Lane, '-ApprovalMap', $ApprovalMap,
        '-SkipPreflight', '-IncludeSwarmDownstream',
        '-GithubOwner', $GithubOwner, '-GithubRepo', $GithubRepo
    )
    if (-not $SkipIntelLiveAtproto) { $intelArgs += '-LiveAtproto' }
    & powershell @intelArgs
    $intelCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    Add-NodeStep -Id "2" -ExitCode $intelCode

    # Node 3 — swarm accumulation
    if ($SkipSwarmRun) {
        Add-NodeStep -Id "3" -ExitCode 0 -Note "SkipSwarmRun" -Skipped
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Invoke-BTrackSwarmStage1DailyAccumulation_v1.ps1')
        $swCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        Add-NodeStep -Id "3" -ExitCode $swCode
    }

    # Node 4 — ops memory + resume pack
    & py (Join-Path $root 'scripts\build_mkm_ops_memory_index_v1.py')
    $opsCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    if ($opsCode -ne 0 -and $pass -ge 2) {
        Add-NodeStep -Id "4" -ExitCode 0 -Note "ops_index_failed_pass2_skip" -Skipped
    } else {
        Add-NodeStep -Id "4" -ExitCode $opsCode
        if ($opsCode -eq 0) {
            $resumeLane = switch ($Lane) {
                "prophecy" { "oracle" }
                "ops"      { "infra" }
                "design"   { "web_ops" }
                default    { $Lane }
            }
            if ($resumeLane -in @('oracle', 'ms', 'infra', 'web_ops')) {
                & py (Join-Path $root 'scripts\build_mkm_chat_resume_pack_v1.py') --lane $resumeLane
            } else {
                & py (Join-Path $root 'scripts\build_mkm_chat_resume_pack_v1.py')
            }
        }
    }

    # Node 5 — NL gate (tier_0: gate only, chat in agent turn)
    if ($CostTier -eq "tier_0") {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\Invoke-MkmDelegationResearchAssistGate_v1.ps1') -Lane $Lane -Topic $Mission
        $nlCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        Add-NodeStep -Id "5" -ExitCode $nlCode -Note "REVIEW chat-only tier_0"
    } else {
        Add-NodeStep -Id "5" -ExitCode 0 -Note "tier_15 NL optional" -Skipped
    }

    Add-NodeStep -Id "0" -ExitCode 0 -Note "mission_envelope"

    ($runSteps | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $stepsPath -Encoding utf8

    # Node 6 — completion
    $compArgs = @(
        (Join-Path $root 'scripts\build_hd_autonomous_evolution_completion_v1.py'),
        '--quality-pass', [string]$pass,
        '--max-quality-passes', [string]$MaxQualityPasses,
        '--steps-json', $stepsPath,
        '--patch-approval-map'
    )
    & py @compArgs
    $compCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }

    if (Test-Path -LiteralPath $completionPath) {
        # Python writes UTF-8 (no BOM); default Get-Content encoding breaks Korean JSON on Windows.
        $comp = Get-Content -LiteralPath $completionPath -Raw -Encoding utf8 | ConvertFrom-Json
        $qualityOk = [bool]$comp.quality_ok
    }

    Add-NodeStep -Id "6" -ExitCode $compCode
    ($runSteps | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $stepsPath -Encoding utf8

    if ($qualityOk) {
        $finalExit = 0
        break
    }

    if ($pass -ge $MaxQualityPasses) {
        $finalExit = 0
        Write-Warning "MaxQualityPasses reached; completion artifact written with quality_ok=$qualityOk"
        break
    }

    Start-Sleep -Seconds 2
}

Write-Host "HD autonomous evolution pass done quality_ok=$qualityOk artifact=$completionPath"
exit $finalExit
