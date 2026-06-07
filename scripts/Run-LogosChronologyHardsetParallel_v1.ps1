# Parallel: hardset gold v2 + mode compare + text_blind eval + digest + pytest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> [A] hardset gold v2 (rank_top1 + overrides slot)"
& $py "$root\scripts\build_logos_hardset_news_era_gold_v2_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [B] v1 vs v2 text_blind compare"
& $py "$root\scripts\run_logos_hardset_gold_mode_compare_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [C] tier_v2 SSOT merge (parallel eval + digest + locked_eval compare)"
& $py "$root\scripts\run_logos_chronology_tier_v2_ssot_merge_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [D] hardset closure (readiness + human margin report + historical AB)"
& $py "$root\scripts\run_logos_chronology_hardset_closure_v1.py" -SkipMerge
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [E] pytest"
& $py -m pytest tests/test_logos_chronology_hardset_gold_v2_v1.py tests/test_logos_chronology_tier_boost_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: hardset parallel complete"
