# Light showroom Track C health: scheduled tasks + dual-host smoke + B2B pack readiness.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ShowroomTrackCHealth_v1.ps1
#   ... -SkipB2bReadiness
#   ... -SkipLensMediaHub (offline / no jemaai.cloud HEAD)

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipB2bReadiness,
    [switch]$SkipLensMediaHub
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

if (-not $SkipLensMediaHub) {
    Invoke-Step "lens media hub live QA (12 pairs)" {
        py (Join-Path $root "scripts\check_lens_media_hub_live_qa_v1.py")
    }
}

if (-not $SkipB2bReadiness) {
    Invoke-Step "B2B meeting pack readiness" {
        py (Join-Path $root "scripts\check_track_c_b2b_meeting_pack_readiness_v1.py")
    }
}

Invoke-Step "Logos Job Reading Pack self-verify" {
    py (Join-Path $root "scripts\_self_verify_job_reading_pack_showroom_v1.py")
}

Invoke-Step "Logos showroom URL SSOT + slice pytest" {
    py -m pytest (Join-Path $root "tests\test_build_jemaai_showroom_public_urls_v1.py") (Join-Path $root "tests\test_build_showroom_logos_job_reading_pack_slice_v1.py") (Join-Path $root "tests\test_build_showroom_meaning_topology_qa_presets_v1.py") -q --tb=short
}

Write-Host "[showroom-health] OK"
