param(
  [switch]$LiveFetch,
  [string]$MappingCsv = "c:\workspace\data\smartfarm_rda_extract_v1\out\station_zone_mapping_operational_v1.csv",
  [string]$Profile = "standard",
  [int]$RecentHoursFromLatest = 96
)

$ErrorActionPreference = "Stop"

$root = "c:\workspace"
$outDir = Join-Path $root "data\smartfarm_rda_extract_v1\out"
$summaryPath = Join-Path $outDir "smartfarm_daily_ingest_and_gate_summary_v1.json"
$alertPath = Join-Path $outDir "smartfarm_daily_ingest_and_gate_alert_v1.json"

$script:steps = @()
function Add-Step([string]$name, [bool]$ok, [string]$detail) {
  $script:steps += [pscustomobject]@{
    step = $name
    ok = $ok
    detail = $detail
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  }
}

try {
  $fetchArgs = @(
    "c:\workspace\scripts\fetch_rda_agmet_openapi_v1.py",
    "--output-json", (Join-Path $outDir "rda_agmet_openapi_latest.json"),
    "--output-alert-json", (Join-Path $outDir "rda_agmet_openapi_alert_latest.json"),
    "--fallback-on-fail"
  )
  if (-not $LiveFetch) { $fetchArgs += "--dry-run" }
  py @fetchArgs
  if ($LASTEXITCODE -ne 0) { throw "fetch_rda_agmet_openapi_v1.py exit=$LASTEXITCODE" }
  $fetchMode = "dry_run"
  if ($LiveFetch) { $fetchMode = "live" }
  Add-Step "fetch_openapi" $true $fetchMode

  py "c:\workspace\scripts\build_smartfarm_zone_weather_features_v1.py" `
    --weather-csv "c:\workspace\data\smartfarm_rda_extract_v1\out\agmet_hourly_canonical.csv" `
    --mapping-csv $MappingCsv `
    --output-dir $outDir `
    --recent-hours-from-latest $RecentHoursFromLatest
  if ($LASTEXITCODE -ne 0) { throw "build_smartfarm_zone_weather_features_v1.py exit=$LASTEXITCODE" }
  Add-Step "build_zone_features" $true "ok"

  py "c:\workspace\scripts\check_smartfarm_week4_data_guard_v1.py" `
    --zone-weather-csv "c:\workspace\data\smartfarm_rda_extract_v1\out\zone_weather_features_v1.csv" `
    --mapping-csv $MappingCsv `
    --output-json "c:\workspace\data\smartfarm_rda_extract_v1\out\week4_data_guard_summary_v1.json"
  # guard may return non-zero on WARN/FAIL by design; continue chain
  Add-Step "guard_check" ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"

  py "c:\workspace\scripts\run_smartfarm_gap_policy_daily_gate_v1.py" `
    --profile $Profile `
    --policy-profile-json "c:\workspace\data\smartfarm_rda_extract_v1\out\daily_gate_policy_profile_v1.json" `
    --recommended-policy-json "c:\workspace\data\smartfarm_rda_extract_v1\out\recommended_policy_v1.json" `
    --guard-summary-json "c:\workspace\data\smartfarm_rda_extract_v1\out\week4_data_guard_summary_v1.json" `
    --zone-weather-csv "c:\workspace\data\smartfarm_rda_extract_v1\out\zone_weather_features_v1.csv" `
    --freshness-reference-json "c:\workspace\data\smartfarm_rda_extract_v1\out\rda_agmet_openapi_latest.json" `
    --output-json "c:\workspace\data\smartfarm_rda_extract_v1\out\smartfarm_gap_policy_daily_gate_v1_$Profile.json" `
    --output-alert-json "c:\workspace\data\smartfarm_rda_extract_v1\out\smartfarm_gap_policy_daily_alert_v1_$Profile.json" `
    --output-log-jsonl "c:\workspace\reports\smartfarm_gap_policy_daily_gate_log.jsonl"
  if ($LASTEXITCODE -ne 0) { throw "run_smartfarm_gap_policy_daily_gate_v1.py exit=$LASTEXITCODE" }
  Add-Step "daily_gate" $true "profile=$Profile"

  $summary = [pscustomobject]@{
    schema = "smartfarm_daily_ingest_and_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    live_fetch = [bool]$LiveFetch
    mapping_csv = $MappingCsv
    profile = $Profile
    recent_hours_from_latest = $RecentHoursFromLatest
    steps = $script:steps
    status = "PASS"
  }
  $summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
  Write-Host "[ok] summary -> $summaryPath"
  exit 0
}
catch {
  Add-Step "pipeline_exception" $false $_.Exception.Message
  $summary = [pscustomobject]@{
    schema = "smartfarm_daily_ingest_and_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    live_fetch = [bool]$LiveFetch
    mapping_csv = $MappingCsv
    profile = $Profile
    recent_hours_from_latest = $RecentHoursFromLatest
    steps = $script:steps
    status = "FAIL"
    error = $_.Exception.Message
  }
  $summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
  $alert = [pscustomobject]@{
    schema = "smartfarm_daily_ingest_and_gate_alert_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    severity = "critical"
    title = "Smartfarm daily ingest+gate failed"
    message = $_.Exception.Message
    summary_path = $summaryPath
  }
  $alert | ConvertTo-Json -Depth 4 | Set-Content -Path $alertPath -Encoding UTF8
  Write-Host "[err] failed; alert -> $alertPath"
  exit 1
}

