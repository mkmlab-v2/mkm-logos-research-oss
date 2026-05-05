[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("health", "approve", "pending", "reject", "status", "taillog")]
    [string]$Action = "health",

    [Parameter(Mandatory = $false)]
    [string]$Recipient = "admin@no1kmedi.com",

    [Parameter(Mandatory = $false)]
    [string]$ApprovalSource = "ops_quick",

    [Parameter(Mandatory = $false)]
    [string]$ApprovalToken = "",

    [Parameter(Mandatory = $false)]
    [string]$WebhookUrl = "http://127.0.0.1:5678/webhook/macro-risk-mail-approval",

    [Parameter(Mandatory = $false)]
    [string]$AuditLogPath = "",

    [Parameter(Mandatory = $false)]
    [int]$TailLines = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AuditLogPath)) {
    $AuditLogPath = Join-Path (Split-Path -Parent $PSScriptRoot) "reports/macro_risk_approval_webhook_audit.jsonl"
}

function Test-N8nHealth {
    try {
        Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:5678/rest/settings" -TimeoutSec 8 | Out-Null
        Write-Output "n8n_health: PASS"
    }
    catch {
        Write-Output ("n8n_health: FAIL - " + $_.Exception.Message)
        exit 1
    }
}

function Invoke-Approval([string]$Flag) {
    $triggerScript = Join-Path $PSScriptRoot "trigger_macro_risk_mail_approval_webhook.ps1"
    if (-not (Test-Path -LiteralPath $triggerScript)) {
        throw "Required script not found: $triggerScript"
    }

    & $triggerScript `
        -ApprovalFlag $Flag `
        -Recipient $Recipient `
        -ApprovalSource $ApprovalSource `
        -ApprovalToken $ApprovalToken `
        -WebhookUrl $WebhookUrl `
        -AuditLogPath $AuditLogPath
}

switch ($Action) {
    "health" {
        Test-N8nHealth
    }
    "approve" {
        Test-N8nHealth
        Invoke-Approval -Flag "APPROVED"
    }
    "pending" {
        Test-N8nHealth
        Invoke-Approval -Flag "PENDING"
    }
    "reject" {
        Test-N8nHealth
        Invoke-Approval -Flag "REJECTED"
    }
    "status" {
        Get-ScheduledTask -TaskName "MKM-n8n-Service" -ErrorAction SilentlyContinue |
            Select-Object TaskName, State
    }
    "taillog" {
        if (-not (Test-Path -LiteralPath $AuditLogPath)) {
            Write-Output "audit_log: NOT_FOUND"
            exit 0
        }
        Get-Content -LiteralPath $AuditLogPath -Tail $TailLines
    }
}
