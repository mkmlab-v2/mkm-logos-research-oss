#Requires -Version 5.1
<#
.SYNOPSIS
  MKM 자율점검 — solo_ops + 일/주간 patrol + Git/CI readiness + manual queue.

.DESCRIPTION
  SSOT: docs/final/artifacts/mkm_command_package_manifest_v1.json (package AutonomousPatrol)
  Manual Tier-3: docs/final/artifacts/mkm_autonomous_patrol_manual_tasks_v1.json

  Daily (default): solo_ops(if stale) → DailyOpsPatrol(-ContinueOnFail)
  Weekly (Sunday or -ForceWeekly): solo_ops → WeeklyOpsPatrol(-ContinueOnFail)
  Non-fatal: git/ci readiness snapshot, pre_push AutoLocal, resume pack merge

.PARAMETER ForceWeekly
  Run WeeklyOpsPatrol even on non-Sunday.

.PARAMETER SkipSoloOps
  Skip Invoke-MkmSoloBackgroundOps even when stale.

.PARAMETER ContinueOnFail
  Continue after optional step failures (default ON).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmAutonomousPatrol_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmAutonomousPatrol_v1.ps1 -ForceWeekly -ContinueOnFail
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$ForceWeekly,
    [switch]$SkipSoloOps,
    [switch]$ContinueOnFail,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $PSBoundParameters.ContainsKey("ContinueOnFail")) {
    $ContinueOnFail = $true
}

$localDate = (Get-Date).ToString("yyyy-MM-dd")
$utcNow = (Get-Date).ToUniversalTime()
$isSunday = ([int](Get-Date).DayOfWeek -eq 0)
$runWeekly = $ForceWeekly.IsPresent -or $isSunday
$patrolPackage = if ($runWeekly) { "WeeklyOpsPatrol" } else { "DailyOpsPatrol" }

$manualSsotPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_autonomous_patrol_manual_tasks_v1.json"
$manualSsot = $null
if (Test-Path -LiteralPath $manualSsotPath) {
    $manualSsot = Get-Content -LiteralPath $manualSsotPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$steps = [ordered]@{}
$manualQueue = [System.Collections.Generic.List[object]]::new()
$ok = $true
$requiredFailed = $false

function Add-ManualItem {
    param([string]$Id, [string]$LabelKo, [string]$Reason, [string]$Command = "")
    $script:manualQueue.Add([ordered]@{
        id       = $Id
        label_ko = $LabelKo
        reason   = $Reason
        command  = $Command
    }) | Out-Null
}

function Invoke-TrackedStep {
    param(
        [string]$Name,
        [scriptblock]$Block,
        [bool]$Required = $false,
        [bool]$NonFatal = $true
    )
    if ($DryRun) {
        Write-Host "DRY_RUN: $Name"
        $steps[$Name] = @{ exit_code = 0; dry_run = $true; required = $Required }
        return 0
    }
    Write-Host ""
    Write-Host "==> [$Name]" -ForegroundColor Cyan
    & $Block | Out-Null
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = @{ exit_code = $code; required = $Required; non_fatal = $NonFatal }
    if ($code -ne 0) {
        if ($Required) {
            $script:requiredFailed = $true
            $script:ok = $false
            if (-not $ContinueOnFail) {
                throw "Required step failed: $Name (exit $code)"
            }
            Write-Host "    REQUIRED FAIL exit $code (continuing)" -ForegroundColor Red
        } else {
            Write-Host "    optional fail exit $code" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    exit 0" -ForegroundColor Green
    }
    return $code
}

function Test-PathMatchesGlob {
    param([string]$RelPath, [string]$Glob)
    $norm = ($RelPath -replace '\\', '/').TrimStart('./')
    $g = ($Glob -replace '\\', '/')
    # Escape regex specials except * which becomes .*
    $rx = [regex]::Escape($g) -replace '\\\*', '.*'
    return [regex]::IsMatch($norm, '^' + $rx + '$', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Get-DirtyTreeNoiseClassification {
    param([string[]]$RelPaths, [string]$AllowlistPath)
    $out = [ordered]@{
        total_count          = @($RelPaths).Count
        noise_count          = 0
        actionable_count     = 0
        noise_only           = $false
        allowlist_path       = $AllowlistPath
        allowlist_loaded     = $false
        sample_actionable    = @()
        sample_noise         = @()
    }
    $globs = @()
    if (Test-Path -LiteralPath $AllowlistPath) {
        try {
            $doc = Get-Content -LiteralPath $AllowlistPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($doc.path_globs) { $globs = @($doc.path_globs) }
            $out.allowlist_loaded = $true
        } catch { }
    }
    foreach ($p in @($RelPaths)) {
        $rel = ($p -replace '\\', '/').TrimStart('./')
        $isNoise = $false
        foreach ($g in $globs) {
            if (Test-PathMatchesGlob -RelPath $rel -Glob ([string]$g)) {
                $isNoise = $true
                break
            }
        }
        if ($isNoise) {
            $out.noise_count++
            if ($out.sample_noise.Count -lt 5) { $out.sample_noise += $rel }
        } else {
            $out.actionable_count++
            if ($out.sample_actionable.Count -lt 5) { $out.sample_actionable += $rel }
        }
    }
    $out.noise_only = ($out.total_count -gt 0 -and $out.actionable_count -eq 0)
    return $out
}

function Get-GitCiReadiness {
    $result = [ordered]@{
        head_sha            = $null
        internal_main_sha   = $null
        origin_main_sha     = $null
        internal_ahead_of_origin = $null
        dirty_file_count    = 0
        dirty_paths         = @()
        branch              = $null
        ok                  = $true
        notes               = @()
    }
    try {
        $result.head_sha = (git rev-parse HEAD 2>$null).Trim()
        $result.branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    } catch { $result.notes += "git_head_unavailable" }

    foreach ($pair in @(
        @{ key = "internal_main_sha"; ref = "internal/main" },
        @{ key = "origin_main_sha"; ref = "origin/main" },
        @{ key = "github_main_sha"; ref = "github/main" },
        @{ key = "hq_main_sha"; ref = "hq/main" }
    )) {
        $rev = $null
        try {
            $rev = (git rev-parse $pair.ref 2>$null).Trim()
        } catch { }
        if ($rev) { $result[$pair.key] = $rev.Substring(0, [Math]::Min(12, $rev.Length)) }
    }

    if (-not $result.origin_main_sha -and $result.github_main_sha) {
        $result.origin_main_sha = $result.github_main_sha
        $result.notes += "origin/main_missing_using_github/main"
    }

    if ($result.internal_main_sha -and $result.origin_main_sha) {
        $cnt = $null
        try {
            $cnt = (git rev-list --count "origin/main..internal/main" 2>$null).Trim()
        } catch { }
        if (-not $cnt -and $result.github_main_sha) {
            try {
                $cnt = (git rev-list --count "github/main..internal/main" 2>$null).Trim()
            } catch { }
        }
        if ($cnt -match '^\d+$') {
            $result.internal_ahead_of_origin = [int]$cnt
        }
    }

    $porcelain = @(git status --porcelain 2>$null)
    $paths = @()
    foreach ($line in $porcelain) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        # porcelain: XY PATH or XY ORIG -> PATH
        $rest = $line.Substring(3).Trim()
        if ($rest -match ' -> ') {
            $rest = ($rest -split ' -> ', 2)[1]
        }
        $paths += ($rest -replace '\\', '/')
    }
    $result.dirty_file_count = $paths.Count
    $result.dirty_paths = $paths
    return $result
}

function Write-AutonomousPatrolStickyAlert {
    param(
        [string]$OutPath,
        [string]$LocalDate,
        [object]$TaskInfo,
        [string]$Overall,
        [bool]$RequiredFailed,
        [string]$PasteLine
    )
    $lastResult = $null
    $lastRun = $null
    $nextRun = $null
    if ($null -ne $TaskInfo) {
        try { $lastResult = [int64][uint32]$TaskInfo.LastTaskResult } catch { $lastResult = $TaskInfo.LastTaskResult }
        $lastRun = $TaskInfo.LastRunTime
        $nextRun = $TaskInfo.NextRunTime
    }
    $alert = $false
    $reasons = New-Object System.Collections.Generic.List[string]
    # 267009=SCHED_S_TASK_RUNNING (IgnoreNew collision); 0x41300-0x41308 = scheduler status, not script exit
    $benignSched = @(267008, 267009, 267010, 267011, 267012, 267013, 267014, 267015, 267016)
    $lr = if ($null -ne $lastResult) { [int64]$lastResult } else { $null }
    # exit 2 = AutonomousPatrol WARN (optional fails only) — not sticky alert
    if ($null -ne $lr -and $lr -eq 2) {
        [void]$reasons.Add("scheduled_last_task_result_warn_exit_2")
    } elseif ($null -ne $lr -and $lr -ne 0 -and ($benignSched -notcontains $lr)) {
        $alert = $true
        [void]$reasons.Add("scheduled_last_task_result_nonzero")
    } elseif ($null -ne $lr -and ($benignSched -contains $lr)) {
        [void]$reasons.Add("scheduled_last_task_result_benign_sched_status")
    }
    if ($RequiredFailed -or $Overall -eq "FAIL") {
        $alert = $true
        [void]$reasons.Add("this_run_required_fail")
    }
    $hint = if ($alert) {
        "schedule LastTaskResult!=0 or this run FAIL - triage reports/mkm_autonomous_patrol_latest.json + daily.log. AutonomousPatrol != remote Actions green."
    } elseif ($null -ne $lr -and $lr -eq 2) {
        "sticky soft-clear - LastTaskResult=2 (WARN optional fails) is not sticky alert"
    } else {
        "sticky clear - scheduled LastTaskResult=0 and this run not FAIL"
    }
    $doc = [ordered]@{
        schema              = "mkm_autonomous_patrol_sticky_alert_v1"
        generated_at_utc    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
        local_date          = $LocalDate
        alert               = $alert
        severity            = $(if ($alert) { "WARN" } else { "OK" })
        task_name           = "MKM_AutonomousPatrol_Daily"
        last_task_result    = $lastResult
        last_run_time       = $(if ($lastRun) { $lastRun.ToString("o") } else { $null })
        next_run_time       = $(if ($nextRun) { $nextRun.ToString("o") } else { $null })
        this_run_overall    = $Overall
        reasons             = @($reasons)
        paste_line          = $PasteLine
        commander_hint_ko   = $hint
        webhook_sent        = $false
        webhook_note_ko     = "webhook not wired in AutonomousPatrol; JSON+paste only"
        metacog_before_ok_claim = "py scripts/run_mkm_claim_adversarial_reread_v1.py --claim-text `"...`""
    }
    $dir = Split-Path -Parent $OutPath
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    ($doc | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $OutPath -Encoding UTF8
    return $doc
}

Write-Host "MKM AutonomousPatrol ($localDate) package=$patrolPackage weekly=$runWeekly" -ForegroundColor Green

# --- solo_ops (today stale) ---
$soloStatePath = Join-Path $WorkspaceRoot "reports\mkm_solo_background_ops_state.json"
$soloNeeded = $true
if (Test-Path -LiteralPath $soloStatePath) {
    try {
        $soloState = Get-Content -LiteralPath $soloStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($soloState.last_run_local_date -eq $localDate -and $soloState.last_ok -eq $true) {
            $soloNeeded = $false
        }
    } catch { }
}

if ($SkipSoloOps) {
    $steps["solo_ops"] = @{ exit_code = 0; skipped = $true; reason = "SkipSoloOps" }
    Write-Host "==> [solo_ops] skipped (-SkipSoloOps)" -ForegroundColor DarkGray
} elseif (-not $soloNeeded) {
    $steps["solo_ops"] = @{ exit_code = 0; skipped = $true; reason = "today_last_ok" }
    Write-Host "==> [solo_ops] skipped (today last_ok)" -ForegroundColor DarkGray
} else {
    $soloCode = Invoke-TrackedStep -Name "solo_ops" -Required $false -NonFatal $true {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmSoloBackgroundOps_v1.ps1") -WorkspaceRoot $WorkspaceRoot
    }
    if ($soloCode -ne 0) {
        Add-ManualItem -Id "solo_ops_remediation" -LabelKo "solo_ops failed step review" -Reason "solo_ops exit $soloCode" -Command "powershell -File scripts\Invoke-MkmSoloBackgroundOps_v1.ps1"
    }
}

# --- git / CI readiness (read-only) ---
$gitCi = Get-GitCiReadiness
$allowlistPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_ops_dirty_tree_noise_allowlist_v1.json"
$dirtyClass = Get-DirtyTreeNoiseClassification -RelPaths @($gitCi.dirty_paths) -AllowlistPath $allowlistPath
$gitCi.dirty_noise = $dirtyClass
$steps["git_ci_readiness"] = @{ exit_code = 0; snapshot = $gitCi; required = $false }
Write-Host ""
Write-Host "==> [git_ci_readiness] branch=$($gitCi.branch) dirty=$($gitCi.dirty_file_count) noise=$($dirtyClass.noise_count) actionable=$($dirtyClass.actionable_count) internal_ahead_origin=$($gitCi.internal_ahead_of_origin)" -ForegroundColor Cyan

if ($gitCi.dirty_file_count -gt 0) {
    if ($dirtyClass.noise_only) {
        Add-ManualItem -Id "ops_artifact_noise_review" `
            -LabelKo "생성 아티팩트 dirty $($dirtyClass.noise_count) (allowlist) — commit 강제 아님; stash -u 금지" `
            -Reason "dirty_noise_only" `
            -Command "git status -sb; Read docs/final/artifacts/mkm_ops_dirty_tree_noise_allowlist_v1.json"
    } else {
        $dirtyLabel = "uncommitted $($dirtyClass.actionable_count) actionable + $($dirtyClass.noise_count) noise - commit/stash(no -u) before push"
        Add-ManualItem -Id "git_commit_or_stash" -LabelKo $dirtyLabel -Reason "working_tree_dirty" -Command "git status -sb"
    }
}
if ($null -ne $gitCi.internal_ahead_of_origin -and $gitCi.internal_ahead_of_origin -ge 5) {
    $ghReason = "internal/main ahead of origin/main by $($gitCi.internal_ahead_of_origin) commits"
    Add-ManualItem -Id "github_explicit_push" -LabelKo "GitHub mirror push optional" -Reason $ghReason -Command "scripts\Push-GitHub-Explicit.ps1 -Acknowledge"
}

# --- pre_push AutoLocal (non-fatal) ---
Invoke-TrackedStep -Name "pre_push_autolocal" -Required $false {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-CursorPrePushReview_v1.ps1") -AutoLocal
} | Out-Null

# --- main patrol package ---
$pkgScript = Join-Path $WorkspaceRoot "scripts\Invoke-MkmCommandPackage_v1.ps1"
$pkgArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $pkgScript, "-Package", $patrolPackage)
if ($ContinueOnFail) { $pkgArgs += "-ContinueOnFail" }

$patrolCode = Invoke-TrackedStep -Name "patrol_$patrolPackage" -Required $false -NonFatal $true {
    powershell @pkgArgs
}
$pastePath = Join-Path $WorkspaceRoot "reports\mkm_command_package_paste_latest.json"
$patrolRequiredFailed = ($patrolCode -ne 0)
if ((Test-Path -LiteralPath $pastePath) -and -not $DryRun) {
    try {
        $paste = Get-Content -LiteralPath $pastePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $patrolRequiredFailed = [bool]$paste.required_failed
        $steps["patrol_$patrolPackage"].patrol_required_failed = $patrolRequiredFailed
        $steps["patrol_$patrolPackage"].optional_fail_count = [int]$paste.optional_fail_count
        $steps["patrol_$patrolPackage"].paste_line = [string]$paste.paste_line
    } catch { }
}
if ($patrolRequiredFailed) {
    $script:requiredFailed = $true
    $script:ok = $false
    Add-ManualItem -Id "patrol_failure_triage" -LabelKo "$patrolPackage required step failure" -Reason "required_failed=true exit=$patrolCode" -Command "Read reports/mkm_command_package_paste_latest.json"
}

# --- weekly-only lifecycle audit (dry) ---
if ($runWeekly) {
    Invoke-TrackedStep -Name "workspace_lifecycle_audit" -Required $false {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmWorkspaceLifecycleRoutine_v1.ps1") -WorkspaceRoot $WorkspaceRoot
    } | Out-Null
    Add-ManualItem -Id "athena_fact_lock_weekly" -LabelKo "weekly AthenaBundle pytest bundle" -Reason "weekly_sunday_suggested" -Command "Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle"
}

# --- resume pack merge ---
$mergePy = Join-Path $WorkspaceRoot "scripts\merge_mkm_ops_patrol_into_resume_pack_v1.py"
if ((Test-Path -LiteralPath $mergePy) -and -not $DryRun) {
    Invoke-TrackedStep -Name "resume_pack_merge" -Required $false {
        py $mergePy
    } | Out-Null
}

# --- build report ---
$optionalFail = 0
foreach ($s in $steps.Values) {
    if ($s.exit_code -and [int]$s.exit_code -ne 0 -and -not $s.required) { $optionalFail++ }
}

$overall = if ($requiredFailed) { "FAIL" }
elseif ($optionalFail -gt 0 -or -not $ok) { "WARN" }
else { "OK" }

$pasteParts = @()
foreach ($name in $steps.Keys) {
    if ($steps[$name].skipped) {
        $pasteParts += "${name}:skip"
    } elseif ($null -ne $steps[$name].exit_code) {
        $ec = [int]$steps[$name].exit_code
        $pasteParts += "${name}:$(if ($ec -eq 0) { 'pass' } else { 'fail' })"
    }
}
$pasteDetail = ($pasteParts -join ', ')
$pasteLine = ('[AutonomousPatrol] {0} {1} ({2}; manual:{3}) | C-layer | No Track A/live' -f $localDate, $overall, $pasteDetail, $manualQueue.Count)

# Sticky alert: surface scheduled LastTaskResult≠0 even when this interactive run looks OK.
$schedInfo = $null
try { $schedInfo = Get-ScheduledTaskInfo -TaskName "MKM_AutonomousPatrol_Daily" -ErrorAction SilentlyContinue } catch { }
$stickyPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_autonomous_patrol_sticky_alert_v1_latest.json"
$sticky = Write-AutonomousPatrolStickyAlert -OutPath $stickyPath -LocalDate $localDate -TaskInfo $schedInfo `
    -Overall $overall -RequiredFailed $requiredFailed -PasteLine $pasteLine
if ($sticky.alert) {
    Add-ManualItem -Id "patrol_scheduled_last_result" `
        -LabelKo ("AutonomousPatrol schedule LastTaskResult={0} sticky alert" -f $sticky.last_task_result) `
        -Reason (($sticky.reasons) -join ',') `
        -Command "Read docs/final/artifacts/mkm_autonomous_patrol_sticky_alert_v1_latest.json"
    $pasteLine = ('[AutonomousPatrol] {0} {1} ({2}; manual:{3}; sticky:ALERT) | C-layer | No Track A/live' -f $localDate, $overall, $pasteDetail, $manualQueue.Count)
}

$metacogReminder = [ordered]@{
    before_overall_ok_or_done_claim = $true
    command = "py scripts/run_mkm_claim_adversarial_reread_v1.py --claim-text `"...`""
    note_ko = "완료/자동화 완료/경영 자율 주장 전 claim adversarial 필수. AutonomousPatrol OK ≠ 회사 경영 자율 DONE ≠ remote Actions green."
}

$report = [ordered]@{
    schema               = "mkm_autonomous_patrol_v1"
    generated_at_utc     = $utcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    last_run_local_date  = $localDate
    ok                   = (-not $requiredFailed)
    overall              = $overall
    patrol_package       = $patrolPackage
    weekly_mode          = $runWeekly
    paste_line           = $pasteLine
    steps                = $steps
    git_ci_readiness     = $gitCi
    sticky_alert         = $sticky
    sticky_alert_path    = "docs/final/artifacts/mkm_autonomous_patrol_sticky_alert_v1_latest.json"
    metacog_reminder     = $metacogReminder
    manual_queue         = @($manualQueue)
    manual_ssot          = "docs/final/artifacts/mkm_autonomous_patrol_manual_tasks_v1.json"
    repro_command        = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmAutonomousPatrol_v1.ps1 -ContinueOnFail"
    chat_triggers        = @("자율루프", "오늘 자율루프", "【자율점검】", "자율점검", "autonomous patrol", "AutonomousPatrol")
    commander_daily_contract = "docs/final/artifacts/mkm_autonomous_patrol_commander_daily_contract_v1_latest.md"
    honesty_limits_ko    = @(
        "ops foundation only — not company-management autonomy DONE",
        "AutonomousPatrol ≠ dual-regime / GitHub Actions green",
        "AutonomousPatrol ≠ AthenaBundle / Fact-Lock daily",
        "PR/CI iron-firewall paste often ~25% policy / ~75% rhetoric — keep Fact-Lock"
    )
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$latestPath = Join-Path $reportDir "mkm_autonomous_patrol_latest.json"
($report | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $latestPath -Encoding UTF8

Write-Host ""
Write-Host "==> paste one-liner" -ForegroundColor Green
Write-Host "  $pasteLine"
Write-Host "  file: $latestPath"
Write-Host "  sticky: $stickyPath alert=$($sticky.alert) last_task_result=$($sticky.last_task_result)"
if ($overall -eq "OK" -and -not $sticky.alert) {
    Write-Host "  metacog: before any 완료 claim → run_mkm_claim_adversarial_reread_v1.py" -ForegroundColor DarkGray
}

if ($manualQueue.Count -gt 0) {
    Write-Host ""
    Write-Host "==> manual_queue Tier-3 human only" -ForegroundColor Yellow
    foreach ($m in $manualQueue) {
        Write-Host "  - [$($m.id)] $($m.label_ko)"
        Write-Host "      reason: $($m.reason)"
        if ($m.command) { Write-Host "      cmd: $($m.command)" -ForegroundColor DarkGray }
    }
}

Write-Host ""
Write-Host "AUTONOMOUS_PATROL_OVERALL=$overall"

if ($requiredFailed) { exit 1 }
if ($optionalFail -gt 0) { exit 2 }
exit 0
