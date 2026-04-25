# Optional: install prometheus_client for daemon /metrics.
# Usage: powershell -File install_prometheus_client.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $here)
$req = Join-Path $projectRoot "requirements-optional-prometheus.txt"
if (-not (Test-Path $req)) {
    Write-Error "Missing $req"
    exit 1
}
py -m pip install -r $req
Write-Host "OK: prometheus_client installed for $projectRoot"
