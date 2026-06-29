# Phase 2: market/news NIM handoff + DE probe refresh + status rollup
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0

function Step($n, [scriptblock] $b) {
    Write-Host "`n=== $n ==="
    & $b
    if ($LASTEXITCODE -ne 0) { $fail = 1; Write-Host "[FAIL] $n" } else { Write-Host "[OK] $n" }
}

Step 'de_anchor_probe' { py scripts/run_ng40_de_logos_anchor_probe_v1.py --page-size 3 }
Step 'nim_market_news' { py scripts/run_nim_market_news_graphrag_handoff_v1.py }
Step 'nim_logos_refresh' { py scripts/run_nim_logos_research_handoff_v1.py }
Step 'hybrid_status' { py scripts/build_hybrid_ai_lab_status_v1.py }
Step 'ops_status' { py scripts/build_nvidia_gpu_credit_ops_status_v1.py }

Write-Host "`nSSOT: reports/hybrid_ai_lab_status_v1_latest.json"
exit $fail
