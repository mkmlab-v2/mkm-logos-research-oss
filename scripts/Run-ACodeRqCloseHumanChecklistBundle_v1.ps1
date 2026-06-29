#Requires -Version 5.1
<#
.SYNOPSIS
  Refresh RQ close gate + commander manual CLOSED checklist ([HYPO] · no auto-close).

.EXAMPLE
  pwsh -File scripts/Run-ACodeRqCloseHumanChecklistBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[rq-close-checklist] gate refresh" -ForegroundColor Cyan
& $py scripts/check_a_code_rq_close_gate_v1.py
if ($LASTEXITCODE -ne 0) { throw "rq close gate exit $LASTEXITCODE" }

Write-Host "[rq-close-checklist] human checklist" -ForegroundColor Cyan
& $py scripts/build_a_code_rq_close_human_checklist_v1.py
if ($LASTEXITCODE -ne 0) { throw "human checklist exit $LASTEXITCODE" }

Write-Host "[rq-close-checklist] done" -ForegroundColor Green
exit 0
