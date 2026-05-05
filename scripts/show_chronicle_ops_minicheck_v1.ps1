[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required file: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

$briefPath = Join-Path $WorkspaceRoot "docs\final\artifacts\global_atom_corpus_fact_brief_latest.md"
$weeklyPath = Join-Path $WorkspaceRoot "docs\final\artifacts\chronicle_human_gate_weekly_report_latest.json"

if (-not (Test-Path -LiteralPath $briefPath)) {
    throw "Missing required file: $briefPath"
}

$weekly = Read-JsonFile -Path $weeklyPath
$briefText = Get-Content -LiteralPath $briefPath -Raw -Encoding UTF8

$profile = "__UNKNOWN__"
$line = ($briefText -split "`r?`n" | Where-Object { $_ -match "corpus_profile_id" } | Select-Object -First 1)
if ($line) {
    $sanitized = ($line -replace '`', '')
    $m = [regex]::Match($sanitized, 'corpus_profile_id\s*:\s*([A-Za-z0-9_\-]+)')
    if ($m.Success -and $m.Groups.Count -ge 2) {
        $profile = $m.Groups[1].Value
    }
}

$reviewGapDetected = [bool]($weekly.review_gap_detected)
$reviewGapCount = [int]($weekly.review_gap_count)
$readiness = [string]($weekly.readiness_for_threshold_switch)
$recommendation = [string]($weekly.threshold_switch_recommendation)

$status = if ($reviewGapDetected) { "ATTENTION" } elseif ($readiness -eq "ready") { "READY" } else { "STABLE" }

$out = [ordered]@{
    schema = "chronicle_ops_minicheck_v1"
    checked_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    status = $status
    corpus_profile_id = $profile
    review_gap_detected = $reviewGapDetected
    review_gap_count = $reviewGapCount
    readiness_for_threshold_switch = $readiness
    threshold_switch_recommendation = $recommendation
    refs = [ordered]@{
        corpus_brief_md = $briefPath
        weekly_report_json = $weeklyPath
    }
}

$out | ConvertTo-Json -Depth 5
