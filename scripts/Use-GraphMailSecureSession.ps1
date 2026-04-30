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

Write-Host "=== Loading Graph Mail secrets into process env ===" -ForegroundColor Cyan

Try-LoadSecret -Key "GRAPH_TENANT_ID" -EnvName "GRAPH_TENANT_ID"
Try-LoadSecret -Key "GRAPH_CLIENT_ID" -EnvName "GRAPH_CLIENT_ID"
Try-LoadSecret -Key "GRAPH_CLIENT_SECRET" -EnvName "GRAPH_CLIENT_SECRET"
Try-LoadSecret -Key "GRAPH_SENDER_UPN" -EnvName "GRAPH_SENDER_UPN"
Try-LoadSecret -Key "GRAPH_APPROVAL_OTP_SEED" -EnvName "GRAPH_APPROVAL_OTP_SEED"
Try-LoadSecret -Key "GRAPH_RECIPIENT_EMAIL" -EnvName "GRAPH_RECIPIENT_EMAIL"
Try-LoadSecret -Key "GRAPH_MAIL_SUBJECT" -EnvName "GRAPH_MAIL_SUBJECT"
Try-LoadSecret -Key "GRAPH_MAIL_BODY_FILE" -EnvName "GRAPH_MAIL_BODY_FILE"

Write-Host "Done. Secrets are available in current process scope only." -ForegroundColor DarkCyan
