# Parallel: tier_v1 AB + gold_tags eval artifact + digest + pytest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$gold = "$root\docs\final\artifacts\fixtures\logos_chronology_historical_era_gold_v1.json"

Write-Host "==> [A] tier boost AB (global vs tier_v1)"
& $py "$root\scripts\run_logos_chronology_era_tier_boost_ab_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [B] historical gold_tags tier_v1 (macro boost 0.08)"
& $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
  --gold-json $gold --tag-mode gold_tags --modern-boost 0.08 --boost-policy tier_v1 `
  --output-json "$root\docs\final\artifacts\logos_chronology_era_blind_eval_v1_latest.json" `
  --append-revalidation "$root\docs\final\artifacts\logos_symbolic_revalidation_report_latest.json" `
  --revalidation-key non_synthetic_era_blind_eval_historical_gold_tags_v1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath "$root\docs\final\artifacts\logos_chronology_era_blind_eval_v1_latest.json" `
  -Destination "$root\docs\final\artifacts\logos_chronology_era_blind_eval_tier_v1_latest.json" -Force

Write-Host "==> [C] merge revalidation + digest"
& $py "$root\scripts\merge_logos_symbolic_revalidation_era_blocks_v1.py"
& $py "$root\scripts\build_logos_chronology_era_eval_digest_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [D] pytest"
& $py -m pytest tests/test_eval_logos_chronology_era_blind_v1.py tests/test_logos_chronology_hardset_and_ab_v1.py tests/test_logos_chronology_tier_boost_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: tier boost parallel complete"
