param(
    [switch]$AutoApprove
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$senderScript = Join-Path $repoRoot "scripts\send_macro_risk_baseurl_confirmation_via_graph.py"

if (-not (Test-Path -LiteralPath $senderScript)) {
    throw "Sender script not found: $senderScript"
}

function Get-EnvValue([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ([string]::IsNullOrWhiteSpace($v)) { $v = [Environment]::GetEnvironmentVariable($name, "User") }
    if ([string]::IsNullOrWhiteSpace($v)) { $v = [Environment]::GetEnvironmentVariable($name, "Machine") }
    return $v
}

function Mask([string]$text) {
    if ([string]::IsNullOrWhiteSpace($text)) { return "<empty>" }
    if ($text.Length -le 6) { return "***" }
    return ($text.Substring(0, 3) + "***" + $text.Substring($text.Length - 3))
}

function Get-CurrentTotp {
    $seed = [Environment]::GetEnvironmentVariable("GRAPH_APPROVAL_OTP_SEED", "Process")
    if ([string]::IsNullOrWhiteSpace($seed)) { $seed = [Environment]::GetEnvironmentVariable("GRAPH_APPROVAL_OTP_SEED", "User") }
    if ([string]::IsNullOrWhiteSpace($seed)) { $seed = [Environment]::GetEnvironmentVariable("GRAPH_APPROVAL_OTP_SEED", "Machine") }
    if ([string]::IsNullOrWhiteSpace($seed)) {
        throw "Missing GRAPH_APPROVAL_OTP_SEED (set a private seed value in user env)."
    }

    # 5-minute TOTP window based on UTC epoch.
    $epochSeconds = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
    $step = [math]::Floor($epochSeconds / 300)
    $raw = "$seed|$step|MKM-GRAPH-MAIL"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
        $hash = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    $hex = [System.BitConverter]::ToString($hash).Replace("-", "")
    $otp = [Convert]::ToInt32($hex.Substring(0, 8), 16) % 1000000
    return $otp.ToString("000000")
}

$tenant = Get-EnvValue "GRAPH_TENANT_ID"
$client = Get-EnvValue "GRAPH_CLIENT_ID"
$secret = Get-EnvValue "GRAPH_CLIENT_SECRET"
$sender = Get-EnvValue "GRAPH_SENDER_UPN"
$recipient = Get-EnvValue "GRAPH_RECIPIENT_EMAIL"
$subject = Get-EnvValue "GRAPH_MAIL_SUBJECT"
$bodyFile = Get-EnvValue "GRAPH_MAIL_BODY_FILE"

if ([string]::IsNullOrWhiteSpace($recipient)) { $recipient = "admin@no1kmedi.com" }
if ([string]::IsNullOrWhiteSpace($subject)) { $subject = "[Action Required] Macro Risk Warning API 파일럿 Base URL 확정 요청" }
if ([string]::IsNullOrWhiteSpace($bodyFile)) { $bodyFile = "docs/final/artifacts/macro_risk_warning_api_base_url_confirmation_email_live_v1.md" }

$missing = @()
foreach ($name in @("GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET", "GRAPH_SENDER_UPN")) {
    if ([string]::IsNullOrWhiteSpace((Get-EnvValue $name))) { $missing += $name }
}
if ($missing.Count -gt 0) {
    Write-Host "[approval-gate] Missing required env vars:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Yellow }
    Write-Host "[approval-gate] Fill with scripts/set_graph_mail_env_template.ps1 then retry."
    exit 1
}

Write-Host "[approval-gate] Pending send summary"
Write-Host ("  sender    : {0}" -f $sender)
Write-Host ("  recipient : {0}" -f $recipient)
Write-Host ("  subject   : {0}" -f $subject)
Write-Host ("  tenant    : {0}" -f (Mask $tenant))
Write-Host ("  client    : {0}" -f (Mask $client))
Write-Host ("  secret    : {0}" -f (Mask $secret))
Write-Host ("  body file : {0}" -f $bodyFile)

if (-not $AutoApprove) {
    Write-Host ""
    Write-Host "Type APPROVE to send email, or anything else to cancel."
    $confirm = Read-Host "Approval"
    if ($confirm -ne "APPROVE") {
        Write-Host "[approval-gate] Cancelled by user."
        exit 0
    }

    Write-Host ""
    Write-Host "Second factor: enter current 6-digit OTP (5-minute expiry, UTC-based)."
    $otpExpected = Get-CurrentTotp
    $otpInput = Read-Host "OTP"
    if ($otpInput -ne $otpExpected) {
        Write-Host "[approval-gate] OTP mismatch. Cancelled." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "[approval-gate] Approved. Sending..."
py $senderScript
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    throw "Graph mail sender failed with exit code $rc"
}
Write-Host "[approval-gate] Done."
