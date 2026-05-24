<#
.SYNOPSIS
  O-P31c Zone B Friday VOD: build -> gate -> SRT -> optional TTS.

.EXAMPLE
  pwsh -File scripts\Invoke-RadioDialogueFridayVodChain_v1.ps1
  pwsh -File scripts\Invoke-RadioDialogueFridayVodChain_v1.ps1 -RecordSignoff -Render
#>
param(
    [string]$StoryJson = "data\radio\listener_story_v1.example.json",
    [string]$NarrativeFuelJson = "",
    [switch]$RecordSignoff,
    [string]$ApprovedBy = "commander",
    [switch]$Render,
    [switch]$SkipRenderIfNotReady
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ScriptJson = Join-Path $RepoRoot "reports\radio_dialogue_script_friday_vod_latest.json"
$SignoffJson = Join-Path $RepoRoot "reports\radio_dialogue_signoff_friday_latest.json"
$MergedMp3 = Join-Path $RepoRoot "reports\radio_dialogue_friday_merged_latest.mp3"
$RenderDir = Join-Path $RepoRoot "reports\radio_dialogue_render_friday_latest"

$buildArgs = @(
    (Join-Path $RepoRoot "scripts\build_radio_dialogue_script_friday_vod_v1.py"),
    "--story-json", $StoryJson
)
if ($NarrativeFuelJson -and $NarrativeFuelJson.Trim()) {
    $buildArgs += @("--narrative-fuel-json", $NarrativeFuelJson)
}
& py @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\check_radio_dialogue_script_v1.py") --script-json $ScriptJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\radio_dialogue_to_srt_v1.py") `
    --in-json $ScriptJson `
    --out-srt (Join-Path $RepoRoot "reports\radio_dialogue_script_friday_vod_latest.srt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RecordSignoff) {
    & py (Join-Path $RepoRoot "scripts\record_radio_dialogue_signoff_v1.py") `
        --script-json $ScriptJson `
        --out-json $SignoffJson `
        --approved-by $ApprovedBy
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Render) {
    & py (Join-Path $RepoRoot "scripts\check_radio_dialogue_render_readiness_v1.py") --require-all
    if ($LASTEXITCODE -ne 0) {
        if ($SkipRenderIfNotReady) {
            Write-Host "SKIP: edge-tts/ffmpeg not ready" -ForegroundColor Yellow
            exit 0
        }
        exit $LASTEXITCODE
    }
    & py (Join-Path $RepoRoot "scripts\radio_dialogue_render_edge_tts_v1.py") `
        --script-json $ScriptJson `
        --signoff-json $SignoffJson `
        --out-dir $RenderDir `
        --merged-mp3 $MergedMp3
    exit $LASTEXITCODE
}

Write-Host "OK: Friday script + gate + SRT" -ForegroundColor Green
exit 0
