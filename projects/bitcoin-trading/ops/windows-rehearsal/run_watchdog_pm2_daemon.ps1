$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$watchdog = Join-Path $projectRoot "ops\windows-rehearsal\watchdog_pm2_daemon.py"

if (-not (Test-Path $watchdog)) {
    throw "Watchdog script not found: $watchdog"
}

Set-Location $projectRoot
python "$watchdog" --app bitcoin-trading-daemon-win --stale-minutes 15 --restart-cooldown-minutes 10
if ($LASTEXITCODE -ne 0) {
    throw "Watchdog execution failed with exit code: $LASTEXITCODE"
}
