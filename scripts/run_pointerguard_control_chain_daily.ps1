<#
.SYNOPSIS
  Run PointerGuard control chain and save a timestamped run log.

.DESCRIPTION
  Executes scripts/run_genesis_pointer_routing_control_chain_v1.py with the current
  production-like defaults, then writes stdout/stderr to reports/pointerguard/.
#>
param(
    [string]$RouterTargetPath = "reports/demo_run.json",
    [string]$MemoryTuningTargetPath = "projects/bitcoin-trading/memory/v2/demo.json",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$WeeklyP0DrillDay = "Sunday",
    [switch]$ForceP0Drill
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_genesis_pointer_routing_control_chain_v1.py"
$alertRunner = Join-Path $WorkspaceRoot "scripts\send_pointerguard_ops_alert_v1.py"
$securityRunner = Join-Path $WorkspaceRoot "scripts\harden_pointerguard_security_v1.py"
$launchChecklistRunner = Join-Path $WorkspaceRoot "scripts\build_a_codeai_public_benchmark_launch_checklist_v1.py"
$readinessRunner = Join-Path $WorkspaceRoot "scripts\check_pointerguard_ops_readiness_v1.py"
$manualApprovalRunner = Join-Path $WorkspaceRoot "scripts\build_pointerguard_manual_approval_log_v1.py"
$readinessBlockRunner = Join-Path $WorkspaceRoot "scripts\apply_pointerguard_readiness_block_v1.py"
$p0DrillRunner = Join-Path $WorkspaceRoot "scripts\run_pointerguard_p0_alert_drill_v1.py"
$schedulerEvidenceRunner = Join-Path $WorkspaceRoot "scripts\build_pointerguard_scheduler_arguments_evidence_v1.py"
$approvalAuditRunner = Join-Path $WorkspaceRoot "scripts\build_pointerguard_manual_approval_audit_report_v1.py"
$readinessTopnRunner = Join-Path $WorkspaceRoot "scripts\build_pointerguard_readiness_failure_topn_v1.py"
$opsDashboardRunner = Join-Path $WorkspaceRoot "scripts\build_pointerguard_ops_status_dashboard_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$logDir = Join-Path $WorkspaceRoot "reports\pointerguard"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir ("pointerguard_control_chain_{0}.log" -f $stamp)

$argList = @(
    $runner,
    "--router-target-path", $RouterTargetPath,
    "--memory-tuning-target-path", $MemoryTuningTargetPath
)

"[$((Get-Date).ToString('s'))] Running PointerGuard control chain..." | Out-File -FilePath $logFile -Encoding utf8
"Command: py $($argList -join ' ')" | Out-File -FilePath $logFile -Encoding utf8 -Append

& py @argList *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
$exitCode = $LASTEXITCODE

# Security-first hardening gate (C1/C6 + non-exposure + manual lock policy).
if (Test-Path -LiteralPath $securityRunner) {
    "[$((Get-Date).ToString('s'))] Running security hardening gate..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $securityRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Refresh public benchmark launch checklist from latest hardening artifact.
if (Test-Path -LiteralPath $launchChecklistRunner) {
    "[$((Get-Date).ToString('s'))] Refreshing public benchmark checklist..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $launchChecklistRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Ensure manual-approval governance artifact exists before readiness check.
if (Test-Path -LiteralPath $manualApprovalRunner) {
    "[$((Get-Date).ToString('s'))] Refreshing manual approval governance log..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $manualApprovalRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Record scheduler argument evidence for Fact-Lock visibility.
if (Test-Path -LiteralPath $schedulerEvidenceRunner) {
    "[$((Get-Date).ToString('s'))] Refreshing scheduler argument evidence..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $schedulerEvidenceRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Final operational readiness gate (must include security controls).
if (Test-Path -LiteralPath $readinessRunner) {
    "[$((Get-Date).ToString('s'))] Running ops readiness gate..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $readinessRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Build maintenance audit report daily.
if (Test-Path -LiteralPath $approvalAuditRunner) {
    "[$((Get-Date).ToString('s'))] Building manual approval audit report..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $approvalAuditRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Build readiness failure Top-N queue (used by alert payload).
if (Test-Path -LiteralPath $readinessTopnRunner) {
    "[$((Get-Date).ToString('s'))] Building readiness failure Top-N report..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $readinessTopnRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Build ops status dashboard summary.
if (Test-Path -LiteralPath $opsDashboardRunner) {
    "[$((Get-Date).ToString('s'))] Building ops status dashboard..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $opsDashboardRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Enforce automatic blocking rules when readiness is not green (force HOLD route).
if (Test-Path -LiteralPath $readinessBlockRunner) {
    "[$((Get-Date).ToString('s'))] Applying readiness block rules..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $readinessBlockRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Weekly alert-path liveness health check (dry-run P0 drill).
if (Test-Path -LiteralPath $p0DrillRunner) {
    $today = (Get-Date).DayOfWeek.ToString()
    $shouldRunP0Drill = $ForceP0Drill -or ($today -eq $WeeklyP0DrillDay)
    if ($shouldRunP0Drill) {
        "[$((Get-Date).ToString('s'))] Running weekly P0 alert drill (dry-run)..." | Out-File -FilePath $logFile -Encoding utf8 -Append
        & py $p0DrillRunner --dry-run --alert-on-failure *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
        if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
            $exitCode = $LASTEXITCODE
        }
    } else {
        "[$((Get-Date).ToString('s'))] Skipping P0 drill (today=$today, weekly_day=$WeeklyP0DrillDay)." | Out-File -FilePath $logFile -Encoding utf8 -Append
    }
}

# Fire-and-record alert delivery regardless of chain exit code.
if (Test-Path -LiteralPath $alertRunner) {
    "[$((Get-Date).ToString('s'))] Running ops alert delivery..." | Out-File -FilePath $logFile -Encoding utf8 -Append
    & py $alertRunner *>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
}

"[$((Get-Date).ToString('s'))] ExitCode=$exitCode" | Out-File -FilePath $logFile -Encoding utf8 -Append
Write-Host "PointerGuard daily chain log: $logFile"

exit $exitCode
