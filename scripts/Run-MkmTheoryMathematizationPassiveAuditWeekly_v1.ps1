#Requires -Version 5.1
<#
.SYNOPSIS
  Run MKM theory mathematization passive audit chain (weekly default).

.DESCRIPTION
  Wrapper for scripts/run_mkm_theory_mathematization_passive_audit_v1.py
  B-track / research_only / non-gating.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-MkmTheoryMathematizationPassiveAuditWeekly_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMcp
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$args = @("scripts\run_mkm_theory_mathematization_passive_audit_v1.py")
if ($SkipMcp) {
    $args += "--skip-mcp"
}

& py @args
exit $LASTEXITCODE
