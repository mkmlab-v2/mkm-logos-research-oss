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

Write-Host "==> [C] text_blind eval on v2 gold"
& $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
  --gold-json "$root\docs\final\artifacts\logos_chronology_hardset_news_era_gold_v2_latest.json" `
  --tag-mode text_blind --modern-boost 0.08 --boost-policy tier_v1 `
  --output-json "$root\docs\final\artifacts\logos_chronology_hardset_text_blind_v2_eval_v1_latest.json" `
  --append-revalidation "$root\docs\final\artifacts\logos_symbolic_revalidation_report_latest.json" `
  --revalidation-key non_synthetic_era_blind_eval_hardset_v2
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [D] digest + merge revalidation"
& $py "$root\scripts\merge_logos_symbolic_revalidation_era_blocks_v1.py"
& $py "$root\scripts\build_logos_chronology_era_eval_digest_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [E] pytest"
& $py -m pytest tests/test_logos_chronology_hardset_gold_v2_v1.py tests/test_logos_chronology_tier_boost_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: hardset parallel complete"
