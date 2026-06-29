#Requires -Version 5.1
<#
.SYNOPSIS
  Commander RQ close handoff bundle — gate, checklist, closure, migration draft ([HYPO] · no auto CLOSED).

.EXAMPLE
  pwsh -File scripts/Run-ACodeRqCloseCommanderHandoffBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$handoff = Join-Path $PSScriptRoot "Run-ACodeClosureReadinessBundle_v1.ps1"
if (-not (Test-Path -LiteralPath $handoff)) { throw "Missing: $handoff" }
& $handoff -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "closure readiness bundle exit $LASTEXITCODE" }

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[a-code-handoff] research close migration draft" -ForegroundColor Cyan
& $py scripts/build_a_code_research_close_migration_draft_v1.py
if ($LASTEXITCODE -ne 0) { throw "migration draft exit $LASTEXITCODE" }

Write-Host "[a-code-handoff] sign-off archive pack refresh" -ForegroundColor Cyan
& $py scripts/build_a_code_governor_signoff_archive_pack_v1.py
if ($LASTEXITCODE -ne 0) { throw "archive pack exit $LASTEXITCODE" }

Write-Host "[a-code-handoff] done — commander close: Invoke-ACodeRqCloseCommanderClose_v1.ps1" -ForegroundColor Green
exit 0
