#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_MorningBeans_Daily task and latest feed/card artifacts.
#>
param(
    [string]$TaskName = "MKM_MorningBeans_Daily",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$failed = @()

$feedPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_morning_beans_feed_v1_latest.json"
$cardPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_morning_beans_mkmlife_card_v1_latest.json"
$publicPath = Join-Path $WorkspaceRoot "projects\mkm\mkm-life\public\data\mkm_morning_beans_card_v1.json"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "[verify-morning-beans] MISSING task: $TaskName"
    $failed += "task_missing"
} else {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "[verify-morning-beans] task=$TaskName state=$($task.State) lastResult=$($info.LastTaskResult) nextRun=$($info.NextRunTime)"
    if ($task.State -ne "Ready") { $failed += "task_not_ready" }
}

foreach ($pair in @(
        @{ Name = "feed"; Path = $feedPath; Schema = "mkm_morning_beans_feed_v1" },
        @{ Name = "card"; Path = $cardPath; Schema = "mkm_morning_beans_mkmlife_card_v1" },
        @{ Name = "mkmlife_public"; Path = $publicPath; Schema = "mkm_morning_beans_mkmlife_card_v1" }
    )) {
    if (-not (Test-Path -LiteralPath $pair.Path)) {
        Write-Host "[verify-morning-beans] missing $($pair.Name): $($pair.Path)"
        $failed += "$($pair.Name)_missing"
        continue
    }
    $doc = Get-Content -LiteralPath $pair.Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $cardCount = $doc.card_count
    if (-not $cardCount -and $doc.final) { $cardCount = $doc.final.card_count }
    if (-not $cardCount -and $doc.cards) { $cardCount = @($doc.cards).Count }
    if (-not $cardCount -and $doc.cards_display) { $cardCount = @($doc.cards_display).Count }
    Write-Host "[verify-morning-beans] $($pair.Name) schema=$($doc.schema) cards=$cardCount"
    if ($doc.schema -ne $pair.Schema) { $failed += "$($pair.Name)_schema" }
}

if ($failed.Count -gt 0) {
    Write-Host "[verify-morning-beans] FAIL: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}

Write-Host "[verify-morning-beans] OK" -ForegroundColor Green
exit 0
