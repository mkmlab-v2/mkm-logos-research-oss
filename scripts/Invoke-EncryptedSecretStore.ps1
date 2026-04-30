[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("set", "get", "remove", "list")]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$Key,

    [Parameter(Mandatory = $false)]
    [string]$Value,

    [switch]$AsPlainText
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-SecretStorePath {
    $root = Join-Path $env:APPDATA "MKM"
    if (-not (Test-Path -LiteralPath $root)) {
        New-Item -ItemType Directory -Path $root -Force | Out-Null
    }
    return (Join-Path $root "secret_store_v1.json")
}

function Read-Store([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return @{}
    }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return @{}
    }
    $obj = $raw | ConvertFrom-Json
    $table = @{}
    foreach ($p in $obj.PSObject.Properties) {
        $table[$p.Name] = @{
            encrypted = [string]$p.Value.encrypted
            updated_utc = [string]$p.Value.updated_utc
        }
    }
    return $table
}

function Write-Store([string]$Path, [hashtable]$Data) {
    $json = $Data | ConvertTo-Json -Depth 5
    Set-Content -LiteralPath $Path -Value $json -Encoding UTF8
}

function Protect-PlainText([string]$Plain) {
    $secure = ConvertTo-SecureString -String $Plain -AsPlainText -Force
    # Windows DPAPI (CurrentUser scope) via SecureString serialization.
    return (ConvertFrom-SecureString -SecureString $secure)
}

function Unprotect-ToPlainText([string]$Cipher) {
    $secure = ConvertTo-SecureString -String $Cipher
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

$storePath = Get-SecretStorePath
$store = Read-Store -Path $storePath

switch ($Action) {
    "set" {
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw "Key is required for action 'set'."
        }
        if ($null -eq $Value) {
            throw "Value is required for action 'set'."
        }

        $cipher = Protect-PlainText -Plain $Value
        $store[$Key] = @{
            encrypted = $cipher
            updated_utc = (Get-Date).ToUniversalTime().ToString("o")
        }
        Write-Store -Path $storePath -Data $store
        Write-Output "Saved key '$Key' to encrypted store: $storePath"
    }

    "get" {
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw "Key is required for action 'get'."
        }
        if (-not $store.ContainsKey($Key)) {
            throw "Key '$Key' was not found in encrypted store."
        }

        $cipher = [string]$store[$Key].encrypted
        $plain = Unprotect-ToPlainText -Cipher $cipher
        if ($AsPlainText) {
            Write-Output $plain
        }
        else {
            Write-Output "Key '$Key' found. Use -AsPlainText to print value."
        }
    }

    "remove" {
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw "Key is required for action 'remove'."
        }
        if ($store.ContainsKey($Key)) {
            [void]$store.Remove($Key)
            Write-Store -Path $storePath -Data $store
            Write-Output "Removed key '$Key' from encrypted store."
        }
        else {
            Write-Output "Key '$Key' does not exist. Nothing to remove."
        }
    }

    "list" {
        $keys = @($store.Keys | Sort-Object)
        if ($keys.Count -eq 0) {
            Write-Output "No keys in encrypted store."
        }
        else {
            $keys | ForEach-Object { Write-Output $_ }
        }
    }
}

