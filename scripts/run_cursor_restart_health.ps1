$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$checkScript = Join-Path $workspaceRoot "scripts\check_cursor_restart_health.ps1"
$outDir = Join-Path $workspaceRoot "tmp"
$outFile = Join-Path $outDir "cursor_restart_health_latest.json"

if (-not (Test-Path $checkScript)) {
    throw "Health check script not found: $checkScript"
}

if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

# Give Cursor a short window to fully initialize hooks/log writers.
Start-Sleep -Seconds 20

# Run baseline-based check and store machine-readable latest result.
$null = powershell -NoProfile -ExecutionPolicy Bypass -File $checkScript -InitBaseline
$json = powershell -NoProfile -ExecutionPolicy Bypass -File $checkScript
$json | Out-File -FilePath $outFile -Encoding utf8

Write-Host "Cursor restart health check completed."
Write-Host "Result saved: $outFile"
