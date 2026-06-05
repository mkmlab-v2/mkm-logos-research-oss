#Requires -Version 5.1
<#
.SYNOPSIS
  RunPod path for Nemotron 30B QLoRA smoke: pack bundle + handoff JSON + optional SSH run.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-RunPodNemotronSmoke_v1.ps1
  powershell ... -File scripts\Invoke-RunPodNemotronSmoke_v1.ps1 -PodSsh "root@1.2.3.4 -p 12345"
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
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

$handoff = [ordered]@{
    schema           = "runpod_nemotron_smoke_handoff_v1"
    lane             = "research_only"
    checked_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hf_token_present = $hfOk
    recommended_gpu  = @(
        @{ provider = "RunPod"; sku = "L40S 48GB"; usd_per_hr = "0.40-0.86"; fit = "recommended" }
        @{ provider = "RunPod"; sku = "A100 40GB"; usd_per_hr = "0.59-1.49"; fit = "recommended" }
    )
    pod_settings     = [ordered]@{
        template     = "RunPod PyTorch 2.x (CUDA 12.x)"
        volume_gb    = 80
        mount_path   = "/workspace"
        env          = @("HF_TOKEN")
    }
    bundle_zip       = $zipPath
    bundle_dir       = Join-Path $RepoRoot "reports\runpod_nemotron_smoke_bundle"
    upload_options   = @(
        "A) RunPod Web Terminal: upload zip → unzip -o runpod_nemotron_smoke_bundle_v1.zip -d /workspace"
        "B) git clone gitea (full repo) if faster for you → skip zip"
        "C) scp zip to pod then unzip"
    )
    pod_commands     = @(
        "cd /workspace",
        "export HF_TOKEN='(RunPod pod env / secrets — do not paste in chat)'",
        "bash scripts/runpod/runpod_nemotron_smoke_all_in_one_v1.sh"
    )
    pull_artifacts   = @(
        "reports/kaggle_nemotron_kaggle_train_latest.json",
        "reports/nemotron_cloud_gpu_smoke_latest.log",
        "data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/output/"
    )
    est_cost_usd     = @{ low = 1; high = 10; note = "2-4h incl ~63GB HF download" }
    forbidden        = @("Track A promotion", "competition submit", "MKM core auto-wire")
}

$outJson = Join-Path $RepoRoot "reports\runpod_nemotron_smoke_handoff_v1_latest.json"
$handoff | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outJson -Encoding UTF8

Write-Host ""
Write-Host "=== RunPod Nemotron 30B QLoRA smoke ===" -ForegroundColor Cyan
Write-Host "HF_TOKEN in .env: $(if ($hfOk) { 'yes' } else { 'MISSING — set before pod run' })" -ForegroundColor $(if ($hfOk) { 'Green' } else { 'Yellow' })
Write-Host "Bundle: $zipPath"
Write-Host ""
Write-Host "RunPod console steps:" -ForegroundColor Yellow
Write-Host "  1. https://www.runpod.io/console/pods → Deploy"
Write-Host "  2. GPU: L40S 48GB or A100 40GB | Disk: 80GB+ | Template: PyTorch 2.x"
Write-Host "  3. Pod env: HF_TOKEN = (same as local .env)"
Write-Host "  4. Upload zip from reports\ → unzip to /workspace"
Write-Host "  5. Terminal: bash scripts/runpod/runpod_nemotron_smoke_all_in_one_v1.sh"
Write-Host "  6. Stop/Terminate pod when done"
Write-Host ""
Write-Host "Handoff JSON: $outJson"

if ($PodSsh) {
    Write-Host ""
    Write-Host "=== SSH remote smoke ===" -ForegroundColor Green
    $remote = "cd /workspace && export HF_TOKEN=`"`$HF_TOKEN`" && bash scripts/runpod/runpod_nemotron_smoke_all_in_one_v1.sh"
    ssh $PodSsh $remote
    exit $LASTEXITCODE
}

if (-not $hfOk) { exit 2 }
