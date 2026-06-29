# Local fast-profile smoke (SmolLM2-360M) — pipeline proof, no mamba / no 30B.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-NemotronLocalFastSmoke_v1.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*HF_TOKEN=(.+)\s*$') {
            $env:HF_TOKEN = $matches[1].Trim()
        }
    }
}

$env:PYTHONUNBUFFERED = "1"
$train = "data\kaggle\nvidia-nemotron-model-reasoning-challenge\kaggle_train\nemotron_qlora_train_v1.py"

py $train `
    --smoke `
    --base-model "HuggingFaceTB/SmolLM2-360M-Instruct" `
    --smoke-rows 8 `
    --smoke-steps 5 `
    --max-seq-len 384 `
    --lora-rank 8 `
    --grad-accum 4

exit $LASTEXITCODE
