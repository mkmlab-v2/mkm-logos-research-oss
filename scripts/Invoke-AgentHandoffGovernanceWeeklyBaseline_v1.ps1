#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly Agent Handoff Governance internal baseline chain.

.DESCRIPTION
  1) Token bench refresh
  2) Ops memory lane pack (infra default)
  3) Lifecycle audit (optional -SkipLifecycle)
  4) Phase1 pack build + readiness + PUBLIC_FACING copy guard
  5) Append weekly baseline JSONL row

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AgentHandoffGovernanceWeeklyBaseline_v1.ps1
#>
param(
    [ValidateSet("infra", "oracle", "ms")]
    [string]$Lane = "infra",
    [switch]$SkipLifecycle,
    [switch]$DryRunRecord,
    [string]$CadenceNote = ""
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location -LiteralPath $root

function Invoke-PyStep($name, [string[]]$PyArgv) {
    Write-Host "==> $name" -ForegroundColor Cyan
    & py @PyArgv
    if ($LASTEXITCODE -ne 0) { throw "$name failed exit $LASTEXITCODE" }
}

Write-Host "=== Agent Handoff Governance Weekly Baseline ===" -ForegroundColor Green

Invoke-PyStep "token_bench" @("scripts/bench_mkm_ops_memory_index_token_savings_v1.py")

$opsArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", "scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1",
    "-Lane", $Lane, "-SkipBench"
)
Write-Host "==> ops_memory_lane" -ForegroundColor Cyan
& powershell @opsArgs
$opsExit = $LASTEXITCODE
if ($opsExit -ne 0) { Write-Warning "ops_memory_lane exit $opsExit (recording anyway)" }

if (-not $SkipLifecycle) {
    Write-Host "==> lifecycle_audit" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\Invoke-MkmWorkspaceLifecycleRoutine_v1.ps1"
    if ($LASTEXITCODE -ne 0) { throw "lifecycle_audit failed exit $LASTEXITCODE" }
}

Invoke-PyStep "phase1_pack_build" @("scripts/build_agent_handoff_governance_phase1_pack_v1.py")

$targets = @(
    "docs\final\artifacts\agent_handoff_governance_enterprise_onepager_v1_latest.md",
    "docs\final\artifacts\agent_handoff_governance_enterprise_onepager_v1_latest.json"
)
foreach ($t in $targets) {
    Write-Host "==> copy_guard $t" -ForegroundColor Cyan
    & py "scripts/check_track_c_copy_guard_v1.py" $t
    if ($LASTEXITCODE -ne 0) { throw "copy_guard failed for $t exit $LASTEXITCODE" }
}

Invoke-PyStep "phase1_readiness" @("scripts/check_agent_handoff_governance_phase1_readiness_v1.py")

Invoke-PyStep "public_facing_scan" @("scripts/check_agent_handoff_governance_public_facing_scan_v1.py")

$intakePath = "reports\agent_handoff_governance_internal_pilot_intake_mkm_internal_v1.json"
if (Test-Path -LiteralPath (Join-Path $root $intakePath)) {
    Invoke-PyStep "internal_pilot_intake" @("scripts/check_agent_handoff_governance_internal_pilot_intake_v1.py")
}

$recordArgs = @("scripts/record_agent_handoff_governance_weekly_baseline_v1.py", "--lane", $Lane, "--ops-memory-exit-code", "$opsExit")
if ($DryRunRecord) { $recordArgs += "--dry-run" }
if ($CadenceNote) { $recordArgs += @("--cadence-note", $CadenceNote) }
Invoke-PyStep "weekly_baseline_record" $recordArgs

Write-Host "OK: Invoke-AgentHandoffGovernanceWeeklyBaseline_v1 completed" -ForegroundColor Green
exit 0
