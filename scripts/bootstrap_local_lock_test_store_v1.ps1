[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AppData,

    [Parameter(Mandatory = $true)]
    [string]$Key,

    [Parameter(Mandatory = $true)]
    [string]$Value
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$env:APPDATA = $AppData
$bootstrap = Join-Path $PSScriptRoot 'Invoke-LocalLock_v1.ps1'

$secure = ConvertTo-SecureString -String $Value -AsPlainText -Force
$cipher = ConvertFrom-SecureString -SecureString $secure
$mkm = Join-Path $AppData 'MKM'
if (-not (Test-Path -LiteralPath $mkm)) {
    New-Item -ItemType Directory -Path $mkm -Force | Out-Null
}
$storePath = Join-Path $mkm 'secret_store_v1.json'
$store = [ordered]@{}
if (Test-Path -LiteralPath $storePath) {
    $existing = Get-Content -LiteralPath $storePath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($prop in $existing.PSObject.Properties) {
        $store[$prop.Name] = [ordered]@{
            encrypted   = [string]$prop.Value.encrypted
            updated_utc = [string]$prop.Value.updated_utc
        }
    }
}
$store[$Key] = [ordered]@{
    encrypted   = $cipher
    updated_utc = (Get-Date).ToUniversalTime().ToString('o')
}
($store | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $storePath -Encoding UTF8
Write-Output "OK: bootstrap secret for $Key"
