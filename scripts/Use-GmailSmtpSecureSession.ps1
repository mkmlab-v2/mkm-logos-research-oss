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

Write-Host "=== Loading Gmail SMTP secrets into process env ===" -ForegroundColor Cyan

Try-LoadSecret -Key "GMAIL_SMTP_USER" -EnvName "GMAIL_SMTP_USER"
Try-LoadSecret -Key "GMAIL_APP_PASSWORD" -EnvName "GMAIL_APP_PASSWORD"
Try-LoadSecret -Key "GMAIL_SMTP_HOST" -EnvName "GMAIL_SMTP_HOST"
Try-LoadSecret -Key "GMAIL_SMTP_PORT" -EnvName "GMAIL_SMTP_PORT"

if (-not [Environment]::GetEnvironmentVariable("GMAIL_SMTP_USER", "Process")) {
    [Environment]::SetEnvironmentVariable("GMAIL_SMTP_USER", "moksorinw@gmail.com", "Process")
}
if (-not [Environment]::GetEnvironmentVariable("GMAIL_SMTP_HOST", "Process")) {
    [Environment]::SetEnvironmentVariable("GMAIL_SMTP_HOST", "smtp.gmail.com", "Process")
}
if (-not [Environment]::GetEnvironmentVariable("GMAIL_SMTP_PORT", "Process")) {
    [Environment]::SetEnvironmentVariable("GMAIL_SMTP_PORT", "587", "Process")
}

Write-Host "Done. Secrets are available in current process scope only." -ForegroundColor DarkCyan
