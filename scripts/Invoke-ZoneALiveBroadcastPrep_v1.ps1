<#
.SYNOPSIS
  Zone A live prep: visual bed (1080p) + BGM + manifest + RTMP cmd + optional TTS refresh + go-live.

.EXAMPLE
  pwsh -File scripts\Invoke-ZoneALiveBroadcastPrep_v1.ps1
  pwsh -File scripts\Invoke-ZoneALiveBroadcastPrep_v1.ps1 -Render -GoLive
  pwsh -File scripts\Invoke-ZoneALiveBroadcastPrep_v1.ps1 -SkipRender -GoLive
#>
param(
    [switch]$Render,
    [switch]$SkipRender,
    [switch]$GoLive,
    [switch]$SkipContentRefresh,
    [int]$VideoSeconds = 300
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Step([string]$Label, [scriptblock]$Block) {
    Write-Host "`n=== $Label ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "step_failed:$Label exit=$LASTEXITCODE" }
}

Step "RTMP env sync" {
    & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Set-YoutubeRtmpUrlUserEnv_v1.ps1") `
        -FromDotEnv -QuietMissing
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $userRtmp = [Environment]::GetEnvironmentVariable("YOUTUBE_RTMP_URL", "User")
    if ($userRtmp -and $userRtmp.Trim()) { $env:YOUTUBE_RTMP_URL = $userRtmp.Trim() }
}

if (-not $SkipContentRefresh) {
    $renderArgs = @()
    if ($Render -and -not $SkipRender) { $renderArgs += "-Render" }
    Step "O-P31c fusion (content)" {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Invoke-RadioOp31cFusionDailyChain_v1.ps1") `
            -SkipCommanderRefresh -SkipVideoBed @renderArgs
    }
}

Step "Oracle video bed (live-prep 1080p)" {
    & py (Join-Path $RepoRoot "scripts\build_oracle_sphere_idle_video_bed_v1.py") `
        --live-prep --seconds $VideoSeconds
}

Step "Ambient BED (long loop)" {
    & py (Join-Path $RepoRoot "scripts\build_radio_ambient_bed_v1.py") --seconds 180
}

Step "FIFO init (bed-only 24h)" {
    & py (Join-Path $RepoRoot "scripts\manage_ambient_playlist_fifo_v1.py") init
}

Step "Manifest + RTMP command (ambient_24h)" {
    & py (Join-Path $RepoRoot "scripts\build_ambient_stream_manifest_v1.py")
    & py (Join-Path $RepoRoot "scripts\emit_ambient_stream_rtmp_command_v1.py") --profile ambient_24h
    & py (Join-Path $RepoRoot "scripts\emit_ambient_stream_ffmpeg_plan_v1.py")
}

Step "Studio paste + summary" {
    & py (Join-Path $RepoRoot "scripts\build_radio_youtube_channel_copy_v1.py")
    & py (Join-Path $RepoRoot "scripts\print_radio_youtube_studio_paste_v1.py")
    & py (Join-Path $RepoRoot "scripts\build_radio_op31c_daily_summary_v1.py")
}

if ($env:YOUTUBE_RTMP_URL -and $env:YOUTUBE_RTMP_URL.Trim()) {
    Step "FFmpeg probe (local BED, no RTMP push)" {
        & py (Join-Path $RepoRoot "scripts\run_ambient_stream_ffmpeg_probe_v1.py") --probe-seconds 5
    }
} else {
    Write-Host "WARN: YOUTUBE_RTMP_URL unset — skip probe; set .env then Set-YoutubeRtmpUrlUserEnv" -ForegroundColor Yellow
}

Write-Host "`nOK: Zone A live prep complete" -ForegroundColor Green
Write-Host "  Studio paste: reports\radio_youtube_studio_paste_latest.txt"
Write-Host "  Live title:   MKM Oracle Sphere — 24h ambient [관측·참고용]"
Write-Host "  RTMP cmd:     reports\ambient_stream_rtmp_command_latest.txt"
Write-Host "  Summary:      reports\radio_op31c_daily_summary_latest.json"

if ($GoLive) {
    if (-not $env:YOUTUBE_RTMP_URL -or -not $env:YOUTUBE_RTMP_URL.Trim()) {
        throw "GoLive requires YOUTUBE_RTMP_URL (Set-YoutubeRtmpUrlUserEnv_v1.ps1 -FromDotEnv)"
    }
    Write-Host "`n=== GO LIVE (ffmpeg RTMP) ===" -ForegroundColor Magenta
    Write-Host "YouTube Studio: stream must be Ready — https://studio.youtube.com/video/1CBpdXewV60/livestreaming"
    Write-Host "Stop: Ctrl+C in this window"
    $cmd = Get-Content (Join-Path $RepoRoot "reports\ambient_stream_rtmp_command_latest.txt") -Raw
    if ($cmd.TrimStart().StartsWith("#")) {
        throw "RTMP command file is still placeholder — fix YOUTUBE_RTMP_URL"
    }
    Invoke-Expression $cmd.Trim()
}
