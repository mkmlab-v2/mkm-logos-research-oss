# Night Watchman harness — build public pixel map + dry-run character alert + lock file.
# SSOT: scripts/PIXEL_BATTALION_NIGHT_WATCHMAN_CHECKLIST.md

param(
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $workspaceRoot "scripts\configs\night_watchman_harness_v1.json"
}

Set-Location -LiteralPath $workspaceRoot

$build = Join-Path $workspaceRoot "scripts\build_pixel_battalion_public_map.py"
if (Test-Path -LiteralPath $build) {
    Write-Host "[night-watchman] build public map" -ForegroundColor Cyan
    & py $build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$send = Join-Path $workspaceRoot "scripts\send_night_watchman_character_alert.py"
if (-not (Test-Path -LiteralPath $send)) {
    throw "missing: $send"
}
Write-Host "[night-watchman] send alert dry-run" -ForegroundColor Cyan
& py $send --decision PASS --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$lockDir = Join-Path $workspaceRoot "docs\final\artifacts"
$lockFile = Join-Path $lockDir "night_watchman_harness_lock_latest.json"
New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
$ts = [DateTimeOffset]::UtcNow.ToString("o")
$obj = @{
    schema   = "night_watchman_harness_lock_v1"
    decision = "PASS"
    mode     = "dry_run_character_alert"
    utc      = $ts
    config   = $ConfigPath
} | ConvertTo-Json -Compress
Set-Content -LiteralPath $lockFile -Value $obj -Encoding utf8
Write-Host "[night-watchman] lock -> $lockFile" -ForegroundColor Green
exit 0
