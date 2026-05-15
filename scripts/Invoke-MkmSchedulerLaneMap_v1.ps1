#Requires -Version 5.1
<#
.SYNOPSIS
  Windows Task Scheduler 작업을 "암행어사 / 레지스트리(아테나 번들 축) / 비트코인·예언 / 레거시 Athena_* / 기타 MKM" 레인으로 분류해 JSON을 남긴다.

.DESCRIPTION
  OPS 채팅에서 수시 실행용. 추론 없이 이름 패턴 + automation_registry.json owner로만 분류한다.
  산출: reports/mkm_scheduler_lane_map_latest.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmSchedulerLaneMap_v1.ps1
#>
param(
    [string]$WorkspaceRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$regPath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\automation_registry.json"
$regOwners = @{}
if (Test-Path -LiteralPath $regPath) {
    $doc = Get-Content -LiteralPath $regPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($row in $doc.tasks) {
        $key = [string]$row.name
        if ($key.StartsWith("\")) { $key = $key.TrimStart("\") }
        $regOwners[$key] = [string]$row.owner
    }
}

function Get-SchedulerLane {
    param([string]$TaskName)
    if ($TaskName -like "Athena_*") {
        return [ordered]@{
            lane             = "athena_legacy_scheduler"
            hint             = "Legacy Windows tasks named Athena_*; AGENTS AthenaBundle is on-demand scripts, not these names."
            registry_owner   = $null
        }
    }
    if ($TaskName -like "Bitcoin-*") {
        return [ordered]@{
            lane             = "bitcoin_trading_ops"
            hint             = "bitcoin-trading / runtime_registry rows under Bitcoin-*"
            registry_owner   = $null
        }
    }
    if ($TaskName -like "GeneralProphecy*" -or $TaskName -like "VibeDailyProphecy*") {
        return [ordered]@{
            lane             = "general_prophecy_b_rail"
            hint             = "General prophecy queue / evolution; root scripts, not Track A triggers."
            registry_owner   = $null
        }
    }
    if ($TaskName -match "AmsaengEosa|MKM_SafeOpsSurfaceCheck|SafeOpsSurface") {
        return [ordered]@{
            lane             = "amsaeng_eosa_scheduled"
            hint             = "Scope: docs/final/artifacts/amsaeng_eosa_governance_scope_v1.json; Invoke-AmsaengEosaGovernanceCycle.ps1"
            registry_owner   = $null
        }
    }
    if ($regOwners.ContainsKey($TaskName)) {
        $o = $regOwners[$TaskName]
        return [ordered]@{
            lane             = "automation_registry"
            registry_owner   = $o
            hint             = "Row in projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json (Athena persona health != this list)."
        }
    }
    if ($TaskName -eq "MKM_OrchestratorDaemon") {
        return [ordered]@{
            lane             = "mkm_orchestrator_daemon"
            hint             = "Register-MkmOrchestratorDaemonTask.ps1; logon long-loop; not in automation_registry."
            registry_owner   = $null
        }
    }
    if ($TaskName -like "MKM-*" -or $TaskName -like "MKM_*") {
        return [ordered]@{
            lane             = "mkm_platform_misc"
            hint             = "Other MKM-prefixed scheduler tasks; narrow with AGENTS.md / CONSTITUTION tables."
            registry_owner   = $null
        }
    }
    if ($TaskName -match "^(Darkflow|Showroom|MKMLIFE|Ops-|ProphecyRealtime)") {
        return [ordered]@{
            lane             = "adjacent_workspace_ops"
            hint             = "Related workspace automation; not core MKM_ prefix."
            registry_owner   = $null
        }
    }
    return [ordered]@{
        lane             = "other_matched"
        hint             = "Matched workspace filter but no finer bucket."
        registry_owner   = $null
    }
}

$filter = "MKM|Bitcoin|GeneralProphecy|Athena_|Darkflow|Showroom|MKMLIFE|Ops-|VibeDaily|ProphecyRealtime"
$tasks = @(Get-ScheduledTask | Where-Object { $_.TaskName -match $filter } | Sort-Object TaskName)

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($t in $tasks) {
    $tn = [string]$t.TaskName
    $laneInfo = Get-SchedulerLane -TaskName $tn
    $info = $null
    try { $info = Get-ScheduledTaskInfo -InputObject $t } catch {}
    $row = [ordered]@{
        task_name   = $tn
        state       = [string]$t.State
        lane        = $laneInfo.lane
        hint        = $laneInfo.hint
        last_run    = if ($info) { $info.LastRunTime } else { $null }
        last_result = if ($info) { $info.LastTaskResult } else { $null }
        next_run    = if ($info) { $info.NextRunTime } else { $null }
    }
    if ($null -ne $laneInfo.registry_owner -and "$($laneInfo.registry_owner)" -ne "") {
        $row.registry_owner = $laneInfo.registry_owner
    }
    $rows.Add([pscustomobject]$row)
}

$byLane = $rows | Group-Object lane | ForEach-Object {
    [ordered]@{ lane = $_.Name; count = $_.Count; tasks = @($_.Group | ForEach-Object { $_.task_name }) }
}

$out = [ordered]@{
    schema           = "mkm_scheduler_lane_map_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    workspace_root   = $WorkspaceRoot
    note_ko          = "AthenaBundle/P0/AmsaengHealth는 Invoke-MkmPersonaHealth_v1.ps1 페르소나로 수동·OPS 실행; Athena_* 작업 이름은 레거시 스케줄러."
    registry_path    = $regPath
    summary_by_lane  = @($byLane)
    tasks            = @($rows)
}

$outPath = Join-Path $WorkspaceRoot "reports\mkm_scheduler_lane_map_latest.json"
$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$out | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE $outPath tasks=$($rows.Count)" -ForegroundColor Green

foreach ($g in ($rows | Group-Object lane | Sort-Object Name)) {
    Write-Host ("{0,-32} {1,4}" -f $g.Name, $g.Count)
}
exit 0
