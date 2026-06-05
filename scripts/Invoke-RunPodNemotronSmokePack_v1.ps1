#Requires -Version 5.1
<#
.SYNOPSIS
  Pack minimal Nemotron 30B QLoRA smoke bundle for RunPod upload (~few MB + train.csv).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-RunPodNemotronSmokePack_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutDir = "",
    [string]$OutZip = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$slug = "nvidia-nemotron-model-reasoning-challenge"
$trainPy = Join-Path $RepoRoot "data\kaggle\$slug\kaggle_train\nemotron_qlora_train_v1.py"
$trainCsv = Join-Path $RepoRoot "data\kaggle\$slug\train.csv"
$scripts = @(
    "scripts\run_nemotron_cloud_bootstrap_v1.sh",
    "scripts\run_nemotron_cloud_gpu_smoke_v1.sh",
    "scripts\run_nemotron_wsl_install_mamba_v1.sh",
    "scripts\runpod\runpod_nemotron_smoke_all_in_one_v1.sh"
)

foreach ($p in @($trainPy, $trainCsv) + $scripts) {
    $full = if ([System.IO.Path]::IsPathRooted($p)) { $p } else { Join-Path $RepoRoot $p }
    if (-not (Test-Path -LiteralPath $full)) { throw "missing: $full" }
}

if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot "reports\runpod_nemotron_smoke_bundle"
}
if (-not $OutZip) {
    $OutZip = Join-Path $RepoRoot "reports\runpod_nemotron_smoke_bundle_v1.zip"
}

if (Test-Path -LiteralPath $OutDir) {
    Remove-Item -LiteralPath $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Copy-Rel {
    param([string]$Rel)
    $src = Join-Path $RepoRoot ($Rel -replace '/', '\')
    $dst = Join-Path $OutDir ($Rel -replace '/', '\')
    $parent = Split-Path -Parent $dst
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
}

Copy-Rel "data/kaggle/$slug/kaggle_train/nemotron_qlora_train_v1.py"
Copy-Rel "data/kaggle/$slug/train.csv"
foreach ($s in $scripts) { Copy-Rel ($s -replace '\\', '/') }

Get-ChildItem -Path $OutDir -Recurse -Filter *.sh | ForEach-Object {
    $text = [IO.File]::ReadAllText($_.FullName) -replace "`r`n", "`n"
    [IO.File]::WriteAllText($_.FullName, $text, (New-Object System.Text.UTF8Encoding $false))
}

$readme = @"
RunPod Nemotron 30B QLoRA smoke bundle (research_only)
======================================================
1. Pod: PyTorch 2.x + CUDA 12, L40S 48GB or A100 40GB, volume >= 80GB at /workspace
2. Env: HF_TOKEN=(your token)
3. Unzip to /workspace (must preserve data/kaggle/... and scripts/ paths)
4. Run: bash scripts/runpod/runpod_nemotron_smoke_all_in_one_v1.sh
5. Download: reports/kaggle_nemotron_kaggle_train_latest.json
6. Stop pod when done.
"@
Set-Content -LiteralPath (Join-Path $OutDir "README_RUNPOD.txt") -Value $readme -Encoding UTF8

if (Test-Path -LiteralPath $OutZip) { Remove-Item -LiteralPath $OutZip -Force }
# Use Python zipfile so paths stay POSIX (Compress-Archive emits backslashes; Linux unzip breaks).
$pyZip = @"
import zipfile
from pathlib import Path
root = Path(r'$($OutDir -replace '\\','/')')
out = Path(r'$($OutZip -replace '\\','/')')
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(root.rglob('*')):
        if path.is_file():
            zf.write(path, path.relative_to(root).as_posix())
print('zip_ok', out)
"@
$pyZip | py - | Out-Null
if ($LASTEXITCODE -ne 0) { throw "python zip pack failed exit=$LASTEXITCODE" }

$csvSize = (Get-Item -LiteralPath $trainCsv).Length
$zipSize = (Get-Item -LiteralPath $OutZip).Length
Write-Host "[OK] bundle_dir=$OutDir"
Write-Host "[OK] zip=$OutZip size_mb=$([math]::Round($zipSize/1MB, 2)) train_csv_mb=$([math]::Round($csvSize/1MB, 2))"
