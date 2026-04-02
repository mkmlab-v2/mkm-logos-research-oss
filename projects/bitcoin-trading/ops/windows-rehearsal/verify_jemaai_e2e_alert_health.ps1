param(
    [string]$TaskName = "Jemaai-PublicEvent-E2E-Smoke",
    [string]$StatusPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_status_latest.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_alert_health_latest.json",
    [int]$MaxAgeMinutes = 1440
)

$ErrorActionPreference = "Stop"

function Get-ScheduledTaskInfo([string]$Name) {
    schtasks /Query /TN $Name /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{ exists = $false; status = "NOT_FOUND"; last_result = ""; last_run_time = "" }
    }
    $raw = schtasks /Query /TN $Name /V /FO LIST
    $statusLine = $raw | Where-Object { $_ -match "^Status:\s+" } | Select-Object -First 1
    $lastResultLine = $raw | Where-Object { $_ -match "^Last Result:\s+" } | Select-Object -First 1
    $lastRunLine = $raw | Where-Object { $_ -match "^Last Run Time:\s+" } | Select-Object -First 1
    return @{
        exists = $true
        status = ($statusLine -replace "^Status:\s+", "").Trim()
        last_result = ($lastResultLine -replace "^Last Result:\s+", "").Trim()
        last_run_time = ($lastRunLine -replace "^Last Run Time:\s+", "").Trim()
    }
}

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

$task = Get-ScheduledTaskInfo -Name $TaskName
$statusObj = Read-JsonOrNull -path $StatusPath

$statusRecent = $false
$statusAgeMinutes = $null
if ($null -ne $statusObj) {
    try {
        $checkedAt = [DateTimeOffset]::Parse([string]$statusObj.checked_at_utc)
        $statusAgeMinutes = [Math]::Round(([DateTimeOffset]::UtcNow - $checkedAt).TotalMinutes, 2)
        $statusRecent = ($statusAgeMinutes -le $MaxAgeMinutes)
    } catch {
        $statusRecent = $false
    }
}

$taskReady = $task.exists -and ($task.status -in @("Ready", "Running"))
$overall = $taskReady -and ($null -ne $statusObj) -and $statusRecent

$result = [ordered]@{
    schema = "jemaai_e2e_alert_health_v1"
    checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    task = $task
    status_file_exists = ($null -ne $statusObj)
    status_age_minutes = $statusAgeMinutes
    status_recent = $statusRecent
    smoke_ok_latest = if ($null -ne $statusObj) { [bool]$statusObj.smoke_ok } else { $false }
    channel_ready = if ($null -ne $statusObj) { ([bool]$statusObj.channels.slack_ready -or [bool]$statusObj.channels.telegram_ready) } else { $false }
    overall_ok = $overall
}

$json = $result | ConvertTo-Json -Depth 6
Write-Host $json

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host ("Saved jemaai e2e alert health report: {0}" -f $OutputPath)

if (-not $overall) { exit 1 }
exit 0
