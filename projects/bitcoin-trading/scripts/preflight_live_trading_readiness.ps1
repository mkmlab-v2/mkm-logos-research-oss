<#
.SYNOPSIS
  Read-only: check monorepo .env + config before enabling live auto-trading.

.DESCRIPTION
  Does not start the daemon, does not print API secrets.
  Exits 0 always (informational). See also: start_24h_daemon.py, .env.example (repo root).
#>
$ErrorActionPreference = "Stop"
$btRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
# scripts/ -> bitcoin-trading/ -> projects/ -> workspace (monorepo root where .env lives)
$monoRoot = (Resolve-Path (Join-Path $btRoot "..\..")).Path
$envFile = Join-Path $monoRoot ".env"
$cfgFile = Join-Path $btRoot "config\trading_config.yaml"

function Get-DotEnvKeys([string]$Path) {
  $map = @{}
  if (-not (Test-Path -LiteralPath $Path)) { return $map }
  Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $k = $line.Substring(0, $idx).Trim()
    $v = $line.Substring($idx + 1).Trim()
    if ($k) { $map[$k] = $v }
  }
  return $map
}

Write-Host "=== Live trading preflight (read-only) ===" -ForegroundColor Cyan
Write-Host "monorepo: $monoRoot"
Write-Host "bitcoin-trading: $btRoot"
Write-Host ""

if (-not (Test-Path -LiteralPath $envFile)) {
  Write-Host "[!] Missing: $envFile  (copy from .env.example and add keys manually)" -ForegroundColor Yellow
} else {
  Write-Host "[ok] .env present: $envFile"
  $m = Get-DotEnvKeys $envFile
  $et = $m["ENABLE_TRADING"]
  $tn = $m["TESTNET"]
  $k = $m["BINANCE_API_KEY"]
  Write-Host "    ENABLE_TRADING = $(if ($null -eq $et) { '(unset)' } else { $et })"
  Write-Host "    TESTNET        = $(if ($null -eq $tn) { '(unset)' } else { $tn })"
  Write-Host "    BINANCE_API_KEY= $(if ($k -and $k.Trim().Length -gt 0) { '<set>' } else { '<missing>' })"
  if (($et -match '^(1|true|yes|on)$') -and ($tn -match '^(0|false|no|off)$') -and $k) {
    Write-Host ""
    Write-Host "[!!] Profile: mainnet + trading ON + key present -> REAL ORDERS possible when daemon runs." -ForegroundColor Red
  }
}

Write-Host ""
if (Test-Path -LiteralPath $cfgFile) {
  Write-Host "[ok] trading_config.yaml: $cfgFile"
} else {
  Write-Host "[!] Missing trading_config.yaml (strategy defaults may apply)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next (manual): set .env per repo root .env.example -> VPS git pull -> pm2 restart <app> with cwd=monorepo root, script=projects/bitcoin-trading/start_live_trading.py"
Write-Host "See: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md , projects/bitcoin-trading/AGENTS.md"
exit 0
