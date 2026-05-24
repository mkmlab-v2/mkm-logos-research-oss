# Parallel: hardset text_blind eval + narrative modern_boost AB
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "==> [A] build hardset news era gold"
& $py "$root\scripts\build_logos_hardset_news_era_gold_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [B] modern_boost AB (narrative tier)"
& $py "$root\scripts\run_logos_chronology_era_modern_boost_ab_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [C] hardset text_blind eval"
& $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
  --gold-json "$root\docs\final\artifacts\logos_chronology_hardset_news_era_gold_v1_latest.json" `
  --tag-mode text_blind `
  --modern-boost 0 `
  --output-json "$root\docs\final\artifacts\logos_chronology_hardset_text_blind_eval_v1_latest.json" `
  --append-revalidation "$root\docs\final\artifacts\logos_symbolic_revalidation_report_latest.json" `
  --revalidation-key non_synthetic_era_blind_eval_hardset_v1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: parallel eval complete"
