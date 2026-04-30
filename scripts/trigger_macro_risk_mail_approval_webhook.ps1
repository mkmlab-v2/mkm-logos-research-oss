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
