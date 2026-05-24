<#
.SYNOPSIS
  O-P31c full daily: commander SSOT refresh (best-effort) -> Zone A BED+manifest -> Zone B morning+Friday.

.EXAMPLE
  pwsh -File scripts\Invoke-RadioOp31cFullDailyChain_v1.ps1
  pwsh -File scripts\Invoke-RadioOp31cFullDailyChain_v1.ps1 -SkipCommanderRefresh
  pwsh -File scripts\Invoke-RadioOp31cFullDailyChain_v1.ps1 -SkipRender
#>
param(
    [switch]$SkipCommanderRefresh,
    [switch]$SkipRender,
    [string]$ApprovedBy = "commander",
    [string]$StoryJson = "data\radio\listener_story_v1.example.json",
    [string]$NarrativeFuelJson = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step([string]$Label, [scriptblock]$Block) {
    Write-Host "`n=== $Label ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "step_failed:$Label exit=$LASTEXITCODE"
    }
}

if (-not $SkipCommanderRefresh) {
    $profileJson = if ($env:MKM_COMMANDER_PROFILE_JSON) { $env:MKM_COMMANDER_PROFILE_JSON } else { "docs\final\artifacts\commander_profile_v1.example.json" }
    $reportJson = Join-Path $RepoRoot "reports\commander_myeongni_full_daily_latest.json"
    if (-not (Test-Path $reportJson)) {
        $reportJson = Join-Path $RepoRoot "reports\commander_hyperpersonalized_report_v2_1_latest.json"
    }
    $lifestyleJson = Join-Path $RepoRoot "reports\commander_weather_seoul_latest.json"
    try {
        Invoke-Step "commander logos anchor" {
            $logoArgs = @(
                (Join-Path $RepoRoot "scripts\commander_daily_logos_anchor_v1.py"),
                "--profile-json", (Join-Path $RepoRoot $profileJson),
                "--report-json", $reportJson
            )
            if (Test-Path $lifestyleJson) {
                $logoArgs += @("--lifestyle-json", $lifestyleJson)
            }
            py @logoArgs
        }
    } catch {
        Write-Host "WARN: logos anchor skipped — $($_.Exception.Message)" -ForegroundColor Yellow
    }
    try {
        Invoke-Step "commander daily fortune" {
            py (Join-Path $RepoRoot "scripts\build_commander_daily_fortune_v1.py")
        }
    } catch {
        Write-Host "WARN: fortune skipped — $($_.Exception.Message)" -ForegroundColor Yellow
    }
    try {
        Invoke-Step "commander advanced briefing" {
            py (Join-Path $RepoRoot "scripts\build_commander_telegram_advanced_briefing_v1.py")
        }
    } catch {
        Write-Host "WARN: briefing skipped — $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Invoke-Step "Zone A ambient BED" {
    py (Join-Path $RepoRoot "scripts\build_radio_ambient_bed_v1.py")
}

Invoke-Step "Zone A manifest" {
    py (Join-Path $RepoRoot "scripts\build_ambient_stream_manifest_v1.py")
}

$rtmp = $env:YOUTUBE_RTMP_URL
if (-not $rtmp) { $rtmp = "" }
Invoke-Step "Zone A ffmpeg plan" {
    if ($rtmp) {
        py (Join-Path $RepoRoot "scripts\emit_ambient_stream_ffmpeg_plan_v1.py") --rtmp-url $rtmp
    } else {
        py (Join-Path $RepoRoot "scripts\emit_ambient_stream_ffmpeg_plan_v1.py")
    }
}

$renderSwitch = if ($SkipRender) { "-SkipRenderIfNotReady" } else { "-Render" }

Invoke-Step "Zone B morning Shorts" {
    pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Invoke-RadioDialogueMorningShortsChain_v1.ps1") `
        -RecordSignoff -ApprovedBy $ApprovedBy $renderSwitch
}

$fuelPath = $NarrativeFuelJson
if (-not ($fuelPath -and $fuelPath.Trim())) {
    $fuelDefault = Join-Path $RepoRoot "data\radio\narrative_fuel_science_v1.example.json"
    if (Test-Path $fuelDefault) { $fuelPath = "data\radio\narrative_fuel_science_v1.example.json" }
}
try {
    Invoke-Step "Zone B Friday VOD" {
        $fridayArgs = @(
            "-RecordSignoff", "-ApprovedBy", $ApprovedBy,
            "-StoryJson", $StoryJson, $renderSwitch
        )
        if ($fuelPath -and $fuelPath.Trim()) {
            $fridayArgs += @("-NarrativeFuelJson", $fuelPath)
        }
        pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\Invoke-RadioDialogueFridayVodChain_v1.ps1") @fridayArgs
    }
} catch {
    Write-Host "WARN: Friday VOD step failed (script/SRT may exist; re-run render) — $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    Invoke-Step "ambient ffmpeg probe" {
        py (Join-Path $RepoRoot "scripts\run_ambient_stream_ffmpeg_probe_v1.py")
    }
} catch {
    Write-Host "WARN: ffmpeg probe — $($_.Exception.Message)" -ForegroundColor Yellow
}

$summaryExit = 0
try {
    Invoke-Step "daily summary" {
        py (Join-Path $RepoRoot "scripts\build_radio_op31c_daily_summary_v1.py")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} catch {
    $summaryExit = 1
    Write-Host "WARN: summary incomplete — $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`nOK: O-P31c full daily chain complete" -ForegroundColor Green
Write-Host "  summary:     reports\radio_op31c_daily_summary_latest.json"
Write-Host "  morning MP3: reports\radio_dialogue_merged_latest.mp3"
Write-Host "  friday MP3:  reports\radio_dialogue_friday_merged_latest.mp3"
Write-Host "  ambient BED: reports\audio\mkm_ambient_bed_loop_latest.wav"
Write-Host "  RTMP plan:   reports\ambient_stream_ffmpeg_plan_latest.json"
exit $summaryExit
