# Phase 3: NIM DE synthesis + LUT staging + hybrid spine + operator paste
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0
$nimSyn = Join-Path $root 'reports/ng40_de_probe_nim_synthesis_v1_latest.json'

function Step($n, [scriptblock] $b) {
    Write-Host "`n=== $n ==="
    & $b
    if ($LASTEXITCODE -ne 0) { $fail = 1; Write-Host "[FAIL] $n" } else { Write-Host "[OK] $n" }
}

Step 'nim_de_synthesis' { py scripts/run_nim_de_probe_synthesis_v1.py }
Step 'lut_draft_staging' {
    $lutArgs = @(
        'scripts/build_archetype_prior_lut_draft_v1.py',
        '--de-probe-json', 'reports/ng40_de_logos_anchor_probe_v1_latest.json',
        '--patch-nav-frame'
    )
    if (Test-Path $nimSyn) {
        $lutArgs += @('--nim-synthesis-json', $nimSyn)
    }
    py @lutArgs
}
Step 'hybrid_spine_stack' { py scripts/run_nextgen_hybrid_spine_logos_stack_v1.py }
Step 'market_news_nim_v2' { py scripts/run_nim_market_news_graphrag_handoff_v1.py }
Step 'genai_handoff_report' { py scripts/run_ng40_genai_de_research_handoff_v1.py }
Step 'operator_paste' { py scripts/build_nvidia_hybrid_operator_paste_pack_v1.py }
Step 'hybrid_status' { py scripts/build_hybrid_ai_lab_status_v1.py }

Write-Host "`nPaste: reports/nvidia_hybrid_operator_paste_v1_latest.txt"
Write-Host "LUT: experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json (pending signoff)"
exit $fail
