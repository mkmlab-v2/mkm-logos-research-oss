# Open-source tech radar + guardrail autopilot chain (B-track research_only).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-OpenSourceTechRadarUpgrade_v1.ps1
#   powershell -File scripts\Invoke-OpenSourceTechRadarUpgrade_v1.ps1 -WithGuardrailAutopilot
#   powershell -File scripts\Invoke-OpenSourceTechRadarUpgrade_v1.ps1 -Fetch -WithGuardrailAutopilot
#
param(
    [switch]$Fetch,
    [switch]$WithGuardrailAutopilot,
    [switch]$SkipSafeOps
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

Write-Step 'build_open_source_tech_radar_v1.py'
$radarArgs = @('scripts/build_open_source_tech_radar_v1.py')
if ($Fetch) { $radarArgs += '--fetch' }
& py @radarArgs
if ($LASTEXITCODE -ne 0) { throw "build_open_source_tech_radar_v1.py exit $LASTEXITCODE" }

if ($WithGuardrailAutopilot) {
    if (-not $SkipSafeOps) {
        Write-Step 'Invoke-SafeOpsSurfaceCheck.ps1 (input for autopilot)'
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SafeOpsSurfaceCheck.ps1
        if ($LASTEXITCODE -gt 2) { throw "Invoke-SafeOpsSurfaceCheck.ps1 exit $LASTEXITCODE" }
    }
    Write-Step 'build_guardrail_upgrade_autopilot_v1.py'
    & py scripts/build_guardrail_upgrade_autopilot_v1.py
    if ($LASTEXITCODE -ne 0) { throw "build_guardrail_upgrade_autopilot_v1.py exit $LASTEXITCODE" }
}

Write-Host 'OK: Invoke-OpenSourceTechRadarUpgrade_v1' -ForegroundColor Green
exit 0
