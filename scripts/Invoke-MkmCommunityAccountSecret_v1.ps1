[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$AccountId,

    [Parameter(Mandatory = $false)]
    [ValidateSet("github_mkmlab_v2", "reddit_local_llm", "x_mkmlab", "hn_show")]
    [string]$Platform,

    [switch]$SetPassword,
    [switch]$SetUsername,
    [switch]$SetPat,
    [switch]$ListStatus,
    [switch]$ShowLoginUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RegistryPath = Join-Path $Root "docs\final\artifacts\mkm_community_accounts_registry_v1.json"
$StoreScript = Join-Path $PSScriptRoot "Invoke-EncryptedSecretStore.ps1"

if (-not (Test-Path -LiteralPath $RegistryPath)) {
    throw "Registry missing: $RegistryPath"
}

$registry = Get-Content -LiteralPath $RegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$accounts = @($registry.accounts)

function Resolve-Account {
    param([string]$Id, [string]$Plat)
    if ($Id) {
        $hit = $accounts | Where-Object { $_.id -eq $Id } | Select-Object -First 1
        if (-not $hit) { throw "Unknown AccountId: $Id" }
        return $hit
    }
    if ($Plat) {
        $hit = $accounts | Where-Object { $_.platform -eq $Plat } | Select-Object -First 1
        if (-not $hit) { throw "Unknown Platform: $Plat" }
        return $hit
    }
    throw "Provide -AccountId or -Platform"
}

function Get-ConfiguredDpapiKeys {
    $raw = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StoreScript -Action list 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    $text = ($raw | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -match '^No keys in encrypted store') {
        return @()
    }
    return @($text -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Test-DpapiKeyConfigured([string]$Key, [string[]]$ConfiguredKeys) {
    if ([string]::IsNullOrWhiteSpace($Key)) { return $false }
    return $ConfiguredKeys -contains $Key
}

function Prompt-SecureValue([string]$Prompt) {
    $secure = Read-Host -AsSecureString $Prompt
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if ($ListStatus) {
    $configuredKeys = Get-ConfiguredDpapiKeys
    $rows = @()
    foreach ($acct in $accounts) {
        $rows += [ordered]@{
            id = $acct.id
            platform = $acct.platform
            handle = $acct.handle
            username_configured = (Test-DpapiKeyConfigured $acct.dpapi_username_key $configuredKeys)
            password_configured = (Test-DpapiKeyConfigured $acct.dpapi_password_key $configuredKeys)
            pat_configured = if ($acct.PSObject.Properties.Name -contains "dpapi_pat_key") {
                (Test-DpapiKeyConfigured $acct.dpapi_pat_key $configuredKeys)
            } else { $null }
            login_url = $acct.login_url
        }
    }
    $doc = [ordered]@{
        schema = "mkm_community_account_secret_status_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        note = "Boolean only — no secret values emitted"
        accounts = $rows
    }
    $doc | ConvertTo-Json -Depth 6
    exit 0
}

$account = Resolve-Account -Id $AccountId -Plat $Platform

if ($ShowLoginUrl) {
    Write-Output $account.login_url
    exit 0
}

if ($SetUsername) {
    $val = Prompt-SecureValue "Username/email for $($account.id) (stored DPAPI key $($account.dpapi_username_key))"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StoreScript -Action set -Key $account.dpapi_username_key -Value $val
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Output "OK: username key $($account.dpapi_username_key) set (value not echoed)"
    exit 0
}

if ($SetPassword) {
    $val = Prompt-SecureValue "Password for $($account.id) (stored DPAPI key $($account.dpapi_password_key))"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StoreScript -Action set -Key $account.dpapi_password_key -Value $val
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Output "OK: password key $($account.dpapi_password_key) set (value not echoed)"
    exit 0
}

if ($SetPat) {
    if (-not ($account.PSObject.Properties.Name -contains "dpapi_pat_key")) {
        throw "Account $($account.id) has no dpapi_pat_key"
    }
    $val = Prompt-SecureValue "PAT/token for $($account.id) (stored DPAPI key $($account.dpapi_pat_key))"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StoreScript -Action set -Key $account.dpapi_pat_key -Value $val
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Output "OK: PAT key $($account.dpapi_pat_key) set (value not echoed)"
    exit 0
}

Write-Host @"
Usage (passwords never written to repo or chat logs):

  List configured keys (boolean only):
    powershell -File scripts\Invoke-MkmCommunityAccountSecret_v1.ps1 -ListStatus

  Register Reddit username + password (interactive, DPAPI):
    powershell -File scripts\Invoke-MkmCommunityAccountSecret_v1.ps1 -AccountId reddit_local_llm -SetUsername
    powershell -File scripts\Invoke-MkmCommunityAccountSecret_v1.ps1 -AccountId reddit_local_llm -SetPassword

  GitHub PAT (preferred over password):
    powershell -File scripts\Invoke-MkmCommunityAccountSecret_v1.ps1 -AccountId github_mkmlab_v2 -SetPat

  Open login URL hint:
    powershell -File scripts\Invoke-MkmCommunityAccountSecret_v1.ps1 -AccountId x_mkmlab -ShowLoginUrl

Registry (handles only): docs/final/artifacts/mkm_community_accounts_registry_v1.json
"@
