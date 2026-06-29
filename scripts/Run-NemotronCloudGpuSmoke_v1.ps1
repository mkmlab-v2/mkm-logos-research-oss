# RunPod / Lambda / Vast — Nemotron 30B QLoRA smoke checklist + optional WSL→SSH handoff.
# Does NOT provision cloud VMs (human gate). Prints copy-paste steps.
# Usage:
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-NemotronCloudGpuSmoke_v1.ps1
#   pwsh ... -File scripts/Run-NemotronCloudGpuSmoke_v1.ps1 -ShowRunPodOneLiner

param(
    [switch]$ShowRunPodOneLiner,
    [string]$PodSsh = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$checklist = @{
    schema          = "nemotron_cloud_gpu_smoke_checklist_v1"
    lane            = "research_only"
    updated_at      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    min_total_vram_gb = 20
    recommended_vram_gb = 40
    min_disk_gb     = 80
    smoke_cost_usd  = @{ low = 1; high = 10; note = "2-4h L40S/A100 first run incl ~63GB download" }
    gpu_skus        = @(
        @{ provider = "RunPod"; sku = "L40S 48GB"; usd_per_hr = "0.40-0.86"; fit = "recommended" }
        @{ provider = "RunPod"; sku = "A100 40GB"; usd_per_hr = "0.59-1.49"; fit = "recommended" }
        @{ provider = "RunPod"; sku = "RTX 4090 24GB"; usd_per_hr = "0.34-0.69"; fit = "tight_single_gpu" }
        @{ provider = "Kaggle"; sku = "T4 x2"; usd_per_hr = "0"; fit = "free_if_quota; RAM 30GB risk" }
        @{ provider = "Azure"; sku = "NC4as_T4_v3+"; usd_per_hr = "credits"; fit = "blocked_until_gpu_quota" }
    )
    steps           = @(
        "Pick GPU: L40S 48GB or A100 40GB (RunPod Secure Cloud or Lambda on-demand)."
        "Disk: >=80GB volume at /workspace (RunPod template: PyTorch 2.x + CUDA 12)."
        "Secrets: HF_TOKEN in pod env (Settings or export before run)."
        "Clone or rsync repo to pod; or upload only kaggle_train/ + train.csv + script."
        "Install: pip install torch transformers peft trl bitsandbytes accelerate datasets huggingface_hub"
        "Mamba (Nemotron): pip install mamba-ssm causal-conv1d --no-build-isolation OR use prebuilt wheels (see run_nemotron_wsl_install_mamba_v1.sh)."
        "Run: bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh"
        "Pull report: reports/kaggle_nemotron_kaggle_train_latest.json + kaggle_train/output/"
        "Stop pod when done (per-second billing on RunPod)."
    )
    kaggle_v46_cell = "reports/kaggle_nemotron_notebook_cell12_combined_v46.txt"
    forbidden       = @("Track A promotion", "competition submit", "MKM core auto-wire")
}

$outJson = "reports/nemotron_cloud_gpu_smoke_checklist_v1_latest.json"
$checklist | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 $outJson
Write-Host "[OK] wrote $outJson"

Write-Host ""
Write-Host "=== Nemotron 30B QLoRA smoke — cloud checklist ===" -ForegroundColor Cyan
Write-Host "VRAM: >=20GB total (40GB+ recommended) | Disk: ~80GB+ | Est cost: `$1-10 smoke"
Write-Host ""
foreach ($s in $checklist.steps) { Write-Host "  • $s" }
Write-Host ""
Write-Host "Kaggle (free): paste $outJson → kaggle_v46_cell path in JSON" -ForegroundColor Yellow
Write-Host "  -> $($checklist.kaggle_v46_cell)"
Write-Host ""

if ($ShowRunPodOneLiner) {
    $hf = $env:HF_TOKEN
    if (-not $hf -and (Test-Path ".env")) {
        $m = Select-String -Path ".env" -Pattern '^\s*HF_TOKEN=(.+)\s*$' | Select-Object -First 1
        if ($m) { $hf = $m.Matches[0].Groups[1].Value.Trim() }
    }
    Write-Host "=== RunPod pod shell (after git clone to /workspace) ===" -ForegroundColor Green
    Write-Host @"
export HF_TOKEN='(set in RunPod secrets — do not paste in chat)'
cd /workspace
bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh
"@
}

if ($PodSsh) {
    Write-Host "=== SSH remote smoke ===" -ForegroundColor Green
    $remote = "cd /workspace && bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh"
    ssh $PodSsh $remote
    exit $LASTEXITCODE
}

Write-Host "Optional: -ShowRunPodOneLiner | -PodSsh user@host:port (RunPod TCP proxy SSH)"
