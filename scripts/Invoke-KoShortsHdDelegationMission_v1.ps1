# Ko shorts HD delegation — preflight (ms) + Netflix pro ASS mission [HYPO tier_0].
#
# Usage:
#   powershell -File scripts\Invoke-KoShortsHdDelegationMission_v1.ps1
#   powershell -File scripts\Invoke-KoShortsHdDelegationMission_v1.ps1 -SkipBurn
#
param(
    [switch]$SkipBurn,
    [switch]$SkipAlignment,
    [switch]$SkipPreflight
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

if (-not $SkipPreflight) {
    Write-Step 'High-delegation preflight (ms, tier_0 local nodes)'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts\Invoke-MkmHighDelegationPreflight_v1.ps1') `
        -Scale M -Lane ms -SkipSessionUpgrade
    # browser host may fail; local pytest/chain still valid for this mission
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'preflight: host_ready may be false (browser); continuing tier_0 local mission' -ForegroundColor Yellow
    }
}

$missionArgs = @('scripts/run_ko_shorts_hd_delegation_mission_v1.py')
if ($SkipBurn) { $missionArgs += '--skip-burn' }
if ($SkipAlignment) { $missionArgs += '--skip-alignment' }

Write-Step 'run_ko_shorts_hd_delegation_mission_v1.py'
& py @missionArgs
if ($LASTEXITCODE -ne 0) { throw "hd delegation mission exit $LASTEXITCODE" }

Write-Host 'OK: Invoke-KoShortsHdDelegationMission_v1' -ForegroundColor Green
Write-Host 'Mission: reports/ko_shorts_hd_delegation_mission_v1_latest.json' -ForegroundColor DarkGray
Write-Host 'Completion: reports/ko_shorts_hd_delegation_completion_v1_latest.json' -ForegroundColor DarkGray
exit 0
