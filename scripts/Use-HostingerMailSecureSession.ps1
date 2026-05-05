[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$storeScript = Join-Path $PSScriptRoot "Invoke-EncryptedSecretStore.ps1"
if (-not (Test-Path -LiteralPath $storeScript)) {
    throw "Required script not found: $storeScript"
}

function Try-LoadSecret([string]$Key, [string]$EnvName) {
    try {
        $val = powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action get -Key $Key -AsPlainText
        if (-not [string]::IsNullOrWhiteSpace($val)) {
            [Environment]::SetEnvironmentVariable($EnvName, $val, "Process")
            Write-Host "Loaded $EnvName from secure store." -ForegroundColor Green
        }
    }
    catch {
        Write-Host "Key '$Key' not found (skipped)." -ForegroundColor Yellow
    }
}

Write-Host "=== Loading Hostinger SMTP secrets into process env ===" -ForegroundColor Cyan

Try-LoadSecret -Key "HOSTINGER_SMTP_HOST" -EnvName "HOSTINGER_SMTP_HOST"
Try-LoadSecret -Key "HOSTINGER_SMTP_PORT" -EnvName "HOSTINGER_SMTP_PORT"
Try-LoadSecret -Key "HOSTINGER_SMTP_SECURE" -EnvName "HOSTINGER_SMTP_SECURE"
Try-LoadSecret -Key "HOSTINGER_SMTP_USER" -EnvName "HOSTINGER_SMTP_USER"
Try-LoadSecret -Key "HOSTINGER_SMTP_PASS" -EnvName "HOSTINGER_SMTP_PASS"
Try-LoadSecret -Key "HOSTINGER_SMTP_SENDER" -EnvName "HOSTINGER_SMTP_SENDER"

Write-Host "Done. Secrets are available in current process scope only." -ForegroundColor DarkCyan
