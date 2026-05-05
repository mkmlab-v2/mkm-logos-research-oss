<#
.SYNOPSIS
  Run monthly external anchor downgrade->recovery drill.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_external_anchor_downgrade_recovery_drill_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Drill runner not found: $runner"
}

& py $runner
if ($LASTEXITCODE -ne 0) { throw "Downgrade recovery drill failed ($LASTEXITCODE)" }

Write-Host "DONE: external anchor downgrade recovery monthly drill"
Write-Host "Summary: $WorkspaceRoot\docs\final\artifacts\external_bible_anchor_downgrade_recovery_drill_latest.json"
