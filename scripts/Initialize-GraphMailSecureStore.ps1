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

Write-Host "=== Graph Mail Secure Store Initialization (DPAPI) ===" -ForegroundColor Cyan
Write-Host "Values are encrypted with current Windows user scope." -ForegroundColor DarkCyan

Set-SecretInteractive -Key "GRAPH_TENANT_ID" -Prompt "Graph tenant id (GUID)"
Set-SecretInteractive -Key "GRAPH_CLIENT_ID" -Prompt "Graph client id (GUID)"
Set-SecretInteractive -Key "GRAPH_CLIENT_SECRET" -Prompt "Graph client secret (hidden)" -SecretInput
Set-SecretInteractive -Key "GRAPH_SENDER_UPN" -Prompt "Sender mailbox UPN (e.g. sender@domain.com)"
Set-SecretInteractive -Key "GRAPH_APPROVAL_OTP_SEED" -Prompt "Approval OTP seed (hidden)" -SecretInput
Set-SecretInteractive -Key "GRAPH_RECIPIENT_EMAIL" -Prompt "Recipient email (default admin@no1kmedi.com)"
Set-SecretInteractive -Key "GRAPH_MAIL_SUBJECT" -Prompt "Mail subject (optional)"
Set-SecretInteractive -Key "GRAPH_MAIL_BODY_FILE" -Prompt "Mail body file path (optional)"

Write-Host ""
Write-Host "Stored keys:" -ForegroundColor Green
powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action list | Out-Host
