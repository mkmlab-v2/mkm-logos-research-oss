#Requires -Version 5.1
<#
.SYNOPSIS
  Run Compression Shadow Auditor (pytest + KPI/loss scan + B-track debug queue).

.DESCRIPTION
  Wrapper for scripts/run_compression_shadow_auditor_v1.py (RQ-018).
  Default: read-only audit on frozen artifacts. Use -RefreshLossPatterns or -RefreshBench for refresh.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-CompressionShadowAuditor_v1.ps1

.EXAMPLE
  powershell -File scripts\Run-CompressionShadowAuditor_v1.ps1 -RefreshLossPatterns -DryRun
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RefreshBench,
    [switch]$RefreshLossPatterns,
    [switch]$SkipPytest,
    [switch]$DryRun,
    [switch]$StdoutOnly,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$pyArgs = @("scripts\run_compression_shadow_auditor_v1.py")
if ($RefreshBench) { $pyArgs += "--refresh-bench" }
if ($RefreshLossPatterns) { $pyArgs += "--refresh-loss-patterns" }
if ($SkipPytest) { $pyArgs += "--skip-pytest" }
if ($DryRun) { $pyArgs += "--dry-run" }
if ($StdoutOnly) { $pyArgs += "--stdout-only" }
if ($Quiet) { $pyArgs += "--quiet" }

& py @pyArgs
exit $LASTEXITCODE
