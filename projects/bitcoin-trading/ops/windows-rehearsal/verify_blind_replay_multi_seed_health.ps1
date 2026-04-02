param(
    [string]$TaskName = "BlindReplay-MultiSeed-Daily",
    [string]$StatusPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_status_latest.json",
    [string]$GridPath = "C:\workspace\reports\constitution\btrack_pilot\blind_replay\blind_replay_dataset_grid_latest.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_health_latest.json",
    [int]$MaxAgeMinutes = 1440,
    [double]$MinBalancedAccuracyMean = 0.34,
    [double]$MinHitRateMean = 0.43
)

$ErrorActionPreference = "Stop"

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

function Get-ScheduledTaskInfo([string]$Name) {
    schtasks /Query /TN $Name /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) { return @{ exists = $false; status = "NOT_FOUND"; last_result = "" } }
    $raw = schtasks /Query /TN $Name /V /FO LIST
    $statusLine = $raw | Where-Object { $_ -match "^Status:\s+" } | Select-Object -First 1
    $lastResultLine = $raw | Where-Object { $_ -match "^Last Result:\s+" } | Select-Object -First 1
    return @{
        exists = $true
        status = ($statusLine -replace "^Status:\s+", "").Trim()
        last_result = ($lastResultLine -replace "^Last Result:\s+", "").Trim()
    }
}

$status = Read-JsonOrNull -path $StatusPath
$grid = Read-JsonOrNull -path $GridPath
$task = Get-ScheduledTaskInfo -Name $TaskName

$ageOk = $false
$ageMinutes = $null
if ($null -ne $status) {
    try {
        $checkedAt = [DateTimeOffset]::Parse([string]$status.checked_at_utc)
        $ageMinutes = [Math]::Round(([DateTimeOffset]::UtcNow - $checkedAt).TotalMinutes, 2)
        $ageOk = ($ageMinutes -le $MaxAgeMinutes)
    } catch {
        $ageOk = $false
    }
}

$bal = 0.0
$hit = 0.0
if ($null -ne $grid -and $null -ne $grid.best_config) {
    $bal = [double]$grid.best_config.eligible_best_profile_balanced_accuracy_mean
    $hit = [double]$grid.best_config.eligible_best_profile_hit_rate_mean
}
$metricOk = ($bal -ge $MinBalancedAccuracyMean) -and ($hit -ge $MinHitRateMean)
$taskOk = $task.exists -and ($task.status -in @("Ready", "Running"))
$runOk = ($null -ne $status) -and [bool]$status.run_ok
$overall = $taskOk -and $ageOk -and $metricOk -and $runOk

$result = [ordered]@{
    schema = "blind_replay_multi_seed_health_v1"
    checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    task = $task
    status_file_exists = ($null -ne $status)
    status_age_minutes = $ageMinutes
    status_recent = $ageOk
    run_ok = $runOk
    thresholds = [ordered]@{
        min_balanced_accuracy_mean = $MinBalancedAccuracyMean
        min_hit_rate_mean = $MinHitRateMean
    }
    metrics = [ordered]@{
        balanced_accuracy_mean = $bal
        hit_rate_mean = $hit
        metric_ok = $metricOk
    }
    overall_ok = $overall
}

$json = $result | ConvertTo-Json -Depth 6
Write-Host $json
$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host ("Saved blind replay health report: {0}" -f $OutputPath)
if (-not $overall) { exit 1 }
exit 0
