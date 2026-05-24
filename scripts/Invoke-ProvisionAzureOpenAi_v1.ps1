#Requires -Version 5.1
<#
.SYNOPSIS
  Provision Azure OpenAI (Cognitive Services) and write AZURE_OPENAI_* into workspace .env.

  Prereq: az login (device code). Subscription from AZURE_SUBSCRIPTION_ID in .env.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProvisionAzureOpenAi_v1.ps1 -WhatIfOnly
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProvisionAzureOpenAi_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ResourceGroup = "mkm-startups-rg",
    [string]$AccountName = "mkm-openai-prod",
    [string]$Location = "koreacentral",
    [string]$DeploymentName = "gpt-4o-mini",
    [string]$ModelName = "gpt-4o-mini",
    [string]$ModelVersion = "2024-07-18",
    [switch]$WhatIfOnly
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

function Set-EnvKey {
    param([string]$Path, [string]$Key, [string]$Value)
    $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8)
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            $found = $true
            "$Key=$Value"
        }
        else { $line }
    }
    if (-not $found) { $out += "$Key=$Value" }
    $out | Set-Content -LiteralPath $Path -Encoding UTF8
}

$envPath = Join-Path $RepoRoot ".env"
$envMap = Read-DotEnvKeys -Path $envPath
$subId = $envMap["AZURE_SUBSCRIPTION_ID"]
if (-not $subId) { throw "AZURE_SUBSCRIPTION_ID missing in .env" }

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI (az) not found. Install: https://aka.ms/installazurecliwindows"
}

$login = & az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[action] Run: az login --use-device-code" -ForegroundColor Yellow
    if (-not $WhatIfOnly) {
        & az login --use-device-code
    }
}

if ($WhatIfOnly) {
    Write-Host "[whatif] Would create: RG=$ResourceGroup account=$AccountName location=$Location deployment=$DeploymentName"
    exit 0
}

& az account set --subscription $subId | Out-Null

$rgExists = & az group exists --name $ResourceGroup
if ($rgExists -ne "true") {
    & az group create --name $ResourceGroup --location $Location | Out-Null
}

$accountJson = & az cognitiveservices account show --name $AccountName --resource-group $ResourceGroup 2>$null
if ($LASTEXITCODE -ne 0) {
    & az cognitiveservices account create `
        --name $AccountName `
        --resource-group $ResourceGroup `
        --kind OpenAI `
        --sku S0 `
        --location $Location `
        --yes | Out-Null
}

$keys = & az cognitiveservices account keys list --name $AccountName --resource-group $ResourceGroup | ConvertFrom-Json
$endpoint = (& az cognitiveservices account show --name $AccountName --resource-group $ResourceGroup --query "properties.endpoint" -o tsv).Trim()

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$null = & az cognitiveservices account deployment show `
    --name $AccountName --resource-group $ResourceGroup --deployment-name $DeploymentName 2>&1
if ($LASTEXITCODE -ne 0) {
    $null = & az cognitiveservices account deployment create `
        --name $AccountName `
        --resource-group $ResourceGroup `
        --deployment-name $DeploymentName `
        --model-name $ModelName `
        --model-version $ModelVersion `
        --model-format OpenAI `
        --sku-capacity 10 `
        --sku-name Standard 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[warn] Model deployment '$DeploymentName' not created (quota/region). Request quota in Portal -> mkm-openai-prod -> Quotas, then re-run." -ForegroundColor Yellow
    }
}
$ErrorActionPreference = $prevEap

Set-EnvKey -Path $envPath -Key "MKM_LLM_PRIORITY" -Value "azure_first"
Set-EnvKey -Path $envPath -Key "AZURE_OPENAI_ENDPOINT" -Value $endpoint.TrimEnd('/')
Set-EnvKey -Path $envPath -Key "AZURE_OPENAI_API_KEY" -Value $keys.key1
Set-EnvKey -Path $envPath -Key "AZURE_OPENAI_DEPLOYMENT" -Value $DeploymentName
Set-EnvKey -Path $envPath -Key "AZURE_OPENAI_API_VERSION" -Value "2024-08-01-preview"

Write-Host "[ok] .env updated (endpoint + key1 + deployment). Run:" -ForegroundColor Green
Write-Host "  powershell -File scripts\Invoke-AzureOpenAiLlmReadiness_v1.ps1"
Write-Host "  powershell -File scripts\Sync-AzureOpenAiEnvToVps_v1.ps1"
