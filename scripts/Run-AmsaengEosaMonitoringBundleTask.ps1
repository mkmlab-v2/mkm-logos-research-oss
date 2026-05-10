[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$pyCmd = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $pyCmd)) {
    $pyCmd = (Get-Command -Name "py" -ErrorAction Stop).Source
}

function Invoke-PyScript([string]$ScriptPath, [string[]]$ScriptArgs = @(), [switch]$AllowNonZero) {
    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        throw "Missing script: $ScriptPath"
    }
    & $pyCmd $ScriptPath @ScriptArgs
    if ($LASTEXITCODE -ne 0 -and -not $AllowNonZero) {
        throw "Script failed (exit=$LASTEXITCODE): $ScriptPath $($ScriptArgs -join ' ')"
    }
    return $LASTEXITCODE
}

# Keep security baseline in sync before snapshot generation.
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "security_integrity_monitor_v1.py") -ScriptArgs @("--mode", "check") -AllowNonZero | Out-Null
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "run_execution_gate_rehearsal_matrix_v1.py")
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "build_execution_gate_audit_summary_v1.py")
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "build_amsaeng_eosa_ops_snapshot_v1.py")
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "check_cursorrules_template_drift_v1.py") -AllowNonZero | Out-Null
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "build_fact_lock_evidence_bundle_v1.py") -ScriptArgs @("--append-agent-log")
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "append_amsaeng_eosa_monitoring_heartbeat_v1.py")
Invoke-PyScript -ScriptPath (Join-Path $PSScriptRoot "build_trackc_evidence_rag_mvp_v1.py")

# VPS SSH disk smoke (optional env): never fails the bundle (-SoftFail).
$smokePs1 = Join-Path $PSScriptRoot "Invoke-VpsOpsSmoke_v1.ps1"
if (Test-Path -LiteralPath $smokePs1) {
    Write-Host ""
    Write-Host "=== VPS ops smoke (optional; SoftFail) ===" -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $smokePs1 -WorkspaceRoot $repoRoot -SoftFail
}
