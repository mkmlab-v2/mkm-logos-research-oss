param(
    [string]$QueuePath = "C:\workspace\reports\github_gpu_runner_health_alert_retry_queue.jsonl",
    [switch]$KeepFailed
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $QueuePath)) {
    Write-Host "Queue file not found: $QueuePath"
    exit 0
}

$lines = Get-Content -Path $QueuePath | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
if ($lines.Count -eq 0) {
    Write-Host "Queue is empty: $QueuePath"
    exit 0
}

$failed = New-Object System.Collections.Generic.List[string]
$sent = 0

foreach ($line in $lines) {
    try {
        $item = $line | ConvertFrom-Json
        Invoke-RestMethod -Uri $item.webhook_url -Method Post -ContentType "application/json; charset=utf-8" -Body $item.payload_json | Out-Null
        $sent += 1
    }
    catch {
        $failed.Add($line) | Out-Null
        Write-Host "WARN: replay failed: $($_.Exception.Message)"
    }
}

if ($failed.Count -gt 0 -or $KeepFailed.IsPresent) {
    Set-Content -Path $QueuePath -Value $failed -Encoding utf8
}
else {
    Clear-Content -Path $QueuePath
}

Write-Host "Replay complete. sent=$sent failed=$($failed.Count)"
exit 0
