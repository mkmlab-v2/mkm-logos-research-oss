#Requires -Version 5.1
<#
.SYNOPSIS
  Audit MKM Task Scheduler vs solo core stack SSOT; optionally disable named batches.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1 -ApplyDisable -BatchFilter btrack_dup_daily,prophecy_sandbox_fail

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1 -EnforceSoloBand
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$StackJson = "",
    [string]$OutJson = "",
    [string]$BatchFilter = "",
    [switch]$ApplyDisable,
    [switch]$DryRunOnly,
    [switch]$WhatIfOnly,
    [switch]$EnforceSoloBand
)

if ($WhatIfOnly) { $DryRunOnly = $true }

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($StackJson)) {
    $StackJson = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_scheduler_solo_core_stack_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\mkm_scheduler_solo_core_stack_audit_v1_latest.json"
}

if (-not (Test-Path -LiteralPath $StackJson)) {
    throw "Missing stack SSOT: $StackJson"
}

$stack = Get-Content -LiteralPath $StackJson -Raw -Encoding UTF8 | ConvertFrom-Json

$coreAll = @()
foreach ($key in @("tier0_core_daily", "tier1_core_weekly", "tier2_keep_event", "tier3_optional_active")) {
    if ($stack.PSObject.Properties.Name -contains $key) {
        $coreAll += @($stack.$key)
    }
}
$coreSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($n in $coreAll) { [void]$coreSet.Add($n.Trim()) }

$tier4All = @()
if ($stack.PSObject.Properties.Name -contains "tier4_solo_intentional_keep") {
    $tier4All += @($stack.tier4_solo_intentional_keep)
}
$allowedSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($n in ($coreAll + $tier4All)) {
    $t = ([string]$n).Trim()
    if ($t) { [void]$allowedSet.Add($t) }
}

function Test-SoloStackReadyRow {
    param([object]$Row)
    $tn = ([string]$Row.TaskName).Trim()
    if ($Row.Status -ne 'Ready') { return $false }
    if ($tn -match '\\MKM') { return $true }
    if ($tn -match 'GeneralProphecy') { return $true }
    if ($tn -match 'Showroom-TrackC') { return $true }
    return $false
}

$allCsv = schtasks /Query /FO CSV | ConvertFrom-Csv
$readyMkm = @($allCsv | Where-Object { $_.TaskName -match '\\MKM' -and $_.Status -eq 'Ready' })
$soloStackReady = @($allCsv | Where-Object { Test-SoloStackReadyRow $_ })
$extraReady = @($soloStackReady | Where-Object { $_.TaskName -notmatch '\\MKM' })

$allReady = $soloStackReady
$readyNames = $allReady | ForEach-Object { $_.TaskName.Trim() } | Sort-Object -Unique

$disablePlan = New-Object System.Collections.ArrayList
$batchIds = @()
if (-not [string]::IsNullOrWhiteSpace($BatchFilter)) {
    $batchIds = $BatchFilter -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

if ($ApplyDisable -or $DryRunOnly) {
    $allBatchNames = @($stack.disable_batches.PSObject.Properties | ForEach-Object { $_.Name })
    $batchesToRun = if ($batchIds.Count -gt 0) { $batchIds } else { $allBatchNames }
    foreach ($batchId in $batchesToRun) {
        if ($allBatchNames -notcontains $batchId) {
            [void]$disablePlan.Add(@{
                batch = $batchId
                task_name = $null
                action = "skip_unknown_batch"
                reason = "batch id not in stack JSON"
            })
            continue
        }
        $batchDef = $stack.disable_batches.$batchId
        $taskList = @()
        if ($null -ne $batchDef.tasks) {
            $taskList = @($batchDef.tasks | ForEach-Object { ([string]$_).Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        }
        foreach ($tn in $taskList) {
            $name = $tn.Trim().TrimStart('\')
            $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
            if (-not $task) {
                [void]$disablePlan.Add(@{
                    batch = $batchId
                    task_name = $name
                    action = "skip_missing"
                    reason = [string]$batchDef.reason
                })
                continue
            }
            if ($task.State.ToString() -eq 'Disabled') {
                [void]$disablePlan.Add(@{
                    batch = $batchId
                    task_name = $name
                    action = "already_disabled"
                    reason = [string]$batchDef.reason
                })
                continue
            }
            if ($coreSet.Contains($tn) -or $coreSet.Contains("\" + $name)) {
                [void]$disablePlan.Add(@{
                    batch = $batchId
                    task_name = $name
                    action = "blocked_core_tier"
                    reason = [string]$batchDef.reason
                })
                continue
            }
            if ($ApplyDisable -and -not $DryRunOnly) {
                try {
                    Disable-ScheduledTask -TaskName $name -ErrorAction Stop | Out-Null
                    $act = "disabled"
                }
                catch {
                    $act = "disable_failed"
                }
            }
            else {
                $act = "would_disable"
            }
            [void]$disablePlan.Add(@{
                batch = $batchId
                task_name = $name
                action = $act
                reason = [string]$batchDef.reason
            })
        }
    }
}

$candidates = @()
$unauthorized = @()
foreach ($n in $readyNames) {
    $norm = if ($n.StartsWith('\')) { $n } else { "\" + $n }
    $short = $norm.TrimStart('\')
    $info = Get-ScheduledTaskInfo -TaskName $short -ErrorAction SilentlyContinue
    $rowObj = [ordered]@{
        task_name = $short
        last_result = if ($info) { [string]$info.LastTaskResult } else { $null }
        last_run_local = if ($info -and $info.LastRunTime) { $info.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss") } else { $null }
    }
    if (-not $allowedSet.Contains($norm)) {
        $unauthorized += $rowObj
    }
    if ($coreSet.Contains($norm)) { continue }
    $candidates += $rowObj
}

$bandMin = 0
$bandMax = 48
if ($stack.PSObject.Properties.Name -contains "solo_target_ready_band") {
  $b = $stack.solo_target_ready_band
  if ($null -ne $b.min) { $bandMin = [int]$b.min }
  if ($null -ne $b.max) { $bandMax = [int]$b.max }
}
$soloStackCount = @($soloStackReady).Count
$overBandMax = $soloStackCount -gt $bandMax
$bandOk = (-not $overBandMax) -and (@($unauthorized).Count -eq 0)
$bandGate = [ordered]@{
    band_min = $bandMin
    band_max = $bandMax
    solo_stack_ready = $soloStackCount
    mkm_ready = @($readyMkm).Count
    unauthorized_ready_count = @($unauthorized).Count
    unauthorized_ready_sample = @($unauthorized | Select-Object -First 25)
    over_band_max = $overBandMax
    ok = $bandOk
    enforce = [bool]$EnforceSoloBand
}

$audit = [ordered]@{
    schema = "mkm_scheduler_solo_core_stack_audit_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    stack_json = $StackJson
    counts = [ordered]@{
        mkm_ready = @($readyMkm).Count
        solo_stack_ready = $soloStackCount
        extra_ready = @($extraReady).Count
        core_tier_total = $coreSet.Count
        tier4_intentional_keep = @($tier4All).Count
        allowed_ready_total = $allowedSet.Count
        disable_candidates_not_in_core = $candidates.Count
        unauthorized_ready = @($unauthorized).Count
    }
    band_gate = $bandGate
    core_tiers = [ordered]@{
        tier0_core_daily = @($stack.tier0_core_daily)
        tier1_core_weekly = @($stack.tier1_core_weekly)
        tier2_keep_event = @($stack.tier2_keep_event)
        tier3_optional_active = @($stack.tier3_optional_active)
    }
    disable_plan = @($disablePlan.ToArray())
    ready_not_in_core_sample = $candidates | Select-Object -First 40
    apply_mode = if ($ApplyDisable -and -not $DryRunOnly) { "apply" } elseif ($DryRunOnly) { "dry_run" } else { "audit_only" }
}

$outDir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$jsonText = $audit | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($OutJson, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "=== MKM scheduler solo core stack audit ===" -ForegroundColor Cyan
Write-Host "solo_stack_ready: $($audit.counts.solo_stack_ready) (band $bandMin-$bandMax) | MKM Ready: $($audit.counts.mkm_ready) | core: $($audit.counts.core_tier_total) | tier4: $($audit.counts.tier4_intentional_keep) | unauthorized: $($audit.counts.unauthorized_ready) | plan=$($disablePlan.Count)"
Write-Host "band_gate ok: $bandOk" -ForegroundColor $(if ($bandOk) { 'Green' } else { 'Yellow' })
Write-Host "Artifact: $OutJson" -ForegroundColor DarkGray

if (-not $bandOk) {
    if ($overBandMax) {
        Write-Host "BAND_FAIL: solo_stack_ready $soloStackCount > max $bandMax" -ForegroundColor Red
    }
    if (@($unauthorized).Count -gt 0) {
        Write-Host "SPRAWL_FAIL: $($unauthorized.Count) Ready task(s) not in core+tier4 SSOT (sample below)" -ForegroundColor Red
        $unauthorized | Select-Object -First 10 | ForEach-Object { Write-Host "  - $($_.task_name)" -ForegroundColor DarkYellow }
    }
}

if ($disablePlan.Count -gt 0) {
    Write-Host ""
    Write-Host "Disable plan ($($audit.apply_mode)):" -ForegroundColor Yellow
    $disablePlan | ForEach-Object {
        Write-Host "  [$($_.action)] $($_.task_name) ($($_.batch))"
    }
}

if ($EnforceSoloBand -and -not $bandOk) { exit 1 }
exit 0
