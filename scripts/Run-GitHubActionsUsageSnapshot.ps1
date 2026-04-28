param(
  [string]$Repo = "mkmlab-v2/mkm-destiny-ai-41e38ec6",
  [int]$LongWindow = 300,
  [int]$ShortWindow = 120,
  [int]$TopN = 12
)

$ErrorActionPreference = "Stop"

$workspace = Resolve-Path "."
$reportsDir = Join-Path $workspace "reports"

$runsLong = Join-Path $reportsDir "github_actions_runs_latest_300.json"
$runsShort = Join-Path $reportsDir "github_actions_runs_latest_120.json"
$baseLong = Join-Path $reportsDir "github_actions_usage_baseline_latest.json"
$baseShort = Join-Path $reportsDir "github_actions_usage_baseline_latest_120.json"
$deltaOut = Join-Path $reportsDir "github_actions_usage_delta_latest.json"

Write-Host "[actions-usage] repo=$Repo long=$LongWindow short=$ShortWindow top=$TopN"

gh run list -L $LongWindow --json workflowName,event,status,conclusion,createdAt,updatedAt -R $Repo | Out-File -FilePath $runsLong -Encoding utf8
py scripts/report_github_actions_usage_baseline.py --input-json $runsLong --top-n $TopN --output-json $baseLong

gh run list -L $ShortWindow --json workflowName,event,status,conclusion,createdAt,updatedAt -R $Repo | Out-File -FilePath $runsShort -Encoding utf8
py scripts/report_github_actions_usage_baseline.py --input-json $runsShort --top-n $TopN --output-json $baseShort

py scripts/compare_github_actions_usage_baselines.py --previous-json $baseLong --current-json $baseShort --output-json $deltaOut

Write-Host "[actions-usage] wrote:"
Write-Host " - $runsLong"
Write-Host " - $baseLong"
Write-Host " - $runsShort"
Write-Host " - $baseShort"
Write-Host " - $deltaOut"
