#Requires -Version 5.1
<#
.SYNOPSIS
  Workspace lifecycle audit — C: / F: / Git / folders / compression lane boundaries.

.DESCRIPTION
  Default: read-only audit -> reports/workspace_lifecycle_audit_v1_latest.json
  -ApplySafe: tier-A cache + ephemeral apply + git gc (non-destructive)
  Default tail: ops_memory infra lane refresh (non-blocking; physical audit exit unaffected).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmWorkspaceLifecycleRoutine_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmWorkspaceLifecycleRoutine_v1.ps1 -ApplySafe
.EXAMPLE
  powershell … -SkipOpsMemory
#>
param(
    [switch]$ApplySafe,
    [switch]$SkipCompressionLint,
    [switch]$SkipOpsMemory,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
Set-Location -LiteralPath $root

$govPath = Join-Path $root "docs\final\artifacts\workspace_lifecycle_governance_v1.json"
$outPath = Join-Path $root "reports\workspace_lifecycle_audit_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step($name, $exitCode, $note) {
    $script:steps.Add([ordered]@{ name = $name; exit_code = $exitCode; note = $note }) | Out-Null
}

function Invoke-StepScript($name, $scriptRel, [string[]]$extra = @()) {
    $p = Join-Path $root $scriptRel
    if (-not (Test-Path -LiteralPath $p)) {
        Add-Step $name 0 "missing_skipped=$scriptRel"
        return
    }
    Write-Host "[$name] $scriptRel" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $p @extra
    Add-Step $name $LASTEXITCODE $scriptRel
    if ($LASTEXITCODE -ne 0 -and $name -notin @('git_sanity', 'compression_narrative_lint')) {
        Write-Warning "$name exit $LASTEXITCODE (continuing audit)"
    }
}

Write-Host "=== MKM Workspace Lifecycle ($(if ($ApplySafe) { 'ApplySafe' } else { 'Audit' })) ===" -ForegroundColor Green

# 1 Disk hygiene
Invoke-StepScript "disk_hygiene" "scripts\Invoke-SystemDiskHygieneReport.ps1"

# 2 F: governance (quick)
Invoke-StepScript "f_drive_governance" "scripts\Invoke-ExternalDrivesGovernance.ps1"

# 3 Git sanity
Invoke-StepScript "git_sanity" "scripts\Verify-GitWorkspaceSanity.ps1" @("-WorkspaceRoot", $root)

# 4 Compression narrative lint (B-track guard)
if (-not $SkipCompressionLint) {
    $lintPy = Join-Path $root "scripts\check_compression_narrative_fact_lock_v1.py"
    if (Test-Path -LiteralPath $lintPy) {
        Write-Host "[compression_narrative_lint] py $lintPy" -ForegroundColor Cyan
        & py $lintPy 2>&1 | Out-Null
        Add-Step "compression_narrative_lint" $LASTEXITCODE "check_compression_narrative_fact_lock_v1.py"
    } else {
        Add-Step "compression_narrative_lint" 0 "script_missing_skipped"
    }
}

# 5 Ephemeral
if ($ApplySafe) {
    Invoke-StepScript "ephemeral_cleanup" "scripts\Invoke-EphemeralCleanup.ps1" @("-Apply", "-RetentionDays", "3")
} else {
    Invoke-StepScript "ephemeral_dry_run" "scripts\Invoke-EphemeralCleanup.ps1" @("-RetentionDays", "3")
}

if ($ApplySafe) {
    # 6 Tier-A cache
    Write-Host "[tier_a_cache] workspace pycache/pytest" -ForegroundColor Cyan
    $removed = 0
    Get-ChildItem -Path $root -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache') } |
        ForEach-Object {
            try { Remove-Item -LiteralPath $_.FullName -Recurse -Force -EA Stop; $removed++ } catch { }
        }
    Add-Step "tier_a_cache" 0 "removed_dirs=$removed"

    # 7 git gc light
    Write-Host "[git_gc] prune" -ForegroundColor Cyan
    git -C $root gc --prune=now 2>&1 | Out-Null
    Add-Step "git_gc" $LASTEXITCODE "git gc --prune=now"
}

# 8 Ops memory infra lane (cognitive layer — non-blocking; no Track A / disk KPI merge)
if (-not $SkipOpsMemory) {
    $opsMemScript = Join-Path $root "scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1"
    if (Test-Path -LiteralPath $opsMemScript) {
        Write-Host "[ops_memory_infra_lane] Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -Lane infra -SkipBench" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $opsMemScript -Lane infra -SkipBench
        $opsExit = $LASTEXITCODE
        $opsNote = "Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -Lane infra -SkipBench"
        if ($opsExit -ne 0) { $opsNote = "$opsNote; failed_non_blocking" }
        Add-Step "ops_memory_infra_lane" $opsExit $opsNote
        if ($opsExit -ne 0) {
            Write-Warning "ops_memory_infra_lane exit $opsExit (non-blocking; physical audit status unchanged)"
        }
    } else {
        Add-Step "ops_memory_infra_lane" 0 "script_missing_skipped"
    }
}

# Load pointers
$gov = $null
if (Test-Path -LiteralPath $govPath) {
    $gov = Get-Content -LiteralPath $govPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
$diskJson = $null
$diskPath = Join-Path $root "reports\system_disk_hygiene_latest.json"
if (Test-Path -LiteralPath $diskPath) {
    $diskJson = Get-Content -LiteralPath $diskPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$nonBlockingSteps = @('git_sanity', 'ops_memory_infra_lane')
$failed = @($steps | Where-Object { $_.exit_code -ne 0 -and $_.name -notin $nonBlockingSteps })
$status = if ($failed.Count -eq 0) { "ok" } else { "watch" }

$audit = [ordered]@{
    schema           = "workspace_lifecycle_audit_v1"
    generated_at_utc = $utc
    mode             = if ($ApplySafe) { "apply_safe" } else { "audit" }
    status           = $status
    governance_ssot  = $govPath
    c_free_gb        = ($diskJson.drives | Where-Object { $_.drive -eq 'C:' } | Select-Object -First 1).free_gb
    steps            = $steps
    next_recommended = @(
        "weekly: Invoke-MkmWorkspaceLifecycleRoutine_v1.ps1 (ops_memory infra tail default)",
        "before F: delete: human verify JSON in f_workspace_mirror_consolidation",
        "compression on cold archive only: cold_archive_ops_memory_proxy_poc_v1_latest.json"
    )
    ops_memory_hybrid = [ordered]@{
        enabled       = (-not $SkipOpsMemory)
        lane          = "infra"
        non_blocking  = $true
        resume_pack   = "docs/final/artifacts/mkm_chat_resume_pack_latest.md"
    }
    boundary_ack     = "no_git_lossy_compress_no_track_a_merge; infra_disk_ok_ne_ops_memory_track_a"
}
$audit | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "Audit: $outPath status=$status" -ForegroundColor Green

if ($failed.Count -gt 0) { exit 1 }
exit 0
