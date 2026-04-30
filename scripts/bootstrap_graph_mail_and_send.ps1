param(
    [switch]$SkipSend
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ([string]::IsNullOrWhiteSpace($v)) { $v = [Environment]::GetEnvironmentVariable($name, "User") }
    if ([string]::IsNullOrWhiteSpace($v)) { $v = [Environment]::GetEnvironmentVariable($name, "Machine") }
    return $v
}

function Ensure-Value([string]$name, [string]$prompt, [switch]$Secret) {
    $cur = Get-EnvAny $name
    if (-not [string]::IsNullOrWhiteSpace($cur)) { return $cur }
    if ($Secret) {
        $secure = Read-Host -Prompt $prompt -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    return (Read-Host -Prompt $prompt)
}

$tenant = Ensure-Value "GRAPH_TENANT_ID" "Enter GRAPH_TENANT_ID"
$client = Ensure-Value "GRAPH_CLIENT_ID" "Enter GRAPH_CLIENT_ID"
$secret = Ensure-Value "GRAPH_CLIENT_SECRET" "Enter GRAPH_CLIENT_SECRET" -Secret
$sender = Ensure-Value "GRAPH_SENDER_UPN" "Enter GRAPH_SENDER_UPN (sender mailbox)"
$otpSeed = Ensure-Value "GRAPH_APPROVAL_OTP_SEED" "Enter GRAPH_APPROVAL_OTP_SEED (private seed)"

[Environment]::SetEnvironmentVariable("GRAPH_TENANT_ID", $tenant, "User")
[Environment]::SetEnvironmentVariable("GRAPH_CLIENT_ID", $client, "User")
[Environment]::SetEnvironmentVariable("GRAPH_CLIENT_SECRET", $secret, "User")
[Environment]::SetEnvironmentVariable("GRAPH_SENDER_UPN", $sender, "User")
[Environment]::SetEnvironmentVariable("GRAPH_APPROVAL_OTP_SEED", $otpSeed, "User")
[Environment]::SetEnvironmentVariable("GRAPH_RECIPIENT_EMAIL", "admin@no1kmedi.com", "User")
[Environment]::SetEnvironmentVariable("GRAPH_MAIL_SUBJECT", "[Action Required] Macro Risk Warning API 파일럿 Base URL 확정 요청", "User")
[Environment]::SetEnvironmentVariable("GRAPH_MAIL_BODY_FILE", "docs/final/artifacts/macro_risk_warning_api_base_url_confirmation_email_live_v1.md", "User")

Write-Host "[bootstrap] Graph mail env set at User scope."
if ($SkipSend) {
    Write-Host "[bootstrap] SkipSend set. Done."
    exit 0
}

$approvalScript = Join-Path $repoRoot "scripts\run_macro_risk_graph_mail_with_approval.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $approvalScript
