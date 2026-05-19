# Light showroom Track C health: scheduled tasks + dual-host smoke + B2B pack readiness.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ShowroomTrackCHealth_v1.ps1
#   ... -SkipB2bReadiness

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipB2bReadiness
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

function Invoke-Step([string]$Label, [scriptblock]$Block) {
    Write-Host "[showroom-health] $Label"
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "${Label} failed: exit $LASTEXITCODE"
    }
}

Invoke-Step "publish task verify" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Verify-ShowroomTrackCPublishScheduledTask_v1.ps1") -WorkspaceRoot $root
}

Invoke-Step "nginx weekly task verify" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Verify-ShowroomTrackCNginxWeeklyScheduledTask_v1.ps1") -WorkspaceRoot $root
}

Invoke-Step "dual-host public smoke" {
    py (Join-Path $root "scripts\check_showroom_trust_viz_public_chain_v1.py")
}

if (-not $SkipB2bReadiness) {
    Invoke-Step "B2B meeting pack readiness" {
        py (Join-Path $root "scripts\check_track_c_b2b_meeting_pack_readiness_v1.py")
    }
}

Write-Host "[showroom-health] OK"
