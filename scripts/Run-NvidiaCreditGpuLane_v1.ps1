# NVIDIA GPU credit lane (no Kaggle): NIM inference + local embed/small + Lab status
param([switch] $SkipAb)
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0

function Step($n, [scriptblock] $b) {
    Write-Host "`n=== $n ==="
    & $b
    if ($LASTEXITCODE -ne 0) { $fail = 1 }
}

Step 'policy_status' { py scripts/build_nvidia_gpu_credit_ops_status_v1.py }
Step 'nvidia_api_primary' { py scripts/run_nvidia_api_primary_lane_v1.py }
Step 'ngc_smoke' { py scripts/_check_ngc_env_smoke_v1.py }
Step 'nim_70b' { py scripts/nvidia_nim_large_model_smoke_v1.py }
Step 'hybrid_embed' { py scripts/run_hybrid_local_nim_chain_v1.py }
if (-not $SkipAb) { Step 'ab_local_8b_vs_nim' { py scripts/run_hybrid_local_vs_nim_ab_v1.py } }
Step 'nim_logos_handoff' { py scripts/run_nim_logos_research_handoff_v1.py }

Write-Host "`n[Kaggle GPU] skipped — use Innovation Lab when accepted; NIM for inference now."
Write-Host "SSOT: reports/nvidia_gpu_credit_ops_status_v1_latest.json"
exit $fail
