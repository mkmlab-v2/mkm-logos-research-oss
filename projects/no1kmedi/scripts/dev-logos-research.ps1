# Logos research dev — localhost root mirrors logos.jema-ai.com (/ → /logos-research rewrite)
param(
  # Bench SSOT (`--base http://127.0.0.1:3010`). Parallel HQ dev: use -Port 3035.
  [int]$Port = 3010,
  # Faster Fast Refresh (Next 14). Use dev:logos:turbo when UI/CSS iterate.
  [switch]$Turbo,
  # Windows: file watcher misses saves → set WATCHPACK_POLLING for reliable HMR.
  [switch]$Poll
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot/..

$env:MKM_DEV_SIMULATE_LOGOS_HOST = "1"
$env:NEXT_PUBLIC_MKM_DEV_SIMULATE_LOGOS_HOST = "1"
$env:MKM_DEV_SIMULATE_NO1KMEDI_CLINIC = ""
$env:MKM_DEV_SIMULATE_NO1KMEDI_APEX = ""
$env:MKM_DEV_SIMULATE_NO1KMEDI_HOST = ""
$env:MKM_WORKSPACE_ROOT = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
if ($Poll) {
  $env:WATCHPACK_POLLING = "true"
  $env:MKM_NEXT_DEV_POLL = "1"
}

Write-Host "MKM_DEV_SIMULATE_LOGOS_HOST=1"
Write-Host "  http://localhost:${Port}/          -> Logos research home (rewrite)"
Write-Host "  http://localhost:${Port}/logos-research/ask -> Q&A"
Write-Host "  (without this script: / -> /hub — jema-ai HQ, not Logos)"
Write-Host ""
Write-Host "[HMR] UI/CSS: save -> browser Fast Refresh (keep this terminal open)."
Write-Host "[HMR] API/lib pipeline: recompile then re-submit a question on /ask (no auto replay)."
Write-Host "[HMR] Open http://localhost:${Port}/logos-research/ask (avoid bare / — old browser cache)."
if ($Poll) { Write-Host "[HMR] WATCHPACK_POLLING=1 (Windows file-watch fallback)" }
if ($Turbo) { Write-Host "[HMR] next dev --turbo" }

$nextArgs = @("next", "dev", "-p", "$Port")
if ($Turbo) { $nextArgs += "--turbo" }
& npx @nextArgs
