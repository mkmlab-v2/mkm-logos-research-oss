param(
    [string]$LogPath = "C:\workspace\docs\final\artifacts\all_green_slack_failure_delivery_log.jsonl",
    [int]$TailLines = 500,
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_slack_delivery_check_latest.json",
    [double]$MaxSuccessAgeHours = 24
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $LogPath)) {
    Write-Host ("[all-green-slack-check] log missing: {0}" -f $LogPath) -ForegroundColor Yellow
    exit 1
}

$rows = @()
Get-Content -LiteralPath $LogPath -Tail $TailLines -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    try {
        $obj = $line | ConvertFrom-Json
        if ($null -ne $obj) {
            $rows += $obj
        }
    } catch {
        # skip malformed lines
    }
}

if ($rows.Count -eq 0) {
    Write-Host "[all-green-slack-check] no parseable rows." -ForegroundColor Yellow
    exit 2
}

$finalRows = @($rows | Where-Object {
    # New format: explicit phase/final.
    # Legacy format: no phase/final fields, one row per send result -> treat as final.
    (($_.phase -eq "final") -or ($_.final -eq $true) -or (
        (-not $_.PSObject.Properties.Name.Contains("phase")) -and
        (-not $_.PSObject.Properties.Name.Contains("final"))
    ))
})

if ($finalRows.Count -eq 0) {
    Write-Host "[all-green-slack-check] no final-phase rows found." -ForegroundColor Yellow
    exit 3
}

$latestSuccess = @($finalRows | Where-Object { $_.webhook_sent -eq $true } | Select-Object -Last 1)
$latestFailure = @($finalRows | Where-Object { $_.webhook_sent -ne $true } | Select-Object -Last 1)

$latestSuccessTs = $null
$latestSuccessAgeHours = $null
$successStale = $true
if ($latestSuccess.Count -gt 0) {
    $tsRaw = $latestSuccess[0].ts_utc
    if ($tsRaw) {
        try {
            $latestSuccessTs = [DateTimeOffset]::Parse([string]$tsRaw)
            $latestSuccessAgeHours = ([DateTimeOffset]::UtcNow - $latestSuccessTs).TotalHours
            $successStale = ($latestSuccessAgeHours -gt $MaxSuccessAgeHours)
        } catch {
            # parse failure => keep stale=true
            $latestSuccessTs = $null
            $latestSuccessAgeHours = $null
            $successStale = $true
        }
    }
}

$hasSuccess = ($latestSuccess.Count -gt 0)
$healthy = ($hasSuccess -and (-not $successStale))

$out = [ordered]@{
    schema = "all_green_slack_delivery_check_v1"
    checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    log_path = $LogPath
    scanned_lines = $TailLines
    max_success_age_hours = $MaxSuccessAgeHours
    final_rows = $finalRows.Count
    latest_success = if ($latestSuccess.Count -gt 0) { $latestSuccess[0] } else { $null }
    latest_failure = if ($latestFailure.Count -gt 0) { $latestFailure[0] } else { $null }
    latest_success_age_hours = $latestSuccessAgeHours
    success_stale = $successStale
    has_success = $hasSuccess
    healthy = $healthy
}

$json = $out | ConvertTo-Json -Depth 8
Write-Host $json

$outParent = Split-Path -Parent $OutputPath
if ($outParent -and -not (Test-Path -LiteralPath $outParent)) {
    New-Item -ItemType Directory -Path $outParent -Force | Out-Null
}
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host ("Saved delivery check report: {0}" -f $OutputPath)

if ($out.healthy) { exit 0 }
exit 4

