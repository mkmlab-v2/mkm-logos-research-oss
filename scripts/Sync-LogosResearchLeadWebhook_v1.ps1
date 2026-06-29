#Requires -Version 5.1
<#
.SYNOPSIS
  Wire LOGOS_RESEARCH_LEAD_WEBHOOK_URL into no1kmedi .env.local (and optional VPS PM2 env).

.DESCRIPTION
  Resolution order for webhook URL:
    1. LOGOS_RESEARCH_LEAD_WEBHOOK_URL
    2. FREE_VALIDATION_LEAD_WEBHOOK_URL
    3. OPS_ALARM_WEBHOOK_URL
    4. SLACK_WEBHOOK_URL

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-LogosResearchLeadWebhook_v1.ps1 -SyncVps -PostSmoke
#>
param(
    [switch]$SyncVps,
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

function Upsert-DotEnvKey([string]$path, [string]$key, [string]$value) {
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

$workspaceEnv = Join-Path $root ".env"
$no1kmediLocal = Join-Path $root "projects\no1kmedi\.env.local"

$keys = @(
    "LOGOS_RESEARCH_LEAD_WEBHOOK_URL",
    "FREE_VALIDATION_LEAD_WEBHOOK_URL",
    "OPS_ALARM_WEBHOOK_URL",
    "SLACK_WEBHOOK_URL"
)

$resolvedKey = ""
$resolvedUrl = ""
foreach ($key in $keys) {
    $val = Get-EnvAny $key
    if (-not $val) { $val = Read-DotEnvKey $workspaceEnv $key }
    if (-not $val) { $val = Read-DotEnvKey $no1kmediLocal $key }
    if ($val) {
        $resolvedKey = $key
        $resolvedUrl = $val
        break
    }
}

if (-not $resolvedUrl) {
    Write-Error "No webhook URL found. Set LOGOS_RESEARCH_LEAD_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL in C:\workspace\.env"
}

Write-Host "[logos-lead-webhook] resolved from $resolvedKey (host redacted)" -ForegroundColor Cyan

if ($WhatIfOnly) {
    Write-Host "[logos-lead-webhook] WhatIf: would upsert LOGOS_RESEARCH_LEAD_WEBHOOK_URL in $no1kmediLocal"
    if ($SyncVps) { Write-Host "[logos-lead-webhook] WhatIf: would SSH VPS .env.local + pm2 restart no1kmedi-com" }
    exit 0
}

Upsert-DotEnvKey $no1kmediLocal "LOGOS_RESEARCH_LEAD_WEBHOOK_URL" $resolvedUrl
Write-Host "[logos-lead-webhook] updated $no1kmediLocal" -ForegroundColor Green

if ($SyncVps) {
    $hostName = Get-EnvAny "MKM_VPS_HOST"
    if (-not $hostName) { $hostName = "vps-mkmlife" }
    $user = Get-EnvAny "MKM_VPS_USER"
    if (-not $user) { $user = "root" }
    $remote = "${user}@${hostName}"
    $vpsDest = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"
    $escaped = $resolvedUrl -replace "'", "'\\''"
    $remoteCmd = @"
ENV_FILE='$vpsDest/.env.local'
touch "`$ENV_FILE"
if grep -q '^LOGOS_RESEARCH_LEAD_WEBHOOK_URL=' "`$ENV_FILE"; then
  sed -i 's|^LOGOS_RESEARCH_LEAD_WEBHOOK_URL=.*|LOGOS_RESEARCH_LEAD_WEBHOOK_URL=$escaped|' "`$ENV_FILE"
else
  echo 'LOGOS_RESEARCH_LEAD_WEBHOOK_URL=$escaped' >> "`$ENV_FILE"
fi
pm2 restart no1kmedi-com --update-env
pm2 save
echo '[logos-lead-webhook] VPS env updated'
"@.Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

    $extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
    $sshArgs = @()
    if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

    Write-Host "[logos-lead-webhook] VPS sync + pm2 restart" -ForegroundColor Cyan
    & ssh @($sshArgs + @($remote, $remoteCmd))
    if ($LASTEXITCODE -ne 0) { throw "VPS webhook sync failed exit $LASTEXITCODE" }
}

if ($PostSmoke) {
    & py (Join-Path $root "scripts\check_logos_studio_lead_api_smoke_v1.py") --base "https://logos.jema-ai.com" --require-webhook
    if ($LASTEXITCODE -ne 0) { throw "logos lead webhook smoke failed exit $LASTEXITCODE" }
}

Write-Host "[logos-lead-webhook] OK" -ForegroundColor Green
