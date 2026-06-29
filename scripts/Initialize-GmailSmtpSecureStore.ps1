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

Write-Host "=== Gmail SMTP Secure Store (morning digest outbound) ===" -ForegroundColor Cyan
Write-Host "Google Account -> Security -> 2-Step Verification -> App passwords" -ForegroundColor DarkCyan
Write-Host "Use app password (16 chars), not your login password." -ForegroundColor DarkCyan

Set-SecretInteractive -Key "GMAIL_SMTP_USER" -Prompt "Gmail address (default moksorinw@gmail.com)"
Set-SecretInteractive -Key "GMAIL_APP_PASSWORD" -Prompt "Gmail app password (hidden)" -SecretInput
Set-SecretInteractive -Key "GMAIL_SMTP_HOST" -Prompt "SMTP host (default smtp.gmail.com)"
Set-SecretInteractive -Key "GMAIL_SMTP_PORT" -Prompt "SMTP port (default 587)"

Write-Host ""
Write-Host "Stored keys:" -ForegroundColor Green
powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action list | Out-Host
