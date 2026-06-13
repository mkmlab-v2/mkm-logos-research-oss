#Requires -Version 5.1
<#
.SYNOPSIS
  Tier 3 Cursor parallel-chat wire handoff pilot (one lane).

.EXAMPLE
  powershell -File scripts\Run-A2aTier3CursorWireHandoffPilot_v1.ps1 -Lane oracle -AppendLog
#>
param(
    [ValidateSet("oracle", "ms", "infra", "web_ops")]
    [string]$Lane = "oracle",
    [switch]$AppendLog,
    [switch]$StrictExit
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$pyArgs = @(
    'scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py',
    '--lane', $Lane,
    '--strict-exit'
)
if ($AppendLog) { $pyArgs += '--append-log' }

Write-Host "== Tier 3 Cursor wire handoff pilot [HYPO] ==" -ForegroundColor Cyan
Write-Host ('py ' + ($pyArgs -join ' '))
py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '[DONE] Tier 3 wire handoff pilot OK' -ForegroundColor Green
exit 0
