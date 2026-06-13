#Requires -Version 5.1
<#
.SYNOPSIS
  Sync Turnstile sitekey/secret into no1kmedi VPS .env.local and restart PM2.

.DESCRIPTION
  1. py scripts/sync_turnstile_env_to_no1kmedi_v1.py --target production
  2. Read NEXT_PUBLIC_TURNSTILE_SITEKEY + TURNSTILE_SECRET_KEY from projects/no1kmedi/.env.production
  3. SSH upsert on VPS /opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi/.env.local
  4. pm2 restart no1kmedi-com --update-env

  Run before or after Deploy-No1kmediDestinyTarball_v1.ps1 (tarball excludes .env.local).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-TurnstileEnvToNo1kmediVps_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-TurnstileEnvToNo1kmediVps_v1.ps1 -SkipLocalSync
#>
param(
    [switch]$SkipLocalSync,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $root

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

function Read-DotEnvKey([string]$path, [string]$key) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=\s*(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

$keys = @("NEXT_PUBLIC_TURNSTILE_SITEKEY", "TURNSTILE_SECRET_KEY")
$prodEnv = Join-Path $root "projects\no1kmedi\.env.production"

if (-not $SkipLocalSync) {
    & py (Join-Path $root "scripts\sync_turnstile_env_to_no1kmedi_v1.py") --target all
    if ($LASTEXITCODE -ne 0) { throw "sync_turnstile_env_to_no1kmedi_v1.py failed exit $LASTEXITCODE" }
}

$pairs = @{}
foreach ($key in $keys) {
    $val = Read-DotEnvKey $prodEnv $key
    if (-not $val) { throw "missing $key in $prodEnv — run py scripts/sync_turnstile_env_to_no1kmedi_v1.py --target all" }
    $pairs[$key] = $val
}

Write-Host "[turnstile-vps] sitekey present; secret present (values redacted)" -ForegroundColor Cyan

if ($WhatIfOnly) {
    Write-Host "[turnstile-vps] WhatIf: would SSH upsert $($keys -join ', ') on VPS .env.local + pm2 restart no1kmedi-com"
    exit 0
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$vpsDest = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"

$upsertLines = @()
foreach ($key in $keys) {
    $escaped = $pairs[$key] -replace "'", "'\\''"
    $upsertLines += @"
if grep -q '^$key=' "`$ENV_FILE"; then
  sed -i 's|^$key=.*|$key=$escaped|' "`$ENV_FILE"
else
  echo '$key=$escaped' >> "`$ENV_FILE"
fi
"@
}

$remoteCmd = @"
ENV_FILE='$vpsDest/.env.local'
touch "`$ENV_FILE"
$($upsertLines -join "`n")
if grep -q '^KM_TURNSTILE_SKIP_VERIFY=' "`$ENV_FILE"; then
  sed -i '/^KM_TURNSTILE_SKIP_VERIFY=/d' "`$ENV_FILE"
fi
pm2 restart no1kmedi-com --update-env
pm2 save
echo '[turnstile-vps] VPS env updated'
"@.Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshArgs = @()
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

Write-Host "[turnstile-vps] VPS sync + pm2 restart ($remote)" -ForegroundColor Cyan
& ssh @($sshArgs + @($remote, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "VPS turnstile env sync failed exit $LASTEXITCODE" }

Write-Host "[turnstile-vps] OK" -ForegroundColor Green
