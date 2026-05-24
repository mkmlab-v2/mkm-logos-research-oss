# Finalize provisional 7 + q01 theology order + RAG eval + closure (no bootstrap precision)
param(
    [switch]$SkipClosure,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> q01 theology primary order" -ForegroundColor Cyan
& $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
if ($LASTEXITCODE -ne 0) { throw "q01 order" }

Write-Host "==> provisional 7: commander signoff pack ranks 2-4" -ForegroundColor Cyan
& $py scripts/apply_logos_rag_commander_gold_signoff_v1.py --l2-provisional-thematic pack_ranks_2_4
if ($LASTEXITCODE -ne 0) { throw "signoff" }

Write-Host "==> q01 theology primary (re-apply before align)" -ForegroundColor Cyan
& $py scripts/apply_logos_rag_q01_theology_primary_order_v1.py
if ($LASTEXITCODE -ne 0) { throw "q01 re-apply" }

Write-Host "==> harness align + dual eval (q01 union skipped)" -ForegroundColor Cyan
& $py scripts/apply_logos_rag_thematic_harness_align_v1.py
if ($LASTEXITCODE -ne 0) { throw "harness align" }
& $py scripts/run_logos_rag_dual_gold_eval_v1.py
if ($LASTEXITCODE -ne 0) { throw "dual eval" }
& $py scripts/check_logos_rag_btrack_promotion_gate_v1.py
if ($LASTEXITCODE -ne 0) { throw "gate" }

& $py scripts/build_logos_rag_q01_theology_adjudication_v1.py
& $py scripts/export_logos_rag_provisional_thematic_review_v1.py

if (-not $SkipClosure) {
    & $py scripts/build_showroom_meaning_topology_graph_slice_v1.py --max-nodes 128
    & $py scripts/build_logos_100pct_closure_v1.py --run-pytest
    if ($LASTEXITCODE -ne 0) { throw "closure" }
}

Write-Host "==> provisional gold finalize done" -ForegroundColor Green
