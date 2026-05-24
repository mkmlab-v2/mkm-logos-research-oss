[CmdletBinding()]
param(
    # 번들 말단 거버넌스 주기를 SoftFail 로 돌리면 스케줄 실패가 줄어듦(기본은 엄격 모드).
    [switch]$GovernanceSoftFail
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$pyCmd = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $pyCmd)) {
    $pyCmd = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$bundleSteps = New-Object System.Collections.Generic.List[object]
$bundleOverallStatus = "ok"
$bundleFinalExitCode = 0
$script:lastGovernanceExitCode = 0

function Write-AmsaengBundleCycleArtifact {
    param(
        [string]$Root,
        [System.Collections.Generic.List[object]]$Steps,
        [string]$OverallStatus,
        [int]$ExitCode
    )
    $totalMs = 0
    foreach ($s in $Steps) {
        if ($null -ne $s.duration_ms) { $totalMs += [int]$s.duration_ms }
    }
    $outPath = Join-Path $Root "reports\amsaeng_eosa_bundle_cycle_latest.json"
    $dir = Split-Path -Parent $outPath
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $payload = [ordered]@{
        schema             = "amsaeng_eosa_bundle_cycle_v1"
        completed_at_utc   = [datetime]::UtcNow.ToString("o")
        workspace_root     = $Root
        overall_status     = $OverallStatus
        bundle_exit_code   = $ExitCode
        total_duration_ms  = $totalMs
        steps              = @($Steps)
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
    Write-Output "amsaeng_eosa_bundle_cycle_written=$outPath"
}

function Add-BundleStep {
    param([string]$StepId, [int]$DurationMs, [int]$ExitCode)
    [void]$bundleSteps.Add([ordered]@{ step_id = $StepId; duration_ms = $DurationMs; exit_code = $ExitCode })
}

function Invoke-BundlePyStep {
    param([string]$StepId, [string]$ScriptPath, [string[]]$ScriptArgs = @(), [switch]$AllowNonZero)
    if (-not (Test-Path -LiteralPath $ScriptPath)) { throw "Missing script: $ScriptPath" }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $exitCode = 0
    try {
        & $pyCmd $ScriptPath @ScriptArgs
        $exitCode = [int]$LASTEXITCODE
        if ($exitCode -ne 0 -and -not $AllowNonZero) {
            throw "Script failed (exit=$exitCode): $ScriptPath $($ScriptArgs -join ' ')"
        }
    }
    catch {
        $sw.Stop()
        if ($exitCode -eq 0) { $exitCode = 1 }
        Add-BundleStep -StepId $StepId -DurationMs ([int]$sw.ElapsedMilliseconds) -ExitCode $exitCode
        throw
    }
    $sw.Stop()
    Add-BundleStep -StepId $StepId -DurationMs ([int]$sw.ElapsedMilliseconds) -ExitCode $exitCode
}

function Invoke-BundleGovernance {
    param([string]$Root, [bool]$SoftFail)
    $govPs1 = Join-Path $PSScriptRoot "Invoke-AmsaengEosaGovernanceCycle.ps1"
    if (-not (Test-Path -LiteralPath $govPs1)) { return }
    Write-Host ""
    $govLabel = if ($SoftFail) { "SoftFail" } else { "strict" }
    Write-Host "=== AmsaengEosa governance cycle (SafeOps + MCP + secret hygiene; $govLabel) ===" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $govCli = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $govPs1, "-WorkspaceRoot", $Root)
    if ($SoftFail) { $govCli += "-SoftFail" }
    & powershell.exe @govCli
    $exitCode = [int]$LASTEXITCODE
    $script:lastGovernanceExitCode = $exitCode
    $sw.Stop()
    Add-BundleStep -StepId "governance_cycle" -DurationMs ([int]$sw.ElapsedMilliseconds) -ExitCode $exitCode
    if ($exitCode -ne 0 -and -not $SoftFail) {
        throw "Governance cycle failed (exit=$exitCode)"
    }
}

try {
    Invoke-BundlePyStep -StepId "security_integrity_monitor_check" -ScriptPath (Join-Path $PSScriptRoot "security_integrity_monitor_v1.py") -ScriptArgs @("--mode", "check") -AllowNonZero
    Invoke-BundlePyStep -StepId "execution_gate_rehearsal_matrix" -ScriptPath (Join-Path $PSScriptRoot "run_execution_gate_rehearsal_matrix_v1.py")
    Invoke-BundlePyStep -StepId "execution_gate_audit_summary" -ScriptPath (Join-Path $PSScriptRoot "build_execution_gate_audit_summary_v1.py")
    Invoke-BundlePyStep -StepId "amsaeng_eosa_ops_snapshot" -ScriptPath (Join-Path $PSScriptRoot "build_amsaeng_eosa_ops_snapshot_v1.py")
    Invoke-BundlePyStep -StepId "cursorrules_template_drift" -ScriptPath (Join-Path $PSScriptRoot "check_cursorrules_template_drift_v1.py") -AllowNonZero
    Invoke-BundlePyStep -StepId "fact_lock_evidence_bundle" -ScriptPath (Join-Path $PSScriptRoot "build_fact_lock_evidence_bundle_v1.py") -ScriptArgs @("--append-agent-log")
    Invoke-BundlePyStep -StepId "monitoring_heartbeat_append" -ScriptPath (Join-Path $PSScriptRoot "append_amsaeng_eosa_monitoring_heartbeat_v1.py")
    Invoke-BundlePyStep -StepId "trackc_evidence_rag_mvp" -ScriptPath (Join-Path $PSScriptRoot "build_trackc_evidence_rag_mvp_v1.py")

    $coordObsPy = Join-Path $PSScriptRoot "check_coordinator_lens_conflict_observation_v1.py"
    if (Test-Path -LiteralPath $coordObsPy) {
        Write-Host ""
        Write-Host "=== Coordinator lens conflict observation (O-P22; AllowNonZero) ===" -ForegroundColor Cyan
        Invoke-BundlePyStep -StepId "coordinator_lens_conflict_observation" -ScriptPath $coordObsPy -AllowNonZero
    }

    $headlinePy = Join-Path $PSScriptRoot "check_prophecy_headline_integrity_v1.py"
    if (Test-Path -LiteralPath $headlinePy) {
        Write-Host ""
        Write-Host "=== Prophecy headline integrity observation (B-track; AllowNonZero) ===" -ForegroundColor Cyan
        Invoke-BundlePyStep -StepId "prophecy_headline_integrity_observation" -ScriptPath $headlinePy -AllowNonZero
    }

    $smokePs1 = Join-Path $PSScriptRoot "Invoke-VpsOpsSmoke_v1.ps1"
    if (Test-Path -LiteralPath $smokePs1) {
        Write-Host ""
        Write-Host "=== VPS ops smoke (optional; SoftFail) ===" -ForegroundColor Cyan
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $smokePs1 -WorkspaceRoot $repoRoot -SoftFail
        $vpsExit = [int]$LASTEXITCODE
        $sw.Stop()
        Add-BundleStep -StepId "vps_ops_smoke" -DurationMs ([int]$sw.ElapsedMilliseconds) -ExitCode $vpsExit
    }

    Invoke-BundleGovernance -Root $repoRoot -SoftFail:$GovernanceSoftFail

    $watchdogPy = Join-Path $PSScriptRoot "check_prophecy_evolution_watchdog_v1.py"
    if (Test-Path -LiteralPath $watchdogPy) {
        Write-Host ""
        Write-Host "=== Prophecy evolution watchdog (staleness; bundle soft / AllowNonZero) ===" -ForegroundColor Cyan
        $watchdogArgs = @(
            "--workspace-root", $repoRoot,
            "--allow-missing-ablation",
            "--allow-missing-hit-rate",
            "--max-ablation-age-hours", "96",
            "--max-hit-rate-age-hours", "96"
        )
        Invoke-BundlePyStep -StepId "prophecy_evolution_watchdog_bundle" -ScriptPath $watchdogPy -ScriptArgs $watchdogArgs -AllowNonZero
    }
}
catch {
    $bundleOverallStatus = "failed"
    $bundleFinalExitCode = 1
    if ($script:lastGovernanceExitCode -gt 0) {
        $bundleFinalExitCode = $script:lastGovernanceExitCode
    }
    Write-AmsaengBundleCycleArtifact -Root $repoRoot -Steps $bundleSteps -OverallStatus $bundleOverallStatus -ExitCode $bundleFinalExitCode
    exit $bundleFinalExitCode
}

Write-AmsaengBundleCycleArtifact -Root $repoRoot -Steps $bundleSteps -OverallStatus $bundleOverallStatus -ExitCode $bundleFinalExitCode
exit 0
