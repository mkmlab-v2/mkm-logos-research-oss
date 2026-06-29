# Track C B2B — 15 min internal rehearsal prep (one-click · no external send).
param(
    [switch]$SkipMeetingPackRebuild,
    [switch]$SkipAudioStage,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$root = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}
Set-Location $root

$steps = @(
    @{ id = 'stage_audio_hook_samples'; skip = $SkipAudioStage; cmd = @('py', 'scripts/stage_track_c_audio_hook_samples_for_counsel_v1.py') }
    @{ id = 'meeting_pack'; skip = $SkipMeetingPackRebuild; ps1 = 'Invoke-TrackCB2bMeetingPack_v1.ps1'; ps1Args = @('-SkipCommander') }
    @{ id = 'rehearsal_script'; skip = $false; cmd = @('py', 'scripts/build_track_c_b2b_15min_rehearsal_script_v1.py') }
    @{ id = 'counsel_one_minute_brief'; skip = $false; cmd = @('py', 'scripts/build_track_c_b2b_counsel_one_minute_brief_v1.py') }
    @{ id = 'counsel_manifest'; skip = $false; cmd = @('py', 'scripts/build_track_c_b2b_counsel_export_manifest_v1.py', '--fail-if-missing') }
    @{ id = 'counsel_zip'; skip = $false; cmd = @('py', 'scripts/build_track_c_b2b_counsel_zip_pack_v1.py') }
    @{ id = 'counsel_copy_scan'; skip = $false; cmd = @('py', 'scripts/check_track_c_b2b_counsel_copy_scan_v1.py') }
    @{ id = 'rehearsal_readiness'; skip = $false; cmd = @('py', 'scripts/check_track_c_b2b_internal_rehearsal_readiness_v1.py') }
)

if ($WhatIf) {
    $steps | ForEach-Object { Write-Host ("plan: {0} skip={1}" -f $_.id, $_.skip) }
    exit 0
}

foreach ($s in $steps) {
    if ($s.skip) {
        Write-Host ("[skip] {0}" -f $s.id) -ForegroundColor DarkGray
        continue
    }
    Write-Host ("`n[run] {0}" -f $s.id) -ForegroundColor Cyan
    if ($s.ps1) {
        $ps1Path = Join-Path $PSScriptRoot $s.ps1
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ps1Path @($s.ps1Args)
    }
    else {
        $exe = $s.cmd[0]
        $args = @()
        if ($s.cmd.Count -gt 1) { $args = $s.cmd[1..($s.cmd.Count - 1)] }
        & $exe @args
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error ("Step failed: {0} (exit {1})" -f $s.id, $LASTEXITCODE)
    }
}

Write-Host ""
Write-Host "track_c_b2b_rehearsal_prep: ok" -ForegroundColor Green
Write-Host "script: reports/track_c_b2b_15min_rehearsal_script_v1_latest.md"
Write-Host "zip: docs/final/artifacts/track_c_b2b_counsel_export_pack_v1.zip"
Write-Host "ready_for_external_send: false (human rehearsal + counsel HOLD)"
