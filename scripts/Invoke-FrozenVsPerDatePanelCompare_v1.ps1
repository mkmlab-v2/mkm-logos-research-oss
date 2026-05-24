#Requires -Version 5.1
<#
.SYNOPSIS
  Refresh Dual-KPI compare report (frozen vs per-date WF on same score panel).

.DESCRIPTION
  B-track / research_only. Does not mutate btrack_prophecy_score_latest.json or Track A.
  Writes reports/frozen_vs_per_date_panel_compare_v1_latest.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-FrozenVsPerDatePanelCompare_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MinTrainRows = 3,
    [switch]$RunScoredEval
)

$ErrorActionPreference = "Stop"
$script = Join-Path $WorkspaceRoot "scripts\compare_frozen_vs_per_date_combo_panel_v1.py"
if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing: $script"
}

$argsList = @(
    $script,
    "--min-train-rows", "$MinTrainRows",
    "--output", "reports\frozen_vs_per_date_panel_compare_v1_latest.json"
)
if ($RunScoredEval) {
    $argsList += "--run-scored-eval"
}

& py @argsList
exit $LASTEXITCODE
