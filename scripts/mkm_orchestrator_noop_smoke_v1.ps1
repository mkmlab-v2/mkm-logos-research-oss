<#
.SYNOPSIS
  Ultra-short orchestrator smoke task (writes JSON artifact, exit 0).

.DESCRIPTION
  Resolves repo root from script location (no hardcoded drive). Safe first real poll target.
#>
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$reports = Join-Path $root "reports"
if (-not (Test-Path -LiteralPath $reports)) {
    New-Item -ItemType Directory -Path $reports -Force | Out-Null
}

$out = Join-Path $reports "mkm_orchestrator_noop_smoke_latest.json"
$row = [ordered]@{
    schema  = "mkm_orchestrator_noop_smoke_v1"
    ts_utc  = (Get-Date).ToUniversalTime().ToString("o")
    ok      = $true
    note    = "orchestrator noop smoke"
}
($row | ConvertTo-Json -Compress) | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "mkm_orchestrator_noop_smoke_v1 OK -> $out"
