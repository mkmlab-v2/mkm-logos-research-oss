param(
  [switch]$BackfillPreviousMonth
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot/..")

py "scripts/run_lens_sasang.py"
py "scripts/run_lens_logos.py"
py "scripts/run_lens_myeongni.py"
py "scripts/report_independent_lens_fusion_stub_v0.py"

if ($BackfillPreviousMonth) {
  py "scripts/report_independent_lens_shadow_gate.py" --allow-ts-override --ts-override-utc "2026-03-31T23:59:59Z" --override-label "monthly_backfill_seed_v1"
}

py "scripts/report_independent_lens_shadow_gate.py"
py "scripts/build_myeongni_commercialization_readiness_packet.py"

Write-Host "DONE: run_myeongni_shadow_monthly_catchup_v1"
