<#
.SYNOPSIS
  Read-only: align monorepo .env + trading_config.yaml with start_24h_daemon.py before live trading.

.DESCRIPTION
  Does not start the daemon, does not print API secrets.
  Mirrors resolution order in projects/bitcoin-trading/scripts/start_24h_daemon.py:
    trading_config.yaml defaults -> process env (not inspected here) -> monorepo root .env keys
  Exits 0 always (informational). See also: .env.example (repo root).
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

function Parse-BoolLike {
  param([string]$Raw, [bool]$Default)
  if ($null -eq $Raw) { return @{ Parsed = $false; Value = $Default; RawPresent = $false } }
  $t = $Raw.Trim()
  if (-not $t) { return @{ Parsed = $false; Value = $Default; RawPresent = $false } }
  $s = $t.ToLowerInvariant()
  if ($s -in @("1", "true", "yes", "y", "on")) { return @{ Parsed = $true; Value = $true; RawPresent = $true } }
  if ($s -in @("0", "false", "no", "n", "off")) { return @{ Parsed = $true; Value = $false; RawPresent = $true } }
  return @{ Parsed = $false; Value = $Default; RawPresent = $true }
}

function Get-TopLevelYamlScalar {
  param([string]$Path, [string]$Key)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $pattern = "^\s*$([Regex]::Escape($Key))\s*:\s*(.+)\s*$"
  $last = $null
  Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
    if ($_ -match $pattern) { $last = $Matches[1].Trim() }
  }
  return $last
}

function Get-RiskManagementScalars {
  param([string]$Path)
  $out = @{}
  if (-not (Test-Path -LiteralPath $Path)) { return $out }
  $lines = Get-Content -LiteralPath $Path -Encoding UTF8
  $inRisk = $false
  foreach ($line in $lines) {
    if ($line -match "^\s*risk_management\s*:\s*") {
      $inRisk = $true
      continue
    }
    if ($inRisk) {
      if ($line -match "^\S" -and $line.Trim().Length -gt 0) { break }
      if ($line -match "^\s{2}([A-Za-z0-9_]+)\s*:\s*(.+)\s*$") {
        $out[$Matches[1]] = $Matches[2].Trim()
      }
    }
  }
  return $out
}

function Show-RiskCaps {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $keys = @(
    "max_position_size",
    "max_drawdown",
    "max_daily_loss",
    "stop_loss_ratio",
    "take_profit_ratio"
  )
  $rm = Get-RiskManagementScalars -Path $Path
  if ($rm.Count -eq 0) { return }
  Write-Host "    risk_management caps (YAML, informational):"
  foreach ($k in $keys) {
    if ($rm.ContainsKey($k)) {
      Write-Host ("      {0}: {1}" -f $k, $rm[$k])
    }
  }
}

Write-Host "=== Live trading preflight (read-only) ===" -ForegroundColor Cyan
Write-Host "monorepo: $monoRoot"
Write-Host "bitcoin-trading: $btRoot"
Write-Host "daemon SSOT: $btRoot\scripts\start_24h_daemon.py"
Write-Host ""

$cfgTestnetRaw = Get-TopLevelYamlScalar -Path $cfgFile -Key "testnet"
$cfgEnableLiveRaw = Get-TopLevelYamlScalar -Path $cfgFile -Key "enable_live_trading"
$cfgEnableRaw = Get-TopLevelYamlScalar -Path $cfgFile -Key "enable_trading"
$cfgEnableTradingRaw = if ($cfgEnableLiveRaw) { $cfgEnableLiveRaw } else { $cfgEnableRaw }

$cfgTestnet = (Parse-BoolLike -Raw $cfgTestnetRaw -Default $true).Value
$cfgEnableTrading = (Parse-BoolLike -Raw $cfgEnableTradingRaw -Default $false).Value

if (Test-Path -LiteralPath $cfgFile) {
  Write-Host "[ok] trading_config.yaml: $cfgFile"
  Write-Host ("    [cfg] testnet default            = {0} (raw: {1})" -f $cfgTestnet, $(if ($null -eq $cfgTestnetRaw) { "<missing>" } else { $cfgTestnetRaw }))
  Write-Host ("    [cfg] enable_trading default     = {0} (enable_live_trading: {1}, enable_trading: {2})" -f $cfgEnableTrading, $(if ($null -eq $cfgEnableLiveRaw) { "<missing>" } else { $cfgEnableLiveRaw }), $(if ($null -eq $cfgEnableRaw) { "<missing>" } else { $cfgEnableRaw }))
  Show-RiskCaps -Path $cfgFile
} else {
  Write-Host "[!] Missing trading_config.yaml (daemon defaults may apply)" -ForegroundColor Yellow
}

Write-Host ""
if (-not (Test-Path -LiteralPath $envFile)) {
  Write-Host "[!] Missing: $envFile  (copy from .env.example and add keys manually)" -ForegroundColor Yellow
  $m = @{}
} else {
  Write-Host "[ok] .env present: $envFile"
  $m = Get-DotEnvKeys $envFile
  $et = $m["ENABLE_TRADING"]
  $tn = $m["TESTNET"]
  $k = $m["BINANCE_API_KEY"]
  Write-Host "    ENABLE_TRADING = $(if ($null -eq $et) { '(unset in .env -> YAML default)' } else { $et })"
  Write-Host "    TESTNET        = $(if ($null -eq $tn) { '(unset in .env -> YAML default)' } else { $tn })"
  Write-Host "    BINANCE_API_KEY= $(if ($k -and $k.Trim().Length -gt 0) { '<set>' } else { '<missing>' })"
}

$etRaw = $m["ENABLE_TRADING"]
$tnRaw = $m["TESTNET"]
$etInfo = Parse-BoolLike -Raw $etRaw -Default $cfgEnableTrading
$tnInfo = Parse-BoolLike -Raw $tnRaw -Default $cfgTestnet
$effectiveEnable = $etInfo.Value
$effectiveTestnet = $tnInfo.Value

Write-Host ""
Write-Host "Effective (matches start_24h_daemon.py: .env overrides YAML when set):" -ForegroundColor Cyan
Write-Host ("  testnet         = {0} ({1})" -f $effectiveTestnet, $(if ($effectiveTestnet) { "TESTNET mode" } else { "MAINNET mode" }))
Write-Host ("  enable_trading  = {0} ({1})" -f $effectiveEnable, $(if ($effectiveEnable) { "TRADING enabled" } else { "TRADING disabled (monitor-only)" }))

if ($etRaw -and -not $etInfo.Parsed) {
  Write-Host "[!] ENABLE_TRADING is set but not a recognized boolean token; falling back to YAML default." -ForegroundColor Yellow
}
if ($tnRaw -and -not $tnInfo.Parsed) {
  Write-Host "[!] TESTNET is set but not a recognized boolean token; falling back to YAML default." -ForegroundColor Yellow
}

$kPresent = $false
if ($m["BINANCE_API_KEY"] -and $m["BINANCE_API_KEY"].Trim().Length -gt 0) { $kPresent = $true }

Write-Host ""
if ((-not $effectiveTestnet) -and $effectiveEnable -and $kPresent) {
  Write-Host "[!!] REAL ORDER PROFILE: mainnet + trading ON + key present -> orders possible if daemon runs." -ForegroundColor Red
} elseif ((-not $effectiveTestnet) -and $effectiveEnable -and -not $kPresent) {
  Write-Host "[!] mainnet + trading ON but BINANCE_API_KEY missing in .env -> likely broken or blocked; fix before restart." -ForegroundColor Yellow
} elseif ($effectiveTestnet -and $effectiveEnable) {
  Write-Host "[i] testnet + trading ON -> live mainnet orders should not fire (verify exchange endpoints still match intent)." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Next (manual, human-approved):"
Write-Host '  1) pm2 describe <app> -> confirm exec cwd + script path (live tree vs lab clone).'
Write-Host '  2) git pull in THAT cwd root only -> pm2 restart <that app> (never restart all unless runbook exception).'
Write-Host '  3) Confirm daemon banner lines: "testnet: False (MAINNET)" and "trading: enabled".'
Write-Host "See: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md , projects/bitcoin-trading/AGENTS.md , ops/v2/ssh/VPS_PM2_HEALTH_SSH_CURSOR_RUNBOOK.md"
exit 0
