# MKM recommended hybrid stack — one command
# Local: Ollama llama3.1:8b + nomic embed | Cloud: NIM llama-3.3-70b
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0

function Step($n, [scriptblock] $b) {
    Write-Host "`n=== $n ==="
    & $b
    if ($LASTEXITCODE -ne 0) { $fail = 1; Write-Host "[FAIL] $n" } else { Write-Host "[OK] $n" }
}

Step 'ngc_check' { py scripts/_check_ngc_env_smoke_v1.py }
Step 'hybrid_embed_nim' { py scripts/run_hybrid_local_nim_chain_v1.py }
Step 'ab_local_vs_70b' { py scripts/run_hybrid_local_vs_nim_ab_v1.py }
# Kaggle GPU cancelled — NVIDIA credits: NIM (now) + Innovation Lab Brev (when accepted)
Step 'nvidia_credit_lane' { powershell -NoProfile -File scripts/Run-NvidiaCreditGpuLane_v1.ps1 -SkipAb }
Step 'nvidia_phase2' { powershell -NoProfile -File scripts/Run-NvidiaCreditGpuLanePhase2_v1.ps1 }
Step 'hybrid_status' { py scripts/build_hybrid_ai_lab_status_v1.py }

Write-Host "`nReports:"
Write-Host '  reports/hybrid_local_vs_nim_ab_v1_latest.json'
Write-Host '  reports/hybrid_local_nim_chain_v1_latest.json'
Write-Host '  reports/hybrid_ai_lab_status_v1_latest.json'
exit $fail
