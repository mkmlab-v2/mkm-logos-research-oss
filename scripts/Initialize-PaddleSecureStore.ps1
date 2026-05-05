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
    }
    else {
        $value = Read-Host -Prompt $Prompt
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "Skipped '$Key' (empty input)." -ForegroundColor Yellow
        return
    }

    powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action set -Key $Key -Value $value | Out-Host
}

Write-Host "=== Paddle Secure Store Initialization (DPAPI) ===" -ForegroundColor Cyan
Write-Host "Values are encrypted with current Windows user scope." -ForegroundColor DarkCyan

Set-SecretInteractive -Key "PADDLE_EMAIL" -Prompt "Paddle account email"
Set-SecretInteractive -Key "PADDLE_VENDOR_ID" -Prompt "Paddle vendor id (optional)"
Set-SecretInteractive -Key "PADDLE_API_KEY" -Prompt "Paddle API key (optional, hidden)" -SecretInput
Set-SecretInteractive -Key "PADDLE_PAYONEER_EMAIL" -Prompt "Payoneer payout email (optional)"
Set-SecretInteractive -Key "PADDLE_LEGAL_ENTITY_TYPE" -Prompt "Legal entity type (individual|corporation|non_profit|partnership)"
Set-SecretInteractive -Key "NEXT_PUBLIC_PADDLE_CLIENT_TOKEN" -Prompt "Paddle client token for Paddle.js (optional, hidden)" -SecretInput
Set-SecretInteractive -Key "NEXT_PUBLIC_PADDLE_PRICE_ID" -Prompt "Paddle price id for checkout (optional)"
Set-SecretInteractive -Key "NEXT_PUBLIC_PADDLE_ENV" -Prompt "Paddle env for web (sandbox|live, optional)"

Write-Host ""
Write-Host "Stored keys:" -ForegroundColor Green
powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action list | Out-Host

