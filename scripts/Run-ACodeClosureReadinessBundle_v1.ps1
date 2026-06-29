#Requires -Version 5.1
<#
.SYNOPSIS
  A-code closure readiness + weekly ops summary ([HYPO] · no auto RQ CLOSED).

.EXAMPLE
  pwsh -File scripts/Run-ACodeClosureReadinessBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[a-code-closure] rq close gate" -ForegroundColor Cyan
& $py scripts/check_a_code_rq_close_gate_v1.py
if ($LASTEXITCODE -ne 0) { throw "rq close gate exit $LASTEXITCODE" }

Write-Host "[a-code-closure] human checklist" -ForegroundColor Cyan
& $py scripts/build_a_code_rq_close_human_checklist_v1.py
if ($LASTEXITCODE -ne 0) { throw "human checklist exit $LASTEXITCODE" }

Write-Host "[a-code-closure] closure readiness" -ForegroundColor Cyan
& $py scripts/build_a_code_closure_readiness_v1.py
if ($LASTEXITCODE -ne 0) { throw "closure readiness exit $LASTEXITCODE" }

Write-Host "[a-code-closure] weekly ops summary" -ForegroundColor Cyan
& $py scripts/build_a_code_weekly_ops_summary_v1.py
if ($LASTEXITCODE -ne 0) { throw "weekly ops summary exit $LASTEXITCODE" }

Write-Host "[a-code-closure] research close migration draft" -ForegroundColor Cyan
& $py scripts/build_a_code_research_close_migration_draft_v1.py
if ($LASTEXITCODE -ne 0) { throw "migration draft exit $LASTEXITCODE" }

Write-Host "[a-code-closure] done" -ForegroundColor Green
exit 0
