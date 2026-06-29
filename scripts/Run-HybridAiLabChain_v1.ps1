# One-shot: NGC smoke + Ollama + NIM + hybrid chain + Nemotron Windows dry-run
param(
    [switch] $SkipWsl,
    [switch] $SkipNemotronWin,
    [switch] $IncludeLargeNim,
    [switch] $IncludeWslSmoke
)
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0

function Step($name, [scriptblock] $block) {
    Write-Host "`n=== $name ==="
    & $block
    if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] $name exit=$LASTEXITCODE"; $script:fail = 1 }
    else { Write-Host "[OK] $name" }
}

Step 'ngc_env' { py scripts/_check_ngc_env_smoke_v1.py }
Step 'nim_smoke' { py scripts/nvidia_nim_chat_v1.py smoke }
Step 'ollama' { py scripts/ollama_local_smoke_v1.py }
Step 'hybrid' { py scripts/run_hybrid_local_nim_chain_v1.py }
if ($IncludeLargeNim) { Step 'nim_70b' { py scripts/nvidia_nim_large_model_smoke_v1.py } }
if (-not $SkipNemotronWin) {
    Step 'nemotron_win_dryrun' {
        py data/nvidia/nemotron-local/nemotron_qlora_train_v1.py --dry-run --limit 4 `
            --out-report-json reports/nvidia_nemotron_local_train_dryrun_latest.json
    }
}
if (-not $SkipWsl) {
    Step 'wsl_readiness' { powershell -NoProfile -File scripts/Verify-NvidiaNemotronWslReadiness_v1.ps1 }
    Step 'wsl_dryrun' { powershell -NoProfile -File scripts/Invoke-NvidiaNemotronLocalTrain_v1.ps1 -DryRunLocal }
    if ($IncludeWslSmoke) {
        Step 'wsl_smoke' { powershell -NoProfile -File scripts/Invoke-NvidiaNemotronLocalTrain_v1.ps1 -Smoke }
    }
}

Write-Host "`n=== summary fail=$fail ==="
exit $fail
