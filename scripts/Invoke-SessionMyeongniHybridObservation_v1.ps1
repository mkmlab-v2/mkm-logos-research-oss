# Session myeongni hybrid observation (B-track, non-blocking for daily chain).
param(
  [int]$EvalDays = 30,
  [int]$PanelCalendarDays = 50,
  [switch]$SkipHoldoutSummary
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$pyArgs = @(
  "scripts/build_session_myeongni_hybrid_observation_latest_v1.py",
  "--eval-days", "$EvalDays",
  "--panel-calendar-days", "$PanelCalendarDays"
)
if ($SkipHoldoutSummary) { $pyArgs += "--skip-holdout-summary" }

py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
