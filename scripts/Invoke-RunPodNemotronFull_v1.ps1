#Requires -Version 5.1
<#
.SYNOPSIS
  RunPod path for Nemotron 30B QLoRA full train (research_only): pack + handoff + optional SSH.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-RunPodNemotronFull_v1.ps1
  powershell ... -FullLimit 4096 -PodSsh "root@host -p port"
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$FullLimit = 2048,
    [int]$FullMaxSteps = 0,
    [double]$FullEpochs = 1,
    [string]$PodSsh = "",
    [switch]$SkipPack
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-EnvKey {
    param([string]$Key)
    if ([Environment]::GetEnvironmentVariable($Key)) { return $true }
    $envPath = Join-Path $RepoRoot ".env"
    if (-not (Test-Path -LiteralPath $envPath)) { return $false }
    return [bool](Select-String -Path $envPath -Pattern "^\s*$Key=.+" -Quiet)
}

$packScript = Join-Path $PSScriptRoot "Invoke-RunPodNemotronSmokePack_v1.ps1"
if (-not $SkipPack) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $packScript -RepoRoot $RepoRoot
    if ($LASTEXITCODE -ne 0) { throw "pack failed exit=$LASTEXITCODE" }
}

$zipPath = Join-Path $RepoRoot "reports\runpod_nemotron_smoke_bundle_v1.zip"
$hfOk = Test-EnvKey -Key "HF_TOKEN"
$estSteps = if ($FullMaxSteps -gt 0) { $FullMaxSteps } else { [math]::Ceiling($FullLimit / 8.0) }
$estHours = [math]::Round($estSteps * 49 / 3600, 1)

$handoff = [ordered]@{
    schema           = "runpod_nemotron_full_handoff_v1"
    lane             = "research_only"
    checked_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hf_token_present = $hfOk
    train_profile    = [ordered]@{
        mode       = "full_no_smoke"
        full_limit = $FullLimit
        epochs     = $FullEpochs
        max_steps  = $FullMaxSteps
        est_steps  = $estSteps
        est_hours  = $estHours
        note       = "limit=0 uses all ~69k rows (days on 1xL40S); default 2048 is research full"
    }
    recommended_gpu  = @(
        @{ provider = "RunPod"; sku = "L40S 48GB"; usd_per_hr = "0.86"; fit = "recommended" }
    )
    pod_settings     = [ordered]@{
        name         = "mkm-nemotron-full"
        template     = "RunPod PyTorch 2.x (CUDA 12.x)"
        volume_gb    = 80
        mount_path   = "/workspace"
        env          = @("HF_TOKEN")
    }
    bundle_zip       = $zipPath
    pod_commands     = @(
        "cd /workspace",
        "export HF_TOKEN='(RunPod pod env)'",
        "export MKM_NEMOTRON_CLOUD_FULL_LIMIT=$FullLimit",
        "export MKM_NEMOTRON_CLOUD_FULL_EPOCHS=$FullEpochs",
        "export MKM_NEMOTRON_CLOUD_FULL_MAX_STEPS=$FullMaxSteps",
        "bash scripts/runpod/runpod_nemotron_full_all_in_one_v1.sh"
    )
    pull_artifacts   = @(
        "reports/kaggle_nemotron_kaggle_train_full_latest.json",
        "reports/nemotron_cloud_gpu_full_latest.log",
        "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/output/",
        "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/submission.zip"
    )
    est_cost_usd     = @{ low = 5; high = 15; note = "incl HF download 1st run; ~$estHours h SFT @0.86/hr" }
    forbidden        = @("Track A promotion", "competition submit", "MKM core auto-wire")
}

$outJson = Join-Path $RepoRoot "reports\runpod_nemotron_full_handoff_v1_latest.json"
$handoff | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outJson -Encoding UTF8

Write-Host ""
Write-Host "=== RunPod Nemotron 30B FULL train [HYPO] ===" -ForegroundColor Cyan
Write-Host "Profile: limit=$FullLimit epochs=$FullEpochs max_steps=$FullMaxSteps (~$estSteps steps, ~${estHours}h SFT)"
Write-Host "HF_TOKEN in .env: $(if ($hfOk) { 'yes' } else { 'MISSING' })" -ForegroundColor $(if ($hfOk) { 'Green' } else { 'Yellow' })
Write-Host "Bundle: $zipPath"
Write-Host "Handoff: $outJson"
Write-Host ""
Write-Host "Pod terminal one-liner:" -ForegroundColor Yellow
Write-Host "  export MKM_NEMOTRON_CLOUD_FULL_LIMIT=$FullLimit MKM_NEMOTRON_CLOUD_FULL_EPOCHS=$FullEpochs MKM_NEMOTRON_CLOUD_FULL_MAX_STEPS=$FullMaxSteps"
Write-Host "  bash scripts/runpod/runpod_nemotron_full_all_in_one_v1.sh"

if ($PodSsh) {
    $remote = @(
        "cd /workspace",
        "export MKM_NEMOTRON_CLOUD_FULL_LIMIT=$FullLimit",
        "export MKM_NEMOTRON_CLOUD_FULL_EPOCHS=$FullEpochs",
        "export MKM_NEMOTRON_CLOUD_FULL_MAX_STEPS=$FullMaxSteps",
        "bash scripts/runpod/runpod_nemotron_full_all_in_one_v1.sh"
    ) -join " && "
    ssh $PodSsh $remote
    exit $LASTEXITCODE
}

if (-not $hfOk) { exit 2 }
