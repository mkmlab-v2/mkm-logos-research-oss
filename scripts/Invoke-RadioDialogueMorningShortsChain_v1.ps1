<#
.SYNOPSIS
  O-P31c Zone B morning Shorts: build -> gate -> SRT -> optional TTS (sign-off required).

.EXAMPLE
  pwsh -File scripts\Invoke-RadioDialogueMorningShortsChain_v1.ps1
  pwsh -File scripts\Invoke-RadioDialogueMorningShortsChain_v1.ps1 -RecordSignoff -ApprovedBy commander
  pwsh -File scripts\Invoke-RadioDialogueMorningShortsChain_v1.ps1 -RecordSignoff -Render
#>
param(
    [switch]$RecordSignoff,
    [string]$ApprovedBy = "commander",
    [switch]$Render,
    [switch]$SkipRenderIfNotReady
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

& py (Join-Path $RepoRoot "scripts\build_radio_dialogue_script_morning_shorts_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\check_radio_dialogue_script_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $RepoRoot "scripts\radio_dialogue_to_srt_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RecordSignoff) {
    & py (Join-Path $RepoRoot "scripts\record_radio_dialogue_signoff_v1.py") --approved-by $ApprovedBy
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
    & py (Join-Path $RepoRoot "scripts\radio_dialogue_render_edge_tts_v1.py")
    exit $LASTEXITCODE
}

Write-Host "OK: script + gate + SRT (use -RecordSignoff -Render for TTS)" -ForegroundColor Green
exit 0
