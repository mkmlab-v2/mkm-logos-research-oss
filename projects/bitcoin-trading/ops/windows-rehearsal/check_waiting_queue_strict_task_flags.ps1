param(
    [string[]]$TaskNames = @(
        "Bitcoin-WaitingQueue-DualMarket-Daily",
        "Bitcoin-WaitingQueue-BTCBinance-Daily"
    )
)

$ErrorActionPreference = "Stop"

$failed = $false
foreach ($task in $TaskNames) {
    $query = schtasks /Query /TN $task /V /FO LIST 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $query) {
        Write-Host "MISSING task=$task"
        $failed = $true
        continue
    }

    $taskToRun = ($query | Where-Object { $_ -like "Task To Run:*" } | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($taskToRun)) {
        Write-Host "INVALID task=$task reason=TaskToRunNotFound"
        $failed = $true
        continue
    }

    if ($taskToRun -match "-StrictCloseReturn") {
        Write-Host "OK task=$task strict=true"
    } else {
        Write-Host "WARN task=$task strict=false"
        $failed = $true
    }
}

if ($failed) {
    exit 1
}
exit 0
