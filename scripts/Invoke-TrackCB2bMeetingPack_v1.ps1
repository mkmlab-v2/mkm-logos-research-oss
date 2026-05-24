# Track C B2B meeting pack — rebuild + readiness gate (internal meeting use).
param(
    [switch]$SkipCommander,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($WhatIf) {
    Write-Host 'Would run: build_track_c_b2b_meeting_pack_v1.py + check_track_c_b2b_meeting_pack_readiness_v1.py'
    exit 0
}

$packArgs = @()
if ($SkipCommander) { $packArgs += '--skip-commander' }

py scripts/build_track_c_b2b_meeting_pack_v1.py @packArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/check_track_c_b2b_meeting_pack_readiness_v1.py
exit $LASTEXITCODE
