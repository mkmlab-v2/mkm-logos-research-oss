#Requires -Version 5.1
<#
.SYNOPSIS
  Sync clinician Pro allowlist + LLM keys into no1kmedi VPS .env.local and restart PM2.

.DESCRIPTION
  Reads from projects/no1kmedi/.env.local (fallback C:\workspace\.env):
    GOOGLE_API_KEY, OPENROUTER_API_KEY, OPENROUTER_MODEL, JEMA_AI_LLM_PRIORITY

  Always upserts KM_CLINICIAN_PRO_EMAIL_ALLOWLIST (default smoke + admin ops emails).

  Run before or after Deploy-No1kmediDestinyTarball_v1.ps1 (tarball excludes .env.local).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-No1kmediClinicianOpsEnvToVps_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-No1kmediClinicianOpsEnvToVps_v1.ps1 -PostSmoke
#>
param(
    [string]$Allowlist = "",
    [string[]]$ExtraEmails = @("smoke-paste-chart@local.test", "admin@no1kmedi.com", "moksorinw@gmail.com"),
    [switch]$SyncLocalEnv,
    [switch]$PostSmoke,
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

$localEnv = Join-Path $root "projects\no1kmedi\.env.local"
$workspaceEnv = Join-Path $root ".env"
$llmKeys = @("GOOGLE_API_KEY", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "JEMA_AI_LLM_PRIORITY")
$pairs = @{}
foreach ($k in $llmKeys) {
    $v = Read-DotEnvKey $localEnv $k
    if (-not $v) { $v = Read-DotEnvKey $workspaceEnv $k }
    if ($v) { $pairs[$k] = $v }
}
$pairs["KM_CLINICIAN_PRO_EMAIL_ALLOWLIST"] = if ($Allowlist.Trim()) {
    $Allowlist.Trim()
} else {
    ($ExtraEmails | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ } | Select-Object -Unique) -join ","
}

if ($pairs.Count -lt 2) {
    throw "Need at least allowlist + one LLM key in projects/no1kmedi/.env.local or .env"
}

Write-Host "[clinician-ops-vps] keys: $($pairs.Keys -join ', ') (values redacted)" -ForegroundColor Cyan

function Upsert-DotEnvKeyLocal([string]$path, [string]$key, [string]$value) {
    $lines = [System.Collections.Generic.List[string]]@()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]]@(Get-Content -LiteralPath $path -Encoding UTF8)
    }
    $pattern = "^\s*$([regex]::Escape($key))\s*="
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) { $idx = $i; break }
    }
    $newLine = "$key=$value"
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $path -Value ($lines -join "`n") -Encoding UTF8 -NoNewline
    Add-Content -LiteralPath $path -Value "`n" -Encoding UTF8
}

if ($SyncLocalEnv) {
    Upsert-DotEnvKeyLocal $localEnv "KM_CLINICIAN_PRO_EMAIL_ALLOWLIST" $pairs["KM_CLINICIAN_PRO_EMAIL_ALLOWLIST"]
    Write-Host "[clinician-ops-vps] updated local $localEnv allowlist" -ForegroundColor Green
}

if ($WhatIfOnly) {
    Write-Host "[clinician-ops-vps] WhatIf: would SSH upsert on VPS .env.local + pm2 restart no1kmedi-com"
    exit 0
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$vpsDest = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"

$upsertLines = @()
foreach ($key in $pairs.Keys) {
    $escaped = ($pairs[$key] -replace "\\", "\\\\") -replace "'", "'\\''"
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
pm2 restart no1kmedi-com --update-env
pm2 save
echo '[clinician-ops-vps] VPS env updated'
"@.Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshArgs = @()
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

Write-Host "[clinician-ops-vps] VPS sync + pm2 restart ($remote)" -ForegroundColor Cyan
& ssh @($sshArgs + @($remote, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "VPS clinician ops env sync failed exit $LASTEXITCODE" }

if ($PostSmoke) {
    $base = Get-EnvAny "NO1KMEDI_BASE_URL"
    if (-not $base) { $base = "https://app.jema-ai.com" }
    Push-Location (Join-Path $root "projects\no1kmedi")
    try {
        $env:NO1KMEDI_BASE_URL = $base
        $env:PASTE_EXTRACT_HTTP_REQUIRE_LLM = "1"
        & npm run smoke:clinician-paste-extract-http
        if ($LASTEXITCODE -ne 0) { throw "paste-extract HTTP smoke failed exit $LASTEXITCODE" }
    } finally { Pop-Location }
}

Write-Host "[clinician-ops-vps] OK" -ForegroundColor Green
