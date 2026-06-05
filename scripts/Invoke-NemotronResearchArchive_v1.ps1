#Requires -Version 5.1
<#
.SYNOPSIS
  Archive Nemotron research-only train artifacts to MKM_DATA_VAULT (HOLD lane closure).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NemotronResearchArchive_v1.ps1
  powershell ... -WhatIfOnly
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$VaultTargetRoot = "",
    [switch]$WhatIfOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VaultTargetRoot)) {
    $vaultBase = Get-ChildItem -Path "G:\" -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "vault" -and $_.FullName -match "MKM_DATA_VAULT" } |
        Select-Object -First 1
    if (-not $vaultBase) {
        throw "MKM_DATA_VAULT\vault not found on G: — mount Vault or pass -VaultTargetRoot"
    }
    $VaultTargetRoot = Join-Path $vaultBase.FullName "btrack_artifacts_verified\nemotron_research_2048_v1"
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$destRoot = Join-Path $VaultTargetRoot $stamp

if (-not $WhatIfOnly) {
    New-Item -ItemType Directory -Path $destRoot -Force | Out-Null
}

$relPaths = @(
    "reports/kaggle_nemotron_kaggle_train_full_latest.json",
    "reports/nemotron_cloud_gpu_full_latest.log",
    "reports/kaggle_nemotron_resume_latest.json",
    "reports/runpod_nemotron_full_handoff_v1_latest.json",
    "reports/wsl_nemotron_sandbox_handoff_v1_latest.json",
    "reports/nemotron_pulled_adapter_verify_v1_latest.json",
    "reports/nvidia_api_primary_lane_v1_latest.json",
    "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/submission.zip",
    "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/output"
)

$copied = @()
$missing = @()

foreach ($rel in $relPaths) {
    $src = Join-Path $RepoRoot ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $src)) {
        $missing += $rel
        continue
    }
    $dst = Join-Path $destRoot ($rel -replace '/', '\')
    $dstParent = Split-Path -Parent $dst
    if ($WhatIfOnly) {
        Write-Host "[whatif] copy $rel -> $dst"
        $copied += $rel
        continue
    }
    if (-not (Test-Path -LiteralPath $dstParent)) {
        New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
    }
    if (Test-Path -LiteralPath $src -PathType Container) {
        Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
    } else {
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
    $copied += $rel
}

$summary = [ordered]@{
    schema           = "nemotron_research_archive_v1"
    lane             = "research_only"
    expansion_stance = "HOLD"
    executed_at_utc  = (Get-Date).ToUniversalTime().ToString("o")
    repo_root        = $RepoRoot
    vault_dest       = $destRoot
    copied_count     = $copied.Count
    copied           = $copied
    missing_count    = $missing.Count
    missing          = $missing
    train_fact_lock  = [ordered]@{
        rows                 = 2048
        train_loss           = 9.584
        mean_token_accuracy  = 0.7223
        allow_competition_submit = $false
    }
}

if (-not $WhatIfOnly) {
    $summaryPath = Join-Path $destRoot "_archive_manifest.json"
    ($summary | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    $latestLink = Join-Path $VaultTargetRoot "_archive_latest_manifest.json"
    Copy-Item -LiteralPath $summaryPath -Destination $latestLink -Force
}

$localReport = Join-Path $RepoRoot "reports\nemotron_research_archive_v1_latest.json"
if (-not $WhatIfOnly) {
    ($summary | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $localReport -Encoding UTF8
}

Write-Host "[OK] Nemotron archive copied=$($copied.Count) missing=$($missing.Count)"
Write-Host "Vault: $destRoot"
if (-not $WhatIfOnly) { Write-Host "Local report: $localReport" }
if ($missing.Count -gt 0) { exit 2 }
exit 0
