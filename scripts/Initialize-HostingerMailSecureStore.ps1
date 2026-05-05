[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$storeScript = Join-Path $PSScriptRoot "Invoke-EncryptedSecretStore.ps1"
if (-not (Test-Path -LiteralPath $storeScript)) {
    throw "Required script not found: $storeScript"
}

function Set-SecretInteractive {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Prompt,
        [switch]$SecretInput
    )

    if ($SecretInput) {
        $secure = Read-Host -Prompt $Prompt -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    } else {
        $value = Read-Host -Prompt $Prompt
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "Skipped '$Key' (empty input)." -ForegroundColor Yellow
        return
    }

    powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action set -Key $Key -Value $value | Out-Host
}

Write-Host "=== Hostinger SMTP Secure Store Initialization (DPAPI) ===" -ForegroundColor Cyan
Write-Host "Values are encrypted with current Windows user scope." -ForegroundColor DarkCyan

Set-SecretInteractive -Key "HOSTINGER_SMTP_HOST" -Prompt "SMTP host (default smtp.hostinger.com)"
Set-SecretInteractive -Key "HOSTINGER_SMTP_PORT" -Prompt "SMTP port (default 465)"
Set-SecretInteractive -Key "HOSTINGER_SMTP_SECURE" -Prompt "SMTP secure true/false (default true)"
Set-SecretInteractive -Key "HOSTINGER_SMTP_USER" -Prompt "SMTP user (e.g. admin@no1kmedi.com)"
Set-SecretInteractive -Key "HOSTINGER_SMTP_PASS" -Prompt "SMTP password (hidden)" -SecretInput
Set-SecretInteractive -Key "HOSTINGER_SMTP_SENDER" -Prompt "Sender email (default same as SMTP user)"

Write-Host ""
Write-Host "Stored keys:" -ForegroundColor Green
powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action list | Out-Host
