#Requires -Version 5.1
<#
.SYNOPSIS
  Commander-only RQ close record ([HYPO] · requires MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED).

.EXAMPLE
  $env:MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED='1'
  pwsh -File scripts/Invoke-ACodeRqCloseCommanderClose_v1.ps1 -CloseReference COMMANDER-ACODE-RQ-CLOSE-2026-06-05
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [Parameter(Mandatory = $true)]
    [string]$CloseReference,
    [string]$Note = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$approved = $env:MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED
if (-not $approved -or @('1', 'true', 'yes', 'on') -notcontains $approved.ToString().ToLower()) {
    Write-Host "[FAIL] MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED must be truthy (commander human gate)" -ForegroundColor Red
    exit 2
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[a-code-close] preflight closure readiness" -ForegroundColor Cyan
& $py scripts/build_a_code_closure_readiness_v1.py
if ($LASTEXITCODE -ne 0) { throw "closure readiness preflight exit $LASTEXITCODE" }

Write-Host "[a-code-close] record commander close" -ForegroundColor Cyan
$recordArgs = @(
    "scripts/record_a_code_rq_commander_close_v1.py"
    "--close-reference"
    $CloseReference
)
if ($Note) {
    $recordArgs += @("--note", $Note)
}
& $py @recordArgs
if ($LASTEXITCODE -ne 0) { throw "record commander close exit $LASTEXITCODE" }

Write-Host "[a-code-close] refresh closure readiness + migration draft" -ForegroundColor Cyan
& $py scripts/build_a_code_closure_readiness_v1.py
if ($LASTEXITCODE -ne 0) { throw "closure readiness refresh exit $LASTEXITCODE" }

& $py scripts/build_a_code_research_close_migration_draft_v1.py
if ($LASTEXITCODE -ne 0) { throw "migration draft exit $LASTEXITCODE" }

Write-Host "[a-code-close] done — apply RESEARCH rows manually from migration draft" -ForegroundColor Green
exit 0
