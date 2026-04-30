[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$storeScript = Join-Path $PSScriptRoot "Invoke-EncryptedSecretStore.ps1"
if (-not (Test-Path -LiteralPath $storeScript)) {
    throw "Required script not found: $storeScript"
}

function Try-LoadSecret([string]$Key, [string]$EnvName) {
    $val = $null
    try {
        $val = powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action get -Key $Key -AsPlainText 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "missing"
        }
        if (-not [string]::IsNullOrWhiteSpace($val)) {
            [Environment]::SetEnvironmentVariable($EnvName, $val, "Process")
            Write-Host "Loaded $EnvName from secure store." -ForegroundColor Green
        }
        else {
            Write-Host "Key '$Key' is empty (skipped)." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "Key '$Key' not found (skipped)." -ForegroundColor Yellow
    }
}

Write-Host "=== Loading Paddle secrets into process env ===" -ForegroundColor Cyan

Try-LoadSecret -Key "PADDLE_EMAIL" -EnvName "PADDLE_EMAIL"
Try-LoadSecret -Key "PADDLE_VENDOR_ID" -EnvName "PADDLE_VENDOR_ID"
Try-LoadSecret -Key "PADDLE_API_KEY" -EnvName "PADDLE_API_KEY"
Try-LoadSecret -Key "PADDLE_PAYONEER_EMAIL" -EnvName "PADDLE_PAYONEER_EMAIL"
Try-LoadSecret -Key "PADDLE_LEGAL_ENTITY_TYPE" -EnvName "PADDLE_LEGAL_ENTITY_TYPE"
Try-LoadSecret -Key "NEXT_PUBLIC_PADDLE_CLIENT_TOKEN" -EnvName "NEXT_PUBLIC_PADDLE_CLIENT_TOKEN"
Try-LoadSecret -Key "NEXT_PUBLIC_PADDLE_PRICE_ID" -EnvName "NEXT_PUBLIC_PADDLE_PRICE_ID"
Try-LoadSecret -Key "NEXT_PUBLIC_PADDLE_ENV" -EnvName "NEXT_PUBLIC_PADDLE_ENV"

Write-Host "Done. Secrets are available in current process scope only." -ForegroundColor DarkCyan

