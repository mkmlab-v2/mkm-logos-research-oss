<#
.SYNOPSIS
  O-P31c fusion: daily chain + health skin + video bed + concat FIFO + RTMP cmd.

.EXAMPLE
  pwsh -File scripts\Invoke-RadioOp31cFusionDailyChain_v1.ps1
  pwsh -File scripts\Invoke-RadioOp31cFusionDailyChain_v1.ps1 -SkipRender
#>
param(
    [switch]$SkipCommanderRefresh,
    [switch]$SkipRender,
    [string]$ApprovedBy = "commander",
    [switch]$SkipVideoBed,
    [string]$NarrativeFuelJson = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

# Optional: sync YOUTUBE_RTMP_URL from .env → User env (no-op if key absent).
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Set-YoutubeRtmpUrlUserEnv_v1.ps1") `
    -FromDotEnv -QuietMissing
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$userRtmp = [Environment]::GetEnvironmentVariable("YOUTUBE_RTMP_URL", "User")
if ($userRtmp -and $userRtmp.Trim()) { $env:YOUTUBE_RTMP_URL = $userRtmp.Trim() }

$fullArgs = @("-ApprovedBy", $ApprovedBy)
if ($SkipCommanderRefresh) { $fullArgs += "-SkipCommanderRefresh" }
if ($SkipRender) { $fullArgs += "-SkipRender" }
if ($NarrativeFuelJson -and $NarrativeFuelJson.Trim()) {
    $fullArgs += @("-NarrativeFuelJson", $NarrativeFuelJson)
}
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Invoke-RadioOp31cFullDailyChain_v1.ps1") @fullArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== TKM health shorts ===" -ForegroundColor Cyan
$healthArgs = @("-RecordSignoff", "-ApprovedBy", $ApprovedBy)
if (-not $SkipRender) { $healthArgs += "-Render" }
else { $healthArgs += "-SkipRenderIfNotReady" }
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Invoke-RadioDialogueHealthShortsChain_v1.ps1") @healthArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipVideoBed) {
    Write-Host "`n=== Zone A video bed ===" -ForegroundColor Cyan
    & py (Join-Path $RepoRoot "scripts\build_oracle_sphere_idle_video_bed_v1.py") --seconds 90
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`n=== Zone A concat FIFO ===" -ForegroundColor Cyan
& py (Join-Path $RepoRoot "scripts\manage_ambient_playlist_fifo_v1.py") init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$morningMp3 = Join-Path $RepoRoot "reports\radio_dialogue_merged_latest.mp3"
if (Test-Path $morningMp3) {
    & py (Join-Path $RepoRoot "scripts\manage_ambient_playlist_fifo_v1.py") append --media $morningMp3 --kind zone_b_morning
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$fridayMp3 = Join-Path $RepoRoot "reports\radio_dialogue_friday_merged_latest.mp3"
if (Test-Path $fridayMp3) {
    & py (Join-Path $RepoRoot "scripts\manage_ambient_playlist_fifo_v1.py") append --media $fridayMp3 --kind zone_b_friday_vod
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& py (Join-Path $RepoRoot "scripts\build_ambient_stream_manifest_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\emit_ambient_stream_rtmp_command_v1.py") --profile ambient_24h
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($env:YOUTUBE_RTMP_URL -and $env:YOUTUBE_RTMP_URL.Trim()) {
    & py (Join-Path $RepoRoot "scripts\emit_ambient_stream_ffmpeg_plan_v1.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($env:YOUTUBE_RTMP_URL -and $env:YOUTUBE_RTMP_URL.Trim()) {
    Write-Host "`n=== Zone A ffmpeg probe (5s, no RTMP push) ===" -ForegroundColor Cyan
    & py (Join-Path $RepoRoot "scripts\run_ambient_stream_ffmpeg_probe_v1.py") --probe-seconds 5
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`n=== YouTube channel copy (KO+EN) ===" -ForegroundColor Cyan
& py (Join-Path $RepoRoot "scripts\build_radio_youtube_channel_copy_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\print_radio_youtube_studio_paste_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\build_radio_op31c_daily_summary_v1.py")
exit $LASTEXITCODE
