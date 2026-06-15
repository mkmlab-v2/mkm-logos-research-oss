#Requires -Version 5.1
<#
.SYNOPSIS
  Run MASK HYPO passive cross-audit chain (HYPO-4).

.DESCRIPTION
  Wrapper for scripts/run_compression_mask_hypo_passive_cross_audit_v1.py.
  B-track / research_only / non-gating. Masked corpus JSONL replay only.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-CompressionMaskHypoPassiveCrossAudit_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

& py scripts\run_compression_mask_hypo_passive_cross_audit_v1.py
exit $LASTEXITCODE
