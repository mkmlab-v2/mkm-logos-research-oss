# Cursor 3.5 weekly ops — tech radar + guardrail plan (no full Athena bundle).
# SSOT: docs/final/artifacts/cursor35_oss_ops_routine_v1_latest.json
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-Cursor35WeeklyOpsRoutine_v1.ps1
#
param(
    [switch]$Fetch
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$args = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', (Join-Path $Root 'scripts\Invoke-OpenSourceTechRadarUpgrade_v1.ps1'),
    '-WithGuardrailAutopilot',
    '-SkipSafeOps'
)
if ($Fetch) { $args += '-Fetch' }

& powershell @args
if ($LASTEXITCODE -ne 0) { throw "Invoke-OpenSourceTechRadarUpgrade_v1 exit $LASTEXITCODE" }

Write-Host 'OK: Run-Cursor35WeeklyOpsRoutine_v1 (radar+autopilot; SafeOps skipped by default)' -ForegroundColor Green
exit 0
