#Requires -Version 5.1
<#
.SYNOPSIS
  Copy AZURE_OPENAI_* and MKM_LLM_PRIORITY from workspace .env to VPS monorepo .env (no secret echo).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-AzureOpenAiEnvToVps_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$VpsHost = "",
    [string]$VpsUser = "root",
    [string]$VpsRepoRoot = "",
    [string]$SshKeyPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-DotEnvKeys {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^\s*#' -or [string]::IsNullOrWhiteSpace($line)) { return }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }
        $k = $line.Substring(0, $idx).Trim()
        $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        if ($k) { $map[$k] = $v }
    }
    return $map
}

function Get-EnvAny {
    param([string]$Name)
    $fromProcess = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($fromProcess)) { return $fromProcess }
    $p = Join-Path $RepoRoot ".env"
    $m = Read-DotEnvKeys -Path $p
    if ($m.ContainsKey($Name)) { return $m[$Name] }
    return ""
}

if (-not $VpsHost) { $VpsHost = Get-EnvAny "MKM_VPS_HOST" }
if (-not $SshKeyPath) { $SshKeyPath = Get-EnvAny "MKM_VPS_SSH_KEY_PATH" }
if (-not $VpsRepoRoot) {
    $fromEnv = Get-EnvAny "MKM_VPS_MONOREPO_ROOT"
    if ([string]::IsNullOrWhiteSpace($fromEnv)) { $fromEnv = Get-EnvAny "MKM_VPS_REPO_ROOT" }
    # payapp/no1kmedi live on destiny monorepo; bitcoin-only path must not win
    if ($fromEnv -match 'mkm-lab-workspace') { $VpsRepoRoot = "/opt/mkm-destiny-ai-41e38ec6" }
    elseif (-not [string]::IsNullOrWhiteSpace($fromEnv)) { $VpsRepoRoot = $fromEnv.TrimEnd('/') }
    else { $VpsRepoRoot = "/opt/mkm-destiny-ai-41e38ec6" }
}
if (-not $VpsHost) { throw "MKM_VPS_HOST unset" }

$keys = @(
    "MKM_LLM_PRIORITY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_FETCH_TIMEOUT_MS"
)
$local = Read-DotEnvKeys -Path (Join-Path $RepoRoot ".env")
$lines = @("# --- synced Azure OpenAI LLM (Sync-AzureOpenAiEnvToVps_v1) ---")
foreach ($k in $keys) {
    if ($local.ContainsKey($k) -and -not [string]::IsNullOrWhiteSpace($local[$k])) {
        $lines += "$k=$($local[$k])"
    }
}
if ($lines.Count -le 1) {
    Write-Host "[skip] No AZURE_OPENAI_* values in local .env — fill keys first or run Invoke-ProvisionAzureOpenAi_v1.ps1"
    exit 2
}

$tmp = Join-Path $env:TEMP "mkm_azure_env_sync_$(Get-Random).conf"
$lines | Set-Content -LiteralPath $tmp -Encoding UTF8

$sshTarget = "${VpsUser}@${VpsHost}"
& scp -i $SshKeyPath -o ConnectTimeout=20 $tmp "${sshTarget}:/tmp/mkm_azure_env_sync.conf"
$sshArgs = @("-i", $SshKeyPath, "-o", "ConnectTimeout=20", $sshTarget)
$remoteSh = Join-Path $env:TEMP "mkm_azure_env_apply_$(Get-Random).sh"
$remoteBody = @"
#!/usr/bin/env bash
set -euo pipefail
ENV='$VpsRepoRoot/.env'
touch "`$ENV"
for k in MKM_LLM_PRIORITY AZURE_OPENAI_ENDPOINT AZURE_OPENAI_API_KEY AZURE_OPENAI_DEPLOYMENT AZURE_OPENAI_API_VERSION AZURE_OPENAI_FETCH_TIMEOUT_MS; do
  sed -i "/^`${k}=/d" "`$ENV" 2>/dev/null || true
done
cat /tmp/mkm_azure_env_sync.conf >> "`$ENV"
cd '$VpsRepoRoot/projects/no1kmedi/payapp-api' && pm2 restart ecosystem.config.cjs --only no1kmedi-payapp-api --update-env
sleep 2
curl -sS -m 8 http://127.0.0.1:3847/api/ai/router-status | head -c 800
"@
[System.IO.File]::WriteAllText($remoteSh, ($remoteBody -replace "`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))
& scp -i $SshKeyPath -o ConnectTimeout=20 $remoteSh "${sshTarget}:/tmp/mkm_azure_env_apply.sh"
& ssh @sshArgs "chmod +x /tmp/mkm_azure_env_apply.sh && /tmp/mkm_azure_env_apply.sh"
Remove-Item -LiteralPath $remoteSh -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
Write-Host "[ok] VPS .env patched and payapp-api restarted"
