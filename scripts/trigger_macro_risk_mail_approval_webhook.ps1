[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("APPROVED", "PENDING", "REJECTED")]
    [string]$ApprovalFlag = "APPROVED",

    [Parameter(Mandatory = $false)]
    [string]$Recipient = "admin@no1kmedi.com",

    [Parameter(Mandatory = $false)]
    [string]$ApprovalSource = "ops_manual",

    [Parameter(Mandatory = $false)]
    [string]$WebhookUrl = "http://127.0.0.1:5678/webhook/macro-risk-mail-approval",

    [Parameter(Mandatory = $false)]
    [string]$ApprovalToken = "",

    [Parameter(Mandatory = $false)]
    [string]$AuditLogPath = "reports/macro_risk_approval_webhook_audit.jsonl"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dot = Join-Path $repoRoot ".env"
if (Test-Path -LiteralPath $dot) {
    foreach ($raw in Get-Content -LiteralPath $dot -Encoding utf8) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { continue }
        $k = $line.Substring(0, $eq).Trim()
        if ($k -ne "MKM_MACRO_RISK_APPROVAL_TOKEN") { continue }
        $v = $line.Substring($eq + 1).Trim()
        if ($v.Length -ge 2 -and (
                ($v.StartsWith([char]34) -and $v.EndsWith([char]34)) -or
                ($v.StartsWith([char]39) -and $v.EndsWith([char]39)))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        if ([string]::IsNullOrWhiteSpace($v)) { continue }
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MKM_MACRO_RISK_APPROVAL_TOKEN", "Process"))) {
            [Environment]::SetEnvironmentVariable("MKM_MACRO_RISK_APPROVAL_TOKEN", $v, "Process")
        }
        break
    }
}

if ([string]::IsNullOrWhiteSpace($ApprovalToken)) {
    $ApprovalToken = [Environment]::GetEnvironmentVariable("MKM_MACRO_RISK_APPROVAL_TOKEN", "Process")
}
if ([string]::IsNullOrWhiteSpace($ApprovalToken)) {
    $ApprovalToken = [Environment]::GetEnvironmentVariable("MKM_MACRO_RISK_APPROVAL_TOKEN", "User")
}
if ([string]::IsNullOrWhiteSpace($ApprovalToken)) {
    $ApprovalToken = [Environment]::GetEnvironmentVariable("MKM_MACRO_RISK_APPROVAL_TOKEN", "Machine")
}

if (-not [System.IO.Path]::IsPathRooted($AuditLogPath)) {
    $AuditLogPath = Join-Path $repoRoot $AuditLogPath
}

$payload = @{
    approval_flag   = $ApprovalFlag
    approval_source = $ApprovalSource
    recipient       = $Recipient
}

$json = $payload | ConvertTo-Json -Depth 5
$headers = @{}
if (-not [string]::IsNullOrWhiteSpace($ApprovalToken)) {
    $headers["x-mkm-approval-token"] = $ApprovalToken
}

$response = Invoke-RestMethod -Method Post -Uri $WebhookUrl -ContentType "application/json" -Headers $headers -Body $json

$auditDir = Split-Path -Parent $AuditLogPath
if (-not [string]::IsNullOrWhiteSpace($auditDir) -and -not (Test-Path -LiteralPath $auditDir)) {
    New-Item -ItemType Directory -Path $auditDir -Force | Out-Null
}

$auditEntry = @{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    event = "macro_risk_approval_webhook_call"
    webhook_url = $WebhookUrl
    approval_flag = $ApprovalFlag
    approval_source = $ApprovalSource
    recipient = $Recipient
    token_header_set = (-not [string]::IsNullOrWhiteSpace($ApprovalToken))
    response = $response
} | ConvertTo-Json -Depth 8 -Compress

Add-Content -LiteralPath $AuditLogPath -Value $auditEntry -Encoding UTF8

Write-Output ("macro_risk_approval_webhook: PASS")
Write-Output ("approval_flag={0}" -f $ApprovalFlag)
Write-Output ("recipient={0}" -f $Recipient)
Write-Output ("response={0}" -f (($response | ConvertTo-Json -Depth 5 -Compress)))
Write-Output ("audit_log_path={0}" -f $AuditLogPath)
