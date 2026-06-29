#Requires -Version 5.1
<#
.SYNOPSIS
  Live Azure GPU quota probe for Nemotron 30B QLoRA (NC T4 / A100 families).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureNemotronGpuFeasibility_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string[]]$Regions = @("eastus2", "koreacentral", "westus3", "southcentralus"),
    [string]$OutJson = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "reports\azure_gpu_feasibility_v1_latest.json")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-DotEnvKey {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match "^\s*$Key=(.+)\s*$") { return $matches[1].Trim().Trim('"').Trim("'") }
    }
    return $null
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI (az) not found. Install: https://aka.ms/installazurecliwindows"
}

$sub = & az account show -o json 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "az not logged in — run: az login --use-device-code" }
$acct = $sub | ConvertFrom-Json

$gpuFamilies = @(
    "Standard NCASv3_T4 Family vCPUs",
    "Standard NCADS_A100_v4 Family vCPUs",
    "Standard NCadsH100v5 Family vCPUs"
)

$regionSamples = @()
$bestRegion = $null
$bestT4Limit = 0

foreach ($region in $Regions) {
    $usageJson = & az vm list-usage --location $region -o json 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { continue }
    $usage = $usageJson | ConvertFrom-Json
    foreach ($fam in $gpuFamilies) {
        $row = $usage | Where-Object { $_.localName -eq $fam } | Select-Object -First 1
        if (-not $row) { continue }
        $sample = [ordered]@{
            region  = $region
            family  = $fam
            current = [int]$row.currentValue
            limit   = [int]$row.limit
        }
        $regionSamples += $sample
        if ($fam -eq "Standard NCASv3_T4 Family vCPUs" -and [int]$row.limit -gt $bestT4Limit) {
            $bestT4Limit = [int]$row.limit
            $bestRegion = $region
        }
    }
}

$t4OkForNc8 = ($bestT4Limit -ge 8)
$t4OkForNc4 = ($bestT4Limit -ge 4)
$feasible = $t4OkForNc8 -or ($regionSamples | Where-Object { $_.family -eq "Standard NCADS_A100_v4 Family vCPUs" -and $_.limit -ge 24 })

$envPath = Join-Path $RepoRoot ".env"
$creditsUsd = Read-DotEnvKey -Path $envPath -Key "AZURE_STARTUP_CREDITS_USD_REMAINING"
$creditsExpire = Read-DotEnvKey -Path $envPath -Key "AZURE_STARTUP_CREDITS_EXPIRE"

$quotaTicketPath = Join-Path $RepoRoot "reports\azure_gpu_quota_request_latest.json"
$ticketId = "2606030030000175"
if (Test-Path -LiteralPath $quotaTicketPath) {
    try {
        $qt = Get-Content -LiteralPath $quotaTicketPath -Raw | ConvertFrom-Json
        if ($qt.portal_support_ticket.id) { $ticketId = $qt.portal_support_ticket.id }
    }
    catch { }
}

$blocker = if (-not $feasible) {
    "GPU VM quota limit=0 (or <8 vCPU NC T4). Cannot create NC8as_T4_v3 (2x T4, 56GB RAM) until Microsoft approves support ticket $ticketId."
}
else {
    $null
}

$doc = [ordered]@{
    schema                  = "azure_gpu_feasibility_v1"
    checked_at_utc          = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    subscription_id         = $acct.id
    subscription_name       = $acct.name
    account_email           = $acct.user.name
    credits                 = [ordered]@{
        usd_remaining_env = $creditsUsd
        expire            = $creditsExpire
        note              = "Startup credits bill GPU VMs once quota > 0"
    }
    gpu_vm_feasible_now     = [bool]$feasible
    gpu_vm_blocker          = $blocker
    recommended_vm_size     = "Standard_NC8as_T4_v3"
    recommended_vm_note     = "2x T4 32GB VRAM + 56GB RAM — fits Nemotron 30B 4bit; needs NCASv3_T4 quota >= 8 vCPU"
    minimum_vm_size         = "Standard_NC4as_T4_v3"
    minimum_vm_warning      = "1×T4 16GB — likely OOM for 30B QLoRA; request 8 vCPU not 4"
    best_t4_region          = $bestRegion
    best_t4_limit           = $bestT4Limit
    regions_probed          = $Regions
    gpu_quota_samples       = $regionSamples
    support_ticket_id       = $ticketId
    portal_actions          = @(
        "Portal → Help + support → ticket $ticketId → reply: request Standard NCASv3_T4 8 vCPU in eastus2 for NC8as_T4_v3 (Nemotron fine-tune)",
        "After approval: pwsh scripts/Invoke-AzureNemotronGpuSmoke_v1.ps1",
        "Quota UI: https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/myQuotas"
    )
    mkm_interpretation      = [ordered]@{
        pay_with_startup_credits = $true
        can_run_gpu_workload_today = [bool]$feasible
        kaggle_deprioritized     = "Azure path preferred; Kaggle blocked by session RAM/disk"
    }
}

$json = $doc | ConvertTo-Json -Depth 8
Set-Content -LiteralPath $OutJson -Value $json -Encoding utf8
Write-Host "[OK] $OutJson"
Write-Host "gpu_vm_feasible_now=$($doc.gpu_vm_feasible_now) best_t4_limit=$bestT4Limit region=$bestRegion"
if (-not $feasible) {
    Write-Host "[BLOCKED] $blocker" -ForegroundColor Yellow
    exit 2
}
exit 0
