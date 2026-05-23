#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN is set locally, on no1kmedi VPS, and mkmlife Cloudflare Worker.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-PersonalInsightEvolutionIngestSecret_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-PersonalInsightEvolutionIngestSecret_v1.ps1 -SkipCloudflare -SkipVps
#>
param(
    [switch]$SkipCloudflare,
    [switch]$SkipVps,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
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
    $lines = @()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]]@(
            Get-Content -LiteralPath $path -Encoding UTF8
        )
    } else {
        $lines = [System.Collections.Generic.List[string]]@()
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
$mkmLifeLocal = Join-Path $root "projects\mkm\mkm-life\.env.local"

$token = Get-EnvAny "PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN"
if (-not $token) { $token = Read-DotEnvKey $workspaceEnv "PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN" }
if (-not $token) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    Write-Host "[piev1-ingest-secret] generated new token (not printed)"
}

if ($WhatIfOnly) {
    Write-Host "[piev1-ingest-secret] WhatIf: would upsert token in workspace .env, no1kmedi/.env.local, mkm-life/.env.local"
    if (-not $SkipVps) { Write-Host "[piev1-ingest-secret] WhatIf: would SSH VPS no1kmedi .env.local + pm2 restart" }
    if (-not $SkipCloudflare) { Write-Host "[piev1-ingest-secret] WhatIf: would wrangler secret put on mkmlife worker" }
    exit 0
}

Upsert-DotEnvKey $workspaceEnv "PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN" $token
Upsert-DotEnvKey $no1kmediLocal "PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN" $token
Upsert-DotEnvKey $mkmLifeLocal "PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN" $token
Write-Host "[piev1-ingest-secret] local .env files updated"

if (-not $SkipVps) {
    $hostName = Get-EnvAny "MKM_VPS_HOST"
    if (-not $hostName) { $hostName = "vps-mkmlife" }
    $user = Get-EnvAny "MKM_VPS_USER"
    if (-not $user) { $user = "root" }
    $remote = "${user}@${hostName}"
    $vpsDest = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"
    $escaped = $token -replace "'", "'\\''"
    $remoteCmd = @"
ENV_FILE='$vpsDest/.env.local'
touch "`$ENV_FILE"
if grep -q '^PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN=' "`$ENV_FILE"; then
  sed -i 's|^PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN=.*|PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN=$escaped|' "`$ENV_FILE"
else
  echo 'PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN=$escaped' >> "`$ENV_FILE"
fi
pm2 restart no1kmedi-com --update-env
"@.Replace("`r`n", "`n").TrimEnd() + "`n"

    $sshArgs = @()
    $extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
    if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }
    Write-Host "[piev1-ingest-secret] VPS: $remote ($vpsDest/.env.local)"
    & ssh @($sshArgs + @($remote, $remoteCmd))
    if ($LASTEXITCODE -ne 0) { throw "VPS ingest token sync failed (exit $LASTEXITCODE)" }
}

if (-not $SkipCloudflare) {
    $mkmRoot = Join-Path $root "projects\mkm\mkm-life"
    Push-Location $mkmRoot
    try {
        $savedCf = $env:CLOUDFLARE_API_TOKEN
        $savedCfAlias = $env:CF_API_TOKEN
        if (-not $env:MKM_WRANGLER_FORCE_API_TOKEN) {
            Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
            Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
        }
        $token | npx wrangler secret put PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN --config wrangler.jsonc
        if ($LASTEXITCODE -ne 0) { throw "wrangler secret put failed (exit $LASTEXITCODE)" }
        if ($null -ne $savedCf) { $env:CLOUDFLARE_API_TOKEN = $savedCf }
        if ($null -ne $savedCfAlias) { $env:CF_API_TOKEN = $savedCfAlias }
        Write-Host "[piev1-ingest-secret] Cloudflare Worker secret updated"
    } finally {
        Pop-Location
    }
}

Write-Host "[piev1-ingest-secret] done (token not logged)"
