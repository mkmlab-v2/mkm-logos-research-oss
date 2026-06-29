#Requires -Version 5.1
<#
.SYNOPSIS
  Provision Azure NC GPU VM (startup credits) and run Nemotron 30B QLoRA smoke.

  Prerequisite: NCASv3_T4 quota >= 8 vCPU (NC8as_T4_v3 = 2x T4, 56GB RAM).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureNemotronGpuSmoke_v1.ps1 -WhatIfOnly

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureNemotronGpuSmoke_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ResourceGroup = "mkm-nemotron-gpu-rg",
    [string]$Location = "eastus2",
    [string]$VmName = "mkm-nemotron-nc8",
    [string]$VmSize = "Standard_NC8as_T4_v3",
    [string]$AdminUser = "azureuser",
    [int]$OsDiskGb = 256,
    [switch]$WhatIfOnly,
    [switch]$SkipSmoke,
    [switch]$UseExistingVm
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

$feasScript = Join-Path $PSScriptRoot "Invoke-AzureNemotronGpuFeasibility_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $feasScript -Regions @($Location, "koreacentral") 2>&1 | Out-Host
$quotaOk = ($LASTEXITCODE -eq 0)
if (-not $quotaOk -and -not $WhatIfOnly) {
    Write-Host ""
    Write-Host "=== Azure GPU blocked (quota). 지휘관 액션 ===" -ForegroundColor Cyan
    Write-Host "1. Portal > Help + support > incident 2606030030000175"
    Write-Host "2. Reply in portal thread: eastus2, Standard NCASv3_T4, 8 vCPU, NC8as_T4_v3, Nemotron QLoRA smoke"
    Write-Host "3. Re-run this script after approval"
    Write-Host ""
    Write-Host "Startup credits OK - GPU quota is 0 so az vm create is rejected until MS approves."
    exit 2
}

$envPath = Join-Path $RepoRoot ".env"
$hfToken = Read-DotEnvKey -Path $envPath -Key "HF_TOKEN"
if (-not $hfToken -and -not $WhatIfOnly) {
    throw "HF_TOKEN missing in .env - required for Nemotron hub download"
}

$sshKey = Join-Path (Join-Path $env:USERPROFILE ".ssh") "mkm_azure_nemotron"
$sshPub = "$sshKey.pub"
if (-not (Test-Path -LiteralPath $sshPub)) {
    if ($WhatIfOnly) {
        Write-Host "[whatif] would generate SSH key $sshKey"
    }
    else {
        New-Item -ItemType Directory -Force -Path (Split-Path $sshKey) | Out-Null
        & ssh-keygen -t ed25519 -f $sshKey -N '""' -C "mkm-nemotron-azure"
    }
}

$plan = [ordered]@{
    resource_group = $ResourceGroup
    location       = $Location
    vm_name        = $VmName
    vm_size        = $VmSize
    image          = "microsoft-dsvm:ubuntu-hpc:2204:latest"
    os_disk_gb     = $OsDiskGb
    smoke_script   = "bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh"
    est_usd        = "~USD 3-15 smoke (NC8 T4 x few hours, credits)"
}

Write-Host ($plan | ConvertTo-Json -Depth 4)
if ($WhatIfOnly) { exit 0 }

if (-not $UseExistingVm) {
    $rgExists = & az group exists --name $ResourceGroup 2>&1
    if ($rgExists -eq "false") {
        Write-Host "[azure] creating RG $ResourceGroup ($Location)..."
        & az group create --name $ResourceGroup --location $Location --tags project=mkm lane=research_only | Out-Null
    }

    $vmExists = & az vm show --resource-group $ResourceGroup --name $VmName --query id -o tsv 2>$null
    if (-not $vmExists) {
        Write-Host "[azure] creating VM $VmName ($VmSize) - first time ~5-10 min..."
        & az vm create `
            --resource-group $ResourceGroup `
            --name $VmName `
            --location $Location `
            --size $VmSize `
            --image "microsoft-dsvm:ubuntu-hpc:2204:latest" `
            --admin-username $AdminUser `
            --ssh-key-values "@$sshPub" `
            --os-disk-size-gb $OsDiskGb `
            --storage-sku Premium_LRS `
            --public-ip-sku Standard `
            --tags project=mkm lane=research_only purpose=nemotron_qlora_smoke
        if ($LASTEXITCODE -ne 0) {
            throw "az vm create failed - check quota ticket or try -Location koreacentral"
        }
    }
    else {
        Write-Host "[azure] VM already exists: $VmName"
    }
}

$ip = & az vm show -d --resource-group $ResourceGroup --name $VmName --query publicIps -o tsv
if (-not $ip) { throw "VM has no public IP" }
Write-Host "[azure] VM IP: $ip"

if ($SkipSmoke) {
    Write-Host "[OK] VM ready. SSH: ssh -i $sshKey ${AdminUser}@${ip}"
    exit 0
}

Write-Host "[azure] syncing repo (scp) - may take several minutes..."
$sshArgs = @("-i", $sshKey, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL")
$remoteDir = "/home/$AdminUser/mkm-workspace"

& ssh @sshArgs "${AdminUser}@${ip}" "mkdir -p $remoteDir"
$tarList = @(
    "data/kaggle/nvidia-nemotron-model-reasoning-challenge",
    "scripts/run_nemotron_cloud_gpu_smoke_v1.sh",
    "scripts/run_nemotron_cloud_bootstrap_v1.sh",
    "scripts/run_nemotron_wsl_install_mamba_v1.sh"
)
$staging = Join-Path $env:TEMP "mkm_azure_nemotron_upload"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
foreach ($rel in $tarList) {
    $src = Join-Path $RepoRoot $rel
    if (-not (Test-Path $src)) { throw "missing upload path: $rel" }
    $dest = Join-Path $staging $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item -Recurse -Force $src $dest
}
$tarFile = Join-Path $env:TEMP "mkm_nemotron_upload.tar.gz"
if (Test-Path $tarFile) { Remove-Item -Force $tarFile }
Push-Location $staging
& tar -czf $tarFile .
Pop-Location
& scp @sshArgs $tarFile "${AdminUser}@${ip}:/tmp/mkm_nemotron_upload.tar.gz"
$untarCmd = "cd $remoteDir; tar -xzf /tmp/mkm_nemotron_upload.tar.gz; rm -f /tmp/mkm_nemotron_upload.tar.gz"
& ssh @sshArgs "${AdminUser}@${ip}" $untarCmd

$remoteCmd = "set -euo pipefail; cd $remoteDir; export HF_TOKEN='$hfToken'; export PYTHONUNBUFFERED=1; bash scripts/run_nemotron_cloud_bootstrap_v1.sh; bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh"

Write-Host "[azure] running smoke on VM (download ~63GB + train, allow 2-4h)..."
& ssh @sshArgs "${AdminUser}@${ip}" $remoteCmd
$sshExit = $LASTEXITCODE

Write-Host "[azure] pulling report..."
$reportLocal = Join-Path $RepoRoot "reports\kaggle_nemotron_kaggle_train_latest.json"
& scp @sshArgs "${AdminUser}@${ip}:$remoteDir/reports/kaggle_nemotron_kaggle_train_latest.json" $reportLocal 2>$null

Write-Host ""
Write-Host "=== VM stop reminder ===" -ForegroundColor Yellow
Write-Host "Credits burn while VM runs: az vm deallocate --resource-group $ResourceGroup --name $VmName"
Write-Host "Delete when done: az group delete --name $ResourceGroup --yes --no-wait"

exit $sshExit
