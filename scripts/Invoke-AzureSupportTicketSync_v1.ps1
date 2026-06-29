#Requires -Version 5.1
<#
.SYNOPSIS
  Fetch Azure support ticket status + communications via CLI (portal ReactView bypass).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureSupportTicketSync_v1.ps1
#>
param(
    [string]$SubscriptionId = "d2ccdc4f-531a-42dd-b05e-edea4961acf0",
    [string]$TicketArmName = "06bfd9d3-e12e3d1d-a8890897-5836-499a-9d5c-c58dc2225020",
    [string]$SupportTicketId = "2606030030000175",
    [string]$OutJson = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "reports\azure_support_ticket_status_latest.json")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI (az) not found."
}

& az account set --subscription $SubscriptionId | Out-Null
if ($LASTEXITCODE -ne 0) { throw "az account set failed" }

$ticketJson = & az support in-subscription tickets show --ticket-name $TicketArmName -o json 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "tickets show failed: $ticketJson" }
$ticket = $ticketJson | ConvertFrom-Json

$commsPath = Join-Path $env:TEMP "azure_support_comms_$TicketArmName.json"
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
cmd /c "chcp 65001>nul && az support in-subscription communication list --ticket-name $TicketArmName -o json > `"$commsPath`" 2>nul"
$commExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($commExit -ne 0 -or -not (Test-Path -LiteralPath $commsPath)) {
    throw "communication list failed (exit=$commExit path=$commsPath)"
}
$commsJson = Get-Content -LiteralPath $commsPath -Raw -Encoding UTF8
$comms = $commsJson | ConvertFrom-Json

$rejectionPhrases = @(
    "unable to approve",
    "we are unable to approve",
    "cannot approve",
    "not able to approve"
)
$appealPhrases = @("pay-as-you-go", "alternative", "VM Types", "free/benefit")

$parsed = @()
$rejected = $false
$latestOutbound = $null
foreach ($c in ($comms | Sort-Object { [datetime]$_.createdDate } -Descending)) {
    $plain = ($c.body -replace '<[^>]+>', ' ' -replace '\s+', ' ').Trim()
    $isRejection = $false
    foreach ($p in $rejectionPhrases) {
        if ($plain -match [regex]::Escape($p)) { $isRejection = $true; $rejected = $true; break }
    }
    if ($c.communicationDirection -eq "Outbound" -and -not $latestOutbound) {
        $latestOutbound = [ordered]@{
            createdDate = $c.createdDate
            sender      = $c.sender
            subject     = $c.subject
            is_rejection = $isRejection
            excerpt     = if ($plain.Length -gt 500) { $plain.Substring(0, 500) + "..." } else { $plain }
        }
    }
    $parsed += [ordered]@{
        createdDate = $c.createdDate
        direction   = $c.communicationDirection
        sender      = $c.sender
        subject     = $c.subject
        is_rejection = $isRejection
    }
}

$quotaUsage = & az vm list-usage --location eastus2 -o json 2>&1 | Out-String
$t4Limit = 0
if ($LASTEXITCODE -eq 0) {
    $usage = $quotaUsage | ConvertFrom-Json
    $row = $usage | Where-Object { $_.localName -eq "Standard NCASv3_T4 Family vCPUs" } | Select-Object -First 1
    if ($row) { $t4Limit = [int]$row.limit }
}

$appealBody = @"
Hello Daniel,

Thank you for the update on ticket $SupportTicketId.

We understand GPU capacity is limited on benefit/sponsorship subscriptions. This subscription (MKM-Startups-Prod, $SubscriptionId) is a Microsoft for Startups sponsorship account with approximately USD 1000 credits (valid until 2026-08-18). We intend to pay from those credits, not from a free tier.

Use case (research only, single short smoke):
- One VM: Standard_NC8as_T4_v3 in eastus2 (8 vCPU / 2x T4, 32GB VRAM)
- Purpose: Nemotron 30B QLoRA fine-tuning smoke test (~1-2 hours), then deallocate/delete
- No production workload

Request:
1) Please escalate to Azure Capacity for sponsorship/Startups GPU quota in eastus2, OR
2) Tell us which GPU VM family/size IS approvable on this subscription type in eastus2 or koreacentral.

If NCasT4v3 cannot be approved on sponsorship, we will consider a separate pay-as-you-go subscription only if you confirm that is the only path.

Thank you,
Giryun Lee
giryun288@gmail.com
"@

$portalResourceUrl = "https://portal.azure.com/#resource/subscriptions/$SubscriptionId/providers/microsoft.support/supporttickets/$TicketArmName"
$portalListUrl = "https://portal.azure.com/#view/Microsoft_Azure_Support/HelpAndSupportBlade/overview"

$customerAppealSent = $false
if ($latestOutbound -and $latestOutbound.sender -notmatch 'supportmail|microsoft\.com') {
    $customerAppealSent = -not $latestOutbound.is_rejection
}

$out = [ordered]@{
    schema              = "azure_support_ticket_status_v1"
    checked_at_utc      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    subscription_id     = $SubscriptionId
    support_ticket_id   = $SupportTicketId
    ticket_arm_name     = $TicketArmName
    status              = $ticket.status
    engineer_email      = $ticket.supportEngineer.emailAddress
    modified_date       = $ticket.modifiedDate
    ms_rejection_detected = $rejected
    ncas_t4_limit_eastus2 = $t4Limit
    latest_outbound     = $latestOutbound
    communications      = $parsed
    cli_reply_blocked   = "InvalidSupportPlan: Free — use portal thread only"
    portal_urls         = [ordered]@{
        resource_blade = $portalResourceUrl
        help_overview    = $portalListUrl
    }
    appeal_reply_paste  = $appealBody
    customer_appeal_sent = $customerAppealSent
    next_actions        = @(
        if ($customerAppealSent) {
            "Customer appeal submitted — await MS capacity response (re-run this sync daily)"
        } elseif ($rejected) {
            "MS initially rejected GPU on sponsorship — paste appeal_reply_paste in portal ticket thread (Help + support)"
        } else {
            "Monitor ticket; quota still 0 until approved"
        }
        "Portal ReactView may fail — use portal_urls.resource_blade or Help + support list"
        "After quota>0: Invoke-AzureNemotronGpuFeasibility_v1.ps1 then Invoke-AzureNemotronGpuSmoke_v1.ps1"
        "Parallel fallback: NVIDIA Brev / pay-as-you-go sub if MS confirms only path"
    )
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$out | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutJson -Encoding UTF8

Write-Host "ticket=$SupportTicketId status=$($ticket.status) rejection=$rejected t4_limit=$t4Limit"
Write-Host "wrote: $OutJson"
if ($customerAppealSent) {
    Write-Host "ACTION: appeal already on thread — await MS reply; re-sync daily" -ForegroundColor Cyan
} elseif ($rejected) {
    Write-Host "ACTION: paste appeal from appeal_reply_paste via portal (CLI reply blocked)" -ForegroundColor Yellow
}
