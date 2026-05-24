# Full era blind eval chain: historical + hardset + AB + revalidation merge + dynamic map refresh
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$reval = "$root\docs\final\artifacts\logos_symbolic_revalidation_report_latest.json"
$goldHist = "$root\docs\final\artifacts\fixtures\logos_chronology_historical_era_gold_v1.json"

Write-Host "==> hardset gold"
& $py "$root\scripts\build_logos_hardset_news_era_gold_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> historical gold_tags (tier_v1 macro boost 0.08)"
& $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
  --gold-json $goldHist --tag-mode gold_tags --modern-boost 0.08 --boost-policy tier_v1 `
  --output-json "$root\docs\final\artifacts\logos_chronology_era_blind_eval_v1_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> historical text_blind"
& $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
  --gold-json $goldHist --tag-mode text_blind `
  --output-json "$root\docs\final\artifacts\logos_chronology_era_blind_eval_text_blind_v1_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> hardset text_blind"
& $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
  --gold-json "$root\docs\final\artifacts\logos_chronology_hardset_news_era_gold_v1_latest.json" `
  --tag-mode text_blind `
  --output-json "$root\docs\final\artifacts\logos_chronology_hardset_text_blind_eval_v1_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> modern_boost AB"
& $py "$root\scripts\run_logos_chronology_era_modern_boost_ab_v1.py" --append-revalidation $reval
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> revalidation merge"
& $py "$root\scripts\merge_logos_symbolic_revalidation_era_blocks_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> dynamic map (boost 0 default)"
& $py "$root\scripts\build_logos_chronology_dynamic_map_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> pytest"
& $py -m pytest tests/test_eval_logos_chronology_era_blind_v1.py tests/test_logos_chronology_hardset_and_ab_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> operator digest"
& $py "$root\scripts\build_logos_chronology_era_eval_digest_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: Run-LogosChronologyEraBlindEvalFull_v1 complete"
