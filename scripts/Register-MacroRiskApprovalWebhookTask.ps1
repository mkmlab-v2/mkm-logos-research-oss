[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$TaskName = "MKM-MacroRisk-Approval-Webhook",

    [Parameter(Mandatory = $false)]
    [ValidateSet("APPROVED", "PENDING", "REJECTED")]
    [string]$ApprovalFlag = "APPROVED",

    [Parameter(Mandatory = $false)]
    [string]$Recipient = "admin@no1kmedi.com",

    [Parameter(Mandatory = $false)]
    [string]$ApprovalSource = "ops_scheduler",

    [Parameter(Mandatory = $false)]
    [string]$ApprovalToken = "",

    [Parameter(Mandatory = $false)]
    [string]$WebhookUrl = "http://127.0.0.1:5678/webhook/macro-risk-mail-approval",

    [Parameter(Mandatory = $false)]
    [int]$IntervalMinutes = 60,

    [switch]$Remove
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$scriptPath = Join-Path $PSScriptRoot "trigger_macro_risk_mail_approval_webhook.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Required script not found: $scriptPath"
}

$argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`"",
    "-ApprovalFlag", $ApprovalFlag,
    "-Recipient", "`"$Recipient`"",
    "-ApprovalSource", "`"$ApprovalSource`"",
    "-WebhookUrl", "`"$WebhookUrl`""
)
if (-not [string]::IsNullOrWhiteSpace($ApprovalToken)) {
    $argList += @("-ApprovalToken", "`"$ApprovalToken`"")
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argList -join " ")
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "interval_minutes=$IntervalMinutes"
