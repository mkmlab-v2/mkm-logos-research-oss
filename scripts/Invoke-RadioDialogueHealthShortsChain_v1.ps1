<#
.SYNOPSIS
  TKM health skin 5m Shorts: build -> gate -> SRT -> optional TTS.
#>
param(
    [switch]$RecordSignoff,
    [string]$ApprovedBy = "commander",
    [switch]$Render,
    [switch]$SkipRenderIfNotReady
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ScriptJson = Join-Path $RepoRoot "reports\radio_dialogue_script_health_shorts_latest.json"
$SignoffJson = Join-Path $RepoRoot "reports\radio_dialogue_signoff_health_latest.json"
$MergedMp3 = Join-Path $RepoRoot "reports\radio_dialogue_health_merged_latest.mp3"

& py (Join-Path $RepoRoot "scripts\build_radio_dialogue_script_health_shorts_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\check_radio_dialogue_script_v1.py") --script-json $ScriptJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\radio_dialogue_to_srt_v1.py") `
    --in-json $ScriptJson `
    --out-srt (Join-Path $RepoRoot "reports\radio_dialogue_script_health_shorts_latest.srt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RecordSignoff) {
    & py (Join-Path $RepoRoot "scripts\record_radio_dialogue_signoff_v1.py") `
        --script-json $ScriptJson --out-json $SignoffJson --approved-by $ApprovedBy
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Render) {
    & py (Join-Path $RepoRoot "scripts\check_radio_dialogue_render_readiness_v1.py") --require-all
    if ($LASTEXITCODE -ne 0) {
        if ($SkipRenderIfNotReady) { exit 0 }
        exit $LASTEXITCODE
    }
    & py (Join-Path $RepoRoot "scripts\radio_dialogue_render_edge_tts_v1.py") `
        --script-json $ScriptJson --signoff-json $SignoffJson `
        --out-dir (Join-Path $RepoRoot "reports\radio_dialogue_render_health_latest") `
        --merged-mp3 $MergedMp3
    exit $LASTEXITCODE
}

Write-Host "OK: health shorts script + gate + SRT" -ForegroundColor Green
exit 0
