param(
  [string]$WorkspaceRoot = "C:\workspace",
  [int]$WindowDays = 7,
  [string]$DefaultOwner = "xai-ops",
  [int]$DueDays = 2
)

$ErrorActionPreference = "Stop"

$weeklyScript = Join-Path $WorkspaceRoot "scripts\build_xai_contract_weekly_report_v1.py"
$queueScript = Join-Path $WorkspaceRoot "scripts\build_xai_action_queue_ops_v1.py"
$summaryPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_weekly_reporting_summary_latest.json"

$steps = @()
function Add-Step([string]$step, [bool]$ok, [string]$detail) {
  $script:steps += [pscustomobject]@{
    step = $step
    ok = $ok
    detail = $detail
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  }
}

try {
  Set-Location -LiteralPath $WorkspaceRoot
  if (-not (Test-Path -LiteralPath $weeklyScript)) { throw "Missing script: $weeklyScript" }
  if (-not (Test-Path -LiteralPath $queueScript)) { throw "Missing script: $queueScript" }

  py $weeklyScript --window-days $WindowDays
  if ($LASTEXITCODE -ne 0) { throw "build_xai_contract_weekly_report_v1.py exit=$LASTEXITCODE" }
  Add-Step "build_weekly_report" $true "window_days=$WindowDays"

  py $queueScript --default-owner $DefaultOwner --due-days $DueDays
  if ($LASTEXITCODE -ne 0) { throw "build_xai_action_queue_ops_v1.py exit=$LASTEXITCODE" }
  Add-Step "build_ops_action_queue" $true "owner=$DefaultOwner due_days=$DueDays"

  $summary = [pscustomobject]@{
    schema = "xai_contract_weekly_reporting_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "PASS"
    window_days = $WindowDays
    default_owner = $DefaultOwner
    due_days = $DueDays
    steps = $steps
    weekly_report_json = (Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_weekly_report_latest.json")
    action_queue_json = (Join-Path $WorkspaceRoot "docs\final\artifacts\xai_action_queue_ops_latest.json")
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
  Write-Host "[ok] weekly reporting summary -> $summaryPath"
  exit 0
}
catch {
  Add-Step "pipeline_exception" $false $_.Exception.Message
  $summary = [pscustomobject]@{
    schema = "xai_contract_weekly_reporting_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "FAIL"
    error = $_.Exception.Message
    window_days = $WindowDays
    default_owner = $DefaultOwner
    due_days = $DueDays
    steps = $steps
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
  Write-Host "[err] weekly reporting failed -> $summaryPath"
  exit 1
}
