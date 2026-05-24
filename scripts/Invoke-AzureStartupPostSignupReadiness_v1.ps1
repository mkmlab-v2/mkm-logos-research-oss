#Requires -Version 5.1
<#
.SYNOPSIS
  Post-signup readiness for Microsoft for Startups + Azure subscription (local .env SSOT).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureStartupPostSignupReadiness_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutJson = (Join-Path $RepoRoot "reports\azure_startup_post_signup_readiness_latest.json")
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
        if ($line -match '^\s*export\s+') { $line = ($line -replace '^\s*export\s+', '') }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }
        $k = $line.Substring(0, $idx).Trim()
        $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        if ($k) { $map[$k] = $v }
    }
    return $map
}

$envPath = Join-Path $RepoRoot ".env"
$artifactPath = Join-Path $RepoRoot "reports\azure_startup_subscription_v1_latest.json"
$required = @(
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_SIGNUP_ACCOUNT_EMAIL",
    "AZURE_STARTUP_OFFER"
)

$envMap = Read-DotEnvKeys -Path $envPath
$missing = @($required | Where-Object { -not $envMap.ContainsKey($_) -or [string]::IsNullOrWhiteSpace($envMap[$_]) })

$azCliOk = $false
$azAccount = $null
$azMsg = "az CLI not logged in (optional: az login --use-device-code)"
if (Get-Command az -ErrorAction SilentlyContinue) {
    try {
        $azJson = & az account show 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0 -and $azJson -match '"id"') {
            $azAccount = $azJson | ConvertFrom-Json
            $azCliOk = $true
            $azMsg = "az account show OK"
            if ($envMap["AZURE_SUBSCRIPTION_ID"] -and $azAccount.id -ne $envMap["AZURE_SUBSCRIPTION_ID"]) {
                $azMsg = "az subscription id differs from .env — run: az account set --subscription $($envMap['AZURE_SUBSCRIPTION_ID'])"
            }
        }
    }
    catch {
        $azMsg = "az account show failed (optional): $($_.Exception.Message)"
    }
}

$manualRemainder = @(
    "Portal home: Verify your startup (may unlock higher tier / Founders Hub benefits)",
    "Optional: rename subscription from 'Azure subscription 1' to MKM-Startups-Prod",
    "Optional: az login --use-device-code for CLI automation on this PC"
)

$readinessOk = ($missing.Count -eq 0) -and (Test-Path -LiteralPath $artifactPath)

$doc = [ordered]@{
    schema                     = "azure_startup_post_signup_readiness_v1"
    checked_at_utc             = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    readiness_ok               = $readinessOk
    env_path                   = $envPath
    artifact_path              = $artifactPath
    missing_env_keys           = $missing
    azure_cli_logged_in        = $azCliOk
    azure_cli_message          = $azMsg
    subscription_id            = $envMap["AZURE_SUBSCRIPTION_ID"]
    signup_account_email       = $envMap["AZURE_SIGNUP_ACCOUNT_EMAIL"]
    startup_offer              = $envMap["AZURE_STARTUP_OFFER"]
    startup_credits_usd        = $envMap["AZURE_STARTUP_CREDITS_USD_REMAINING"]
    startup_credits_expire     = $envMap["AZURE_STARTUP_CREDITS_EXPIRE"]
    tenant_domain              = $envMap["AZURE_TENANT_DOMAIN"]
    portal_subscription_url    = "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/resource/subscriptions/$($envMap['AZURE_SUBSCRIPTION_ID'])/overview"
    portal_startup_home_url    = "https://portal.azure.com/?homeview=startup#home"
    signup_completed_url       = "https://signup.azure.com/signup?offer=MS-AZR-0036P&creditId=4d413004-689f-4178-89a0-f493719fc7c5&appId=azsup&redirectURL=https%3A%2F%2Fportal.azure.com%2F%3Fhomeview%3Dstartup%23home"
    manual_remainder           = $manualRemainder
}

$outDir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$doc | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8

Write-Host ""
Write-Host "=== Azure Startup post-signup readiness ===" -ForegroundColor Cyan
Write-Host "env: $envPath"
Write-Host "artifact: $artifactPath"
Write-Host "report: $OutJson"
if ($missing.Count -gt 0) {
    Write-Host "[fail] missing .env keys: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[ok] required .env keys present" -ForegroundColor Green
Write-Host "[info] $azMsg" -ForegroundColor Yellow
foreach ($m in $manualRemainder) {
    Write-Host "  - $m"
}
if (-not $readinessOk) {
    Write-Host "[fail] missing artifact: $artifactPath" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Invoke-AzureStartupPostSignupReadiness_v1: OK (exit 0)" -ForegroundColor Green
exit 0
