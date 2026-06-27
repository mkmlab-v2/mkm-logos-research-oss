#Requires -Version 5.1

<#

.SYNOPSIS

  Fact-Lock 페르소나 래퍼 — 고정 스크립트만 호출한다 (판단·추측 금지, exit code SSOT).



.DESCRIPTION

  AGENTS.md 「페르소나 단축 호출」표와 1:1. 추가 스위치는 하위 스크립트를 직접 호출할 것.



.PARAMETER Persona

  AthenaBundle = run_fact_lock_bundle.ps1

  PremiumMultilensQueue = Invoke-PremiumMultilensQueueRoutine_v1.ps1 (pytest 4 + drain allow-missing + S1 promotion gate --skip-pytest)

  AmsaengHealth = run_workspace_automation_health.ps1 (기본 인자만)

  P0 = verify_p0_constitution_gate_paths.ps1

  AramaicDailyReadiness = Verify-AramaicMvpDailyTaskReadiness.ps1 (Windows Task Scheduler; 미등록 시 실패)

  GpuRecommendedBundle = run_workspace_automation_health.ps1 -MkmGpuRecommendedBundleOnly (P0 + reconcile + Run-MkmGpuRecommendedBundle_v1)

  LinkedInB2bWeekly = run_linkedin_b2b_weekly_draft_chain_v1.ps1 (assemble-only + copy guard; no publish)

  LinkedInB2bWeeklyReadiness = Verify-LinkedInB2bWeeklyDraftTaskReadiness.ps1 (Windows Task Scheduler)

  MarketingWeeklyBundle = Run-MarketingWeeklyDraftBundle_v1.ps1 (tier_0 default; unified queue + LinkedIn + summary)

  MarketingWeeklyBundleReadiness = Verify-MarketingWeeklyDraftBundleTaskReadiness_v1.ps1

  ShowroomTrackCHealth = Invoke-ShowroomTrackCHealth_v1.ps1 (task verify + dual-host smoke + lens media hub QA + B2B readiness)

  BtrackProphecyLightRefresh = Run-BtrackProphecyOpsLightRefresh_v1.ps1 (briefing + mkmlife envelope; no full daily chain)

  BtrackProphecyDailyReadiness = Verify-BtrackProphecyDailyOpsReadiness_v1.ps1 (tasks + chain wiring)

  KospiJune2026DailyReadiness = Verify-KospiJune2026ProphecyEveningTask.ps1 (morning+evening weekday tasks)

  LocalGpuWeeklyRoutine = Run-LocalGpuWeeklyRoutine_v1.ps1 (CPU gates + counsel ZIP; optional -IncludeAudioGenerate on runner directly)

  LocalGpuWeeklyRoutineReadiness = Verify-MkmLocalGpuWeeklyRoutineTaskReadiness_v1.ps1 (Windows Task Scheduler)

  TrackCB2bRehearsalPrep = Invoke-TrackCB2bInternalRehearsalPrep_v1.ps1 (15min script + counsel ZIP + gates; no send)

  ScienceCoreLaneReadiness = Invoke-ScienceCoreLaneReadiness_v1.ps1 (check_science_core_lane_readiness_v1.py; no full governance)

  ScienceCoreWeeklyReadiness = Verify-ScienceCoreWeeklyGovernanceTask_v1.ps1 (Windows Task Scheduler)

  ScienceCoreGovernance = Run-ScienceCoreGovernanceBundle_v1.ps1 -UseFullHumanistPerDate -RunHumanistAb -RunLogosAb -RunLongWalkforward -ExtendCalendarStubs -RebuildScience -RunNewsWeightAblation -RunLongWindowLaneCompare -RunTripleBlendWeightSweep -RunPnlBootstrap

  PrismMetaChannelStaging = Invoke-PrismMetaChannelStaging_v1.ps1 -Action Verify (sign-off + live smoke)

  PrismMetaChannelStagingStatus = Invoke-PrismMetaChannelStaging_v1.ps1 -Action Status

  WebOpsRegimeBundle = Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1 (bundle+overlay+bench; -SkipLiveCdp)

  WebOpsRegimeReadiness = Verify-WebOpsRegimeWeeklyTaskReadiness_v1.ps1 (Task MKM_WebOps_Regime_Weekly)

  OpsMemoryWebOps = route_mkm_ops_memory_pack_v1.py --topic Nebius web_ops --build-resume-pack

  ParallelPassiveLoop = Invoke-ParallelPassiveLoop_v1.ps1 (shim + L1 canary + MAX_HYPO gate + web_ops fusion; parallel)

  MultiResIndexDelegation = Invoke-MultiResIndexDelegationRoutine_v1.ps1 (P0 + multi-res pytest + index + ops overlay + delegation)

  CursorSessionUpgrade = Invoke-MkmCursorSessionUpgrade_v1.ps1 (solo ops + ops memory index + lane resume pack + human_gate report)
  HighDelegationPreflight = Invoke-MkmHighDelegationPreflight_v1.ps1 (P0 + MCP host + browser host + NL gate + optional approval map)

  BoundedLaneLoopShadow = run_workspace_automation_health.ps1 -BoundedLaneLoopSmokeOnly (P0 + bounded lane pytest + dry-run invoke)

  MkmAgentLoops = Invoke-MkmAgentLoopsRoutine_v1.ps1 (SSOT kickoff md + P0 + context diet strict)

  DocSyncSafe = Invoke-MkmDocSyncSafe_v1.ps1

  TestRecoverySafe = Invoke-MkmTestRecoverySafe_v1.ps1

  CursorAutomationsRoutine = Invoke-MkmCursorAutomationsRoutine_v1.ps1 -Mode recommended (local_only 권장 체인)
  AutonomousPatrol = Invoke-MkmAutonomousPatrol_v1.ps1 (-ContinueOnFail; chat 「자율점검」)



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona PremiumMultilensQueue



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AmsaengHealth



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona P0



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AramaicDailyReadiness



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona GpuRecommendedBundle

#>

param(

    [Parameter(Mandatory = $true, Position = 0)]

    [ValidateSet('AthenaBundle', 'PremiumMultilensQueue', 'AmsaengHealth', 'P0', 'AramaicDailyReadiness', 'GpuRecommendedBundle', 'LinkedInB2bWeekly', 'LinkedInB2bWeeklyReadiness', 'MarketingWeeklyBundle', 'MarketingWeeklyBundleReadiness', 'MarketingPublishPhase2', 'ShowroomTrackCHealth', 'BtrackProphecyLightRefresh', 'BtrackProphecyDailyReadiness', 'KospiJune2026DailyReadiness', 'LogosTrackL0', 'LogosTrackL1', 'LocalGpuWeeklyRoutine', 'LocalGpuWeeklyRoutineReadiness', 'TrackCB2bRehearsalPrep', 'ScienceCoreLaneReadiness', 'ScienceCoreWeeklyReadiness', 'ScienceCoreGovernance', 'PrismMetaChannelStaging', 'PrismMetaChannelStagingStatus', 'WebOpsRegimeBundle', 'WebOpsRegimeReadiness', 'OpsMemoryWebOps', 'ParallelPassiveLoop', 'AiToAiGovernanceDelegation', 'MultiResIndexDelegation', 'CursorSessionUpgrade', 'HighDelegationPreflight', 'DelegationResearchAssist', 'HdAutonomousEvolution', 'BoundedLaneLoopShadow', 'MkmAgentLoops', 'CursorAutomationsRoutine', 'AutonomousPatrol', 'DocSyncSafe', 'TestRecoverySafe', 'MkmlifePortalCommercialization', 'MkmlifePortalCommercializationLive', 'PersonadiaryPortalDesign', 'JemaaiShowroomHubFooterLive', 'MkmDomainDesignClosure', 'DesignLane')]

    [string]$Persona

)



Set-StrictMode -Version Latest

$ErrorActionPreference = 'Stop'



$WorkspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {

    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')

} else {

    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

}



if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {

    throw "WorkspaceRoot not found: $WorkspaceRoot"

}



Push-Location -LiteralPath $WorkspaceRoot

try {

    $ps = 'powershell.exe'

    $common = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File')



    switch ($Persona) {

        'AthenaBundle' {

            $script = Join-Path $PSScriptRoot 'run_fact_lock_bundle.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'PremiumMultilensQueue' {

            $script = Join-Path $PSScriptRoot 'Invoke-PremiumMultilensQueueRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'AmsaengHealth' {

            $script = Join-Path $PSScriptRoot 'run_workspace_automation_health.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -IncludeProphecyBtrackScheduledOpsSmoke

            exit $LASTEXITCODE

        }

        'P0' {

            $script = Join-Path $PSScriptRoot 'verify_p0_constitution_gate_paths.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'AramaicDailyReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-AramaicMvpDailyTaskReadiness.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'GpuRecommendedBundle' {

            $script = Join-Path $PSScriptRoot 'run_workspace_automation_health.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot -MkmGpuRecommendedBundleOnly

            exit $LASTEXITCODE

        }

        'LinkedInB2bWeekly' {

            $script = Join-Path $PSScriptRoot 'run_linkedin_b2b_weekly_draft_chain_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'LinkedInB2bWeeklyReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-LinkedInB2bWeeklyDraftTaskReadiness.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'MarketingWeeklyBundle' {

            $script = Join-Path $PSScriptRoot 'Run-MarketingWeeklyDraftBundle_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'MarketingWeeklyBundleReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-MarketingWeeklyDraftBundleTaskReadiness_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'MarketingPublishPhase2' {

            $script = Join-Path $PSScriptRoot 'Invoke-MarketingPublishPhase2_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'ShowroomTrackCHealth' {

            $script = Join-Path $PSScriptRoot 'Invoke-ShowroomTrackCHealth_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'BtrackProphecyLightRefresh' {

            $script = Join-Path $PSScriptRoot 'Run-BtrackProphecyOpsLightRefresh_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'BtrackProphecyDailyReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-BtrackProphecyDailyOpsReadiness_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'KospiJune2026DailyReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-KospiJune2026ProphecyEveningTask.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'LogosTrackL0' {

            $script = Join-Path $PSScriptRoot 'run_logos_track_l_l0_readiness_v1.py'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & py -3 $script

            exit $LASTEXITCODE

        }

        'LogosTrackL1' {

            $script = Join-Path $PSScriptRoot 'run_logos_track_l_l1_readiness_v1.py'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & py -3 $script

            exit $LASTEXITCODE

        }

        'LocalGpuWeeklyRoutine' {

            $script = Join-Path $PSScriptRoot 'Run-LocalGpuWeeklyRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'LocalGpuWeeklyRoutineReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-MkmLocalGpuWeeklyRoutineTaskReadiness_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'TrackCB2bRehearsalPrep' {

            $script = Join-Path $PSScriptRoot 'Invoke-TrackCB2bInternalRehearsalPrep_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'ScienceCoreLaneReadiness' {

            $script = Join-Path $PSScriptRoot 'Invoke-ScienceCoreLaneReadiness_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'ScienceCoreWeeklyReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-ScienceCoreWeeklyGovernanceTask_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'ScienceCoreGovernance' {

            $script = Join-Path $PSScriptRoot 'Run-ScienceCoreGovernanceBundle_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -UseFullHumanistPerDate -RunHumanistAb -RunLogosAb -RunLongWalkforward -ExtendCalendarStubs -RebuildScience -RunNewsWeightAblation -RunLongWindowLaneCompare -RunTripleBlendWeightSweep -RunPnlBootstrap

            exit $LASTEXITCODE

        }

        'PrismMetaChannelStaging' {

            $script = Join-Path $PSScriptRoot 'Invoke-PrismMetaChannelStaging_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -Action Verify

            exit $LASTEXITCODE

        }

        'PrismMetaChannelStagingStatus' {

            $script = Join-Path $PSScriptRoot 'Invoke-PrismMetaChannelStaging_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -Action Status

            exit $LASTEXITCODE

        }

        'WebOpsRegimeBundle' {

            $script = Join-Path $PSScriptRoot 'Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -SkipLiveCdp -RequireDualAlignment

            exit $LASTEXITCODE

        }

        'WebOpsRegimeReadiness' {

            $script = Join-Path $PSScriptRoot 'Verify-WebOpsRegimeWeeklyTaskReadiness_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'OpsMemoryWebOps' {

            $route = Join-Path $PSScriptRoot 'route_mkm_ops_memory_pack_v1.py'

            if (-not (Test-Path -LiteralPath $route)) { throw "Missing: $route" }

            & py $route --topic 'Nebius web_ops cost audit' --build-resume-pack

            exit $LASTEXITCODE

        }

        'ParallelPassiveLoop' {

            $script = Join-Path $PSScriptRoot 'Invoke-ParallelPassiveLoop_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'AiToAiGovernanceDelegation' {

            $script = Join-Path $PSScriptRoot 'Invoke-AiToAiGovernanceDelegation_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'MultiResIndexDelegation' {

            $script = Join-Path $PSScriptRoot 'Invoke-MultiResIndexDelegationRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'CursorSessionUpgrade' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmCursorSessionUpgrade_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'BoundedLaneLoopShadow' {

            $script = Join-Path $PSScriptRoot 'run_workspace_automation_health.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -BoundedLaneLoopSmokeOnly

            exit $LASTEXITCODE

        }

        'MkmAgentLoops' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmAgentLoopsRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'CursorAutomationsRoutine' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmCursorAutomationsRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -Mode recommended -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'AutonomousPatrol' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmAutonomousPatrol_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot -ContinueOnFail

            exit $LASTEXITCODE

        }

        'DocSyncSafe' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmDocSyncSafe_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'TestRecoverySafe' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmTestRecoverySafe_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -WorkspaceRoot $WorkspaceRoot

            exit $LASTEXITCODE

        }

        'MkmlifePortalCommercialization' {

            $script = Join-Path $PSScriptRoot 'Run-MkmlifePortalCommercializationGate_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'MkmlifePortalCommercializationLive' {

            $script = Join-Path $PSScriptRoot 'Run-MkmlifePortalCommercializationGate_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script -IncludeLiveSmoke -IncludePlaywright

            exit $LASTEXITCODE

        }

        'PersonadiaryPortalDesign' {

            $script = Join-Path $PSScriptRoot 'Run-PersonadiaryPortalDesignSmoke_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'JemaaiShowroomHubFooterLive' {

            $script = Join-Path $PSScriptRoot 'Run-JemaaiShowroomHubFooterLiveSmoke_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'MkmDomainDesignClosure' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmDomainDesignClosureBundle_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'DesignLane' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmDesignLaneRoutine_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            & $ps @common $script

            exit $LASTEXITCODE

        }

        'DelegationResearchAssist' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmDelegationResearchAssistGate_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            $gateArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $script)

            if ($env:MKM_DELEGATION_RESEARCH_LANE) {
                $gateArgs += @('-Lane', $env:MKM_DELEGATION_RESEARCH_LANE)
            }

            if ($env:MKM_DELEGATION_RESEARCH_TOPIC) {
                $gateArgs += @('-Topic', $env:MKM_DELEGATION_RESEARCH_TOPIC)
            }

            & powershell @gateArgs

            exit $LASTEXITCODE

        }

        'HighDelegationPreflight' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmHighDelegationPreflight_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            $pfArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $script)

            $scale = if ($env:MKM_HIGH_DELEGATION_SCALE) { $env:MKM_HIGH_DELEGATION_SCALE } else { 'M' }
            $pfArgs += @('-Scale', $scale)

            if ($env:MKM_HIGH_DELEGATION_LANE) {
                $pfArgs += @('-Lane', $env:MKM_HIGH_DELEGATION_LANE)
            }

            if ($env:MKM_HIGH_DELEGATION_APPROVAL_MAP) {
                $pfArgs += @('-ApprovalMap', $env:MKM_HIGH_DELEGATION_APPROVAL_MAP)
            }

            & powershell @pfArgs

            exit $LASTEXITCODE

        }

        'HdAutonomousEvolution' {

            $script = Join-Path $PSScriptRoot 'Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1'

            if (-not (Test-Path -LiteralPath $script)) { throw "Missing: $script" }

            $aeArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $script)

            $mission = if ($env:MKM_HD_AE_MISSION) {
                $env:MKM_HD_AE_MISSION
            } else {
                'B-track high-delegation intel + swarm stage1 accumulation observability'
            }
            $aeArgs += @('-Mission', $mission)

            $lane = if ($env:MKM_HD_AE_LANE) { $env:MKM_HD_AE_LANE } else { 'oracle' }
            $aeArgs += @('-Lane', $lane)

            $tier = if ($env:MKM_HD_AE_COST_TIER) { $env:MKM_HD_AE_COST_TIER } else { 'tier_0' }
            $aeArgs += @('-CostTier', $tier)

            if ($env:MKM_HD_AE_MAX_QUALITY_PASSES) {
                $aeArgs += @('-MaxQualityPasses', $env:MKM_HD_AE_MAX_QUALITY_PASSES)
            }

            if ($env:MKM_HD_AE_SKIP_SWARM -match '^(1|true|yes|on)$') {
                $aeArgs += '-SkipSwarmRun'
            }

            if ($env:MKM_HD_AE_SKIP_LIVE_ATPROTO -match '^(1|true|yes|on)$') {
                $aeArgs += '-SkipIntelLiveAtproto'
            }

            & powershell @aeArgs

            exit $LASTEXITCODE

        }

        default {

            throw "Unhandled Persona: $Persona"

        }

    }

}

finally {

    Pop-Location

}

