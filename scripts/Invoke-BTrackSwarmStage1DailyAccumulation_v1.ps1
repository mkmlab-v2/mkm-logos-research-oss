<#
.SYNOPSIS
  B-track Stage 1: collect Bluesky + backfill recent KRX days + tier_a ingest (no re-eval until 30 rows).

.NOTES
  Skips live API if BSKY_* missing (probe wrapper exit 0). Does not promote Track A or fusion.
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
Push-Location $workspaceRoot
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$workspaceRoot\scripts\Invoke-BTrackAtprotoBlueskyProbe.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $from = (Get-Date).AddDays(-21).ToString("yyyy-MM-dd")
    & py "$workspaceRoot\scripts\backfill_atproto_sentiment_raw_by_created_date_v1.py" `
        --date-from $from --date-to $today --calendar-mode krx_weekdays --max-posts 6000 --min-posts-per-day 1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & py "$workspaceRoot\scripts\build_swarm_sentiment_from_atproto_v1.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & py "$workspaceRoot\scripts\check_btrack_swarm_tier_a_prereqs_v1.py" --jsonl "$workspaceRoot\data\btrack\swarm_sentiment_real_pit_v1.jsonl"
    & py "$workspaceRoot\scripts\build_btrack_swarm_sasang_stage1_accumulation_v1.py"

    $prereqs = Get-Content "$workspaceRoot\reports\btrack_swarm_tier_a_prereqs_v1_latest.json" -Raw | ConvertFrom-Json
    if ($prereqs.tier_a_ready -eq $true) {
        & py "$workspaceRoot\scripts\run_btrack_swarm_sasang_stage1_bundle_v1.py"
        exit $LASTEXITCODE
    }
    exit 0
}
finally {
    Pop-Location
}
