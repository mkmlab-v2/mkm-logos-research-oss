#Requires -Version 5.1
<#
.SYNOPSIS
  O-P29b full bundle: dynamic per-date lens (b-1) + news/macro as-of (b-2) in shadow only.

.DESCRIPTION
  Does NOT overwrite prophecy_hit_rate_eval_latest.json or Track A paths.
  Writes under reports/op29b_shadow/ and optional compare vs op29a.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$MinConfidence = 0.18,
    [double]$NeutralBps = 4.0
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$shadow = Join-Path $WorkspaceRoot "reports\op29b_shadow"
New-Item -ItemType Directory -Force -Path $shadow | Out-Null

$py = "py"
$btc = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$kospi = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"

Write-Host "==> O-P29b-1+b-2 dynamic per-date ensemble (v2)" -ForegroundColor Cyan
& $py scripts/build_btrack_ensemble_per_date_directions_op29b_v1.py `
    --recent-trading-days 180 `
    --ensemble-mode v2_confidence_fusion `
    --output (Join-Path $shadow "btrack_ensemble_per_date_directions_180d_op29b_v1.json")
if ($LASTEXITCODE -ne 0) { throw "op29b per-date build failed" }

$perDate = Join-Path $shadow "btrack_ensemble_per_date_directions_180d_op29b_v1.json"
$perDateGated = Join-Path $shadow "btrack_ensemble_per_date_directions_180d_op29b_gated.json"
$scoreShadow = Join-Path $shadow "btrack_prophecy_score_op29b_shadow.json"
$holdoutOut = Join-Path $shadow "prophecy_headline_confidence_holdout_op29b.json"
$sweepOut = Join-Path $shadow "prophecy_headline_deadzone_hold_sweep_op29b.json"
$evalShadow = Join-Path $shadow "prophecy_hit_rate_eval_op29b_shadow.json"
$summaryOut = Join-Path $shadow "o29b_full_bundle_summary_v1.json"

Write-Host "==> min_confidence gate (O-P28 parity)" -ForegroundColor Cyan
& $py scripts/apply_btrack_min_conf_to_per_date_directions_v1.py `
    --input $perDate --output $perDateGated --min-direction-confidence $MinConfidence
if ($LASTEXITCODE -ne 0) { throw "gate failed" }

Write-Host "==> dual-leg score shadow" -ForegroundColor Cyan
& $py scripts/build_btrack_prophecy_score_from_ohlcv.py `
    --btc-csv $btc --kospi-csv $kospi `
    --per-date-direction-json $perDateGated `
    --recent-trading-days 180 --force-dual-leg-panel --neutral-bps $NeutralBps `
    --output $scoreShadow
if ($LASTEXITCODE -ne 0) { throw "score build failed" }

Write-Host "==> holdout + sweep + in-sample eval (parallel)" -ForegroundColor Cyan
$jobs = @(
    @{ Name = "holdout"; Args = @(
        "scripts/eval_prophecy_headline_confidence_holdout_v1.py",
        "--score-json", $scoreShadow,
        "--per-date-json", $perDateGated,
        "--output", $holdoutOut
    ) },
    @{ Name = "sweep"; Args = @(
        "scripts/sweep_prophecy_headline_deadzone_hold_v1.py",
        "--score-json", $scoreShadow,
        "--per-date-json", $perDateGated,
        "--output", $sweepOut
    ) },
    @{ Name = "eval"; Args = @(
        "scripts/eval_prophecy_hit_rate_v1.py",
        "--run-mode", "price",
        "--score-json", $scoreShadow,
        "--output", $evalShadow
    ) }
)
$procs = foreach ($j in $jobs) {
    Start-Process -FilePath $py -ArgumentList $j.Args -WorkingDirectory $WorkspaceRoot -PassThru -NoNewWindow
}
$procs | Wait-Process
foreach ($j in $jobs) { }
if (($procs | ForEach-Object { $_.ExitCode }) -contains $null) { throw "parallel subprocess failed" }
$bad = $procs | Where-Object { $_.ExitCode -ne 0 }
if ($bad) {
    Write-Host "WARN: some parallel steps non-zero exit (holdout may be 2 on fail)" -ForegroundColor Yellow
}

Write-Host "==> headline SSOT unchanged check" -ForegroundColor Cyan
$headline = Get-Content (Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_latest.json") -Raw | ConvertFrom-Json
$hr = [double]$headline.metrics.price_directional_hit_rate
if ([math]::Abs($hr - 0.535354) -gt 0.0001) {
    Write-Host "WARN: headline hit rate drifted from 53.5% — investigate" -ForegroundColor Yellow
} else {
    Write-Host "OK: headline still 53.5% ACTIVE" -ForegroundColor Green
}

Write-Host "==> summary JSON" -ForegroundColor Cyan
& $py -c @"
import json
from pathlib import Path
root = Path(r'$WorkspaceRoot')
shadow = root / 'reports/op29b_shadow'
def load(p):
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
sweep = load(shadow / 'prophecy_headline_deadzone_hold_sweep_op29b.json')
hold = load(shadow / 'prophecy_headline_confidence_holdout_op29b.json')
op29a = load(root / 'reports/op29a_shadow/o29a_ab_summary_v1.json')
headline = load(root / 'docs/final/artifacts/prophecy_hit_rate_eval_latest.json')
best = sweep.get('best_active') or {}
test = (hold.get('test') or {}).get('metrics_active') or {}
doc = {
  'schema': 'o29b_full_bundle_summary_v1',
  'hypothesis_tier': 'B',
  'research_only': True,
  'headline_overwritten': False,
  'headline_active_hit_rate': (headline.get('metrics') or {}).get('price_directional_hit_rate'),
  'op29b_dynamic': {
    'active_hit_rate': best.get('price_directional_hit_rate_active'),
    'coverage_active': best.get('coverage_active'),
    'passes_both': sweep.get('passes_both'),
  },
  'op29a_static_v2_reference': op29a.get('op28_style_active_sweep', {}),
  'holdout_test_active': test.get('price_directional_hit_rate_active'),
  'holdout_coverage': test.get('coverage_active'),
  'holdout_pass': hold.get('holdout_pass'),
  'verdict_ko': 'O-P29b dynamic feed shadow complete; compare op29b vs op29a vs headline in shadow only.',
}
out = shadow / 'o29b_full_bundle_summary_v1.json'
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('WROTE', out)
"@

Write-Host "DONE O-P29b shadow: $shadow" -ForegroundColor Green
exit 0
